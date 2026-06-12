# 【功能描述】md2xhs 端口定义（依赖倒置）
# 【输入】无
# 【输出】TextLLM / CopyOptimizer / SlideSplitter / SlideRenderer 协议

from __future__ import annotations

from typing import Protocol

from .models import Carousel, RawInput, Slide


class TextLLM(Protocol):
    def complete(self, prompt: str, *, system: str | None = None) -> str: ...


class CarouselPlanner(Protocol):
    def plan(self, raw: RawInput) -> Carousel: ...


class CopyOptimizer(Protocol):
    def optimize(self, raw: RawInput) -> str: ...


class SlideSplitter(Protocol):
    def split(self, optimized_text: str) -> Carousel: ...


class CopyLinter(Protocol):
    def lint(self, carousel: Carousel) -> list[str]: ...


class SlideRenderer(Protocol):
    def render_all(self, slides: list[Slide], output_dir: str) -> list[str]: ...
