from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Central app configuration, loaded from environment variables / .env."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Defaults to a local SQLite file for dev; override with a Postgres URL in prod,
    # e.g. postgresql+psycopg://user:pass@host:5432/laptops
    database_url: str = "sqlite:///./laptops.db"

    vllm_base_url: str | None = None
    vllm_api_key: str | None = None
    vllm_served_model_name: str = "qwen2.5-7b-instruct"

    # Used by Phase 5 (live_price_tool) to fetch prices/sellers/ratings via
    # SerpApi's Google Shopping engine. Never hardcode this key.
    serpapi_api_key: str | None = None


settings = Settings()
