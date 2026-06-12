# 【功能描述】加载 copy_rules.yaml
# 【输入】config 目录路径
# 【输出】规则 dict

from __future__ import annotations

from pathlib import Path

import yaml

_RULES_PATH = Path(__file__).parent.parent / "config" / "copy_rules.yaml"


def load_copy_rules() -> dict:
    with open(_RULES_PATH, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}
