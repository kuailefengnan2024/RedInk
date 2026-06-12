"""
【功能描述】api-core 图片生成器：通过 D:/api-core SDK 调用生图模型
【输入】prompt、宽高比/尺寸等模型参数
【输出】图片二进制数据
"""
import base64
import logging
from typing import Any, Dict, Optional

from .base import ImageGeneratorBase
from backend.utils.apicore_bridge import build_image_kwargs, run_async
from backend.utils.image_compressor import compress_image

logger = logging.getLogger(__name__)


class ApiCoreImageGenerator(ImageGeneratorBase):
    """基于 api-core ImageClient 的图片生成器"""

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.provider_name = config.get("provider_name", "gemini_3_1_fi")
        self.image_kwargs = build_image_kwargs(config)

        from api_core.client import ImageClient
        self._client = ImageClient(provider=self.provider_name)
        logger.info(f"ApiCoreImageGenerator 初始化: provider={self.provider_name}")

    def validate_config(self) -> bool:
        if not self.provider_name:
            raise ValueError("api-core 图片 provider_name 未配置")
        return True

    def get_supported_sizes(self) -> list:
        return ["1024x1024", "1536x1024", "1024x1536", "1920x1920", "2048x2048", "1K", "2K", "4K"]

    def get_supported_aspect_ratios(self) -> list:
        return ["1:1", "2:3", "3:2", "3:4", "4:3", "4:5", "5:4", "9:16", "16:9", "21:9"]

    async def _generate_async(self, prompt: str, **kwargs) -> bytes:
        merged = {**self.image_kwargs, **kwargs}
        if kwargs.get("reference_image"):
            merged["reference_image"] = compress_image(kwargs["reference_image"], max_size_kb=200)
        image_bytes, error = await self._client.generate(prompt, **merged)
        if error:
            raise Exception(f"api-core 图片生成失败: {error}")
        if not image_bytes:
            raise Exception("api-core 返回空图片数据")
        return image_bytes

    def generate_image(self, prompt: str, **kwargs) -> bytes:
        call_kwargs = {}
        if kwargs.get("aspect_ratio"):
            call_kwargs["aspectRatio"] = kwargs["aspect_ratio"]
        if kwargs.get("image_size"):
            call_kwargs["imageSize"] = kwargs["image_size"]
        if kwargs.get("size"):
            call_kwargs["size"] = kwargs["size"]
        if kwargs.get("quality"):
            call_kwargs["quality"] = kwargs["quality"]
        if kwargs.get("reference_image"):
            call_kwargs["reference_image"] = kwargs["reference_image"]

        logger.info(
            f"api-core 生图: provider={self.provider_name}, "
            f"ref={bool(kwargs.get('reference_image'))}, kwargs={call_kwargs or self.image_kwargs}"
        )
        return run_async(self._generate_async(prompt, **call_kwargs))
