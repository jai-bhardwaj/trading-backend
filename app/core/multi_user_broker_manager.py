"""
Multi-User Broker Manager

A comprehensive broker management system that supports:
- Multiple users with different broker accounts
- Multiple Angel One accounts per user
- Multiple broker types (Angel One, Zerodha, etc.)
- Proper session isolation and security
- Automatic authentication and reconnection
- Health monitoring and diagnostics
"""

import asyncio
import logging
from typing import Dict, Any, List, Optional, Set, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from contextlib import asynccontextmanager
import hashlib
import json

from app.models.base import (
    BrokerConfig, BrokerName, User, Order as DBOrder, Trade as DBTrade,
    Position as DBPosition, Balance as DBBalance, OrderSide, OrderType,
    ProductType, OrderStatus
)
from app.brokers.base import (
    BrokerRegistry, BrokerInterface, BrokerOrder, BrokerPosition, 
    BrokerBalance, BrokerTrade, MarketData, BrokerError,
    AuthenticationError, OrderError, InsufficientFundsError
)
from app.database import get_database_manager
from app.core.config import get_settings
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

@dataclass
class BrokerSession:
    """Represents an active broker session for a user"""
    user_id: str
    config_id: str
    broker_name: BrokerName
    broker_instance: BrokerInterface
    authenticated_at: datetime
    last_activity: datetime
    session_id: str
    health_status: str = "healthy"
    error_count: int = 0
    
    def is_expired(self, timeout_minutes: int = 60) -> bool:
        """Check if session is expired"""
        return datetime.utcnow() - self.last_activity > timedelta(minutes=timeout_minutes)
    
    def update_activity(self):
        """Update last activity timestamp"""
        self.last_activity = datetime.utcnow()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            "user_id": self.user_id,
            "config_id": self.config_id,
            "broker_name": self.broker_name.value,
            "session_id": self.session_id,
            "authenticated_at": self.authenticated_at.isoformat(),
            "last_activity": self.last_activity.isoformat(),
            "health_status": self.health_status,
            "error_count": self.error_count
        }

@dataclass
class BrokerOperationResult:
    """Result of broker operations with detailed context"""
    success: bool
    message: str
    user_id: str
    broker_name: str
    config_id: str
    data: Optional[Dict[str, Any]] = None
    error_code: Optional[str] = None
    session_id: Optional[str] = None
    execution_time: Optional[float] = None

