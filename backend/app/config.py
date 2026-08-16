from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Central app configuration, loaded from environment variables / .env."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Defaults to a local SQLite file for dev; override with a Postgres URL in prod,
    # e.g. postgresql+psycopg://user:pass@host:5432/laptops
    database_url: str = "sqlite:///./laptops.db"

    vllm_base_url: str | None = None
    vllm_api_key: str | None = None
    vllm_served_model_name: str = "qwen3-4b-instruct"

    # Used by Phase 5 (live_price_tool) to fetch prices/sellers/ratings via
    # SerpApi's Google Shopping engine. Never hardcode this key.
    serpapi_api_key: str | None = None

    # Phase 6: comma-separated list of origins allowed to call the API
    # (the Vite dev server by default; add your deployed frontend's origin
    # in production via CORS_ALLOW_ORIGINS).
    cors_allow_origins: str = "http://localhost:5173"

    @property
    def cors_allow_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_allow_origins.split(",") if origin.strip()]


settings = Settings()
