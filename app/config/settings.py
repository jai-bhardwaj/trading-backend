"""
Settings and configuration for the trading engine
"""

from typing import Optional
from pydantic_settings import BaseSettings
from pydantic import Field
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class Settings(BaseSettings):
    """Application settings"""
    # Project
    project_name: str = Field("Trading Backend", env="PROJECT_NAME")
    api_v1_str: str = Field("/api/v1", env="API_V1_STR")
    env: str = Field("production", env="ENV")
    debug: bool = Field(False, env="DEBUG")

    # Database
    database_url: str = Field(..., env="DATABASE_URL")

    # Redis
    redis_url: str = Field("redis://localhost:6379/0", env="REDIS_URL")
    redis_host: Optional[str] = Field(None, env="REDIS_HOST")
    redis_port: Optional[int] = Field(None, env="REDIS_PORT")
    redis_db: Optional[int] = Field(None, env="REDIS_DB")

    # Security / Auth
    secret_key: str = Field(..., env="SECRET_KEY")
    algorithm: str = Field("HS256", env="ALGORITHM")
    access_token_expire_minutes: int = Field(1440, env="ACCESS_TOKEN_EXPIRE_MINUTES")

    # Angel One Broker
    angelone_api_key: Optional[str] = Field(None, env="ANGELONE_API_KEY")
    angelone_client_id: Optional[str] = Field(None, env="ANGELONE_CLIENT_ID")
    angelone_password: Optional[str] = Field(None, env="ANGELONE_PASSWORD")
    angelone_totp_secret: Optional[str] = Field(None, env="ANGELONE_TOTP_SECRET")

    # Logging
    log_level: str = Field("INFO", env="LOG_LEVEL")
    log_file: str = Field("trading_engine.log", env="LOG_FILE")

    # Trading Engine
    engine_loop_interval: float = Field(1.0, env="ENGINE_LOOP_INTERVAL")
    max_concurrent_orders: int = Field(100, env="MAX_CONCURRENT_ORDERS")

    # Risk Management
    max_daily_loss_pct: float = Field(5.0, env="MAX_DAILY_LOSS_PCT")
    max_position_size_pct: float = Field(10.0, env="MAX_POSITION_SIZE_PCT")

    class Config:
        env_file = ".env"
        case_sensitive = False

# Global settings instance
_settings: Optional[Settings] = None

def get_settings() -> Settings:
    """Get application settings (singleton)"""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings 