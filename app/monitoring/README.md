# 🔍 **Strategy Monitoring System**

A comprehensive real-time monitoring system for algorithmic trading strategies with intelligent alerting, performance tracking, and risk management.

## 📋 **Overview**

The Strategy Monitoring System provides enterprise-grade monitoring capabilities for your algorithmic trading engine, including:

- **Real-time Strategy Health Monitoring** - Track strategy performance, health, and status
- **Intelligent Alerting** - Configurable alerts with multiple notification channels
- **Performance Analytics** - Comprehensive performance metrics and risk analysis
- **Unified Dashboard** - Single interface for monitoring all strategies
- **Command-Line Interface** - Quick access to monitoring data via CLI

## 🏗️ **Architecture**

```
┌─────────────────────────────────────────────────────────────┐
│                 Strategy Monitoring System                  │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────────┐  ┌─────────────────┐  ┌──────────────┐ │
│  │ Strategy Monitor│  │  Alert Manager  │  │  Dashboard   │ │
│  │                 │  │                 │  │              │ │
│  │ • Health Checks │  │ • Alert Rules   │  │ • Overview   │ │
│  │ • Performance   │  │ • Notifications │  │ • Analytics  │ │
│  │ • Risk Metrics  │  │ • Escalation    │  │ • Reports    │ │
│  │ • System Status │  │ • History       │  │ • API        │ │
│  └─────────────────┘  └─────────────────┘  └──────────────┘ │
├─────────────────────────────────────────────────────────────┤
│                    Database & Storage                       │
│  ┌─────────────────┐  ┌─────────────────┐  ┌──────────────┐ │
│  │   Strategies    │  │     Orders      │  │   Trades     │ │
│  │   Positions     │  │    Balances     │  │   Alerts     │ │
│  └─────────────────┘  └─────────────────┘  └──────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

## 🚀 **Quick Start**

### **1. Start the Monitoring Service**

```bash
# Start the complete monitoring system
python -m app.monitoring.main

# Or run individual components
python -m app.monitoring.strategy_monitor
python -m app.monitoring.alert_manager
```

### **2. Use the CLI Interface**

```bash
# Check overall status
python -m app.monitoring.cli status

# View all strategies
python -m app.monitoring.cli strategies

# Check active alerts
python -m app.monitoring.cli alerts

# View performance summary
python -m app.monitoring.cli performance
```

### **3. Monitor via Dashboard**

```python
from app.monitoring.dashboard import monitoring_dashboard

# Get dashboard data
dashboard_data = monitoring_dashboard.get_dashboard_data()

# Get strategy details
strategy_detail = monitoring_dashboard.get_strategy_detail("strategy_id")
```

## 📊 **Components**

### **1. Strategy Monitor (`strategy_monitor.py`)**

Real-time monitoring of strategy health and performance.

**Features:**
- ✅ Health status tracking (HEALTHY, WARNING, CRITICAL, OFFLINE)
- 📈 Performance metrics (P&L, win rate, drawdown)
- ⚠️ Risk monitoring (exposure, position size, utilization)
- 🔧 System metrics (latency, errors, uptime)

**Health Thresholds:**
```python
{
    'performance': {
        'max_daily_loss_pct': -0.05,    # -5%
        'max_drawdown_pct': -0.10,      # -10%
        'min_win_rate': 0.30            # 30%
    },
    'risk': {
        'max_exposure_pct': 0.80,       # 80%
        'max_position_pct': 0.20        # 20%
    },
    'system': {
        'max_error_count': 10,
        'max_latency_ms': 5000,         # 5 seconds
        'max_offline_minutes': 15
    }
}
```

### **2. Alert Manager (`alert_manager.py`)**

Intelligent alerting system with configurable rules and notifications.

**Features:**
- 🚨 Configurable alert rules with Python expressions
- 📧 Multiple notification channels (Email, SMS, Slack, Webhook)
- ⏰ Alert cooldown and escalation
- 📝 Alert acknowledgment and resolution
- 📊 Alert analytics and trends

**Default Alert Rules:**
- **Daily Loss > 5%** - High severity
- **Max Drawdown > 10%** - Critical severity
- **Risk Exposure > 80%** - High severity
- **Strategy Offline** - Critical severity
- **Position Size > 20%** - Medium severity
- **High Error Count** - High severity

**Notification Channels:**
- 📧 Email
- 📱 SMS
- 🔗 Webhook
- 💬 Slack
- 📲 Telegram
- 🔔 In-App

### **3. Dashboard (`dashboard.py`)**

Unified monitoring interface with comprehensive analytics.

**Features:**
- 📋 Overview dashboard with key metrics
- 📊 Strategy-specific detailed views
- 📈 Performance analytics by time period
- 🚨 Alert management and history
- 🏥 System health monitoring
- 📊 Risk analysis and recommendations

**Dashboard Sections:**
- **Overview** - High-level system status
- **Strategies** - Individual strategy monitoring
- **Performance** - P&L and trading analytics
- **Alerts** - Active alerts and history
- **System** - Infrastructure health

## 🛠️ **CLI Commands**

### **Status Commands**
```bash
# Overall system status
python -m app.monitoring.cli status

