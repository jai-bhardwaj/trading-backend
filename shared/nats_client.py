"""
NATS Client - Consumer for market data ticks
"""

import asyncio
import logging
import json
import os
from typing import Dict, Callable, Optional
from datetime import datetime
from dataclasses import dataclass
import nats
from nats.js.api import ConsumerConfig, AckPolicy

logger = logging.getLogger(__name__)

# NATS configuration
NATS_URL = os.getenv("NATS_URL", "nats://nats:4222")
MARKET_DATA_STREAM = "MARKET_DATA"
MARKET_DATA_SUBJECT = "market.data.tick"

@dataclass
class MarketDataTick:
    """Market data tick structure"""
    symbol: str
    token: str
    ltp: float
    change: float
    change_percent: float
    high: float
    low: float
    volume: int
    bid: float
    ask: float
    timestamp: str
    exchange_timestamp: str
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'MarketDataTick':
        """Create MarketDataTick from dictionary"""
        return cls(
            symbol=data.get('symbol', ''),
            token=data.get('token', ''),
            ltp=float(data.get('ltp', 0)),
            change=float(data.get('change', 0)),
            change_percent=float(data.get('change_percent', 0)),
            high=float(data.get('high', 0)),
            low=float(data.get('low', 0)),
            volume=int(data.get('volume', 0)),
            bid=float(data.get('bid', 0)),
            ask=float(data.get('ask', 0)),
            timestamp=data.get('timestamp', ''),
            exchange_timestamp=data.get('exchange_timestamp', '')
        )

class NATSMarketDataConsumer:
    """NATS consumer for market data ticks"""
    
    def __init__(self, consumer_name: str = "trading-strategy"):
        self.consumer_name = consumer_name
        self.nats_client = None
        self.jetstream = None
        self.subscription = None
        self.running = False
        self.tick_handlers = []
        self.tick_count = 0
        self.symbols_filter = []  # Empty = all symbols
    
    async def connect(self):
        """Connect to NATS"""
        try:
            logger.info(f"Connecting to NATS at {NATS_URL}...")
            self.nats_client = await nats.connect(NATS_URL)
            self.jetstream = self.nats_client.jetstream()
            logger.info("✅ NATS connected")
            return True
        except Exception as e:
            logger.error(f"❌ Failed to connect to NATS: {e}")
            return False
    
    async def disconnect(self):
        """Disconnect from NATS"""
        try:
            self.running = False
            
            if self.subscription:
                await self.subscription.unsubscribe()
            
            if self.nats_client:
                await self.nats_client.close()
            
            logger.info("✅ NATS disconnected")
        except Exception as e:
            logger.error(f"Error disconnecting from NATS: {e}")
    
    def add_tick_handler(self, handler: Callable[[MarketDataTick], None]):
        """Add a tick handler function"""
        self.tick_handlers.append(handler)
    
    def set_symbols_filter(self, symbols: list):
        """Set symbols to filter (empty = all symbols)"""
        self.symbols_filter = symbols
    
    async def subscribe(self, symbols: Optional[list] = None):
        """Subscribe to market data ticks"""
        try:
            if symbols:
                self.symbols_filter = symbols
            
            # Determine subject to subscribe to
            if self.symbols_filter:
                # Subscribe to specific symbols
                subjects = [f"{MARKET_DATA_SUBJECT}.{symbol}" for symbol in self.symbols_filter]
                logger.info(f"Subscribing to symbols: {self.symbols_filter}")
            else:
                # Subscribe to all symbols
                subjects = [f"{MARKET_DATA_SUBJECT}.>"]
                logger.info("Subscribing to all symbols")
            
            # Create durable consumer
            for subject in subjects:
                subscription = await self.jetstream.subscribe(
                    subject,
                    durable=self.consumer_name,
                    config=ConsumerConfig(
                        ack_policy=AckPolicy.EXPLICIT,
                        max_deliver=3,
                    )
                )
                
                # Start message handler
                asyncio.create_task(self._handle_messages(subscription))
            
            self.running = True
            logger.info(f"✅ Subscribed to market data with consumer: {self.consumer_name}")
            
        except Exception as e:
            logger.error(f"Error subscribing to market data: {e}")
            import traceback
            logger.error(traceback.format_exc())
    
    async def _handle_messages(self, subscription):
        """Handle incoming messages"""
        try:
            async for msg in subscription.messages:
                try:
                    # Parse tick data
                    tick_data = json.loads(msg.data.decode())
                    tick = MarketDataTick.from_dict(tick_data)
                    
                    # Call all tick handlers
                    for handler in self.tick_handlers:
                        try:
                            # Support both sync and async handlers
                            if asyncio.iscoroutinefunction(handler):
                                await handler(tick)
                            else:
                                handler(tick)
                        except Exception as e:
                            logger.error(f"Error in tick handler: {e}")
                    
                    # Acknowledge message
                    await msg.ack()
                    
                    self.tick_count += 1
                    
                    if self.tick_count % 100 == 0:
                        logger.info(f"📊 Processed {self.tick_count} ticks from NATS")
                
                except Exception as e:
                    logger.error(f"Error handling message: {e}")
                    await msg.nak()
        
        except Exception as e:
            logger.error(f"Error in message handler: {e}")
            import traceback
            logger.error(traceback.format_exc())
    
    async def get_latest_tick(self, symbol: str) -> Optional[MarketDataTick]:
        """Get the latest tick for a symbol (one-off fetch)"""
        try:
            # Fetch from stream
            subject = f"{MARKET_DATA_SUBJECT}.{symbol}"
            
            # Get last message
            msgs = await self.jetstream.fetch(
                stream=MARKET_DATA_STREAM,
                subject=subject,
                max_msgs=1
            )
            
            if msgs:
                tick_data = json.loads(msgs[0].data.decode())
                return MarketDataTick.from_dict(tick_data)
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting latest tick: {e}")
            return None

def create_nats_consumer(consumer_name: str = "trading-strategy") -> NATSMarketDataConsumer:
    """Create a NATS market data consumer"""
    return NATSMarketDataConsumer(consumer_name)

