"""
Enhanced Database Manager
Centralized database connection and session management with improved error handling
"""

import logging
import redis.asyncio as redis
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Dict, Optional, Any
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.pool import StaticPool
from sqlalchemy import text, event
from sqlalchemy.engine import Engine

from app.core.config import get_settings, AppSettings

logger = logging.getLogger(__name__)

class RedisKeys:
    """Redis key patterns for the trading system"""
    
    # User-specific keys
    USER_NOTIFICATIONS = "user:{user_id}:notifications"
    USER_CHANNEL = "user:{user_id}:channel"
    USER_POSITIONS = "user:{user_id}:positions"
    USER_ORDERS = "user:{user_id}:orders"
    
    # Strategy-specific keys
    STRATEGY_STATUS = "strategy:{strategy_id}:status"
    STRATEGY_COMMANDS = "strategy:{strategy_id}:commands"
    STRATEGY_CHANNEL = "strategy:{strategy_id}:channel"
    STRATEGY_METRICS = "strategy:{strategy_id}:metrics"
    
    # Market data keys
    MARKET_DATA = "market:{symbol}:{exchange}"
    MARKET_DEPTH = "market:{symbol}:{exchange}:depth"
    MARKET_TICKS = "market:{symbol}:{exchange}:ticks"
    
    # Order and execution keys
    ORDER_QUEUE = "orders:queue"
    ORDER_PRIORITY_QUEUE = "orders:priority"
    ORDER_STATUS = "order:{order_id}:status"
    
    # System keys
    SYSTEM_STATUS = "system:status"
    SYSTEM_HEALTH = "system:health"
    BROKER_STATUS = "broker:{broker_name}:status"