# Strategy health summary
python -m app.monitoring.cli health

# System performance
python -m app.monitoring.cli performance
```

### **Strategy Commands**
```bash
# List all strategies
python -m app.monitoring.cli strategies

# Detailed strategy view
python -m app.monitoring.cli strategy --strategy-id STRATEGY_ID
```

### **Alert Commands**
```bash
# View active alerts
python -m app.monitoring.cli alerts

# Acknowledge alert
python -m app.monitoring.cli ack --alert-id ALERT_ID --user "John Doe"

# Resolve alert
python -m app.monitoring.cli resolve --alert-id ALERT_ID
```

### **Dashboard Commands**
```bash
# Full dashboard (human-readable)
python -m app.monitoring.cli dashboard

# Dashboard data (JSON format)
python -m app.monitoring.cli dashboard --json
```

## ⚙️ **Configuration**

### **Monitoring Levels**
```python
from app.monitoring.strategy_monitor import MonitoringLevel

# Basic monitoring (essential metrics only)
monitor = StrategyMonitor(MonitoringLevel.BASIC)

# Detailed monitoring (default)
monitor = StrategyMonitor(MonitoringLevel.DETAILED)

# Comprehensive monitoring (all metrics)
monitor = StrategyMonitor(MonitoringLevel.COMPREHENSIVE)
```

### **Custom Alert Rules**
```python
from app.monitoring.alert_manager import AlertRule, AlertType, AlertSeverity

# Create custom alert rule
custom_rule = AlertRule(
    id="custom_win_rate",
    name="Low Win Rate Alert",
    alert_type=AlertType.PERFORMANCE_DEGRADATION,
    severity=AlertSeverity.MEDIUM,
    condition="win_rate < 0.25",  # Win rate below 25%
    threshold=0.25,
    notification_channels=[NotificationChannel.EMAIL]
)

# Add to alert manager
alert_manager.add_alert_rule(custom_rule)
```

### **Health Thresholds**
```python
# Customize health thresholds
custom_thresholds = {
    'performance': {
        'max_daily_loss_pct': -0.03,    # -3% (more strict)
        'max_drawdown_pct': -0.08,      # -8% (more strict)
        'min_win_rate': 0.40            # 40% (higher requirement)
    }
}

strategy_monitor._health_thresholds = custom_thresholds
```

## 📈 **Metrics & Analytics**

### **Performance Metrics**
- **Total P&L** - Cumulative profit/loss
- **Daily P&L** - Today's profit/loss
- **Win Rate** - Percentage of profitable trades
- **Sharpe Ratio** - Risk-adjusted returns
- **Max Drawdown** - Maximum peak-to-trough decline

### **Risk Metrics**
- **Current Exposure** - Total position value
- **Risk Utilization** - Percentage of capital at risk
- **Largest Position** - Biggest single position
- **Concentration Risk** - Position diversification

### **Activity Metrics**
- **Total Orders** - All orders placed
- **Successful Orders** - Completed orders
- **Failed Orders** - Rejected/error orders
- **Active Positions** - Current open positions

### **System Metrics**
- **Execution Latency** - Order execution time
- **Error Count** - System errors
- **Last Signal Time** - Strategy activity
- **Uptime** - System availability

## 🚨 **Alert Types**

| Alert Type | Description | Default Threshold |
|------------|-------------|-------------------|
| `DAILY_LOSS_LIMIT` | Daily loss exceeds limit | -5% |
| `DRAWDOWN_LIMIT` | Max drawdown exceeded | -10% |
| `HIGH_RISK_EXPOSURE` | Risk exposure too high | 80% |
| `STRATEGY_OFFLINE` | Strategy not responding | 15 minutes |
| `POSITION_SIZE_VIOLATION` | Position too large | 20% |
| `EXECUTION_ERROR` | High error count | 10 errors |
| `PERFORMANCE_DEGRADATION` | Poor performance | Custom |
| `SYSTEM_ERROR` | System issues | Custom |

## 🔧 **Integration**

### **With Trading Engine**
```python
from app.monitoring import strategy_monitor, alert_manager

# In your trading engine
async def process_strategy_signal(strategy_id, signal):
    # Process the signal
    result = await execute_order(signal)
    
    # Update monitoring metrics
    metrics = strategy_monitor.get_strategy_metrics(strategy_id)
    if metrics:
        # Metrics are automatically updated by the monitor
        pass
```

### **With Database Engine**
```python
# The monitoring system automatically integrates with the database
# It reads from the same tables used by the trading engine:
# - strategies
# - orders
# - trades
# - positions
# - balances
```

### **With Frontend**
```python
from app.monitoring.dashboard import monitoring_dashboard

# API endpoint for dashboard data
@app.get("/api/monitoring/dashboard")
async def get_dashboard():
    return monitoring_dashboard.get_dashboard_data()

