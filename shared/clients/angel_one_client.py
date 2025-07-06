"""
Angel One API Client - Real broker integration for live trading
"""

import asyncio
import logging
import json
import time
import hashlib
import hmac
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import httpx
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)

class OrderType(Enum):
    MARKET = "MARKET"
    LIMIT = "LIMIT"
    STOP_LOSS = "STOP_LOSS"
    STOP_LOSS_MARKET = "STOP_LOSS_MARKET"

class OrderSide(Enum):
    BUY = "BUY"
    SELL = "SELL"

class OrderStatus(Enum):
    PENDING = "PENDING"
    PLACED = "PLACED"
    FILLED = "FILLED"
    REJECTED = "REJECTED"
    CANCELLED = "CANCELLED"

@dataclass
class AngelOneConfig:
    """Angel One API configuration"""
    api_key: str
    client_id: str
    client_secret: str
    access_token: str = ""
    refresh_token: str = ""
    base_url: str = "https://apiconnect.angelbroking.com"
    feed_url: str = "https://feed.angelbroking.com"
    timeout: int = 30

class AngelOneClient:
    """Real Angel One API client for live trading"""
    
    def __init__(self, config: AngelOneConfig):
        self.config = config
        self.session = None
        self.access_token = config.access_token
        self.refresh_token = config.refresh_token
        self.token_expiry = None
        
    async def initialize(self):
        """Initialize the client and authenticate"""
        try:
            # Create session
            self.session = httpx.AsyncClient(
                timeout=self.config.timeout,
                headers={
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                    "User-Agent": "PinnacleTrading/1.0"
                }
            )
            
            # Authenticate if no token
            if not self.access_token:
                await self.authenticate()
            
            logger.info("✅ Angel One client initialized successfully")
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize Angel One client: {e}")
            raise
    
    async def authenticate(self):
        """Authenticate with Angel One API"""
        try:
            # Generate login payload
            login_payload = {
                "clientcode": self.config.client_id,
                "password": self.config.client_secret,
                "totp": self._generate_totp()  # You'll need to implement TOTP
            }
            
            response = await self.session.post(
                f"{self.config.base_url}/rest/auth/angelbroking/user/v1/loginByPassword",
                json=login_payload
            )
            
            if response.status_code == 200:
                data = response.json()
                self.access_token = data.get("data", {}).get("jwtToken", "")
                self.refresh_token = data.get("data", {}).get("refreshToken", "")
                self.token_expiry = datetime.utcnow() + timedelta(hours=24)
                
                # Update session headers
                self.session.headers["Authorization"] = f"Bearer {self.access_token}"
                
                logger.info("✅ Angel One authentication successful")
                return True
            else:
                logger.error(f"❌ Authentication failed: {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Authentication error: {e}")
            return False
    
    async def refresh_auth_token(self):
        """Refresh authentication token"""
        try:
            refresh_payload = {
                "refreshToken": self.refresh_token
            }
            
            response = await self.session.post(
                f"{self.config.base_url}/rest/auth/angelbroking/jwt/v1/generateTokens",
                json=refresh_payload
            )
            
            if response.status_code == 200:
                data = response.json()
                self.access_token = data.get("data", {}).get("jwtToken", "")
                self.refresh_token = data.get("data", {}).get("refreshToken", "")
                self.token_expiry = datetime.utcnow() + timedelta(hours=24)
                
                self.session.headers["Authorization"] = f"Bearer {self.access_token}"
                logger.info("✅ Token refreshed successfully")
                return True
            else:
                logger.error(f"❌ Token refresh failed: {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Token refresh error: {e}")
            return False
    
    async def get_user_profile(self) -> Optional[Dict]:
        """Get user profile and account details"""
        try:
            response = await self.session.get(
                f"{self.config.base_url}/rest/secure/angelbroking/user/v1/getProfile"
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"❌ Failed to get profile: {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"❌ Profile fetch error: {e}")
            return None
    
    async def get_holdings(self) -> List[Dict]:
        """Get current holdings"""
        try:
            response = await self.session.get(
                f"{self.config.base_url}/rest/secure/angelbroking/order/v1/getHoldings"
            )
            
            if response.status_code == 200:
                data = response.json()
                return data.get("data", [])
            else:
                logger.error(f"❌ Failed to get holdings: {response.status_code}")
                return []
                
        except Exception as e:
            logger.error(f"❌ Holdings fetch error: {e}")
            return []
    
    async def get_market_data(self, symbols: List[str]) -> Dict[str, Dict]:
        """Get real-time market data for symbols"""
        try:
            # Convert symbols to Angel One format
            formatted_symbols = []
            for symbol in symbols:
                formatted_symbols.append({
                    "exchangeType": 1,  # NSE
                    "tradingSymbol": symbol,
                    "symbolToken": self._get_symbol_token(symbol)
                })
            
            payload = {
                "mode": "FULL",
                "exchangeTokens": formatted_symbols
            }
            
            response = await self.session.post(
                f"{self.config.feed_url}/rest/secure/angelbroking/order/v1/getQuotes",
                json=payload
            )
            
            if response.status_code == 200:
                data = response.json()
                return self._parse_market_data(data.get("data", {}))
            else:
                logger.error(f"❌ Failed to get market data: {response.status_code}")
                return {}
                
        except Exception as e:
            logger.error(f"❌ Market data fetch error: {e}")
            return {}
    
    async def place_order(self, order_data: Dict) -> Dict[str, Any]:
        """Place a real order with Angel One"""
        try:
            # Validate order data
            if not self._validate_order_data(order_data):
                return {
                    "status": "error",
                    "error": "Invalid order data",
                    "message": "Order validation failed"
                }
            
            # Prepare order payload
            order_payload = {
                "variety": "NORMAL",
                "tradingsymbol": order_data["symbol"],
                "symboltoken": self._get_symbol_token(order_data["symbol"]),
                "transactiontype": order_data["side"],
                "exchange": "NSE",
                "ordertype": order_data["order_type"],
                "producttype": "INTRADAY",
                "duration": "DAY",
                "price": order_data.get("price", 0),
                "squareoff": "0",
                "stoploss": "0",
                "quantity": order_data["quantity"]
            }
            
            response = await self.session.post(
                f"{self.config.base_url}/rest/secure/angelbroking/order/v1/placeOrder",
                json=order_payload
            )
            
            if response.status_code == 200:
                data = response.json()
                order_id = data.get("data", {}).get("orderid", "")
                
                logger.info(f"✅ Order placed successfully: {order_id}")
                return {
                    "status": "success",
                    "broker_order_id": order_id,
                    "message": "Order placed successfully"
                }
            else:
                error_msg = response.json().get("message", "Unknown error")
                logger.error(f"❌ Order placement failed: {error_msg}")
                return {
                    "status": "error",
                    "error": error_msg,
                    "message": "Order placement failed"
                }
                
        except Exception as e:
            logger.error(f"❌ Order placement error: {e}")
            return {
                "status": "error",
                "error": str(e),
                "message": "Order placement failed"
            }
    
    async def get_order_status(self, order_id: str) -> Dict[str, Any]:
        """Get order status"""
        try:
            response = await self.session.get(
                f"{self.config.base_url}/rest/secure/angelbroking/order/v1/orderBook"
            )
            
            if response.status_code == 200:
                data = response.json()
                orders = data.get("data", [])
                
                for order in orders:
                    if order.get("orderid") == order_id:
                        return {
                            "status": "success",
                            "order_status": order.get("orderstatus"),
                            "filled_quantity": order.get("filledquantity", 0),
                            "filled_price": order.get("averageprice", 0),
                            "order_details": order
                        }
                
                return {
                    "status": "error",
                    "error": "Order not found",
                    "message": "Order not found in order book"
                }
            else:
                return {
                    "status": "error",
                    "error": f"Failed to get order status: {response.status_code}",
                    "message": "Failed to fetch order status"
                }
                
        except Exception as e:
            logger.error(f"❌ Order status fetch error: {e}")
            return {
                "status": "error",
                "error": str(e),
                "message": "Failed to fetch order status"
            }
    
    async def cancel_order(self, order_id: str) -> Dict[str, Any]:
        """Cancel an order"""
        try:
            cancel_payload = {
                "variety": "NORMAL",
                "orderid": order_id
            }
            
            response = await self.session.post(
                f"{self.config.base_url}/rest/secure/angelbroking/order/v1/cancelOrder",
                json=cancel_payload
            )
            
            if response.status_code == 200:
                logger.info(f"✅ Order cancelled successfully: {order_id}")
                return {
                    "status": "success",
                    "message": "Order cancelled successfully"
                }
            else:
                error_msg = response.json().get("message", "Unknown error")
                logger.error(f"❌ Order cancellation failed: {error_msg}")
                return {
                    "status": "error",
                    "error": error_msg,
                    "message": "Order cancellation failed"
                }
                
        except Exception as e:
            logger.error(f"❌ Order cancellation error: {e}")
            return {
                "status": "error",
                "error": str(e),
                "message": "Order cancellation failed"
            }
    
    def _validate_order_data(self, order_data: Dict) -> bool:
        """Validate order data"""
        required_fields = ["symbol", "side", "order_type", "quantity"]
        
        for field in required_fields:
            if field not in order_data:
                return False
        
        if order_data["quantity"] <= 0:
            return False
        
        if order_data["side"] not in ["BUY", "SELL"]:
            return False
        
        if order_data["order_type"] not in ["MARKET", "LIMIT", "STOP_LOSS"]:
            return False
        
        return True
    
    def _get_symbol_token(self, symbol: str) -> str:
        """Get symbol token for Angel One API"""
        # This is a simplified mapping - in production, you'd have a proper symbol mapping
        symbol_mapping = {
            "RELIANCE": "2885",
            "TCS": "11536",
            "INFY": "1594",
            "HDFC": "1330",
            "ICICIBANK": "4963"
        }
        return symbol_mapping.get(symbol, "0")
    
    def _parse_market_data(self, data: Dict) -> Dict[str, Dict]:
        """Parse market data from Angel One response"""
        result = {}
        
        for item in data.get("fetched", []):
            symbol = item.get("tradingSymbol", "")
            result[symbol] = {
                "symbol": symbol,
                "ltp": item.get("ltp", 0),
                "change": item.get("netChange", 0),
                "change_percent": item.get("pChange", 0),
                "high": item.get("high", 0),
                "low": item.get("low", 0),
                "volume": item.get("totalTradedVolume", 0),
                "timestamp": datetime.utcnow().isoformat()
            }
        
        return result
    
    def _generate_totp(self) -> str:
        """Generate TOTP for authentication"""
        # This is a placeholder - you'll need to implement proper TOTP generation
        # using a library like pyotp
        return "123456"
    
    async def close(self):
        """Close the client session"""
        if self.session:
            await self.session.aclose() 