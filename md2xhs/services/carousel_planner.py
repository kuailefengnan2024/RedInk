# 【功能描述】LLM 轮播规划器：非结构化输入 → 直接输出 Carousel JSON
# 【输入】RawInput；TextLLM；plan 提示词
# 【输出】Carousel（LLM 自行决定分页与叙事）

from __future__ import annotations

import json
from pathlib import Path

from md2xhs.domain.models import Carousel, RawInput
from md2xhs.domain.ports import TextLLM
from md2xhs.infra.carousel_json import build_carousel, parse_json_object

_PROMPT = (Path(__file__).parent.parent / "prompts" / "plan.txt").read_text(encoding="utf-8")


class LlmCarouselPlanner:
    def __init__(self, llm: TextLLM, max_retries: int = 2):
        self._llm = llm
        self._max_retries = max_retries

    def plan(self, raw: RawInput) -> Carousel:
        prompt = _PROMPT.format(raw_text=raw.text.strip())
        extra = ""
        last_err: Exception | None = None
        for _ in range(self._max_retries + 1):
            try:
                out = self._llm.complete(prompt + extra)
                data = parse_json_object(out)
                return build_carousel(data)
            except (ValueError, json.JSONDecodeError, TimeoutError, RuntimeError) as e:
                last_err = e
                extra = f"\n\n【JSON 不合格】{e}\n请重新输出完整合法 JSON。"
        raise last_err or ValueError("规划失败")
