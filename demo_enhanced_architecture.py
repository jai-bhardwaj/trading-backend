#!/usr/bin/env python3
"""
Enhanced Trading Engine Architecture Demo

This demonstration shows:
1. Database-controlled strategy management
2. Independent strategy execution
3. Real-time monitoring and control
4. API-driven strategy operations
"""

import asyncio
import json
import uuid
from datetime import datetime
import aiohttp
import logging

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class EnhancedArchitectureDemo:
    """Complete demonstration of the enhanced trading engine"""
    
    def __init__(self):
        self.api_base_url = "http://localhost:8000/api/strategies"
        
    async def demonstrate_complete_architecture(self):
        """Demonstrate the complete enhanced architecture"""
        
        print("🏗️  Enhanced Trading Engine Architecture Demo")
        print("=" * 70)
        
        try:
            # Step 1: Create strategy configurations
            await self.demo_strategy_creation()
            
            # Step 2: Show database control
            await self.demo_database_control()
            
            # Step 3: Demonstrate independent execution
            await self.demo_independent_execution()
            
            # Step 4: Show real-time monitoring
            await self.demo_real_time_monitoring()
            
            # Step 5: Show API management
            await self.demo_api_management()
            
            print("\n✅ Complete architecture demonstration finished!")
            
        except Exception as e:
            print(f"❌ Demo failed: {e}")
            import traceback
            traceback.print_exc()
    
    async def demo_strategy_creation(self):
        """Demonstrate creating strategies via database/API"""
        
        print("\n📊 Step 1: Strategy Creation via Database Control")
        print("-" * 50)
        
        # Sample strategy configurations
        strategies_to_create = [
            {
                "name": "BankNifty_Momentum_1",
                "class_name": "SampleMomentumStrategy",
                "module_path": "app.strategies.sample_momentum_strategy",
                "config": {
                    "target_symbols": ["BANKNIFTY", "BANK"],
                    "momentum_period": 10,
                    "entry_threshold": 0.8,
                    "stop_loss_pct": 1.5,
                    "take_profit_pct": 2.5,
                    "max_positions": 3,
                    "position_size": 50000,
                    "execution_interval": 2,
                    "broker_config": {
                        "api_key": "demo_key",
                        "client_id": "demo_client"
                    }
                },
                "auto_start": True
            },
            {
                "name": "Nifty_Swing_1",
                "class_name": "SampleMomentumStrategy", 
                "module_path": "app.strategies.sample_momentum_strategy",
                "config": {
                    "target_symbols": ["NIFTY", "IT"],
                    "momentum_period": 15,
                    "entry_threshold": 1.2,
                    "stop_loss_pct": 2.0,
                    "take_profit_pct": 4.0,
                    "max_positions": 2,
                    "position_size": 75000,
                    "execution_interval": 5
                },
                "auto_start": False
            },
            {
                "name": "Options_Scalper_1",
                "class_name": "SampleMomentumStrategy",
                "module_path": "app.strategies.sample_momentum_strategy", 
                "config": {
                    "target_symbols": ["BANKNIFTY"],
                    "momentum_period": 5,
                    "entry_threshold": 0.3,
                    "stop_loss_pct": 1.0,
                    "take_profit_pct": 1.5,
                    "max_positions": 5,
                    "position_size": 25000,
                    "execution_interval": 1
                },
                "auto_start": True
            }
        ]
        
        print(f"🔧 Creating {len(strategies_to_create)} strategy configurations...")
        
        for i, strategy_config in enumerate(strategies_to_create, 1):
            print(f"\n📋 Strategy {i}: {strategy_config['name']}")
            print(f"   Type: {strategy_config['class_name']}")
            print(f"   Symbols: {strategy_config['config']['target_symbols']}")
            print(f"   Auto-start: {strategy_config['auto_start']}")
            print(f"   Position size: ₹{strategy_config['config']['position_size']:,}")
            
            # Simulate database insertion
            strategy_id = str(uuid.uuid4())
            print(f"   ✅ Created with ID: {strategy_id}")
            
            # Simulate auto-start command if enabled
            if strategy_config['auto_start']:
                print(f"   🚀 Auto-start command queued")
    
    async def demo_database_control(self):
        """Demonstrate database-driven control"""
        
        print("\n🗄️  Step 2: Database Control Demonstration")
        print("-" * 50)
        
        print("💾 Database Tables Structure:")
        print("""
        strategy_configs:
        ├── id (UUID)
        ├── name (VARCHAR)
        ├── class_name (VARCHAR)
        ├── module_path (VARCHAR)
        ├── config_json (JSONB)
        ├── status (ENUM: active, stopped, error)
        ├── auto_start (BOOLEAN)
        └── timestamps
        
        strategy_commands:
        ├── id (UUID)
        ├── strategy_id (UUID → strategy_configs.id)
        ├── command (ENUM: start, stop, restart, update)
        ├── parameters (JSONB)
        ├── status (ENUM: pending, executed, failed)
        └── timestamps
        
        strategy_metrics:
        ├── strategy_id (UUID → strategy_configs.id)
        ├── timestamp (TIMESTAMP)
        ├── pnl (DECIMAL)
        ├── positions_count (INTEGER)
        ├── orders_count (INTEGER)
        ├── success_rate (DECIMAL)
        └── metrics_json (JSONB)
        """)
        
        print("\n🔄 Command Flow:")
        print("1. API/Admin inserts command → strategy_commands table")
        print("2. Engine Manager polls database every second")
        print("3. Manager executes pending commands")
        print("4. Command status updated: pending → executed/failed")
        print("5. Strategy processes receive commands via Redis")
        
        # Simulate command examples
        sample_commands = [
            {"strategy": "BankNifty_Momentum_1", "command": "start", "reason": "Market opening"},
            {"strategy": "Nifty_Swing_1", "command": "pause", "reason": "High volatility"},
            {"strategy": "Options_Scalper_1", "command": "update", "reason": "Parameter tuning"},
            {"strategy": "BankNifty_Momentum_1", "command": "stop", "reason": "End of day"}
        ]
        
        print(f"\n📤 Sample Commands Queue:")
        for cmd in sample_commands:
            timestamp = datetime.now().strftime("%H:%M:%S")
            print(f"   {timestamp} | {cmd['command'].upper():8} | {cmd['strategy']} | {cmd['reason']}")
    
    async def demo_independent_execution(self):
        """Demonstrate independent strategy execution"""
        
        print("\n🔄 Step 3: Independent Strategy Execution")
        print("-" * 50)
        
        print("🏃 Strategy Process Management:")
        print("""
        Engine Manager spawns independent processes:
        
        ┌─────────────────────────────────────────────────────────┐
        │  Engine Manager (PID: 1001)                            │
        │  ├── Monitors all strategy processes                   │
        │  ├── Handles start/stop commands                       │
        │  └── Reports health metrics                            │
        └─────────────────────────────────────────────────────────┘
                               │
                               ├─ Strategy A (PID: 1002) 🟢 Running
                               ├─ Strategy B (PID: 1003) 🟡 Paused  
                               └─ Strategy C (PID: 1004) 🟢 Running
        """)
        
        # Simulate process status
        strategies_status = [
            {
                "name": "BankNifty_Momentum_1",
                "pid": 1002,
                "status": "running",
                "cpu_percent": 2.3,
                "memory_mb": 45.2,
                "uptime": "02:15:30",
                "pnl": 2500.75,
                "positions": 2
            },
            {
                "name": "Nifty_Swing_1", 
                "pid": 1003,
                "status": "paused",
                "cpu_percent": 0.1,
                "memory_mb": 38.7,
                "uptime": "01:45:22",
                "pnl": -450.25,
                "positions": 1
            },
            {
                "name": "Options_Scalper_1",
                "pid": 1004,
                "status": "running",
                "cpu_percent": 5.8,
                "memory_mb": 52.1,
                "uptime": "00:30:45",
                "pnl": 1250.50,
                "positions": 3
            }
        ]
        
        print("\n📊 Live Process Status:")
        print(f"{'Strategy':<20} {'PID':<6} {'Status':<8} {'CPU%':<6} {'RAM(MB)':<8} {'PnL':<10} {'Pos':<4}")
        print("-" * 70)
        
        for strategy in strategies_status:
            status_icon = {"running": "🟢", "paused": "🟡", "stopped": "🔴"}.get(strategy['status'], "⚪")
            pnl_color = "+" if strategy['pnl'] > 0 else ""
            
            print(f"{strategy['name']:<20} {strategy['pid']:<6} "
                  f"{status_icon} {strategy['status']:<6} {strategy['cpu_percent']:<6} "
                  f"{strategy['memory_mb']:<8} {pnl_color}{strategy['pnl']:<10.2f} {strategy['positions']:<4}")
        
        print(f"\n🔄 Process Isolation Benefits:")
        print("   ✅ One strategy crash doesn't affect others")
        print("   ✅ Independent resource usage")
        print("   ✅ Zero-downtime start/stop")
        print("   ✅ Horizontal scaling possible")
        print("   ✅ Easy debugging and monitoring")
    
    async def demo_real_time_monitoring(self):
        """Demonstrate real-time monitoring capabilities"""
        
        print("\n📈 Step 4: Real-Time Monitoring")
        print("-" * 50)
        
        print("📡 Redis Pub/Sub Channels:")
        print("""
        strategy:status:{strategy_id}    → Status updates
        strategy:metrics:{strategy_id}   → Performance metrics
        strategy:health                  → Health monitoring
        strategy:commands:{strategy_id}  → Command delivery
        """)
        
        # Simulate real-time metrics
        print("\n📊 Live Strategy Metrics (Last 5 minutes):")
        
        sample_metrics = [
            {
                "timestamp": "14:25:30",
                "strategy": "BankNifty_Momentum_1",
                "event": "ORDER_FILLED",
                "details": "BUY BANKBARODA x100 @ 245.50"
            },
            {
                "timestamp": "14:25:45", 
                "strategy": "Options_Scalper_1",
                "event": "SIGNAL_GENERATED",
                "details": "Bullish momentum: BANKNIFTY +1.2%"
            },
            {
                "timestamp": "14:26:10",
                "strategy": "BankNifty_Momentum_1", 
                "event": "POSITION_OPENED",
                "details": "BANKBARODA: 100 shares @ ₹245.50"
            },
            {
                "timestamp": "14:26:25",
                "strategy": "Nifty_Swing_1",
                "event": "STATUS_CHANGE", 
                "details": "PAUSED → RUNNING"
            },
            {
                "timestamp": "14:26:40",
                "strategy": "Options_Scalper_1",
                "event": "STOP_LOSS_HIT",
                "details": "BANKNIFTY25600CE: -₹1,250"
            }
        ]
        
        for metric in sample_metrics:
            event_icon = {
                "ORDER_FILLED": "📈",
                "SIGNAL_GENERATED": "🎯", 
                "POSITION_OPENED": "📍",
                "STATUS_CHANGE": "🔄",
                "STOP_LOSS_HIT": "🛑"
            }.get(metric['event'], "📊")
            
            print(f"{metric['timestamp']} | {event_icon} {metric['strategy']} | {metric['details']}")
        
        print(f"\n📋 System Overview:")
        print(f"   🟢 Active Strategies: 2")
        print(f"   🟡 Paused Strategies: 1") 
        print(f"   📈 Total PnL: +₹3,301.00")
        print(f"   📍 Open Positions: 6")
        print(f"   📊 Orders Today: 47")
        print(f"   ⚡ Avg Response Time: 15ms")
    
    async def demo_api_management(self):
        """Demonstrate API-driven management"""
        
        print("\n🌐 Step 5: API Management Interface")
        print("-" * 50)
        
        print("🔌 RESTful API Endpoints:")
        api_endpoints = [
            ("POST", "/api/strategies", "Create new strategy"),
            ("GET", "/api/strategies", "List all strategies"),
            ("GET", "/api/strategies/{id}", "Get strategy details"),
            ("PUT", "/api/strategies/{id}", "Update strategy config"),
            ("POST", "/api/strategies/{id}/commands", "Send command (start/stop/etc)"),
            ("GET", "/api/strategies/{id}/status", "Get strategy status"),
            ("GET", "/api/strategies/{id}/metrics", "Get performance metrics"),
            ("DELETE", "/api/strategies/{id}", "Delete strategy"),
            ("GET", "/api/strategies/overview", "System overview")
        ]
        
        for method, endpoint, description in api_endpoints:
            method_color = {"GET": "🟢", "POST": "🔵", "PUT": "🟡", "DELETE": "🔴"}.get(method, "⚪")
            print(f"  {method_color} {method:<6} {endpoint:<35} {description}")
        
        print(f"\n💻 Sample API Usage:")
        
        # Create strategy example
        create_payload = {
            "name": "NewMomentumStrategy",
            "class_name": "SampleMomentumStrategy",
            "module_path": "app.strategies.sample_momentum_strategy",
            "config": {
                "target_symbols": ["NIFTY"],
                "momentum_period": 12,
                "entry_threshold": 1.0,
                "max_positions": 2
            },
            "auto_start": True
        }
        
        print(f"\n1️⃣  Create Strategy:")
        print(f"   POST /api/strategies")
        print(f"   {json.dumps(create_payload, indent=6)}")
        
        # Command example
        command_payload = {
            "command": "start",
            "parameters": {"reason": "Market conditions favorable"}
        }
        
        print(f"\n2️⃣  Send Command:")
        print(f"   POST /api/strategies/{{strategy_id}}/commands")
        print(f"   {json.dumps(command_payload, indent=6)}")
        
        # Update config example
        update_payload = {
            "config": {
                "entry_threshold": 1.5,
                "stop_loss_pct": 1.8
            }
        }
        
        print(f"\n3️⃣  Update Configuration:")
        print(f"   PUT /api/strategies/{{strategy_id}}")
        print(f"   {json.dumps(update_payload, indent=6)}")
        
        print(f"\n🎛️  Management Benefits:")
        print("   ✅ Web dashboard control")
        print("   ✅ Mobile app integration")
        print("   ✅ Third-party tool connectivity") 
        print("   ✅ Automated monitoring systems")
        print("   ✅ Real-time configuration updates")
        print("   ✅ Historical performance analysis")
    
    async def demo_workflow_example(self):
        """Show a complete workflow example"""
        
        print("\n🔄 Complete Workflow Example")
        print("-" * 50)
        
        workflow_steps = [
            ("09:00", "🌅", "Market Opens", "Auto-start configured strategies"),
            ("09:05", "📊", "Data Flow", "Strategies receive live market data"),
            ("09:10", "🎯", "Signal Generated", "BankNifty momentum strategy detects opportunity"),
            ("09:11", "📈", "Order Placed", "BUY BANKBARODA 100 shares @ ₹245.50"),
            ("09:12", "✅", "Order Filled", "Position opened: +₹500 unrealized PnL"),
            ("10:30", "⚙️", "Config Update", "Admin updates stop-loss via API"),
            ("11:45", "🛑", "Stop Loss", "Position closed: -₹300 realized PnL"),
            ("14:20", "🔄", "Strategy Restart", "System automatically restarts crashed strategy"),
            ("15:25", "📉", "Market Close", "All positions closed, strategies paused"),
            ("15:30", "📋", "Daily Report", "Performance metrics saved to database")
        ]
        
        print(f"📅 Daily Trading Workflow:")
        for time, icon, event, description in workflow_steps:
            print(f"   {time} | {icon} {event:<15} | {description}")
        
        print(f"\n🎯 Architecture Benefits Realized:")
        print("   🚀 Zero downtime operations")
        print("   📊 Real-time performance tracking")
        print("   🔧 Hot configuration updates")
        print("   🛡️  Fault isolation and recovery")
        print("   📈 Horizontal scalability")
        print("   🎛️  Centralized control with distributed execution")

async def main():
    """Run the complete architecture demonstration"""
    demo = EnhancedArchitectureDemo()
    await demo.demonstrate_complete_architecture()

if __name__ == "__main__":
    asyncio.run(main()) 