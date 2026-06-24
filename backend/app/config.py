# backend/app/config.py
from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field

class Settings(BaseSettings):
    APP_NAME: str = "OverLook - Public Signal Intelligence"
    APP_VERSION: str = "1.0.0"
    API_V1_PREFIX: str = "/api/v1"
    
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    DEBUG: bool = False
    ENVIRONMENT: str = "development"
    
    # Database
    DATABASE_URL: str = Field(
        default="sqlite+aiosqlite:///./overlook.db",
        description="Async database connection string (PostgreSQL+asyncpg or SQLite+aiosqlite fallback)"
    )
    
    # CORS
    CORS_ORIGINS: List[str] = [
        "http://localhost:5173",
        "http://localhost:3000",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:3000"
    ]
    
    # Provider Settings
    PROVIDER_TIMEOUT_SECONDS: float = 10.0
    PROVIDER_CACHE_TTL_SECONDS: int = 120
    DEFAULT_SYNC_INTERVAL_SECONDS: int = 300
    ENABLE_BACKGROUND_SYNC: bool = True
    
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
        extra="ignore"
    )

settings = Settings()

