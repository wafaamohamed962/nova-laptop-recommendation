from app.config import Settings


def test_settings_defaults_to_local_sqlite():
    settings = Settings(_env_file=None)
    assert settings.database_url == "sqlite:///./laptops.db"
    assert settings.vllm_base_url is None
    assert settings.vllm_served_model_name == "qwen2.5-7b-instruct"


def test_settings_reads_env_vars(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "sqlite:///./other.db")
    monkeypatch.setenv("VLLM_BASE_URL", "https://example.modal.run/v1")
    monkeypatch.setenv("VLLM_API_KEY", "secret-key")

    settings = Settings(_env_file=None)

    assert settings.database_url == "sqlite:///./other.db"
    assert settings.vllm_base_url == "https://example.modal.run/v1"
    assert settings.vllm_api_key == "secret-key"