class DatabaseManager:
    """
    Enhanced database manager with improved connection handling and monitoring
    """
    
    def __init__(self, settings: Optional[AppSettings] = None):
        self.settings = settings or get_settings()
        self.async_engine = None
        self.async_session_factory = None
        self.redis_client = None
        self._initialized = False
        self._connection_pool_status = {
            'total_connections': 0,
            'active_connections': 0,
            'idle_connections': 0
        }
    
    async def initialize(self, database_url: str = None, redis_url: str = None):
        """Initialize database and Redis connections with enhanced configuration"""
        if self._initialized:
            logger.warning("Database manager already initialized")
            return
        
        try:
            # Use configuration if parameters not provided
            if database_url is None:
                database_url = self.settings.database.url
            if redis_url is None:
                redis_url = self.settings.redis.url
            
            if not database_url:
                raise ValueError("DATABASE_URL must be provided")
            
            # Setup PostgreSQL async engine
            await self._setup_postgresql_engine(database_url)
            
            # Setup Redis connection
            await self._setup_redis_connection(redis_url)
            
            self._initialized = True
            logger.info("✅ Database and Redis connections initialized successfully")
            
            # Log configuration info
            self._log_configuration_info()
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize database connections: {e}")
            raise
    
    async def _setup_postgresql_engine(self, database_url: str):
        """Setup PostgreSQL async engine with optimized configuration"""
        # Use processed URL from configuration that handles SSL for DigitalOcean
        processed_url = self.settings.database.processed_url
        
        # Engine configuration optimized for async operations
        engine_config = {
            'echo': self.settings.database.echo,
            'future': True,
        }
        
        # For async engines, we need to be careful with pool settings
        # Async engines use different pooling mechanisms
        if not self.settings.is_testing():
            # Production/development async settings
            engine_config.update({
                'pool_size': self.settings.database.pool_size,
                'max_overflow': self.settings.database.max_overflow,
                'pool_pre_ping': self.settings.database.pool_pre_ping,
                'pool_recycle': self.settings.database.pool_recycle,
                'poolclass': None,  # Let SQLAlchemy choose the appropriate async pool
            })
        else:
            # Testing configuration with StaticPool
            from sqlalchemy.pool import StaticPool
            engine_config.update({
                'pool_size': 5,
                'max_overflow': 10,
                'poolclass': StaticPool,
            })
        
        # Connection arguments optimized for DigitalOcean managed database
        connect_args = {
            'server_settings': dict(self.settings.database.server_settings),
            'command_timeout': self.settings.database.command_timeout,
        }
        
        # Log if DigitalOcean database detected
        if "ondigitalocean.com" in processed_url:
            logger.info("🔒 DigitalOcean managed database detected with SSL")
        
        # Set application name for connection tracking
        if self.settings.is_testing():
            connect_args['server_settings']['application_name'] += '_test'
        else:
            connect_args['server_settings']['application_name'] = f'{self.settings.app_name}_v{self.settings.app_version}'
        
        engine_config['connect_args'] = connect_args
        
        try:
            self.async_engine = create_async_engine(processed_url, **engine_config)
            logger.info("✅ Async database engine created successfully")
        except Exception as e:
            logger.error(f"❌ Failed to create async engine: {e}")
            raise
        
        # Setup connection pool monitoring
        self._setup_connection_pool_monitoring()
        
        # Create session factory
        self.async_session_factory = async_sessionmaker(
            self.async_engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )
        
        logger.info(f"📊 PostgreSQL async engine configured for DigitalOcean managed database")
        if not self.settings.is_testing():
            logger.info(f"🔗 Pool: size={engine_config.get('pool_size', 'default')}, max_overflow={engine_config.get('max_overflow', 'default')}")
        logger.info(f"⚙️ SSL: {self.settings.database.ssl_mode}, Timeout: {self.settings.database.command_timeout}s")
    
    async def _setup_redis_connection(self, redis_url: str):
        """Setup Redis connection with aioredis for full async support"""
        try:
            # Use aioredis for full async support
            self.redis_client = await redis.from_url(
                redis_url,
                decode_responses=self.settings.redis.decode_responses,
                socket_connect_timeout=self.settings.redis.socket_connect_timeout,
                socket_timeout=self.settings.redis.socket_timeout,
                retry_on_timeout=self.settings.redis.retry_on_timeout,
                socket_keepalive=self.settings.redis.socket_keepalive,
                health_check_interval=self.settings.redis.health_check_interval,
            )
            
            logger.info(f"📊 Redis configured with timeout={self.settings.redis.socket_timeout}s")
            
        except Exception as e:
            logger.error(f"❌ Failed to setup Redis connection: {e}")
            raise
    
    def _setup_connection_pool_monitoring(self):
        """Setup connection pool event monitoring"""
        if not self.async_engine:
            return
        
        @event.listens_for(self.async_engine.sync_engine, "connect")
        def receive_connect(dbapi_connection, connection_record):
            self._connection_pool_status['total_connections'] += 1
            logger.debug(f"🔗 New database connection established (Total: {self._connection_pool_status['total_connections']})")
        
        @event.listens_for(self.async_engine.sync_engine, "checkout")
        def receive_checkout(dbapi_connection, connection_record, connection_proxy):
            self._connection_pool_status['active_connections'] += 1
            logger.debug(f"📤 Connection checked out (Active: {self._connection_pool_status['active_connections']})")
        
        @event.listens_for(self.async_engine.sync_engine, "checkin")
        def receive_checkin(dbapi_connection, connection_record):
            self._connection_pool_status['active_connections'] -= 1
            logger.debug(f"📥 Connection checked in (Active: {self._connection_pool_status['active_connections']})")
    
    def _log_configuration_info(self):
        """Log configuration information"""
        config_info = [
            f"Environment: {self.settings.environment}",
            f"Database Pool Size: {self.settings.database.pool_size}",
            f"Redis URL: {self.settings.redis.url}",
            f"Debug Mode: {self.settings.debug}",
        ]
        
        for info in config_info:
            logger.info(f"⚙️ {info}")
    
    @asynccontextmanager
    async def get_async_session(self) -> AsyncGenerator[AsyncSession, None]:
        """
        Get an async database session with enhanced error handling
        
        Yields:
            AsyncSession: Database session
            
        Raises:
            RuntimeError: If database not initialized
            SQLAlchemyError: For database-related errors
        """
        if not self._initialized:
            raise RuntimeError("❌ Database not initialized. Call initialize() first.")
        
        if not self.async_session_factory:
            raise RuntimeError("❌ Session factory not available")
        
        session = None
        try:
            session = self.async_session_factory()
            
            # Log session creation in debug mode
            if self.settings.debug:
                logger.debug("🔄 Database session created")
            
            yield session
            
            # Commit if no exception occurred
            await session.commit()
            
            if self.settings.debug:
                logger.debug("✅ Database session committed")
                
        except SQLAlchemyError as e:
            if session:
                try:
                    await session.rollback()
                    logger.warning("🔄 Database session rolled back due to error")
                except Exception as rollback_error:
                    logger.error(f"❌ Error during rollback: {rollback_error}")
            
            # Log the specific SQLAlchemy error with more context
            error_msg = f"Database session error: {e}"
            logger.error(error_msg)
            raise
            
        except Exception as e:
            if session:
                try:
                    await session.rollback()
                    logger.warning("🔄 Database session rolled back due to unexpected error")
                except Exception as rollback_error:
                    logger.error(f"❌ Error during rollback: {rollback_error}")
            
            logger.error(f"❌ Unexpected database session error: {e}")
            raise
            
        finally:
            if session:
                try:
                    await session.close()
                    if self.settings.debug:
                        logger.debug("🔒 Database session closed")
                except Exception as close_error:
                    logger.error(f"❌ Error closing session: {close_error}")
    
    async def get_redis(self) -> redis.Redis:
        """
        Get Redis client for real-time notifications and caching
        
        Returns:
            aioredis.Redis: Redis client instance
            
        Raises:
            RuntimeError: If Redis not initialized
        """
        if not self._initialized:
            raise RuntimeError("❌ Redis not initialized. Call initialize() first.")
        
        if not self.redis_client:
            raise RuntimeError("❌ Redis client not available")
        
        return self.redis_client
    
    async def health_check(self) -> Dict[str, Any]:
        """
        Comprehensive health check for database and Redis connections
        
        Returns:
            Dict containing health status and metrics
        """
        health = {
            "database": {"healthy": False, "error": None, "metrics": {}},
            "redis": {"healthy": False, "error": None, "metrics": {}},
            "pool_status": self._connection_pool_status.copy(),
            "overall_healthy": False
        }
        
        # Check database
        try:
            async with self.get_async_session() as session:
                # Test query with timeout
                result = await session.execute(text("SELECT 1 as test_connection"))
                test_value = result.scalar()
                
                if test_value == 1:
                    health["database"]["healthy"] = True
                    
                    # Get additional database metrics
                    try:
                        pool_info = self.async_engine.pool
                        health["database"]["metrics"] = {
                            "pool_size": pool_info.size(),
                            "checked_in": pool_info.checkedin(),
                            "overflow": pool_info.overflow(),
                            "checked_out": pool_info.checkedout(),
                        }
                    except Exception as metrics_error:
                        logger.debug(f"Could not retrieve database metrics: {metrics_error}")
                        
        except Exception as e:
            health["database"]["error"] = str(e)
            logger.error(f"❌ Database health check failed: {e}")
        
        # Check Redis
        try:
            redis_client = await self.get_redis()
            # Use async ping method
            pong = await redis_client.ping()
            
            if pong:
                health["redis"]["healthy"] = True
                
                # Get Redis info asynchronously
                try:
                    info = await redis_client.info()
                    health["redis"]["metrics"] = {
                        "connected_clients": info.get("connected_clients", 0),
                        "used_memory": info.get("used_memory", 0),
                        "uptime_in_seconds": info.get("uptime_in_seconds", 0),
                    }
                except Exception as metrics_error:
                    logger.debug(f"Could not retrieve Redis metrics: {metrics_error}")
                    
        except Exception as e:
            health["redis"]["error"] = str(e)
            logger.error(f"❌ Redis health check failed: {e}")
        
        # Overall health
        health["overall_healthy"] = health["database"]["healthy"] and health["redis"]["healthy"]
        
        return health
    
    async def execute_raw_sql(self, sql: str, parameters: Optional[Dict[str, Any]] = None) -> Any:
        """
        Execute raw SQL with parameters safely
        
        Args:
            sql: SQL query string
            parameters: Optional parameters for the query
            
        Returns:
            Query result
        """
        async with self.get_async_session() as session:
            if parameters:
                result = await session.execute(text(sql), parameters)
            else:
                result = await session.execute(text(sql))
            return result
    
    def get_connection_stats(self) -> Dict[str, Any]:
        """Get current connection pool statistics"""
        if not self.async_engine:
            return {"error": "Engine not initialized"}
        
        try:
            pool = self.async_engine.pool
            return {
                "pool_size": pool.size(),
                "checked_in": pool.checkedin(),
                "overflow": pool.overflow(),
                "checked_out": pool.checkedout(),
                "total_connections": self._connection_pool_status['total_connections'],
                "active_connections": self._connection_pool_status['active_connections'],
            }
        except Exception as e:
            return {"error": f"Could not retrieve stats: {e}"}
    
    async def test_connection(self) -> bool:
        """
        Simple connection test
        
        Returns:
            bool: True if connection successful
        """
        try:
            async with self.get_async_session() as session:
                await session.execute(text("SELECT 1"))
                return True
        except Exception as e:
            logger.error(f"❌ Connection test failed: {e}")
            return False
    
    async def close(self):
        """Close all connections gracefully"""
        closed_components = []
        
        try:
            if self.async_engine:
                await self.async_engine.dispose()
                closed_components.append("PostgreSQL")
        except Exception as e:
            logger.error(f"❌ Error closing database engine: {e}")
        
        try:
            if self.redis_client:
                await self.redis_client.close()
                closed_components.append("Redis")
        except Exception as e:
            logger.error(f"❌ Error closing Redis client: {e}")
        
        self._initialized = False
        self.async_engine = None
        self.async_session_factory = None
        self.redis_client = None
        
        if closed_components:
            logger.info(f"🔒 Closed connections: {', '.join(closed_components)}")
        else:
            logger.info("🔒 Database manager closed (no active connections)")

