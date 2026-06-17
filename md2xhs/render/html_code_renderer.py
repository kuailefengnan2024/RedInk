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

        # Clean stale HTML pages
        html_dir = out / "html_pages"
        if html_dir.exists():
            shutil.rmtree(html_dir)
        html_dir.mkdir(parents=True, exist_ok=True)

        design = self._plan_design(carousel)
        self._validate_design(design)
        
        # Save formatted design where html and css are lists of lines for easy editing
        import copy
        display_design = copy.deepcopy(design)
        if "global_css" in display_design and isinstance(display_design["global_css"], str):
            display_design["global_css"] = display_design["global_css"].splitlines()
        for page in display_design.get("pages") or []:
            if "html" in page and isinstance(page["html"], str):
                page["html"] = page["html"].splitlines()
            if "css" in page and isinstance(page["css"], str):
                page["css"] = page["css"].splitlines()

        (out / "04_render_design.json").write_text(
            json.dumps(display_design, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        html_dir = out / "html_pages"
        html_dir.mkdir(parents=True, exist_ok=True)
        paths: list[str] = []
        global_css = design.get("global_css") or ""
        for page in design.get("pages") or []:
            idx = int(page.get("index") or len(paths) + 1)
            filename = page.get("filename") or f"{idx:02d}.png"
            png_path = (out / filename).resolve()
            html_path = html_dir / f"{idx:02d}.html"
            
            slide = carousel.slides[idx - 1]
            page_html = page.get("html") or ""
            
            replacements = {
                "{{label}}": slide.label,
                "{{label }}": slide.label,
                "{{ label}}": slide.label,
                "{{ label }}": slide.label,
                "{{icon}}": slide.icon,
                "{{icon }}": slide.icon,
                "{{ icon}}": slide.icon,
                "{{ icon }}": slide.icon,
                "{{title}}": "<br>".join(slide.title),
                "{{title }}": "<br>".join(slide.title),
                "{{ title}}": "<br>".join(slide.title),
                "{{ title }}": "<br>".join(slide.title),
                "{{highlight}}": slide.highlight,
                "{{highlight }}": slide.highlight,
                "{{ highlight}}": slide.highlight,
                "{{ highlight }}": slide.highlight,
                "{{highlight_sub}}": slide.highlight_sub,
                "{{highlight_sub }}": slide.highlight_sub,
                "{{ highlight_sub}}": slide.highlight_sub,
                "{{ highlight_sub }}": slide.highlight_sub,
                "{{footnote}}": slide.footnote,
                "{{footnote }}": slide.footnote,
                "{{ footnote}}": slide.footnote,
                "{{ footnote }}": slide.footnote,
            }
            for key, val in replacements.items():
                page_html = page_html.replace(key, val)
                
            # Strip LLM-generated header labels and icons on non-cover pages
            if slide.type != "cover":
                # Strip elements with page-label, page-icon, page-number, etc.
                page_html = re.sub(
                    r'<(span|p|div)[^>]*class\s*=\s*[\'"]?[^\'"]*(page|header)-(label|icon|number)[^\'"]*[\'"]?[^>]*>.*?</\1>',
                    '',
                    page_html,
                    flags=re.DOTALL | re.IGNORECASE
                )

                # Inject our standardized page label (only current page number)
                header_html = f'<div class="system-page-label">{idx:02d}</div>'
                main_match = re.search(r'<main[^>]*>', page_html, re.IGNORECASE)
                if main_match:
                    insert_pos = main_match.end()
                    page_html = page_html[:insert_pos] + "\n  " + header_html + page_html[insert_pos:]

            doc = self._build_doc(global_css, page.get("css") or "", page_html)
            html_path.write_text(doc, encoding="utf-8")
            self._screenshot(html_path, png_path)
            paths.append(str(png_path))
        return paths

    def render_design(self, design: dict, output_dir: str) -> list[str]:
        out = Path(output_dir)
        out.mkdir(parents=True, exist_ok=True)
        html_dir = out / "html_pages"
        html_dir.mkdir(parents=True, exist_ok=True)

        paths: list[str] = []
        global_css = design.get("global_css") or ""
        if isinstance(global_css, list):
            global_css = "\n".join(global_css)

        for page in design.get("pages") or []:
            idx = int(page.get("index") or len(paths) + 1)
            filename = page.get("filename") or f"{idx:02d}.png"
            png_path = (out / filename).resolve()
            html_path = html_dir / f"{idx:02d}.html"

            page_html = page.get("html") or ""
            if isinstance(page_html, list):
                page_html = "\n".join(page_html)

            page_css = page.get("css") or ""
            if isinstance(page_css, list):
                page_css = "\n".join(page_css)

            # Inject our standardized page label if it's not present and it's not the first page
            if idx != 1 and "system-page-label" not in page_html:
                header_html = f'<div class="system-page-label">{idx:02d}</div>'
                main_match = re.search(r'<main[^>]*>', page_html, re.IGNORECASE)
                if main_match:
                    insert_pos = main_match.end()
                    page_html = page_html[:insert_pos] + "\n  " + header_html + page_html[insert_pos:]

            doc = self._build_doc(global_css, page_css, page_html)
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
            allowed = {"main", "section", "header", "footer", "div", "p", "span", "strong", "em", "b", "i", "br", "ol", "ul", "li", "h1", "h2", "h3", "h4", "h5", "h6"}
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
html, body, h1, h2, h3, h4, h5, h6, p, ul, ol, li {{ margin: 0; padding: 0; }}
html, body {{ width: {W}px; height: {H}px; overflow: hidden; }}
body {{ font-family: system-ui, -apple-system, BlinkMacSystemFont, "PingFang SC", "Microsoft YaHei", sans-serif; }}
.page {{
  box-sizing: border-box;
  width: {W}px;
  height: {H}px;
  overflow: hidden;
  position: relative;
  padding: 100px !important;
  display: flex !important;
  flex-direction: column !important;
}}
h1, h2, h3, h4, h5, h6, p, span, li, div {{
  text-wrap: pretty;
}}
.page-title, h1, h2, h3, h4, h5, h6 {{
  text-wrap: balance;
}}
.system-page-label {{
  font-size: 38px;
  font-weight: 600;
  color: #888888;
  margin-bottom: 48px;
  text-align: left;
  width: 100%;
  font-family: system-ui, -apple-system, sans-serif;
  letter-spacing: 0;
}}
{global_css}
{page_css}
</style>
</head>
<body>
{body}
<script>
(function() {{
    const page = document.querySelector('.page');
    if (!page) return;
    
    // Ensure the page root itself is exactly fixed size
    page.style.width = '1242px';
    page.style.height = '1660px';
    page.style.boxSizing = 'border-box';
    page.style.overflow = 'hidden';
    page.style.position = 'relative';
    page.style.display = 'flex';
    page.style.flexDirection = 'column';
    
    const clientHeight = 1660;
    
    // 1. Gather elements to scale spacing
    const elementsWithSpacing = Array.from(page.querySelectorAll('*')).concat([page]);
    const spacingData = [];
    elementsWithSpacing.forEach(el => {{
        const style = window.getComputedStyle(el);
        const data = {{
            el: el,
            paddingTop: parseFloat(style.paddingTop) || 0,
            paddingBottom: parseFloat(style.paddingBottom) || 0,
            marginTop: parseFloat(style.marginTop) || 0,
            marginBottom: parseFloat(style.marginBottom) || 0,
            gap: parseFloat(style.gap) || 0
        }};
        if (data.paddingTop || data.paddingBottom || data.marginTop || data.marginBottom || data.gap) {{
            spacingData.push(data);
        }}
    }});

    // 2. Shrink spacing first (gaps, margins, card paddings)
    let spacingScale = 1.0;
    const minSpacingScale = 0.3;
    while (page.scrollHeight > clientHeight && spacingScale > minSpacingScale) {{
        spacingScale -= 0.05;
        spacingData.forEach(data => {{
            if (data.el === page) {{
                // Keep some padding for safety boundary
                const newPT = Math.max(60, data.paddingTop * spacingScale);
                const newPB = Math.max(60, data.paddingBottom * spacingScale);
                data.el.style.paddingTop = newPT + 'px';
                data.el.style.paddingBottom = newPB + 'px';
            }} else {{
                if (data.paddingTop) data.el.style.paddingTop = (data.paddingTop * spacingScale) + 'px';
                if (data.paddingBottom) data.el.style.paddingBottom = (data.paddingBottom * spacingScale) + 'px';
                if (data.marginTop) data.el.style.marginTop = (data.marginTop * spacingScale) + 'px';
                if (data.marginBottom) data.el.style.marginBottom = (data.marginBottom * spacingScale) + 'px';
                if (data.gap) data.el.style.gap = (data.gap * spacingScale) + 'px';
            }}
        }});
    }}

    // 3. If still overflowing, shrink font sizes as a last resort
    if (page.scrollHeight > clientHeight) {{
        const elementsToScale = Array.from(page.querySelectorAll('*')).filter(el => {{
            if (el === page || el.classList.contains('system-page-label')) return false;
            const style = window.getComputedStyle(el);
            return parseFloat(style.fontSize) > 0;
        }});
        
        elementsToScale.forEach(el => {{
            const style = window.getComputedStyle(el);
            el.dataset.origFontSize = parseFloat(style.fontSize);
            const lh = style.lineHeight;
            if (lh.endsWith('px')) {{
                el.dataset.origLineHeight = parseFloat(lh);
            }}
        }});

        let fontScale = 1.0;
        const minFontScale = 0.5;
        while (page.scrollHeight > clientHeight && fontScale > minFontScale) {{
            fontScale -= 0.02;
            elementsToScale.forEach(el => {{
                el.style.fontSize = (parseFloat(el.dataset.origFontSize) * fontScale) + 'px';
                if (el.dataset.origLineHeight) {{
                    el.style.lineHeight = (parseFloat(el.dataset.origLineHeight) * fontScale) + 'px';
                }}
            }});
        }}
    }}
}})();
</script>
</body>
</html>
"""

    def _screenshot(self, html_path: Path, png_path: Path) -> None:
        abs_png_path = png_path.resolve()
        url = html_path.resolve().as_uri()
        cmd = [
            self._chrome_path,
            "--headless=new",
            "--no-sandbox",
            "--disable-gpu",
            "--disable-cache",
            "--hide-scrollbars",
            f"--window-size={W},{H}",
            f"--screenshot={abs_png_path.as_posix()}",
            url,
        ]
        subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    def _find_chrome(self) -> str:
        candidates = [
            shutil.which("google-chrome"),
            shutil.which("chromium"),
            shutil.which("chrome"),
            r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
            "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
            "/Applications/Chromium.app/Contents/MacOS/Chromium",
        ]
        for candidate in candidates:
            if candidate and Path(candidate).exists():
                return str(candidate)
        raise FileNotFoundError("未找到 Chrome/Chromium，无法进行 HTML 截图")
