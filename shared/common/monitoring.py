"""
Monitoring and Observability Module
Provides metrics collection, alerting, and distributed tracing
"""

import asyncio
import time
import logging
import json
from typing import Dict, Any, Optional, List, Callable
from datetime import datetime, timedelta
import redis.asyncio as redis
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)

class AlertLevel(Enum):
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"

@dataclass
class Alert:
    id: str
    level: AlertLevel
    title: str
    message: str
    service: str
    timestamp: datetime
    resolved: bool = False
    metadata: Dict = field(default_factory=dict)

class MetricsCollector:
    """Collect and store system metrics"""
    
    def __init__(self, redis_client: redis.Redis):
        self.redis_client = redis_client
        self.metrics_buffer = []
        self.buffer_size = 100
    
    async def record_metric(self, name: str, value: float, tags: Dict = None):
        """Record a metric"""
        metric = {
            "name": name,
            "value": value,
            "tags": tags or {},
            "timestamp": time.time()
        }
        
        self.metrics_buffer.append(metric)
        
        # Flush buffer when full
        if len(self.metrics_buffer) >= self.buffer_size:
            await self._flush_buffer()
    
    async def _flush_buffer(self):
        """Flush metrics buffer to Redis"""
        if not self.metrics_buffer:
            return
        
        # Store metrics in Redis
        for metric in self.metrics_buffer:
            key = f"metrics:{metric['name']}:{int(metric['timestamp'])}"
            await self.redis_client.setex(key, 86400, json.dumps(metric))  # 24h TTL
        
        self.metrics_buffer.clear()
    
    async def get_metric_stats(self, name: str, window_minutes: int = 60) -> Dict:
        """Get metric statistics for a time window"""
        cutoff_time = time.time() - (window_minutes * 60)
        
        # Get metrics from Redis
        pattern = f"metrics:{name}:*"
        keys = await self.redis_client.keys(pattern)
        
        values = []
        for key in keys:
            metric_data = await self.redis_client.get(key)
            if metric_data:
                metric = json.loads(metric_data)
                if metric["timestamp"] >= cutoff_time:
                    values.append(metric["value"])
        
        if not values:
            return {"count": 0, "avg": 0, "min": 0, "max": 0}
        
        return {
            "count": len(values),
            "avg": sum(values) / len(values),
            "min": min(values),
            "max": max(values),
            "latest": values[-1] if values else 0
        }

class AlertManager:
    """Manage system alerts and notifications"""
    
    def __init__(self, redis_client: redis.Redis):
        self.redis_client = redis_client
        self.alert_rules = {}
        self.active_alerts = {}
    
    async def add_alert_rule(self, name: str, condition: Callable, level: AlertLevel):
        """Add an alert rule"""
        self.alert_rules[name] = {
            "condition": condition,
            "level": level,
            "created_at": datetime.utcnow()
        }
    
    async def check_alerts(self, metrics: Dict):
        """Check metrics against alert rules"""
        for rule_name, rule in self.alert_rules.items():
            try:
                if rule["condition"](metrics):
                    await self._trigger_alert(rule_name, rule, metrics)
                else:
                    await self._resolve_alert(rule_name)
            except Exception as e:
                logger.error(f"Error checking alert rule {rule_name}: {e}")
    
    async def _trigger_alert(self, rule_name: str, rule: Dict, metrics: Dict):
        """Trigger an alert"""
        if rule_name in self.active_alerts:
            return  # Alert already active
        
        alert = Alert(
            id=f"{rule_name}_{int(time.time())}",
            level=rule["level"],
            title=f"Alert: {rule_name}",
            message=f"Alert condition met for {rule_name}",
            service="system",
            timestamp=datetime.utcnow(),
            metadata={"metrics": metrics}
        )
        
        self.active_alerts[rule_name] = alert
        
        # Store alert in Redis
        await self.redis_client.setex(
            f"alert:{alert.id}",
            86400,  # 24h TTL
            json.dumps(alert.__dict__, default=str)
        )
        
        logger.warning(f"Alert triggered: {alert.title}")
    
    async def _resolve_alert(self, rule_name: str):
        """Resolve an alert"""
        if rule_name in self.active_alerts:
            alert = self.active_alerts[rule_name]
            alert.resolved = True
            
            # Update in Redis
            await self.redis_client.setex(
                f"alert:{alert.id}",
                86400,
                json.dumps(alert.__dict__, default=str)
            )
            
            del self.active_alerts[rule_name]
            logger.info(f"Alert resolved: {alert.title}")
    
    async def get_active_alerts(self) -> List[Alert]:
        """Get all active alerts"""
        return list(self.active_alerts.values())

class HealthChecker:
    """Enhanced health checking for services"""
    
    def __init__(self, redis_client: redis.Redis):
        self.redis_client = redis_client
        self.health_checks = {}
    
    async def register_health_check(self, service_name: str, check_func: Callable):
        """Register a health check function"""
        self.health_checks[service_name] = check_func
    
    async def run_health_checks(self) -> Dict:
        """Run all registered health checks"""
        results = {}
        
        for service_name, check_func in self.health_checks.items():
            try:
                start_time = time.time()
                result = await check_func()
                response_time = time.time() - start_time
                
                results[service_name] = {
                    "healthy": result.get("healthy", False),
                    "response_time": response_time,
                    "details": result,
                    "last_check": datetime.utcnow().isoformat()
                }
                
            except Exception as e:
                results[service_name] = {
                    "healthy": False,
                    "response_time": 0,
                    "error": str(e),
                    "last_check": datetime.utcnow().isoformat()
                }
        
        return results

