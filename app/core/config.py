"""
Centralized Configuration Management
Handles all application settings, database connections, and environment variables
"""

import os
import logging
from typing import Dict, Any, Optional, List
from pydantic_settings import BaseSettings
from pydantic import Field, validator
from functools import lru_cache
from pathlib import Path
from pydantic import BaseModel, ConfigDict, computed_field, model_validator

logger = logging.getLogger(__name__)

class DatabaseConfig(BaseModel):
    """Database configuration with DigitalOcean optimizations"""
    url: str = Field(
        default="postgresql+asyncpg://localhost:5432/trading",
        description="Database connection URL with SSL support"
    )
    
    # Connection pool settings optimized for managed database
    pool_size: int = Field(default=20, ge=5, le=100)
    max_overflow: int = Field(default=30, ge=10, le=200)
    pool_pre_ping: bool = Field(default=True, description="Enable connection health checks")
    pool_recycle: int = Field(default=3600, description="Connection recycle time (seconds)")
    echo: bool = Field(default=False, description="Enable SQL query logging")
    
    # DigitalOcean specific settings
    connect_timeout: int = Field(default=60, description="Connection timeout for managed DB")
    command_timeout: int = Field(default=60, description="Command timeout for managed DB")
    server_settings: Dict[str, str] = Field(
        default_factory=lambda: {
            "application_name": "trading_engine",
            "jit": "off",  # Disable JIT for better connection performance
        }
    )
    
    # SSL configuration for DigitalOcean
    ssl_mode: str = Field(default="require", description="SSL mode for managed database")
    ssl_cert_reqs: str = Field(default="required", description="SSL certificate requirements")
    
    model_config = ConfigDict(
        extra="allow",
        validate_assignment=True,
        str_strip_whitespace=True
    )
    
    @computed_field
    @property
    def processed_url(self) -> str:
        """Process database URL for async operations with SSL"""
        url = str(self.url)
        
        # Ensure async driver
        if url.startswith("postgresql://"):
            url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
        elif not url.startswith("postgresql+asyncpg://"):
            raise ValueError("Database URL must use postgresql+asyncpg:// for async operations")
        
        # Convert sslmode to ssl for asyncpg compatibility
        if "sslmode=" in url:
            url = url.replace("sslmode=", "ssl=")
            logger.info("🔄 Converted sslmode to ssl for asyncpg compatibility")
        
        # Add SSL parameters if not present and using managed database
        elif "ondigitalocean.com" in url and "ssl=" not in url:
            separator = "&" if "?" in url else "?"
            url += f"{separator}ssl={self.ssl_mode}"
            logger.info("🔒 Added SSL parameter for DigitalOcean managed database")
        
        return url
    
    @model_validator(mode='after')
    def validate_database_config(self) -> 'DatabaseConfig':
        """Validate database configuration"""
        url = str(self.url)
        
        # Validate DigitalOcean managed database URLs
        if "ondigitalocean.com" in url:
            if not url.startswith(("postgresql://", "postgresql+asyncpg://")):
                raise ValueError("DigitalOcean database URL must start with postgresql://")
            
            if "sslmode=" not in url:
                logger.warning("SSL mode not specified for DigitalOcean database, adding sslmode=require")
        
        # Validate pool settings for managed database
        if "ondigitalocean.com" in url and self.pool_size > 50:
            logger.warning("Large pool size detected for managed database. Consider reducing for better performance.")
        
        return self

class RedisConfig(BaseSettings):
    """Redis configuration settings"""
    url: str = Field("redis://localhost:6379", env="REDIS_URL")
    decode_responses: bool = Field(True, env="REDIS_DECODE_RESPONSES")
    socket_connect_timeout: int = Field(30, env="REDIS_SOCKET_CONNECT_TIMEOUT")
    socket_timeout: int = Field(30, env="REDIS_SOCKET_TIMEOUT")
    retry_on_timeout: bool = Field(True, env="REDIS_RETRY_ON_TIMEOUT")
    socket_keepalive: bool = Field(True, env="REDIS_SOCKET_KEEPALIVE")
    health_check_interval: int = Field(30, env="REDIS_HEALTH_CHECK_INTERVAL")

