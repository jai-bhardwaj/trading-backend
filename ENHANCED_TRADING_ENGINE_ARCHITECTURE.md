# Enhanced Trading Engine Architecture - Independent Strategy Execution

## 🎯 **Architecture Overview**

This design creates a **decoupled, scalable trading engine** where:
- ✅ **Strategies run independently** (separate processes/containers)
- ✅ **Database controls everything** (configuration, commands, monitoring)
- ✅ **Zero downtime** (start/stop strategies without affecting others)
- ✅ **Horizontally scalable** (run multiple instances)
- ✅ **Real-time monitoring** (live performance tracking)

## 🏗️ **System Components**

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Database      │    │  Redis Broker   │    │  Market Data    │
│  (Control)      │    │  (Messaging)    │    │   Service       │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         │                       │                       │
┌─────────────────────────────────────────────────────────────────┐
│                Strategy Engine Manager                          │
│  - Orchestrates all strategies                                 │
│  - Handles lifecycle management                                │
│  - Monitors health and performance                             │
└─────────────────────────────────────────────────────────────────┘
         │
         │
┌────────┴─────────┬─────────────────┬─────────────────┐
│                  │                 │                 │
┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│  Strategy A  │  │  Strategy B  │  │  Strategy C  │  │     ...      │
│ (Independent │  │ (Independent │  │ (Independent │  │ (Independent │
│   Process)   │  │   Process)   │  │   Process)   │  │   Process)   │
└──────────────┘  └──────────────┘  └──────────────┘  └──────────────┘
```

## 📊 **Component Details**

### 1. **Database (Control Plane)**
```sql
-- Strategy configurations
CREATE TABLE strategy_configs (
    id UUID PRIMARY KEY,
    name VARCHAR(100) UNIQUE,
    class_name VARCHAR(100),
    module_path VARCHAR(200),
    config_json JSONB,
    status ENUM('active', 'stopped', 'error'),
    auto_start BOOLEAN DEFAULT true,
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);

-- Strategy commands (start/stop/update)
CREATE TABLE strategy_commands (
    id UUID PRIMARY KEY,
    strategy_id UUID REFERENCES strategy_configs(id),
    command ENUM('start', 'stop', 'restart', 'update'),
    parameters JSONB,
    status ENUM('pending', 'executed', 'failed'),
    created_at TIMESTAMP,
    executed_at TIMESTAMP
);

-- Real-time performance metrics
CREATE TABLE strategy_metrics (
    id UUID PRIMARY KEY,
    strategy_id UUID REFERENCES strategy_configs(id),
    timestamp TIMESTAMP,
    pnl DECIMAL(15,2),
    positions_count INTEGER,
    orders_count INTEGER,
    success_rate DECIMAL(5,2),
    metrics_json JSONB
);
```

### 2. **Redis Message Broker**
```
# Command channels
strategy:commands:{strategy_id}     # Commands to specific strategy
strategy:global:commands           # Global commands to all strategies

# Status channels  
strategy:status:{strategy_id}       # Strategy status updates
strategy:metrics:{strategy_id}      # Real-time metrics
strategy:health                    # Health checks

# Market data (from our existing service)
live_data:{token}                  # Real-time prices
instruments:category:{category}     # Instrument data
```

### 3. **Strategy Engine Manager**
- **Orchestrates** all strategy processes
- **Monitors** health and performance
- **Handles** start/stop/restart commands
- **Manages** configuration updates
- **Provides** unified API interface

## 🚀 **Implementation**

### Core Strategy Engine Manager

```python
# app/core/strategy_engine_manager.py
import asyncio
import json
import subprocess
import psutil
from typing import Dict, List, Optional
import redis.asyncio as aioredis
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

