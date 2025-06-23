"""
Live Trading Logger Configuration

Enhanced logging for live market hours with:
- Detailed trade execution logging
- Performance monitoring
- Error tracking
- Real-time alerts
- Market data quality logging
"""

import logging
import logging.handlers
import os
import json
import time
from datetime import datetime
from typing import Dict, Any, Optional
import threading

class LiveTradingFormatter(logging.Formatter):
    """Custom formatter for live trading logs"""
    
    def __init__(self):
        super().__init__()
        
    def format(self, record):
        # Add timestamp with milliseconds
        dt = datetime.fromtimestamp(record.created)
        timestamp = dt.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
        
        # Add thread info for debugging
        thread_name = threading.current_thread().name
        
        # Color coding for different log levels
        colors = {
            'DEBUG': '\033[36m',    # Cyan
            'INFO': '\033[32m',     # Green  
            'WARNING': '\033[33m',  # Yellow
            'ERROR': '\033[31m',    # Red
            'CRITICAL': '\033[41m'  # Red background
        }
        
        reset_color = '\033[0m'
        color = colors.get(record.levelname, '')
        
        # Format message
        formatted = f"{timestamp} [{thread_name}] {color}{record.levelname:8}{reset_color} {record.name:20} | {record.getMessage()}"
        
        # Add exception info if present
        if record.exc_info:
            formatted += f"\n{self.formatException(record.exc_info)}"
            
        return formatted

class TradeExecutionLogger:
    """Specialized logger for trade execution details"""
    
    def __init__(self):
        self.logger = logging.getLogger('trade_execution')
        self._setup_trade_logger()
        
    def _setup_trade_logger(self):
        """Setup specialized trade execution logging"""
        # Create trades directory
        os.makedirs('logs/trades', exist_ok=True)
        
        # Daily rotating file for trades
        trade_handler = logging.handlers.TimedRotatingFileHandler(
            'logs/trades/trades.log',
            when='midnight',
            interval=1,
            backupCount=30,
            encoding='utf-8'
        )
        
        # JSON formatter for structured trade data
        trade_handler.setFormatter(logging.Formatter('%(asctime)s | %(message)s'))
        self.logger.addHandler(trade_handler)
        self.logger.setLevel(logging.INFO)
    
    def log_order_placed(self, order_data: Dict[str, Any]):
        """Log order placement with full details"""
        log_entry = {
            'event': 'ORDER_PLACED',
            'timestamp': time.time(),
            'order_id': order_data.get('order_id'),
            'user_id': order_data.get('user_id'),
            'symbol': order_data.get('symbol'),
            'side': order_data.get('side'),
            'quantity': order_data.get('quantity'),
            'order_type': order_data.get('order_type'),
            'price': order_data.get('price'),
            'strategy_id': order_data.get('strategy_id'),
            'signal_id': order_data.get('signal_id')
        }
        self.logger.info(json.dumps(log_entry))
    
    def log_order_filled(self, fill_data: Dict[str, Any]):
        """Log order fill with execution details"""
        log_entry = {
            'event': 'ORDER_FILLED',
            'timestamp': time.time(),
            'order_id': fill_data.get('order_id'),
            'broker_order_id': fill_data.get('broker_order_id'),
            'symbol': fill_data.get('symbol'),
            'side': fill_data.get('side'),
            'quantity': fill_data.get('quantity'),
            'fill_price': fill_data.get('fill_price'),
            'fill_time': fill_data.get('filled_at'),
            'execution_type': fill_data.get('execution_type', 'UNKNOWN')
        }
        self.logger.info(json.dumps(log_entry))
    
    def log_order_rejected(self, rejection_data: Dict[str, Any]):
        """Log order rejection with reason"""
        log_entry = {
            'event': 'ORDER_REJECTED',
            'timestamp': time.time(),
            'order_id': rejection_data.get('order_id'),
            'symbol': rejection_data.get('symbol'),
            'rejection_reason': rejection_data.get('rejection_reason'),
            'user_id': rejection_data.get('user_id')
        }
        self.logger.info(json.dumps(log_entry))

class PerformanceLogger:
    """Logger for system performance metrics"""
    
    def __init__(self):
        self.logger = logging.getLogger('performance')
        self._setup_performance_logger()
        
    def _setup_performance_logger(self):
        """Setup performance logging"""
        os.makedirs('logs/performance', exist_ok=True)
        
        # Performance metrics file
        perf_handler = logging.handlers.TimedRotatingFileHandler(
            'logs/performance/performance.log',
            when='H',  # Hourly rotation
            interval=1,
            backupCount=24,  # Keep 24 hours
            encoding='utf-8'
        )
        
        perf_handler.setFormatter(logging.Formatter('%(asctime)s | %(message)s'))
        self.logger.addHandler(perf_handler)
        self.logger.setLevel(logging.INFO)
    
    def log_metrics(self, metrics: Dict[str, Any]):
        """Log performance metrics"""
        self.logger.info(json.dumps(metrics))

