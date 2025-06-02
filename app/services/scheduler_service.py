"""
Scheduler Service - Daily Tasks and Scheduling

This service handles:
1. Daily instrument master downloads at 9:00 AM
2. Market data service initialization
3. Database maintenance tasks
4. Strategy execution scheduling
5. System health checks
"""

import asyncio
import logging
from typing import Dict, List, Optional, Callable, Any
from datetime import datetime, time, timedelta
from dataclasses import dataclass
import pytz
from pathlib import Path

from app.services.market_data_service import get_market_data_service, shutdown_all_services
from app.services.market_data_handler import get_market_data_handler, shutdown_all_handlers
from app.database import get_database

logger = logging.getLogger(__name__)

@dataclass
class ScheduledTask:
    """Represents a scheduled task"""
    name: str
    description: str
    schedule_time: time  # Daily execution time
    callback: Callable
    timezone: str = "Asia/Kolkata"
    enabled: bool = True
    last_run: Optional[datetime] = None
    next_run: Optional[datetime] = None
    error_count: int = 0
    max_retries: int = 3

class SchedulerService:
    """
    Comprehensive scheduler service for trading system
    
    Features:
    - Daily task scheduling
    - Market hours aware scheduling
    - Error handling and retries
    - Task monitoring and logging
    - Timezone support
    """
    
    def __init__(self, timezone: str = "Asia/Kolkata"):
        self.timezone = pytz.timezone(timezone)
        self.tasks: Dict[str, ScheduledTask] = {}
        self.running_tasks: List[asyncio.Task] = []
        self.is_running = False
        
        # Market configuration
        self.market_open_time = time(9, 15)  # 9:15 AM
        self.market_close_time = time(15, 30)  # 3:30 PM
        self.pre_market_time = time(9, 0)     # 9:00 AM
        
        # Initialize default tasks
        self._initialize_default_tasks()
    
    def _initialize_default_tasks(self):
        """Initialize default scheduled tasks"""
        
        # Daily instrument download at 9:00 AM
        self.add_task(
            name="daily_instrument_download",
            description="Download daily instrument master from brokers",
            schedule_time=self.pre_market_time,
            callback=self._download_instruments_task
        )
        
        # Market data service health check at 8:45 AM
        self.add_task(
            name="market_data_health_check",
            description="Health check for market data services",
            schedule_time=time(8, 45),
            callback=self._market_data_health_check
        )
        
        # Database cleanup at 11:30 PM
        self.add_task(
            name="database_cleanup",
            description="Daily database maintenance and cleanup",
            schedule_time=time(23, 30),
            callback=self._database_cleanup_task
        )
        
        # Performance metrics collection at 4:00 PM
        self.add_task(
            name="performance_metrics",
            description="Collect and store daily performance metrics",
            schedule_time=time(16, 0),
            callback=self._collect_performance_metrics
        )
    
    def add_task(self, name: str, description: str, schedule_time: time, 
                 callback: Callable, enabled: bool = True, max_retries: int = 3):
        """Add a new scheduled task"""
        task = ScheduledTask(
            name=name,
            description=description,
            schedule_time=schedule_time,
            callback=callback,
            enabled=enabled,
            max_retries=max_retries
        )
        
        # Calculate next run time
        task.next_run = self._calculate_next_run(task.schedule_time)
        
        self.tasks[name] = task
        logger.info(f"Added scheduled task: {name} at {schedule_time}")
    
    def remove_task(self, name: str):
        """Remove a scheduled task"""
        if name in self.tasks:
            del self.tasks[name]
            logger.info(f"Removed scheduled task: {name}")
    
    def enable_task(self, name: str):
        """Enable a scheduled task"""
        if name in self.tasks:
            self.tasks[name].enabled = True
            self.tasks[name].next_run = self._calculate_next_run(self.tasks[name].schedule_time)
            logger.info(f"Enabled scheduled task: {name}")
    
    def disable_task(self, name: str):
        """Disable a scheduled task"""
        if name in self.tasks:
            self.tasks[name].enabled = False
            self.tasks[name].next_run = None
            logger.info(f"Disabled scheduled task: {name}")
    
    def _calculate_next_run(self, schedule_time: time) -> datetime:
        """Calculate next run time for a task"""
        now = datetime.now(self.timezone)
        next_run = now.replace(
            hour=schedule_time.hour,
            minute=schedule_time.minute,
            second=schedule_time.second,
            microsecond=0
        )
        
        # If the time has passed today, schedule for tomorrow
        if next_run <= now:
            next_run += timedelta(days=1)
        
        return next_run
    
    async def start(self):
        """Start the scheduler service"""
        if self.is_running:
            logger.warning("Scheduler service is already running")
            return
        
        self.is_running = True
        logger.info("Starting scheduler service")
        
        # Start main scheduler loop
        task = asyncio.create_task(self._scheduler_loop())
        self.running_tasks.append(task)
        
        # Start monitoring task
        monitor_task = asyncio.create_task(self._monitor_tasks())
        self.running_tasks.append(monitor_task)
        
        logger.info("Scheduler service started successfully")
    
    async def stop(self):
        """Stop the scheduler service"""
        if not self.is_running:
            return
        
        self.is_running = False
        logger.info("Stopping scheduler service")
        
        # Cancel all running tasks
        for task in self.running_tasks:
            task.cancel()
        
        # Wait for tasks to complete
        if self.running_tasks:
            await asyncio.gather(*self.running_tasks, return_exceptions=True)
        
        self.running_tasks.clear()
        logger.info("Scheduler service stopped")
    
    async def _scheduler_loop(self):
        """Main scheduler loop"""
        while self.is_running:
            try:
                now = datetime.now(self.timezone)
                
                # Check each task
                for task_name, task in self.tasks.items():
                    if not task.enabled or not task.next_run:
                        continue
                    
                    if now >= task.next_run:
                        logger.info(f"Executing scheduled task: {task_name}")
                        asyncio.create_task(self._execute_task(task))
                
                # Sleep for 30 seconds before next check
                await asyncio.sleep(30)
                
            except Exception as e:
                logger.error(f"Error in scheduler loop: {e}")
                await asyncio.sleep(60)  # Wait longer on error
    
    async def _execute_task(self, task: ScheduledTask):
        """Execute a scheduled task"""
        try:
            start_time = datetime.now(self.timezone)
            
            # Execute the task
            if asyncio.iscoroutinefunction(task.callback):
                await task.callback()
            else:
                task.callback()
            
            # Update task status
            task.last_run = start_time
            task.next_run = self._calculate_next_run(task.schedule_time)
            task.error_count = 0
            
            execution_time = (datetime.now(self.timezone) - start_time).total_seconds()
            logger.info(f"Task {task.name} completed successfully in {execution_time:.2f}s")
            
        except Exception as e:
            task.error_count += 1
            logger.error(f"Error executing task {task.name}: {e}")
            
            # Retry logic
            if task.error_count < task.max_retries:
                # Schedule retry in 5 minutes
                task.next_run = datetime.now(self.timezone) + timedelta(minutes=5)
                logger.info(f"Scheduling retry for task {task.name} in 5 minutes")
            else:
                # Too many failures, disable task temporarily
                task.next_run = self._calculate_next_run(task.schedule_time)
                logger.error(f"Task {task.name} failed {task.max_retries} times, scheduling for next day")
    
    async def _monitor_tasks(self):
        """Monitor task execution and health"""
        while self.is_running:
            try:
                await asyncio.sleep(300)  # Check every 5 minutes
                
                now = datetime.now(self.timezone)
                
                for task_name, task in self.tasks.items():
                    if not task.enabled:
                        continue
                    
                    # Check for overdue tasks
                    if task.next_run and now > task.next_run + timedelta(minutes=30):
                        logger.warning(f"Task {task_name} is overdue by {now - task.next_run}")
                    
                    # Check error rates
                    if task.error_count > 0:
                        logger.warning(f"Task {task_name} has {task.error_count} recent errors")
                
            except Exception as e:
                logger.error(f"Error in task monitor: {e}")
    
    # Task implementations
    
    async def _download_instruments_task(self):
        """Download instruments from all configured brokers"""
        try:
            logger.info("Starting daily instrument download")
            
            # Get all active broker configurations
            db = next(get_database())
            result = await db.execute(
                "SELECT id FROM broker_configs WHERE is_active = true"
            )
            broker_configs = result.fetchall()
            
            if not broker_configs:
                logger.warning("No active broker configurations found")
                return
            
            # Download instruments for each broker
            for config in broker_configs:
                try:
                    broker_config_id = config.id
                    market_data_service = await get_market_data_service(broker_config_id)
                    
                    # This will trigger instrument download if needed
                    await market_data_service._download_instruments()
                    
                    logger.info(f"Instrument download completed for broker config: {broker_config_id}")
                    
                except Exception as e:
                    logger.error(f"Failed to download instruments for broker {config.id}: {e}")
            
            logger.info("Daily instrument download completed")
            
        except Exception as e:
            logger.error(f"Error in instrument download task: {e}")
            raise
    
    async def _market_data_health_check(self):
        """Health check for market data services"""
        try:
            logger.info("Starting market data health check")
            
            # Get all active broker configurations
            db = next(get_database())
            result = await db.execute(
                "SELECT id FROM broker_configs WHERE is_active = true"
            )
            broker_configs = result.fetchall()
            
            for config in broker_configs:
                try:
                    broker_config_id = config.id
                    
                    # Check market data service
                    market_data_service = await get_market_data_service(broker_config_id)
                    
                    # Verify Redis connection
                    if market_data_service.redis_client:
                        await market_data_service.redis_client.ping()
                        logger.info(f"Market data service healthy for broker {broker_config_id}")
                    else:
                        logger.warning(f"Redis connection not available for broker {broker_config_id}")
                    
                except Exception as e:
                    logger.error(f"Health check failed for broker {config.id}: {e}")
            
            logger.info("Market data health check completed")
            
        except Exception as e:
            logger.error(f"Error in market data health check: {e}")
            raise
    
    async def _database_cleanup_task(self):
        """Database maintenance and cleanup"""
        try:
            logger.info("Starting database cleanup")
            
            db = next(get_database())
            
            # Clean up old audit logs (keep 90 days)
            await db.execute("""
                DELETE FROM audit_logs 
                WHERE timestamp < NOW() - INTERVAL '90 days'
            """)
            
            # Clean up old market data (keep 1 year)
            await db.execute("""
                DELETE FROM market_data 
                WHERE created_at < NOW() - INTERVAL '1 year'
            """)
            
            # Clean up old user sessions (keep 30 days)
            await db.execute("""
                DELETE FROM user_sessions 
                WHERE expires_at < NOW() - INTERVAL '30 days'
            """)
            
            await db.commit()
            
            logger.info("Database cleanup completed")
            
        except Exception as e:
            logger.error(f"Error in database cleanup task: {e}")
            raise
    
    async def _collect_performance_metrics(self):
        """Collect and store daily performance metrics"""
        try:
            logger.info("Collecting performance metrics")
            
            # This would collect various performance metrics
            # For now, just log that it's running
            
            db = next(get_database())
            
            # Example: Count active strategies
            result = await db.execute(
                "SELECT COUNT(*) as active_strategies FROM strategies WHERE status = 'ACTIVE'"
            )
            active_strategies = result.fetchone().active_strategies
            
            # Example: Count total orders today
            result = await db.execute("""
                SELECT COUNT(*) as orders_today FROM orders 
                WHERE DATE(created_at) = CURRENT_DATE
            """)
            orders_today = result.fetchone().orders_today
            
            logger.info(f"Performance metrics - Active strategies: {active_strategies}, Orders today: {orders_today}")
            
        except Exception as e:
            logger.error(f"Error collecting performance metrics: {e}")
            raise
    
    def get_task_status(self, name: str) -> Optional[Dict[str, Any]]:
        """Get status of a specific task"""
        if name not in self.tasks:
            return None
        
        task = self.tasks[name]
        return {
            'name': task.name,
            'description': task.description,
            'schedule_time': task.schedule_time.isoformat(),
            'enabled': task.enabled,
            'last_run': task.last_run.isoformat() if task.last_run else None,
            'next_run': task.next_run.isoformat() if task.next_run else None,
            'error_count': task.error_count,
            'max_retries': task.max_retries
        }
    
    def get_all_tasks_status(self) -> Dict[str, Dict[str, Any]]:
        """Get status of all tasks"""
        return {name: self.get_task_status(name) for name in self.tasks.keys()}
    
    async def run_task_now(self, name: str) -> bool:
        """Run a specific task immediately"""
        if name not in self.tasks:
            logger.error(f"Task not found: {name}")
            return False
        
        task = self.tasks[name]
        logger.info(f"Running task {name} immediately")
        
        try:
            await self._execute_task(task)
            return True
        except Exception as e:
            logger.error(f"Failed to run task {name}: {e}")
            return False

# Global scheduler instance
_scheduler_service: Optional[SchedulerService] = None

def get_scheduler_service() -> SchedulerService:
    """Get the global scheduler service instance"""
    global _scheduler_service
    if _scheduler_service is None:
        _scheduler_service = SchedulerService()
    return _scheduler_service

async def start_scheduler():
    """Start the global scheduler service"""
    scheduler = get_scheduler_service()
    await scheduler.start()

async def stop_scheduler():
    """Stop the global scheduler service"""
    global _scheduler_service
    if _scheduler_service:
        await _scheduler_service.stop()
        _scheduler_service = None 