class DistributedTracer:
    """Simple distributed tracing"""
    
    def __init__(self, redis_client: redis.Redis):
        self.redis_client = redis_client
    
    async def start_trace(self, trace_id: str, service: str, operation: str):
        """Start a new trace"""
        trace = {
            "trace_id": trace_id,
            "service": service,
            "operation": operation,
            "start_time": time.time(),
            "spans": []
        }
        
        await self.redis_client.setex(
            f"trace:{trace_id}",
            3600,  # 1 hour TTL
            json.dumps(trace)
        )
    
    async def add_span(self, trace_id: str, span_name: str, duration: float, metadata: Dict = None):
        """Add a span to a trace"""
        span = {
            "name": span_name,
            "duration": duration,
            "metadata": metadata or {},
            "timestamp": time.time()
        }
        
        trace_data = await self.redis_client.get(f"trace:{trace_id}")
        if trace_data:
            trace = json.loads(trace_data)
            trace["spans"].append(span)
            
            await self.redis_client.setex(
                f"trace:{trace_id}",
                3600,
                json.dumps(trace)
            )
    
    async def get_trace(self, trace_id: str) -> Optional[Dict]:
        """Get a trace by ID"""
        trace_data = await self.redis_client.get(f"trace:{trace_id}")
        if trace_data:
            return json.loads(trace_data)
        return None

class SystemMonitor:
    """Main system monitoring orchestrator"""
    
    def __init__(self, redis_client: redis.Redis):
        self.redis_client = redis_client
        self.metrics_collector = MetricsCollector(redis_client)
        self.alert_manager = AlertManager(redis_client)
        self.health_checker = HealthChecker(redis_client)
        self.tracer = DistributedTracer(redis_client)
        
        # Initialize default alert rules
        self._setup_default_alerts()
    
    def _setup_default_alerts(self):
        """Setup default alert rules"""
        # High CPU usage
        async def high_cpu_alert(metrics):
            return metrics.get("cpu_percent", 0) > 80
        
        # High memory usage
        async def high_memory_alert(metrics):
            return metrics.get("memory_percent", 0) > 90
        
        # Service down
        async def service_down_alert(metrics):
            return not metrics.get("healthy", True)
        
        # Add alert rules
        asyncio.create_task(self.alert_manager.add_alert_rule(
            "high_cpu", high_cpu_alert, AlertLevel.WARNING
        ))
        asyncio.create_task(self.alert_manager.add_alert_rule(
            "high_memory", high_memory_alert, AlertLevel.WARNING
        ))
        asyncio.create_task(self.alert_manager.add_alert_rule(
            "service_down", service_down_alert, AlertLevel.CRITICAL
        ))
    
    async def collect_system_metrics(self):
        """Collect system-wide metrics"""
        import psutil
        
        metrics = {
            "cpu_percent": psutil.cpu_percent(),
            "memory_percent": psutil.virtual_memory().percent,
            "disk_percent": psutil.disk_usage('/').percent,
            "timestamp": time.time()
        }
        
        # Record metrics
        for name, value in metrics.items():
            await self.metrics_collector.record_metric(name, value)
        
        # Check alerts
        await self.alert_manager.check_alerts(metrics)
        
        return metrics
    
    async def get_system_status(self) -> Dict:
        """Get comprehensive system status"""
        return {
            "metrics": await self.metrics_collector.get_metric_stats("cpu_percent"),
            "alerts": [alert.__dict__ for alert in await self.alert_manager.get_active_alerts()],
            "health": await self.health_checker.run_health_checks(),
            "timestamp": datetime.utcnow().isoformat()
        }
    
    async def start_monitoring(self, interval_seconds: int = 30):
        """Start continuous monitoring"""
        while True:
            try:
                await self.collect_system_metrics()
                await asyncio.sleep(interval_seconds)
            except Exception as e:
                logger.error(f"Monitoring error: {e}")
                await asyncio.sleep(5)

# Monitoring decorators
def trace_operation(operation_name: str):
    """Decorator to trace function execution"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            trace_id = f"{func.__name__}_{int(time.time())}"
            start_time = time.time()
            
            # Start trace
            # await tracer.start_trace(trace_id, "service", operation_name)
            
            try:
                result = await func(*args, **kwargs)
                duration = time.time() - start_time
                
                # Add span
                # await tracer.add_span(trace_id, operation_name, duration)
                
                return result
            except Exception as e:
                duration = time.time() - start_time
                
                # Add error span
                # await tracer.add_span(trace_id, f"{operation_name}_error", duration, {"error": str(e)})
                
                raise e
        
        return wrapper
    return decorator

def monitor_health(service_name: str):
    """Decorator to monitor service health"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            start_time = time.time()
            
            try:
                result = await func(*args, **kwargs)
                duration = time.time() - start_time
                
                # Record health metric
                # await metrics_collector.record_metric(f"{service_name}_response_time", duration)
                
                return result
            except Exception as e:
                duration = time.time() - start_time
                
                # Record error metric
                # await metrics_collector.record_metric(f"{service_name}_error", 1)
                
                raise e
        
        return wrapper
    return decorator 