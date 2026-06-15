# 【功能描述】md2xhs 领域模型：原始输入、轮播页、发布包
# 【输入】无（纯数据结构）
# 【输出】类型安全的 Slide / Carousel / PipelineResult

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class SubItem:
    tag: str
    text: str


@dataclass
class Slide:
    type: str
    label: str
    icon: str
    title: list[str]
    layout: dict[str, str] = field(default_factory=dict)
    sub_items: list[SubItem] = field(default_factory=list)
    steps: list[str] = field(default_factory=list)
    highlight: str = ""
    highlight_sub: str = ""
    footnote: str = ""
    phases: list[tuple[str, str]] = field(default_factory=list)


@dataclass(frozen=True)
class Carousel:
    post_title: str
    tags: list[str]
    slides: list[Slide]
    caption: str = ""


@dataclass(frozen=True)
class RawInput:
    text: str
    source_path: str = ""


@dataclass
class PipelineResult:
    carousel: Carousel
    optimized_text: str
    output_dir: str
    image_paths: list[str] = field(default_factory=list)