class TradingEngineConfig(BaseSettings):
    """Trading engine configuration"""
    worker_count: int = Field(4, env="TRADING_WORKER_COUNT")
    max_queue_size: int = Field(10000, env="TRADING_MAX_QUEUE_SIZE")
    loop_interval: float = Field(1.0, env="TRADING_LOOP_INTERVAL")
    strategy_execution_interval: int = Field(30, env="STRATEGY_EXECUTION_INTERVAL")
    database_sync_interval: int = Field(60, env="DATABASE_SYNC_INTERVAL")
    performance_monitor_interval: int = Field(300, env="PERFORMANCE_MONITOR_INTERVAL")
    queue_health_check_interval: int = Field(60, env="QUEUE_HEALTH_CHECK_INTERVAL")
    paper_trading: bool = Field(True, env="PAPER_TRADING")  # Add paper trading control

class InstrumentConfig(BaseSettings):
    """Instrument management configuration"""
    max_equity_instruments: int = Field(1000, env="MAX_EQUITY_INSTRUMENTS")
    max_derivatives_instruments: int = Field(500, env="MAX_DERIVATIVES_INSTRUMENTS")
    max_total_instruments: int = Field(2000, env="MAX_TOTAL_INSTRUMENTS")
    load_all_instruments: bool = Field(False, env="LOAD_ALL_INSTRUMENTS")
    instrument_refresh_interval: int = Field(3600, env="INSTRUMENT_REFRESH_INTERVAL")  # 1 hour
    angel_one_instrument_url: str = Field(
        "https://margincalculator.angelbroking.com/OpenAPI_File/files/OpenAPIScripMaster.json",
        env="ANGEL_ONE_INSTRUMENT_URL"
    )

class SecurityConfig(BaseSettings):
    """Security and authentication configuration"""
    secret_key: str = Field("dev-secret-key-change-in-production", env="SECRET_KEY")
    access_token_expire_minutes: int = Field(30, env="ACCESS_TOKEN_EXPIRE_MINUTES")
    refresh_token_expire_days: int = Field(7, env="REFRESH_TOKEN_EXPIRE_DAYS")
    password_reset_expire_minutes: int = Field(15, env="PASSWORD_RESET_EXPIRE_MINUTES")
    max_login_attempts: int = Field(5, env="MAX_LOGIN_ATTEMPTS")
    account_lockout_duration: int = Field(900, env="ACCOUNT_LOCKOUT_DURATION")  # 15 minutes

class BrokerConfig(BaseSettings):
    """Broker configuration"""
    default_broker: str = Field("angelone", env="DEFAULT_BROKER")
    connection_timeout: int = Field(30, env="BROKER_CONNECTION_TIMEOUT")
    max_retries: int = Field(3, env="BROKER_MAX_RETRIES")
    retry_delay: float = Field(1.0, env="BROKER_RETRY_DELAY")
    
    # Angel One specific
    angelone_base_url: str = Field("https://apiconnect.angelbroking.com", env="ANGELONE_BASE_URL")
    angelone_rate_limit: int = Field(100, env="ANGELONE_RATE_LIMIT")  # requests per minute

class RiskManagementConfig(BaseSettings):
    """Risk management configuration"""
    max_daily_loss_pct: float = Field(0.02, env="RISK_MAX_DAILY_LOSS_PCT")
    max_position_size_pct: float = Field(0.10, env="RISK_MAX_POSITION_SIZE_PCT")
    max_order_value: float = Field(50000, env="RISK_MAX_ORDER_VALUE")
    max_orders_per_minute: int = Field(10, env="RISK_MAX_ORDERS_PER_MINUTE")
    circuit_breaker_threshold: int = Field(5, env="RISK_CIRCUIT_BREAKER_THRESHOLD")
    circuit_breaker_timeout: int = Field(60, env="RISK_CIRCUIT_BREAKER_TIMEOUT")

