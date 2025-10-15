"""
Signal Publisher for Strategy Service
"""
import asyncio
import json
import logging
from datetime import datetime
from typing import Dict, Any
import redis.asyncio as redis
from shared.models import TradingSignal, SignalType

logger = logging.getLogger(__name__)

class SignalPublisher:
    """Redis publisher for trading signals"""
    
    def __init__(self, redis_url: str, signal_channel: str = "strategy_signals"):
        self.redis_url = redis_url
        self.signal_channel = signal_channel
        self.redis_client = None
        self.signals_published = 0
        
    async def connect(self):
        """Connect to Redis"""
        try:
            self.redis_client = redis.from_url(self.redis_url)
            await self.redis_client.ping()
            logger.info(f"✅ Redis connected for signal publisher")
            return True
        except Exception as e:
            logger.error(f"❌ Failed to connect to Redis for publishing: {e}")
            return False
    
    async def disconnect(self):
        """Disconnect from Redis"""
        if self.redis_client:
            await self.redis_client.close()
            logger.info("✅ Redis disconnected for signal publisher")
    
    async def publish_signal(self, signal: TradingSignal):
        """Publish a trading signal to Redis"""
        try:
            if not self.redis_client:
                logger.error("❌ Not connected to Redis")
                return False
            
            # Convert signal to dict
            signal_dict = {
                "strategy_id": signal.strategy_id,
                "symbol": signal.symbol,
                "signal_type": signal.signal_type.value,
                "confidence": signal.confidence,
                "price": signal.price,
                "quantity": signal.quantity,
                "timestamp": signal.timestamp.isoformat(),
                "metadata": signal.metadata
            }
            
            # Publish to Redis channel
            await self.redis_client.publish(
                self.signal_channel,
                json.dumps(signal_dict, default=str)
            )
            
            self.signals_published += 1
            logger.info(f"📊 Published signal: {signal.symbol} {signal.signal_type.value} @ {signal.price} (confidence: {signal.confidence:.2f})")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Error publishing signal: {e}")
            return False
    
    async def publish_signal_dict(self, signal_dict: Dict[str, Any]):
        """Publish a signal from dictionary format"""
        try:
            if not self.redis_client:
                logger.error("❌ Not connected to Redis")
                return False
            
            # Ensure timestamp is ISO format
            if 'timestamp' in signal_dict and isinstance(signal_dict['timestamp'], datetime):
                signal_dict['timestamp'] = signal_dict['timestamp'].isoformat()
            
            # Publish to Redis channel
            await self.redis_client.publish(
                self.signal_channel,
                json.dumps(signal_dict, default=str)
            )
            
            self.signals_published += 1
            logger.info(f"📊 Published signal: {signal_dict.get('symbol', 'UNKNOWN')} {signal_dict.get('signal_type', 'UNKNOWN')}")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Error publishing signal dict: {e}")
            return False
    
    def get_stats(self) -> Dict[str, Any]:
        """Get publisher statistics"""
        return {
            "signals_published": self.signals_published,
            "signal_channel": self.signal_channel,
            "redis_connected": self.redis_client is not None
        }
