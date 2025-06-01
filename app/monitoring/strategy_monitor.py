"""
Strategy Monitor - Real-time monitoring of algorithmic trading strategies

This module provides comprehensive monitoring capabilities for trading strategies,
including health checks, performance tracking, risk monitoring, and alerting.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
from sqlalchemy.orm import Session
from sqlalchemy import and_, func

from app.database import DatabaseManager
from app.models.base import (
    Strategy as StrategyModel, Order, Trade, Position, Balance,
    OrderStatus, StrategyStatus
)
from app.strategies.base import BaseStrategy

logger = logging.getLogger(__name__)

class StrategyHealth(Enum):
    """Strategy health status"""
    HEALTHY = "HEALTHY"
    WARNING = "WARNING"
    CRITICAL = "CRITICAL"
    OFFLINE = "OFFLINE"

class MonitoringLevel(Enum):
    """Monitoring detail levels"""
    BASIC = "BASIC"
    DETAILED = "DETAILED"
    COMPREHENSIVE = "COMPREHENSIVE"

@dataclass
class MonitoringMetrics:
    """Comprehensive monitoring metrics for a strategy"""
    strategy_id: str
    strategy_name: str
    health_status: StrategyHealth
    last_update: datetime
    
    # Performance Metrics
    total_pnl: float = 0.0
    daily_pnl: float = 0.0
    win_rate: float = 0.0
    sharpe_ratio: float = 0.0
    max_drawdown: float = 0.0
    
    # Activity Metrics
    total_orders: int = 0
    successful_orders: int = 0
    failed_orders: int = 0
    active_positions: int = 0
    
    # Risk Metrics
    current_exposure: float = 0.0
    risk_utilization: float = 0.0
    largest_position: float = 0.0
    
    # System Metrics
    last_signal_time: Optional[datetime] = None
    last_order_time: Optional[datetime] = None
    execution_latency: float = 0.0
    error_count: int = 0
    
    # Alerts
    active_alerts: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            'strategy_id': self.strategy_id,
            'strategy_name': self.strategy_name,
            'health_status': self.health_status.value,
            'last_update': self.last_update.isoformat(),
            'performance': {
                'total_pnl': self.total_pnl,
                'daily_pnl': self.daily_pnl,
                'win_rate': self.win_rate,
                'sharpe_ratio': self.sharpe_ratio,
                'max_drawdown': self.max_drawdown
            },
            'activity': {
                'total_orders': self.total_orders,
                'successful_orders': self.successful_orders,
                'failed_orders': self.failed_orders,
                'active_positions': self.active_positions
            },
            'risk': {
                'current_exposure': self.current_exposure,
                'risk_utilization': self.risk_utilization,
                'largest_position': self.largest_position
            },
            'system': {
                'last_signal_time': self.last_signal_time.isoformat() if self.last_signal_time else None,
                'last_order_time': self.last_order_time.isoformat() if self.last_order_time else None,
                'execution_latency': self.execution_latency,
                'error_count': self.error_count
            },
            'active_alerts': self.active_alerts
        }

class StrategyMonitor:
    """
    Real-time strategy monitoring system
    
    Provides comprehensive monitoring of strategy performance, health,
    and risk metrics with configurable alerting.
    """
    
    def __init__(self, monitoring_level: MonitoringLevel = MonitoringLevel.DETAILED):
        self.monitoring_level = monitoring_level
        self.running = False
        self._strategy_metrics: Dict[str, MonitoringMetrics] = {}
        self._health_thresholds = self._get_health_thresholds()
        self._monitoring_interval = 30  # seconds
        
    def _get_health_thresholds(self) -> Dict[str, Dict[str, float]]:
        """Get health check thresholds"""
        return {
            'performance': {
                'max_daily_loss_pct': -0.05,  # -5%
                'max_drawdown_pct': -0.10,    # -10%
                'min_win_rate': 0.30          # 30%
            },
            'risk': {
                'max_exposure_pct': 0.80,     # 80%
                'max_position_pct': 0.20      # 20%
            },
            'system': {
                'max_error_count': 10,
                'max_latency_ms': 5000,       # 5 seconds
                'max_offline_minutes': 15
            }
        }
    
    async def start_monitoring(self):
        """Start the monitoring system"""
        self.running = True
        logger.info("🔍 Strategy Monitor started")
        
        # Start monitoring tasks
        await asyncio.gather(
            self._monitor_strategies(),
            self._health_checker(),
            self._performance_calculator(),
            self._risk_monitor()
        )
    
    async def stop_monitoring(self):
        """Stop the monitoring system"""
        self.running = False
        logger.info("🛑 Strategy Monitor stopped")
    
    async def _monitor_strategies(self):
        """Main monitoring loop"""
        while self.running:
            try:
                await self._update_all_metrics()
                await asyncio.sleep(self._monitoring_interval)
            except Exception as e:
                logger.error(f"Error in strategy monitoring: {e}")
                await asyncio.sleep(self._monitoring_interval)
    
    async def _update_all_metrics(self):
        """Update metrics for all active strategies"""
        db_manager = DatabaseManager()
        try:
            async with db_manager.get_session() as db:
                # Get all active strategies
                strategies = db.query(StrategyModel).filter(
                    StrategyModel.status.in_([StrategyStatus.ACTIVE, StrategyStatus.PAUSED])
                ).all()
                
                for strategy in strategies:
                    metrics = await self._calculate_strategy_metrics(db, strategy)
                    self._strategy_metrics[strategy.id] = metrics
                    
                    # Update health status
                    health_status = self._assess_strategy_health(metrics)
                    metrics.health_status = health_status
                    
                    logger.debug(f"Updated metrics for strategy {strategy.name}: {health_status.value}")
                    
        except Exception as e:
            logger.error(f"Error in strategy monitoring: {e}")
    
    async def _calculate_strategy_metrics(self, db: Session, strategy: StrategyModel) -> MonitoringMetrics:
        """Calculate comprehensive metrics for a strategy"""
        strategy_id = strategy.id
        
        # Initialize metrics
        metrics = MonitoringMetrics(
            strategy_id=strategy_id,
            strategy_name=strategy.name,
            health_status=StrategyHealth.HEALTHY,
            last_update=datetime.utcnow()
        )
        
        # Calculate performance metrics
        await self._calculate_performance_metrics(db, strategy, metrics)
        
        # Calculate activity metrics
        await self._calculate_activity_metrics(db, strategy, metrics)
        
        # Calculate risk metrics
        await self._calculate_risk_metrics(db, strategy, metrics)
        
        # Calculate system metrics
        await self._calculate_system_metrics(db, strategy, metrics)
        
        return metrics
    
    async def _calculate_performance_metrics(self, db: Session, strategy: StrategyModel, metrics: MonitoringMetrics):
        """Calculate performance-related metrics"""
        try:
            # Get all trades for this strategy
            trades = db.query(Trade).filter(
                Trade.user_id == strategy.user_id,
                # Add strategy_id filter when available
            ).all()
            
            if trades:
                # Calculate total P&L
                total_pnl = sum(trade.netAmount - (trade.quantity * trade.price) for trade in trades)
                metrics.total_pnl = total_pnl
                
                # Calculate daily P&L
                today = datetime.utcnow().date()
                daily_trades = [t for t in trades if t.tradeTimestamp and t.tradeTimestamp.date() == today]
                daily_pnl = sum(trade.netAmount - (trade.quantity * trade.price) for trade in daily_trades)
                metrics.daily_pnl = daily_pnl
                
                # Calculate win rate
                profitable_trades = [t for t in trades if (t.netAmount - (t.quantity * t.price)) > 0]
                metrics.win_rate = len(profitable_trades) / len(trades) if trades else 0.0
                
                # Calculate max drawdown (simplified)
                if len(trades) > 1:
                    running_pnl = 0
                    peak = 0
                    max_dd = 0
                    for trade in sorted(trades, key=lambda x: x.tradeTimestamp or datetime.min):
                        trade_pnl = trade.netAmount - (trade.quantity * trade.price)
                        running_pnl += trade_pnl
                        peak = max(peak, running_pnl)
                        drawdown = (running_pnl - peak) / peak if peak > 0 else 0
                        max_dd = min(max_dd, drawdown)
                    metrics.max_drawdown = max_dd
                
        except Exception as e:
            logger.error(f"Error calculating performance metrics for {strategy.name}: {e}")
    
    async def _calculate_activity_metrics(self, db: Session, strategy: StrategyModel, metrics: MonitoringMetrics):
        """Calculate activity-related metrics"""
        try:
            # Get orders for this strategy
            orders = db.query(Order).filter(
                Order.user_id == strategy.user_id,
                Order.strategy_id == strategy.id
            ).all()
            
            metrics.total_orders = len(orders)
            metrics.successful_orders = len([o for o in orders if o.status == OrderStatus.COMPLETE])
            metrics.failed_orders = len([o for o in orders if o.status in [OrderStatus.REJECTED, OrderStatus.ERROR]])
            
            # Get active positions
            positions = db.query(Position).filter(
                Position.user_id == strategy.user_id,
                Position.quantity != 0
            ).all()
            
            metrics.active_positions = len(positions)
            
            # Get last order time
            if orders:
                last_order = max(orders, key=lambda x: x.createdAt)
                metrics.last_order_time = last_order.createdAt
                
        except Exception as e:
            logger.error(f"Error calculating activity metrics for {strategy.name}: {e}")
    
    async def _calculate_risk_metrics(self, db: Session, strategy: StrategyModel, metrics: MonitoringMetrics):
        """Calculate risk-related metrics"""
        try:
            # Get user balance
            balance = db.query(Balance).filter(
                Balance.user_id == strategy.user_id
            ).first()
            
            if balance:
                # Calculate current exposure
                positions = db.query(Position).filter(
                    Position.user_id == strategy.user_id,
                    Position.quantity != 0
                ).all()
                
                total_exposure = sum(abs(pos.quantity * pos.lastTradedPrice) for pos in positions)
                metrics.current_exposure = total_exposure
                metrics.risk_utilization = total_exposure / balance.totalBalance if balance.totalBalance > 0 else 0
                
                # Find largest position
                if positions:
                    largest_pos_value = max(abs(pos.quantity * pos.lastTradedPrice) for pos in positions)
                    metrics.largest_position = largest_pos_value / balance.totalBalance if balance.totalBalance > 0 else 0
                
        except Exception as e:
            logger.error(f"Error calculating risk metrics for {strategy.name}: {e}")
    
    async def _calculate_system_metrics(self, db: Session, strategy: StrategyModel, metrics: MonitoringMetrics):
        """Calculate system-related metrics"""
        try:
            # Last signal time (would need to be tracked in strategy logs)
            # For now, use last order time as proxy
            metrics.last_signal_time = metrics.last_order_time
            
            # Execution latency (would need to be measured during order execution)
            # For now, set to 0
            metrics.execution_latency = 0.0
            
            # Error count (would need error tracking)
            metrics.error_count = 0
            
        except Exception as e:
            logger.error(f"Error calculating system metrics for {strategy.name}: {e}")
    
    def _assess_strategy_health(self, metrics: MonitoringMetrics) -> StrategyHealth:
        """Assess overall strategy health based on metrics"""
        thresholds = self._health_thresholds
        critical_issues = 0
        warning_issues = 0
        
        # Check performance health
        if metrics.daily_pnl < thresholds['performance']['max_daily_loss_pct'] * 100000:  # Assuming 100k base
            critical_issues += 1
        
        if metrics.max_drawdown < thresholds['performance']['max_drawdown_pct']:
            warning_issues += 1
        
        if metrics.win_rate < thresholds['performance']['min_win_rate']:
            warning_issues += 1
        
        # Check risk health
        if metrics.risk_utilization > thresholds['risk']['max_exposure_pct']:
            critical_issues += 1
        
        if metrics.largest_position > thresholds['risk']['max_position_pct']:
            warning_issues += 1
        
        # Check system health
        if metrics.error_count > thresholds['system']['max_error_count']:
            critical_issues += 1
        
        if metrics.execution_latency > thresholds['system']['max_latency_ms']:
            warning_issues += 1
        
        # Check if strategy is offline
        if metrics.last_signal_time:
            offline_minutes = (datetime.utcnow() - metrics.last_signal_time).total_seconds() / 60
            if offline_minutes > thresholds['system']['max_offline_minutes']:
                return StrategyHealth.OFFLINE
        
        # Determine overall health
        if critical_issues > 0:
            return StrategyHealth.CRITICAL
        elif warning_issues > 0:
            return StrategyHealth.WARNING
        else:
            return StrategyHealth.HEALTHY
    
    async def _health_checker(self):
        """Continuous health checking"""
        while self.running:
            try:
                await self._check_all_strategy_health()
                await asyncio.sleep(60)  # Check every minute
            except Exception as e:
                logger.error(f"Error in health checker: {e}")
                await asyncio.sleep(60)
    
    async def _check_all_strategy_health(self):
        """Check health of all monitored strategies"""
        for strategy_id, metrics in self._strategy_metrics.items():
            if metrics.health_status in [StrategyHealth.CRITICAL, StrategyHealth.OFFLINE]:
                logger.warning(f"Strategy {metrics.strategy_name} health: {metrics.health_status.value}")
                # Here you could trigger alerts or automatic actions
    
    async def _performance_calculator(self):
        """Calculate advanced performance metrics"""
        while self.running:
            try:
                await self._calculate_advanced_performance()
                await asyncio.sleep(300)  # Every 5 minutes
            except Exception as e:
                logger.error(f"Error in performance calculator: {e}")
                await asyncio.sleep(300)
    
    async def _calculate_advanced_performance(self):
        """Calculate advanced performance metrics like Sharpe ratio"""
        # Implementation for advanced metrics
        pass
    
    async def _risk_monitor(self):
        """Continuous risk monitoring"""
        while self.running:
            try:
                await self._monitor_risk_levels()
                await asyncio.sleep(30)  # Check every 30 seconds
            except Exception as e:
                logger.error(f"Error in risk monitor: {e}")
                await asyncio.sleep(30)
    
    async def _monitor_risk_levels(self):
        """Monitor risk levels across all strategies"""
        for strategy_id, metrics in self._strategy_metrics.items():
            if metrics.risk_utilization > 0.9:  # 90% risk utilization
                logger.warning(f"High risk utilization for {metrics.strategy_name}: {metrics.risk_utilization:.2%}")
    
    def get_strategy_metrics(self, strategy_id: str) -> Optional[MonitoringMetrics]:
        """Get metrics for a specific strategy"""
        return self._strategy_metrics.get(strategy_id)
    
    def get_all_metrics(self) -> Dict[str, MonitoringMetrics]:
        """Get metrics for all monitored strategies"""
        return self._strategy_metrics.copy()
    
    def get_health_summary(self) -> Dict[str, Any]:
        """Get overall health summary"""
        if not self._strategy_metrics:
            return {'total_strategies': 0, 'health_distribution': {}}
        
        health_counts = {}
        for health_status in StrategyHealth:
            health_counts[health_status.value] = sum(
                1 for metrics in self._strategy_metrics.values()
                if metrics.health_status == health_status
            )
        
        return {
            'total_strategies': len(self._strategy_metrics),
            'health_distribution': health_counts,
            'last_update': datetime.utcnow().isoformat()
        }
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """Get overall performance summary"""
        if not self._strategy_metrics:
            return {}
        
        total_pnl = sum(m.total_pnl for m in self._strategy_metrics.values())
        daily_pnl = sum(m.daily_pnl for m in self._strategy_metrics.values())
        avg_win_rate = sum(m.win_rate for m in self._strategy_metrics.values()) / len(self._strategy_metrics)
        
        return {
            'total_pnl': total_pnl,
            'daily_pnl': daily_pnl,
            'average_win_rate': avg_win_rate,
            'active_strategies': len([m for m in self._strategy_metrics.values() if m.health_status != StrategyHealth.OFFLINE])
        }

# Global monitor instance
strategy_monitor = StrategyMonitor()

# Ensure db_manager.initialize() is called at startup (e.g., in main()) 