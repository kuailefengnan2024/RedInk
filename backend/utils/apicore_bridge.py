"""
【功能描述】api-core 桥接层：同步封装异步 SDK、注册可用模型与参数元数据
【输入】provider 配置（provider_name、temperature、size 等）、业务 prompt/messages
【输出】文本/图片生成结果，或模型列表供前端设置页使用
"""
import asyncio
import logging
from typing import Any

logger = logging.getLogger(__name__)

# api-core 文本模型注册表（与 D:/api-core/api_core/factory.py 保持同步）
LLM_PROVIDERS: dict[str, dict[str, Any]] = {
    "doubao15thinkpro": {"label": "豆包 1.5 Thinking Pro", "params": ["temperature", "max_output_tokens"]},
    "doubao20pro": {"label": "豆包 Seed 2.0 Pro", "params": ["temperature", "max_output_tokens"]},
    "doubao18": {"label": "豆包 Seed 1.8", "params": ["temperature", "max_output_tokens"]},
    "gemini_2_5_pro": {"label": "Gemini 2.5 Pro", "params": ["temperature", "max_output_tokens", "budget_tokens"]},
    "gemini_3_pro": {"label": "Gemini 3 Pro", "params": ["temperature", "max_output_tokens", "budget_tokens"]},
    "gemini_3_1_p": {"label": "Gemini 3.1 P", "params": ["temperature", "max_output_tokens", "budget_tokens"]},
    "gemini_3_1_fi": {"label": "Gemini 3.1 FI (多模态)", "params": ["temperature", "max_output_tokens", "budget_tokens"]},
    "gpt_5_5": {"label": "GPT 5.5", "params": ["temperature", "max_output_tokens"]},
}

# api-core 图片模型注册表
IMAGE_PROVIDERS: dict[str, dict[str, Any]] = {
    "seedream_4_5": {
        "label": "Seedream 4.5 (即梦)",
        "params": ["size", "watermark"],
        "defaults": {"size": "2048x2048", "watermark": False},
    },
    "seedream_5": {
        "label": "Seedream 5.0 (即梦)",
        "params": ["size", "watermark"],
        "defaults": {"size": "1920x1920", "watermark": False},
    },
    "gpt_image_1": {
        "label": "GPT Image 1",
        "params": ["size", "quality"],
        "defaults": {"size": "1024x1024", "quality": "high"},
    },
    "gpt_image_2": {
        "label": "GPT Image 2",
        "params": ["size", "quality"],
        "defaults": {"size": "1024x1024", "quality": "high"},
    },
    "gemini_3_pro_image": {
        "label": "Gemini 3 Pro Image",
        "params": ["aspect_ratio", "image_size"],
        "defaults": {"aspect_ratio": "3:4", "image_size": "2K"},
    },
    "gemini_3_1_fi": {
        "label": "Gemini 3.1 FI Image",
        "params": ["aspect_ratio", "image_size"],
        "defaults": {"aspect_ratio": "3:4", "image_size": "2K"},
    },
}

GEMINI_IMAGE_PROVIDERS = {"gemini_3_pro_image", "gemini_3_1_fi"}
GPT_IMAGE_PROVIDERS = {"gpt_image_1", "gpt_image_2"}
SEEDREAM_PROVIDERS = {"seedream_4_5", "seedream_5"}


def is_apicore_available() -> bool:
    """检查 api-core 是否已安装"""
    try:
        import api_core  # noqa: F401
        return True
    except ImportError:
        return False


def get_model_catalog(category: str) -> dict:
    """返回指定类别的模型目录，供设置页下拉选择"""
    if category == "image":
        providers = IMAGE_PROVIDERS
    else:
        providers = LLM_PROVIDERS

    return {
        "available": is_apicore_available(),
        "providers": [
            {
                "name": name,
                "label": meta["label"],
                "params": meta["params"],
                "defaults": meta.get("defaults", {}),
            }
            for name, meta in providers.items()
        ],
    }


def run_async(coro):
    """在 Flask 同步上下文中运行 api-core 异步调用"""
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as pool:
                return pool.submit(asyncio.run, coro).result()
        return loop.run_until_complete(coro)
    except RuntimeError:
        return asyncio.run(coro)


def build_image_kwargs(config: dict) -> dict:
    """从 RedInk 配置构建 api-core 生图参数"""
    provider_name = config.get("provider_name", "gemini_3_1_fi")
    kwargs: dict[str, Any] = {}

    if provider_name in GEMINI_IMAGE_PROVIDERS:
        kwargs["aspectRatio"] = config.get("aspect_ratio", "3:4")
        kwargs["imageSize"] = config.get("image_size", "2K")
    elif provider_name in GPT_IMAGE_PROVIDERS:
        kwargs["size"] = config.get("size", "1024x1024")
        kwargs["quality"] = config.get("quality", "high")
    elif provider_name in SEEDREAM_PROVIDERS:
        kwargs["size"] = config.get("size", "2048x2048")
        kwargs["watermark"] = config.get("watermark", False)

    return kwargs
