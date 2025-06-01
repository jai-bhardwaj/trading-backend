#!/usr/bin/env python3
"""
Strategy Monitoring CLI - Command-line interface for monitoring strategies

This provides a simple CLI for viewing strategy status, alerts, and performance
without needing a web interface.
"""

import asyncio
import argparse
import json
import sys
from datetime import datetime
from typing import Dict, Any, List

from app.monitoring.strategy_monitor import strategy_monitor, StrategyHealth
from app.monitoring.alert_manager import alert_manager, AlertSeverity
from app.monitoring.dashboard import monitoring_dashboard

class MonitoringCLI:
    """Command-line interface for strategy monitoring"""
    
    def __init__(self):
        self.commands = {
            'status': self.show_status,
            'strategies': self.show_strategies,
            'alerts': self.show_alerts,
            'performance': self.show_performance,
            'dashboard': self.show_dashboard,
            'strategy': self.show_strategy_detail,
            'health': self.show_health_summary,
            'ack': self.acknowledge_alert,
            'resolve': self.resolve_alert
        }
    
    async def run(self, args):
        """Run the CLI command"""
        if args.command not in self.commands:
            print(f"Unknown command: {args.command}")
            print(f"Available commands: {', '.join(self.commands.keys())}")
            return
        
        await self.commands[args.command](args)
    
    async def show_status(self, args):
        """Show overall system status"""
        print("🔍 Strategy Monitoring System Status")
        print("=" * 50)
        
        # Get health summary
        health_summary = strategy_monitor.get_health_summary()
        performance_summary = strategy_monitor.get_performance_summary()
        alert_stats = alert_manager.get_alert_statistics()
        
        print(f"📊 Strategies: {health_summary.get('total_strategies', 0)}")
        print(f"✅ Healthy: {health_summary.get('health_distribution', {}).get('HEALTHY', 0)}")
        print(f"⚠️  Warning: {health_summary.get('health_distribution', {}).get('WARNING', 0)}")
        print(f"🚨 Critical: {health_summary.get('health_distribution', {}).get('CRITICAL', 0)}")
        print(f"💤 Offline: {health_summary.get('health_distribution', {}).get('OFFLINE', 0)}")
        print()
        print(f"💰 Total P&L: ₹{performance_summary.get('total_pnl', 0):,.2f}")
        print(f"📈 Daily P&L: ₹{performance_summary.get('daily_pnl', 0):,.2f}")
        print(f"🎯 Avg Win Rate: {performance_summary.get('average_win_rate', 0):.1%}")
        print()
        print(f"🚨 Active Alerts: {alert_stats.get('total_active_alerts', 0)}")
        print(f"🔴 Critical: {alert_stats.get('severity_distribution', {}).get('CRITICAL', 0)}")
        print(f"🟡 High: {alert_stats.get('severity_distribution', {}).get('HIGH', 0)}")
    
    async def show_strategies(self, args):
        """Show all strategies with their status"""
        print("📋 Strategy Overview")
        print("=" * 80)
        
        all_metrics = strategy_monitor.get_all_metrics()
        
        if not all_metrics:
            print("No strategies currently monitored.")
            return
        
        # Header
        print(f"{'Name':<20} {'Health':<10} {'P&L':<12} {'Daily P&L':<12} {'Win Rate':<10} {'Risk':<8}")
        print("-" * 80)
        
        for strategy_id, metrics in all_metrics.items():
            health_icon = self._get_health_icon(metrics.health_status)
            risk_pct = f"{metrics.risk_utilization:.1%}" if metrics.risk_utilization else "N/A"
            
            print(f"{metrics.strategy_name:<20} "
                  f"{health_icon} {metrics.health_status.value:<8} "
                  f"₹{metrics.total_pnl:>10,.0f} "
                  f"₹{metrics.daily_pnl:>10,.0f} "
                  f"{metrics.win_rate:>8.1%} "
                  f"{risk_pct:>7}")
    
    async def show_alerts(self, args):
        """Show active alerts"""
        print("🚨 Active Alerts")
        print("=" * 80)
        
        active_alerts = alert_manager.get_active_alerts()
        
        if not active_alerts:
            print("No active alerts.")
            return
        
        for alert in sorted(active_alerts, key=lambda x: (x.severity.value, x.created_at), reverse=True):
            severity_icon = self._get_severity_icon(alert.severity)
            time_ago = self._time_ago(alert.created_at)
            
            print(f"{severity_icon} {alert.severity.value:<8} | {alert.strategy_name:<20} | {time_ago}")
            print(f"   {alert.title}")
            print(f"   {alert.message}")
            print(f"   ID: {alert.id}")
            print()
    
    async def show_performance(self, args):
        """Show performance summary"""
        print("📈 Performance Summary")
        print("=" * 50)
        
        dashboard_data = monitoring_dashboard.get_dashboard_data()
        performance = dashboard_data.get('performance', {})
        
        print(f"💰 Total P&L: ₹{performance.get('total_pnl', 0):,.2f}")
        print(f"📊 Daily P&L: ₹{performance.get('daily_pnl', 0):,.2f}")
        print(f"📈 Total Trades: {performance.get('total_trades', 0):,}")
        print(f"🎯 Win Rate: {performance.get('win_rate', 0):.1%}")
        print(f"💼 Total Exposure: ₹{performance.get('total_exposure', 0):,.2f}")
        print(f"💳 Total Balance: ₹{performance.get('total_balance', 0):,.2f}")
        print(f"📊 Exposure Ratio: {performance.get('exposure_ratio', 0):.1%}")
        print(f"📍 Active Positions: {performance.get('active_positions', 0)}")
        
        # Performance by period
        by_period = performance.get('performance_by_period', {})
        if by_period:
            print("\n📅 Performance by Period:")
            for period, data in by_period.items():
                print(f"   {period.title()}: ₹{data.get('pnl', 0):,.2f} "
                      f"({data.get('trades', 0)} trades, {data.get('win_rate', 0):.1%} win rate)")
    
    async def show_dashboard(self, args):
        """Show full dashboard data"""
        print("📊 Complete Dashboard")
        print("=" * 50)
        
        dashboard_data = monitoring_dashboard.get_dashboard_data()
        
        if args.json:
            print(json.dumps(dashboard_data, indent=2, default=str))
        else:
            # Show overview
            overview = dashboard_data.get('overview', {})
            print("📋 Overview:")
            for key, value in overview.items():
                if key != 'system_status':
                    print(f"   {key.replace('_', ' ').title()}: {value}")
            print()
            
            # Show system health
            system = dashboard_data.get('system', {})
            health = system.get('system_health', {})
            print("🏥 System Health:")
            print(f"   Overall Status: {health.get('overall_status', 'UNKNOWN')}")
            components = health.get('components', {})
            for component, status in components.items():
                print(f"   {component.title()}: {status.get('status', 'UNKNOWN')}")
    
    async def show_strategy_detail(self, args):
        """Show detailed information for a specific strategy"""
        if not args.strategy_id:
            print("Please provide a strategy ID with --strategy-id")
            return
        
        detail = await monitoring_dashboard.get_strategy_detail(args.strategy_id)
        if not detail:
            print(f"Strategy {args.strategy_id} not found.")
            return
        
        metrics = detail['metrics']
        print(f"📊 Strategy Detail: {metrics['strategy_name']}")
        print("=" * 60)
        
        # Performance metrics
        perf = metrics['performance']
        print("📈 Performance:")
        print(f"   Total P&L: ₹{perf['total_pnl']:,.2f}")
        print(f"   Daily P&L: ₹{perf['daily_pnl']:,.2f}")
        print(f"   Win Rate: {perf['win_rate']:.1%}")
        print(f"   Max Drawdown: {perf['max_drawdown']:.1%}")
        print()
        
        # Activity metrics
        activity = metrics['activity']
        print("📊 Activity:")
        print(f"   Total Orders: {activity['total_orders']}")
        print(f"   Successful: {activity['successful_orders']}")
        print(f"   Failed: {activity['failed_orders']}")
        print(f"   Active Positions: {activity['active_positions']}")
        print()
        
        # Risk metrics
        risk = metrics['risk']
        print("⚠️ Risk:")
        print(f"   Current Exposure: ₹{risk['current_exposure']:,.2f}")
        print(f"   Risk Utilization: {risk['risk_utilization']:.1%}")
        print(f"   Largest Position: {risk['largest_position']:.1%}")
        print()
        
        # Risk analysis
        risk_analysis = detail['risk_analysis']
        print(f"🎯 Risk Score: {risk_analysis['risk_score']:.0f}/100")
        
        if risk_analysis['risk_factors']:
            print("⚠️ Risk Factors:")
            for factor in risk_analysis['risk_factors']:
                print(f"   • {factor}")
        
        if risk_analysis['recommendations']:
            print("💡 Recommendations:")
            for rec in risk_analysis['recommendations']:
                print(f"   • {rec}")
        
        # Active alerts
        alerts = detail['alerts']
        if alerts:
            print(f"\n🚨 Active Alerts ({len(alerts)}):")
            for alert in alerts:
                severity_icon = self._get_severity_icon_from_str(alert['severity'])
                print(f"   {severity_icon} {alert['title']}")
    
    async def show_health_summary(self, args):
        """Show health summary for all strategies"""
        print("🏥 Strategy Health Summary")
        print("=" * 60)
        
        all_metrics = strategy_monitor.get_all_metrics()
        
        # Group by health status
        by_health = {}
        for metrics in all_metrics.values():
            health = metrics.health_status
            if health not in by_health:
                by_health[health] = []
            by_health[health].append(metrics)
        
        for health_status in [StrategyHealth.CRITICAL, StrategyHealth.OFFLINE, 
                             StrategyHealth.WARNING, StrategyHealth.HEALTHY]:
            strategies = by_health.get(health_status, [])
            if strategies:
                icon = self._get_health_icon(health_status)
                print(f"\n{icon} {health_status.value} ({len(strategies)} strategies):")
                for metrics in strategies:
                    print(f"   • {metrics.strategy_name}")
                    if health_status in [StrategyHealth.CRITICAL, StrategyHealth.WARNING]:
                        # Show key metrics for problematic strategies
                        print(f"     Daily P&L: ₹{metrics.daily_pnl:,.2f}, "
                              f"Risk: {metrics.risk_utilization:.1%}, "
                              f"Drawdown: {metrics.max_drawdown:.1%}")
    
    async def acknowledge_alert(self, args):
        """Acknowledge an alert"""
        if not args.alert_id:
            print("Please provide an alert ID with --alert-id")
            return
        
        acknowledged_by = args.user or "CLI User"
        success = alert_manager.acknowledge_alert(args.alert_id, acknowledged_by)
        
        if success:
            print(f"✅ Alert {args.alert_id} acknowledged by {acknowledged_by}")
        else:
            print(f"❌ Failed to acknowledge alert {args.alert_id}")
    
    async def resolve_alert(self, args):
        """Resolve an alert"""
        if not args.alert_id:
            print("Please provide an alert ID with --alert-id")
            return
        
        success = alert_manager.resolve_alert(args.alert_id)
        
        if success:
            print(f"✅ Alert {args.alert_id} resolved")
        else:
            print(f"❌ Failed to resolve alert {args.alert_id}")
    
    def _get_health_icon(self, health: StrategyHealth) -> str:
        """Get icon for health status"""
        icons = {
            StrategyHealth.HEALTHY: "✅",
            StrategyHealth.WARNING: "⚠️",
            StrategyHealth.CRITICAL: "🚨",
            StrategyHealth.OFFLINE: "💤"
        }
        return icons.get(health, "❓")
    
    def _get_severity_icon(self, severity: AlertSeverity) -> str:
        """Get icon for alert severity"""
        icons = {
            AlertSeverity.LOW: "🔵",
            AlertSeverity.MEDIUM: "🟡",
            AlertSeverity.HIGH: "🟠",
            AlertSeverity.CRITICAL: "🔴"
        }
        return icons.get(severity, "❓")
    
    def _get_severity_icon_from_str(self, severity_str: str) -> str:
        """Get icon for alert severity from string"""
        icons = {
            "LOW": "🔵",
            "MEDIUM": "🟡",
            "HIGH": "🟠",
            "CRITICAL": "🔴"
        }
        return icons.get(severity_str, "❓")
    
    def _time_ago(self, timestamp: datetime) -> str:
        """Get human-readable time ago"""
        now = datetime.utcnow()
        diff = now - timestamp
        
        if diff.days > 0:
            return f"{diff.days}d ago"
        elif diff.seconds > 3600:
            hours = diff.seconds // 3600
            return f"{hours}h ago"
        elif diff.seconds > 60:
            minutes = diff.seconds // 60
            return f"{minutes}m ago"
        else:
            return "just now"

def main():
    """Main CLI entry point"""
    parser = argparse.ArgumentParser(description="Strategy Monitoring CLI")
    parser.add_argument('command', choices=[
        'status', 'strategies', 'alerts', 'performance', 'dashboard', 
        'strategy', 'health', 'ack', 'resolve'
    ], help='Command to execute')
    
    # Optional arguments
    parser.add_argument('--strategy-id', help='Strategy ID for detailed view')
    parser.add_argument('--alert-id', help='Alert ID for acknowledgment/resolution')
    parser.add_argument('--user', help='User name for alert acknowledgment')
    parser.add_argument('--json', action='store_true', help='Output in JSON format')
    
    args = parser.parse_args()
    
    # Run the CLI
    cli = MonitoringCLI()
    
    try:
        asyncio.run(cli.run(args))
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")
        sys.exit(0)
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 