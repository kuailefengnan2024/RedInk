# 【功能描述】Carousel JSON 解析与构建（Planner / Splitter 共用）
# 【输入】LLM 输出的 JSON 文本
# 【输出】Carousel 领域对象

from __future__ import annotations

import json
import re

from md2xhs.domain.models import Carousel, Slide, SubItem


def parse_json_object(text: str) -> dict:
    text = text.strip()
    fence = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
    if fence:
        text = fence.group(1).strip()
    start, end = text.find("{"), text.rfind("}")
    if start < 0 or end <= start:
        raise ValueError("未找到合法 JSON 对象")
    return json.loads(text[start : end + 1])


def _as_str_list(items) -> list[str]:
    out: list[str] = []
    for x in items or []:
        if isinstance(x, str):
            out.append(x)
        elif isinstance(x, dict):
            out.append(x.get("text") or x.get("desc") or str(x))
        else:
            out.append(str(x))
    return out


def build_carousel(data: dict) -> Carousel:
    slides: list[Slide] = []
    for item in data.get("slides") or []:
        sub = []
        for s in item.get("sub_items") or []:
            if isinstance(s, dict):
                sub.append(SubItem(tag=s.get("tag", "·"), text=s.get("text", "")))
            elif isinstance(s, str):
                sub.append(SubItem(tag="·", text=s))
        phases = []
        for p in item.get("phases") or []:
            if isinstance(p, dict):
                phases.append((p.get("phase", ""), p.get("desc", "")))
            elif isinstance(p, (list, tuple)) and len(p) >= 2:
                phases.append((str(p[0]), str(p[1])))
        slides.append(
            Slide(
                type=item.get("type", "body"),
                label=item.get("label", ""),
                icon=item.get("icon", "·"),
                title=[str(t) for t in (item.get("title") or [""])],
                sub_items=sub,
                steps=_as_str_list(item.get("steps")),
                phases=phases,
                highlight=str(item.get("highlight") or ""),
                highlight_sub=str(item.get("highlight_sub") or ""),
                footnote=str(item.get("footnote") or ""),
            )
        )
    if not slides:
        raise ValueError("slides 为空")
    return Carousel(
        post_title=data.get("post_title") or "",
        tags=list(data.get("tags") or []),
        slides=slides,
        caption=data.get("caption") or "",
    )


def carousel_to_dict(carousel: Carousel) -> dict:
    return {
        "post_title": carousel.post_title,
        "tags": carousel.tags,
        "caption": carousel.caption,
        "slides": [
            {
                "type": s.type,
                "label": s.label,
                "icon": s.icon,
                "title": s.title,
                "sub_items": [{"tag": x.tag, "text": x.text} for x in s.sub_items],
                "steps": s.steps,
                "phases": [{"phase": p, "desc": d} for p, d in s.phases],
                "highlight": s.highlight,
                "highlight_sub": s.highlight_sub,
                "footnote": s.footnote,
            }
            for s in carousel.slides
        ],
    }
