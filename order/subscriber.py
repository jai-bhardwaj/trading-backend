"""
Signal Subscriber - Listens to strategy signals and processes orders
"""

import asyncio
import json
import logging
import redis.asyncio as redis
from typing import Dict, List, Optional
from datetime import datetime
from shared.user_service import UserService

logger = logging.getLogger(__name__)

class SignalSubscriber:
    """Subscribes to strategy signals and processes orders"""
    
    def __init__(self, redis_url: str = "redis://localhost:6379/2"):
        self.redis_url = redis_url
        self.redis_client = None
        self.pubsub = None
        self.running = False
        self.order_manager = None
        self.user_service = UserService()
        
    async def initialize(self, order_manager):
        """Initialize the signal subscriber"""
        try:
            # Connect to Redis
            self.redis_client = redis.from_url(self.redis_url)
            await self.redis_client.ping()
            logger.info("✅ Signal subscriber connected to Redis")
            
            # Initialize pubsub
            self.pubsub = self.redis_client.pubsub()
            await self.pubsub.subscribe("strategy_signals")
            logger.info("✅ Subscribed to strategy_signals channel")
            
            # User service is already initialized (no async init needed)
            logger.info("✅ User service ready")
            
            # Set order manager
            self.order_manager = order_manager
            
            logger.info("✅ Signal subscriber initialized")
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize signal subscriber: {e}")
            raise
    
    async def start_listening(self):
        """Start listening for signals"""
        self.running = True
        logger.info("🚀 Signal subscriber started listening")
        
        while self.running:
            try:
                message = await self.pubsub.get_message(
                    ignore_subscribe_messages=True, 
                    timeout=1.0
                )
                
                if message and message["type"] == "message":
                    await self._process_signal(message["data"])
                
                await asyncio.sleep(0.1)
                
            except Exception as e:
                logger.error(f"❌ Error in signal subscriber loop: {e}")
                await asyncio.sleep(1)
    
    async def stop_listening(self):
        """Stop listening for signals"""
        self.running = False
        logger.info("🛑 Signal subscriber stopped listening")
    
    async def _process_signal(self, signal_data: bytes):
        """Process a received signal"""
        try:
            signal = json.loads(signal_data.decode())
            logger.info(f"📥 Received signal: {signal['symbol']} {signal['signal_type']}")
            
            # Get active users (mock for now)
            active_users = await self._get_active_users()
            
            # Process signal for each user
            for user in active_users:
                await self._process_signal_for_user(signal, user)
                
        except Exception as e:
            logger.error(f"❌ Error processing signal: {e}")
    
    async def _process_signal_for_user(self, signal: Dict, user: Dict):
        """Process signal for a specific user"""
        try:
            # Get user_id from the correct field (PostgreSQL uses 'id', Redis uses 'user_id')
            user_id = user.get("user_id") or user.get("id")
            if not user_id:
                logger.error(f"❌ No user_id found in user data: {user}")
                return
            
            # Create order request
            order_request = {
                "symbol": signal["symbol"],
                "side": signal["signal_type"],
                "order_type": "MARKET",
                "quantity": signal["quantity"],
                "price": signal.get("price"),
                "strategy_id": signal.get("strategy_id", "unknown"),
                "user_id": user_id
            }
            
            # Execute order
            if self.order_manager:
                result = await self.order_manager.execute_order(order_request)
                logger.info(f"📋 Order executed for user {user_id}: {result}")
            else:
                logger.warning("⚠️ No order manager available")
                
        except Exception as e:
            logger.error(f"❌ Error processing signal for user {user_id}: {e}")
    
    async def _get_active_users(self) -> List[Dict]:
        """Get list of active users from the database"""
        try:
            return self.user_service.get_active_users()
        except Exception as e:
            logger.error(f"❌ Error getting active users: {e}")
            # Fallback to empty list if user service fails
            return []
    
    async def close(self):
        """Close the signal subscriber"""
        if self.pubsub:
            await self.pubsub.unsubscribe("strategy_signals")
        if self.redis_client:
            await self.redis_client.close()
        # User service doesn't need async close
        logger.info("✅ Signal subscriber closed") 