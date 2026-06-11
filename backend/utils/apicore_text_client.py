"""
【功能描述】api-core 文本客户端：通过 D:/api-core SDK 调用大语言模型
【输入】prompt、温度/token 参数、可选参考图
【输出】生成的文本字符串
"""
import base64
import logging
from typing import List, Optional, Union

from backend.utils.apicore_bridge import run_async

logger = logging.getLogger(__name__)


class ApiCoreTextClient:
    """基于 api-core LLMClient 的文本生成客户端"""

    def __init__(self, provider_config: dict):
        if not provider_config.get("provider_name"):
            raise ValueError(
                "api-core 未配置 provider_name。\n"
                "解决方案：在设置页选择 api-core 类型并指定模型（如 gemini_3_pro）"
            )

        self.provider_name = provider_config["provider_name"]
        self.temperature = provider_config.get("temperature", 1.0)
        self.max_output_tokens = provider_config.get("max_output_tokens", 8000)
        self.budget_tokens = provider_config.get("budget_tokens", 2000)
        self._config = provider_config

        from api_core.client import LLMClient
        self._client = LLMClient(provider=self.provider_name)

    def _build_messages(
        self,
        prompt: str,
        images: Optional[List[Union[bytes, str]]] = None,
        system_prompt: Optional[str] = None,
    ) -> list:
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})

        if images:
            content = [{"type": "text", "text": prompt}]
            for img in images:
                if isinstance(img, bytes):
                    from backend.utils.image_compressor import compress_image
                    compressed = compress_image(img, max_size_kb=200)
                    b64 = base64.b64encode(compressed).decode("utf-8")
                    content.append({
                        "type": "image_url",
                        "image_url": {"url": f"data:image/png;base64,{b64}"},
                    })
                else:
                    content.append({
                        "type": "image_url",
                        "image_url": {"url": img},
                    })
            messages.append({"role": "user", "content": content})
        else:
            messages.append({"role": "user", "content": prompt})

        return messages

    async def _chat_async(self, messages: list, **kwargs) -> str:
        text, error = await self._client.chat(messages, **kwargs)
        if error:
            raise Exception(f"api-core 文本生成失败: {error}")
        if not text:
            raise Exception("api-core 返回空文本")
        return text

    def generate_text(
        self,
        prompt: str,
        model: str = None,
        temperature: float = None,
        max_output_tokens: int = None,
        images: Optional[List[Union[bytes, str]]] = None,
        system_prompt: str = None,
        **kwargs,
    ) -> str:
        messages = self._build_messages(prompt, images, system_prompt)
        call_kwargs = {
            "temperature": temperature if temperature is not None else self.temperature,
            "max_tokens": max_output_tokens or self.max_output_tokens,
        }
        if self.budget_tokens and self.provider_name in {
            "gemini_2_5_pro", "gemini_3_pro", "gemini_3_1_p", "gemini_3_1_fi",
        }:
            call_kwargs["budget_tokens"] = self.budget_tokens

        call_kwargs.update(kwargs)
        logger.info(f"api-core 文本调用: provider={self.provider_name}")
        return run_async(self._chat_async(messages, **call_kwargs))
