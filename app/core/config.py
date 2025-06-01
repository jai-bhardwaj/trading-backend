"""
Production Configuration Management
Centralized settings with validation and environment variable support
"""

import os
from typing import Optional, List
from pydantic_settings import BaseSettings
from pydantic import Field, validator
from functools import lru_cache

class Settings(BaseSettings):
    """Application settings with validation"""
    
    # Application
    project_name: str = Field(default="Trading Engine", alias="PROJECT_NAME")
    environment: str = Field(default="production", alias="ENV")
    debug: bool = Field(default=False, alias="DEBUG")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    
    # Database
    database_url: str = Field(..., alias="DATABASE_URL")
    database_echo: bool = Field(default=False, alias="DATABASE_ECHO")
    database_pool_size: int = Field(default=20, alias="DATABASE_POOL_SIZE")
    database_max_overflow: int = Field(default=30, alias="DATABASE_MAX_OVERFLOW")
    
    # Redis
    redis_url: str = Field(default="redis://localhost:6379/0", alias="REDIS_URL")
    redis_host: str = Field(default="localhost", alias="REDIS_HOST")
    redis_port: int = Field(default=6379, alias="REDIS_PORT")
    redis_db: int = Field(default=0, alias="REDIS_DB")
    redis_password: Optional[str] = Field(default=None, alias="REDIS_PASSWORD")
    
    # Security
    secret_key: str = Field(..., alias="SECRET_KEY")
    algorithm: str = Field(default="HS256", alias="ALGORITHM")
    access_token_expire_minutes: int = Field(default=1440, alias="ACCESS_TOKEN_EXPIRE_MINUTES")
    
    # Trading Engine
    engine_loop_interval: float = Field(default=1.0, alias="ENGINE_LOOP_INTERVAL")
    max_concurrent_orders: int = Field(default=100, alias="MAX_CONCURRENT_ORDERS")
    worker_count: int = Field(default=4, alias="WORKER_COUNT")
    max_queue_size: int = Field(default=10000, alias="MAX_QUEUE_SIZE")
    
    # Risk Management
    max_daily_loss_pct: float = Field(default=5.0, alias="MAX_DAILY_LOSS_PCT")
    max_position_size_pct: float = Field(default=10.0, alias="MAX_POSITION_SIZE_PCT")
    
    # Broker Configuration
    angelone_api_key: Optional[str] = Field(default=None, alias="ANGELONE_API_KEY")
    angelone_client_id: Optional[str] = Field(default=None, alias="ANGELONE_CLIENT_ID")
    angelone_password: Optional[str] = Field(default=None, alias="ANGELONE_PASSWORD")
    angelone_totp_secret: Optional[str] = Field(default=None, alias="ANGELONE_TOTP_SECRET")
    
    # Monitoring
    metrics_enabled: bool = Field(default=True, alias="METRICS_ENABLED")
    health_check_interval: int = Field(default=60, alias="HEALTH_CHECK_INTERVAL")
    
    @validator("database_url")
    def validate_database_url(cls, v):
        if not v or not v.startswith("postgresql"):
            raise ValueError("DATABASE_URL must be a valid PostgreSQL connection string")
        return v
    
    @validator("secret_key")
    def validate_secret_key(cls, v):
        if not v or len(v) < 32:
            raise ValueError("SECRET_KEY must be at least 32 characters long")
        return v
    
    @validator("log_level")
    def validate_log_level(cls, v):
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if v.upper() not in valid_levels:
            raise ValueError(f"LOG_LEVEL must be one of {valid_levels}")
        return v.upper()
    
    @validator("worker_count")
    def validate_worker_count(cls, v):
        if v < 1 or v > 20:
            raise ValueError("WORKER_COUNT must be between 1 and 20")
        return v
    
    @validator("max_daily_loss_pct")
    def validate_max_daily_loss_pct(cls, v):
        if v < 0 or v > 50:
            raise ValueError("MAX_DAILY_LOSS_PCT must be between 0 and 50")
        return v
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False

@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()

# Global settings instance
settings = get_settings()
