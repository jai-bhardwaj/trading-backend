"""
Trading System Constants
Eliminates magic numbers and provides centralized configuration
"""

from typing import Dict, Any
from decimal import Decimal

# =============================================================================
# TRADING CONSTANTS
# =============================================================================

class TradingConstants:
    """Core trading system constants"""
    
    # Order Management
    MAX_ORDERS_PER_USER = 100
    MAX_ORDERS_PER_SYMBOL = 50
    ORDER_TIMEOUT_SECONDS = 300  # 5 minutes
    ORDER_RETRY_ATTEMPTS = 3
    ORDER_RETRY_DELAY_SECONDS = 1
    
    # Position Management
    MAX_POSITIONS_PER_USER = 20
    MAX_POSITION_SIZE_PERCENT = 10.0  # 10% of portfolio
    MIN_POSITION_VALUE = 100.0  # $100 minimum
    MAX_POSITION_VALUE = 100000.0  # $100k maximum
    
    # Risk Management
    DEFAULT_STOP_LOSS_PERCENT = 5.0  # 5%
    DEFAULT_TAKE_PROFIT_PERCENT = 10.0  # 10%
    MAX_DAILY_LOSS_PERCENT = 2.0  # 2% of account
    MAX_DRAWDOWN_PERCENT = 10.0  # 10% maximum drawdown
    
    # Price Validation
    MIN_PRICE = Decimal('0.01')  # 1 cent minimum
    MAX_PRICE = Decimal('1000000.00')  # $1M maximum
    PRICE_PRECISION = 2  # 2 decimal places
    
    # Quantity Validation
    MIN_QUANTITY = 1
    MAX_QUANTITY = 1000000
    QUANTITY_PRECISION = 0  # Whole numbers only

class SystemConstants:
    """System-level constants"""
    
    # Memory Management
    MAX_PRICE_HISTORY_PER_SYMBOL = 200
    MAX_TOTAL_SYMBOLS = 1000
    MEMORY_CLEANUP_INTERVAL_MINUTES = 15
    INACTIVE_SYMBOL_THRESHOLD_MINUTES = 30
    MEMORY_LIMIT_MB = 100
    
    # Database
    CONNECTION_TIMEOUT_SECONDS = 30
    QUERY_TIMEOUT_SECONDS = 60
    MAX_CONNECTIONS = 20
    CONNECTION_RETRY_ATTEMPTS = 3
    
    # API Rate Limiting
    API_RATE_LIMIT_PER_MINUTE = 60
    LOGIN_RATE_LIMIT_PER_15_MIN = 5
    MAX_REQUEST_SIZE_MB = 10
    REQUEST_TIMEOUT_SECONDS = 30
    
    # Monitoring
    HEALTH_CHECK_INTERVAL_SECONDS = 60
    RESOURCE_MONITORING_INTERVAL_SECONDS = 30
    LOG_ROTATION_SIZE_MB = 100
    LOG_RETENTION_DAYS = 30

