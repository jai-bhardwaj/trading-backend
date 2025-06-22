"""
Trading System Monitoring Dashboard
Comprehensive system health and performance monitoring
"""

import asyncio
import logging
import time
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)

class SystemHealth(Enum):
    """Overall system health status"""
    EXCELLENT = "EXCELLENT"
    GOOD = "GOOD"
    WARNING = "WARNING"
    CRITICAL = "CRITICAL"
    UNKNOWN = "UNKNOWN"

@dataclass
class HealthMetric:
    """Individual health metric"""
    name: str
    value: float
    unit: str
    status: SystemHealth
    threshold_warning: float
    threshold_critical: float
    timestamp: datetime

@dataclass
class SystemStatus:
    """Complete system status"""
    overall_health: SystemHealth
    timestamp: datetime
    uptime_seconds: float
    metrics: List[HealthMetric] = field(default_factory=list)
    alerts: List[str] = field(default_factory=list)
    components_status: Dict[str, SystemHealth] = field(default_factory=dict)

class TradingSystemMonitor:
    """Comprehensive trading system monitor"""
    
    def __init__(self):
        self.start_time = time.time()
        self.monitoring_active = False
        self.health_history: List[SystemStatus] = []
        self.max_history_size = 1000
        self.alert_thresholds = {
            'memory_usage_mb': {'warning': 500, 'critical': 1000},
            'cpu_usage_percent': {'warning': 80, 'critical': 95},
            'order_error_rate': {'warning': 5, 'critical': 15},  # percentage
            'response_time_ms': {'warning': 1000, 'critical': 5000},
            'active_connections': {'warning': 100, 'critical': 200}
        }
        
    def get_component_health(self, component_name: str) -> SystemHealth:
        """Get health status of a specific component"""
        try:
            if component_name == "authentication":
                return self._check_auth_health()
            elif component_name == "memory_manager":
                return self._check_memory_health()
            elif component_name == "order_system":
                return self._check_order_system_health()
            elif component_name == "broker_connection":
                return self._check_broker_health()
            elif component_name == "database":
                return self._check_database_health()
            else:
                return SystemHealth.UNKNOWN
        except Exception as e:
            logger.error(f"❌ Error checking {component_name} health: {e}")
            return SystemHealth.CRITICAL
    
    def _check_auth_health(self) -> SystemHealth:
        """Check authentication system health"""
        try:
            from .auth import get_auth_manager
            auth_manager = get_auth_manager()
            
            # Check if auth manager is responsive
            test_payload = {"user_id": "health_check", "role": "test"}
            token = auth_manager.create_access_token(test_payload)
            
            if token and len(token) > 50:
                return SystemHealth.GOOD
            else:
                return SystemHealth.WARNING
        except Exception:
            return SystemHealth.CRITICAL
    
    def _check_memory_health(self) -> SystemHealth:
        """Check memory management health"""
        try:
            from .memory_manager import get_smart_memory_manager
            memory_manager = get_smart_memory_manager()
            
            stats = memory_manager.get_memory_stats()
            memory_usage = stats.get('total_memory_usage_mb', 0)
            
            if memory_usage < 200:
                return SystemHealth.EXCELLENT
            elif memory_usage < 500:
                return SystemHealth.GOOD
            elif memory_usage < 1000:
                return SystemHealth.WARNING
            else:
                return SystemHealth.CRITICAL
        except Exception:
            return SystemHealth.WARNING
    
    def _check_order_system_health(self) -> SystemHealth:
        """Check order system health"""
        try:
            from .order_sync import get_thread_safe_order_manager
            order_manager = get_thread_safe_order_manager()
            
            stats = order_manager.get_statistics()
            
            # Check for race conditions or duplicate orders
            race_conditions = stats.get('race_conditions_prevented', 0)
            duplicates = stats.get('duplicate_orders_prevented', 0)
            
            if race_conditions > 10 or duplicates > 20:
                return SystemHealth.WARNING
            else:
                return SystemHealth.GOOD
        except Exception:
            return SystemHealth.WARNING
    
    def _check_broker_health(self) -> SystemHealth:
        """Check broker connection health"""
        try:
            from .production_safety import get_production_safety_validator
            safety_validator = get_production_safety_validator()
            
            # Simulate broker connectivity check
            if safety_validator.should_allow_trading(broker_connected=True):
                return SystemHealth.GOOD
            else:
                return SystemHealth.CRITICAL
        except Exception:
            return SystemHealth.WARNING
    
    def _check_database_health(self) -> SystemHealth:
        """Check database health"""
        try:
            # Simple database health check
            # In a real implementation, this would ping the database
            return SystemHealth.GOOD
        except Exception:
            return SystemHealth.WARNING
    
    def collect_system_metrics(self) -> List[HealthMetric]:
        """Collect current system metrics"""
        metrics = []
        current_time = datetime.now()
        
        try:
            # Resource metrics
            from .resource_manager import get_resource_manager
            resource_manager = get_resource_manager()
            resource_status = resource_manager.get_resource_status()
            
            # Memory metric
            memory_mb = resource_status.get('current_memory_mb', 0)
            memory_status = self._determine_metric_health(
                memory_mb, 
                self.alert_thresholds['memory_usage_mb']
            )
            metrics.append(HealthMetric(
                name="Memory Usage",
                value=memory_mb,
                unit="MB",
                status=memory_status,
                threshold_warning=self.alert_thresholds['memory_usage_mb']['warning'],
                threshold_critical=self.alert_thresholds['memory_usage_mb']['critical'],
                timestamp=current_time
            ))
            
            # CPU metric
            cpu_percent = resource_status.get('current_cpu_percent', 0)
            cpu_status = self._determine_metric_health(
                cpu_percent,
                self.alert_thresholds['cpu_usage_percent']
            )
            metrics.append(HealthMetric(
                name="CPU Usage",
                value=cpu_percent,
                unit="%",
                status=cpu_status,
                threshold_warning=self.alert_thresholds['cpu_usage_percent']['warning'],
                threshold_critical=self.alert_thresholds['cpu_usage_percent']['critical'],
                timestamp=current_time
            ))
            
        except Exception as e:
            logger.error(f"❌ Error collecting system metrics: {e}")
        
        try:
            # Order system metrics
            from .order_sync import get_thread_safe_order_manager
            order_manager = get_thread_safe_order_manager()
            order_stats = order_manager.get_statistics()
            
            active_orders = order_stats.get('active_orders', 0)
            metrics.append(HealthMetric(
                name="Active Orders",
                value=active_orders,
                unit="count",
                status=SystemHealth.GOOD if active_orders < 100 else SystemHealth.WARNING,
                threshold_warning=50,
                threshold_critical=100,
                timestamp=current_time
            ))
            
        except Exception as e:
            logger.debug(f"Order metrics not available: {e}")
        
        return metrics
    
    def _determine_metric_health(self, value: float, thresholds: Dict[str, float]) -> SystemHealth:
        """Determine health status based on metric value and thresholds"""
        if value >= thresholds['critical']:
            return SystemHealth.CRITICAL
        elif value >= thresholds['warning']:
            return SystemHealth.WARNING
        elif value <= thresholds['warning'] * 0.5:
            return SystemHealth.EXCELLENT
        else:
            return SystemHealth.GOOD
    
    def generate_system_status(self) -> SystemStatus:
        """Generate comprehensive system status"""
        current_time = datetime.now()
        uptime = time.time() - self.start_time
        
        # Collect metrics
        metrics = self.collect_system_metrics()
        
        # Check component health
        components = [
            "authentication",
            "memory_manager", 
            "order_system",
            "broker_connection",
            "database"
        ]
        
        components_status = {}
        for component in components:
            components_status[component] = self.get_component_health(component)
        
        # Determine overall health
        overall_health = self._determine_overall_health(metrics, components_status)
        
        # Generate alerts
        alerts = self._generate_alerts(metrics, components_status)
        
        status = SystemStatus(
            overall_health=overall_health,
            timestamp=current_time,
            uptime_seconds=uptime,
            metrics=metrics,
            alerts=alerts,
            components_status=components_status
        )
        
        # Add to history
        self.health_history.append(status)
        if len(self.health_history) > self.max_history_size:
            self.health_history = self.health_history[-self.max_history_size:]
        
        return status
    
    def _determine_overall_health(self, metrics: List[HealthMetric], 
                                components: Dict[str, SystemHealth]) -> SystemHealth:
        """Determine overall system health"""
        
        # Check for any critical issues
        critical_metrics = [m for m in metrics if m.status == SystemHealth.CRITICAL]
        critical_components = [h for h in components.values() if h == SystemHealth.CRITICAL]
        
        if critical_metrics or critical_components:
            return SystemHealth.CRITICAL
        
        # Check for warnings
        warning_metrics = [m for m in metrics if m.status == SystemHealth.WARNING]
        warning_components = [h for h in components.values() if h == SystemHealth.WARNING]
        
        if len(warning_metrics) > 2 or len(warning_components) > 1:
            return SystemHealth.WARNING
        elif warning_metrics or warning_components:
            return SystemHealth.GOOD
        
        # Check for excellent performance
        excellent_metrics = [m for m in metrics if m.status == SystemHealth.EXCELLENT]
        if len(excellent_metrics) >= len(metrics) * 0.8:  # 80% excellent
            return SystemHealth.EXCELLENT
        
        return SystemHealth.GOOD
    
    def _generate_alerts(self, metrics: List[HealthMetric], 
                        components: Dict[str, SystemHealth]) -> List[str]:
        """Generate system alerts"""
        alerts = []
        
        # Metric-based alerts
        for metric in metrics:
            if metric.status == SystemHealth.CRITICAL:
                alerts.append(f"🚨 CRITICAL: {metric.name} is {metric.value}{metric.unit} (threshold: {metric.threshold_critical}{metric.unit})")
            elif metric.status == SystemHealth.WARNING:
                alerts.append(f"⚠️ WARNING: {metric.name} is {metric.value}{metric.unit} (threshold: {metric.threshold_warning}{metric.unit})")
        
        # Component-based alerts
        for component, health in components.items():
            if health == SystemHealth.CRITICAL:
                alerts.append(f"🚨 CRITICAL: {component.replace('_', ' ').title()} system is down")
            elif health == SystemHealth.WARNING:
                alerts.append(f"⚠️ WARNING: {component.replace('_', ' ').title()} system has issues")
        
        return alerts
    
    def get_dashboard_data(self) -> Dict[str, Any]:
        """Get formatted dashboard data"""
        current_status = self.generate_system_status()
        
        # Get recent history for trends
        recent_history = self.health_history[-20:] if len(self.health_history) >= 20 else self.health_history
        
        return {
            'system_status': {
                'overall_health': current_status.overall_health.value,
                'uptime_hours': round(current_status.uptime_seconds / 3600, 2),
                'timestamp': current_status.timestamp.isoformat(),
                'total_alerts': len(current_status.alerts)
            },
            'components': {
                component: health.value 
                for component, health in current_status.components_status.items()
            },
            'metrics': [
                {
                    'name': metric.name,
                    'value': metric.value,
                    'unit': metric.unit,
                    'status': metric.status.value,
                    'threshold_warning': metric.threshold_warning,
                    'threshold_critical': metric.threshold_critical
                }
                for metric in current_status.metrics
            ],
            'alerts': current_status.alerts,
            'trends': {
                'health_history_count': len(self.health_history),
                'recent_health_scores': [
                    {
                        'timestamp': status.timestamp.isoformat(),
                        'health': status.overall_health.value,
                        'alert_count': len(status.alerts)
                    }
                    for status in recent_history
                ]
            },
            'statistics': {
                'monitoring_active': self.monitoring_active,
                'health_checks_performed': len(self.health_history),
                'system_start_time': datetime.fromtimestamp(self.start_time).isoformat()
            }
        }
    
    async def start_monitoring(self, interval_seconds: int = 60):
        """Start continuous monitoring"""
        if self.monitoring_active:
            return
        
        self.monitoring_active = True
        logger.info(f"📊 System monitoring started (interval: {interval_seconds}s)")
        
        asyncio.create_task(self._monitoring_loop(interval_seconds))
    
    def stop_monitoring(self):
        """Stop monitoring"""
        self.monitoring_active = False
        logger.info("📊 System monitoring stopped")
    
    async def _monitoring_loop(self, interval_seconds: int):
        """Main monitoring loop"""
        while self.monitoring_active:
            try:
                status = self.generate_system_status()
                
                # Log critical alerts
                if status.overall_health == SystemHealth.CRITICAL:
                    logger.critical(f"🚨 SYSTEM CRITICAL: {len(status.alerts)} critical issues")
                    for alert in status.alerts:
                        logger.critical(f"   {alert}")
                elif status.alerts:
                    logger.warning(f"⚠️ System alerts: {len(status.alerts)} issues")
                
                await asyncio.sleep(interval_seconds)
                
            except Exception as e:
                logger.error(f"❌ Monitoring loop error: {e}")
                await asyncio.sleep(interval_seconds)

# Global instance
_system_monitor = None

def get_system_monitor() -> TradingSystemMonitor:
    """Get global system monitor"""
    global _system_monitor
    if _system_monitor is None:
        _system_monitor = TradingSystemMonitor()
    return _system_monitor
