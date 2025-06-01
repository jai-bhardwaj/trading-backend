"""
Comprehensive Broker Package - Multi-broker trading system

This package provides a unified interface for multiple brokers with automatic
discovery, registration, and management capabilities.
"""

import logging
from typing import Dict, List, Any, Optional

# Import base classes and utilities
from .base import (
    BrokerInterface, BrokerRegistry, BrokerManager, register_broker,
    BrokerOrder, BrokerPosition, BrokerBalance, BrokerTrade, MarketData,
    BrokerError, AuthenticationError, OrderError, InsufficientFundsError,
    SymbolNotFoundError, RateLimitError, broker_manager
)

# Import broker implementations
from .angelone_new import AngelOneBroker
from .mock_broker import MockBroker

logger = logging.getLogger(__name__)

# Auto-register all broker implementations
def _auto_register_brokers():
    """Automatically register all available broker implementations"""
    try:
        # AngelOne is already registered via decorator
        logger.info("Angel One broker registered")
        
        # Register MockBroker if available
        try:
            from .mock_broker import MockBroker
            # MockBroker should also use the @register_broker decorator
            logger.info("Mock broker available")
        except ImportError:
            logger.debug("Mock broker not available")
        
        # Add more brokers here as they are implemented
        # from .zerodha import ZerodhaBroker  # Future implementation
        # from .upstox import UpstoxBroker    # Future implementation
        
        registered_brokers = BrokerRegistry.list_brokers()
        logger.info(f"Registered brokers: {[b.value for b in registered_brokers]}")
        
    except Exception as e:
        logger.error(f"Error during broker auto-registration: {e}")

# Initialize broker system
_auto_register_brokers()

# Convenience functions for broker management
async def get_broker_instance(config) -> BrokerInterface:
    """
    Get a broker instance from configuration
    
    Args:
        config: BrokerConfig from database
        
    Returns:
        BrokerInterface: Configured broker instance
    """
    return BrokerRegistry.get_broker(config)

async def list_available_brokers() -> List[str]:
    """
    List all available broker implementations
    
    Returns:
        List[str]: List of broker names
    """
    return [broker.value for broker in BrokerRegistry.list_brokers()]

async def get_broker_capabilities() -> Dict[str, Dict[str, Any]]:
    """
    Get detailed capabilities of all registered brokers
    
    Returns:
        Dict: Broker capabilities and features
    """
    return BrokerRegistry.get_supported_brokers()

async def health_check_all_brokers() -> Dict[str, Dict[str, Any]]:
    """
    Perform health check on all active broker instances
    
    Returns:
        Dict: Health status for all brokers
    """
    return await BrokerRegistry.health_check_all()

# Export main classes and functions
__all__ = [
    # Base classes
    "BrokerInterface",
    "BrokerRegistry", 
    "BrokerManager",
    "broker_manager",
    
    # Data structures
    "BrokerOrder",
    "BrokerPosition", 
    "BrokerBalance",
    "BrokerTrade",
    "MarketData",
    
    # Exceptions
    "BrokerError",
    "AuthenticationError",
    "OrderError", 
    "InsufficientFundsError",
    "SymbolNotFoundError",
    "RateLimitError",
    
    # Broker implementations
    "AngelOneBroker",
    "MockBroker",
    
    # Utility functions
    "register_broker",
    "get_broker_instance",
    "list_available_brokers", 
    "get_broker_capabilities",
    "health_check_all_brokers"
]


