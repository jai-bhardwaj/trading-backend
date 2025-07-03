#!/usr/bin/env python3
"""
Notification Service - Simple alerts and monitoring service
"""

import asyncio
import logging
import json
import time
from datetime import datetime
from typing import Dict, List, Optional, Any
from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel
import redis.asyncio as redis
import httpx
import os
from enum import Enum

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

config = {
    "REDIS_URL": os.getenv("REDIS_URL", "redis://localhost:6379/5"),
    "ADMIN_EMAIL": os.getenv("ADMIN_EMAIL", "admin@pinnacle.com")
}

class NotificationType(Enum):
    ORDER_FILLED = "ORDER_FILLED"
    ORDER_REJECTED = "ORDER_REJECTED"
    SERVICE_DOWN = "SERVICE_DOWN"
    SERVICE_RESTORED = "SERVICE_RESTORED"
    SYSTEM_ERROR = "SYSTEM_ERROR"

class AlertLevel(Enum):
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"

# Initialize FastAPI app
app = FastAPI(
    title="Notification Service",
    description="System Monitoring and Alert Management",
    version="1.0.0"
)

# Global components
redis_client = None
service_status = {}

@app.on_event("startup")
async def startup_event():
    """Initialize notification service"""
    global redis_client
    
    try:
        logger.info("🚀 Notification Service starting up...")
        
        # Connect to Redis
        redis_client = redis.from_url(config["REDIS_URL"])
        await redis_client.ping()
        logger.info("✅ Redis connected")
        
        # Start monitoring
        asyncio.create_task(monitor_services())
        
        logger.info("✅ Notification Service ready on port 8005")
        
    except Exception as e:
        logger.error(f"❌ Failed to initialize Notification Service: {e}")
        raise

async def monitor_services():
    """Simple service monitoring"""
    services = {
        "user": "http://localhost:8001",
        "market_data": "http://localhost:8002", 
        "strategy": "http://localhost:8003",
        "order": "http://localhost:8004"
    }
    
    while True:
        try:
            for service_name, url in services.items():
                try:
                    async with httpx.AsyncClient(timeout=3.0) as client:
                        response = await client.get(f"{url}/health")
                        is_healthy = response.status_code == 200
                        
                        previous_status = service_status.get(service_name, True)
                        service_status[service_name] = is_healthy
                        
                        if previous_status and not is_healthy:
                            logger.error(f"🚨 Service {service_name} is DOWN")
                        elif not previous_status and is_healthy:
                            logger.info(f"✅ Service {service_name} is RESTORED")
                            
                except Exception as e:
                    service_status[service_name] = False
                    logger.warning(f"Health check failed for {service_name}: {e}")
            
            await asyncio.sleep(30)  # Check every 30 seconds
            
        except Exception as e:
            logger.error(f"Error in monitoring loop: {e}")
            await asyncio.sleep(5)

@app.get("/health")
async def health_check():
    """Service health check"""
    try:
        await redis_client.ping()
        return {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "service_status": service_status
        }
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Service unhealthy: {e}")

class NotificationRequest(BaseModel):
    user_id: Optional[str] = None
    notification_type: str
    alert_level: str = "INFO"
    title: str
    message: str
    data: Dict[str, Any] = {}

@app.post("/notify")
async def send_notification(notification_request: NotificationRequest):
    """Send a notification"""
    try:
        notification_id = f"NOTIF_{int(time.time())}"
        
        notification_data = {
            "notification_id": notification_id,
            "user_id": notification_request.user_id,
            "notification_type": notification_request.notification_type,
            "alert_level": notification_request.alert_level,
            "title": notification_request.title,
            "message": notification_request.message,
            "data": notification_request.data,
            "created_at": datetime.utcnow().isoformat()
        }
        
        # Store in Redis
        await redis_client.setex(
            f"notification:{notification_id}",
            86400,  # 24 hours
            json.dumps(notification_data)
        )
        
        # Add to user's notification list if user_id provided
        if notification_request.user_id:
            await redis_client.lpush(
                f"user_notifications:{notification_request.user_id}",
                notification_id
            )
            await redis_client.ltrim(f"user_notifications:{notification_request.user_id}", 0, 99)
        
        logger.info(f"📢 Notification sent: {notification_request.title}")
        
        return {
            "notification_id": notification_id,
            "status": "sent",
            "message": "Notification sent successfully"
        }
        
    except Exception as e:
        logger.error(f"Error sending notification: {e}")
        raise HTTPException(status_code=500, detail="Failed to send notification")

@app.get("/notifications/{user_id}")
async def get_user_notifications(user_id: str, limit: int = 20):
    """Get user's notifications"""
    try:
        notification_ids = await redis_client.lrange(f"user_notifications:{user_id}", 0, limit - 1)
        notifications = []
        
        for notification_id in notification_ids:
            if isinstance(notification_id, bytes):
                notification_id = notification_id.decode()
                
            notification_data = await redis_client.get(f"notification:{notification_id}")
            if notification_data:
                notifications.append(json.loads(notification_data))
        
        return {
            "user_id": user_id,
            "notifications": notifications,
            "count": len(notifications),
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error getting notifications: {e}")
        raise HTTPException(status_code=500, detail="Failed to get notifications")

@app.get("/system/status")
async def get_system_status():
    """Get system-wide status"""
    return {
        "service_status": service_status,
        "timestamp": datetime.utcnow().isoformat(),
        "all_services_healthy": all(service_status.values()) if service_status else False
    }

@app.get("/")
async def service_info():
    """Service information"""
    return {
        "service": "Notification Service",
        "version": "1.0.0",
        "status": "operational",
        "monitoring_services": len(service_status),
        "endpoints": [
            "POST /notify",
            "GET /notifications/{user_id}",
            "GET /system/status",
            "GET /health"
        ]
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8005) 