from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(".env", "../../.env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    environment: str = "development"
    demo_mode: bool = True

    database_url: str = "postgresql+psycopg://naimos:naimos_dev_password@localhost:5433/naimos"
    database_url_readonly: str = (
        "postgresql+psycopg://naimos_readonly:naimos_readonly_password@localhost:5433/naimos"
    )

    jwt_secret: str = "change-me-to-a-long-random-string"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7

    openai_api_key: str = ""
    openai_base_url: str = "https://api.openai.com/v1"
    openai_model: str = "gpt-4o-mini"

    mapbox_token: str = ""

    storage_provider: str = "local"
    storage_bucket: str = "naimos-evidence"
    storage_local_path: str = "./storage"

    redis_url: str = "redis://localhost:6380/0"

    cors_origins: list[str] = ["http://localhost:3000"]

    @property
    def ai_enabled_real_provider(self) -> bool:
        """True once a real API key is configured; otherwise the mock provider is used."""
        return bool(self.openai_api_key)


@lru_cache
def get_settings() -> Settings:
    return Settings()
