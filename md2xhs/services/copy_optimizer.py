# 【功能描述】LLM 文案优化器：非结构化输入 → 精炼发帖文稿
# 【输入】RawInput；TextLLM；optimize 提示词模板
# 【输出】优化后的 Markdown 文本

from __future__ import annotations

from pathlib import Path

from md2xhs.domain.models import RawInput
from md2xhs.domain.ports import TextLLM

_PROMPT = (Path(__file__).parent.parent / "prompts" / "optimize.txt").read_text(encoding="utf-8")


class LlmCopyOptimizer:
    def __init__(self, llm: TextLLM):
        self._llm = llm

    def optimize(self, raw: RawInput) -> str:
        prompt = _PROMPT.format(raw_text=raw.text.strip())
        return self._llm.complete(prompt).strip()
