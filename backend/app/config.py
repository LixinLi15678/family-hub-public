"""
Application configuration management
"""
from functools import lru_cache
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings"""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )
    
    # Application
    APP_NAME: str = "Family Hub"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    
    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    
    # Database
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/family_hub"
    DATABASE_ECHO: bool = False
    
    # JWT Authentication
    JWT_SECRET_KEY: str = "your-super-secret-key-change-in-production"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    
    # CORS
    CORS_ORIGINS: list[str] = ["http://localhost:3000", "http://localhost:5173"]
    
    # External APIs
    EXCHANGE_RATE_API_URL: str = "https://api.exchangerate.host/latest?base={base}"
    EXCHANGE_RATE_HISTORICAL_API_URL: str = "https://api.exchangerate.host/{date}?base={base}"
    
    # Points system
    POINTS_EXPIRY_DAYS: int = 90

    # Uploads (served under /uploads)
    UPLOAD_DIR: str = "/data/uploads"
    UPLOAD_PUBLIC_BASE_URL: str = "/uploads"
    UPLOAD_MAX_BYTES: int = 10 * 1024 * 1024  # 10MB


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()


settings = get_settings()
