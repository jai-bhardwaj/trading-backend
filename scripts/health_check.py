#!/usr/bin/env python3
"""
Comprehensive Trading System Health Check
Tests all critical components and their integration
"""

import asyncio
import logging
import sys
from pathlib import Path
from datetime import datetime, timedelta, timezone
import redis

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from app.database import DatabaseManager
from app.models.base import User, Strategy, Order, StrategyStatus, OrderStatus
from app.core.instrument_manager import get_instrument_manager
from sqlalchemy import select, text

# Configure logging
logging.basicConfig(level=logging.WARNING)  # Reduce noise

class HealthChecker:
    """Comprehensive system health checker"""
    
    def __init__(self):
        self.results = []
        self.db_manager = None
        
    async def run_all_checks(self):
        """Run all health checks"""
        print("🏥 TRADING SYSTEM HEALTH CHECK")
        print("=" * 50)
        
        # Database checks
        await self.check_database()
        await self.check_database_tables()
        await self.check_users()
        await self.check_strategies()
        await self.check_orders()
        
        # Component checks
        await self.check_redis()
        await self.check_instrument_manager()
        
        # Performance checks
        await self.check_recent_activity()
        await self.check_system_performance()
        
        # Summary
        self.print_summary()
    
    async def check_database(self):
        """Check database connectivity"""
        try:
            self.db_manager = DatabaseManager()
            await self.db_manager.initialize()
            
            # Test basic query
            async with self.db_manager.get_session() as db:
                result = await db.execute(text("SELECT 1"))
                result.scalar()
            
            self.log_success("Database", "Connected and responsive")
        except Exception as e:
            self.log_error("Database", f"Connection failed: {e}")
    
    async def check_database_tables(self):
        """Check if all required tables exist"""
        required_tables = ["users", "strategies", "orders", "broker_configs", "risk_profiles"]
        
        try:
            async with self.db_manager.get_session() as db:
                missing_tables = []
                for table in required_tables:
                    try:
                        result = await db.execute(text(f"SELECT COUNT(*) FROM {table}"))
                        result.scalar()
                    except Exception:
                        missing_tables.append(table)
                
                if missing_tables:
                    self.log_warning("Database Tables", f"Missing tables: {missing_tables}")
                else:
                    self.log_success("Database Tables", "All required tables exist")
        except Exception as e:
            self.log_error("Database Tables", f"Check failed: {e}")
    
    async def check_users(self):
        """Check user accounts"""
        try:
            async with self.db_manager.get_session() as db:
                result = await db.execute(select(User))
                users = result.scalars().all()
                
                if len(users) == 0:
                    self.log_warning("Users", "No users found")
                else:
                    demo_users = [u for u in users if u.username == "demo_trader"]
                    if demo_users:
                        self.log_success("Users", f"{len(users)} users found (demo account ready)")
                    else:
                        self.log_info("Users", f"{len(users)} users found")
        except Exception as e:
            self.log_error("Users", f"Check failed: {e}")
    
    async def check_strategies(self):
        """Check strategy status"""
        try:
            async with self.db_manager.get_session() as db:
                result = await db.execute(select(Strategy))
                strategies = result.scalars().all()
                
                active_strategies = [s for s in strategies if s.status == StrategyStatus.ACTIVE]
                
                if len(strategies) == 0:
                    self.log_warning("Strategies", "No strategies found")
                elif len(active_strategies) == 0:
                    self.log_warning("Strategies", f"{len(strategies)} strategies found but none active")
                else:
                    self.log_success("Strategies", f"{len(active_strategies)} active strategies of {len(strategies)} total")
                    
                    # Check strategy symbols
                    for strategy in active_strategies:
                        symbol_count = len(strategy.symbols) if strategy.symbols else 0
                        if symbol_count == 0:
                            self.log_warning("Strategy Symbols", f"{strategy.name} has no symbols assigned")
                        else:
                            self.log_info("Strategy Symbols", f"{strategy.name}: {symbol_count} symbols")
        except Exception as e:
            self.log_error("Strategies", f"Check failed: {e}")
    
    async def check_orders(self):
        """Check order processing"""
        try:
            async with self.db_manager.get_session() as db:
                # Check recent orders (use naive datetime to match database)
                yesterday = datetime.utcnow() - timedelta(days=1)
                result = await db.execute(
                    select(Order).where(Order.created_at >= yesterday)
                )
                recent_orders = result.scalars().all()
                
                if len(recent_orders) == 0:
                    self.log_info("Orders", "No recent orders (last 24h)")
                else:
                    completed_orders = [o for o in recent_orders if o.status == OrderStatus.COMPLETE]
                    failed_orders = [o for o in recent_orders if o.status in [OrderStatus.ERROR, OrderStatus.REJECTED, OrderStatus.CANCELLED]]
                    pending_orders = [o for o in recent_orders if o.status in [OrderStatus.PENDING, OrderStatus.QUEUED]]
                    
                    success_rate = (len(completed_orders) / len(recent_orders)) * 100 if recent_orders else 0
                    
                    if success_rate >= 95:
                        self.log_success("Orders", f"{len(recent_orders)} orders, {success_rate:.1f}% success rate")
                    elif success_rate >= 80:
                        self.log_warning("Orders", f"{len(recent_orders)} orders, {success_rate:.1f}% success rate")
                    else:
                        self.log_error("Orders", f"{len(recent_orders)} orders, {success_rate:.1f}% success rate")
                    
                    if pending_orders:
                        self.log_info("Order Queue", f"{len(pending_orders)} orders pending/queued")
                    
                    if failed_orders:
                        self.log_warning("Order Failures", f"{len(failed_orders)} failed orders")
        except Exception as e:
            self.log_error("Orders", f"Check failed: {e}")
    
    async def check_redis(self):
        """Check Redis connectivity"""
        try:
            r = redis.Redis(host='localhost', port=6379, decode_responses=True)
            r.ping()
            
            # Check queue keys
            queue_keys = r.keys("trading:*")
            if queue_keys:
                self.log_success("Redis", f"Connected, {len(queue_keys)} queue keys found")
            else:
                self.log_info("Redis", "Connected, no queue data")
        except Exception as e:
            self.log_error("Redis", f"Connection failed: {e}")
    
    async def check_instrument_manager(self):
        """Check instrument manager"""
        try:
            instrument_manager = await get_instrument_manager(self.db_manager)
            status = instrument_manager.get_status()
            
            total_instruments = status.get('total_instruments', 0)
            if total_instruments == 0:
                self.log_warning("Instrument Manager", "No instruments loaded")
            else:
                equity_count = status.get('equity_count', 0)
                derivatives_count = status.get('derivatives_count', 0)
                auth_status = status.get('auth_status', 'unknown')
                
                self.log_success("Instrument Manager", 
                               f"{total_instruments} instruments ({equity_count} equity, {derivatives_count} derivatives) - {auth_status}")
            
            await instrument_manager.stop()
        except Exception as e:
            self.log_error("Instrument Manager", f"Check failed: {e}")
    
    async def check_recent_activity(self):
        """Check recent system activity"""
        try:
            async with self.db_manager.get_session() as db:
                # Check recent strategy executions (use naive datetime to match database)
                last_hour = datetime.utcnow() - timedelta(hours=1)
                
                # Check recent orders as proxy for activity
                result = await db.execute(
                    select(Order).where(Order.created_at >= last_hour)
                )
                recent_activity = result.scalars().all()
                
                if len(recent_activity) == 0:
                    self.log_info("Recent Activity", "No activity in last hour")
                else:
                    self.log_success("Recent Activity", f"{len(recent_activity)} orders in last hour")
        except Exception as e:
            self.log_error("Recent Activity", f"Check failed: {e}")
    
    async def check_system_performance(self):
        """Check system performance metrics"""
        try:
            # Check if trading engine is running via PM2
            import subprocess
            result = subprocess.run(['pm2', 'jlist'], capture_output=True, text=True)
            
            if result.returncode == 0:
                import json
                processes = json.loads(result.stdout)
                trading_engine = next((p for p in processes if p['name'] == 'trading-engine'), None)
                
                if trading_engine:
                    status = trading_engine['pm2_env']['status']
                    memory = trading_engine['monit']['memory'] / 1024 / 1024  # MB
                    uptime = trading_engine['pm2_env']['pm_uptime']
                    
                    if status == 'online':
                        self.log_success("Trading Engine", f"Running (Memory: {memory:.1f}MB)")
                    else:
                        self.log_error("Trading Engine", f"Status: {status}")
                else:
                    self.log_warning("Trading Engine", "Not found in PM2")
            else:
                self.log_warning("System Performance", "PM2 not available")
        except Exception as e:
            self.log_info("System Performance", f"Check incomplete: {e}")
    
    def log_success(self, component, message):
        """Log successful check"""
        self.results.append(("SUCCESS", component, message))
        print(f"✅ {component}: {message}")
    
    def log_warning(self, component, message):
        """Log warning"""
        self.results.append(("WARNING", component, message))
        print(f"⚠️ {component}: {message}")
    
    def log_error(self, component, message):
        """Log error"""
        self.results.append(("ERROR", component, message))
        print(f"❌ {component}: {message}")
    
    def log_info(self, component, message):
        """Log info"""
        self.results.append(("INFO", component, message))
        print(f"ℹ️ {component}: {message}")
    
    def print_summary(self):
        """Print health check summary"""
        print("\n" + "=" * 50)
        print("📊 HEALTH CHECK SUMMARY")
        print("=" * 50)
        
        success_count = len([r for r in self.results if r[0] == "SUCCESS"])
        warning_count = len([r for r in self.results if r[0] == "WARNING"])
        error_count = len([r for r in self.results if r[0] == "ERROR"])
        info_count = len([r for r in self.results if r[0] == "INFO"])
        
        print(f"✅ Success: {success_count}")
        print(f"⚠️ Warnings: {warning_count}")
        print(f"❌ Errors: {error_count}")
        print(f"ℹ️ Info: {info_count}")
        
        if error_count == 0 and warning_count <= 2:
            print("\n🎉 System Health: EXCELLENT")
        elif error_count == 0:
            print("\n✅ System Health: GOOD")
        elif error_count <= 2:
            print("\n⚠️ System Health: FAIR (needs attention)")
        else:
            print("\n❌ System Health: POOR (immediate action required)")
        
        print("\n🔧 Quick Actions:")
        print("• View logs: pm2 logs trading-engine")
        print("• Restart engine: pm2 restart trading-engine")
        print("• Refresh instruments: python3 scripts/refresh_instruments.py")
        print("• Test orders: python3 scripts/test_trading.py")
    
    async def cleanup(self):
        """Cleanup resources"""
        if self.db_manager:
            await self.db_manager.close()

async def main():
    """Main health check function"""
    checker = HealthChecker()
    try:
        await checker.run_all_checks()
    finally:
        await checker.cleanup()

if __name__ == "__main__":
    asyncio.run(main()) 