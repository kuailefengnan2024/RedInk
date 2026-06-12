# 【功能描述】流水线：原文 → LLM 规划 JSON → 校验 → 出图
# 【输入】RawInput；CarouselPlanner；Linter；Renderer
# 【输出】PipelineResult

from __future__ import annotations

import json
from pathlib import Path

from md2xhs.domain.models import PipelineResult, RawInput
from md2xhs.domain.ports import CarouselPlanner, CopyLinter, SlideRenderer
from md2xhs.infra.carousel_json import carousel_to_dict


class Md2XhsPipeline:
    def __init__(
        self,
        planner: CarouselPlanner,
        linter: CopyLinter,
        renderer: SlideRenderer,
    ):
        self._planner = planner
        self._linter = linter
        self._renderer = renderer

    def run(
        self,
        raw: RawInput,
        output_dir: str | Path,
        *,
        save_intermediate: bool = True,
    ) -> PipelineResult:
        out = Path(output_dir)
        out.mkdir(parents=True, exist_ok=True)

        if save_intermediate:
            (out / "00_raw.txt").write_text(raw.text, encoding="utf-8")

        carousel = self._planner.plan(raw)
        if save_intermediate:
            (out / "01_carousel.json").write_text(
                json.dumps(carousel_to_dict(carousel), ensure_ascii=False, indent=2),
                encoding="utf-8",
            )

        issues = self._linter.lint(carousel)
        if save_intermediate:
            (out / "02_lint.txt").write_text("\n".join(issues) or "OK", encoding="utf-8")
        if issues:
            raise ValueError("文案校验未通过:\n" + "\n".join(f"- {x}" for x in issues))

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
