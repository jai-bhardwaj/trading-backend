"""
Industrial Trading System Configuration
"""

import os
from typing import Dict, Any

class TradingConfig:
    """Main trading system configuration"""
    
    # Environment
    ENVIRONMENT = os.getenv('ENVIRONMENT', os.getenv('TRADING_ENV', 'production'))
    DEBUG = ENVIRONMENT != 'production'
    
    # API Configuration
    API_HOST = os.getenv('API_HOST', '0.0.0.0')
    API_PORT = int(os.getenv('API_PORT', 8000))
    ADMIN_PORT = int(os.getenv('ADMIN_PORT', 8080))
    
    # Redis Configuration  
    REDIS_URL = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
    
    # Angel One Broker Configuration
    ANGEL_ONE_API_KEY = os.getenv('ANGEL_ONE_API_KEY', '')
    ANGEL_ONE_SECRET_KEY = os.getenv('ANGEL_ONE_SECRET_KEY', '')
    ANGEL_ONE_CLIENT_ID = os.getenv('ANGEL_ONE_CLIENT_ID', '')
    ANGEL_ONE_PIN = os.getenv('ANGEL_ONE_PIN', '')
    ANGEL_ONE_TOTP_SECRET = os.getenv('ANGEL_ONE_TOTP_SECRET', '')
    
    # Email Configuration
    SMTP_HOST = os.getenv('SMTP_HOST', 'smtp.gmail.com')
    SMTP_PORT = int(os.getenv('SMTP_PORT', 587))
    SMTP_USER = os.getenv('SMTP_USER', '')
    SMTP_PASSWORD = os.getenv('SMTP_PASSWORD', '')
    EMAIL_FROM = os.getenv('EMAIL_FROM', 'trading@example.com')
    
    # Trading Configuration
    MAX_STRATEGIES_PER_USER = int(os.getenv('MAX_STRATEGIES_PER_USER', 10))
    MAX_ORDERS_PER_MINUTE = int(os.getenv('MAX_ORDERS_PER_MINUTE', 100))
    DEFAULT_CAPITAL = float(os.getenv('DEFAULT_CAPITAL', 100000.0))
    
    # System Configuration
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
    MEMORY_LIMIT_MB = int(os.getenv('MEMORY_LIMIT_MB', 1024))
    
    # Market Data Configuration - Real-time settings
    MARKET_DATA_REFRESH_INTERVAL = int(os.getenv('MARKET_DATA_REFRESH_INTERVAL', 1))  # 1 second for real-time
    STRATEGY_EXECUTION_INTERVAL = int(os.getenv('STRATEGY_EXECUTION_INTERVAL', 2))    # 2 seconds for faster execution
    
    @classmethod
    def get_config(cls) -> Dict[str, Any]:
        """Get all configuration as a dictionary"""
        return {
            'environment': cls.ENVIRONMENT,
            'debug': cls.DEBUG,
            'api': {
                'host': cls.API_HOST,
                'port': cls.API_PORT,
                'admin_port': cls.ADMIN_PORT
            },
            'redis': {
                'url': cls.REDIS_URL
            },
            'broker': {
                'api_key': cls.ANGEL_ONE_API_KEY,
                'secret_key': cls.ANGEL_ONE_SECRET_KEY,
                'client_id': cls.ANGEL_ONE_CLIENT_ID,
                'pin': cls.ANGEL_ONE_PIN,
                'totp_secret': cls.ANGEL_ONE_TOTP_SECRET
            },
            'email': {
                'smtp_host': cls.SMTP_HOST,
                'smtp_port': cls.SMTP_PORT,
                'smtp_user': cls.SMTP_USER,
                'smtp_password': cls.SMTP_PASSWORD,
                'from_email': cls.EMAIL_FROM
            },
            'trading': {
                'max_strategies_per_user': cls.MAX_STRATEGIES_PER_USER,
                'max_orders_per_minute': cls.MAX_ORDERS_PER_MINUTE,
                'default_capital': cls.DEFAULT_CAPITAL
            },
            'system': {
                'log_level': cls.LOG_LEVEL,
                'memory_limit_mb': cls.MEMORY_LIMIT_MB
            },
            'market_data': {
                'refresh_interval': cls.MARKET_DATA_REFRESH_INTERVAL,
                'execution_interval': cls.STRATEGY_EXECUTION_INTERVAL
            }
        }
    
    @classmethod
    def validate_config(cls) -> Dict[str, Any]:
        """Validate configuration and return status"""
        errors = []
        warnings = []
        
        # Check required broker configuration
        if not cls.ANGEL_ONE_API_KEY:
            errors.append("ANGEL_ONE_API_KEY is required")
        if not cls.ANGEL_ONE_SECRET_KEY:
            errors.append("ANGEL_ONE_SECRET_KEY is required")
        if not cls.ANGEL_ONE_CLIENT_ID:
            errors.append("ANGEL_ONE_CLIENT_ID is required")
        
        # Check email configuration
        if not cls.SMTP_USER and cls.ENVIRONMENT == 'production':
            warnings.append("Email notifications disabled - SMTP_USER not configured")
        
        return {
            'valid': len(errors) == 0,
            'errors': errors,
            'warnings': warnings
        } 