class LoggingConfig(BaseSettings):
    """Logging configuration"""
    level: str = Field("INFO", env="LOG_LEVEL")
    format: str = Field(
        "%(asctime)s [%(levelname)s] %(name)s:%(lineno)d - %(funcName)s() - %(message)s",
        env="LOG_FORMAT"
    )
    file_path: Optional[str] = Field(None, env="LOG_FILE_PATH")
    max_file_size: int = Field(10 * 1024 * 1024, env="LOG_MAX_FILE_SIZE")  # 10MB
    backup_count: int = Field(5, env="LOG_BACKUP_COUNT")
    enable_console: bool = Field(True, env="LOG_ENABLE_CONSOLE")
    enable_file: bool = Field(True, env="LOG_ENABLE_FILE")

class ApiConfig(BaseSettings):
    """API configuration"""
    host: str = Field("0.0.0.0", env="API_HOST")
    port: int = Field(8000, env="API_PORT")
    debug: bool = Field(False, env="API_DEBUG")
    reload: bool = Field(False, env="API_RELOAD")
    cors_origins: List[str] = Field(["*"], env="CORS_ORIGINS")
    rate_limit: str = Field("100/minute", env="API_RATE_LIMIT")

class NotificationConfig(BaseSettings):
    """Notification configuration"""
    email_enabled: bool = Field(False, env="NOTIFICATION_EMAIL_ENABLED")
    sms_enabled: bool = Field(False, env="NOTIFICATION_SMS_ENABLED")
    webhook_enabled: bool = Field(False, env="NOTIFICATION_WEBHOOK_ENABLED")
    
    # Email settings
    smtp_host: Optional[str] = Field(None, env="SMTP_HOST")
    smtp_port: int = Field(587, env="SMTP_PORT")
    smtp_username: Optional[str] = Field(None, env="SMTP_USERNAME")
    smtp_password: Optional[str] = Field(None, env="SMTP_PASSWORD")
    smtp_use_tls: bool = Field(True, env="SMTP_USE_TLS")
    
    # Default notification limits
    max_notifications_per_minute: int = Field(10, env="MAX_NOTIFICATIONS_PER_MINUTE")

class MonitoringConfig(BaseSettings):
    """Monitoring and observability configuration"""
    metrics_enabled: bool = Field(True, env="METRICS_ENABLED")
    health_check_enabled: bool = Field(True, env="HEALTH_CHECK_ENABLED")
    performance_tracking: bool = Field(True, env="PERFORMANCE_TRACKING_ENABLED")
    audit_logging: bool = Field(True, env="AUDIT_LOGGING_ENABLED")
    
    # Prometheus metrics
    prometheus_enabled: bool = Field(False, env="PROMETHEUS_ENABLED")
    prometheus_port: int = Field(9090, env="PROMETHEUS_PORT")

class AppSettings(BaseSettings):
    """Main application settings"""
    
    # Environment
    environment: str = Field("development", env="ENVIRONMENT")
    debug: bool = Field(False, env="DEBUG")
    testing: bool = Field(False, env="TESTING")
    
    # Application info
    app_name: str = Field("Trading Engine", env="APP_NAME")
    app_version: str = Field("1.0.0", env="APP_VERSION")
    
    model_config = {
        'env_file': '.env',
        'env_file_encoding': 'utf-8',
        'case_sensitive': False,
        'extra': 'allow'  # Allow extra fields from .env
    }
        
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        
        # Initialize sub-configurations with environment variables
        from os import getenv
        
        # Database configuration with environment variables
        self.database = DatabaseConfig(
            url=getenv("DATABASE_URL", "postgresql+asyncpg://localhost:5432/trading"),
            pool_size=int(getenv("DB_POOL_SIZE", "20")),
            max_overflow=int(getenv("DB_MAX_OVERFLOW", "30")),
            pool_pre_ping=getenv("DB_POOL_PRE_PING", "true").lower() == "true",
            pool_recycle=int(getenv("DB_POOL_RECYCLE", "3600")),
            echo=getenv("DB_ECHO", "false").lower() == "true"
        )
        
        self.redis = RedisConfig()
        self.trading_engine = TradingEngineConfig()
        self.instruments = InstrumentConfig()
        self.security = SecurityConfig()
        self.broker = BrokerConfig()
        self.risk_management = RiskManagementConfig()
        self.logging = LoggingConfig()
        self.api = ApiConfig()
        self.notifications = NotificationConfig()
        self.monitoring = MonitoringConfig()
        
    @validator('environment')
    def validate_environment(cls, v):
        allowed_envs = ['development', 'staging', 'production', 'testing']
        if v.lower() not in allowed_envs:
            raise ValueError(f"Environment must be one of: {allowed_envs}")
        return v.lower()
    
    def is_production(self) -> bool:
        """Check if running in production"""
        return self.environment == "production"
    
    def is_development(self) -> bool:
        """Check if running in development"""
        return self.environment == "development"
    
    def is_testing(self) -> bool:
        """Check if running in testing"""
        return self.environment == "testing" or self.testing

