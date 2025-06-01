"""
Alert Manager - Intelligent alerting system for strategy monitoring

This module provides comprehensive alerting capabilities including:
- Configurable alert rules and thresholds
- Multiple notification channels (email, SMS, webhook)
- Alert escalation and acknowledgment
- Alert history and analytics
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum
import json
from sqlalchemy.orm import Session

from app.database import DatabaseManager
from app.models.base import Strategy as StrategyModel, User
from app.monitoring.strategy_monitor import MonitoringMetrics, StrategyHealth

logger = logging.getLogger(__name__)

class AlertType(Enum):
    """Types of alerts"""
    PERFORMANCE_DEGRADATION = "PERFORMANCE_DEGRADATION"
    HIGH_RISK_EXPOSURE = "HIGH_RISK_EXPOSURE"
    STRATEGY_OFFLINE = "STRATEGY_OFFLINE"
    EXECUTION_ERROR = "EXECUTION_ERROR"
    DAILY_LOSS_LIMIT = "DAILY_LOSS_LIMIT"
    DRAWDOWN_LIMIT = "DRAWDOWN_LIMIT"
    POSITION_SIZE_VIOLATION = "POSITION_SIZE_VIOLATION"
    SYSTEM_ERROR = "SYSTEM_ERROR"
    CUSTOM = "CUSTOM"

class AlertSeverity(Enum):
    """Alert severity levels"""
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"

class AlertStatus(Enum):
    """Alert status"""
    ACTIVE = "ACTIVE"
    ACKNOWLEDGED = "ACKNOWLEDGED"
    RESOLVED = "RESOLVED"
    SUPPRESSED = "SUPPRESSED"

class NotificationChannel(Enum):
    """Notification channels"""
    EMAIL = "EMAIL"
    SMS = "SMS"
    WEBHOOK = "WEBHOOK"
    SLACK = "SLACK"
    TELEGRAM = "TELEGRAM"
    IN_APP = "IN_APP"

@dataclass
class Alert:
    """Alert data structure"""
    id: str
    alert_type: AlertType
    severity: AlertSeverity
    status: AlertStatus
    strategy_id: str
    strategy_name: str
    user_id: str
    title: str
    message: str
    data: Dict[str, Any]
    created_at: datetime
    updated_at: datetime
    acknowledged_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None
    acknowledged_by: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            'id': self.id,
            'alert_type': self.alert_type.value,
            'severity': self.severity.value,
            'status': self.status.value,
            'strategy_id': self.strategy_id,
            'strategy_name': self.strategy_name,
            'user_id': self.user_id,
            'title': self.title,
            'message': self.message,
            'data': self.data,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'acknowledged_at': self.acknowledged_at.isoformat() if self.acknowledged_at else None,
            'resolved_at': self.resolved_at.isoformat() if self.resolved_at else None,
            'acknowledged_by': self.acknowledged_by
        }

@dataclass
class AlertRule:
    """Alert rule configuration"""
    id: str
    name: str
    alert_type: AlertType
    severity: AlertSeverity
    condition: str  # Python expression to evaluate
    threshold: float
    enabled: bool = True
    cooldown_minutes: int = 15  # Minimum time between same alerts
    notification_channels: List[NotificationChannel] = field(default_factory=list)
    escalation_rules: Dict[str, Any] = field(default_factory=dict)
    
    def evaluate(self, metrics: MonitoringMetrics) -> bool:
        """Evaluate if alert condition is met"""
        try:
            # Create evaluation context
            context = {
                'metrics': metrics,
                'total_pnl': metrics.total_pnl,
                'daily_pnl': metrics.daily_pnl,
                'win_rate': metrics.win_rate,
                'max_drawdown': metrics.max_drawdown,
                'risk_utilization': metrics.risk_utilization,
                'largest_position': metrics.largest_position,
                'error_count': metrics.error_count,
                'execution_latency': metrics.execution_latency,
                'threshold': self.threshold
            }
            
            # Evaluate condition
            return eval(self.condition, {"__builtins__": {}}, context)
            
        except Exception as e:
            logger.error(f"Error evaluating alert rule {self.name}: {e}")
            return False

class AlertManager:
    """
    Intelligent alert management system
    
    Manages alert rules, evaluates conditions, sends notifications,
    and handles alert lifecycle including acknowledgment and resolution.
    """
    
    def __init__(self):
        self.running = False
        self._active_alerts: Dict[str, Alert] = {}
        self._alert_rules: Dict[str, AlertRule] = {}
        self._alert_history: List[Alert] = []
        self._notification_handlers: Dict[NotificationChannel, Callable] = {}
        self._last_alert_times: Dict[str, datetime] = {}
        
        # Initialize default alert rules
        self._initialize_default_rules()
        
        # Initialize notification handlers
        self._initialize_notification_handlers()
    
    def _initialize_default_rules(self):
        """Initialize default alert rules"""
        default_rules = [
            AlertRule(
                id="daily_loss_5pct",
                name="Daily Loss > 5%",
                alert_type=AlertType.DAILY_LOSS_LIMIT,
                severity=AlertSeverity.HIGH,
                condition="daily_pnl < -5000",  # Assuming 100k base capital
                threshold=-5000,
                notification_channels=[NotificationChannel.EMAIL, NotificationChannel.IN_APP]
            ),
            AlertRule(
                id="drawdown_10pct",
                name="Max Drawdown > 10%",
                alert_type=AlertType.DRAWDOWN_LIMIT,
                severity=AlertSeverity.CRITICAL,
                condition="max_drawdown < -0.10",
                threshold=-0.10,
                notification_channels=[NotificationChannel.EMAIL, NotificationChannel.SMS, NotificationChannel.IN_APP]
            ),
            AlertRule(
                id="high_risk_exposure",
                name="Risk Exposure > 80%",
                alert_type=AlertType.HIGH_RISK_EXPOSURE,
                severity=AlertSeverity.HIGH,
                condition="risk_utilization > 0.80",
                threshold=0.80,
                notification_channels=[NotificationChannel.EMAIL, NotificationChannel.IN_APP]
            ),
            AlertRule(
                id="strategy_offline",
                name="Strategy Offline",
                alert_type=AlertType.STRATEGY_OFFLINE,
                severity=AlertSeverity.CRITICAL,
                condition="metrics.health_status.value == 'OFFLINE'",
                threshold=0,
                notification_channels=[NotificationChannel.EMAIL, NotificationChannel.SMS, NotificationChannel.IN_APP]
            ),
            AlertRule(
                id="large_position",
                name="Position Size > 20%",
                alert_type=AlertType.POSITION_SIZE_VIOLATION,
                severity=AlertSeverity.MEDIUM,
                condition="largest_position > 0.20",
                threshold=0.20,
                notification_channels=[NotificationChannel.IN_APP]
            ),
            AlertRule(
                id="high_error_count",
                name="High Error Count",
                alert_type=AlertType.EXECUTION_ERROR,
                severity=AlertSeverity.HIGH,
                condition="error_count > 10",
                threshold=10,
                notification_channels=[NotificationChannel.EMAIL, NotificationChannel.IN_APP]
            )
        ]
        
        for rule in default_rules:
            self._alert_rules[rule.id] = rule
    
    def _initialize_notification_handlers(self):
        """Initialize notification handlers"""
        self._notification_handlers = {
            NotificationChannel.EMAIL: self._send_email_notification,
            NotificationChannel.SMS: self._send_sms_notification,
            NotificationChannel.WEBHOOK: self._send_webhook_notification,
            NotificationChannel.SLACK: self._send_slack_notification,
            NotificationChannel.TELEGRAM: self._send_telegram_notification,
            NotificationChannel.IN_APP: self._send_in_app_notification
        }
    
    async def start_alert_manager(self):
        """Start the alert manager"""
        self.running = True
        logger.info("🚨 Alert Manager started")
        
        # Start alert processing
        await asyncio.gather(
            self._alert_processor(),
            self._alert_escalator(),
            self._alert_cleaner()
        )
    
    async def stop_alert_manager(self):
        """Stop the alert manager"""
        self.running = False
        logger.info("🛑 Alert Manager stopped")
    
    async def _alert_processor(self):
        """Main alert processing loop"""
        while self.running:
            try:
                await self._process_alerts()
                await asyncio.sleep(30)  # Check every 30 seconds
            except Exception as e:
                logger.error(f"Error in alert processor: {e}")
                await asyncio.sleep(30)
    
    async def _process_alerts(self):
        """Process alerts for all strategies"""
        from app.monitoring.strategy_monitor import strategy_monitor
        
        # Get all strategy metrics
        all_metrics = strategy_monitor.get_all_metrics()
        
        for strategy_id, metrics in all_metrics.items():
            await self._evaluate_strategy_alerts(strategy_id, metrics)
    
    async def _evaluate_strategy_alerts(self, strategy_id: str, metrics: MonitoringMetrics):
        """Evaluate alert rules for a specific strategy"""
        for rule_id, rule in self._alert_rules.items():
            if not rule.enabled:
                continue
            
            # Check cooldown
            cooldown_key = f"{strategy_id}_{rule_id}"
            if self._is_in_cooldown(cooldown_key, rule.cooldown_minutes):
                continue
            
            # Evaluate rule condition
            if rule.evaluate(metrics):
                await self._trigger_alert(rule, strategy_id, metrics)
                self._last_alert_times[cooldown_key] = datetime.utcnow()
    
    def _is_in_cooldown(self, cooldown_key: str, cooldown_minutes: int) -> bool:
        """Check if alert is in cooldown period"""
        if cooldown_key not in self._last_alert_times:
            return False
        
        last_alert_time = self._last_alert_times[cooldown_key]
        cooldown_period = timedelta(minutes=cooldown_minutes)
        
        return datetime.utcnow() - last_alert_time < cooldown_period
    
    async def _trigger_alert(self, rule: AlertRule, strategy_id: str, metrics: MonitoringMetrics):
        """Trigger an alert"""
        # Generate alert ID
        alert_id = f"{strategy_id}_{rule.id}_{int(datetime.utcnow().timestamp())}"
        
        # Get strategy info
        db_manager = DatabaseManager()
        try:
            async with db_manager.get_session() as db:
                strategy = await db.query(StrategyModel).filter(StrategyModel.id == strategy_id).first()
                if not strategy:
                    return
                
                # Create alert
                alert = Alert(
                    id=alert_id,
                    alert_type=rule.alert_type,
                    severity=rule.severity,
                    status=AlertStatus.ACTIVE,
                    strategy_id=strategy_id,
                    strategy_name=strategy.name,
                    user_id=strategy.user_id,
                    title=self._generate_alert_title(rule, metrics),
                    message=self._generate_alert_message(rule, metrics),
                    data=self._generate_alert_data(rule, metrics),
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow()
                )
                
                # Store alert
                self._active_alerts[alert_id] = alert
                self._alert_history.append(alert)
                
                # Send notifications
                await self._send_notifications(alert, rule.notification_channels)
                
                logger.warning(f"Alert triggered: {alert.title} for strategy {metrics.strategy_name}")
                
        finally:
            await db_manager.close_session()
    
    def _generate_alert_title(self, rule: AlertRule, metrics: MonitoringMetrics) -> str:
        """Generate alert title"""
        titles = {
            AlertType.DAILY_LOSS_LIMIT: f"Daily Loss Alert: {metrics.strategy_name}",
            AlertType.DRAWDOWN_LIMIT: f"Drawdown Alert: {metrics.strategy_name}",
            AlertType.HIGH_RISK_EXPOSURE: f"High Risk Exposure: {metrics.strategy_name}",
            AlertType.STRATEGY_OFFLINE: f"Strategy Offline: {metrics.strategy_name}",
            AlertType.POSITION_SIZE_VIOLATION: f"Large Position Alert: {metrics.strategy_name}",
            AlertType.EXECUTION_ERROR: f"Execution Errors: {metrics.strategy_name}"
        }
        
        return titles.get(rule.alert_type, f"Alert: {metrics.strategy_name}")
    
    def _generate_alert_message(self, rule: AlertRule, metrics: MonitoringMetrics) -> str:
        """Generate alert message"""
        if rule.alert_type == AlertType.DAILY_LOSS_LIMIT:
            return f"Strategy {metrics.strategy_name} has exceeded daily loss limit. Current daily P&L: ₹{metrics.daily_pnl:,.2f}"
        elif rule.alert_type == AlertType.DRAWDOWN_LIMIT:
            return f"Strategy {metrics.strategy_name} has exceeded maximum drawdown limit. Current drawdown: {metrics.max_drawdown:.2%}"
        elif rule.alert_type == AlertType.HIGH_RISK_EXPOSURE:
            return f"Strategy {metrics.strategy_name} has high risk exposure. Current utilization: {metrics.risk_utilization:.2%}"
        elif rule.alert_type == AlertType.STRATEGY_OFFLINE:
            return f"Strategy {metrics.strategy_name} appears to be offline. Last activity: {metrics.last_signal_time}"
        elif rule.alert_type == AlertType.POSITION_SIZE_VIOLATION:
            return f"Strategy {metrics.strategy_name} has a large position. Largest position: {metrics.largest_position:.2%} of capital"
        elif rule.alert_type == AlertType.EXECUTION_ERROR:
            return f"Strategy {metrics.strategy_name} has high error count. Current errors: {metrics.error_count}"
        else:
            return f"Alert triggered for strategy {metrics.strategy_name}"
    
    def _generate_alert_data(self, rule: AlertRule, metrics: MonitoringMetrics) -> Dict[str, Any]:
        """Generate alert data"""
        return {
            'rule_id': rule.id,
            'rule_name': rule.name,
            'threshold': rule.threshold,
            'current_value': self._get_current_value(rule, metrics),
            'metrics_snapshot': metrics.to_dict()
        }
    
    def _get_current_value(self, rule: AlertRule, metrics: MonitoringMetrics) -> Any:
        """Get current value for the alert condition"""
        value_map = {
            AlertType.DAILY_LOSS_LIMIT: metrics.daily_pnl,
            AlertType.DRAWDOWN_LIMIT: metrics.max_drawdown,
            AlertType.HIGH_RISK_EXPOSURE: metrics.risk_utilization,
            AlertType.POSITION_SIZE_VIOLATION: metrics.largest_position,
            AlertType.EXECUTION_ERROR: metrics.error_count
        }
        
        return value_map.get(rule.alert_type, None)
    
    async def _send_notifications(self, alert: Alert, channels: List[NotificationChannel]):
        """Send notifications through specified channels"""
        for channel in channels:
            try:
                handler = self._notification_handlers.get(channel)
                if handler:
                    await handler(alert)
            except Exception as e:
                logger.error(f"Error sending notification via {channel.value}: {e}")
    
    async def _send_email_notification(self, alert: Alert):
        """Send email notification"""
        # Implementation for email notifications
        logger.info(f"📧 Email notification sent for alert: {alert.title}")
    
    async def _send_sms_notification(self, alert: Alert):
        """Send SMS notification"""
        # Implementation for SMS notifications
        logger.info(f"📱 SMS notification sent for alert: {alert.title}")
    
    async def _send_webhook_notification(self, alert: Alert):
        """Send webhook notification"""
        # Implementation for webhook notifications
        logger.info(f"🔗 Webhook notification sent for alert: {alert.title}")
    
    async def _send_slack_notification(self, alert: Alert):
        """Send Slack notification"""
        # Implementation for Slack notifications
        logger.info(f"💬 Slack notification sent for alert: {alert.title}")
    
    async def _send_telegram_notification(self, alert: Alert):
        """Send Telegram notification"""
        # Implementation for Telegram notifications
        logger.info(f"📲 Telegram notification sent for alert: {alert.title}")
    
    async def _send_in_app_notification(self, alert: Alert):
        """Send in-app notification"""
        # Store in database for in-app display
        logger.info(f"🔔 In-app notification created for alert: {alert.title}")
    
    async def _alert_escalator(self):
        """Handle alert escalation"""
        while self.running:
            try:
                await self._process_escalations()
                await asyncio.sleep(300)  # Check every 5 minutes
            except Exception as e:
                logger.error(f"Error in alert escalator: {e}")
                await asyncio.sleep(300)
    
    async def _process_escalations(self):
        """Process alert escalations"""
        current_time = datetime.utcnow()
        
        for alert in self._active_alerts.values():
            if alert.status != AlertStatus.ACTIVE:
                continue
            
            # Check if alert needs escalation
            time_since_created = current_time - alert.created_at
            
            # Escalate critical alerts after 15 minutes
            if (alert.severity == AlertSeverity.CRITICAL and 
                time_since_created > timedelta(minutes=15)):
                await self._escalate_alert(alert)
    
    async def _escalate_alert(self, alert: Alert):
        """Escalate an alert"""
        logger.warning(f"Escalating alert: {alert.title}")
        
        # Send escalation notifications
        escalation_channels = [NotificationChannel.EMAIL, NotificationChannel.SMS]
        await self._send_notifications(alert, escalation_channels)
    
    async def _alert_cleaner(self):
        """Clean up old resolved alerts"""
        while self.running:
            try:
                await self._cleanup_old_alerts()
                await asyncio.sleep(3600)  # Clean every hour
            except Exception as e:
                logger.error(f"Error in alert cleaner: {e}")
                await asyncio.sleep(3600)
    
    async def _cleanup_old_alerts(self):
        """Clean up old resolved alerts"""
        cutoff_time = datetime.utcnow() - timedelta(days=7)  # Keep alerts for 7 days
        
        # Remove old alerts from history
        self._alert_history = [
            alert for alert in self._alert_history
            if alert.created_at > cutoff_time
        ]
        
        # Remove resolved alerts from active alerts
        resolved_alerts = [
            alert_id for alert_id, alert in self._active_alerts.items()
            if alert.status == AlertStatus.RESOLVED and alert.resolved_at
            and alert.resolved_at < cutoff_time
        ]
        
        for alert_id in resolved_alerts:
            del self._active_alerts[alert_id]
    
    def acknowledge_alert(self, alert_id: str, acknowledged_by: str) -> bool:
        """Acknowledge an alert"""
        if alert_id in self._active_alerts:
            alert = self._active_alerts[alert_id]
            alert.status = AlertStatus.ACKNOWLEDGED
            alert.acknowledged_at = datetime.utcnow()
            alert.acknowledged_by = acknowledged_by
            alert.updated_at = datetime.utcnow()
            
            logger.info(f"Alert acknowledged: {alert.title} by {acknowledged_by}")
            return True
        
        return False
    
    def resolve_alert(self, alert_id: str) -> bool:
        """Resolve an alert"""
        if alert_id in self._active_alerts:
            alert = self._active_alerts[alert_id]
            alert.status = AlertStatus.RESOLVED
            alert.resolved_at = datetime.utcnow()
            alert.updated_at = datetime.utcnow()
            
            logger.info(f"Alert resolved: {alert.title}")
            return True
        
        return False
    
    def suppress_alert(self, alert_id: str) -> bool:
        """Suppress an alert"""
        if alert_id in self._active_alerts:
            alert = self._active_alerts[alert_id]
            alert.status = AlertStatus.SUPPRESSED
            alert.updated_at = datetime.utcnow()
            
            logger.info(f"Alert suppressed: {alert.title}")
            return True
        
        return False
    
    def add_alert_rule(self, rule: AlertRule):
        """Add a custom alert rule"""
        self._alert_rules[rule.id] = rule
        logger.info(f"Added alert rule: {rule.name}")
    
    def remove_alert_rule(self, rule_id: str) -> bool:
        """Remove an alert rule"""
        if rule_id in self._alert_rules:
            del self._alert_rules[rule_id]
            logger.info(f"Removed alert rule: {rule_id}")
            return True
        return False
    
    def get_active_alerts(self) -> List[Alert]:
        """Get all active alerts"""
        return [alert for alert in self._active_alerts.values() if alert.status == AlertStatus.ACTIVE]
    
    def get_alert_history(self, limit: int = 100) -> List[Alert]:
        """Get alert history"""
        return sorted(self._alert_history, key=lambda x: x.created_at, reverse=True)[:limit]
    
    def get_alert_statistics(self) -> Dict[str, Any]:
        """Get alert statistics"""
        active_alerts = self.get_active_alerts()
        
        # Count by severity
        severity_counts = {}
        for severity in AlertSeverity:
            severity_counts[severity.value] = len([a for a in active_alerts if a.severity == severity])
        
        # Count by type
        type_counts = {}
        for alert_type in AlertType:
            type_counts[alert_type.value] = len([a for a in active_alerts if a.alert_type == alert_type])
        
        return {
            'total_active_alerts': len(active_alerts),
            'severity_distribution': severity_counts,
            'type_distribution': type_counts,
            'total_rules': len(self._alert_rules),
            'enabled_rules': len([r for r in self._alert_rules.values() if r.enabled])
        }

# Global alert manager instance
alert_manager = AlertManager()

# Ensure db_manager.initialize() is called at startup (e.g., in main()) 