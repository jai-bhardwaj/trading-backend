#!/usr/bin/env python3
"""
Strategy Signal Monitor
Monitor and display signals from all strategy services in real-time
"""
import asyncio
import json
import logging
import sys
from datetime import datetime
from typing import Dict, List
import redis.asyncio as redis

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class StrategySignalMonitor:
    """Monitor signals from all strategy services"""
    
    def __init__(self, redis_url: str = "redis://localhost:6379"):
        self.redis_url = redis_url
        self.redis_client = None
        self.signals_received = []
        self.strategy_stats = {}
        
    async def connect(self):
        """Connect to Redis"""
        try:
            self.redis_client = redis.from_url(self.redis_url)
            await self.redis_client.ping()
            logger.info("✅ Connected to Redis for signal monitoring")
            return True
        except Exception as e:
            logger.error(f"❌ Failed to connect to Redis: {e}")
            return False
    
    async def disconnect(self):
        """Disconnect from Redis"""
        if self.redis_client:
            await self.redis_client.close()
    
    async def monitor_signals(self):
        """Monitor strategy signals in real-time"""
        try:
            pubsub = self.redis_client.pubsub()
            await pubsub.subscribe("strategy_signals")
            
            logger.info("📡 Monitoring strategy signals...")
            logger.info("Press Ctrl+C to stop monitoring")
            print("\n" + "="*80)
            print("STRATEGY SIGNAL MONITOR")
            print("="*80)
            
            async for message in pubsub.listen():
                if message['type'] == 'message':
                    try:
                        signal_data = json.loads(message['data'])
                        await self._process_signal(signal_data)
                    except Exception as e:
                        logger.error(f"❌ Error processing signal: {e}")
                        
        except Exception as e:
            logger.error(f"❌ Error monitoring signals: {e}")
    
    async def _process_signal(self, signal_data: Dict):
        """Process and display a signal"""
        try:
            # Extract signal information
            strategy_id = signal_data.get('strategy_id', 'UNKNOWN')
            symbol = signal_data.get('symbol', 'UNKNOWN')
            signal_type = signal_data.get('signal_type', 'UNKNOWN')
            confidence = signal_data.get('confidence', 0.0)
            price = signal_data.get('price', 0.0)
            quantity = signal_data.get('quantity', 0)
            timestamp = signal_data.get('timestamp', '')
            metadata = signal_data.get('metadata', {})
            
            # Update statistics
            if strategy_id not in self.strategy_stats:
                self.strategy_stats[strategy_id] = {
                    'total_signals': 0,
                    'buy_signals': 0,
                    'sell_signals': 0,
                    'last_signal': None
                }
            
            self.strategy_stats[strategy_id]['total_signals'] += 1
            if signal_type == 'BUY':
                self.strategy_stats[strategy_id]['buy_signals'] += 1
            elif signal_type == 'SELL':
                self.strategy_stats[strategy_id]['sell_signals'] += 1
            
            self.strategy_stats[strategy_id]['last_signal'] = datetime.now()
            
            # Display signal
            self._display_signal(signal_data)
            
            # Store signal
            self.signals_received.append(signal_data)
            
        except Exception as e:
            logger.error(f"❌ Error processing signal: {e}")
    
    def _display_signal(self, signal_data: Dict):
        """Display a formatted signal"""
        strategy_id = signal_data.get('strategy_id', 'UNKNOWN')
        symbol = signal_data.get('symbol', 'UNKNOWN')
        signal_type = signal_data.get('signal_type', 'UNKNOWN')
        confidence = signal_data.get('confidence', 0.0)
        price = signal_data.get('price', 0.0)
        quantity = signal_data.get('quantity', 0)
        timestamp = signal_data.get('timestamp', '')
        metadata = signal_data.get('metadata', {})
        
        # Color coding for signal types
        signal_color = "🟢" if signal_type == "BUY" else "🔴" if signal_type == "SELL" else "🟡"
        
        print(f"\n{signal_color} NEW SIGNAL RECEIVED")
        print(f"   Strategy: {strategy_id}")
        print(f"   Symbol: {symbol}")
        print(f"   Type: {signal_type}")
        print(f"   Price: ₹{price:.2f}")
        print(f"   Quantity: {quantity}")
        print(f"   Confidence: {confidence:.2f}")
        print(f"   Time: {timestamp}")
        
        # Display metadata if available
        if metadata:
            print(f"   Metadata:")
            for key, value in metadata.items():
                if isinstance(value, float):
                    print(f"     {key}: {value:.2f}")
                else:
                    print(f"     {key}: {value}")
        
        print("-" * 60)
    
    def display_summary(self):
        """Display summary of all signals received"""
        print("\n" + "="*80)
        print("SIGNAL SUMMARY")
        print("="*80)
        
        if not self.strategy_stats:
            print("No signals received yet.")
            return
        
        total_signals = sum(stats['total_signals'] for stats in self.strategy_stats.values())
        print(f"Total signals received: {total_signals}")
        print(f"Total strategies active: {len(self.strategy_stats)}")
        
        print("\nStrategy Statistics:")
        for strategy_id, stats in self.strategy_stats.items():
            print(f"\n📊 {strategy_id}:")
            print(f"   Total Signals: {stats['total_signals']}")
            print(f"   Buy Signals: {stats['buy_signals']}")
            print(f"   Sell Signals: {stats['sell_signals']}")
            if stats['last_signal']:
                print(f"   Last Signal: {stats['last_signal'].strftime('%H:%M:%S')}")
    
    async def check_market_data_streams(self):
        """Check if market data streams exist"""
        print("\n" + "="*80)
        print("MARKET DATA STREAMS CHECK")
        print("="*80)
        
        # Common symbols
        symbols = ["RELIANCE", "TCS", "INFY", "HDFC", "ICICIBANK"]
        
        for symbol in symbols:
            stream_name = f"market_data_stream:{symbol}"
            try:
                stream_info = await self.redis_client.xinfo_stream(stream_name)
                print(f"✅ {stream_name}: {stream_info['length']} messages")
            except Exception as e:
                print(f"❌ {stream_name}: Not found")
    
    async def run_monitor(self):
        """Run the signal monitor"""
        try:
            logger.info("🚀 Starting Strategy Signal Monitor")
            
            # Connect to Redis
            if not await self.connect():
                return False
            
            # Check market data streams
            await self.check_market_data_streams()
            
            # Start monitoring signals
            await self.monitor_signals()
            
        except KeyboardInterrupt:
            logger.info("🛑 Signal monitoring stopped by user")
            self.display_summary()
        except Exception as e:
            logger.error(f"❌ Monitor failed: {e}")
        finally:
            await self.disconnect()

async def main():
    """Main function"""
    monitor = StrategySignalMonitor()
    
    try:
        await monitor.run_monitor()
    except KeyboardInterrupt:
        print("\n🛑 Monitoring stopped by user")
    except Exception as e:
        logger.error(f"❌ Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
