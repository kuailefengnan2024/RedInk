# 【功能描述】md2xhs CLI
# 【输入】命令行；输入 MD；api-core 配置
# 【输出】轮播 PNG + carousel.json

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv

from md2xhs.domain.models import RawInput, Slide, SubItem
from md2xhs.infra.carousel_json import build_carousel, carousel_to_dict, parse_json_object
from md2xhs.infra.llm_factory import load_llm_from_yaml
from md2xhs.render.finance_dark_renderer import FinanceDarkRenderer
from md2xhs.render.html_code_renderer import LlmHtmlCodeRenderer
from md2xhs.services.carousel_planner import LlmCarouselPlanner
from md2xhs.services.copy_linter import RuleCopyLinter
from md2xhs.services.copy_optimizer import LlmCopyOptimizer
from md2xhs.services.copy_polisher import LlmCopyPolisher
from md2xhs.services.pipeline import Md2XhsPipeline
from md2xhs.services.slide_splitter import LlmSlideSplitter


def _pipeline(renderer_name: str = "pillow") -> Md2XhsPipeline:
    load_dotenv(ROOT / ".env")
    planner_llm = load_llm_from_yaml(role="plan")
    polish_llm = load_llm_from_yaml(role="polish")
    if renderer_name == "html":
        renderer = LlmHtmlCodeRenderer(
            load_llm_from_yaml(role="render"),
            llm_factory=lambda: load_llm_from_yaml(role="render"),
            max_workers=3,
        )
    else:
        renderer = FinanceDarkRenderer()
    return Md2XhsPipeline(
        planner=LlmCarouselPlanner(planner_llm),
        linter=RuleCopyLinter(),
        renderer=renderer,
        polisher=LlmCopyPolisher(polish_llm),
    )


def cmd_run(args: argparse.Namespace) -> int:
    raw_path = Path(args.input)
    result = _pipeline(args.renderer).run(
        RawInput(text=raw_path.read_text(encoding="utf-8"), source_path=str(raw_path)),
        args.output,
    )
    print(f"Done: {len(result.image_paths)} pages -> {result.output_dir}")
    for p in result.image_paths:
        print(f"  {p}")
    return 0


def cmd_plan(args: argparse.Namespace) -> int:
    load_dotenv(ROOT / ".env")
    raw_path = Path(args.input)
    carousel = LlmCarouselPlanner(load_llm_from_yaml(role="plan")).plan(
        RawInput(raw_path.read_text(encoding="utf-8"))
    )
    out = Path(args.output)
    out.write_text(json.dumps(carousel_to_dict(carousel), ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"plan: {len(carousel.slides)} pages -> {out}")
    return 0


def cmd_render(args: argparse.Namespace) -> int:
    data = json.loads(Path(args.input).read_text(encoding="utf-8"))
    is_design = "pages" in data and isinstance(data["pages"], list)
    load_dotenv(ROOT / ".env")
    if args.renderer == "html":
        renderer = LlmHtmlCodeRenderer(
            load_llm_from_yaml(role="render"),
            llm_factory=lambda: load_llm_from_yaml(role="render"),
            max_workers=3,
        )
        if is_design:
            print("Detecting render_design format. Rendering directly without LLM...")
            paths = renderer.render_design(data, args.output)
        else:
            carousel = build_carousel(data)
            paths = renderer.render_carousel(carousel, args.output)
    else:
        if is_design:
            print("Pillow renderer does not support render_design JSON directly.", file=sys.stderr)
            return 1
        carousel = build_carousel(data)
        paths = FinanceDarkRenderer().render_all(carousel.slides, args.output)
    print(f"rendered {len(paths)} -> {args.output}")
    return 0



def cmd_optimize(args: argparse.Namespace) -> int:
    load_dotenv(ROOT / ".env")
    text = LlmCopyOptimizer(load_llm_from_yaml()).optimize(
        RawInput(Path(args.input).read_text(encoding="utf-8"))
    )
    Path(args.output).write_text(text, encoding="utf-8")
    print(f"optimized -> {args.output}")
    return 0


def cmd_polish(args: argparse.Namespace) -> int:
    load_dotenv(ROOT / ".env")
    text = LlmCopyPolisher(load_llm_from_yaml(role="polish")).optimize(
        RawInput(Path(args.input).read_text(encoding="utf-8"))
    )
    Path(args.output).write_text(text, encoding="utf-8")
    print(f"polished -> {args.output}")
    return 0


def cmd_split(args: argparse.Namespace) -> int:
    load_dotenv(ROOT / ".env")
    carousel = LlmSlideSplitter(load_llm_from_yaml(role="plan")).split(
        Path(args.input).read_text(encoding="utf-8")
    )
    Path(args.output).write_text(
        json.dumps(carousel_to_dict(carousel), ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"split: {len(carousel.slides)} pages -> {args.output}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="md2xhs", description="草稿 MD → 小红书轮播图")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_run = sub.add_parser("run", help="默认：LLM 规划 JSON → 出图")
    p_run.add_argument("input")
    p_run.add_argument("-o", "--output", default="./output")
    p_run.add_argument("--renderer", choices=["pillow", "html"], default="pillow")
    p_run.set_defaults(func=cmd_run)

    p_plan = sub.add_parser("plan", help="仅 LLM 规划，输出 carousel.json")
    p_plan.add_argument("input")
    p_plan.add_argument("-o", "--output", default="./01_carousel.json")
    p_plan.set_defaults(func=cmd_plan)

    p_ren = sub.add_parser("render", help="从 carousel.json 出图")
    p_ren.add_argument("input")
    p_ren.add_argument("-o", "--output", default="./output")
    p_ren.add_argument("--renderer", choices=["pillow", "html"], default="pillow")
    p_ren.set_defaults(func=cmd_render)

    p_opt = sub.add_parser("optimize", help="[legacy] 仅优化文案")
    p_opt.add_argument("input")
    p_opt.add_argument("-o", "--output", default="./optimized.md")
    p_opt.set_defaults(func=cmd_optimize)

    p_polish = sub.add_parser("polish", help="按当前人设润色文案，输出中间 Markdown")
    p_polish.add_argument("input")
    p_polish.add_argument("-o", "--output", default="./polished.md")
    p_polish.set_defaults(func=cmd_polish)

    p_spl = sub.add_parser("split", help="[legacy] 对已优化文稿切页")
    p_spl.add_argument("input")
    p_spl.add_argument("-o", "--output", default="./carousel.json")
    p_spl.set_defaults(func=cmd_split)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