class MarketDataLogger:
    """Logger for market data quality and issues"""
    
    def __init__(self):
        self.logger = logging.getLogger('market_data')
        self._setup_market_data_logger()
        
    def _setup_market_data_logger(self):
        """Setup market data logging"""
        os.makedirs('logs/market_data', exist_ok=True)
        
        # Market data quality log
        market_handler = logging.handlers.TimedRotatingFileHandler(
            'logs/market_data/market_data.log',
            when='H',
            interval=1, 
            backupCount=24,
            encoding='utf-8'
        )
        
        market_handler.setFormatter(logging.Formatter('%(asctime)s | %(message)s'))
        self.logger.addHandler(market_handler)
        self.logger.setLevel(logging.INFO)
    
    def log_connection_status(self, status: str, details: Dict[str, Any]):
        """Log market data connection status changes"""
        log_entry = {
            'event': 'CONNECTION_STATUS',
            'timestamp': time.time(),
            'status': status,
            'details': details
        }
        self.logger.info(json.dumps(log_entry))
    
    def log_data_quality_issue(self, issue_type: str, symbol: str, details: Dict[str, Any]):
        """Log market data quality issues"""
        log_entry = {
            'event': 'DATA_QUALITY_ISSUE',
            'timestamp': time.time(),
            'issue_type': issue_type,
            'symbol': symbol,
            'details': details
        }
        self.logger.info(json.dumps(log_entry))

def setup_live_trading_logging():
    """Setup comprehensive logging for live trading"""
    
    # Create logs directory structure
    os.makedirs('logs', exist_ok=True)
    os.makedirs('logs/trades', exist_ok=True)
    os.makedirs('logs/performance', exist_ok=True)
    os.makedirs('logs/market_data', exist_ok=True)
    os.makedirs('logs/errors', exist_ok=True)
    
    # Root logger configuration
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    
    # Clear existing handlers
    root_logger.handlers.clear()
    
    # Console handler with colors
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(LiveTradingFormatter())
    console_handler.setLevel(logging.INFO)
    root_logger.addHandler(console_handler)
    
    # Main application log file
    main_handler = logging.handlers.TimedRotatingFileHandler(
        'logs/trading_system.log',
        when='midnight',
        interval=1,
        backupCount=7,
        encoding='utf-8'
    )
    main_handler.setFormatter(logging.Formatter(
        '%(asctime)s [%(threadName)s] %(levelname)-8s %(name)-20s | %(message)s'
    ))
    main_handler.setLevel(logging.INFO)
    root_logger.addHandler(main_handler)
    
    # Error log file
    error_handler = logging.handlers.TimedRotatingFileHandler(
        'logs/errors/errors.log',
        when='midnight',
        interval=1,
        backupCount=30,
        encoding='utf-8'
    )
    error_handler.setFormatter(logging.Formatter(
        '%(asctime)s [%(threadName)s] %(levelname)-8s %(name)-20s | %(message)s\n%(pathname)s:%(lineno)d'
    ))
    error_handler.setLevel(logging.ERROR)
    root_logger.addHandler(error_handler)
    
    # Set specific logger levels for debugging
    logging.getLogger('src.core').setLevel(logging.INFO)
    logging.getLogger('src.engine').setLevel(logging.INFO)
    logging.getLogger('uvicorn').setLevel(logging.WARNING)
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    
    # Initialize specialized loggers
    trade_logger = TradeExecutionLogger()
    perf_logger = PerformanceLogger()
    market_logger = MarketDataLogger()
    
    print("🔍 LIVE TRADING LOGGING INITIALIZED")
    print(f"📁 Log files created in: {os.path.abspath('logs')}")
    print("📊 Specialized loggers ready:")
    print("   • Trade execution: logs/trades/trades.log")
    print("   • Performance: logs/performance/performance.log")
    print("   • Market data: logs/market_data/market_data.log")
    print("   • Errors: logs/errors/errors.log")
    
    return {
        'trade_logger': trade_logger,
        'performance_logger': perf_logger,
        'market_data_logger': market_logger
    }

def log_system_startup():
    """Log system startup details"""
    logger = logging.getLogger('system_startup')
    
    startup_info = {
        'event': 'SYSTEM_STARTUP',
        'timestamp': time.time(),
        'datetime': datetime.now().isoformat(),
        'pid': os.getpid(),
        'python_version': os.sys.version,
        'working_directory': os.getcwd(),
        'environment_vars': {
            'ENVIRONMENT': os.getenv('ENVIRONMENT', 'unknown'),
            'PYTHON_ENV': os.getenv('PYTHON_ENV', 'unknown'),
            'LOG_LEVEL': os.getenv('LOG_LEVEL', 'INFO')
        }
    }
    
    logger.info("🚀 TRADING SYSTEM STARTUP")
    logger.info("=" * 80)
    for key, value in startup_info.items():
        if key not in ['event', 'timestamp']:
            logger.info(f"   {key}: {value}")
    logger.info("=" * 80)

def log_market_hours_start():
    """Log market hours start"""
    logger = logging.getLogger('market_hours')
    logger.info("🏁 MARKET HOURS STARTED - LIVE TRADING ACTIVE")
    logger.info("📈 System ready for live order execution")
    logger.info("🔍 Enhanced monitoring and logging active")

def log_market_hours_end():
    """Log market hours end"""
    logger = logging.getLogger('market_hours')
    logger.info("🏁 MARKET HOURS ENDED - LIVE TRADING STOPPED")
    logger.info("📊 Daily trading session complete") 