"""
Redis Stream Market Data Consumer for Strategy Service
"""
import asyncio
import logging
import os
import json
from datetime import datetime
from typing import Dict, List, Optional, Callable, Any
import redis.asyncio as redis
from shared.models import MarketDataTick
from shared.timezone import get_ist_now, get_ist_timestamp

logger = logging.getLogger(__name__)

class MarketDataConsumer:
    """Redis Stream consumer for market data with auto-reconnect"""
    
    def __init__(self, redis_url: str, consumer_group: str = "strategy_consumers"):
        self.redis_url = redis_url
        self.consumer_group = consumer_group
        self.consumer_name = f"consumer_{os.getpid()}_{id(self)}"
        self.redis_client = None
        self.running = False
        self.tick_handler: Optional[Callable[[MarketDataTick], None]] = None
        self.market_data_buffer: Dict[str, List[MarketDataTick]] = {}
        self.max_buffer_size = 1000  # Keep last 1000 ticks per symbol
        
    async def connect(self):
        """Connect to Redis"""
        try:
            self.redis_client = redis.from_url(self.redis_url)
            await self.redis_client.ping()
            logger.info(f"✅ Redis connected for consumer {self.consumer_name}")
            return True
        except Exception as e:
            logger.error(f"❌ Failed to connect to Redis: {e}")
            return False
    
    async def disconnect(self):
        """Disconnect from Redis"""
        if self.redis_client:
            await self.redis_client.close()
            logger.info("✅ Redis disconnected")
    
    def set_tick_handler(self, handler: Callable[[MarketDataTick], None]):
        """Set the tick data handler"""
        self.tick_handler = handler
    
    async def start_consuming(self, symbols: List[str]):
        """Start consuming market data for given symbols"""
        if not self.redis_client:
            logger.error("❌ Not connected to Redis")
            return False
        
        self.running = True
        logger.info(f"🚀 Starting to consume market data for {len(symbols)} symbols: {symbols}")
        
        # Create consumer group for each symbol stream
        for symbol in symbols:
            stream_name = f"market_data_stream:{symbol}"
            try:
                # Create consumer group (ignore if already exists)
                await self.redis_client.xgroup_create(
                    stream_name, 
                    self.consumer_group, 
                    id="0", 
                    mkstream=True
                )
                logger.info(f"✅ Created consumer group for {stream_name}")
            except Exception as e:
                if "BUSYGROUP" in str(e):
                    logger.info(f"✅ Consumer group already exists for {stream_name}")
                else:
                    logger.error(f"❌ Error creating consumer group for {stream_name}: {e}")
        
        # Start consuming loop
        await self._consume_loop(symbols)
    
    async def _consume_loop(self, symbols: List[str]):
        """Main consumption loop"""
        while self.running:
            try:
                # Read from all symbol streams
                stream_names = [f"market_data_stream:{symbol}" for symbol in symbols]
                
                # Read new messages
                messages = await self.redis_client.xreadgroup(
                    self.consumer_group,
                    self.consumer_name,
                    {stream_name: ">" for stream_name in stream_names},
                    count=10,
                    block=1000  # Block for 1 second
                )
                
                for stream_name, stream_messages in messages:
                    for message_id, fields in stream_messages:
                        await self._process_message(stream_name, message_id, fields)
                        
            except Exception as e:
                logger.error(f"❌ Error in consume loop: {e}")
                await asyncio.sleep(5)  # Wait before retrying
    
    async def _process_message(self, stream_name: str, message_id: str, fields: Dict):
        """Process a market data message"""
        try:
            # Convert bytes to strings if needed
            processed_fields = {}
            for key, value in fields.items():
                if isinstance(key, bytes):
                    key = key.decode()
                if isinstance(value, bytes):
                    value = value.decode()
                processed_fields[key] = value
            
            # Parse the tick data
            tick = self._parse_tick_data(processed_fields)
            if not tick:
                return
            
            # Add to buffer
            symbol = tick.symbol
            if symbol not in self.market_data_buffer:
                self.market_data_buffer[symbol] = []
            
            self.market_data_buffer[symbol].append(tick)
            
            # Keep buffer size manageable
            if len(self.market_data_buffer[symbol]) > self.max_buffer_size:
                self.market_data_buffer[symbol] = self.market_data_buffer[symbol][-self.max_buffer_size:]
            
            # Call tick handler if set
            if self.tick_handler:
                try:
                    self.tick_handler(tick)
                except Exception as e:
                    logger.error(f"❌ Error in tick handler: {e}")
            
            # Acknowledge the message
            await self.redis_client.xack(stream_name, self.consumer_group, message_id)
            
        except Exception as e:
            logger.error(f"❌ Error processing message {message_id}: {e}")
    
    def _parse_tick_data(self, fields: Dict[str, str]) -> Optional[MarketDataTick]:
        """Parse tick data from Redis fields"""
        try:
            # Extract symbol from stream name
            symbol = fields.get('symbol', 'UNKNOWN')
            
            # Parse numeric fields
            ltp = float(fields.get('ltp', '0'))
            change = float(fields.get('change', '0'))
            change_percent = float(fields.get('change_percent', '0'))
            high = float(fields.get('high', '0'))
            low = float(fields.get('low', '0'))
            volume = int(fields.get('volume', '0'))
            bid = float(fields.get('bid', '0'))
            ask = float(fields.get('ask', '0'))
            open_price = float(fields.get('open', '0'))
            close = float(fields.get('close', '0'))
            
            # Parse timestamps
            timestamp_str = fields.get('timestamp', '')
            exchange_timestamp_str = fields.get('exchange_timestamp', '')
            
            try:
                timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
            except:
                timestamp = get_ist_now()
            
            try:
                exchange_timestamp = datetime.fromisoformat(exchange_timestamp_str.replace('Z', '+00:00'))
            except:
                exchange_timestamp = timestamp
            
            return MarketDataTick(
                symbol=symbol,
                token=fields.get('token', ''),
                ltp=ltp,
                change=change,
                change_percent=change_percent,
                high=high,
                low=low,
                volume=volume,
                bid=bid,
                ask=ask,
                open=open_price,
                close=close,
                timestamp=timestamp,
                exchange_timestamp=exchange_timestamp,
                raw_data=fields
            )
            
        except Exception as e:
            logger.error(f"❌ Error parsing tick data: {e}")
            return None
    
    def get_historical_buffer(self, symbol: str, periods: int = 100) -> List[MarketDataTick]:
        """Get historical market data from buffer"""
        if symbol not in self.market_data_buffer:
            return []
        
        buffer = self.market_data_buffer[symbol]
        return buffer[-periods:] if periods > 0 else buffer
    
    def get_latest_tick(self, symbol: str) -> Optional[MarketDataTick]:
        """Get the latest tick for a symbol"""
        buffer = self.get_historical_buffer(symbol, 1)
        return buffer[0] if buffer else None
    
    async def stop(self):
        """Stop consuming"""
        self.running = False
        logger.info("🛑 Stopped consuming market data")
