#!/usr/bin/env python3
"""
Simple Redis Stream Consumer for Market Data
Runs inside Docker container to consume ticks from Redis streams
"""

import asyncio
import logging
import os
import sys
from datetime import datetime
from typing import Dict, List, Optional
import redis.asyncio as redis
import redis.exceptions

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Redis configuration
REDIS_URL = "redis://trading-redis:6379"
MARKET_DATA_STREAM_PREFIX = "market_data_stream"

class SimpleMarketDataConsumer:
    """Simple consumer for market data from Redis streams"""
    
    def __init__(self):
        self.redis_client = None
        self.running = False
        self.consumer_group = "market_data_consumers_live"
        self.consumer_name = f"consumer_{os.getpid()}"
        self.tick_count = 0
        
    async def start(self):
        """Start the consumer"""
        try:
            logger.info("🚀 Starting Simple Market Data Consumer...")
            
            # Connect to Redis
            logger.info(f"Connecting to Redis at {REDIS_URL}...")
            self.redis_client = redis.from_url(REDIS_URL)
            ping_result = self.redis_client.ping()
            logger.info("✅ Redis connected")
            
            # Set running flag
            self.running = True
            
            # Start consuming
            await self.start_consuming()
            
        except Exception as e:
            logger.error(f"❌ Failed to start consumer: {e}")
            self.running = False
            raise
    
    async def start_consuming(self):
        """Start consuming from all market data streams"""
        try:
            logger.info("📡 Starting to consume market data streams...")
            
            while self.running:
                try:
                    # Get all market data streams
                    streams = await self.get_market_data_streams()
                    
                    if not streams:
                        logger.warning("No market data streams found, waiting...")
                        await asyncio.sleep(5)
                        continue
                    
                    # Ensure consumer groups exist
                    await self.ensure_consumer_groups(streams)
                    
                    # Consume from streams
                    await self.consume_from_streams(streams)
                    
                except Exception as e:
                    logger.error(f"Error in consumption loop: {e}")
                    await asyncio.sleep(5)
                    
        except Exception as e:
            logger.error(f"Error in start_consuming: {e}")
            raise
    
    async def get_market_data_streams(self) -> List[str]:
        """Get all market data streams"""
        try:
            # Get all keys matching market_data_stream:*
            keys = self.redis_client.keys(f"{MARKET_DATA_STREAM_PREFIX}:*")
            return [key.decode() if isinstance(key, bytes) else key for key in keys]
        except Exception as e:
            logger.error(f"Error getting streams: {e}")
            return []
    
    async def ensure_consumer_groups(self, streams: List[str]):
        """Ensure consumer groups exist for all streams"""
        for stream in streams:
            try:
                # Try to create consumer group
                self.redis_client.xgroup_create(
                    stream, 
                    self.consumer_group, 
                    id='0', 
                    mkstream=True
                )
                logger.debug(f"Created consumer group for {stream}")
            except redis.exceptions.ResponseError as e:
                if "BUSYGROUP" in str(e):
                    logger.debug(f"Consumer group already exists for {stream}")
                else:
                    logger.error(f"Error creating consumer group for {stream}: {e}")
    
    async def consume_from_streams(self, streams: List[str]):
        """Consume messages from all streams"""
        try:
            # Prepare stream dictionary for XREADGROUP
            stream_dict = {}
            for stream in streams:
                stream_dict[stream] = '>'
            
            # Read from all streams
            messages = self.redis_client.xreadgroup(
                self.consumer_group,
                self.consumer_name,
                stream_dict,
                count=10,  # Read up to 10 messages at a time
                block=1000  # Block for 1 second if no messages
            )
            
            if messages:
                for stream, stream_messages in messages:
                    for message_id, fields in stream_messages:
                        await self.process_tick(stream, message_id, fields)
            
        except Exception as e:
            logger.error(f"Error consuming from streams: {e}")
            raise
    
    async def process_tick(self, stream: str, message_id: str, fields: Dict):
        """Process a tick message"""
        try:
            # Convert bytes to strings if needed
            processed_fields = {}
            for key, value in fields.items():
                if isinstance(key, bytes):
                    key = key.decode()
                if isinstance(value, bytes):
                    value = value.decode()
                processed_fields[key] = value
            
            # Extract tick data
            symbol = processed_fields.get('symbol', 'UNKNOWN')
            ltp = processed_fields.get('ltp', '0')
            change = processed_fields.get('change', '0')
            change_percent = processed_fields.get('change_percent', '0')
            volume = processed_fields.get('volume', '0')
            bid = processed_fields.get('bid', '0')
            ask = processed_fields.get('ask', '0')
            high = processed_fields.get('high', '0')
            low = processed_fields.get('low', '0')
            timestamp = processed_fields.get('timestamp', '')
            
            # Log the tick
            logger.info(f"📊 TICK RECEIVED - Symbol: {symbol} | LTP: ₹{ltp} | Change: {change} ({change_percent}%) | Volume: {volume} | Bid: ₹{bid} | Ask: ₹{ask} | High: ₹{high} | Low: ₹{low} | Timestamp: {timestamp} | Message ID: {message_id}")
            
            # Acknowledge the message
            self.redis_client.xack(stream, self.consumer_group, message_id)
            
            # Update stats
            self.tick_count += 1
            
            if self.tick_count % 10 == 0:
                logger.info(f"📈 Processed {self.tick_count} ticks total")
            
        except Exception as e:
            logger.error(f"Error processing tick: {e}")
    
    async def stop(self):
        """Stop the consumer"""
        try:
            self.running = False
            if self.redis_client:
                self.redis_client.close()
            logger.info("✅ Consumer stopped successfully")
        except Exception as e:
            logger.error(f"Error stopping consumer: {e}")

async def main():
    """Main function"""
    logger.info("Simple Market Data Stream Consumer")
    logger.info("=" * 50)
    
    consumer = SimpleMarketDataConsumer()
    
    try:
        await consumer.start()
    except KeyboardInterrupt:
        logger.info("🛑 Received interrupt signal (Ctrl+C), stopping consumer...")
    except Exception as e:
        logger.error(f"❌ Consumer failed with error: {e}")
        import traceback
        logger.error(traceback.format_exc())
    finally:
        logger.info("🔄 Shutting down consumer...")
        await consumer.stop()
        logger.info("✅ Consumer shutdown complete")

if __name__ == "__main__":
    print("Simple Market Data Stream Consumer")
    print("=" * 40)
    print("This consumer will log every tick received from Redis streams")
    print("Press Ctrl+C to stop the consumer")
    print("=" * 40)
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Consumer stopped by user")
    except Exception as e:
        print(f"❌ Failed to start consumer: {e}")
        sys.exit(1)
