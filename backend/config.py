from pydantic_settings import BaseSettings
from typing import Optional
from functools import lru_cache

class Settings(BaseSettings):
    # Database
    DATABASE_URL: str = "sqlite:///./wattbox.db"
    
    # Storage
    UPLOAD_DIRECTORY: str = "./static/uploads"
    S3_BUCKET_NAME: Optional[str] = None
    AWS_ACCESS_KEY_ID: Optional[str] = None
    AWS_SECRET_ACCESS_KEY: Optional[str] = None
    AWS_REGION: Optional[str] = None
    
    # OCR
    TESSERACT_PATH: Optional[str] = None
    
    # Pricing
    PRICE_PER_KWH: float = 0.42
    
    # Security
    ALLOWED_DEVICE_IDS: str = "esp1,esp2,esp3"
    RATE_LIMIT_PER_MINUTE: int = 60
    
    # API
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    API_TITLE: str = "WattBox API"
    API_VERSION: str = "1.0.0"
    
    # CORS
    CORS_ORIGINS: str = "http://localhost:3000,http://localhost:5173"
    
    # Logging
    LOG_LEVEL: str = "INFO"
    
    class Config:
        env_file = ".env"
        case_sensitive = True

@lru_cache()
def get_settings() -> Settings:
    return Settings()