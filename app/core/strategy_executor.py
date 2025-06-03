"""
Strategy Executor for Independent Strategy Processes
Works with the new cleaned schema and manages individual strategy execution.
"""

import asyncio
import json
import logging
import sys
import traceback
from datetime import datetime
from typing import Dict, Any, Optional
import importlib
import redis.asyncio as redis
from sqlalchemy import text

from app.database import db_manager, RedisKeys
from app.core.notification_service import NotificationService

logger = logging.getLogger(__name__)

class StrategyExecutor:
    """
    Executes a single trading strategy as an independent process.
    Handles communication with the main engine via Redis and database.
    """
    
    def __init__(self, config_id: str, user_id: str, strategy_id: Optional[str],
                 class_name: str, module_path: str, config: Dict[str, Any]):
        self.config_id = config_id
        self.user_id = user_id
        self.strategy_id = strategy_id
        self.class_name = class_name
        self.module_path = module_path
        self.config = config
        
        self.strategy_instance = None
        self.redis_client: Optional[redis.Redis] = None
        self.notification_service: Optional[NotificationService] = None
        self.running = False
        self.paused = False
        self.process = None
        
    async def start(self) -> asyncio.subprocess.Process:
        """Start the strategy process."""
        try:
            # Create the command to run this strategy
            cmd = [
                sys.executable, 
                "-m", "app.core.strategy_executor",
                "--config-id", self.config_id,
                "--user-id", self.user_id,
                "--class-name", self.class_name,
                "--module-path", self.module_path,
                "--config", json.dumps(self.config)
            ]
            
            if self.strategy_id:
                cmd.extend(["--strategy-id", self.strategy_id])
            
            # Start the subprocess
            self.process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            logger.info(f"Started strategy process {self.config_id} with PID {self.process.pid}")
            return self.process
            
        except Exception as e:
            logger.error(f"Failed to start strategy process {self.config_id}: {e}")
            raise
    
    async def stop(self):
        """Stop the strategy process."""
        try:
            if self.process and self.process.returncode is None:
                self.process.terminate()
                try:
                    await asyncio.wait_for(self.process.wait(), timeout=10)
                except asyncio.TimeoutError:
                    logger.warning(f"Strategy process {self.config_id} did not terminate gracefully, killing...")
                    self.process.kill()
                    await self.process.wait()
            
            logger.info(f"Stopped strategy process {self.config_id}")
            
        except Exception as e:
            logger.error(f"Failed to stop strategy process {self.config_id}: {e}")
            raise
    
    async def pause(self):
        """Pause the strategy execution."""
        try:
            # Send pause command via Redis
            redis_client = await db_manager.get_redis()
            await redis_client.publish(
                RedisKeys.STRATEGY_COMMANDS.format(strategy_id=self.config_id),
                json.dumps({"command": "PAUSE"})
            )
            
            logger.info(f"Sent pause command to strategy {self.config_id}")
            
        except Exception as e:
            logger.error(f"Failed to pause strategy {self.config_id}: {e}")
            raise
    
    async def resume(self):
        """Resume the strategy execution."""
        try:
            # Send resume command via Redis
            redis_client = await db_manager.get_redis()
            await redis_client.publish(
                RedisKeys.STRATEGY_COMMANDS.format(strategy_id=self.config_id),
                json.dumps({"command": "RESUME"})
            )
            
            logger.info(f"Sent resume command to strategy {self.config_id}")
            
        except Exception as e:
            logger.error(f"Failed to resume strategy {self.config_id}: {e}")
            raise

