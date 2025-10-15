"""
Configuration for RSI DMI Strategy
"""
import os
from typing import Dict, Any

class RSIDMIConfig:
    """Configuration class for RSI DMI Strategy"""
    
    # Strategy identification
    STRATEGY_ID = os.getenv('STRATEGY_ID', 'rsi_dmi_strategy')
    
    # Symbols to trade
    SYMBOLS = [s.strip() for s in os.getenv('SYMBOLS', 'RELIANCE,TCS,INFY').split(',')]
    
    # Strategy parameters
    PARAMETERS = {
        'entry_rsi_UL': float(os.getenv('ENTRY_RSI_UL', '70')),
        'di_UL': float(os.getenv('DI_UL', '25')),
        'rsi_LL': float(os.getenv('RSI_LL', '30')),
        'capital': float(os.getenv('CAPITAL', '100000')),
        'max_quantity': int(os.getenv('MAX_QUANTITY', '1000')),
        'min_quantity': int(os.getenv('MIN_QUANTITY', '1'))
    }
    
    # Redis configuration
    REDIS_URL = os.getenv('REDIS_URL', 'redis://redis:6379')
    
    # Consumer group
    CONSUMER_GROUP = os.getenv('CONSUMER_GROUP', 'strategy_consumers')
    
    # Signal channel
    SIGNAL_CHANNEL = os.getenv('SIGNAL_CHANNEL', 'strategy_signals')
    
    # Strategy enabled
    ENABLED = os.getenv('ENABLED', 'true').lower() == 'true'
    
    @classmethod
    def get_config_dict(cls) -> Dict[str, Any]:
        """Get configuration as dictionary"""
        return {
            'strategy_id': cls.STRATEGY_ID,
            'symbols': cls.SYMBOLS,
            'parameters': cls.PARAMETERS,
            'enabled': cls.ENABLED,
            'redis_url': cls.REDIS_URL,
            'consumer_group': cls.CONSUMER_GROUP,
            'signal_channel': cls.SIGNAL_CHANNEL
        }