# Global database manager instance (singleton pattern)
_db_manager_instance: Optional[DatabaseManager] = None

def get_database_manager() -> DatabaseManager:
    """
    Get global database manager instance (singleton)
    
    Returns:
        DatabaseManager: Global instance
    """
    global _db_manager_instance
    
    if _db_manager_instance is None:
        _db_manager_instance = DatabaseManager()
    
    return _db_manager_instance

async def initialize_database() -> DatabaseManager:
    """
    Initialize global database manager
    
    Returns:
        DatabaseManager: Initialized instance
    """
    db_manager = get_database_manager()
    
    if not db_manager._initialized:
        await db_manager.initialize()
    
    return db_manager

# Convenience functions for backward compatibility
async def get_async_session():
    """Get async database session (backward compatibility)"""
    db_manager = get_database_manager()
    async with db_manager.get_async_session() as session:
        yield session

async def get_redis():
    """Get Redis client (backward compatibility)"""
    db_manager = get_database_manager()
    return await db_manager.get_redis()

# Legacy support
DatabaseManager.__doc__ += """

Legacy usage:
    db_manager = DatabaseManager()
    await db_manager.initialize()
    
    async with db_manager.get_async_session() as session:
        # Use session
        pass

New recommended usage:
    from app.database import get_database_manager, initialize_database
    
    # Initialize once at startup
    await initialize_database()
    
    # Use anywhere in the app
    db_manager = get_database_manager()
    async with db_manager.get_async_session() as session:
        # Use session
        pass
"""