class SecurityConstants:
    """Security-related constants"""
    
    # Authentication
    ACCESS_TOKEN_EXPIRE_MINUTES = 30
    REFRESH_TOKEN_EXPIRE_DAYS = 7
    JWT_ALGORITHM = "HS256"
    
    # Password Requirements
    MIN_PASSWORD_LENGTH = 8
    MAX_PASSWORD_LENGTH = 128
    REQUIRE_UPPERCASE = True
    REQUIRE_LOWERCASE = True
    REQUIRE_NUMBERS = True
    REQUIRE_SPECIAL_CHARS = True
    
    # Session Management
    MAX_SESSIONS_PER_USER = 5
    SESSION_TIMEOUT_MINUTES = 60
    IDLE_TIMEOUT_MINUTES = 30
    
    # Input Validation
    MAX_STRING_LENGTH = 1000
    MAX_ARRAY_LENGTH = 1000
    MAX_NESTED_DEPTH = 10
    
    # SQL Injection Patterns (for detection)
    SQL_INJECTION_PATTERNS = [
        r"(\s*(union|select|insert|update|delete|drop|create|alter|exec|execute)\s+)",
        r"(\s*;\s*(union|select|insert|update|delete|drop|create|alter|exec|execute)\s+)",
        r"(\s*'\s*(or|and)\s+)",
        r"(\s*--\s*)",
        r"(\s*/\*.*\*/\s*)",
        r"(\s*xp_\w+)",
        r"(\s*sp_\w+)",
        r"(\s*0x[0-9a-f]+)",
        r"(\s*char\s*\(\s*\d+\s*\))",
        r"(\s*ascii\s*\(\s*)",
        r"(\s*substring\s*\(\s*)",
        r"(\s*len\s*\(\s*)",
        r"(\s*cast\s*\(\s*)",
        r"(\s*convert\s*\(\s*)",
        r"(\s*waitfor\s+delay\s+)",
        r"(\s*benchmark\s*\(\s*)"
    ]
    
    # XSS Patterns (for detection)
    XSS_PATTERNS = [
        r"<script[^>]*>.*?</script>",
        r"javascript:",
        r"on\w+\s*=",
        r"<iframe[^>]*>",
        r"<object[^>]*>",
        r"<embed[^>]*>",
        r"<link[^>]*>",
        r"<meta[^>]*>",
        r"<form[^>]*>",
        r"<input[^>]*>",
        r"eval\s*\(",
        r"expression\s*\("
    ]

class BrokerConstants:
    """Broker-specific constants"""
    
    # Connection
    CONNECTION_TIMEOUT_SECONDS = 10
    RECONNECTION_ATTEMPTS = 5
    RECONNECTION_DELAY_SECONDS = 5
    HEARTBEAT_INTERVAL_SECONDS = 30
    
    # Order Management
    ORDER_STATUS_CHECK_INTERVAL_SECONDS = 1
    PENDING_ORDER_TIMEOUT_SECONDS = 300
    FILL_CONFIRMATION_TIMEOUT_SECONDS = 10
    
    # Market Data
    MARKET_DATA_TIMEOUT_SECONDS = 5
    PRICE_STALENESS_THRESHOLD_SECONDS = 60
    MAX_MARKET_DATA_SUBSCRIPTIONS = 100

class StrategyConstants:
    """Strategy-related constants"""
    
    # Technical Indicators
    RSI_PERIOD = 14
    RSI_OVERBOUGHT = 70
    RSI_OVERSOLD = 30
    
    MOVING_AVERAGE_SHORT_PERIOD = 10
    MOVING_AVERAGE_LONG_PERIOD = 50
    
    BOLLINGER_BANDS_PERIOD = 20
    BOLLINGER_BANDS_STD_DEV = 2
    
    MACD_FAST_PERIOD = 12
    MACD_SLOW_PERIOD = 26
    MACD_SIGNAL_PERIOD = 9
    
    # Strategy Execution
    MIN_SIGNAL_CONFIDENCE = 0.6  # 60% confidence minimum
    SIGNAL_TIMEOUT_SECONDS = 300  # 5 minutes
    MAX_CONCURRENT_SIGNALS = 10
    
    # Backtesting
    MIN_BACKTEST_DAYS = 30
    MAX_BACKTEST_DAYS = 365
    BACKTEST_COMMISSION_PERCENT = 0.1  # 0.1%
    BACKTEST_SLIPPAGE_PERCENT = 0.05  # 0.05%

class ErrorConstants:
    """Error handling constants"""
    
    # Retry Logic
    MAX_RETRY_ATTEMPTS = 3
    RETRY_DELAY_SECONDS = 1
    EXPONENTIAL_BACKOFF_MULTIPLIER = 2
    MAX_RETRY_DELAY_SECONDS = 60
    
    # Error Classification
    CRITICAL_ERROR_THRESHOLD = 5  # 5 critical errors trigger shutdown
    ERROR_RATE_THRESHOLD_PERCENT = 10  # 10% error rate is concerning
    ERROR_BURST_THRESHOLD = 10  # 10 errors in short time
    ERROR_BURST_WINDOW_SECONDS = 60
    
    # Circuit Breaker
    CIRCUIT_BREAKER_FAILURE_THRESHOLD = 10
    CIRCUIT_BREAKER_TIMEOUT_SECONDS = 300  # 5 minutes
    CIRCUIT_BREAKER_SUCCESS_THRESHOLD = 5

