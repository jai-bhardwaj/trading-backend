"""
Enhanced Strategy Engine Manager for Live Trading
Works with the new cleaned schema and hybrid notification system.
"""

import asyncio
import json
import logging
import signal
import time
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum
import psutil
import redis.asyncio as redis
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import db_manager, RedisKeys
from app.core.strategy_executor import StrategyExecutor
from app.core.notification_service import NotificationService

logger = logging.getLogger(__name__)

class StrategyConfigStatus(Enum):
    ACTIVE = "ACTIVE"
    STOPPED = "STOPPED"
    ERROR = "ERROR"
    PAUSED = "PAUSED"

class StrategyCommandType(Enum):
    START = "START"
    STOP = "STOP"
    RESTART = "RESTART"
    PAUSE = "PAUSE"
    RESUME = "RESUME"
    UPDATE_CONFIG = "UPDATE_CONFIG"

class CommandStatus(Enum):
    PENDING = "PENDING"
    EXECUTED = "EXECUTED"
    FAILED = "FAILED"

@dataclass
class StrategyProcess:
    """Represents a running strategy process."""
    config_id: str
    process: asyncio.subprocess.Process
    executor: StrategyExecutor
    status: StrategyConfigStatus
    started_at: datetime
    last_heartbeat: datetime
    error_count: int = 0

