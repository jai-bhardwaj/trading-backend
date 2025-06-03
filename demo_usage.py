#!/usr/bin/env python3
"""
Demo Usage - Clean Categorized Market Data Service

This script demonstrates practical usage examples.
"""

import asyncio
import os
from dotenv import load_dotenv

load_dotenv()

async def demo_usage():
    """Demonstrate practical usage of the service"""
    
    print("🎯 Practical Usage Demo - Clean Market Data Service")
    print("=" * 60)
    
    from app.services.categorized_redis_market_data import create_categorized_service
    
    # Setup
    broker_config = {
        'api_key': os.getenv('ANGELONE_API_KEY', 'demo'),
        'client_id': os.getenv('ANGELONE_CLIENT_ID', 'demo'),
        'password': os.getenv('ANGELONE_PASSWORD', 'demo'),
        'totp_token': os.getenv('ANGELONE_TOTP_TOKEN', 'demo')
    }
    
    service = await create_categorized_service(broker_config)
    
    # Example 1: Get NSE equity stocks
    print("📊 Example 1: Get NSE Equity Stocks")
    print("-" * 40)
    equity = await service.get_category_instruments('EQUITY')
    nse_stocks = {k: v for k, v in equity.items() if v['exchange'] == 'NSE'}
    print(f"Total NSE equity stocks: {len(nse_stocks):,}")
    
    # Show some popular stocks
    popular_stocks = ['INFY', 'TCS', 'RELIANCE', 'HDFCBANK', 'SBIN']
    for stock in popular_stocks:
        results = await service.search_instruments(stock, category='EQUITY', exchange='NSE', limit=1)
        if results:
            result = results[0]
            print(f"  {result['symbol']}: {result['name']} (Token: {result['token']})")
    print()
    
    # Example 2: Find Index instruments  
    print("📈 Example 2: Index Instruments")
    print("-" * 40)
    indices = await service.get_category_instruments('INDEX')
    print(f"Total index instruments: {len(indices):,}")
    
    # Show popular indices
    popular_indices = ['NIFTY', 'SENSEX', 'BANKNIFTY']
    for index in popular_indices:
        results = await service.search_instruments(index, category='INDEX', limit=3)
        if results:
            print(f"  📊 {index} related indices:")
            for result in results:
                print(f"    • {result['symbol']}: {result['name']}")
    print()
    
    # Example 3: Options for popular stocks
    print("🎯 Example 3: Options for Popular Stocks")  
    print("-" * 40)
    
    # Find NIFTY options
    nifty_options = await service.search_instruments('NIFTY', category='OPTIONS', limit=5)
    print(f"NIFTY options (showing first 5 of many):")
    for option in nifty_options:
        print(f"  • {option['symbol']}: {option['name']} ({option['exchange']})")
    print()
    
    # Example 4: Commodity instruments
    print("🌾 Example 4: Commodity Trading") 
    print("-" * 40)
    commodities = await service.get_category_instruments('COMMODITY')
    print(f"Total commodity instruments: {len(commodities):,}")
    
    # Show popular commodities
    popular_commodities = ['GOLD', 'SILVER', 'CRUDE']
    for commodity in popular_commodities:
        results = await service.search_instruments(commodity, category='COMMODITY', limit=2)
        if results:
            print(f"  🥇 {commodity} instruments:")
            for result in results:
                print(f"    • {result['symbol']}: {result['name']} ({result['exchange']})")
    print()
    
    # Example 5: Currency instruments
    print("💱 Example 5: Currency Trading")
    print("-" * 40)
    currencies = await service.get_category_instruments('CURRENCY')
    print(f"Total currency instruments: {len(currencies):,}")
    
    # Show USD related instruments
    usd_instruments = await service.search_instruments('USD', category='CURRENCY', limit=3)
    if usd_instruments:
        print(f"  💵 USD related instruments:")
        for result in usd_instruments:
            print(f"    • {result['symbol']}: {result['name']} ({result['exchange']})")
    print()
    
    # Example 6: Search by exchange
    print("🏛️ Example 6: Search by Exchange")
    print("-" * 40)
    
    exchanges = ['NSE', 'BSE', 'MCX']
    for exchange in exchanges:
        bank_stocks = await service.search_instruments('BANK', exchange=exchange, limit=3)
        if bank_stocks:
            print(f"  🏦 Bank related instruments on {exchange}:")
            for result in bank_stocks:
                print(f"    • {result['symbol']}: {result['name']} ({result['category']})")
    print()
    
    # Example 7: Service metrics
    print("📊 Example 7: Service Metrics")
    print("-" * 40)
    metrics = await service.get_metrics()
    summary = await service.get_category_summary()
    
    print(f"Service Status: {metrics['download_status']}")
    print(f"Total Instruments: {metrics['total_instruments']:,}")
    print(f"Categories: {metrics['categories_count']}")
    
    print(f"\nCategory Breakdown:")
    for category, info in summary.items():
        print(f"  📂 {category}: {info['count']:,} instruments")
        print(f"     Exchanges: {', '.join(info['exchanges'][:5])}")
    
    await service.cleanup()
    print("\n✅ Demo completed!")

if __name__ == "__main__":
    asyncio.run(demo_usage()) 