class StrategyProcessRunner:
    """
    Runs inside the strategy process to execute the actual strategy logic.
    """
    
    def __init__(self, config_id: str, user_id: str, strategy_id: Optional[str],
                 class_name: str, module_path: str, config: Dict[str, Any]):
        self.config_id = config_id
        self.user_id = user_id
        self.strategy_id = strategy_id
        self.class_name = class_name
        self.module_path = module_path
        self.config = config
        
        self.strategy_instance = None
        self.redis_client: Optional[redis.Redis] = None
        self.notification_service: Optional[NotificationService] = None
        self.running = False
        self.paused = False
        
    async def initialize(self):
        """Initialize the strategy process."""
        try:
            # Initialize database and Redis connections
            from app.database import init_database
            init_database()
            
            # Get Redis client
            self.redis_client = await db_manager.get_redis()
            
            # Initialize notification service
            self.notification_service = NotificationService()
            await self.notification_service.initialize()
            
            # Load and instantiate the strategy class
            await self._load_strategy()
            
            logger.info(f"Strategy process {self.config_id} initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize strategy process {self.config_id}: {e}")
            raise
    
    async def _load_strategy(self):
        """Load the strategy class dynamically."""
        try:
            # Import the module
            module = importlib.import_module(self.module_path)
            
            # Get the strategy class
            strategy_class = getattr(module, self.class_name)
            
            # Create strategy instance
            self.strategy_instance = strategy_class(
                config_id=self.config_id,
                user_id=self.user_id,
                strategy_id=self.strategy_id,
                config=self.config
            )
            
            # Initialize the strategy
            if hasattr(self.strategy_instance, 'initialize'):
                await self.strategy_instance.initialize()
            
            logger.info(f"Loaded strategy class {self.class_name} from {self.module_path}")
            
        except Exception as e:
            logger.error(f"Failed to load strategy class {self.class_name}: {e}")
            raise
    
    async def run(self):
        """Main execution loop for the strategy."""
        try:
            await self.initialize()
            self.running = True
            
            # Start background tasks
            tasks = [
                asyncio.create_task(self._execution_loop()),
                asyncio.create_task(self._command_listener()),
                asyncio.create_task(self._heartbeat_sender()),
                asyncio.create_task(self._metrics_reporter())
            ]
            
            # Send strategy started notification
            await self.notification_service.send_realtime_notification(
                user_id=self.user_id,
                type="STRATEGY_STARTED",
                title="Strategy Started",
                message=f"Strategy {self.class_name} is now running",
                data={"config_id": self.config_id, "strategy_id": self.strategy_id}
            )
            
            # Wait for all tasks
            await asyncio.gather(*tasks)
            
        except Exception as e:
            logger.error(f"Strategy execution error: {e}")
            await self._handle_error(e)
        finally:
            await self._cleanup()
    
    async def _execution_loop(self):
        """Main strategy execution loop."""
        while self.running:
            try:
                if not self.paused and self.strategy_instance:
                    # Execute strategy logic
                    if hasattr(self.strategy_instance, 'execute'):
                        await self.strategy_instance.execute()
                    
                    # Strategy-specific sleep interval
                    sleep_interval = getattr(self.strategy_instance, 'execution_interval', 1)
                    await asyncio.sleep(sleep_interval)
                else:
                    # If paused, sleep longer
                    await asyncio.sleep(5)
                    
            except Exception as e:
                logger.error(f"Strategy execution error: {e}")
                await self._handle_error(e)
                await asyncio.sleep(10)  # Wait before retrying
    
    async def _command_listener(self):
        """Listen for commands from the strategy engine."""
        try:
            # Subscribe to strategy command channel
            channel = RedisKeys.STRATEGY_COMMANDS.format(strategy_id=self.config_id)
            pubsub = self.redis_client.pubsub()
            await pubsub.subscribe(channel)
            
            while self.running:
                message = await pubsub.get_message(timeout=1.0)
                if message and message['type'] == 'message':
                    try:
                        command_data = json.loads(message['data'])
                        command = command_data.get('command')
                        
                        if command == 'PAUSE':
                            self.paused = True
                            logger.info(f"Strategy {self.config_id} paused")
                            
                        elif command == 'RESUME':
                            self.paused = False
                            logger.info(f"Strategy {self.config_id} resumed")
                            
                        elif command == 'STOP':
                            self.running = False
                            logger.info(f"Strategy {self.config_id} received stop command")
                            
                    except Exception as e:
                        logger.error(f"Error processing command: {e}")
                        
        except Exception as e:
            logger.error(f"Command listener error: {e}")
    
    async def _heartbeat_sender(self):
        """Send periodic heartbeat to indicate the strategy is alive."""
        while self.running:
            try:
                # Send heartbeat via Redis
                heartbeat_data = {
                    "config_id": self.config_id,
                    "timestamp": datetime.now().isoformat(),
                    "status": "PAUSED" if self.paused else "ACTIVE",
                    "process_id": os.getpid() if 'os' in globals() else None
                }
                
                await self.redis_client.setex(
                    RedisKeys.STRATEGY_STATUS.format(strategy_id=self.config_id),
                    60,  # TTL of 60 seconds
                    json.dumps(heartbeat_data)
                )
                
                await asyncio.sleep(30)  # Send heartbeat every 30 seconds
                
            except Exception as e:
                logger.error(f"Heartbeat sender error: {e}")
                await asyncio.sleep(10)
    
    async def _metrics_reporter(self):
        """Report strategy metrics to the database."""
        while self.running:
            try:
                if self.strategy_instance and hasattr(self.strategy_instance, 'get_metrics'):
                    metrics = await self.strategy_instance.get_metrics()
                    
                    # Save metrics to database
                    async with db_manager.get_async_session() as session:
                        await session.execute(text("""
                            INSERT INTO strategy_metrics 
                            (strategy_config_id, timestamp, pnl, positions_count, 
                             orders_count, success_rate, metrics_json)
                            VALUES (:config_id, NOW(), :pnl, :positions_count, 
                                    :orders_count, :success_rate, :metrics_json)
                        """), {
                            "config_id": self.config_id,
                            "pnl": metrics.get('pnl', 0),
                            "positions_count": metrics.get('positions_count', 0),
                            "orders_count": metrics.get('orders_count', 0),
                            "success_rate": metrics.get('success_rate', 0),
                            "metrics_json": json.dumps(metrics)
                        })
                        await session.commit()
                
                # Report metrics every 5 minutes
                await asyncio.sleep(300)
                
            except Exception as e:
                logger.error(f"Metrics reporter error: {e}")
                await asyncio.sleep(60)
    
    async def _handle_error(self, error: Exception):
        """Handle strategy execution errors."""
        try:
            error_data = {
                "config_id": self.config_id,
                "error": str(error),
                "traceback": traceback.format_exc(),
                "timestamp": datetime.now().isoformat()
            }
            
            # Send error notification
            await self.notification_service.send_realtime_notification(
                user_id=self.user_id,
                type="STRATEGY_ERROR",
                title="Strategy Error",
                message=f"Strategy {self.class_name} encountered an error: {str(error)}",
                data=error_data
            )
            
            # Update strategy status to ERROR
            async with db_manager.get_async_session() as session:
                await session.execute(text("""
                    UPDATE strategy_configs 
                    SET status = 'ERROR' 
                    WHERE id = :config_id
                """), {"config_id": self.config_id})
                await session.commit()
            
        except Exception as e:
            logger.error(f"Error handling error: {e}")
    
    async def _cleanup(self):
        """Cleanup resources when strategy stops."""
        try:
            self.running = False
            
            # Cleanup strategy instance
            if self.strategy_instance and hasattr(self.strategy_instance, 'cleanup'):
                await self.strategy_instance.cleanup()
            
            # Close Redis connection
            if self.redis_client:
                await self.redis_client.close()
            
            # Send strategy stopped notification
            if self.notification_service:
                await self.notification_service.send_realtime_notification(
                    user_id=self.user_id,
                    type="STRATEGY_STOPPED",
                    title="Strategy Stopped",
                    message=f"Strategy {self.class_name} has stopped",
                    data={"config_id": self.config_id, "strategy_id": self.strategy_id}
                )
            
            logger.info(f"Strategy process {self.config_id} cleanup completed")
            
        except Exception as e:
            logger.error(f"Cleanup error: {e}")

# Entry point for when this module is run as a subprocess
if __name__ == "__main__":
    import argparse
    import os
    
    parser = argparse.ArgumentParser(description="Run a trading strategy process")
    parser.add_argument("--config-id", required=True, help="Strategy config ID")
    parser.add_argument("--user-id", required=True, help="User ID")
    parser.add_argument("--strategy-id", help="Strategy ID (optional)")
    parser.add_argument("--class-name", required=True, help="Strategy class name")
    parser.add_argument("--module-path", required=True, help="Module path")
    parser.add_argument("--config", required=True, help="Strategy configuration JSON")
    
    args = parser.parse_args()
    
    # Parse configuration
    config = json.loads(args.config)
    
    # Create and run the strategy process
    runner = StrategyProcessRunner(
        config_id=args.config_id,
        user_id=args.user_id,
        strategy_id=args.strategy_id,
        class_name=args.class_name,
        module_path=args.module_path,
        config=config
    )
    
    # Run the strategy
    asyncio.run(runner.run()) 