class StrategyEngineManager:
    """
    Manages the lifecycle of trading strategies as independent processes.
    Works with the new cleaned schema and hybrid notification system.
    """
    
    def __init__(self):
        self.processes: Dict[str, StrategyProcess] = {}
        self.redis_client: Optional[redis.Redis] = None
        self.notification_service: Optional[NotificationService] = None
        self.running = False
        self.heartbeat_interval = 30  # seconds
        self.max_retries = 3
        
    async def initialize(self):
        """Initialize the strategy engine manager."""
        try:
            # Get Redis client for real-time communication
            self.redis_client = await db_manager.get_redis()
            
            # Initialize notification service
            self.notification_service = NotificationService()
            await self.notification_service.initialize()
            
            # Set up signal handlers for graceful shutdown
            signal.signal(signal.SIGTERM, self._signal_handler)
            signal.signal(signal.SIGINT, self._signal_handler)
            
            self.running = True
            logger.info("Strategy Engine Manager initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize Strategy Engine Manager: {e}")
            raise
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals gracefully."""
        logger.info(f"Received signal {signum}, initiating graceful shutdown...")
        asyncio.create_task(self.shutdown())
    
    async def start(self):
        """Start the strategy engine manager."""
        await self.initialize()
        
        # Start background tasks
        tasks = [
            asyncio.create_task(self._command_processor()),
            asyncio.create_task(self._heartbeat_monitor()),
            asyncio.create_task(self._auto_start_strategies()),
        ]
        
        try:
            # Wait for all tasks to complete
            await asyncio.gather(*tasks)
        except Exception as e:
            logger.error(f"Strategy Engine Manager error: {e}")
        finally:
            await self.shutdown()
    
    async def _auto_start_strategies(self):
        """Auto-start strategies marked for auto-start."""
        try:
            async with db_manager.get_async_session() as session:
                # Query strategies with auto_start = true
                query = text("""
                    SELECT id, user_id, strategy_id, name, class_name, 
                           module_path, config_json, status, auto_start
                    FROM strategy_configs 
                    WHERE auto_start = true AND status = 'ACTIVE'
                """)
                
                result = await session.execute(query)
                configs = result.fetchall()
                
                for config in configs:
                    await self._start_strategy_process(
                        config_id=config.id,
                        user_id=config.user_id,
                        strategy_id=config.strategy_id,
                        class_name=config.class_name,
                        module_path=config.module_path,
                        config_json=config.config_json
                    )
                    
                    # Small delay between starts
                    await asyncio.sleep(1)
                    
        except Exception as e:
            logger.error(f"Auto-start strategies error: {e}")
    
    async def _command_processor(self):
        """Process strategy commands from the database."""
        while self.running:
            try:
                async with db_manager.get_async_session() as session:
                    # Get pending commands
                    query = text("""
                        SELECT sc.id, sc.strategy_config_id, sc.command, sc.parameters,
                               config.user_id, config.strategy_id, config.class_name,
                               config.module_path, config.config_json
                        FROM strategy_commands sc
                        JOIN strategy_configs config ON sc.strategy_config_id = config.id
                        WHERE sc.status = 'PENDING'
                        ORDER BY sc.created_at ASC
                        LIMIT 10
                    """)
                    
                    result = await session.execute(query)
                    commands = result.fetchall()
                    
                    for cmd in commands:
                        await self._execute_command(session, cmd)
                
                # Check for new commands every 2 seconds
                await asyncio.sleep(2)
                
            except Exception as e:
                logger.error(f"Command processor error: {e}")
                await asyncio.sleep(5)
    
    async def _execute_command(self, session: AsyncSession, command):
        """Execute a strategy command."""
        command_id = command.id
        config_id = command.strategy_config_id
        cmd_type = StrategyCommandType(command.command)
        
        try:
            logger.info(f"Executing command {cmd_type.value} for strategy config {config_id}")
            
            if cmd_type == StrategyCommandType.START:
                await self._start_strategy_process(
                    config_id=config_id,
                    user_id=command.user_id,
                    strategy_id=command.strategy_id,
                    class_name=command.class_name,
                    module_path=command.module_path,
                    config_json=command.config_json
                )
                
            elif cmd_type == StrategyCommandType.STOP:
                await self._stop_strategy_process(config_id)
                
            elif cmd_type == StrategyCommandType.RESTART:
                await self._stop_strategy_process(config_id)
                await asyncio.sleep(2)
                await self._start_strategy_process(
                    config_id=config_id,
                    user_id=command.user_id,
                    strategy_id=command.strategy_id,
                    class_name=command.class_name,
                    module_path=command.module_path,
                    config_json=command.config_json
                )
                
            elif cmd_type == StrategyCommandType.PAUSE:
                await self._pause_strategy_process(config_id)
                
            elif cmd_type == StrategyCommandType.RESUME:
                await self._resume_strategy_process(config_id)
            
            # Mark command as executed
            await session.execute(text("""
                UPDATE strategy_commands 
                SET status = 'EXECUTED', executed_at = NOW()
                WHERE id = :command_id
            """), {"command_id": command_id})
            
            await session.commit()
            
        except Exception as e:
            logger.error(f"Failed to execute command {command_id}: {e}")
            
            # Mark command as failed
            await session.execute(text("""
                UPDATE strategy_commands 
                SET status = 'FAILED', executed_at = NOW()
                WHERE id = :command_id
            """), {"command_id": command_id})
            
            await session.commit()
    
    async def _start_strategy_process(self, config_id: str, user_id: str, 
                                    strategy_id: Optional[str], class_name: str,
                                    module_path: str, config_json: Dict[str, Any]):
        """Start a new strategy process."""
        try:
            # Check if already running
            if config_id in self.processes:
                logger.warning(f"Strategy {config_id} is already running")
                return
            
            # Create strategy executor
            executor = StrategyExecutor(
                config_id=config_id,
                user_id=user_id,
                strategy_id=strategy_id,
                class_name=class_name,
                module_path=module_path,
                config=config_json
            )
            
            # Start the process
            process = await executor.start()
            
            # Track the process
            strategy_process = StrategyProcess(
                config_id=config_id,
                process=process,
                executor=executor,
                status=StrategyConfigStatus.ACTIVE,
                started_at=datetime.now(),
                last_heartbeat=datetime.now()
            )
            
            self.processes[config_id] = strategy_process
            
            # Update status in database
            async with db_manager.get_async_session() as session:
                await session.execute(text("""
                    UPDATE strategy_configs 
                    SET status = 'ACTIVE' 
                    WHERE id = :config_id
                """), {"config_id": config_id})
                await session.commit()
            
            # Send notification
            await self.notification_service.send_realtime_notification(
                user_id=user_id,
                type="STRATEGY_STARTED",
                title="Strategy Started",
                message=f"Strategy {class_name} started successfully",
                data={"config_id": config_id, "strategy_id": strategy_id}
            )
            
            logger.info(f"Strategy process {config_id} started successfully")
            
        except Exception as e:
            logger.error(f"Failed to start strategy process {config_id}: {e}")
            
            # Update status to ERROR
            async with db_manager.get_async_session() as session:
                await session.execute(text("""
                    UPDATE strategy_configs 
                    SET status = 'ERROR' 
                    WHERE id = :config_id
                """), {"config_id": config_id})
                await session.commit()
            
            raise
    
    async def _stop_strategy_process(self, config_id: str):
        """Stop a strategy process."""
        try:
            if config_id not in self.processes:
                logger.warning(f"Strategy {config_id} is not running")
                return
            
            strategy_process = self.processes[config_id]
            
            # Stop the executor
            await strategy_process.executor.stop()
            
            # Remove from tracking
            del self.processes[config_id]
            
            # Update status in database
            async with db_manager.get_async_session() as session:
                await session.execute(text("""
                    UPDATE strategy_configs 
                    SET status = 'STOPPED' 
                    WHERE id = :config_id
                """), {"config_id": config_id})
                await session.commit()
            
            logger.info(f"Strategy process {config_id} stopped successfully")
            
        except Exception as e:
            logger.error(f"Failed to stop strategy process {config_id}: {e}")
            raise
    
    async def _pause_strategy_process(self, config_id: str):
        """Pause a strategy process."""
        try:
            if config_id not in self.processes:
                logger.warning(f"Strategy {config_id} is not running")
                return
            
            strategy_process = self.processes[config_id]
            await strategy_process.executor.pause()
            strategy_process.status = StrategyConfigStatus.PAUSED
            
            # Update status in database
            async with db_manager.get_async_session() as session:
                await session.execute(text("""
                    UPDATE strategy_configs 
                    SET status = 'PAUSED' 
                    WHERE id = :config_id
                """), {"config_id": config_id})
                await session.commit()
            
            logger.info(f"Strategy process {config_id} paused")
            
        except Exception as e:
            logger.error(f"Failed to pause strategy process {config_id}: {e}")
            raise
    
    async def _resume_strategy_process(self, config_id: str):
        """Resume a paused strategy process."""
        try:
            if config_id not in self.processes:
                logger.warning(f"Strategy {config_id} is not running")
                return
            
            strategy_process = self.processes[config_id]
            await strategy_process.executor.resume()
            strategy_process.status = StrategyConfigStatus.ACTIVE
            
            # Update status in database
            async with db_manager.get_async_session() as session:
                await session.execute(text("""
                    UPDATE strategy_configs 
                    SET status = 'ACTIVE' 
                    WHERE id = :config_id
                """), {"config_id": config_id})
                await session.commit()
            
            logger.info(f"Strategy process {config_id} resumed")
            
        except Exception as e:
            logger.error(f"Failed to resume strategy process {config_id}: {e}")
            raise
    
    async def _heartbeat_monitor(self):
        """Monitor strategy process health."""
        while self.running:
            try:
                current_time = datetime.now()
                dead_processes = []
                
                for config_id, strategy_process in self.processes.items():
                    # Check if process is still alive
                    if strategy_process.process.returncode is not None:
                        logger.warning(f"Strategy process {config_id} has died")
                        dead_processes.append(config_id)
                        continue
                    
                    # Check heartbeat
                    time_since_heartbeat = (current_time - strategy_process.last_heartbeat).total_seconds()
                    if time_since_heartbeat > self.heartbeat_interval * 2:
                        logger.warning(f"Strategy process {config_id} missed heartbeat")
                        
                        # Try to restart if not too many errors
                        if strategy_process.error_count < self.max_retries:
                            strategy_process.error_count += 1
                            logger.info(f"Attempting to restart strategy {config_id}")
                            # Could implement restart logic here
                        else:
                            logger.error(f"Strategy process {config_id} exceeded max retries")
                            dead_processes.append(config_id)
                
                # Clean up dead processes
                for config_id in dead_processes:
                    await self._cleanup_dead_process(config_id)
                
                await asyncio.sleep(self.heartbeat_interval)
                
            except Exception as e:
                logger.error(f"Heartbeat monitor error: {e}")
                await asyncio.sleep(10)
    
    async def _cleanup_dead_process(self, config_id: str):
        """Clean up a dead strategy process."""
        try:
            if config_id in self.processes:
                del self.processes[config_id]
            
            # Update status in database
            async with db_manager.get_async_session() as session:
                await session.execute(text("""
                    UPDATE strategy_configs 
                    SET status = 'ERROR' 
                    WHERE id = :config_id
                """), {"config_id": config_id})
                await session.commit()
            
            logger.info(f"Cleaned up dead process {config_id}")
            
        except Exception as e:
            logger.error(f"Failed to cleanup dead process {config_id}: {e}")
    
    async def get_strategy_status(self, config_id: str) -> Dict[str, Any]:
        """Get status of a specific strategy."""
        if config_id not in self.processes:
            return {"status": "STOPPED", "running": False}
        
        strategy_process = self.processes[config_id]
        
        return {
            "status": strategy_process.status.value,
            "running": True,
            "started_at": strategy_process.started_at.isoformat(),
            "last_heartbeat": strategy_process.last_heartbeat.isoformat(),
            "error_count": strategy_process.error_count,
            "process_id": strategy_process.process.pid
        }
    
    async def get_all_strategies_status(self) -> Dict[str, Dict[str, Any]]:
        """Get status of all strategies."""
        status = {}
        for config_id in self.processes:
            status[config_id] = await self.get_strategy_status(config_id)
        return status
    
    async def shutdown(self):
        """Gracefully shutdown all strategy processes."""
        logger.info("Shutting down Strategy Engine Manager...")
        self.running = False
        
        # Stop all strategy processes
        for config_id in list(self.processes.keys()):
            try:
                await self._stop_strategy_process(config_id)
            except Exception as e:
                logger.error(f"Error stopping strategy {config_id}: {e}")
        
        # Close Redis connection
        if self.redis_client:
            await self.redis_client.close()
        
        logger.info("Strategy Engine Manager shutdown complete")

# Global instance
strategy_engine_manager = StrategyEngineManager()

# Convenience functions
async def start_strategy_engine():
    """Start the strategy engine manager."""
    await strategy_engine_manager.start()

async def get_strategy_status(config_id: str):
    """Get status of a specific strategy."""
    return await strategy_engine_manager.get_strategy_status(config_id)

async def get_all_strategies_status():
    """Get status of all strategies."""
    return await strategy_engine_manager.get_all_strategies_status() 