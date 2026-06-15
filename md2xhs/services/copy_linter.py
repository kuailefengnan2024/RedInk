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
        title_banned = rules.get("title_banned_phrases") or []
        sub_rules = rules.get("sub_item") or {}
        min_per_page = int(sub_rules.get("min_per_page", 0) or 0)
        min_sub_chars = int(sub_rules.get("min_chars", 0) or 0)
        max_sub_chars = int(sub_rules.get("max_chars", 0) or 0)
        evidence_markers = [str(x) for x in (rules.get("evidence_markers") or [])]

        blob = carousel.post_title + carousel.caption
        for slide in carousel.slides:
            title_text = "".join(slide.title)
            for phrase in title_banned:
                if str(phrase) in title_text:
                    issues.append(f"{slide.label or slide.type} 标题抽象词：「{phrase}」")
            blob += slide.type + slide.label + slide.icon + "".join(slide.title)
            blob += slide.highlight + slide.highlight_sub + slide.footnote
            if slide.type == "cover" and len(slide.sub_items) < 2:
                issues.append(f"{slide.label or slide.type} 小字少于 2 条")
            if slide.type in {"body", "hero"} and len(slide.sub_items) < min_per_page:
                issues.append(f"{slide.label or slide.type} 小字少于 {min_per_page} 条")
            if slide.type == "cta" and len(slide.sub_items) < 2:
                issues.append(f"{slide.label or slide.type} 小字少于 2 条")
            if slide.type == "flow":
                if not slide.sub_items:
                    issues.append(f"{slide.label or slide.type} 缺少流程总判断小字")
                if len(slide.steps) < 3:
                    issues.append(f"{slide.label or slide.type} steps 少于 3 步")
            if slide.type == "estimate" and not (slide.highlight_sub or slide.footnote or slide.sub_items):
                issues.append(f"{slide.label or slide.type} 缺少数字口径或现实对照")
            for sub in slide.sub_items:
                blob += sub.tag + sub.text
                if slide.type == "cta":
                    continue
                if min_sub_chars and len(sub.text) < min_sub_chars:
                    issues.append(f"小字过短：「{sub.text}」")
                if max_sub_chars and len(sub.text) > max_sub_chars:
                    issues.append(f"小字过长：「{sub.text}」")
                if evidence_markers and not any(x in sub.text for x in evidence_markers):
                    issues.append(f"小字缺少例子/论证：「{sub.text}」")
            blob += "".join(slide.steps)
            for phase, desc in slide.phases:
                blob += phase + desc

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
