import asyncio
import time
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, asdict
from collections import deque
import psutil
import json

logger = logging.getLogger(__name__)

@dataclass
class PerformanceMetrics:
    """Performance metrics snapshot"""
    timestamp: datetime
    db_sync_time: float
    db_sync_count: int
    redis_ops: int
    memory_usage_mb: float
    cpu_usage_percent: float
    active_connections: int
    queue_size: int
    throughput_ops_per_sec: float

class PerformanceMonitor:
    """Real-time performance monitoring for the trading engine"""
    
    def __init__(self, history_size: int = 1000):
        self.history_size = history_size
        self.metrics_history: deque = deque(maxlen=history_size)
        self.start_time = datetime.now()
        self.last_snapshot_time = time.time()
        
        # Performance counters
        self.counters = {
            'total_db_syncs': 0,
            'total_redis_ops': 0,
            'total_errors': 0,
            'total_orders_processed': 0
        }
        
        # Thresholds for alerts
        self.thresholds = {
            'max_sync_time': 2.0,  # seconds
            'max_memory_mb': 1000,  # MB
            'max_cpu_percent': 80,  # %
            'max_queue_size': 1000
        }
        
        self.alerts: List[Dict[str, Any]] = []
        
    def record_db_sync(self, sync_time: float, orders_synced: int):
        """Record a database sync operation"""
        self.counters['total_db_syncs'] += 1
        self.counters['total_orders_processed'] += orders_synced
        
        # Check for performance alerts
        if sync_time > self.thresholds['max_sync_time']:
            self._add_alert('slow_db_sync', f"DB sync took {sync_time:.2f}s (threshold: {self.thresholds['max_sync_time']}s)")
    
    def record_redis_operation(self, op_count: int = 1):
        """Record Redis operations"""
        self.counters['total_redis_ops'] += op_count
    
    def record_error(self, error_type: str, details: str):
        """Record an error occurrence"""
        self.counters['total_errors'] += 1
        self._add_alert('error', f"{error_type}: {details}")
    
    def _add_alert(self, alert_type: str, message: str):
        """Add a performance alert"""
        alert = {
            'timestamp': datetime.now(),
            'type': alert_type,
            'message': message
        }
        self.alerts.append(alert)
        
        # Keep only last 100 alerts
        if len(self.alerts) > 100:
            self.alerts = self.alerts[-100:]
        
        logger.warning(f"🚨 Performance Alert [{alert_type}]: {message}")
    
    def take_snapshot(self, additional_metrics: Dict[str, Any] = None) -> PerformanceMetrics:
        """Take a performance snapshot"""
        current_time = time.time()
        
        # System metrics
        memory_mb = psutil.virtual_memory().used / 1024 / 1024
        cpu_percent = psutil.cpu_percent()
        
        # Calculate throughput
        time_diff = current_time - self.last_snapshot_time
        if time_diff > 0:
            throughput = self.counters['total_orders_processed'] / time_diff
        else:
            throughput = 0
        
        # Create metrics snapshot
        metrics = PerformanceMetrics(
            timestamp=datetime.now(),
            db_sync_time=additional_metrics.get('last_sync_time', 0) if additional_metrics else 0,
            db_sync_count=self.counters['total_db_syncs'],
            redis_ops=self.counters['total_redis_ops'],
            memory_usage_mb=memory_mb,
            cpu_usage_percent=cpu_percent,
            active_connections=additional_metrics.get('active_connections', 0) if additional_metrics else 0,
            queue_size=additional_metrics.get('queue_size', 0) if additional_metrics else 0,
            throughput_ops_per_sec=throughput
        )
        
        # Add to history
        self.metrics_history.append(metrics)
        
        # Check thresholds
        self._check_thresholds(metrics)
        
        self.last_snapshot_time = current_time
        return metrics
    
    def _check_thresholds(self, metrics: PerformanceMetrics):
        """Check if any performance thresholds are exceeded"""
        if metrics.memory_usage_mb > self.thresholds['max_memory_mb']:
            self._add_alert('high_memory', f"Memory usage: {metrics.memory_usage_mb:.1f}MB")
        
        if metrics.cpu_usage_percent > self.thresholds['max_cpu_percent']:
            self._add_alert('high_cpu', f"CPU usage: {metrics.cpu_usage_percent:.1f}%")
        
        if metrics.queue_size > self.thresholds['max_queue_size']:
            self._add_alert('large_queue', f"Queue size: {metrics.queue_size}")
    
    def get_performance_summary(self, minutes: int = 5) -> Dict[str, Any]:
        """Get performance summary for the last N minutes"""
        cutoff_time = datetime.now() - timedelta(minutes=minutes)
        recent_metrics = [m for m in self.metrics_history if m.timestamp >= cutoff_time]
        
        if not recent_metrics:
            return {"message": "No recent metrics available"}
        
        # Calculate averages
        avg_sync_time = sum(m.db_sync_time for m in recent_metrics) / len(recent_metrics)
        avg_memory = sum(m.memory_usage_mb for m in recent_metrics) / len(recent_metrics)
        avg_cpu = sum(m.cpu_usage_percent for m in recent_metrics) / len(recent_metrics)
        avg_throughput = sum(m.throughput_ops_per_sec for m in recent_metrics) / len(recent_metrics)
        
        # Find peaks
        peak_memory = max(m.memory_usage_mb for m in recent_metrics)
        peak_cpu = max(m.cpu_usage_percent for m in recent_metrics)
        max_sync_time = max(m.db_sync_time for m in recent_metrics)
        
        uptime = datetime.now() - self.start_time
        
        return {
            'period_minutes': minutes,
            'uptime': str(uptime),
            'total_metrics_collected': len(self.metrics_history),
            'averages': {
                'sync_time_ms': avg_sync_time * 1000,
                'memory_mb': avg_memory,
                'cpu_percent': avg_cpu,
                'throughput_ops_per_sec': avg_throughput
            },
            'peaks': {
                'max_sync_time_ms': max_sync_time * 1000,
                'peak_memory_mb': peak_memory,
                'peak_cpu_percent': peak_cpu
            },
            'totals': dict(self.counters),
            'recent_alerts': self.alerts[-10:] if self.alerts else [],
            'performance_score': self._calculate_performance_score(recent_metrics)
        }
    
    def _calculate_performance_score(self, metrics: List[PerformanceMetrics]) -> Dict[str, Any]:
        """Calculate an overall performance score (0-100)"""
        if not metrics:
            return {'score': 0, 'rating': 'No Data'}
        
        score = 100
        
        # Deduct points for slow syncs
        avg_sync_time = sum(m.db_sync_time for m in metrics) / len(metrics)
        if avg_sync_time > 0.5:
            score -= min(30, (avg_sync_time - 0.5) * 60)
        
        # Deduct points for high memory usage
        avg_memory = sum(m.memory_usage_mb for m in metrics) / len(metrics)
        if avg_memory > 500:
            score -= min(20, (avg_memory - 500) / 25)
        
        # Deduct points for high CPU usage
        avg_cpu = sum(m.cpu_usage_percent for m in metrics) / len(metrics)
        if avg_cpu > 50:
            score -= min(20, (avg_cpu - 50) / 2.5)
        
        # Deduct points for errors
        error_rate = self.counters['total_errors'] / max(1, self.counters['total_db_syncs'])
        if error_rate > 0.01:  # 1% error rate
            score -= min(30, error_rate * 1000)
        
        score = max(0, score)
        
        if score >= 90:
            rating = 'Excellent'
        elif score >= 75:
            rating = 'Good'
        elif score >= 60:
            rating = 'Fair'
        elif score >= 40:
            rating = 'Poor'
        else:
            rating = 'Critical'
        
        return {
            'score': round(score, 1),
            'rating': rating,
            'details': {
                'avg_sync_time_ms': avg_sync_time * 1000,
                'avg_memory_mb': avg_memory,
                'avg_cpu_percent': avg_cpu,
                'error_rate_percent': error_rate * 100
            }
        }
    
    def export_metrics(self, format: str = 'json') -> str:
        """Export metrics history"""
        if format == 'json':
            data = [asdict(m) for m in self.metrics_history]
            # Convert datetime to string for JSON serialization
            for item in data:
                item['timestamp'] = item['timestamp'].isoformat()
            return json.dumps(data, indent=2)
        else:
            raise ValueError(f"Unsupported format: {format}")
    
    def get_optimization_recommendations(self) -> List[str]:
        """Get performance optimization recommendations"""
        recommendations = []
        
        if not self.metrics_history:
            return ["Insufficient data for recommendations"]
        
        recent_metrics = list(self.metrics_history)[-10:]  # Last 10 measurements
        
        avg_sync_time = sum(m.db_sync_time for m in recent_metrics) / len(recent_metrics)
        avg_memory = sum(m.memory_usage_mb for m in recent_metrics) / len(recent_metrics)
        avg_cpu = sum(m.cpu_usage_percent for m in recent_metrics) / len(recent_metrics)
        
        if avg_sync_time > 1.0:
            recommendations.append("🔧 Consider increasing batch size or using bulk operations for DB sync")
        
        if avg_memory > 800:
            recommendations.append("💾 High memory usage detected - consider implementing data compression")
        
        if avg_cpu > 70:
            recommendations.append("⚡ High CPU usage - consider optimizing Redis operations or adding connection pooling")
        
        error_rate = self.counters['total_errors'] / max(1, self.counters['total_db_syncs'])
        if error_rate > 0.05:  # 5% error rate
            recommendations.append("🚨 High error rate detected - review error logs and implement better error handling")
        
        if len(self.alerts) > 50:
            recommendations.append("📊 Many performance alerts - consider adjusting thresholds or optimizing bottlenecks")
        
        if not recommendations:
            recommendations.append("✅ System performance is optimal - no recommendations at this time")
        
        return recommendations

# Global performance monitor instance
_performance_monitor: Optional[PerformanceMonitor] = None

def get_performance_monitor() -> PerformanceMonitor:
    """Get the global performance monitor instance"""
    global _performance_monitor
    if _performance_monitor is None:
        _performance_monitor = PerformanceMonitor()
    return _performance_monitor

def record_db_sync_performance(sync_time: float, orders_synced: int):
    """Convenience function to record DB sync performance"""
    monitor = get_performance_monitor()
    monitor.record_db_sync(sync_time, orders_synced)

def record_redis_performance(op_count: int = 1):
    """Convenience function to record Redis performance"""
    monitor = get_performance_monitor()
    monitor.record_redis_operation(op_count)

def get_performance_dashboard() -> Dict[str, Any]:
    """Get a complete performance dashboard"""
    monitor = get_performance_monitor()
    
    return {
        'current_time': datetime.now().isoformat(),
        'summary_5min': monitor.get_performance_summary(5),
        'summary_15min': monitor.get_performance_summary(15),
        'summary_60min': monitor.get_performance_summary(60),
        'optimization_recommendations': monitor.get_optimization_recommendations(),
        'recent_alerts': monitor.alerts[-5:] if monitor.alerts else []
    } 