class StrategyEngineManager:
    """Independent strategy execution manager"""
    
    def __init__(self, db_pool, redis_url: str = "redis://localhost:6379"):
        self.db_pool = db_pool
        self.redis_client = None
        self.running_strategies: Dict[str, Dict] = {}
        self.is_running = False
        
    async def initialize(self):
        """Initialize the engine manager"""
        # Connect to Redis
        self.redis_client = aioredis.from_url(
            redis_url, encoding="utf-8", decode_responses=True
        )
        
        # Start command listener
        asyncio.create_task(self.listen_for_commands())
        
        # Start health monitor
        asyncio.create_task(self.monitor_strategies())
        
        # Auto-start configured strategies
        await self.auto_start_strategies()
        
        self.is_running = True
        logger.info("🚀 Strategy Engine Manager initialized")
    
    async def auto_start_strategies(self):
        """Auto-start strategies marked for auto-start"""
        async with self.db_pool.acquire() as conn:
            strategies = await conn.fetch("""
                SELECT id, name, class_name, module_path, config_json 
                FROM strategy_configs 
                WHERE auto_start = true AND status = 'active'
            """)
            
            for strategy in strategies:
                await self.start_strategy(
                    strategy_id=str(strategy['id']),
                    name=strategy['name'],
                    class_name=strategy['class_name'],
                    module_path=strategy['module_path'],
                    config=strategy['config_json']
                )
    
    async def start_strategy(self, strategy_id: str, name: str, 
                           class_name: str, module_path: str, config: dict):
        """Start an independent strategy process"""
        
        if strategy_id in self.running_strategies:
            logger.warning(f"Strategy {name} already running")
            return False
        
        try:
            # Create strategy process
            cmd = [
                'python', '-m', 'app.core.strategy_executor',
                '--strategy-id', strategy_id,
                '--name', name,
                '--class-name', class_name,
                '--module-path', module_path,
                '--config', json.dumps(config)
            ]
            
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            # Track the strategy
            self.running_strategies[strategy_id] = {
                'name': name,
                'process': process,
                'pid': process.pid,
                'started_at': datetime.now(),
                'status': 'running'
            }
            
            # Update database
            await self.update_strategy_status(strategy_id, 'running')
            
            # Publish status
            await self.redis_client.publish(
                f"strategy:status:{strategy_id}",
                json.dumps({'status': 'started', 'pid': process.pid})
            )
            
            logger.info(f"✅ Started strategy {name} (PID: {process.pid})")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to start strategy {name}: {e}")
            await self.update_strategy_status(strategy_id, 'error')
            return False
    
    async def stop_strategy(self, strategy_id: str):
        """Stop a running strategy"""
        
        if strategy_id not in self.running_strategies:
            logger.warning(f"Strategy {strategy_id} not running")
            return False
        
        try:
            strategy_info = self.running_strategies[strategy_id]
            process = strategy_info['process']
            
            # Graceful shutdown
            await self.redis_client.publish(
                f"strategy:commands:{strategy_id}",
                json.dumps({'command': 'shutdown'})
            )
            
            # Wait for graceful shutdown
            try:
                await asyncio.wait_for(process.wait(), timeout=10.0)
            except asyncio.TimeoutError:
                # Force kill if not shutdown gracefully
                process.terminate()
                await process.wait()
            
            # Clean up
            del self.running_strategies[strategy_id]
            await self.update_strategy_status(strategy_id, 'stopped')
            
            logger.info(f"✅ Stopped strategy {strategy_info['name']}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to stop strategy {strategy_id}: {e}")
            return False
    
    async def listen_for_commands(self):
        """Listen for strategy commands from database/API"""
        
        while self.is_running:
            try:
                # Check for pending commands
                async with self.db_pool.acquire() as conn:
                    commands = await conn.fetch("""
                        SELECT id, strategy_id, command, parameters
                        FROM strategy_commands 
                        WHERE status = 'pending'
                        ORDER BY created_at ASC
                    """)
                    
                    for cmd in commands:
                        await self.execute_command(
                            command_id=str(cmd['id']),
                            strategy_id=str(cmd['strategy_id']),
                            command=cmd['command'],
                            parameters=cmd['parameters']
                        )
                
                await asyncio.sleep(1)  # Check every second
                
            except Exception as e:
                logger.error(f"❌ Command listener error: {e}")
                await asyncio.sleep(5)
    
    async def execute_command(self, command_id: str, strategy_id: str, 
                            command: str, parameters: dict):
        """Execute a strategy command"""
        
        try:
            if command == 'start':
                # Get strategy config from database
                async with self.db_pool.acquire() as conn:
                    strategy = await conn.fetchrow("""
                        SELECT name, class_name, module_path, config_json
                        FROM strategy_configs WHERE id = $1
                    """, strategy_id)
                    
                    if strategy:
                        success = await self.start_strategy(
                            strategy_id, strategy['name'],
                            strategy['class_name'], strategy['module_path'],
                            strategy['config_json']
                        )
            
            elif command == 'stop':
                success = await self.stop_strategy(strategy_id)
            
            elif command == 'restart':
                await self.stop_strategy(strategy_id)
                await asyncio.sleep(2)
                # Get fresh config and restart
                success = await self.execute_command(
                    command_id, strategy_id, 'start', parameters
                )
            
            # Mark command as executed
            await self.mark_command_executed(
                command_id, 'executed' if success else 'failed'
            )
            
        except Exception as e:
            logger.error(f"❌ Command execution failed: {e}")
            await self.mark_command_executed(command_id, 'failed')
    
    async def monitor_strategies(self):
        """Monitor running strategies health"""
        
        while self.is_running:
            try:
                for strategy_id, info in list(self.running_strategies.items()):
                    process = info['process']
                    
                    # Check if process is still alive
                    if process.returncode is not None:
                        logger.warning(f"Strategy {info['name']} died unexpectedly")
                        del self.running_strategies[strategy_id]
                        await self.update_strategy_status(strategy_id, 'error')
                    
                    # Get CPU/Memory usage
                    try:
                        proc = psutil.Process(info['pid'])
                        cpu_percent = proc.cpu_percent()
                        memory_mb = proc.memory_info().rss / 1024 / 1024
                        
                        # Publish health metrics
                        await self.redis_client.publish(
                            f"strategy:health",
                            json.dumps({
                                'strategy_id': strategy_id,
                                'name': info['name'],
                                'cpu_percent': cpu_percent,
                                'memory_mb': memory_mb,
                                'status': 'healthy'
                            })
                        )
                    except psutil.NoSuchProcess:
                        pass
                
                await asyncio.sleep(30)  # Check every 30 seconds
                
            except Exception as e:
                logger.error(f"❌ Health monitor error: {e}")
                await asyncio.sleep(60)
    
    async def update_strategy_status(self, strategy_id: str, status: str):
        """Update strategy status in database"""
        async with self.db_pool.acquire() as conn:
            await conn.execute("""
                UPDATE strategy_configs 
                SET status = $1, updated_at = NOW()
                WHERE id = $2
            """, status, strategy_id)
    
    async def mark_command_executed(self, command_id: str, status: str):
        """Mark command as executed in database"""
        async with self.db_pool.acquire() as conn:
            await conn.execute("""
                UPDATE strategy_commands 
                SET status = $1, executed_at = NOW()
                WHERE id = $2
            """, status, command_id)
    
    async def get_strategy_stats(self) -> Dict:
        """Get current strategy statistics"""
        return {
            'total_strategies': len(self.running_strategies),
            'running_strategies': [
                {
                    'id': sid,
                    'name': info['name'],
                    'pid': info['pid'],
                    'started_at': info['started_at'].isoformat(),
                    'status': info['status']
                }
                for sid, info in self.running_strategies.items()
            ]
        }
