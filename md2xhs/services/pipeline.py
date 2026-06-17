# 【功能描述】流水线：原文 → LLM 规划 JSON → 校验 → 出图
# 【输入】RawInput；CarouselPlanner；Linter；Renderer
# 【输出】PipelineResult

from __future__ import annotations

import json
from pathlib import Path

from md2xhs.domain.models import Carousel, PipelineResult, RawInput, Slide, SubItem
from md2xhs.domain.ports import CarouselPlanner, CopyLinter, CopyOptimizer, SlideRenderer
from md2xhs.infra.carousel_json import carousel_to_dict
from md2xhs.infra.rules_loader import load_copy_rules


class Md2XhsPipeline:
    def __init__(
        self,
        planner: CarouselPlanner,
        linter: CopyLinter,
        renderer: SlideRenderer,
        polisher: CopyOptimizer | None = None,
    ):
        self._planner = planner
        self._linter = linter
        self._renderer = renderer
        self._polisher = polisher

    def run(
        self,
        raw: RawInput,
        output_dir: str | Path,
        *,
        save_intermediate: bool = True,
        lint_retries: int = 4,
    ) -> PipelineResult:
        out = Path(output_dir)
        out.mkdir(parents=True, exist_ok=True)

        if save_intermediate:
            (out / "00_raw.txt").write_text(raw.text, encoding="utf-8")

        planner_input = raw
        if self._polisher:
            polished = self._polisher.optimize(raw)
            planner_input = RawInput(text=polished, source_path=raw.source_path)
            if save_intermediate:
                (out / "01_polished.md").write_text(polished, encoding="utf-8")

        carousel = self._apply_replacements(self._planner.plan(planner_input))
        issues = self._linter.lint(carousel)
        for _ in range(lint_retries):
            if not issues:
                break
            feedback = "\n".join(f"- {x}" for x in issues)
            planner_input = RawInput(
                text=(
                    planner_input.text
                    + "\n\n【上一版 carousel 未通过文案校验】\n"
                    + feedback
                    + "\n请逐条修复后重写完整 JSON：小字少于要求的页面必须补足；禁词必须删除；不要解释，不要保留这些词，也不要换成同类说教口吻或平台套话。\n"
                    + "【重要提示 1 - 关于小字缺少例子/论证】：必须确保该条小字里包含以下词汇中的至少一个以提供写实论据（如：年、公司、岗位、数据、钱、你、我、先、后、但、却）。\n"
                    + "【重要提示 2 - 关于小字过短】：小红书排版小字单条必须不少于 30 个汉字（一般为 30~80 字），请补充具体描述/细节将字数凑足到 30 字以上（不能缩字号糊弄）。\n"
                    + "【重要提示 3 - 关于标题抽象词】：大标题严禁包含抽象概念词，如：超额利润、利润表、公共账本、数据红利、统计口径、账本的背面、弹窗与账户 等。请替换成更生动大白话的字词。"
                ),
                source_path=planner_input.source_path,
            )
            carousel = self._apply_replacements(self._planner.plan(planner_input))
            issues = self._linter.lint(carousel)

        if save_intermediate:
            (out / "02_carousel.json").write_text(
                json.dumps(carousel_to_dict(carousel), ensure_ascii=False, indent=2),
                encoding="utf-8",
            )

        if save_intermediate:
            (out / "03_lint.txt").write_text("\n".join(issues) or "OK", encoding="utf-8")
        if issues:
            raise ValueError("文案校验未通过:\n" + "\n".join(f"- {x}" for x in issues))

        render_carousel = getattr(self._renderer, "render_carousel", None)
        if callable(render_carousel):
            images = render_carousel(carousel, str(out))
        else:
            images = self._renderer.render_all(carousel.slides, str(out))
        (out / "caption.txt").write_text(
            f"{carousel.post_title}\n\n{carousel.caption}\n\n"
            + " ".join(f"#{t}" for t in carousel.tags),
            encoding="utf-8",
        )

        return PipelineResult(
            carousel=carousel,
            optimized_text=carousel.caption,
            output_dir=str(out),
            image_paths=images,
        )

    def _apply_replacements(self, carousel: Carousel) -> Carousel:
        replacements = (load_copy_rules().get("replace") or {})
        if not replacements:
            return carousel

        def clean(value: str) -> str:
            out = value
            for src, dst in replacements.items():
                out = out.replace(str(src), str(dst))
            return out

        slides = []
        for slide in carousel.slides:
            slides.append(
                Slide(
                    type=clean(slide.type),
                    label=clean(slide.label),
                    icon=clean(slide.icon),
                    title=[clean(x) for x in slide.title],
                    layout=dict(slide.layout),
                    sub_items=[SubItem(tag=clean(x.tag), text=clean(x.text)) for x in slide.sub_items],
                    steps=[clean(x) for x in slide.steps],
                    highlight=clean(slide.highlight),
                    highlight_sub=clean(slide.highlight_sub),
                    footnote=clean(slide.footnote),
                    phases=[(clean(phase), clean(desc)) for phase, desc in slide.phases],
                )
            )
        return Carousel(
            post_title=clean(carousel.post_title),
            tags=[clean(x) for x in carousel.tags],
            slides=slides,
            caption=clean(carousel.caption),
        )
