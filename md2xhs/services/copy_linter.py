# 【功能描述】规则校验器：禁词、页型、结构
# 【输入】Carousel；copy_rules
# 【输出】警告/错误消息列表

from __future__ import annotations

from md2xhs.domain.models import Carousel
from md2xhs.infra.rules_loader import load_copy_rules


class RuleCopyLinter:
    def lint(self, carousel: Carousel) -> list[str]:
        rules = load_copy_rules()
        issues: list[str] = []
        banned = rules.get("banned_phrases") or []

        blob = carousel.post_title + carousel.caption
        for slide in carousel.slides:
            blob += "".join(slide.title)
            for sub in slide.sub_items:
                blob += sub.text

        for phrase in banned:
            if phrase in blob:
                issues.append(f"禁词：「{phrase}」")

        if not carousel.slides:
            issues.append("无页面")
            return issues

        if carousel.slides[0].type != "cover":
            issues.append("首页应为 cover")
        if carousel.slides[-1].type != "cta":
            issues.append("末页应为 cta")

        return issues
