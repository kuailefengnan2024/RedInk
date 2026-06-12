# 【功能描述】LLM 切页器（legacy：对已优化文稿切页）
# 【输入】优化文本；TextLLM
# 【输出】Carousel

from __future__ import annotations

import json
from pathlib import Path

from md2xhs.domain.models import Carousel
from md2xhs.domain.ports import TextLLM
from md2xhs.infra.carousel_json import build_carousel, parse_json_object
from md2xhs.infra.rules_loader import load_copy_rules

_PROMPT = (Path(__file__).parent.parent / "prompts" / "split.txt").read_text(encoding="utf-8")


class LlmSlideSplitter:
    def __init__(self, llm: TextLLM, max_retries: int = 2):
        self._llm = llm
        self._rules = load_copy_rules()
        self._max_retries = max_retries

    def split(self, optimized_text: str) -> Carousel:
        pc = self._rules.get("page_count", {})
        prompt = _PROMPT.format(
            optimized_text=optimized_text.strip(),
            page_min=pc.get("min", 6),
            page_max=pc.get("max", 12),
        )
        extra = ""
        last_err: Exception | None = None
        for _ in range(self._max_retries + 1):
            try:
                out = self._llm.complete(prompt + extra)
                return build_carousel(parse_json_object(out))
            except (ValueError, json.JSONDecodeError) as e:
                last_err = e
                extra = f"\n\n【修正】{e}"
        raise last_err or ValueError("切页失败")
