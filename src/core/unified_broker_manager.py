"""
Unified Broker Manager
Uses new Angel One architecture with separated market data and order APIs
"""

import os
import asyncio
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime

from .angel_one_market_data_api import get_market_data_api
from .angel_one_order_api import place_user_order, get_user_order_api

logger = logging.getLogger(__name__)

class UnifiedBrokerManager:
    """
    Unified broker manager implementing the new architecture:
    - Global market data API for instruments and prices
    - User-specific order APIs for trading
    """
    
    def __init__(self):
        self.market_data_api = get_market_data_api()
        self.user_order_apis = {}
        self.is_initialized = False
        
        logger.info("🚀 Unified Broker Manager initialized")
    
    async def initialize(self):
        """Initialize the broker manager"""
        
        logger.info("🔧 Initializing Unified Broker Manager...")
        
        # Initialize market data API
        try:
            connected = await self.market_data_api.connect()
            if connected:
                logger.info("✅ Market data API connected successfully")
            else:
                logger.warning("⚠️  Market data API in demo mode")
        except Exception as e:
            logger.warning(f"⚠️  Market data API initialization failed: {e}")
        
        self.is_initialized = True
        logger.info("✅ Unified Broker Manager initialized successfully")
        
        return True
    
    async def get_instruments(self) -> List[Dict]:
        """Get instrument master data"""
        
        try:
            instruments = await self.market_data_api.get_instrument_master()
            logger.info(f"📊 Retrieved {len(instruments)} instruments")
            return instruments
        except Exception as e:
            logger.error(f"❌ Error getting instruments: {e}")
            return []
    
    async def get_market_data(self, symbols: List[str]) -> Dict[str, Any]:
        """Get live market data for symbols"""
        
        try:
            market_data = await self.market_data_api.get_live_prices(symbols)
            logger.debug(f"📈 Retrieved market data for {len(market_data)} symbols")
            return market_data
        except Exception as e:
            logger.error(f"❌ Error getting market data: {e}")
            return {}
    
    async def place_order(self, user_id: str, order_data: Dict[str, Any]) -> Dict[str, Any]:
        """Place an order for a specific user"""
        
        try:
            # Get user credentials from database (for now, using demo credentials)
            user_credentials = await self._get_user_credentials(user_id)
            
            if not user_credentials:
                return {
                    'status': 'error',
                    'message': f'No credentials found for user {user_id}',
                    'order_id': None
                }
            
            # Place order using user-specific API
            result = await place_user_order(user_id, user_credentials, order_data)
            
            logger.info(f"📝 Order result for user {user_id}: {result['status']}")
            return result
            
        except Exception as e:
            logger.error(f"❌ Error placing order for user {user_id}: {e}")
            return {
                'status': 'error',
                'message': str(e),
                'order_id': None
            }
    
    async def get_user_positions(self, user_id: str) -> List[Dict[str, Any]]:
        """Get positions for a specific user"""
        
        try:
            if user_id not in self.user_order_apis:
                return []
            
            order_api = self.user_order_apis[user_id]
            positions = await order_api.get_positions()
            return positions
            
        except Exception as e:
            logger.error(f"❌ Error getting positions for user {user_id}: {e}")
            return []
    
    async def get_order_status(self, user_id: str, order_id: str) -> Dict[str, Any]:
        """Get status of a specific order"""
        
        try:
            if user_id not in self.user_order_apis:
                return {'status': 'error', 'message': 'User not connected'}
            
            order_api = self.user_order_apis[user_id]
            status = await order_api.get_order_status(order_id)
            return status
            
        except Exception as e:
            logger.error(f"❌ Error getting order status for user {user_id}: {e}")
            return {'status': 'error', 'message': str(e)}
    
    async def _get_user_credentials(self, user_id: str) -> Optional[Dict[str, str]]:
        """Get user credentials from database"""
        
        # For now, using the same credentials for demo
        # In production, this would fetch from database
        demo_credentials = {
            'api_key': os.getenv('MARKET_ANGEL_ONE_API_KEY', 'demo_key'),
            'secret_key': os.getenv('MARKET_ANGEL_ONE_SECRET_KEY', 'demo_secret'),
            'client_id': os.getenv('MARKET_ANGEL_ONE_CLIENT_ID', 'demo_client'),
            'pin': os.getenv('MARKET_ANGEL_ONE_PIN', '0000')
        }
        
        logger.info(f"🔐 Retrieved credentials for user {user_id}")
        return demo_credentials
    
    def get_system_status(self) -> Dict[str, Any]:
        """Get overall system status"""
        
        market_status = self.market_data_api.get_connection_status()
        
        return {
            'initialized': self.is_initialized,
            'market_data_connected': market_status['connected'],
            'active_users': len(self.user_order_apis),
            'timestamp': datetime.now().isoformat(),
            'architecture': 'separated_apis'
        }

# Global unified broker manager
_unified_broker_manager = None

def get_unified_broker_manager() -> UnifiedBrokerManager:
    """Get the global unified broker manager"""
    global _unified_broker_manager
    if _unified_broker_manager is None:
        _unified_broker_manager = UnifiedBrokerManager()
    return _unified_broker_manager 