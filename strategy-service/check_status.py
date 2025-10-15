#!/usr/bin/env python3
"""
Strategy Service Status Checker
Check the status of all strategy services
"""
import asyncio
import json
import logging
import sys
from datetime import datetime
import redis.asyncio as redis

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class StrategyStatusChecker:
    """Check status of all strategy services"""
    
    def __init__(self, redis_url: str = "redis://localhost:6379"):
        self.redis_url = redis_url
        self.redis_client = None
        
    async def connect(self):
        """Connect to Redis"""
        try:
            self.redis_client = redis.from_url(self.redis_url)
            await self.redis_client.ping()
            logger.info("✅ Connected to Redis")
            return True
        except Exception as e:
            logger.error(f"❌ Failed to connect to Redis: {e}")
            return False
    
    async def disconnect(self):
        """Disconnect from Redis"""
        if self.redis_client:
            await self.redis_client.close()
    
    async def check_strategy_streams(self):
        """Check if strategy consumer groups exist"""
        print("\n" + "="*80)
        print("STRATEGY CONSUMER GROUPS STATUS")
        print("="*80)
        
        # Expected strategy services
        strategies = [
            "rsi_dmi_strategy",
            "btst_momentum_strategy", 
            "rsi_dmi_intraday_strategy",
            "swing_momentum_strategy",
            "test_strategy"
        ]
        
        symbols = ["RELIANCE", "TCS", "INFY", "HDFC", "ICICIBANK"]
        
        for strategy in strategies:
            print(f"\n📊 {strategy}:")
            
            for symbol in symbols:
                stream_name = f"market_data_stream:{symbol}"
                consumer_group = "strategy_consumers"
                
                try:
                    # Check if consumer group exists
                    groups = await self.redis_client.xinfo_groups(stream_name)
                    group_exists = any(group['name'] == consumer_group for group in groups)
                    
                    if group_exists:
                        # Get consumer info
                        consumers = await self.redis_client.xinfo_consumers(stream_name, consumer_group)
                        strategy_consumers = [c for c in consumers if strategy in c['name']]
                        
                        if strategy_consumers:
                            consumer = strategy_consumers[0]
                            print(f"   ✅ {symbol}: Consumer active (pending: {consumer['pending']})")
                        else:
                            print(f"   ⚠️ {symbol}: Group exists but no consumer")
                    else:
                        print(f"   ❌ {symbol}: No consumer group")
                        
                except Exception as e:
                    print(f"   ❌ {symbol}: Error - {e}")
    
    async def check_recent_signals(self):
        """Check recent signals in Redis"""
        print("\n" + "="*80)
        print("RECENT SIGNALS CHECK")
        print("="*80)
        
        try:
            # Check if there are any recent signals
            # We can't directly read from pub/sub, but we can check if the channel exists
            # and if there are any recent messages
            
            # Try to get info about the signal channel
            print("📡 Strategy signals channel: strategy_signals")
            print("   (Signals are published here by strategy services)")
            
            # Check if we can see any recent activity by looking at stream lengths
            symbols = ["RELIANCE", "TCS", "INFY", "HDFC", "ICICIBANK"]
            
            print("\n📊 Market Data Stream Activity:")
            for symbol in symbols:
                stream_name = f"market_data_stream:{symbol}"
                try:
                    stream_info = await self.redis_client.xinfo_stream(stream_name)
                    print(f"   {symbol}: {stream_info['length']} messages")
                except Exception as e:
                    print(f"   {symbol}: No stream found")
                    
        except Exception as e:
            logger.error(f"❌ Error checking signals: {e}")
    
    async def run_status_check(self):
        """Run the status check"""
        try:
            logger.info("🚀 Starting Strategy Status Check")
            
            # Connect to Redis
            if not await self.connect():
                return False
            
            # Check strategy streams
            await self.check_strategy_streams()
            
            # Check recent signals
            await self.check_recent_signals()
            
            print("\n" + "="*80)
            print("RECOMMENDATIONS")
            print("="*80)
            print("1. Make sure all strategy services are running:")
            print("   docker-compose ps")
            print("\n2. Check strategy service logs:")
            print("   docker-compose logs rsi-dmi-strategy")
            print("   docker-compose logs btst-momentum-strategy")
            print("   docker-compose logs rsi-dmi-intraday-strategy")
            print("   docker-compose logs swing-momentum-strategy")
            print("   docker-compose logs test-strategy")
            print("\n3. Monitor signals in real-time:")
            print("   python strategy-service/monitor_signals.py")
            print("\n4. Start all services if not running:")
            print("   docker-compose up -d")
            
        except Exception as e:
            logger.error(f"❌ Status check failed: {e}")
        finally:
            await self.disconnect()

async def main():
    """Main function"""
    checker = StrategyStatusChecker()
    
    try:
        await checker.run_status_check()
    except Exception as e:
        logger.error(f"❌ Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
