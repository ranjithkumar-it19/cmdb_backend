import os
from pathlib import Path
from typing import List, Optional
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=Path(__file__).resolve().parents[2] / ".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    APP_NAME: str = "Atlas Discovery & CMDB"
    API_V1_STR: str = "/api/v1"

    # Security
    SECRET_KEY: str = "atlas_discovery_super_secret_jwt_key_2026_production_grade_32chars"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 120
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # Host & Ports
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # CORS
    BACKEND_CORS_ORIGINS: List[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
    ]

    # Database
    DATABASE_URL: str = "sqlite:///./atlas_discovery.db"
    POSTGRES_SERVER: Optional[str] = "localhost"
    POSTGRES_PORT: Optional[int] = 5432
    POSTGRES_USER: Optional[str] = "postgres"
    POSTGRES_PASSWORD: Optional[str] = "postgres"
    POSTGRES_DB: Optional[str] = "atlas_discovery"

    # Broker & Cache
    USE_CELERY: bool = False
    CELERY_BROKER_URL: str = "amqp://guest:guest@localhost:5672//"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/0"

    # Discovery defaults
    DISCOVERY_DEFAULT_TIMEOUT_SECONDS: int = 30
    DISCOVERY_MAX_PARALLEL_TARGETS: int = 10
    DISCOVERY_ALLOW_LOCAL_TESTING: bool = True

    # Initial Admin Seed
    INITIAL_ADMIN_EMAIL: str = "admin@atlas.local"
    INITIAL_ADMIN_PASSWORD: str = "AdminSecurePassword123!"
    INITIAL_ADMIN_NAME: str = "System Administrator"


settings = Settings()
