from functools import lru_cache

from langchain_openai import ChatOpenAI

from app.config import settings


@lru_cache
def get_chat_llm(temperature: float = 0.0) -> ChatOpenAI:
    """
    Chat model client pointed at the self-hosted Modal vLLM OpenAI-compatible
    endpoint (see deploy_modal.py). Requires VLLM_BASE_URL / VLLM_API_KEY to be
    set in the environment (see .env.example).
    """
    if not settings.vllm_base_url or not settings.vllm_api_key:
        raise RuntimeError(
            "VLLM_BASE_URL and VLLM_API_KEY must be set (see backend/.env.example) "
            "before the Evaluator Agent can call the LLM."
        )
    return ChatOpenAI(
        base_url=settings.vllm_base_url,
        api_key=settings.vllm_api_key,
        model=settings.vllm_served_model_name,
        temperature=temperature,
    )