```

### Independent Strategy Executor

```python
# app/core/strategy_executor.py
import asyncio
import argparse
import json
import signal
import sys
from typing import Dict, Any
import redis.asyncio as aioredis
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class StrategyExecutor:
    """Independent strategy process executor"""
    
    def __init__(self, strategy_id: str, name: str, class_name: str, 
                 module_path: str, config: Dict[str, Any]):
        self.strategy_id = strategy_id
        self.name = name
        self.class_name = class_name
        self.module_path = module_path
        self.config = config
        self.strategy_instance = None
        self.redis_client = None
        self.is_running = False
        self.market_data_service = None
    
    async def initialize(self):
        """Initialize the strategy executor"""
        
        # Connect to Redis
        self.redis_client = aioredis.from_url(
            "redis://localhost:6379", encoding="utf-8", decode_responses=True
        )
        
        # Initialize market data service
        from app.services.categorized_redis_market_data import create_categorized_service
        broker_config = self.config.get('broker_config', {})
        self.market_data_service = await create_categorized_service(broker_config)
        
        # Load and initialize strategy
        await self.load_strategy()
        
        # Listen for commands
        asyncio.create_task(self.listen_for_commands())
        
        # Start metrics reporting
        asyncio.create_task(self.report_metrics())
        
        # Setup signal handlers for graceful shutdown
        signal.signal(signal.SIGTERM, self.handle_shutdown)
        signal.signal(signal.SIGINT, self.handle_shutdown)
        
        logger.info(f"✅ Strategy executor {self.name} initialized")
    
    async def load_strategy(self):
        """Dynamically load and initialize strategy class"""
        try:
            # Import strategy module
            module = __import__(self.module_path, fromlist=[self.class_name])
            strategy_class = getattr(module, self.class_name)
            
            # Create strategy instance
            self.strategy_instance = strategy_class(
                strategy_id=self.strategy_id,
                config=self.config,
                market_data_service=self.market_data_service,
                redis_client=self.redis_client
            )
            
            # Initialize strategy
            await self.strategy_instance.initialize()
            
            logger.info(f"✅ Loaded strategy {self.class_name}")
            
        except Exception as e:
            logger.error(f"❌ Failed to load strategy: {e}")
            raise
    
    async def run(self):
        """Main execution loop"""
        self.is_running = True
        
        try:
            # Start strategy execution
            await self.strategy_instance.start()
            
            # Keep running until shutdown
            while self.is_running:
                await asyncio.sleep(1)
                
        except Exception as e:
            logger.error(f"❌ Strategy execution error: {e}")
            await self.report_error(str(e))
        finally:
            await self.cleanup()
    
    async def listen_for_commands(self):
        """Listen for commands from the engine manager"""
        
        # Subscribe to strategy-specific commands
        pubsub = self.redis_client.pubsub()
        await pubsub.subscribe(f"strategy:commands:{self.strategy_id}")
        
        async for message in pubsub.listen():
            if message['type'] == 'message':
                try:
                    command_data = json.loads(message['data'])
                    command = command_data.get('command')
                    
                    if command == 'shutdown':
                        logger.info(f"🔄 Received shutdown command")
                        self.is_running = False
                        break
                    elif command == 'update_config':
                        new_config = command_data.get('config', {})
                        await self.update_config(new_config)
                    elif command == 'pause':
                        await self.strategy_instance.pause()
                    elif command == 'resume':
                        await self.strategy_instance.resume()
                        
                except Exception as e:
                    logger.error(f"❌ Command processing error: {e}")
    
    async def report_metrics(self):
        """Report strategy metrics periodically"""
        
        while self.is_running:
            try:
                if self.strategy_instance and hasattr(self.strategy_instance, 'get_metrics'):
                    metrics = await self.strategy_instance.get_metrics()
                    
                    # Publish to Redis
                    await self.redis_client.publish(
                        f"strategy:metrics:{self.strategy_id}",
                        json.dumps({
                            'strategy_id': self.strategy_id,
                            'timestamp': datetime.now().isoformat(),
                            'metrics': metrics
                        })
                    )
                
                await asyncio.sleep(60)  # Report every minute
                
            except Exception as e:
                logger.error(f"❌ Metrics reporting error: {e}")
                await asyncio.sleep(60)
    
    async def update_config(self, new_config: Dict[str, Any]):
        """Update strategy configuration"""
        try:
            self.config.update(new_config)
            if hasattr(self.strategy_instance, 'update_config'):
                await self.strategy_instance.update_config(new_config)
            logger.info(f"✅ Updated configuration for {self.name}")
        except Exception as e:
            logger.error(f"❌ Config update failed: {e}")
    
    async def report_error(self, error_message: str):
        """Report strategy error"""
        await self.redis_client.publish(
            f"strategy:status:{self.strategy_id}",
            json.dumps({
                'status': 'error',
                'error': error_message,
                'timestamp': datetime.now().isoformat()
            })
        )
    
    def handle_shutdown(self, signum, frame):
        """Handle shutdown signals"""
        logger.info(f"🔄 Received shutdown signal {signum}")
        self.is_running = False
    
    async def cleanup(self):
        """Clean up resources"""
        try:
            if self.strategy_instance and hasattr(self.strategy_instance, 'cleanup'):
                await self.strategy_instance.cleanup()
            
            if self.market_data_service:
                await self.market_data_service.cleanup()
            
            if self.redis_client:
                await self.redis_client.close()
                
            logger.info(f"🧹 Strategy {self.name} cleaned up")
            
        except Exception as e:
            logger.error(f"❌ Cleanup error: {e}")

# Command line entry point
async def main():
    parser = argparse.ArgumentParser(description='Strategy Executor')
    parser.add_argument('--strategy-id', required=True)
    parser.add_argument('--name', required=True)
    parser.add_argument('--class-name', required=True)
    parser.add_argument('--module-path', required=True)
    parser.add_argument('--config', required=True)
    
    args = parser.parse_args()
    config = json.loads(args.config)
    
    executor = StrategyExecutor(
        strategy_id=args.strategy_id,
        name=args.name,
        class_name=args.class_name,
        module_path=args.module_path,
        config=config
    )
    
    await executor.initialize()
    await executor.run()

if __name__ == "__main__":
    asyncio.run(main())
```

This architecture gives you:

1. **🔗 Loose Coupling**: Strategies run independently but are controlled via database
2. **📈 Scalability**: Start/stop strategies without affecting others
3. **🛡️ Fault Tolerance**: One strategy failure doesn't crash the system
4. **⚡ Real-time Control**: Instant start/stop/configure via database commands
5. **📊 Complete Monitoring**: Real-time metrics and health monitoring
6. **🔄 Hot Deployment**: Update strategies without system restart

Would you like me to continue with the API layer and strategy base classes? 