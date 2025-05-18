from pydantic_settings import BaseSettings
import os


class Settings(BaseSettings):
    PROJECT_NAME: str = os.getenv("PROJECT_NAME", "Trading Backend")
    API_V1_STR: str = os.getenv("API_V1_STR", "/api/v1")
    ENV: str = os.getenv("ENV", "development")
    DEBUG: bool = os.getenv("DEBUG", "True").lower() in ("true", "1", "yes")
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/trading_db"
    )
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    SECRET_KEY: str = os.getenv("SECRET_KEY", "your-secret-key-here")
    ALGORITHM: str = os.getenv("ALGORITHM", "HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(
        os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 60 * 24)
    )
    # Broker credentials (for real brokers, if needed)
    ANGELONE_API_KEY: str = os.getenv("ANGELONE_API_KEY", "")
    ANGELONE_CLIENT_ID: str = os.getenv("ANGELONE_CLIENT_ID", "")
    ANGELONE_PASSWORD: str = os.getenv("ANGELONE_PASSWORD", "")
    ANGELONE_TOTP_SECRET: str = os.getenv("ANGELONE_TOTP_SECRET", "")
    # Add more broker or service credentials as needed

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


settings = Settings()
