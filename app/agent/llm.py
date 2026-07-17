import os

from langchain_openai import ChatOpenAI
from app.core.config import settings


def get_llm(*, streaming: bool = True):
    """Return a provider-neutral OpenAI-compatible chat model.

    The standardized planning module can run with ``LLM_PROVIDER=none`` by using
    its deterministic requirement parser. Existing generative chat paths must
    configure a provider explicitly.
    """
    provider = settings.LLM_PROVIDER.strip().lower()
    if provider in {"", "none", "disabled"}:
        raise RuntimeError("LLM is not configured; set LLM_PROVIDER and MODEL_NAME")
    if not settings.MODEL_NAME:
        raise RuntimeError("MODEL_NAME is required when LLM_PROVIDER is enabled")

    api_key = ""
    if settings.LLM_API_KEY_ENV:
        api_key = os.getenv(settings.LLM_API_KEY_ENV, "")
    if not api_key and provider in {"qwen", "dashscope", "qwen_openai_compatible"}:
        api_key = settings.DASHSCOPE_API_KEY
    if not api_key:
        raise RuntimeError("Configured LLM API key environment variable is empty")

    kwargs = {
        "api_key": api_key,
        "model": settings.MODEL_NAME,
        "streaming": streaming,
    }
    if settings.LLM_BASE_URL:
        kwargs["base_url"] = settings.LLM_BASE_URL
    if settings.ENABLE_REASONING and provider in {
        "qwen",
        "dashscope",
        "qwen_openai_compatible",
    }:
        kwargs["model_kwargs"] = {"extra_body": {"enable_thinking": True}}
    return ChatOpenAI(**kwargs)
