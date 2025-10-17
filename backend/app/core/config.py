"""Application configuration via Pydantic Settings."""

from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )

    # API Settings
    PROJECT_NAME: str = "Elephantasm API"
    VERSION: str = "0.1.0"
    API_V1_STR: str = "/api/v1"

    # Database Settings
    DATABASE_URL: str = "postgresql+asyncpg://elephantasm:dev_password@localhost:5432/elephantasm"

    # CORS Settings
    BACKEND_CORS_ORIGINS: List[str] = [
        "http://localhost:3000",  # Next.js/React default
        "http://localhost:5173",  # Vite default
        "http://localhost:8080",  # Vue default
    ]

    # Security Settings (for future auth)
    SECRET_KEY: str = "your-secret-key-here-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30


# Global settings instance
settings = Settings()
