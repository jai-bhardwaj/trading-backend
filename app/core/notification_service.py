#!/usr/bin/env python3
"""
Notification Service
Handles notifications for trading events
"""

import asyncio
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any

from app.database import DatabaseManager
from app.models.base import *
from app.strategies.base import StrategySignal

logger = logging.getLogger(__name__)

class NotificationService:
    """Simple notification service for trading events"""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager
        self.is_initialized = False
    
    async def initialize(self):
        """Initialize notification service"""
        logger.info("📣 Initializing Notification Service")
        self.is_initialized = True
        logger.info("✅ Notification Service initialized")
    
    async def stop(self):
        """Stop notification service"""
        logger.info("⏹️ Stopping Notification Service")
        self.is_initialized = False
        logger.info("🏁 Notification Service stopped")
    
    async def send_signal_notification(self, user_id: str, signal: StrategySignal, order_id: str):
        """Send notification for strategy signal"""
        try:
            async with self.db_manager.get_session() as db:
                notification = Notification(
                    user_id=user_id,
                    type=NotificationType.STRATEGY_STARTED,
                    title=f"Trading Signal: {signal.symbol}",
                    message=f"Strategy generated {signal.signal_type.value} signal for {signal.symbol} with {signal.confidence:.1%} confidence",
                    data={
                        'signal_type': signal.signal_type.value,
                        'symbol': signal.symbol,
                        'confidence': signal.confidence,
                        'quantity': signal.quantity,
                        'order_id': order_id
                    }
                )
                
                db.add(notification)
                await db.commit()
                
                logger.info(f"📩 Sent signal notification for {signal.symbol}")
        
        except Exception as e:
            logger.error(f"Error sending signal notification: {e}")
    
    async def send_order_notification(self, user_id: str, order: Order, event: str):
        """Send notification for order events"""
        try:
            async with self.db_manager.get_session() as db:
                notification = Notification(
                    user_id=user_id,
                    type=NotificationType.ORDER_EXECUTED if event == "EXECUTED" else NotificationType.ORDER_CANCELLED,
                    title=f"Order {event}: {order.symbol}",
                    message=f"Order {order.id} for {order.symbol} has been {event.lower()}",
                    data={
                        'order_id': order.id,
                        'symbol': order.symbol,
                        'side': order.side.value,
                        'quantity': order.quantity,
                        'status': order.status.value
                    }
                )
                
                db.add(notification)
                await db.commit()
                
                logger.info(f"📩 Sent order notification for {order.symbol}")
        
        except Exception as e:
            logger.error(f"Error sending order notification: {e}") 