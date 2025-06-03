#!/usr/bin/env python3
"""
Complete AngelOne Integration Flow Demo

This demo shows the complete flow:
1. How instruments are downloaded and categorized
2. How to find instruments for trading
3. How to get tokens for real-time data subscription
4. How strategies can use this data
"""

import asyncio
import os
import json
from dotenv import load_dotenv

load_dotenv()

async def demo_complete_flow():
    """Demonstrate the complete AngelOne integration flow"""
    
    print("🚀 Complete AngelOne Integration Flow Demo")
    print("=" * 60)
    
    try:
        from app.services.categorized_redis_market_data import create_categorized_service
        
        # Setup broker config
        broker_config = {
            'api_key': os.getenv('ANGELONE_API_KEY', 'demo'),
            'client_id': os.getenv('ANGELONE_CLIENT_ID', 'demo'),
            'password': os.getenv('ANGELONE_PASSWORD', 'demo'),
            'totp_token': os.getenv('ANGELONE_TOTP_TOKEN', 'demo')
        }
        
        print("📊 Step 1: Initialize Market Data Service")
        print("-" * 40)
        service = await create_categorized_service(broker_config)
        
        metrics = await service.get_metrics()
        print(f"✅ Service initialized with {metrics['total_instruments']:,} instruments")
        print(f"📂 Categories: {metrics['categories_count']}")
        print()
        
        print("🔍 Step 2: Discover Instruments for Trading")
        print("-" * 40)
        
        # Example 1: Find Bank Nifty options for options strategy
        print("🎯 Finding Bank Nifty Options:")
        bank_nifty_options = await service.search_instruments(
            'BANKNIFTY', 
            category='OPTIONS', 
            exchange='NFO', 
            limit=10
        )
        
        if bank_nifty_options:
            print(f"   Found {len(bank_nifty_options)} Bank Nifty options")
            for option in bank_nifty_options[:3]:
                print(f"   • {option['symbol']}: Token {option['token']}")
        
        # Example 2: Find NSE equity stocks for equity strategy
        print("\n📈 Finding NSE Bank Stocks:")
        bank_stocks = await service.search_instruments(
            'BANK', 
            category='EQUITY', 
            exchange='NSE', 
            limit=5
        )
        
        if bank_stocks:
            print(f"   Found {len(bank_stocks)} bank stocks")
            for stock in bank_stocks:
                print(f"   • {stock['symbol']}: Token {stock['token']}")
        
        # Example 3: Find NIFTY futures
        print("\n🔮 Finding NIFTY Futures:")
        nifty_futures = await service.search_instruments(
            'NIFTY', 
            category='FUTURES', 
            limit=3
        )
        
        if nifty_futures:
            print(f"   Found {len(nifty_futures)} NIFTY futures")
            for future in nifty_futures:
                print(f"   • {future['symbol']}: Token {future['token']}")
        
        print()
        
        print("📡 Step 3: Extract Tokens for Real-Time Subscription")
        print("-" * 40)
        
        # Collect all tokens for live data subscription
        all_tokens = []
        
        # From options
        option_tokens = [opt['token'] for opt in bank_nifty_options]
        all_tokens.extend(option_tokens)
        
        # From stocks
        stock_tokens = [stock['token'] for stock in bank_stocks]
        all_tokens.extend(stock_tokens)
        
        # From futures
        future_tokens = [fut['token'] for fut in nifty_futures]
        all_tokens.extend(future_tokens)
        
        print(f"📊 Total tokens for subscription: {len(all_tokens)}")
        print(f"🎯 Sample tokens: {all_tokens[:5]}")
        
        # Show WebSocket subscription format
        print(f"\n📲 WebSocket Subscription Format:")
        websocket_payload = {
            "correlationID": "strategy_001",
            "action": 1,
            "params": {
                "mode": 1,
                "tokenList": [
                    {"exchangeType": 1, "tokens": all_tokens[:10]}  # First 10 tokens
                ]
            }
        }
        print(json.dumps(websocket_payload, indent=2))
        print()
        
        print("🚀 Step 4: Strategy Usage Examples")
        print("-" * 40)
        
        # Example strategy implementations
        await demo_strategy_usage(service, bank_nifty_options, bank_stocks)
        
        print("💾 Step 5: Data Storage Structure")
        print("-" * 40)
        
        print("📁 Redis Storage Structure:")
        print("   instruments:category:equity    # 17,924 equity stocks")
        print("   instruments:category:options   # 95,043 option contracts")
        print("   instruments:category:futures   # 1,825 future contracts")
        print("   instruments:summary           # Category summary")
        print("   live_data:{token}             # Real-time price data")
        
        print("\n📁 File Storage Structure:")
        print("   data/instruments/instruments_20250603.json  # Daily backup")
        print("   data/market_data/tick_data/                 # Tick data")
        print("   data/market_data/ohlc_data/                 # OHLC data")
        
        await service.cleanup()
        print("\n✅ Complete flow demonstration finished!")
        
    except Exception as e:
        print(f"❌ Demo failed: {e}")
        import traceback
        traceback.print_exc()