# API endpoint for strategy details
@app.get("/api/monitoring/strategy/{strategy_id}")
async def get_strategy_detail(strategy_id: str):
    return monitoring_dashboard.get_strategy_detail(strategy_id)
```

## 📝 **Logging**

The monitoring system provides comprehensive logging:

```
2024-01-01 10:00:00 - strategy_monitor - INFO - 🔍 Strategy Monitor started
2024-01-01 10:00:01 - alert_manager - INFO - 🚨 Alert Manager started
2024-01-01 10:00:02 - dashboard - INFO - 📊 Monitoring Dashboard started
2024-01-01 10:05:00 - strategy_monitor - WARNING - Strategy MyStrategy health: WARNING
2024-01-01 10:05:01 - alert_manager - WARNING - Alert triggered: High Risk Exposure: MyStrategy
```

**Log Files:**
- `monitoring.log` - Main monitoring log
- `alerts.log` - Alert-specific events
- `performance.log` - Performance metrics

## 🔒 **Security**

### **Alert Rule Security**
- Alert conditions use restricted `eval()` with no builtins
- Only safe mathematical and comparison operations allowed
- No file system or network access from alert rules

### **Notification Security**
- Webhook URLs validated before sending
- Email templates sanitized
- SMS content length limits enforced

## 🚀 **Performance**

### **Monitoring Intervals**
- **Strategy Metrics**: Updated every 30 seconds
- **Health Checks**: Every 60 seconds
- **Alert Processing**: Every 30 seconds
- **Dashboard Data**: Every 30 seconds
- **Performance Analytics**: Every 5 minutes

### **Resource Usage**
- **Memory**: ~50MB for 100 strategies
- **CPU**: <5% on modern hardware
- **Database**: Minimal impact (read-only queries)

## 🧪 **Testing**

```bash
# Run monitoring system tests
python -m pytest app/monitoring/tests/

# Test individual components
python -m pytest app/monitoring/tests/test_strategy_monitor.py
python -m pytest app/monitoring/tests/test_alert_manager.py
python -m pytest app/monitoring/tests/test_dashboard.py
```

## 📚 **Examples**

### **Basic Monitoring Setup**
```python
import asyncio
from app.monitoring.main import MonitoringService

async def main():
    service = MonitoringService()
    await service.start()

if __name__ == "__main__":
    asyncio.run(main())
```

### **Custom Alert Rule**
```python
from app.monitoring.alert_manager import AlertRule, AlertType, AlertSeverity

# Alert when strategy hasn't traded in 2 hours
no_activity_rule = AlertRule(
    id="no_activity_2h",
    name="No Trading Activity",
    alert_type=AlertType.STRATEGY_OFFLINE,
    severity=AlertSeverity.MEDIUM,
    condition="(datetime.utcnow() - metrics.last_order_time).total_seconds() > 7200",
    threshold=7200,  # 2 hours in seconds
    cooldown_minutes=60
)

alert_manager.add_alert_rule(no_activity_rule)
```

### **Performance Analysis**
```python
from app.monitoring.dashboard import monitoring_dashboard

# Get performance data
dashboard_data = monitoring_dashboard.get_dashboard_data()
performance = dashboard_data['performance']

print(f"Total P&L: ₹{performance['total_pnl']:,.2f}")
print(f"Win Rate: {performance['win_rate']:.1%}")
print(f"Risk Utilization: {performance['exposure_ratio']:.1%}")
```

## 🆘 **Troubleshooting**

### **Common Issues**

**1. No Strategies Monitored**
```bash
# Check if strategies are active in database
python -c "from app.database import SessionLocal; from app.models.base import Strategy; db = SessionLocal(); print(db.query(Strategy).filter(Strategy.status == 'ACTIVE').count())"
```

**2. Alerts Not Triggering**
```bash
# Check alert rules
python -m app.monitoring.cli dashboard --json | jq '.alerts.alert_statistics'
```

**3. High Memory Usage**
```bash
# Reduce monitoring level
export MONITORING_LEVEL=BASIC
python -m app.monitoring.main
```

### **Debug Mode**
```bash
# Enable debug logging
export LOG_LEVEL=DEBUG
python -m app.monitoring.main
```

## 🔄 **Updates & Maintenance**

### **Regular Maintenance**
- Review alert thresholds monthly
- Clean up old alert history (automated)
- Monitor system resource usage
- Update notification channels as needed

### **Performance Tuning**
- Adjust monitoring intervals based on load
- Optimize database queries for large datasets
- Scale notification systems for high alert volumes

## 📞 **Support**

For issues or questions:
1. Check the logs in `monitoring.log`
2. Use the CLI for quick diagnostics
3. Review the dashboard for system health
4. Check database connectivity and permissions

---

**🎯 The Strategy Monitoring System provides enterprise-grade monitoring for your algorithmic trading strategies with real-time health tracking, intelligent alerting, and comprehensive analytics!** 