"""
Comprehensive System Monitoring for Live Trading

This module provides detailed logging and monitoring for live market hours:
- Real-time performance metrics
- Trade execution tracking
- System health monitoring
- Error detection and alerting
- Market data quality monitoring
"""

import logging
import time
import threading
import psutil
import json
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime
from collections import defaultdict, deque
from enum import Enum
import asyncio

logger = logging.getLogger(__name__)

class SystemStatus(Enum):
    HEALTHY = "healthy"
    WARNING = "warning"
    CRITICAL = "critical"
    DOWN = "down"

@dataclass
class PerformanceMetrics:
    """Real-time performance metrics"""
    timestamp: float
    cpu_percent: float
    memory_percent: float
    memory_used_mb: float
    disk_usage_percent: float
    network_bytes_sent: int
    network_bytes_recv: int
    active_threads: int
    orders_per_minute: int
    market_data_ticks_per_minute: int
    api_response_time_ms: float
    database_response_time_ms: float
    errors_per_minute: int

@dataclass
class TradingMetrics:
    """Trading-specific metrics"""
    timestamp: float
    total_orders_sent: int
    orders_filled: int
    orders_rejected: int
    orders_pending: int
    total_volume_traded: float
    pnl_realized: float
    pnl_unrealized: float
    active_strategies: int
    active_users: int
    symbols_monitored: int
    last_order_time: Optional[float]
    broker_connection_status: str
    market_data_lag_ms: float

@dataclass
class MarketDataMetrics:
    """Market data quality metrics"""
    timestamp: float
    total_symbols: int
    active_symbols: int
    ticks_received_per_minute: int
    data_lag_avg_ms: float
    data_lag_max_ms: float
    missing_data_count: int
    invalid_data_count: int
    connection_status: str
    last_tick_time: Optional[float]

