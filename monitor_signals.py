#!/usr/bin/env python3
"""
Monitor Redis signals in real-time
"""

import asyncio
import json
import logging
import redis.asyncio as redis
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def monitor_signals():
    """Monitor Redis signals in real-time"""
    
    redis_url = "redis://localhost:6379/2"
    redis_client = redis.from_url(redis_url)
    
    try:
        await redis_client.ping()
        logger.info("✅ Connected to Redis")
        
        pubsub = redis_client.pubsub()
        await pubsub.subscribe("strategy_signals")
        logger.info("✅ Subscribed to strategy_signals channel")
        
        logger.info("👀 Monitoring signals... (Press Ctrl+C to stop)")
        logger.info("=" * 60)
        
        while True:
            message = await pubsub.get_message(
                ignore_subscribe_messages=True,
                timeout=1.0
            )
            
            if message and message["type"] == "message":
                signal = json.loads(message["data"].decode())
                timestamp = datetime.now().strftime("%H:%M:%S")
                
                print(f"[{timestamp}] 📡 Signal: {signal['symbol']} {signal['signal_type']} "
                      f"@ {signal['price']} (Qty: {signal['quantity']}) "
                      f"| Strategy: {signal['strategy_id']}")
                
                if 'metadata' in signal and signal['metadata'].get('test_signal'):
                    print(f"    🧪 Test Signal #{signal['metadata']['signal_number']}")
                
    except KeyboardInterrupt:
        logger.info("🛑 Monitoring stopped")
    except Exception as e:
        logger.error(f"❌ Error monitoring signals: {e}")
    finally:
        if pubsub:
            await pubsub.unsubscribe("strategy_signals")
        if redis_client:
            await redis_client.close()

if __name__ == "__main__":
    asyncio.run(monitor_signals()) 