# =============================================================================
# CONFIGURATION MAPPINGS
# =============================================================================

class ConfigMappings:
    """Configuration value mappings"""
    
    # Risk Level Mappings
    RISK_LEVEL_MULTIPLIERS = {
        'low': 0.5,
        'medium': 1.0,
        'high': 2.0
    }
    
    # Time Interval Mappings (in seconds)
    TIME_INTERVALS = {
        '1m': 60,
        '5m': 300,
        '15m': 900,
        '30m': 1800,
        '1h': 3600,
        '4h': 14400,
        '1d': 86400
    }
    
    # Order Type Mappings
    ORDER_TYPE_PRIORITIES = {
        'MARKET': 1,  # Highest priority
        'LIMIT': 2,
        'STOP': 3,
        'STOP_LIMIT': 4  # Lowest priority
    }
    
    # Status Mappings
    STATUS_COLORS = {
        'ACTIVE': 'green',
        'INACTIVE': 'gray',
        'ERROR': 'red',
        'WARNING': 'yellow',
        'PENDING': 'blue'
    }

# =============================================================================
# VALIDATION CONSTANTS
# =============================================================================

class ValidationConstants:
    """Input validation constants"""
    
    # String Validation
    SYMBOL_REGEX = r'^[A-Z0-9._-]{1,20}$'
    EMAIL_REGEX = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    PASSWORD_REGEX = r'^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]{8,128}$'
    
    # Numeric Validation
    MIN_PERCENTAGE = 0.0
    MAX_PERCENTAGE = 100.0
    MIN_CONFIDENCE = 0.0
    MAX_CONFIDENCE = 1.0
    
    # Date Validation
    MIN_DATE_YEAR = 2020
    MAX_DATE_YEAR = 2030

# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def get_constant(category: str, name: str, default: Any = None) -> Any:
    """Get constant value by category and name"""
    categories = {
        'trading': TradingConstants,
        'system': SystemConstants,
        'security': SecurityConstants,
        'broker': BrokerConstants,
        'strategy': StrategyConstants,
        'error': ErrorConstants,
        'validation': ValidationConstants
    }
    
    category_class = categories.get(category.lower())
    if category_class:
        return getattr(category_class, name.upper(), default)
    return default

def get_all_constants() -> Dict[str, Dict[str, Any]]:
    """Get all constants organized by category"""
    return {
        'trading': {k: v for k, v in TradingConstants.__dict__.items() if not k.startswith('_')},
        'system': {k: v for k, v in SystemConstants.__dict__.items() if not k.startswith('_')},
        'security': {k: v for k, v in SecurityConstants.__dict__.items() if not k.startswith('_')},
        'broker': {k: v for k, v in BrokerConstants.__dict__.items() if not k.startswith('_')},
        'strategy': {k: v for k, v in StrategyConstants.__dict__.items() if not k.startswith('_')},
        'error': {k: v for k, v in ErrorConstants.__dict__.items() if not k.startswith('_')},
        'validation': {k: v for k, v in ValidationConstants.__dict__.items() if not k.startswith('_')},
        'mappings': {k: v for k, v in ConfigMappings.__dict__.items() if not k.startswith('_')}
    }

def validate_constant_usage():
    """Validate that constants are being used properly"""
    # This could be extended to scan code for magic numbers
    pass

# Export commonly used constants for easy access
DEFAULT_STOP_LOSS = TradingConstants.DEFAULT_STOP_LOSS_PERCENT
DEFAULT_TAKE_PROFIT = TradingConstants.DEFAULT_TAKE_PROFIT_PERCENT
MAX_ORDERS = TradingConstants.MAX_ORDERS_PER_USER
API_RATE_LIMIT = SystemConstants.API_RATE_LIMIT_PER_MINUTE
TOKEN_EXPIRE_MINUTES = SecurityConstants.ACCESS_TOKEN_EXPIRE_MINUTES
RSI_PERIOD = StrategyConstants.RSI_PERIOD
MAX_RETRIES = ErrorConstants.MAX_RETRY_ATTEMPTS
