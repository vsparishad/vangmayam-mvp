"""
Core configuration settings for Vāṇmayam
"""

from pydantic_settings import BaseSettings
from typing import List, Optional
import os


class Settings(BaseSettings):
    """Application settings"""
    
    # Application
    APP_NAME: str = "Vāṇmayam - The Vedic Corpus Portal"
    APP_VERSION: str = "1.0.0-mvp"
    DEBUG: bool = False
    ENVIRONMENT: str = "development"
    
    # Security
    SECRET_KEY: str = "your-secret-key-change-in-production"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    ALGORITHM: str = "HS256"
    
    # CORS
    ALLOWED_HOSTS: List[str] = ["localhost", "127.0.0.1", "0.0.0.0"]
    ALLOWED_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:8000",
    ]
    
    # Database
    DATABASE_URL: str = "postgresql+asyncpg://vangmayam:vangmayam_dev@localhost:5432/vangmayam"
    DATABASE_POOL_SIZE: int = 10
    DATABASE_MAX_OVERFLOW: int = 20
    
    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"
    REDIS_CACHE_TTL: int = 3600  # 1 hour
    
    # Elasticsearch
    ELASTICSEARCH_URL: str = "http://localhost:9200"
    ELASTICSEARCH_INDEX_PREFIX: str = "vangmayam"
    
    # MinIO/S3 Storage
    MINIO_ENDPOINT: str = "localhost:9000"
    MINIO_ACCESS_KEY: str = "vangmayam"
    MINIO_SECRET_KEY: str = "vangmayam_dev"
    MINIO_SECURE: bool = False
    MINIO_BUCKET_NAME: str = "vangmayam-storage"
    
    # File Upload
    MAX_FILE_SIZE: int = 100 * 1024 * 1024  # 100MB
    ALLOWED_FILE_TYPES: List[str] = [".pdf", ".png", ".jpg", ".jpeg", ".tiff"]
    UPLOAD_DIR: str = "uploads"
    
    # OCR Settings
    TESSERACT_CMD: Optional[str] = None  # Auto-detect
    TESSERACT_LANGUAGES: List[str] = ["san", "hin", "eng", "tam"]
    OCR_DPI: int = 400
    OCR_CONFIDENCE_THRESHOLD: float = 0.7
    
    # Google Vision API
    GOOGLE_CLOUD_PROJECT: Optional[str] = None
    GOOGLE_APPLICATION_CREDENTIALS: Optional[str] = None
    
    # Celery
    CELERY_BROKER_URL: str = "redis://localhost:6379/1"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/2"
    
    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "json"
    
    # Google OAuth
    GOOGLE_CLIENT_ID: Optional[str] = None
    GOOGLE_CLIENT_SECRET: Optional[str] = None
    GOOGLE_REDIRECT_URI: str = "http://localhost:8000/api/v1/auth/google/callback"
    
    # Pagination
    DEFAULT_PAGE_SIZE: int = 20
    MAX_PAGE_SIZE: int = 100
    
    # Search
    SEARCH_RESULTS_PER_PAGE: int = 10
    SEARCH_MAX_RESULTS: int = 1000
    
    # Export
    EXPORT_MAX_PAGES: int = 500
    EXPORT_TIMEOUT_SECONDS: int = 300
    
    class Config:
        env_file = ".env"
        case_sensitive = True


# Global settings instance
settings = Settings()


# Environment-specific configurations
class DevelopmentSettings(Settings):
    """Development environment settings"""
    DEBUG: bool = True
    LOG_LEVEL: str = "DEBUG"


class ProductionSettings(Settings):
    """Production environment settings"""
    DEBUG: bool = False
    LOG_LEVEL: str = "WARNING"
    
    # Override with secure defaults
    ALLOWED_HOSTS: List[str] = ["vangmayam.org", "api.vangmayam.org"]
    ALLOWED_ORIGINS: List[str] = ["https://vangmayam.org"]
    
    # Production database
    DATABASE_URL: str = "postgresql+asyncpg://user:password@prod-db:5432/vangmayam"
    
    # Production Redis
    REDIS_URL: str = "redis://prod-redis:6379/0"
    
    # Production Elasticsearch
    ELASTICSEARCH_URL: str = "https://prod-elasticsearch:9200"
    
    # Production MinIO
    MINIO_ENDPOINT: str = "prod-minio:9000"
    MINIO_SECURE: bool = True


def get_settings() -> Settings:
    """Get settings based on environment"""
    env = os.getenv("ENVIRONMENT", "development").lower()
    
    if env == "production":
        return ProductionSettings()
    elif env == "development":
        return DevelopmentSettings()
    else:
        return Settings()


# Export the appropriate settings
settings = get_settings()