class MultiUserBrokerManager:
    """
    Multi-User Broker Manager
    
    Manages multiple broker accounts for multiple users with:
    - Proper session isolation
    - Automatic authentication and reconnection
    - Health monitoring and error recovery
    - Support for multiple broker types
    - Concurrent operations with thread safety
    """
    
    def __init__(self):
        self.settings = get_settings()
        self.db_manager = get_database_manager()
        
        # Core data structures
        self._user_sessions: Dict[str, Dict[str, BrokerSession]] = {}  # user_id -> {config_id: session}
        self._session_locks: Dict[str, asyncio.Lock] = {}  # session_id -> lock
        self._global_lock = asyncio.Lock()
        
        # Health monitoring
        self._health_check_interval = 300  # 5 minutes
        self._session_timeout = 3600  # 1 hour
        self._max_error_count = 5
        
        # Background tasks
        self._background_tasks: Set[asyncio.Task] = set()
        self._running = False
        
        self.logger = logging.getLogger(self.__class__.__name__)
    
    async def initialize(self) -> bool:
        """Initialize the multi-user broker manager"""
        try:
            await self.db_manager.initialize()
            self._running = True
            
            # Start background health monitoring
            self._start_background_tasks()
            
            self.logger.info("✅ Multi-User Broker Manager initialized successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Failed to initialize Multi-User Broker Manager: {e}")
            return False
    
    def _start_background_tasks(self):
        """Start background monitoring tasks"""
        if self._running:
            # Health check task
            task = asyncio.create_task(self._health_monitor_loop())
            self._background_tasks.add(task)
            task.add_done_callback(self._background_tasks.discard)
            
            # Session cleanup task
            task = asyncio.create_task(self._session_cleanup_loop())
            self._background_tasks.add(task)
            task.add_done_callback(self._background_tasks.discard)
    
    async def add_user_broker(self, user_id: str, broker_config_id: str) -> BrokerOperationResult:
        """
        Add a broker account for a user
        
        Args:
            user_id: User identifier
            broker_config_id: Broker configuration ID from database
            
        Returns:
            BrokerOperationResult: Result of the operation
        """
        start_time = datetime.utcnow()
        
        try:
            async with self._global_lock:
                # Get broker configuration from database
                async with self.db_manager.get_async_session() as session:
                    result = await session.execute(
                        select(BrokerConfig).where(
                            and_(
                                BrokerConfig.id == broker_config_id,
                                BrokerConfig.user_id == user_id,
                                BrokerConfig.is_active == True
                            )
                        )
                    )
                    broker_config = result.scalar_one_or_none()
                    
                    if not broker_config:
                        return BrokerOperationResult(
                            success=False,
                            message="Broker configuration not found or not active",
                            user_id=user_id,
                            broker_name="unknown",
                            config_id=broker_config_id,
                            error_code="CONFIG_NOT_FOUND"
                        )
                
                # Check if user already has this broker session
                if user_id in self._user_sessions and broker_config_id in self._user_sessions[user_id]:
                    existing_session = self._user_sessions[user_id][broker_config_id]
                    if not existing_session.is_expired(self._session_timeout // 60):
                        return BrokerOperationResult(
                            success=True,
                            message="Broker session already exists and is active",
                            user_id=user_id,
                            broker_name=broker_config.broker_name.value,
                            config_id=broker_config_id,
                            session_id=existing_session.session_id,
                            data=existing_session.to_dict()
                        )
                
                # Create new broker instance
                broker_instance = BrokerRegistry.get_broker(broker_config)
                
                # Authenticate broker
                auth_success = await broker_instance.authenticate()
                if not auth_success:
                    return BrokerOperationResult(
                        success=False,
                        message="Broker authentication failed",
                        user_id=user_id,
                        broker_name=broker_config.broker_name.value,
                        config_id=broker_config_id,
                        error_code="AUTH_FAILED"
                    )
                
                # Create session
                session_id = self._generate_session_id(user_id, broker_config_id)
                broker_session = BrokerSession(
                    user_id=user_id,
                    config_id=broker_config_id,
                    broker_name=broker_config.broker_name,
                    broker_instance=broker_instance,
                    authenticated_at=datetime.utcnow(),
                    last_activity=datetime.utcnow(),
                    session_id=session_id
                )
                
                # Store session
                if user_id not in self._user_sessions:
                    self._user_sessions[user_id] = {}
                
                self._user_sessions[user_id][broker_config_id] = broker_session
                self._session_locks[session_id] = asyncio.Lock()
                
                execution_time = (datetime.utcnow() - start_time).total_seconds()
                
                self.logger.info(f"✅ Added broker session: {broker_config.broker_name.value} for user {user_id}")
                
                return BrokerOperationResult(
                    success=True,
                    message="Broker session created successfully",
                    user_id=user_id,
                    broker_name=broker_config.broker_name.value,
                    config_id=broker_config_id,
                    session_id=session_id,
                    execution_time=execution_time,
                    data=broker_session.to_dict()
                )
                
        except Exception as e:
            self.logger.error(f"❌ Error adding broker for user {user_id}: {e}")
            return BrokerOperationResult(
                success=False,
                message=f"Error adding broker: {e}",
                user_id=user_id,
                broker_name="unknown",
                config_id=broker_config_id,
                error_code="SYSTEM_ERROR"
            )
    
    async def remove_user_broker(self, user_id: str, broker_config_id: str) -> BrokerOperationResult:
        """Remove a broker session for a user"""
        try:
            async with self._global_lock:
                if user_id not in self._user_sessions:
                    return BrokerOperationResult(
                        success=False,
                        message="User has no active broker sessions",
                        user_id=user_id,
                        broker_name="unknown",
                        config_id=broker_config_id,
                        error_code="NO_SESSIONS"
                    )
                
                if broker_config_id not in self._user_sessions[user_id]:
                    return BrokerOperationResult(
                        success=False,
                        message="Broker session not found",
                        user_id=user_id,
                        broker_name="unknown",
                        config_id=broker_config_id,
                        error_code="SESSION_NOT_FOUND"
                    )
                
                # Get session and cleanup
                session = self._user_sessions[user_id][broker_config_id]
                broker_name = session.broker_name.value
                session_id = session.session_id
                
                # Disconnect broker
                try:
                    await session.broker_instance.disconnect()
                except Exception as e:
                    self.logger.warning(f"⚠️ Error disconnecting broker: {e}")
                
                # Remove from data structures
                del self._user_sessions[user_id][broker_config_id]
                if session_id in self._session_locks:
                    del self._session_locks[session_id]
                
                # Clean up empty user entry
                if not self._user_sessions[user_id]:
                    del self._user_sessions[user_id]
                
                self.logger.info(f"✅ Removed broker session: {broker_name} for user {user_id}")
                
                return BrokerOperationResult(
                    success=True,
                    message="Broker session removed successfully",
                    user_id=user_id,
                    broker_name=broker_name,
                    config_id=broker_config_id,
                    session_id=session_id
                )
                
        except Exception as e:
            self.logger.error(f"❌ Error removing broker for user {user_id}: {e}")
            return BrokerOperationResult(
                success=False,
                message=f"Error removing broker: {e}",
                user_id=user_id,
                broker_name="unknown",
                config_id=broker_config_id,
                error_code="SYSTEM_ERROR"
            )
    
    async def get_user_brokers(self, user_id: str) -> List[BrokerSession]:
        """Get all active broker sessions for a user"""
        if user_id not in self._user_sessions:
            return []
        
        return list(self._user_sessions[user_id].values())
    
    async def get_broker_session(self, user_id: str, broker_config_id: str) -> Optional[BrokerSession]:
        """Get a specific broker session"""
        if user_id not in self._user_sessions:
            return None
        
        return self._user_sessions[user_id].get(broker_config_id)
    
    @asynccontextmanager
    async def broker_session(self, user_id: str, broker_config_id: str):
        """
        Context manager for safe broker operations
        
        Automatically handles:
        - Session validation and refresh
        - Error recovery
        - Activity tracking
        - Proper cleanup
        """
        session = await self.get_broker_session(user_id, broker_config_id)
        
        if not session:
            # Try to create session if it doesn't exist
            result = await self.add_user_broker(user_id, broker_config_id)
            if not result.success:
                raise Exception(f"Failed to create broker session: {result.message}")
            session = await self.get_broker_session(user_id, broker_config_id)
        
        if not session:
            raise Exception("Failed to get broker session")
        
        # Check if session is expired
        if session.is_expired(self._session_timeout // 60):
            self.logger.info(f"🔄 Session expired, recreating for user {user_id}")
            await self.remove_user_broker(user_id, broker_config_id)
            result = await self.add_user_broker(user_id, broker_config_id)
            if not result.success:
                raise Exception(f"Failed to recreate broker session: {result.message}")
            session = await self.get_broker_session(user_id, broker_config_id)
        
        # Acquire session lock
        session_lock = self._session_locks.get(session.session_id)
        if not session_lock:
            session_lock = asyncio.Lock()
            self._session_locks[session.session_id] = session_lock
        
        async with session_lock:
            try:
                # Update activity
                session.update_activity()
                
                # Yield broker instance
                yield session.broker_instance
                
                # Reset error count on successful operation
                session.error_count = 0
                session.health_status = "healthy"
                
            except Exception as e:
                # Track errors
                session.error_count += 1
                session.health_status = "error"
                
                self.logger.error(f"❌ Error in broker session {session.session_id}: {e}")
                
                # Remove session if too many errors
                if session.error_count >= self._max_error_count:
                    self.logger.warning(f"⚠️ Removing unhealthy session {session.session_id}")
                    await self.remove_user_broker(user_id, broker_config_id)
                
                raise
    
    async def place_order_for_user(self, user_id: str, broker_config_id: str, order: BrokerOrder) -> BrokerOperationResult:
        """Place an order using a specific user's broker"""
        start_time = datetime.utcnow()
        
        try:
            async with self.broker_session(user_id, broker_config_id) as broker:
                # Validate order
                if not broker.validate_order(order):
                    return BrokerOperationResult(
                        success=False,
                        message="Order validation failed",
                        user_id=user_id,
                        broker_name=broker.broker_name.value,
                        config_id=broker_config_id,
                        error_code="INVALID_ORDER"
                    )
                
                # Place order
                broker_order_id = await broker.place_order(order)
                
                execution_time = (datetime.utcnow() - start_time).total_seconds()
                
                return BrokerOperationResult(
                    success=True,
                    message="Order placed successfully",
                    user_id=user_id,
                    broker_name=broker.broker_name.value,
                    config_id=broker_config_id,
                    execution_time=execution_time,
                    data={"broker_order_id": broker_order_id}
                )
                
        except Exception as e:
            execution_time = (datetime.utcnow() - start_time).total_seconds()
            
            error_code = "SYSTEM_ERROR"
            if isinstance(e, InsufficientFundsError):
                error_code = "INSUFFICIENT_FUNDS"
            elif isinstance(e, OrderError):
                error_code = "ORDER_ERROR"
            elif isinstance(e, AuthenticationError):
                error_code = "AUTH_ERROR"
            
            return BrokerOperationResult(
                success=False,
                message=str(e),
                user_id=user_id,
                broker_name="unknown",
                config_id=broker_config_id,
                error_code=error_code,
                execution_time=execution_time
            )
    
    async def get_positions_for_user(self, user_id: str, broker_config_id: str) -> BrokerOperationResult:
        """Get positions for a specific user's broker"""
        start_time = datetime.utcnow()
        
        try:
            async with self.broker_session(user_id, broker_config_id) as broker:
                positions = await broker.get_positions()
                
                execution_time = (datetime.utcnow() - start_time).total_seconds()
                
                return BrokerOperationResult(
                    success=True,
                    message="Positions retrieved successfully",
                    user_id=user_id,
                    broker_name=broker.broker_name.value,
                    config_id=broker_config_id,
                    execution_time=execution_time,
                    data={"positions": [pos.to_dict() for pos in positions]}
                )
                
        except Exception as e:
            execution_time = (datetime.utcnow() - start_time).total_seconds()
            
            return BrokerOperationResult(
                success=False,
                message=str(e),
                user_id=user_id,
                broker_name="unknown",
                config_id=broker_config_id,
                error_code="SYSTEM_ERROR",
                execution_time=execution_time
            )
    
    async def get_balance_for_user(self, user_id: str, broker_config_id: str) -> BrokerOperationResult:
        """Get balance for a specific user's broker"""
        start_time = datetime.utcnow()
        
        try:
            async with self.broker_session(user_id, broker_config_id) as broker:
                balance = await broker.get_balance()
                
                execution_time = (datetime.utcnow() - start_time).total_seconds()
                
                return BrokerOperationResult(
                    success=True,
                    message="Balance retrieved successfully",
                    user_id=user_id,
                    broker_name=broker.broker_name.value,
                    config_id=broker_config_id,
                    execution_time=execution_time,
                    data=balance.to_dict()
                )
                
        except Exception as e:
            execution_time = (datetime.utcnow() - start_time).total_seconds()
            
            return BrokerOperationResult(
                success=False,
                message=str(e),
                user_id=user_id,
                broker_name="unknown",
                config_id=broker_config_id,
                error_code="SYSTEM_ERROR",
                execution_time=execution_time
            )
    
    async def get_market_data_for_user(self, user_id: str, broker_config_id: str, 
                                     symbol: str, exchange: str = "NSE") -> BrokerOperationResult:
        """Get market data for a specific user's broker"""
        start_time = datetime.utcnow()
        
        try:
            async with self.broker_session(user_id, broker_config_id) as broker:
                market_data = await broker.get_market_data(symbol, exchange)
                
                execution_time = (datetime.utcnow() - start_time).total_seconds()
                
                if market_data:
                    return BrokerOperationResult(
                        success=True,
                        message="Market data retrieved successfully",
                        user_id=user_id,
                        broker_name=broker.broker_name.value,
                        config_id=broker_config_id,
                        execution_time=execution_time,
                        data=market_data.to_dict()
                    )
                else:
                    return BrokerOperationResult(
                        success=False,
                        message="Market data not available",
                        user_id=user_id,
                        broker_name=broker.broker_name.value,
                        config_id=broker_config_id,
                        error_code="NO_DATA",
                        execution_time=execution_time
                    )
                
        except Exception as e:
            execution_time = (datetime.utcnow() - start_time).total_seconds()
            
            return BrokerOperationResult(
                success=False,
                message=str(e),
                user_id=user_id,
                broker_name="unknown",
                config_id=broker_config_id,
                error_code="SYSTEM_ERROR",
                execution_time=execution_time
            )
    
    async def get_all_user_positions(self, user_id: str) -> Dict[str, BrokerOperationResult]:
        """Get positions from all brokers for a user"""
        results = {}
        
        user_sessions = await self.get_user_brokers(user_id)
        
        for session in user_sessions:
            result = await self.get_positions_for_user(user_id, session.config_id)
            results[session.config_id] = result
        
        return results
    
    async def get_all_user_balances(self, user_id: str) -> Dict[str, BrokerOperationResult]:
        """Get balances from all brokers for a user"""
        results = {}
        
        user_sessions = await self.get_user_brokers(user_id)
        
        for session in user_sessions:
            result = await self.get_balance_for_user(user_id, session.config_id)
            results[session.config_id] = result
        
        return results
    
    async def get_system_status(self) -> Dict[str, Any]:
        """Get overall system status"""
        status = {
            "total_users": len(self._user_sessions),
            "total_sessions": sum(len(sessions) for sessions in self._user_sessions.values()),
            "healthy_sessions": 0,
            "error_sessions": 0,
            "expired_sessions": 0,
            "by_broker": {},
            "uptime": datetime.utcnow().isoformat(),
            "background_tasks": len(self._background_tasks)
        }
        
        # Analyze sessions
        for user_id, user_sessions in self._user_sessions.items():
            for config_id, session in user_sessions.items():
                broker_name = session.broker_name.value
                
                if broker_name not in status["by_broker"]:
                    status["by_broker"][broker_name] = {
                        "total": 0,
                        "healthy": 0,
                        "error": 0,
                        "expired": 0
                    }
                
                status["by_broker"][broker_name]["total"] += 1
                
                if session.is_expired():
                    status["expired_sessions"] += 1
                    status["by_broker"][broker_name]["expired"] += 1
                elif session.health_status == "healthy":
                    status["healthy_sessions"] += 1
                    status["by_broker"][broker_name]["healthy"] += 1
                else:
                    status["error_sessions"] += 1
                    status["by_broker"][broker_name]["error"] += 1
        
        return status
    
    async def _health_monitor_loop(self):
        """Background task to monitor broker health"""
        while self._running:
            try:
                await asyncio.sleep(self._health_check_interval)
                
                if not self._running:
                    break
                
                self.logger.debug("🔍 Running health check on all broker sessions")
                
                # Check all sessions
                unhealthy_sessions = []
                
                for user_id, user_sessions in self._user_sessions.items():
                    for config_id, session in user_sessions.items():
                        try:
                            # Check if session is expired
                            if session.is_expired():
                                unhealthy_sessions.append((user_id, config_id, "expired"))
                                continue
                            
                            # Perform health check
                            async with self._session_locks.get(session.session_id, asyncio.Lock()):
                                health = await session.broker_instance.health_check()
                                
                                if health.get("status") != "healthy":
                                    session.health_status = "unhealthy"
                                    session.error_count += 1
                                else:
                                    session.health_status = "healthy"
                                    session.error_count = max(0, session.error_count - 1)
                                
                                # Mark for removal if too many errors
                                if session.error_count >= self._max_error_count:
                                    unhealthy_sessions.append((user_id, config_id, "too_many_errors"))
                        
                        except Exception as e:
                            self.logger.warning(f"⚠️ Health check failed for {session.session_id}: {e}")
                            session.error_count += 1
                            session.health_status = "error"
                            
                            if session.error_count >= self._max_error_count:
                                unhealthy_sessions.append((user_id, config_id, "health_check_failed"))
                
                # Remove unhealthy sessions
                for user_id, config_id, reason in unhealthy_sessions:
                    self.logger.warning(f"🗑️ Removing unhealthy session {user_id}/{config_id}: {reason}")
                    await self.remove_user_broker(user_id, config_id)
                
            except Exception as e:
                self.logger.error(f"❌ Error in health monitor loop: {e}")
    
    async def _session_cleanup_loop(self):
        """Background task to clean up expired sessions"""
        while self._running:
            try:
                await asyncio.sleep(self._health_check_interval // 2)  # Run more frequently
                
                if not self._running:
                    break
                
                # Find expired sessions
                expired_sessions = []
                
                for user_id, user_sessions in self._user_sessions.items():
                    for config_id, session in user_sessions.items():
                        if session.is_expired(self._session_timeout // 60):
                            expired_sessions.append((user_id, config_id))
                
                # Clean up expired sessions
                for user_id, config_id in expired_sessions:
                    self.logger.info(f"🧹 Cleaning up expired session {user_id}/{config_id}")
                    await self.remove_user_broker(user_id, config_id)
                
            except Exception as e:
                self.logger.error(f"❌ Error in session cleanup loop: {e}")
    
    def _generate_session_id(self, user_id: str, config_id: str) -> str:
        """Generate a unique session ID"""
        timestamp = datetime.utcnow().isoformat()
        data = f"{user_id}:{config_id}:{timestamp}"
        return hashlib.sha256(data.encode()).hexdigest()[:16]
    
    async def shutdown(self):
        """Gracefully shutdown the broker manager"""
        self.logger.info("🛑 Shutting down Multi-User Broker Manager")
        
        self._running = False
        
        # Cancel background tasks
        for task in self._background_tasks:
            task.cancel()
        
        # Wait for tasks to finish
        if self._background_tasks:
            await asyncio.gather(*self._background_tasks, return_exceptions=True)
        
        # Disconnect all broker sessions
        disconnect_tasks = []
        for user_id, user_sessions in self._user_sessions.items():
            for config_id, session in user_sessions.items():
                disconnect_tasks.append(session.broker_instance.disconnect())
        
        if disconnect_tasks:
            await asyncio.gather(*disconnect_tasks, return_exceptions=True)
        
        # Clear all data structures
        self._user_sessions.clear()
        self._session_locks.clear()
        
        # Close database connections
        if self.db_manager:
            await self.db_manager.close()
        
        self.logger.info("✅ Multi-User Broker Manager shutdown complete")

# Global instance
multi_user_broker_manager = MultiUserBrokerManager()

# Convenience functions for easy access
async def add_user_broker(user_id: str, broker_config_id: str) -> BrokerOperationResult:
    """Add a broker for a user"""
    return await multi_user_broker_manager.add_user_broker(user_id, broker_config_id)

async def remove_user_broker(user_id: str, broker_config_id: str) -> BrokerOperationResult:
    """Remove a broker for a user"""
    return await multi_user_broker_manager.remove_user_broker(user_id, broker_config_id)

async def place_order_for_user(user_id: str, broker_config_id: str, order: BrokerOrder) -> BrokerOperationResult:
    """Place an order for a user"""
    return await multi_user_broker_manager.place_order_for_user(user_id, broker_config_id, order)

async def get_positions_for_user(user_id: str, broker_config_id: str) -> BrokerOperationResult:
    """Get positions for a user"""
    return await multi_user_broker_manager.get_positions_for_user(user_id, broker_config_id)

async def get_balance_for_user(user_id: str, broker_config_id: str) -> BrokerOperationResult:
    """Get balance for a user"""
    return await multi_user_broker_manager.get_balance_for_user(user_id, broker_config_id)

async def get_all_user_positions(user_id: str) -> Dict[str, BrokerOperationResult]:
    """Get positions from all brokers for a user"""
    return await multi_user_broker_manager.get_all_user_positions(user_id) 