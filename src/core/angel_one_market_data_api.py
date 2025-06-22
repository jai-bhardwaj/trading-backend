"""
Angel One Market Data API
Uses MARKET_ANGEL_ONE credentials for global market data and instruments
Separate from user-specific order placement
"""

import os
import asyncio
import logging
import requests
from typing import Dict, List, Optional, Any
from datetime import datetime
import json

logger = logging.getLogger(__name__)

class AngelOneMarketDataAPI:
    """
    Global Angel One Market Data API
    Uses MARKET_ANGEL_ONE credentials for:
    - Instrument master data
    - Live market prices
    - Market status
    """
    
    def __init__(self):
        self.api_key = os.getenv('MARKET_ANGEL_ONE_API_KEY')
        self.secret_key = os.getenv('MARKET_ANGEL_ONE_SECRET_KEY')
        self.client_id = os.getenv('MARKET_ANGEL_ONE_CLIENT_ID')
        self.pin = os.getenv('MARKET_ANGEL_ONE_PIN')
        
        self.access_token = None
        self.feed_token = None
        self.is_connected = False
        
        logger.info("🌐 Angel One Market Data API initialized")
    
    async def connect(self) -> bool:
        """Connect to Angel One for market data"""
        
        if not all([self.api_key, self.secret_key, self.client_id, self.pin]):
            logger.warning("⚠️  MARKET_ANGEL_ONE credentials not found - using demo mode")
            return False
        
        try:
            login_url = "https://smartapi.angelbroking.com/rest/auth/angelbroking/user/v1/loginByPassword"
            
            headers = {
                'Content-Type': 'application/json',
                'Accept': 'application/json',
                'X-UserType': 'USER',
                'X-SourceID': 'WEB',
                'X-ClientLocalIP': '127.0.0.1',
                'X-ClientPublicIP': '127.0.0.1',
                'X-MACAddress': '00:00:00:00:00:00',
                'X-PrivateKey': self.api_key
            }
            
            payload = {
                "clientcode": self.client_id,
                "password": self.pin
            }
            
            logger.info("🔑 Connecting to Angel One Market Data API...")
            response = requests.post(login_url, json=payload, headers=headers, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                
                if data.get('status') and data.get('data'):
                    self.access_token = data['data'].get('jwtToken')
                    self.feed_token = data['data'].get('feedToken')
                    
                    if self.access_token:
                        self.is_connected = True
                        logger.info("✅ Angel One Market Data API connected successfully")
                        return True
                    
                logger.error(f"❌ Invalid response from Angel One: {data}")
                return False
            else:
                logger.error(f"❌ Angel One login failed: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Error connecting to Angel One Market Data API: {e}")
            return False
    
    async def get_instrument_master(self) -> List[Dict]:
        """Get complete instrument master from Angel One"""
        
        try:
            url = "https://margincalculator.angelbroking.com/OpenAPI_File/files/OpenAPIScripMaster.json"
            
            logger.info("📡 Fetching instrument master from Angel One...")
            response = requests.get(url, timeout=60)
            
            if response.status_code == 200:
                instruments = response.json()
                logger.info(f"✅ Fetched {len(instruments)} instruments from Angel One")
                return instruments
            else:
                logger.error(f"❌ Failed to fetch instruments: {response.status_code}")
                return []
                
        except Exception as e:
            logger.error(f"❌ Error fetching instrument master: {e}")
            return []
    
    async def get_live_prices(self, symbols: List[str]) -> Dict[str, Any]:
        """Get live market prices for symbols"""
        
        if not self.is_connected:
            logger.warning("⚠️  Not connected - returning demo prices")
            return self._get_demo_prices(symbols)
        
        try:
            headers = {
                'Authorization': f'Bearer {self.access_token}',
                'Content-Type': 'application/json',
                'Accept': 'application/json',
                'X-UserType': 'USER',
                'X-SourceID': 'WEB',
                'X-ClientLocalIP': '127.0.0.1',
                'X-ClientPublicIP': '127.0.0.1',
                'X-MACAddress': '00:00:00:00:00:00',
                'X-PrivateKey': self.api_key
            }
            
            market_data = {}
            
            for symbol in symbols:
                try:
                    url = "https://smartapi.angelbroking.com/rest/secure/angelbroking/order/v1/getLTP"
                    payload = {
                        "exchange": "NSE",
                        "tradingsymbol": symbol,
                        "symboltoken": str(hash(symbol) % 100000)
                    }
                    
                    response = requests.post(url, json=payload, headers=headers, timeout=10)
                    
                    if response.status_code == 200:
                        data = response.json()
                        if data.get('status') and data.get('data'):
                            ltp_data = data['data']
                            market_data[symbol] = {
                                'ltp': float(ltp_data.get('ltp', 0)),
                                'volume': int(ltp_data.get('volume', 0)),
                                'timestamp': datetime.now().isoformat()
                            }
                    
                except Exception as e:
                    logger.warning(f"⚠️  Error fetching price for {symbol}: {e}")
            
            return market_data
            
        except Exception as e:
            logger.error(f"❌ Error fetching live prices: {e}")
            return self._get_demo_prices(symbols)
    
    def _get_demo_prices(self, symbols: List[str]) -> Dict[str, Any]:
        """Generate demo prices for symbols"""
        
        market_data = {}
        base_prices = {
            'RELIANCE': 2500,
            'TCS': 3500,
            'INFY': 1600,
            'HDFCBANK': 1700,
            'ICICIBANK': 1100
        }
        
        for symbol in symbols:
            base_price = base_prices.get(symbol, 1000)
            
            # Add some random variation
            variation = (hash(symbol + str(datetime.now().minute)) % 20) - 10
            current_price = base_price + variation
            
            market_data[symbol] = {
                'ltp': float(current_price),
                'volume': 10000 + (hash(symbol) % 5000),
                'timestamp': datetime.now().isoformat(),
                'mode': 'demo'
            }
        
        return market_data
    
    def get_connection_status(self) -> Dict[str, Any]:
        """Get current connection status"""
        return {
            'connected': self.is_connected,
            'api_key': self.api_key[:10] + '...' if self.api_key else 'Not Set',
            'client_id': self.client_id if self.client_id else 'Not Set',
            'timestamp': datetime.now().isoformat()
        }

# Global market data API instance
_market_data_api = None

def get_market_data_api() -> AngelOneMarketDataAPI:
    """Get the global market data API instance"""
    global _market_data_api
    if _market_data_api is None:
        _market_data_api = AngelOneMarketDataAPI()
    return _market_data_api 