import pytest

from app import llm as llm_module


@pytest.fixture(autouse=True)
def _clear_llm_cache():
    llm_module.get_chat_llm.cache_clear()
    yield
    llm_module.get_chat_llm.cache_clear()


def test_get_chat_llm_raises_without_base_url(monkeypatch):
    monkeypatch.setattr(llm_module.settings, "vllm_base_url", None)
    monkeypatch.setattr(llm_module.settings, "vllm_api_key", "some-key")

    with pytest.raises(RuntimeError, match="VLLM_BASE_URL"):
        llm_module.get_chat_llm()


def test_get_chat_llm_raises_without_api_key(monkeypatch):
    monkeypatch.setattr(llm_module.settings, "vllm_base_url", "https://example.modal.run/v1")
    monkeypatch.setattr(llm_module.settings, "vllm_api_key", None)

    with pytest.raises(RuntimeError, match="VLLM_BASE_URL"):
        llm_module.get_chat_llm()


def test_get_chat_llm_builds_client_when_configured(monkeypatch):
    monkeypatch.setattr(llm_module.settings, "vllm_base_url", "https://example.modal.run/v1")
    monkeypatch.setattr(llm_module.settings, "vllm_api_key", "some-key")
    monkeypatch.setattr(llm_module.settings, "vllm_served_model_name", "qwen2.5-7b-instruct")

    client = llm_module.get_chat_llm()

    assert client.model_name == "qwen2.5-7b-instruct"
