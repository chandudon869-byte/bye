from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    # Database
    DATABASE_URL: str = "postgresql://postgres:postgres@postgres:5432/nepse_db"
    
    # Redis
    REDIS_URL: str = "redis://redis:6379/0"
    
    # API
    API_V1_PREFIX: str = "/api/v1"
    PROJECT_NAME: str = "NEPSE IPO Intelligence API"
    VERSION: str = "1.0.0"
    
    # Celery Schedule (in seconds)
    SCRAPE_INTERVAL_HOURS: int = 6
    SCRAPE_INTERVAL_SECONDS: int = 21600  # 6 hours
    
    # AI Scoring weights
    DEMAND_WEIGHT: float = 0.4
    FINANCIAL_WEIGHT: float = 0.3
    SECTOR_WEIGHT: float = 0.2
    RISK_WEIGHT: float = 0.1
    
    # Rate limiting
    RATE_LIMIT_PER_MINUTE: int = 60
    
    # CORS
    ALLOWED_ORIGINS: list = ["*"]
    
    class Config:
        env_file = ".env"

settings = Settings()