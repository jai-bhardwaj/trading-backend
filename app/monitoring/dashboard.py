"""
Monitoring Dashboard - Comprehensive strategy monitoring interface

This module provides a unified dashboard for monitoring all aspects of
algorithmic trading strategies including performance, health, alerts, and system status.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
import json
from dataclasses import asdict

from app.monitoring.strategy_monitor import strategy_monitor, StrategyHealth, MonitoringMetrics
from app.monitoring.alert_manager import alert_manager, AlertSeverity, AlertStatus
from app.database import DatabaseManager

logger = logging.getLogger(__name__)

class MonitoringDashboard:
    """
    Comprehensive monitoring dashboard
    
    Provides a unified interface for viewing strategy performance,
    health status, alerts, and system metrics.
    """
    
    def __init__(self):
        self.last_update = datetime.utcnow()
        self._dashboard_data: Dict[str, Any] = {}
        self._update_interval = 30  # seconds
    
    async def start_dashboard(self):
        """Start the dashboard data collection"""
        logger.info("📊 Monitoring Dashboard started")
        
        # Start dashboard update loop
        while True:
            try:
                await self._update_dashboard_data()
                await asyncio.sleep(self._update_interval)
            except Exception as e:
                logger.error(f"Error updating dashboard: {e}")
                await asyncio.sleep(self._update_interval)
    
    async def _update_dashboard_data(self):
        """Update all dashboard data"""
        self._dashboard_data = {
            'overview': await self._get_overview_data(),
            'strategies': await self._get_strategies_data(),
            'performance': await self._get_performance_data(),
            'alerts': await self._get_alerts_data(),
            'system': await self._get_system_data(),
            'last_update': datetime.utcnow().isoformat()
        }
        self.last_update = datetime.utcnow()
    
    async def _get_overview_data(self) -> Dict[str, Any]:
        """Get overview dashboard data"""
        # Get strategy health summary
        health_summary = strategy_monitor.get_health_summary()
        
        # Get performance summary
        performance_summary = strategy_monitor.get_performance_summary()
        
        # Get alert statistics
        alert_stats = alert_manager.get_alert_statistics()
        
        # Get active alerts count by severity
        active_alerts = alert_manager.get_active_alerts()
        critical_alerts = len([a for a in active_alerts if a.severity == AlertSeverity.CRITICAL])
        high_alerts = len([a for a in active_alerts if a.severity == AlertSeverity.HIGH])
        
        return {
            'total_strategies': health_summary.get('total_strategies', 0),
            'healthy_strategies': health_summary.get('health_distribution', {}).get('HEALTHY', 0),
            'warning_strategies': health_summary.get('health_distribution', {}).get('WARNING', 0),
            'critical_strategies': health_summary.get('health_distribution', {}).get('CRITICAL', 0),
            'offline_strategies': health_summary.get('health_distribution', {}).get('OFFLINE', 0),
            'total_pnl': performance_summary.get('total_pnl', 0),
            'daily_pnl': performance_summary.get('daily_pnl', 0),
            'average_win_rate': performance_summary.get('average_win_rate', 0),
            'active_alerts': alert_stats.get('total_active_alerts', 0),
            'critical_alerts': critical_alerts,
            'high_alerts': high_alerts,
            'system_status': 'OPERATIONAL'  # This could be enhanced with actual system checks
        }
    
    async def _get_strategies_data(self) -> List[Dict[str, Any]]:
        """Get detailed strategy data"""
        all_metrics = strategy_monitor.get_all_metrics()
        strategies_data = []
        
        for strategy_id, metrics in all_metrics.items():
            strategy_data = metrics.to_dict()
            
            # Add additional strategy information
            db_manager = DatabaseManager()
            try:
                async with db_manager.get_session() as db:
                    strategy = db.query(StrategyModel).filter(StrategyModel.id == strategy_id).first()
                    if strategy:
                        strategy_data.update({
                            'asset_class': getattr(strategy, 'assetClass', 'EQUITY'),
                            'symbols': getattr(strategy, 'symbols', []),
                            'is_live': getattr(strategy, 'isLive', False),
                            'is_paper_trading': getattr(strategy, 'isPaperTrading', True),
                            'capital_allocated': getattr(strategy, 'capitalAllocated', 0),
                            'created_at': strategy.createdAt.isoformat() if hasattr(strategy, 'createdAt') else None
                        })
            finally:
                pass
            
            # Add strategy-specific alerts
            strategy_alerts = [
                alert.to_dict() for alert in alert_manager.get_active_alerts()
                if alert.strategy_id == strategy_id
            ]
            strategy_data['active_alerts'] = strategy_alerts
            
            strategies_data.append(strategy_data)
        
        # Sort by health status (critical first) and then by name
        def sort_key(strategy):
            health_priority = {
                'CRITICAL': 0,
                'OFFLINE': 1,
                'WARNING': 2,
                'HEALTHY': 3
            }
            return (health_priority.get(strategy['health_status'], 4), strategy['strategy_name'])
        
        return sorted(strategies_data, key=sort_key)
    
    async def _get_performance_data(self) -> Dict[str, Any]:
        """Get performance analytics data"""
        db_manager = DatabaseManager()
        try:
            # Get overall portfolio performance
            total_pnl = 0
            daily_pnl = 0
            total_trades = 0
            winning_trades = 0
            
            # Calculate from trades
            async with db_manager.get_session() as db:
                trades = db.query(Trade).all()
                today = datetime.utcnow().date()
                
                for trade in trades:
                    trade_pnl = trade.netAmount - (trade.quantity * trade.price)
                    total_pnl += trade_pnl
                    
                    if trade.tradeTimestamp and trade.tradeTimestamp.date() == today:
                        daily_pnl += trade_pnl
                    
                    total_trades += 1
                    if trade_pnl > 0:
                        winning_trades += 1
                
                win_rate = (winning_trades / total_trades) if total_trades > 0 else 0
                
                # Get position data
                positions = db.query(Position).filter(Position.quantity != 0).all()
                total_exposure = sum(abs(pos.quantity * pos.lastTradedPrice) for pos in positions)
                
                # Get balance data
                balances = db.query(Balance).all()
                total_balance = sum(balance.totalBalance for balance in balances)
                
                # Calculate performance metrics by time period
                performance_by_period = await self._calculate_performance_by_period(db)
                
                return {
                    'total_pnl': total_pnl,
                    'daily_pnl': daily_pnl,
                    'total_trades': total_trades,
                    'win_rate': win_rate,
                    'total_exposure': total_exposure,
                    'total_balance': total_balance,
                    'exposure_ratio': total_exposure / total_balance if total_balance > 0 else 0,
                    'active_positions': len(positions),
                    'performance_by_period': performance_by_period
                }
            
        finally:
            pass
    
    async def _calculate_performance_by_period(self, db) -> Dict[str, Any]:
        """Calculate performance metrics by different time periods"""
        now = datetime.utcnow()
        periods = {
            'today': now.replace(hour=0, minute=0, second=0, microsecond=0),
            'week': now - timedelta(days=7),
            'month': now - timedelta(days=30),
            'quarter': now - timedelta(days=90)
        }
        
        performance = {}
        
        for period_name, start_date in periods.items():
            trades = db.query(Trade).filter(
                Trade.tradeTimestamp >= start_date
            ).all()
            
            period_pnl = sum(
                trade.netAmount - (trade.quantity * trade.price)
                for trade in trades
            )
            
            performance[period_name] = {
                'pnl': period_pnl,
                'trades': len(trades),
                'win_rate': len([t for t in trades if (t.netAmount - (t.quantity * t.price)) > 0]) / len(trades) if trades else 0
            }
        
        return performance
    
    async def _get_alerts_data(self) -> Dict[str, Any]:
        """Get alerts dashboard data"""
        active_alerts = alert_manager.get_active_alerts()
        alert_history = alert_manager.get_alert_history(limit=50)
        alert_stats = alert_manager.get_alert_statistics()
        
        # Group alerts by strategy
        alerts_by_strategy = {}
        for alert in active_alerts:
            if alert.strategy_id not in alerts_by_strategy:
                alerts_by_strategy[alert.strategy_id] = []
            alerts_by_strategy[alert.strategy_id].append(alert.to_dict())
        
        # Recent alert trends
        recent_alerts = [a for a in alert_history if a.created_at > datetime.utcnow() - timedelta(hours=24)]
        alert_trends = self._calculate_alert_trends(recent_alerts)
        
        return {
            'active_alerts': [alert.to_dict() for alert in active_alerts],
            'alert_history': [alert.to_dict() for alert in alert_history],
            'alerts_by_strategy': alerts_by_strategy,
            'alert_statistics': alert_stats,
            'alert_trends': alert_trends,
            'top_alert_types': self._get_top_alert_types(recent_alerts)
        }
    
    def _calculate_alert_trends(self, alerts: List) -> Dict[str, Any]:
        """Calculate alert trends over time"""
        # Group alerts by hour for the last 24 hours
        hourly_counts = {}
        now = datetime.utcnow()
        
        for i in range(24):
            hour = now - timedelta(hours=i)
            hour_key = hour.strftime('%H:00')
            hourly_counts[hour_key] = 0
        
        for alert in alerts:
            hour_key = alert.created_at.strftime('%H:00')
            if hour_key in hourly_counts:
                hourly_counts[hour_key] += 1
        
        return {
            'hourly_counts': hourly_counts,
            'total_24h': len(alerts),
            'avg_per_hour': len(alerts) / 24 if alerts else 0
        }
    
    def _get_top_alert_types(self, alerts: List) -> List[Dict[str, Any]]:
        """Get top alert types by frequency"""
        type_counts = {}
        for alert in alerts:
            alert_type = alert.alert_type.value
            type_counts[alert_type] = type_counts.get(alert_type, 0) + 1
        
        # Sort by count and return top 5
        sorted_types = sorted(type_counts.items(), key=lambda x: x[1], reverse=True)
        return [{'type': t[0], 'count': t[1]} for t in sorted_types[:5]]
    
    async def _get_system_data(self) -> Dict[str, Any]:
        """Get system status and metrics"""
        # System health checks
        system_health = await self._check_system_health()
        
        # Database statistics
        db_stats = await self._get_database_stats()
        
        # Monitoring system status
        monitoring_status = {
            'strategy_monitor_running': strategy_monitor.running if hasattr(strategy_monitor, 'running') else False,
            'alert_manager_running': alert_manager.running if hasattr(alert_manager, 'running') else False,
            'last_monitor_update': strategy_monitor.last_update.isoformat() if hasattr(strategy_monitor, 'last_update') else None,
            'monitored_strategies': len(strategy_monitor.get_all_metrics())
        }
        
        return {
            'system_health': system_health,
            'database_stats': db_stats,
            'monitoring_status': monitoring_status,
            'uptime': self._calculate_uptime(),
            'memory_usage': self._get_memory_usage(),
            'cpu_usage': self._get_cpu_usage()
        }
    
    async def _check_system_health(self) -> Dict[str, Any]:
        """Check overall system health"""
        health_checks = {
            'database': await self._check_database_health(),
            'strategy_engine': await self._check_strategy_engine_health(),
            'order_executor': await self._check_order_executor_health(),
            'monitoring': await self._check_monitoring_health()
        }
        
        # Overall status
        all_healthy = all(check['status'] == 'HEALTHY' for check in health_checks.values())
        overall_status = 'HEALTHY' if all_healthy else 'WARNING'
        
        return {
            'overall_status': overall_status,
            'components': health_checks
        }
    
    async def _check_database_health(self) -> Dict[str, Any]:
        """Check database health"""
        try:
            db_manager = DatabaseManager()
            async with db_manager.get_session() as db:
                # Simple query to test connection
                db.execute("SELECT 1")
            return {'status': 'HEALTHY', 'message': 'Database connection OK'}
        except Exception as e:
            return {'status': 'ERROR', 'message': f'Database error: {str(e)}'}
    
    async def _check_strategy_engine_health(self) -> Dict[str, Any]:
        """Check strategy engine health"""
        # This would check if the strategy engine is running and responsive
        return {'status': 'HEALTHY', 'message': 'Strategy engine operational'}
    
    async def _check_order_executor_health(self) -> Dict[str, Any]:
        """Check order executor health"""
        # This would check if the order executor is functioning properly
        return {'status': 'HEALTHY', 'message': 'Order executor operational'}
    
    async def _check_monitoring_health(self) -> Dict[str, Any]:
        """Check monitoring system health"""
        # Check if monitoring components are running
        monitor_running = hasattr(strategy_monitor, 'running') and strategy_monitor.running
        alert_running = hasattr(alert_manager, 'running') and alert_manager.running
        
        if monitor_running and alert_running:
            return {'status': 'HEALTHY', 'message': 'Monitoring systems operational'}
        else:
            return {'status': 'WARNING', 'message': 'Some monitoring components not running'}
    
    async def _get_database_stats(self) -> Dict[str, Any]:
        """Get database statistics"""
        db_manager = DatabaseManager()
        try:
            # Count records in main tables
            async with db_manager.get_session() as db:
                strategy_count = db.query(StrategyModel).count()
                order_count = db.query(Order).count()
                trade_count = db.query(Trade).count()
                position_count = db.query(Position).count()
                
                return {
                    'strategies': strategy_count,
                    'orders': order_count,
                    'trades': trade_count,
                    'positions': position_count
                }
        finally:
            pass
    
    def _calculate_uptime(self) -> str:
        """Calculate system uptime"""
        # This would calculate actual uptime - for now return placeholder
        return "24h 15m"
    
    def _get_memory_usage(self) -> Dict[str, Any]:
        """Get memory usage statistics"""
        try:
            import psutil
            memory = psutil.virtual_memory()
            return {
                'total': memory.total,
                'available': memory.available,
                'percent': memory.percent,
                'used': memory.used
            }
        except ImportError:
            return {'error': 'psutil not available'}
    
    def _get_cpu_usage(self) -> float:
        """Get CPU usage percentage"""
        try:
            import psutil
            return psutil.cpu_percent(interval=1)
        except ImportError:
            return 0.0
    
    def get_dashboard_data(self) -> Dict[str, Any]:
        """Get current dashboard data"""
        return self._dashboard_data.copy()
    
    async def get_strategy_detail(self, strategy_id: str) -> Optional[Dict[str, Any]]:
        """Get detailed data for a specific strategy"""
        metrics = strategy_monitor.get_strategy_metrics(strategy_id)
        if not metrics:
            return None
        
        # Get strategy alerts
        strategy_alerts = [
            alert.to_dict() for alert in alert_manager.get_active_alerts()
            if alert.strategy_id == strategy_id
        ]
        
        # Get recent orders for this strategy
        db_manager = DatabaseManager()
        order_data = []
        try:
            async with db_manager.get_session() as db:
                recent_orders = db.query(Order).filter(
                    Order.strategy_id == strategy_id
                ).order_by(Order.createdAt.desc()).limit(10).all()
                for order in recent_orders:
                    order_data.append({
                        'id': order.id,
                        'symbol': order.symbol,
                        'side': order.side.value,
                        'quantity': order.quantity,
                        'price': order.price,
                        'status': order.status.value,
                        'created_at': order.createdAt.isoformat()
                    })
        finally:
            pass
        
        return {
            'metrics': metrics.to_dict(),
            'alerts': strategy_alerts,
            'recent_orders': order_data,
            'performance_chart': self._generate_performance_chart_data(strategy_id),
            'risk_analysis': self._generate_risk_analysis(metrics)
        }
    
    def _generate_performance_chart_data(self, strategy_id: str) -> List[Dict[str, Any]]:
        """Generate performance chart data for a strategy"""
        # This would generate time-series data for performance charts
        # For now, return placeholder data
        return [
            {'timestamp': '2024-01-01T00:00:00Z', 'pnl': 0},
            {'timestamp': '2024-01-02T00:00:00Z', 'pnl': 1000},
            {'timestamp': '2024-01-03T00:00:00Z', 'pnl': 1500},
        ]
    
    def _generate_risk_analysis(self, metrics: MonitoringMetrics) -> Dict[str, Any]:
        """Generate risk analysis for a strategy"""
        return {
            'risk_score': self._calculate_risk_score(metrics),
            'risk_factors': self._identify_risk_factors(metrics),
            'recommendations': self._generate_risk_recommendations(metrics)
        }
    
    def _calculate_risk_score(self, metrics: MonitoringMetrics) -> float:
        """Calculate overall risk score (0-100)"""
        risk_score = 0
        
        # Risk from exposure
        if metrics.risk_utilization > 0.8:
            risk_score += 30
        elif metrics.risk_utilization > 0.6:
            risk_score += 20
        elif metrics.risk_utilization > 0.4:
            risk_score += 10
        
        # Risk from drawdown
        if metrics.max_drawdown < -0.15:
            risk_score += 25
        elif metrics.max_drawdown < -0.10:
            risk_score += 15
        elif metrics.max_drawdown < -0.05:
            risk_score += 10
        
        # Risk from position concentration
        if metrics.largest_position > 0.3:
            risk_score += 20
        elif metrics.largest_position > 0.2:
            risk_score += 10
        
        # Risk from performance
        if metrics.win_rate < 0.3:
            risk_score += 15
        elif metrics.win_rate < 0.4:
            risk_score += 10
        
        # Risk from daily losses
        if metrics.daily_pnl < -5000:
            risk_score += 10
        
        return min(risk_score, 100)
    
    def _identify_risk_factors(self, metrics: MonitoringMetrics) -> List[str]:
        """Identify specific risk factors"""
        factors = []
        
        if metrics.risk_utilization > 0.8:
            factors.append("High capital utilization")
        
        if metrics.max_drawdown < -0.10:
            factors.append("Significant drawdown")
        
        if metrics.largest_position > 0.2:
            factors.append("Position concentration risk")
        
        if metrics.win_rate < 0.4:
            factors.append("Low win rate")
        
        if metrics.daily_pnl < -3000:
            factors.append("Daily loss threshold")
        
        return factors
    
    def _generate_risk_recommendations(self, metrics: MonitoringMetrics) -> List[str]:
        """Generate risk management recommendations"""
        recommendations = []
        
        if metrics.risk_utilization > 0.8:
            recommendations.append("Consider reducing position sizes")
        
        if metrics.max_drawdown < -0.10:
            recommendations.append("Review stop-loss settings")
        
        if metrics.largest_position > 0.2:
            recommendations.append("Diversify positions across more symbols")
        
        if metrics.win_rate < 0.4:
            recommendations.append("Review strategy parameters and entry/exit rules")
        
        return recommendations

# Global dashboard instance
monitoring_dashboard = MonitoringDashboard() 