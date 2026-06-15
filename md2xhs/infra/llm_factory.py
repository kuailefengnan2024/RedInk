# 【功能描述】api-core 文本 LLM 适配器
# 【输入】text_providers.yaml 中的 provider 配置
# 【输出】实现 TextLLM.complete

from __future__ import annotations

import signal
import sys
import threading
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.utils.text_client import get_text_chat_client  # noqa: E402


class ApiCoreLLM:
    def __init__(self, provider_config: dict):
        self._client = get_text_chat_client(provider_config)
        self._timeout_sec = int(provider_config.get("request_timeout_sec", 0) or 0)

    def complete(self, prompt: str, *, system: str | None = None) -> str:
        if not self._timeout_sec or threading.current_thread() is not threading.main_thread():
            return self._client.generate_text(
                prompt=prompt,
                system_prompt=system,
            )

        def _timeout_handler(signum, frame):
            raise TimeoutError(f"LLM 调用超过 {self._timeout_sec}s")

        previous = signal.signal(signal.SIGALRM, _timeout_handler)
        signal.setitimer(signal.ITIMER_REAL, self._timeout_sec)
        try:
            return self._client.generate_text(
                prompt=prompt,
                system_prompt=system,
            )
        finally:
            signal.setitimer(signal.ITIMER_REAL, 0)
            signal.signal(signal.SIGALRM, previous)


def load_llm_from_yaml(*, provider_key: str | None = None, role: str | None = None) -> ApiCoreLLM:
    import yaml
    from dotenv import load_dotenv

    load_dotenv(ROOT / ".env")
    path = ROOT / "text_providers.yaml"
    if not path.exists():
        raise FileNotFoundError(f"缺少 text_providers.yaml: {path}")
    cfg = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    role_provider = None
    if role:
        role_provider = (cfg.get("md2xhs") or {}).get(f"{role}_provider")
    active = provider_key or role_provider or cfg.get("active_provider")
    providers = cfg.get("providers") or {}
    if active not in providers:
        raise ValueError(f"active_provider [{active}] 未在 text_providers.yaml 中定义")
    return ApiCoreLLM(providers[active])
