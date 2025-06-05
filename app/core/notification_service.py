#!/usr/bin/env python3
"""
Hybrid Notification Service for Live Trading
Implements real-time Redis notifications with selective database persistence.
"""

import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from enum import Enum
import redis.asyncio as redis
from sqlalchemy import text

from app.database import get_database_manager, RedisKeys
from app.models.base import *
from app.strategies.base import StrategySignal

logger = logging.getLogger(__name__)

class NotificationType(Enum):
    # Real-time notifications (Redis only)
    ORDER_EXECUTED = "ORDER_EXECUTED"
    ORDER_CANCELLED = "ORDER_CANCELLED"
    ORDER_REJECTED = "ORDER_REJECTED"
    STRATEGY_STARTED = "STRATEGY_STARTED"
    STRATEGY_STOPPED = "STRATEGY_STOPPED"
    STRATEGY_ERROR = "STRATEGY_ERROR"
    PRICE_ALERT = "PRICE_ALERT"
    SYSTEM_ALERT = "SYSTEM_ALERT"
    BROKER_DISCONNECTED = "BROKER_DISCONNECTED"
    
    # Critical notifications (Database + Redis)
    RISK_VIOLATION = "RISK_VIOLATION"
    ACCOUNT_SECURITY = "ACCOUNT_SECURITY"
    REGULATORY_NOTICE = "REGULATORY_NOTICE"
    SYSTEM_MAINTENANCE = "SYSTEM_MAINTENANCE"
    STRATEGY_PERFORMANCE_SUMMARY = "STRATEGY_PERFORMANCE_SUMMARY"
    ACCOUNT_STATEMENT = "ACCOUNT_STATEMENT"
    COMPLIANCE_ALERT = "COMPLIANCE_ALERT"

