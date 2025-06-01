#!/usr/bin/env python3
"""
Main Monitoring Service - Comprehensive strategy monitoring system

This service starts and coordinates all monitoring components:
- Strategy Monitor: Real-time strategy health and performance tracking
- Alert Manager: Intelligent alerting with configurable rules
- Dashboard: Unified monitoring interface

Usage:
    python -m app.monitoring.main
"""

import asyncio
import logging
import signal
import sys
from datetime import datetime
from typing import Dict, Any

from app.monitoring.strategy_monitor import strategy_monitor
from app.monitoring.alert_manager import alert_manager
from app.monitoring.dashboard import monitoring_dashboard

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('monitoring.log')
    ]
)

logger = logging.getLogger(__name__)

class MonitoringService:
    """
    Main monitoring service that coordinates all monitoring components
    """
    
    def __init__(self):
        self.running = False
        self.start_time = None
        self.components = {
            'strategy_monitor': strategy_monitor,
            'alert_manager': alert_manager,
            'dashboard': monitoring_dashboard
        }
        
        # Setup signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        logger.info(f"Received signal {signum}, initiating graceful shutdown...")
        self.running = False
    
    async def start(self):
        """Start the monitoring service"""
        self.running = True
        self.start_time = datetime.utcnow()
        
        logger.info("🚀 Starting Comprehensive Strategy Monitoring Service")
        logger.info("=" * 60)
        
        try:
            # Start all monitoring components concurrently
            await asyncio.gather(
                self._start_strategy_monitor(),
                self._start_alert_manager(),
                self._start_dashboard(),
                self._start_health_checker(),
                return_exceptions=True
            )
        except Exception as e:
            logger.error(f"Error in monitoring service: {e}")
        finally:
            await self._shutdown()
    
    async def _start_strategy_monitor(self):
        """Start the strategy monitor"""
        try:
            logger.info("🔍 Starting Strategy Monitor...")
            await strategy_monitor.start_monitoring()
        except Exception as e:
            logger.error(f"Strategy Monitor error: {e}")
            raise
    
    async def _start_alert_manager(self):
        """Start the alert manager"""
        try:
            logger.info("🚨 Starting Alert Manager...")
            await alert_manager.start_alert_manager()
        except Exception as e:
            logger.error(f"Alert Manager error: {e}")
            raise
    
    async def _start_dashboard(self):
        """Start the dashboard"""
        try:
            logger.info("📊 Starting Monitoring Dashboard...")
            await monitoring_dashboard.start_dashboard()
        except Exception as e:
            logger.error(f"Dashboard error: {e}")
            raise
    
    async def _start_health_checker(self):
        """Start the health checker for the monitoring service itself"""
        logger.info("🏥 Starting Monitoring Health Checker...")
        
        while self.running:
            try:
                await self._check_monitoring_health()
                await asyncio.sleep(300)  # Check every 5 minutes
            except Exception as e:
                logger.error(f"Health checker error: {e}")
                await asyncio.sleep(300)
    
    async def _check_monitoring_health(self):
        """Check health of monitoring components"""
        health_status = {}
        
        # Check strategy monitor
        try:
            metrics_count = len(strategy_monitor.get_all_metrics())
            health_status['strategy_monitor'] = {
                'status': 'HEALTHY',
                'monitored_strategies': metrics_count,
                'last_check': datetime.utcnow().isoformat()
            }
        except Exception as e:
            health_status['strategy_monitor'] = {
                'status': 'ERROR',
                'error': str(e),
                'last_check': datetime.utcnow().isoformat()
            }
        
        # Check alert manager
        try:
            active_alerts = len(alert_manager.get_active_alerts())
            alert_rules = len(alert_manager._alert_rules)
            health_status['alert_manager'] = {
                'status': 'HEALTHY',
                'active_alerts': active_alerts,
                'alert_rules': alert_rules,
                'last_check': datetime.utcnow().isoformat()
            }
        except Exception as e:
            health_status['alert_manager'] = {
                'status': 'ERROR',
                'error': str(e),
                'last_check': datetime.utcnow().isoformat()
            }
        
        # Check dashboard
        try:
            dashboard_data = monitoring_dashboard.get_dashboard_data()
            health_status['dashboard'] = {
                'status': 'HEALTHY',
                'last_update': dashboard_data.get('last_update'),
                'last_check': datetime.utcnow().isoformat()
            }
        except Exception as e:
            health_status['dashboard'] = {
                'status': 'ERROR',
                'error': str(e),
                'last_check': datetime.utcnow().isoformat()
            }
        
        # Log health summary
        healthy_components = sum(1 for status in health_status.values() if status['status'] == 'HEALTHY')
        total_components = len(health_status)
        
        if healthy_components == total_components:
            logger.info(f"✅ All monitoring components healthy ({healthy_components}/{total_components})")
        else:
            logger.warning(f"⚠️ Monitoring health: {healthy_components}/{total_components} components healthy")
            for component, status in health_status.items():
                if status['status'] != 'HEALTHY':
                    logger.error(f"❌ {component}: {status.get('error', 'Unknown error')}")
    
    async def _shutdown(self):
        """Graceful shutdown of all components"""
        logger.info("🛑 Shutting down monitoring service...")
        
        # Stop all components
        shutdown_tasks = []
        
        if hasattr(strategy_monitor, 'stop_monitoring'):
            shutdown_tasks.append(strategy_monitor.stop_monitoring())
        
        if hasattr(alert_manager, 'stop_alert_manager'):
            shutdown_tasks.append(alert_manager.stop_alert_manager())
        
        # Wait for all components to shutdown
        if shutdown_tasks:
            await asyncio.gather(*shutdown_tasks, return_exceptions=True)
        
        # Calculate uptime
        if self.start_time:
            uptime = datetime.utcnow() - self.start_time
            logger.info(f"📊 Service uptime: {uptime}")
        
        logger.info("✅ Monitoring service shutdown complete")
    
    def get_service_status(self) -> Dict[str, Any]:
        """Get current service status"""
        uptime = datetime.utcnow() - self.start_time if self.start_time else None
        
        return {
            'running': self.running,
            'start_time': self.start_time.isoformat() if self.start_time else None,
            'uptime_seconds': uptime.total_seconds() if uptime else None,
            'components': {
                name: {
                    'running': hasattr(component, 'running') and getattr(component, 'running', False)
                }
                for name, component in self.components.items()
            }
        }

async def main():
    """Main entry point"""
    print("🔍 Comprehensive Strategy Monitoring System")
    print("=" * 50)
    print("Starting monitoring service...")
    print()
    
    # Create and start the monitoring service
    service = MonitoringService()
    
    try:
        await service.start()
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt")
    except Exception as e:
        logger.error(f"Service error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    # Run the monitoring service
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Monitoring service stopped")
        sys.exit(0) 