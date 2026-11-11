# backend/app/config.py
from typing import Annotated, List, Literal

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Settings(BaseSettings):
    APP_NAME: str = "OverLook - Public Signal Intelligence"
    APP_VERSION: str = "1.1.0"
    API_V1_PREFIX: str = "/api/v1"

    HOST: str = "0.0.0.0"
    PORT: int = 8000
    DEBUG: bool = False
    ENVIRONMENT: Literal["development", "test", "staging", "production"] = "development"

    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: Literal["json", "console"] = "console"

    # Database. A postgresql+asyncpg URL selects the PostGIS store; anything else
    # (or an empty value) selects the in-process memory store.
    DATABASE_URL: str = Field(
        default="memory://",
        description="postgresql+asyncpg://... for PostGIS, or memory:// for the in-process store",
    )
    DB_POOL_SIZE: int = 10
    DB_MAX_OVERFLOW: int = 10

    # CORS — comma-separated in env files, e.g. CORS_ORIGINS=http://a,http://b
    CORS_ORIGINS: Annotated[List[str], NoDecode] = [
        "http://localhost:5173",
        "http://localhost:3000",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:3000",
    ]

    # Ingestion
    PROVIDER_TIMEOUT_SECONDS: float = 10.0
    PROVIDER_CACHE_TTL_SECONDS: int = 120
    DEFAULT_SYNC_INTERVAL_SECONDS: int = 300
    # Run the scheduler inside the API process. Fine for a single instance;
    # multi-replica deployments run `python -m backend.app.worker` instead.
    ENABLE_BACKGROUND_SYNC: bool = True
    SEED_FIXTURES: bool = True
    SIGNAL_RETENTION_HOURS: int = 72
    CIRCUIT_FAILURE_THRESHOLD: int = 3
    CIRCUIT_RESET_SECONDS: float = 300.0
    MAX_BACKOFF_SECONDS: float = 1800.0
    MANUAL_SYNC_COOLDOWN_SECONDS: float = 60.0
    WORKER_METRICS_PORT: int = 9100
    MAX_SSE_CLIENTS: int = 500

    # API protection
    RATE_LIMIT_ENABLED: bool = True
    RATE_LIMIT_PER_MINUTE: int = 600
    RATE_LIMIT_BURST: int = 100
    TRUSTED_PROXY_COUNT: int = 1

    # Query Bounds
    MAX_QUERY_RESULTS: int = 1000
    DEFAULT_QUERY_RESULTS: int = 250
    MAX_BBOX_DIAGONAL_KM: float = 20000.0

    # Credentials (Optional)
    OPENSKY_USERNAME: str = ""
    OPENSKY_PASSWORD: str = ""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def split_origins(cls, v):
        if isinstance(v, str):
            return [o.strip() for o in v.split(",") if o.strip()]
        return v

    @model_validator(mode="after")
    def reject_unsafe_production_config(self):
        if self.ENVIRONMENT == "production":
            if "*" in self.CORS_ORIGINS:
                raise ValueError("CORS_ORIGINS must not contain '*' in production")
            if self.DEBUG:
                raise ValueError("DEBUG must be false in production")
        return self

    @property
    def uses_postgis(self) -> bool:
        return self.DATABASE_URL.startswith("postgresql")


settings = Settings()