async def demo_strategy_usage(service, options, stocks):
    """Demonstrate how strategies would use the instruments"""
    
    print("📈 Strategy Example 1: Options Trading")
    print("   1. Find ATM options for Bank Nifty")
    print("   2. Subscribe to live data for these options")
    print("   3. Monitor option Greeks and prices")
    print("   4. Execute trades based on signals")
    
    # Simulate options strategy setup
    atm_options = [opt for opt in options if 'CE' in opt['symbol'] or 'PE' in opt['symbol']]
    if atm_options:
        print(f"   ✅ Selected {len(atm_options)} ATM options for trading")
    
    print("\n🏦 Strategy Example 2: Bank Stock Momentum")
    print("   1. Monitor top 5 bank stocks")
    print("   2. Track price movements and volume")
    print("   3. Detect momentum breakouts")
    print("   4. Execute momentum trades")
    
    # Simulate equity strategy setup
    if stocks:
        print(f"   ✅ Monitoring {len(stocks)} bank stocks for momentum")
    
    print("\n⚡ Strategy Example 3: Cross-Asset Arbitrage")
    print("   1. Monitor NIFTY index, futures, and options")
    print("   2. Detect price discrepancies")
    print("   3. Execute arbitrage trades")
    print("   4. Manage risk across instruments")
    
    # Simulate arbitrage strategy setup
    nifty_instruments = await service.search_instruments('NIFTY', limit=20)
    if nifty_instruments:
        print(f"   ✅ Tracking {len(nifty_instruments)} NIFTY instruments for arbitrage")

async def demo_live_data_simulation():
    """Simulate how live data would be processed"""
    
    print("\n📊 Live Data Processing Simulation")
    print("-" * 40)
    
    # Simulate incoming WebSocket data
    sample_live_data = [
        {"token": "1594", "ltp": 1805.50, "volume": 125000, "timestamp": "2025-06-03T09:15:00"},
        {"token": "11536", "ltp": 4245.75, "volume": 85000, "timestamp": "2025-06-03T09:15:01"},
        {"token": "2885", "ltp": 2680.25, "volume": 200000, "timestamp": "2025-06-03T09:15:02"}
    ]
    
    print("📡 Simulated Live Data Feed:")
    for data in sample_live_data:
        token = data['token']
        ltp = data['ltp']
        volume = data['volume']
        
        print(f"   Token {token}: LTP={ltp}, Volume={volume:,}")
        
        # This would be stored in Redis as:
        # redis_key = f"live_data:{token}"
        # redis_value = json.dumps(data)
    
    print("\n🔄 How Strategies Access This Data:")
    print("   1. strategy.get_current_price(token) -> Gets LTP from Redis")
    print("   2. strategy.get_volume(token) -> Gets volume from Redis") 
    print("   3. strategy.calculate_signals() -> Uses price/volume for decisions")
    print("   4. strategy.place_order() -> Executes trades based on signals")

if __name__ == "__main__":
    asyncio.run(demo_complete_flow()) 