# 【功能描述】LLM HTML/CSS 排版渲染器：Carousel → HTML/CSS → Chrome 截图 PNG
# 【输入】Carousel；TextLLM；render_code 提示词
# 【输出】01.png … 0N.png 路径列表，同时保存 render_design.json / page html

from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from collections.abc import Callable
from pathlib import Path

from md2xhs.domain.models import Carousel
from md2xhs.domain.ports import TextLLM
from md2xhs.infra.carousel_json import carousel_to_dict, parse_json_object

_PROMPT = (Path(__file__).parent.parent / "prompts" / "render_code.txt").read_text(encoding="utf-8")
_PAGE_PROMPT = (Path(__file__).parent.parent / "prompts" / "render_page_code.txt").read_text(encoding="utf-8")
W, H = 1242, 1660


class LlmHtmlCodeRenderer:
    def __init__(
        self,
        llm: TextLLM,
        chrome_path: str | None = None,
        max_retries: int = 2,
        *,
        llm_factory: Callable[[], TextLLM] | None = None,
        max_workers: int = 3,
    ):
        self._llm = llm
        self._chrome_path = chrome_path or self._find_chrome()
        self._max_retries = max_retries
        self._llm_factory = llm_factory
        self._max_workers = max(1, max_workers)

    def render_carousel(self, carousel: Carousel, output_dir: str) -> list[str]:
        out = Path(output_dir)
        out.mkdir(parents=True, exist_ok=True)
        for stale in out.glob("[0-9][0-9].png"):
            stale.unlink()

        design = self._plan_design(carousel)
        self._validate_design(design)
        (out / "04_render_design.json").write_text(
            json.dumps(design, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        html_dir = out / "html_pages"
        html_dir.mkdir(parents=True, exist_ok=True)
        paths: list[str] = []
        global_css = design.get("global_css") or ""
        for page in design.get("pages") or []:
            idx = int(page.get("index") or len(paths) + 1)
            filename = page.get("filename") or f"{idx:02d}.png"
            png_path = out / filename
            html_path = html_dir / f"{idx:02d}.html"
            doc = self._build_doc(global_css, page.get("css") or "", page.get("html") or "")
            html_path.write_text(doc, encoding="utf-8")
            self._screenshot(html_path, png_path)
            paths.append(str(png_path))
        return paths

    def _plan_design(self, carousel: Carousel) -> dict:
        carousel_dict = carousel_to_dict(carousel)
        post_context = json.dumps(
            {
                "post_title": carousel_dict.get("post_title"),
                "caption": carousel_dict.get("caption"),
                "tags": carousel_dict.get("tags"),
                "total_pages": len(carousel.slides),
            },
            ensure_ascii=False,
            indent=2,
        )
        if self._llm_factory and self._max_workers > 1:
            pages = self._plan_pages_concurrently(carousel_dict, post_context)
        else:
            pages = [
                self._plan_page(carousel_dict, post_context, idx, self._llm)
                for idx in range(1, len(carousel.slides) + 1)
            ]
        return {"global_css": "", "pages": pages}

    def _plan_pages_concurrently(self, carousel_dict: dict, post_context: str) -> list[dict]:
        page_count = len(carousel_dict.get("slides") or [])
        pages_by_index: dict[int, dict] = {}
        workers = min(self._max_workers, page_count)
        with ThreadPoolExecutor(max_workers=workers) as executor:
            futures = {
                executor.submit(self._plan_page, carousel_dict, post_context, idx, self._llm_factory()): idx
                for idx in range(1, page_count + 1)
            }
            for future in as_completed(futures):
                idx = futures[future]
                pages_by_index[idx] = future.result()
        return [pages_by_index[idx] for idx in range(1, page_count + 1)]

    def _plan_page(self, carousel_dict: dict, post_context: str, idx: int, llm: TextLLM) -> dict:
        page_count = len(carousel_dict.get("slides") or [])
        print(f"[render-html] planning page {idx}/{page_count}", file=sys.stderr, flush=True)
        prompt = _PAGE_PROMPT.format(
            page_index=idx,
            filename=f"{idx:02d}.png",
            post_context=post_context,
            slide_json=json.dumps(carousel_dict["slides"][idx - 1], ensure_ascii=False, indent=2),
        )
        data = self._complete_design_json(prompt, "排版 JSON 不合格", llm=llm)
        print(f"[render-html] page {idx} design ready", file=sys.stderr, flush=True)
        page_list = data.get("pages") or []
        if len(page_list) != 1:
            raise ValueError("逐页排版必须只返回 1 个 page")
        page = page_list[0]
        page["index"] = idx
        page["filename"] = f"{idx:02d}.png"
        page["css"] = (data.get("global_css") or "") + "\n" + (page.get("css") or "")
        return page

    def _plan_design_all_at_once(self, carousel: Carousel) -> dict:
        prompt = _PROMPT.format(
            carousel_json=json.dumps(carousel_to_dict(carousel), ensure_ascii=False, indent=2)
        )
        return self._complete_design_json(prompt, "排版 JSON 不合格")

    def _complete_design_json(self, prompt: str, label: str, *, llm: TextLLM | None = None) -> dict:
        active_llm = llm or self._llm
        extra = ""
        last_err: Exception | None = None
        for _ in range(self._max_retries + 1):
            try:
                data = parse_json_object(active_llm.complete(prompt + extra))
                self._validate_design(data)
                return data
            except (ValueError, json.JSONDecodeError, TimeoutError, RuntimeError, Exception) as e:
                last_err = e
                extra = f"\n\n【{label}】{e}\n请重新输出完整合法 JSON。"
        raise last_err or ValueError("排版代码生成失败")

    def _validate_design(self, data: dict) -> None:
        if not isinstance(data.get("global_css"), str):
            raise ValueError("缺少 global_css 字符串")
        pages = data.get("pages")
        if not isinstance(pages, list) or not pages:
            raise ValueError("pages 为空")
        banned = [
            "<script",
            "</script",
            "<iframe",
            "<canvas",
            "javascript:",
            "@import",
            "http://",
            "https://",
            "data:image",
            "base64",
            "position: fixed",
            "letter-spacing:-",
            "letter-spacing: -",
        ]
        for page in pages:
            html = page.get("html")
            css = page.get("css") or ""
            if not isinstance(html, str) or "<main" not in html or "</main>" not in html:
                raise ValueError("page.html 必须包含 main")
            blob = (data["global_css"] + css + html).lower()
            for token in banned:
                if token in blob:
                    raise ValueError(f"排版代码包含禁用内容: {token}")
            tags = re.findall(r"</?([a-zA-Z0-9]+)", html)
            allowed = {"main", "section", "header", "div", "p", "span", "strong", "ol", "ul", "li"}
            illegal = sorted({t.lower() for t in tags if t.lower() not in allowed})
            if illegal:
                raise ValueError(f"HTML 包含禁用标签: {illegal}")

    def _build_doc(self, global_css: str, page_css: str, body: str) -> str:
        return f"""<!doctype html>
<html>
<head>
<meta charset="utf-8">
<meta name="viewport" content="width={W}, initial-scale=1">
<style>
* {{ box-sizing: border-box; }}
html, body {{ margin: 0; width: {W}px; height: {H}px; overflow: hidden; }}
body {{ font-family: system-ui, -apple-system, BlinkMacSystemFont, "PingFang SC", "Microsoft YaHei", sans-serif; }}
{global_css}
{page_css}
</style>
</head>
<body>
{body}
</body>
</html>
"""

    def _screenshot(self, html_path: Path, png_path: Path) -> None:
        url = html_path.resolve().as_uri()
        cmd = [
            self._chrome_path,
            "--headless=new",
            "--disable-gpu",
            "--hide-scrollbars",
            f"--window-size={W},{H}",
            f"--screenshot={png_path}",
            url,
        ]
        subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    def _find_chrome(self) -> str:
        candidates = [
            shutil.which("google-chrome"),
            shutil.which("chromium"),
            shutil.which("chrome"),
            "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
            "/Applications/Chromium.app/Contents/MacOS/Chromium",
        ]
        for candidate in candidates:
            if candidate and Path(candidate).exists():
                return str(candidate)
        raise FileNotFoundError("未找到 Chrome/Chromium，无法进行 HTML 截图")