@lru_cache()
def get_settings() -> AppSettings:
    """Get cached application settings"""
    return AppSettings()

def setup_logging(settings: Optional[AppSettings] = None) -> None:
    """Setup application logging"""
    if settings is None:
        settings = get_settings()
    
    logging_config = settings.logging
    
    # Create logs directory if it doesn't exist
    if logging_config.file_path:
        log_dir = Path(logging_config.file_path).parent
        log_dir.mkdir(parents=True, exist_ok=True)
    
    # Setup logging configuration
    log_level = getattr(logging, logging_config.level.upper(), logging.INFO)
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    
    # Clear existing handlers
    root_logger.handlers.clear()
    
    # Create formatter
    formatter = logging.Formatter(logging_config.format)
    
    # Console handler
    if logging_config.enable_console:
        console_handler = logging.StreamHandler()
        console_handler.setLevel(log_level)
        console_handler.setFormatter(formatter)
        root_logger.addHandler(console_handler)
    
    # File handler
    if logging_config.enable_file and logging_config.file_path:
        from logging.handlers import RotatingFileHandler
        file_handler = RotatingFileHandler(
            logging_config.file_path,
            maxBytes=logging_config.max_file_size,
            backupCount=logging_config.backup_count
        )
        file_handler.setLevel(log_level)
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)

def validate_configuration(settings: Optional[AppSettings] = None) -> Dict[str, Any]:
    """Validate application configuration and return status"""
    if settings is None:
        settings = get_settings()
    
    validation_results = {
        "valid": True,
        "errors": [],
        "warnings": [],
        "info": []
    }
    
    try:
        # Validate database URL
        if not settings.database.url:
            validation_results["errors"].append("DATABASE_URL is required")
            validation_results["valid"] = False
        
        # Validate secret key for production
        if settings.is_production() and (not settings.security.secret_key or len(settings.security.secret_key) < 32):
            validation_results["errors"].append("SECRET_KEY must be at least 32 characters in production")
            validation_results["valid"] = False
        
        # Check Redis connection
        if not settings.redis.url:
            validation_results["warnings"].append("Redis URL not configured, using default")
        
        # Validate broker configuration
        if settings.broker.default_broker not in ["angelone", "zerodha", "upstox"]:
            validation_results["warnings"].append(f"Unknown default broker: {settings.broker.default_broker}")
        
        # Check instrument limits
        if settings.instruments.max_total_instruments > 50000:
            validation_results["warnings"].append("Max total instruments is very high, may impact performance")
        
        # Production-specific checks
        if settings.is_production():
            if settings.debug:
                validation_results["warnings"].append("Debug mode enabled in production")
            
            if settings.api.debug:
                validation_results["warnings"].append("API debug mode enabled in production")
        
        validation_results["info"].append(f"Environment: {settings.environment}")
        validation_results["info"].append(f"Debug mode: {settings.debug}")
        validation_results["info"].append(f"Database pool size: {settings.database.pool_size}")
        validation_results["info"].append(f"Trading workers: {settings.trading_engine.worker_count}")
        
    except Exception as e:
        validation_results["errors"].append(f"Configuration validation error: {str(e)}")
        validation_results["valid"] = False
    
    return validation_results

# Global settings instance
settings = get_settings()

# Setup logging on import
setup_logging(settings)
