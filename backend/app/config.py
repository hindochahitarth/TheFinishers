"""
GreenPulse AI — Application Configuration
Reads all settings from environment variables / .env file.
"""

from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", case_sensitive=False, extra="ignore"
    )

    # ── Application ─────────────────────────────────────────
    app_name: str = "GreenPulse AI"
    app_version: str = "1.0.0"
    environment: str = "development"
    log_level: str = "INFO"

    # ── Database ────────────────────────────────────────────
    database_url: str

    @property
    def async_database_url(self) -> str:
        """Sanitize database URL for Render and ensure asyncpg is used."""
        url = self.database_url
        if url.startswith("postgres://"):
            url = url.replace("postgres://", "postgresql+asyncpg://", 1)
        elif url.startswith("postgresql://") and "+asyncpg" not in url:
            url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
        return url

    # ── Redis ───────────────────────────────────────────────
    redis_url: str = "redis://localhost:6379/0"
    cache_ttl_seconds: int = 300  # 5 minutes default

    # ── Security / JWT ──────────────────────────────────────
    secret_key: str = "change-me-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60

    # ── External APIs ───────────────────────────────────────
    openweather_api_key: str = ""
    openaq_api_key: str = ""
    tomtom_api_key: str = ""

    # ── LLM ─────────────────────────────────────────────────
    llm_provider: str = "openai"   # openai | google | anthropic
    llm_api_key: str = ""
    llm_model: str = "gpt-4o"

    # ── Monitoring Location ─────────────────────────────────
    default_city: str = "New Delhi"
    default_lat: float = 28.6139
    default_lon: float = 77.2090
    default_country_code: str = "IN"

    # ── Data Pipeline ───────────────────────────────────────
    ingestion_interval_minutes: int = 10
    data_retention_days: int = 365

    # ── Alert Thresholds (WHO 2021) ─────────────────────────
    who_pm25_24h: float = 15.0    # µg/m³
    who_pm10_24h: float = 45.0
    who_no2_24h: float = 25.0
    who_o3_8h: float = 100.0

    # ── CPCB Thresholds (India NAAQS) ──────────────────────
    cpcb_pm25_24h: float = 60.0
    cpcb_pm10_24h: float = 100.0
    cpcb_no2_24h: float = 80.0
    cpcb_o3_8h: float = 180.0
    cpcb_co_8h: float = 4.0       # mg/m³
    cpcb_so2_24h: float = 80.0

    # ── Model Paths ─────────────────────────────────────────
    registry_artifacts_dir: str = "/app/ml_models/artifacts"


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