class SystemMonitor:
    """Comprehensive system monitoring for live trading"""
    
    def __init__(self):
        self._lock = threading.RLock()
        self._running = False
        self._monitor_thread = None
        
        # Metrics storage (rolling windows)
        self.performance_history = deque(maxlen=1000)  # ~16 minutes at 1-second intervals
        self.trading_history = deque(maxlen=500)       # ~8 minutes at 1-second intervals
        self.market_data_history = deque(maxlen=500)   # ~8 minutes at 1-second intervals
        
        # Real-time counters
        self.counters = {
            'orders_sent': 0,
            'orders_filled': 0,
            'orders_rejected': 0,
            'api_calls': 0,
            'errors': 0,
            'market_ticks': 0,
            'database_queries': 0
        }
        
        # Performance tracking
        self.response_times = {
            'api_calls': deque(maxlen=100),
            'database_queries': deque(maxlen=100),
            'order_executions': deque(maxlen=100)
        }
        
        # System status
        self.current_status = SystemStatus.HEALTHY
        self.status_reasons = []
        
        # Alert thresholds
        self.thresholds = {
            'cpu_warning': 70.0,
            'cpu_critical': 85.0,
            'memory_warning': 80.0,
            'memory_critical': 90.0,
            'disk_warning': 85.0,
            'disk_critical': 95.0,
            'api_response_warning': 1000.0,  # ms
            'api_response_critical': 5000.0,  # ms
            'market_data_lag_warning': 2000.0,  # ms
            'market_data_lag_critical': 10000.0,  # ms
            'errors_per_minute_warning': 10,
            'errors_per_minute_critical': 50
        }
        
        logger.info("🔍 System Monitor initialized for live trading")
    
    def start_monitoring(self):
        """Start system monitoring"""
        with self._lock:
            if self._running:
                logger.warning("System monitor already running")
                return
            
            self._running = True
            self._monitor_thread = threading.Thread(target=self._monitoring_loop, daemon=True)
            self._monitor_thread.start()
            
            logger.info("🚀 System monitoring started for LIVE MARKET HOURS")
    
    def stop_monitoring(self):
        """Stop system monitoring"""
        with self._lock:
            self._running = False
            if self._monitor_thread:
                self._monitor_thread.join(timeout=5)
            
            logger.info("🛑 System monitoring stopped")
    
    def _monitoring_loop(self):
        """Main monitoring loop"""
        logger.info("📊 Starting real-time monitoring loop")
        
        while self._running:
            try:
                # Collect all metrics
                perf_metrics = self._collect_performance_metrics()
                trading_metrics = self._collect_trading_metrics()
                market_metrics = self._collect_market_data_metrics()
                
                # Store metrics
                with self._lock:
                    self.performance_history.append(perf_metrics)
                    self.trading_history.append(trading_metrics)
                    self.market_data_history.append(market_metrics)
                
                # Analyze system health
                self._analyze_system_health(perf_metrics, trading_metrics, market_metrics)
                
                # Log detailed status every 30 seconds
                if int(time.time()) % 30 == 0:
                    self._log_detailed_status(perf_metrics, trading_metrics, market_metrics)
                
                time.sleep(1)
                
            except Exception as e:
                logger.error(f"❌ Error in monitoring loop: {e}")
                time.sleep(5)
    
    def _collect_performance_metrics(self) -> PerformanceMetrics:
        """Collect system performance metrics"""
        try:
            # CPU and Memory
            cpu_percent = psutil.cpu_percent(interval=0.1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            network = psutil.net_io_counters()
            
            # Threading
            active_threads = threading.active_count()
            
            # Calculate rates
            current_time = time.time()
            orders_per_minute, ticks_per_minute, errors_per_minute = self._calculate_rates(current_time)
            
            # Response times
            api_response_time = self._get_avg_response_time('api_calls')
            db_response_time = self._get_avg_response_time('database_queries')
            
            return PerformanceMetrics(
                timestamp=current_time,
                cpu_percent=cpu_percent,
                memory_percent=memory.percent,
                memory_used_mb=memory.used / (1024 * 1024),
                disk_usage_percent=disk.percent,
                network_bytes_sent=network.bytes_sent,
                network_bytes_recv=network.bytes_recv,
                active_threads=active_threads,
                orders_per_minute=orders_per_minute,
                market_data_ticks_per_minute=ticks_per_minute,
                api_response_time_ms=api_response_time,
                database_response_time_ms=db_response_time,
                errors_per_minute=errors_per_minute
            )
            
        except Exception as e:
            logger.error(f"❌ Error collecting performance metrics: {e}")
            return PerformanceMetrics(
                timestamp=time.time(),
                cpu_percent=0, memory_percent=0, memory_used_mb=0,
                disk_usage_percent=0, network_bytes_sent=0, network_bytes_recv=0,
                active_threads=0, orders_per_minute=0, market_data_ticks_per_minute=0,
                api_response_time_ms=0, database_response_time_ms=0, errors_per_minute=0
            )
    
    def _collect_trading_metrics(self) -> TradingMetrics:
        """Collect trading-specific metrics"""
        try:
            current_time = time.time()
            
            # Get trading stats from various components
            # These would be collected from the actual trading engine
            return TradingMetrics(
                timestamp=current_time,
                total_orders_sent=self.counters['orders_sent'],
                orders_filled=self.counters['orders_filled'],
                orders_rejected=self.counters['orders_rejected'],
                orders_pending=max(0, self.counters['orders_sent'] - self.counters['orders_filled'] - self.counters['orders_rejected']),
                total_volume_traded=0.0,  # Would be calculated from actual trades
                pnl_realized=0.0,         # Would be calculated from filled orders
                pnl_unrealized=0.0,       # Would be calculated from open positions
                active_strategies=0,      # Would be counted from strategy manager
                active_users=0,           # Would be counted from user sessions
                symbols_monitored=0,      # Would be counted from market data
                last_order_time=None,     # Would be tracked from last order
                broker_connection_status="unknown",  # Would be from broker manager
                market_data_lag_ms=0.0    # Would be calculated from market data timestamps
            )
            
        except Exception as e:
            logger.error(f"❌ Error collecting trading metrics: {e}")
            return TradingMetrics(
                timestamp=time.time(),
                total_orders_sent=0, orders_filled=0, orders_rejected=0, orders_pending=0,
                total_volume_traded=0.0, pnl_realized=0.0, pnl_unrealized=0.0,
                active_strategies=0, active_users=0, symbols_monitored=0,
                last_order_time=None, broker_connection_status="error", market_data_lag_ms=999999.0
            )
    
    def _collect_market_data_metrics(self) -> MarketDataMetrics:
        """Collect market data quality metrics"""
        try:
            current_time = time.time()
            
            return MarketDataMetrics(
                timestamp=current_time,
                total_symbols=0,          # Would be counted from market data manager
                active_symbols=0,         # Symbols with recent ticks
                ticks_received_per_minute=self.counters['market_ticks'],
                data_lag_avg_ms=0.0,      # Average lag of market data
                data_lag_max_ms=0.0,      # Maximum lag observed
                missing_data_count=0,     # Count of missing/stale data
                invalid_data_count=0,     # Count of invalid ticks
                connection_status="unknown",  # Market data connection status
                last_tick_time=None       # Last market tick received
            )
            
        except Exception as e:
            logger.error(f"❌ Error collecting market data metrics: {e}")
            return MarketDataMetrics(
                timestamp=time.time(),
                total_symbols=0, active_symbols=0, ticks_received_per_minute=0,
                data_lag_avg_ms=999999.0, data_lag_max_ms=999999.0,
                missing_data_count=999, invalid_data_count=999,
                connection_status="error", last_tick_time=None
            )
    
    def _calculate_rates(self, current_time: float) -> tuple:
        """Calculate per-minute rates"""
        # This would calculate actual rates based on timestamps
        # For now, return current counter values
        return (
            self.counters.get('orders_sent', 0),
            self.counters.get('market_ticks', 0), 
            self.counters.get('errors', 0)
        )
    
    def _get_avg_response_time(self, metric_type: str) -> float:
        """Get average response time for metric type"""
        response_times = self.response_times.get(metric_type, [])
        if not response_times:
            return 0.0
        return sum(response_times) / len(response_times)
    
    def _analyze_system_health(self, perf: PerformanceMetrics, 
                             trading: TradingMetrics, market: MarketDataMetrics):
        """Analyze system health and set status"""
        issues = []
        warnings = []
        
        # CPU Analysis
        if perf.cpu_percent > self.thresholds['cpu_critical']:
            issues.append(f"CPU usage critical: {perf.cpu_percent:.1f}%")
        elif perf.cpu_percent > self.thresholds['cpu_warning']:
            warnings.append(f"CPU usage high: {perf.cpu_percent:.1f}%")
        
        # Memory Analysis
        if perf.memory_percent > self.thresholds['memory_critical']:
            issues.append(f"Memory usage critical: {perf.memory_percent:.1f}%")
        elif perf.memory_percent > self.thresholds['memory_warning']:
            warnings.append(f"Memory usage high: {perf.memory_percent:.1f}%")
        
        # API Response Time Analysis
        if perf.api_response_time_ms > self.thresholds['api_response_critical']:
            issues.append(f"API response time critical: {perf.api_response_time_ms:.1f}ms")
        elif perf.api_response_time_ms > self.thresholds['api_response_warning']:
            warnings.append(f"API response time high: {perf.api_response_time_ms:.1f}ms")
        
        # Trading Analysis
        if trading.broker_connection_status == "disconnected":
            issues.append("Broker connection lost")
        
        # Market Data Analysis
        if market.connection_status == "disconnected":
            issues.append("Market data connection lost")
        
        if market.data_lag_avg_ms > self.thresholds['market_data_lag_critical']:
            issues.append(f"Market data lag critical: {market.data_lag_avg_ms:.1f}ms")
        elif market.data_lag_avg_ms > self.thresholds['market_data_lag_warning']:
            warnings.append(f"Market data lag high: {market.data_lag_avg_ms:.1f}ms")
        
        # Set overall status
        with self._lock:
            if issues:
                self.current_status = SystemStatus.CRITICAL
                self.status_reasons = issues
            elif warnings:
                self.current_status = SystemStatus.WARNING
                self.status_reasons = warnings
            else:
                self.current_status = SystemStatus.HEALTHY
                self.status_reasons = []
    
    def _log_detailed_status(self, perf: PerformanceMetrics, 
                           trading: TradingMetrics, market: MarketDataMetrics):
        """Log detailed system status"""
        status_emoji = {
            SystemStatus.HEALTHY: "✅",
            SystemStatus.WARNING: "⚠️",
            SystemStatus.CRITICAL: "🚨",
            SystemStatus.DOWN: "💀"
        }
        
        logger.info("=" * 80)
        logger.info(f"{status_emoji[self.current_status]} LIVE TRADING SYSTEM STATUS - {datetime.now().strftime('%H:%M:%S')}")
        logger.info("=" * 80)
        
        # System Performance
        logger.info(f"🖥️  SYSTEM PERFORMANCE:")
        logger.info(f"   CPU: {perf.cpu_percent:.1f}% | Memory: {perf.memory_percent:.1f}% ({perf.memory_used_mb:.0f}MB)")
        logger.info(f"   Disk: {perf.disk_usage_percent:.1f}% | Threads: {perf.active_threads}")
        logger.info(f"   API Response: {perf.api_response_time_ms:.1f}ms | DB Response: {perf.database_response_time_ms:.1f}ms")
        
        # Trading Status
        logger.info(f"💰 TRADING STATUS:")
        logger.info(f"   Orders: {trading.total_orders_sent} sent | {trading.orders_filled} filled | {trading.orders_rejected} rejected")
        logger.info(f"   Pending: {trading.orders_pending} | Rate: {perf.orders_per_minute}/min")
        logger.info(f"   Broker: {trading.broker_connection_status} | Users: {trading.active_users} | Strategies: {trading.active_strategies}")
        
        # Market Data Status
        logger.info(f"📊 MARKET DATA:")
        logger.info(f"   Connection: {market.connection_status} | Symbols: {market.active_symbols}/{market.total_symbols}")
        logger.info(f"   Ticks: {market.ticks_received_per_minute}/min | Lag: {market.data_lag_avg_ms:.1f}ms avg")
        logger.info(f"   Missing: {market.missing_data_count} | Invalid: {market.invalid_data_count}")
        
        # Errors and Warnings
        if self.status_reasons:
            logger.info(f"⚠️  ISSUES:")
            for reason in self.status_reasons:
                logger.info(f"   • {reason}")
        
        logger.info("=" * 80)
    
    # Counter increment methods for other components to use
    def increment_counter(self, counter_name: str, amount: int = 1):
        """Increment a counter (thread-safe)"""
        with self._lock:
            self.counters[counter_name] = self.counters.get(counter_name, 0) + amount
    
    def record_response_time(self, metric_type: str, response_time_ms: float):
        """Record response time for analysis"""
        with self._lock:
            if metric_type in self.response_times:
                self.response_times[metric_type].append(response_time_ms)
    
    def get_current_status(self) -> Dict[str, Any]:
        """Get current system status"""
        with self._lock:
            latest_perf = self.performance_history[-1] if self.performance_history else None
            latest_trading = self.trading_history[-1] if self.trading_history else None
            latest_market = self.market_data_history[-1] if self.market_data_history else None
            
            return {
                'status': self.current_status.value,
                'status_reasons': self.status_reasons,
                'timestamp': time.time(),
                'performance': latest_perf.__dict__ if latest_perf else None,
                'trading': latest_trading.__dict__ if latest_trading else None,
                'market_data': latest_market.__dict__ if latest_market else None,
                'counters': dict(self.counters),
                'uptime_seconds': time.time() - (self.performance_history[0].timestamp if self.performance_history else time.time())
            }
    
    def get_metrics_summary(self, minutes: int = 10) -> Dict[str, Any]:
        """Get metrics summary for last N minutes"""
        with self._lock:
            cutoff_time = time.time() - (minutes * 60)
            
            # Filter recent metrics
            recent_perf = [m for m in self.performance_history if m.timestamp >= cutoff_time]
            recent_trading = [m for m in self.trading_history if m.timestamp >= cutoff_time]
            recent_market = [m for m in self.market_data_history if m.timestamp >= cutoff_time]
            
            return {
                'time_window_minutes': minutes,
                'data_points': len(recent_perf),
                'performance_summary': self._summarize_performance_metrics(recent_perf),
                'trading_summary': self._summarize_trading_metrics(recent_trading),
                'market_data_summary': self._summarize_market_metrics(recent_market)
            }
    
    def _summarize_performance_metrics(self, metrics: List[PerformanceMetrics]) -> Dict[str, Any]:
        """Summarize performance metrics"""
        if not metrics:
            return {}
        
        cpu_values = [m.cpu_percent for m in metrics]
        memory_values = [m.memory_percent for m in metrics]
        api_times = [m.api_response_time_ms for m in metrics]
        
        return {
            'cpu_avg': sum(cpu_values) / len(cpu_values),
            'cpu_max': max(cpu_values),
            'memory_avg': sum(memory_values) / len(memory_values),
            'memory_max': max(memory_values),
            'api_response_avg': sum(api_times) / len(api_times),
            'api_response_max': max(api_times),
            'total_errors': sum(m.errors_per_minute for m in metrics)
        }
    
    def _summarize_trading_metrics(self, metrics: List[TradingMetrics]) -> Dict[str, Any]:
        """Summarize trading metrics"""
        if not metrics:
            return {}
        
        latest = metrics[-1]
        first = metrics[0]
        
        return {
            'orders_sent_delta': latest.total_orders_sent - first.total_orders_sent,
            'orders_filled_delta': latest.orders_filled - first.orders_filled,
            'orders_rejected_delta': latest.orders_rejected - first.orders_rejected,
            'current_pending': latest.orders_pending,
            'fill_rate_percent': (latest.orders_filled / max(1, latest.total_orders_sent)) * 100
        }
    
    def _summarize_market_metrics(self, metrics: List[MarketDataMetrics]) -> Dict[str, Any]:
        """Summarize market data metrics"""
        if not metrics:
            return {}
        
        lag_values = [m.data_lag_avg_ms for m in metrics]
        tick_rates = [m.ticks_received_per_minute for m in metrics]
        
        return {
            'avg_data_lag_ms': sum(lag_values) / len(lag_values),
            'max_data_lag_ms': max(lag_values),
            'avg_tick_rate': sum(tick_rates) / len(tick_rates),
            'total_missing_data': sum(m.missing_data_count for m in metrics),
            'total_invalid_data': sum(m.invalid_data_count for m in metrics)
        }

# Global system monitor instance
_global_monitor: Optional[SystemMonitor] = None
_monitor_lock = threading.Lock()

def get_system_monitor() -> SystemMonitor:
    """Get global system monitor instance"""
    global _global_monitor
    
    with _monitor_lock:
        if _global_monitor is None:
            _global_monitor = SystemMonitor()
    
    return _global_monitor

def start_live_monitoring():
    """Start live monitoring for market hours"""
    monitor = get_system_monitor()
    monitor.start_monitoring()
    logger.info("🚀 LIVE MARKET MONITORING STARTED")

def stop_live_monitoring():
    """Stop live monitoring"""
    monitor = get_system_monitor()
    monitor.stop_monitoring()
    logger.info("🛑 LIVE MARKET MONITORING STOPPED") 