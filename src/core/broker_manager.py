"""
Lightweight Broker Manager
Efficient broker integration with minimal memory usage
"""

import asyncio
import logging
import time
import requests
import os
import pyotp
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from datetime import datetime

from .events import EventBus, Event, EventType
from .production_safety import get_production_safety_validator, TradingMode

logger = logging.getLogger(__name__)

@dataclass
class BrokerConfig:
    """Broker configuration"""
    broker_name: str = "ANGEL_ONE"
    api_key: Optional[str] = None
    secret_key: Optional[str] = None
    paper_trading: bool = True
    rate_limit_per_second: int = 10

class BrokerManager:
    """
    Lightweight broker manager
    Memory usage: ~20MB
    """
    
    def __init__(self, event_bus: EventBus, config):
        self.event_bus = event_bus
        self.config = config
        self.broker_config = BrokerConfig(paper_trading=config.enable_paper_trading)
        self.is_running = False
        
        # Production safety validator
        self.safety_validator = get_production_safety_validator()
        self.broker_connected = False
        self.intended_mode = TradingMode.LIVE if not config.enable_paper_trading else TradingMode.PAPER
        self.safety_validator.set_intended_mode(self.intended_mode)
        
        # Angel One session management
        self.access_token = None
        self.refresh_token = None
        self.feed_token = None
        self.client_id = None
        self.session_expires_at = None
        
        # Performance tracking
        self.orders_sent = 0
        self.orders_filled = 0
        self.orders_rejected = 0
        
        # Rate limiting
        self.last_order_time = 0
        self.rate_limit = 1.0 / self.broker_config.rate_limit_per_second
        
        # Setup event handlers
        self._setup_event_handlers()
    
    def _setup_event_handlers(self):
        """Setup event handlers"""
        self.event_bus.subscribe(EventType.ORDER_PLACED, self._handle_order_placed)
    
    async def start(self):
        """Start broker manager"""
        self.is_running = True
        logger.info(f"🏦 Broker Manager started (Paper Trading: {self.broker_config.paper_trading})")
        
        # Initialize broker connection
        await self._initialize_broker()
        
        # Start monitoring loop
        while self.is_running:
            try:
                await self._monitor_orders()
                await asyncio.sleep(1)
            except Exception as e:
                logger.error(f"❌ Broker monitoring error: {e}")
                await asyncio.sleep(5)
    
    async def stop(self):
        """Stop broker manager"""
        self.is_running = False
        logger.info(f"🏦 Broker Manager stopped. Orders sent: {self.orders_sent}")
    
    async def _initialize_broker(self):
        """Initialize broker connection with production safety validation"""
        if self.broker_config.paper_trading:
            logger.info("📝 Paper trading mode enabled")
            self.broker_connected = True  # Paper trading always "connected"
        else:
            logger.info("💰 Live trading mode enabled - Authenticating with Angel One...")
            auth_success = await self._authenticate_angel_one()
            self.broker_connected = auth_success
            
            # CRITICAL PRODUCTION SAFETY CHECK
            if not self.broker_connected and self.intended_mode == TradingMode.LIVE:
                logger.critical("🚨 BROKER CONNECTION FAILED IN PRODUCTION MODE")
                logger.critical("🚨 TRADING SYSTEM WILL BE DISABLED - NO FALLBACK TO PAPER TRADING")
                logger.critical("🚨 Manual intervention required to restore trading")
                
                # Send critical alert
                from src.core.critical_error_handler import get_critical_error_handler
                error_handler = get_critical_error_handler()
                
                broker_error = Exception("Live broker connection failed in production mode")
                context = {
                    'operation': 'broker_initialization',
                    'intended_mode': self.intended_mode.value,
                    'broker_connected': self.broker_connected,
                    'critical_failure': True
                }
                
                await error_handler.handle_error(broker_error, context)
    
    async def _authenticate_angel_one(self):
        """Authenticate with Angel One API"""
        try:
            # Get credentials from environment
            api_key = os.getenv('ANGEL_ONE_API_KEY', '')
            secret_key = os.getenv('ANGEL_ONE_SECRET_KEY', '') 
            client_id = os.getenv('ANGEL_ONE_CLIENT_ID', '')
            pin = os.getenv('ANGEL_ONE_PIN', '')
            totp_secret = os.getenv('ANGEL_ONE_TOTP_SECRET', '')
            
            if not all([api_key, secret_key, client_id, pin]):
                raise ValueError("Angel One credentials missing in environment")
            
            self.client_id = client_id
            
            # Login to Angel One
            login_url = "https://smartapi.angelbroking.com/rest/auth/angelbroking/user/v1/loginByPassword"
            
            headers = {
                'Content-Type': 'application/json',
                'Accept': 'application/json',
                'X-UserType': 'USER',
                'X-SourceID': 'WEB',
                'X-ClientLocalIP': '127.0.0.1',
                'X-ClientPublicIP': '127.0.0.1',
                'X-MACAddress': '00:00:00:00:00:00',
                'X-PrivateKey': api_key
            }
            
            payload = {
                "clientcode": client_id,
                "password": pin
            }
            
            # Generate TOTP if available
            if totp_secret:
                try:
                    totp = pyotp.TOTP(totp_secret)
                    payload["totp"] = totp.now()
                    logger.info("🔐 Using TOTP for authentication")
                except Exception as e:
                    logger.warning(f"⚠️ TOTP generation failed: {e}")
            
            logger.info("🔑 Authenticating with Angel One...")
            response = requests.post(login_url, json=payload, headers=headers, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                if data.get('status') and data.get('data'):
                    auth_data = data['data']
                    self.access_token = auth_data.get('jwtToken')
                    self.refresh_token = auth_data.get('refreshToken')
                    self.feed_token = auth_data.get('feedToken')
                    
                    logger.info("✅ Angel One authentication successful")
                    logger.info(f"🎯 Client ID: {client_id}")
                    return True
                else:
                    error_msg = data.get('message', 'Unknown error')
                    logger.error(f"❌ Angel One authentication failed: {error_msg}")
                    return False
            else:
                logger.error(f"❌ Angel One API error: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Angel One authentication error: {e}")
            return False
    
    async def _handle_order_placed(self, event: Event):
        """Handle order placement requests with critical error handling and production safety"""
        try:
            order_data = event.data
            
            # CRITICAL PRODUCTION SAFETY CHECK
            if not self.safety_validator.should_allow_trading(self.broker_connected):
                logger.critical("🚨 TRADING BLOCKED BY PRODUCTION SAFETY VALIDATOR")
                logger.critical(f"🚨 Intended mode: {self.intended_mode.value}, Broker connected: {self.broker_connected}")
                
                # Reject the order
                await self._publish_order_error(
                    order_data, 
                    "Trading blocked - broker connection failed in production mode"
                )
                return
            
            # Rate limiting
            current_time = time.time()
            if current_time - self.last_order_time < self.rate_limit:
                await asyncio.sleep(self.rate_limit)
            
            # Send order to broker with additional safety validation
            trading_mode = TradingMode.PAPER if self.broker_config.paper_trading else TradingMode.LIVE
            
            if not self.safety_validator.validate_trading_mode_safety(trading_mode, self.broker_connected):
                logger.critical("🚨 PRODUCTION SAFETY VIOLATION DETECTED")
                await self._publish_order_error(
                    order_data,
                    "Production safety violation - trading mode mismatch"
                )
                return
            
            # Execute order
            if self.broker_config.paper_trading:
                await self._execute_paper_order(order_data)
            else:
                await self._execute_live_order(order_data)
            
            self.last_order_time = time.time()
            self.orders_sent += 1
            
        except Exception as e:
            # Handle order execution errors through critical error handler
            from src.core.critical_error_handler import get_critical_error_handler
            error_handler = get_critical_error_handler()
            
            context = {
                'operation': 'order_execution',
                'order_id': order_data.get('order_id'),
                'symbol': order_data.get('symbol'),
                'user_id': order_data.get('user_id'),
                'order_value': order_data.get('price', 0) * order_data.get('quantity', 0),
                'affected_users': [order_data.get('user_id')] if order_data.get('user_id') else []
            }
            
            action = await error_handler.handle_error(e, context)
            
            logger.error(f"❌ Order execution error: {e} | Action: {action.value}")
            self.orders_rejected += 1
            
            # If critical error, additional handling might be needed by the caller
    
    async def _execute_paper_order(self, order_data: Dict[str, Any]):
        """Execute order in paper trading mode"""
        # Simulate broker processing delay
        await asyncio.sleep(0.1)
        
        # Simulate 95% success rate
        import random
        if random.random() < 0.95:
            # Order filled
            fill_price = order_data.get('price', 100.0) + random.uniform(-2, 2)  # Simulate slippage
            
            await self.event_bus.publish(Event(
                type=EventType.ORDER_FILLED,
                data={
                    'order_id': order_data['order_id'],
                    'broker_order_id': f"PAPER_{order_data['order_id']}",
                    'symbol': order_data['symbol'],
                    'side': order_data['side'],
                    'quantity': order_data['quantity'],
                    'fill_price': fill_price,
                    'filled_at': datetime.now().isoformat(),
                    'execution_type': 'PAPER'
                },
                source='broker_manager'
            ))
            
            self.orders_filled += 1
            logger.info(f"✅ Paper order filled: {order_data['symbol']} @ ₹{fill_price:.2f}")
        else:
            # Order rejected
            await self.event_bus.publish(Event(
                type=EventType.ORDER_REJECTED,
                data={
                    'order_id': order_data['order_id'],
                    'symbol': order_data['symbol'],
                    'reason': 'Simulated rejection',
                    'rejected_at': datetime.now().isoformat()
                },
                source='broker_manager'
            ))
            
            self.orders_rejected += 1
            logger.warning(f"❌ Paper order rejected: {order_data['symbol']}")
    
    async def _execute_live_order(self, order_data: Dict[str, Any]):
        """Execute order with real Angel One broker"""
        try:
            if not self.access_token:
                logger.error("❌ No active Angel One session for live order placement")
                await self._publish_order_error(order_data, "No active broker session")
                return
            
            # Place order with Angel One
            result = await self._place_angel_one_order(order_data)
            
            if result.get('success'):
                # Order placed successfully
                await self.event_bus.publish(Event(
                    type=EventType.ORDER_FILLED,
                    data={
                        'order_id': order_data['order_id'],
                        'broker_order_id': result.get('broker_order_id'),
                        'symbol': order_data['symbol'],
                        'side': order_data['side'],
                        'quantity': order_data['quantity'],
                        'fill_price': result.get('price'),
                        'filled_at': datetime.now().isoformat(),
                        'execution_type': 'LIVE'
                    },
                    source='broker_manager'
                ))
                
                self.orders_filled += 1
                logger.info(f"✅ Live order placed: {order_data['symbol']} @ ₹{result.get('price', 'Market')}")
            else:
                # Order failed
                await self._publish_order_error(order_data, result.get('error', 'Unknown error'))
                
        except Exception as e:
            logger.error(f"❌ Live order execution error: {e}")
            await self._publish_order_error(order_data, str(e))
    
    async def _place_angel_one_order(self, order_data: Dict[str, Any]) -> Dict[str, Any]:
        """Place order using Angel One API"""
        try:
            order_url = "https://smartapi.angelbroking.com/rest/secure/angelbroking/order/v1/placeOrder"
            
            headers = {
                'Content-Type': 'application/json',
                'Accept': 'application/json',
                'X-UserType': 'USER',
                'X-SourceID': 'WEB',
                'X-ClientLocalIP': '127.0.0.1',
                'X-ClientPublicIP': '127.0.0.1',
                'X-MACAddress': '00:00:00:00:00:00',
                'Authorization': f'Bearer {self.access_token}'
            }
            
            # Convert order data to Angel One format
            angel_order = {
                "variety": "NORMAL",
                "tradingsymbol": order_data['symbol'],
                "symboltoken": self._get_symbol_token(order_data['symbol']),
                "transactiontype": order_data['side'],  # BUY/SELL
                "exchange": order_data.get('exchange', 'NSE'),
                "ordertype": order_data.get('order_type', 'MARKET'),
                "producttype": order_data.get('product_type', 'INTRADAY'),
                "duration": order_data.get('duration', 'DAY'),
                "quantity": str(order_data['quantity']),
                "disclosedquantity": "0"
            }
            
            # Add price for limit orders
            if order_data.get('order_type') == 'LIMIT' and order_data.get('price'):
                angel_order["price"] = str(order_data['price'])
            
            # Add trigger price for stop loss orders
            if 'trigger_price' in order_data:
                angel_order["triggerprice"] = str(order_data['trigger_price'])
            
            logger.info(f"📋 Placing Angel One order: {order_data['symbol']} {order_data['side']} {order_data['quantity']}")
            
            response = requests.post(order_url, json=angel_order, headers=headers, timeout=30)
            
            if response.status_code == 200:
                result = response.json()
                if result.get('status') and result.get('data'):
                    order_id = result['data'].get('orderid')
                    return {
                        'success': True,
                        'broker_order_id': order_id,
                        'price': order_data.get('price', 'MARKET'),
                        'message': 'Order placed successfully'
                    }
                else:
                    error_msg = result.get('message', 'Unknown Angel One error')
                    logger.error(f"❌ Angel One order error: {error_msg}")
                    return {'success': False, 'error': error_msg}
            else:
                error_msg = f"HTTP {response.status_code}: {response.text}"
                logger.error(f"❌ Angel One API error: {error_msg}")
                return {'success': False, 'error': error_msg}
                
        except Exception as e:
            logger.error(f"❌ Error placing Angel One order: {e}")
            return {'success': False, 'error': str(e)}
    
    def _get_symbol_token(self, symbol: str) -> str:
        """Get Angel One symbol token - simplified for now"""
        # In production, this should fetch from Angel One instruments API
        # For now, return a placeholder token
        symbol_tokens = {
            'RELIANCE': '2885',
            'TCS': '11536', 
            'INFY': '1594',
            'HDFC': '1333',
            'ICICIBANK': '4963',
            'SBIN': '3045',
            'ITC': '424',
            'HDFCBANK': '1333',
            'LT': '17818',
            'AXISBANK': '5900'
        }
        return symbol_tokens.get(symbol, '1')  # Default token
    
    async def _publish_order_error(self, order_data: Dict[str, Any], error_msg: str):
        """Publish order error event"""
        await self.event_bus.publish(Event(
            type=EventType.ORDER_REJECTED,
            data={
                'order_id': order_data['order_id'],
                'symbol': order_data['symbol'],
                'reason': error_msg,
                'rejected_at': datetime.now().isoformat()
            },
            source='broker_manager'
        ))
        
        self.orders_rejected += 1
        logger.error(f"❌ Order rejected: {order_data['symbol']} - {error_msg}")
    
    async def _monitor_orders(self):
        """Monitor order status"""
        # Placeholder for order status monitoring
        pass
    
    def get_stats(self) -> Dict[str, Any]:
        """Get broker statistics"""
        return {
            'orders_sent': self.orders_sent,
            'orders_filled': self.orders_filled,
            'orders_rejected': self.orders_rejected,
            'broker_connected': self.broker_connected,
            'paper_trading': self.broker_config.paper_trading,
            'rate_limit_per_second': self.broker_config.rate_limit_per_second
        }
    
    async def get_live_market_data(self, symbols: List[str] = None) -> Dict[str, Any]:
        """Get live market data from broker"""
        try:
            if self.broker_config.paper_trading:
                # Return simulated market data for paper trading
                return self._generate_simulated_market_data(symbols)
            else:
                # Return live market data from Angel One
                return await self._get_angel_one_market_data(symbols)
        except Exception as e:
            logger.error(f"❌ Error getting market data: {e}")
            return {}
    
    def _generate_simulated_market_data(self, symbols: List[str] = None) -> Dict[str, Any]:
        """Generate simulated market data for testing"""
        import random
        from datetime import datetime
        
        # Use provided symbols or default ones
        if symbols is None:
            symbols = ['RELIANCE', 'TCS', 'INFY', 'HDFCBANK', 'ICICIBANK']
        
        market_data = {}
        
        base_prices = {
            'RELIANCE': 2450.75,
            'TCS': 3890.50, 
            'INFY': 1756.30,
            'HDFCBANK': 1642.80,
            'ICICIBANK': 1198.45
        }
        
        for symbol in symbols:
            base_price = base_prices.get(symbol, 1000.0)  # Default price if symbol not found
            volatility = random.uniform(-0.02, 0.02)  # 2% max volatility
            current_price = base_price * (1 + volatility)
            
            market_data[symbol] = {
                'symbol': symbol,
                'price': round(current_price, 2),
                'high': round(current_price * 1.01, 2),
                'low': round(current_price * 0.99, 2),
                'volume': random.randint(100000, 1000000),
                'timestamp': datetime.now().isoformat(),
                'change': round(volatility * 100, 3),
                'change_percent': round(volatility * 100, 3)
            }
        
        return market_data
    
    async def _get_angel_one_market_data(self, symbols: List[str] = None) -> Dict[str, Any]:
        """Get live market data from Angel One API"""
        try:
            if not self.access_token:
                logger.warning("⚠️ No Angel One access token - returning empty market data")
                return {}
            
            # Angel One market data API endpoint
            url = "https://smartapi.angelbroking.com/rest/secure/angelbroking/market/v1/quote/"
            
            headers = {
                'Authorization': f'Bearer {self.access_token}',
                'Content-Type': 'application/json',
                'Accept': 'application/json',
                'X-UserType': 'USER',
                'X-SourceID': 'WEB',
                'X-ClientLocalIP': '127.0.0.1',
                'X-ClientPublicIP': '127.0.0.1'
            }
            
            # Get quotes for popular stocks
            if symbols is None:
                symbols = ['3045', '11536', '1594', '1333', '4963']  # RELIANCE, TCS, INFY, HDFC, ICICI tokens
            
            market_data = {}
            
            for token in symbols:
                try:
                    payload = {
                        "mode": "FULL",
                        "exchangeTokens": {
                            "NSE": [token]
                        }
                    }
                    
                    response = requests.post(url, json=payload, headers=headers, timeout=10)
                    
                    if response.status_code == 200:
                        data = response.json()
                        if data.get('status') and data.get('data'):
                            quote_data = data['data']['fetched'][0]
                            symbol_name = quote_data.get('tradingSymbol', f'TOKEN_{token}')
                            
                            market_data[symbol_name] = {
                                'symbol': symbol_name,
                                'price': float(quote_data.get('ltp', 0)),
                                'high': float(quote_data.get('high', 0)),
                                'low': float(quote_data.get('low', 0)),
                                'volume': int(quote_data.get('volume', 0)),
                                'timestamp': datetime.now().isoformat(),
                                'change': float(quote_data.get('change', 0)),
                                'change_percent': float(quote_data.get('pChange', 0))
                            }
                    
                    await asyncio.sleep(0.1)  # Rate limiting
                    
                except Exception as e:
                    logger.warning(f"⚠️ Error getting quote for token {token}: {e}")
            
            return market_data
            
        except Exception as e:
            logger.error(f"❌ Error getting Angel One market data: {e}")
            return {} 