class NotificationService:
    """
    Hybrid notification service providing real-time alerts via Redis
    and persistent storage for critical notifications.
    """
    
    def __init__(self):
        self.redis_client: Optional[redis.Redis] = None
        self.critical_types = {
            NotificationType.RISK_VIOLATION,
            NotificationType.ACCOUNT_SECURITY,
            NotificationType.REGULATORY_NOTICE,
            NotificationType.SYSTEM_MAINTENANCE,
            NotificationType.STRATEGY_PERFORMANCE_SUMMARY,
            NotificationType.ACCOUNT_STATEMENT,
            NotificationType.COMPLIANCE_ALERT
        }
        
        self.urgent_types = {
            NotificationType.ORDER_REJECTED,
            NotificationType.STRATEGY_ERROR,
            NotificationType.RISK_VIOLATION,
            NotificationType.BROKER_DISCONNECTED,
            NotificationType.ACCOUNT_SECURITY
        }
    
    async def initialize(self):
        """Initialize the notification service."""
        try:
            self.redis_client = await get_database_manager().get_redis()
            logger.info("Notification service initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize notification service: {e}")
            raise
    
    async def send_realtime_notification(self, user_id: str, type: str, 
                                       title: str, message: str, 
                                       data: Optional[Dict[str, Any]] = None,
                                       ttl: int = 3600):
        """
        Send a real-time notification via Redis.
        
        Args:
            user_id: Target user ID
            type: Notification type
            title: Notification title
            message: Notification message
            data: Additional data
            ttl: Time to live in seconds (default 1 hour)
        """
        try:
            notification_type = NotificationType(type)
            
            notification = {
                "id": f"notif_{int(datetime.now().timestamp() * 1000)}",
                "user_id": user_id,
                "type": type,
                "title": title,
                "message": message,
                "data": data or {},
                "timestamp": datetime.now().isoformat(),
                "ttl": ttl
            }
            
            # 1. Always send to Redis for real-time delivery
            await self._send_to_redis(user_id, notification, ttl)
            
            # 2. Store critical notifications in database
            if notification_type in self.critical_types:
                await self._store_in_database(notification)
            
            # 3. Send external alerts for urgent notifications
            if notification_type in self.urgent_types:
                await self._send_external_alert(user_id, notification)
            
            logger.debug(f"Sent notification {type} to user {user_id}")
            
        except Exception as e:
            logger.error(f"Failed to send notification: {e}")
            raise
    
    async def _send_to_redis(self, user_id: str, notification: Dict[str, Any], ttl: int):
        """Send notification to Redis for real-time delivery."""
        try:
            # Store in user's notification list
            user_key = RedisKeys.USER_NOTIFICATIONS.format(user_id=user_id)
            await self.redis_client.lpush(user_key, json.dumps(notification))
            await self.redis_client.expire(user_key, ttl)
            
            # Publish to user's channel for WebSocket delivery
            user_channel = RedisKeys.USER_CHANNEL.format(user_id=user_id)
            await self.redis_client.publish(user_channel, json.dumps(notification))
            
            # If strategy-related, also publish to strategy channel
            strategy_id = notification.get("data", {}).get("strategy_id")
            if strategy_id:
                strategy_channel = RedisKeys.STRATEGY_CHANNEL.format(strategy_id=strategy_id)
                await self.redis_client.publish(strategy_channel, json.dumps(notification))
            
        except Exception as e:
            logger.error(f"Failed to send notification to Redis: {e}")
            raise
    
    async def _store_in_database(self, notification: Dict[str, Any]):
        """Store critical notification in database."""
        try:
            async with get_database_manager().get_async_session() as session:
                await session.execute(text("""
                    INSERT INTO notifications 
                    (user_id, type, title, message, data, status, created_at)
                    VALUES (:user_id, :type, :title, :message, :data, 'UNREAD', NOW())
                """), {
                    "user_id": notification["user_id"],
                    "type": notification["type"],
                    "title": notification["title"],
                    "message": notification["message"],
                    "data": json.dumps(notification.get("data", {}))
                })
                await session.commit()
                
        except Exception as e:
            logger.error(f"Failed to store notification in database: {e}")
            # Don't re-raise to avoid breaking real-time delivery
    
    async def _send_external_alert(self, user_id: str, notification: Dict[str, Any]):
        """Send external alerts (SMS, Email, Push) for urgent notifications."""
        try:
            # Get user notification preferences
            preferences = await self._get_user_preferences(user_id)
            if not preferences:
                return
            
            notification_type = notification["type"]
            
            # Send SMS for critical alerts
            if self._should_send_sms(notification_type, preferences):
                await self._send_sms_alert(user_id, notification)
            
            # Send email for reports and summaries
            if self._should_send_email(notification_type, preferences):
                await self._send_email_alert(user_id, notification)
            
            # Send push notification
            if self._should_send_push(notification_type, preferences):
                await self._send_push_notification(user_id, notification)
                
        except Exception as e:
            logger.error(f"Failed to send external alert: {e}")
            # Don't re-raise to avoid breaking real-time delivery
    
    async def _get_user_preferences(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get user notification preferences."""
        try:
            async with get_database_manager().get_async_session() as session:
                result = await session.execute(text("""
                    SELECT * FROM notification_settings WHERE user_id = :user_id
                """), {"user_id": user_id})
                
                row = result.fetchone()
                if row:
                    return dict(row._mapping)
                return None
                
        except Exception as e:
            logger.error(f"Failed to get user preferences: {e}")
            return None
    
    def _should_send_sms(self, notification_type: str, preferences: Dict[str, Any]) -> bool:
        """Check if SMS should be sent for this notification type."""
        type_mapping = {
            "RISK_VIOLATION": preferences.get("sms_risk_violations", True),
            "ORDER_REJECTED": preferences.get("sms_order_failures", True),
            "ACCOUNT_SECURITY": preferences.get("sms_account_security", True),
            "SYSTEM_MAINTENANCE": preferences.get("sms_system_downtime", True)
        }
        return type_mapping.get(notification_type, False)
    
    def _should_send_email(self, notification_type: str, preferences: Dict[str, Any]) -> bool:
        """Check if email should be sent for this notification type."""
        type_mapping = {
            "STRATEGY_PERFORMANCE_SUMMARY": preferences.get("email_daily_summary", False),
            "ACCOUNT_STATEMENT": preferences.get("email_monthly_statement", True),
            "REGULATORY_NOTICE": preferences.get("email_regulatory", True)
        }
        return type_mapping.get(notification_type, False)
    
    def _should_send_push(self, notification_type: str, preferences: Dict[str, Any]) -> bool:
        """Check if push notification should be sent."""
        # For now, send push for most real-time alerts
        return notification_type in [
            "ORDER_EXECUTED", "ORDER_REJECTED", "STRATEGY_ERROR", 
            "PRICE_ALERT", "RISK_VIOLATION"
        ]
    
    async def _send_sms_alert(self, user_id: str, notification: Dict[str, Any]):
        """Send SMS alert (placeholder - integrate with Twilio)."""
        try:
            # TODO: Integrate with Twilio SMS service
            logger.info(f"SMS alert sent to user {user_id}: {notification['title']}")
        except Exception as e:
            logger.error(f"Failed to send SMS alert: {e}")
    
    async def _send_email_alert(self, user_id: str, notification: Dict[str, Any]):
        """Send email alert (placeholder - integrate with SendGrid)."""
        try:
            # TODO: Integrate with SendGrid email service
            logger.info(f"Email alert sent to user {user_id}: {notification['title']}")
        except Exception as e:
            logger.error(f"Failed to send email alert: {e}")
    
    async def _send_push_notification(self, user_id: str, notification: Dict[str, Any]):
        """Send push notification (placeholder - integrate with Firebase)."""
        try:
            # TODO: Integrate with Firebase/OneSignal push service
            logger.info(f"Push notification sent to user {user_id}: {notification['title']}")
        except Exception as e:
            logger.error(f"Failed to send push notification: {e}")
    
    async def get_user_notifications(self, user_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Get recent notifications for a user from Redis."""
        try:
            user_key = RedisKeys.USER_NOTIFICATIONS.format(user_id=user_id)
            notifications_data = await self.redis_client.lrange(user_key, 0, limit - 1)
            
            notifications = []
            for data in notifications_data:
                try:
                    notification = json.loads(data)
                    notifications.append(notification)
                except json.JSONDecodeError:
                    continue
            
            return notifications
            
        except Exception as e:
            logger.error(f"Failed to get user notifications: {e}")
            return []
    
    async def get_critical_notifications(self, user_id: str, limit: int = 20) -> List[Dict[str, Any]]:
        """Get critical notifications from database."""
        try:
            async with get_database_manager().get_async_session() as session:
                result = await session.execute(text("""
                    SELECT id, type, title, message, data, status, created_at, read_at
                    FROM notifications 
                    WHERE user_id = :user_id 
                    ORDER BY created_at DESC 
                    LIMIT :limit
                """), {"user_id": user_id, "limit": limit})
                
                notifications = []
                for row in result.fetchall():
                    notification = {
                        "id": row.id,
                        "type": row.type,
                        "title": row.title,
                        "message": row.message,
                        "data": json.loads(row.data) if row.data else {},
                        "status": row.status,
                        "created_at": row.created_at.isoformat(),
                        "read_at": row.read_at.isoformat() if row.read_at else None
                    }
                    notifications.append(notification)
                
                return notifications
                
        except Exception as e:
            logger.error(f"Failed to get critical notifications: {e}")
            return []
    
    async def mark_notification_read(self, user_id: str, notification_id: str):
        """Mark a critical notification as read."""
        try:
            async with get_database_manager().get_async_session() as session:
                await session.execute(text("""
                    UPDATE notifications 
                    SET status = 'READ', read_at = NOW()
                    WHERE id = :notification_id AND user_id = :user_id
                """), {"notification_id": notification_id, "user_id": user_id})
                await session.commit()
                
        except Exception as e:
            logger.error(f"Failed to mark notification as read: {e}")
    
    async def cleanup_old_notifications(self, days: int = 7):
        """Clean up old notifications from Redis and database."""
        try:
            # Clean up database notifications older than specified days
            async with get_database_manager().get_async_session() as session:
                await session.execute(text("""
                    DELETE FROM notifications 
                    WHERE created_at < NOW() - INTERVAL :days DAY
                    AND status = 'READ'
                """), {"days": days})
                await session.commit()
            
            logger.info(f"Cleaned up notifications older than {days} days")
            
        except Exception as e:
            logger.error(f"Failed to cleanup old notifications: {e}")

# Global notification service instance
notification_service = NotificationService()

# Convenience functions
async def send_notification(user_id: str, type: str, title: str, message: str, 
                          data: Optional[Dict[str, Any]] = None):
    """Send a notification."""
    await notification_service.send_realtime_notification(user_id, type, title, message, data)

async def get_user_notifications(user_id: str, limit: int = 50):
    """Get user notifications."""
    return await notification_service.get_user_notifications(user_id, limit)

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