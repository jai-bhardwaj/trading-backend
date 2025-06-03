#!/usr/bin/env python3
"""
Test Clean Categorized Market Data Service

This script tests the clean categorized service implementation.
"""

import asyncio
import logging
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def test_clean_service():
    """Test the clean categorized service"""
    
    print("🧪 Testing Clean Categorized Market Data Service")
    print("=" * 60)
    
    try:
        # Import the clean service
        from app.services.categorized_redis_market_data import create_categorized_service
        
        # Setup broker config
        broker_config = {
            'api_key': os.getenv('ANGELONE_API_KEY', 'demo_key'),
            'client_id': os.getenv('ANGELONE_CLIENT_ID', 'demo_client'),
            'password': os.getenv('ANGELONE_PASSWORD', 'demo_password'),
            'totp_token': os.getenv('ANGELONE_TOTP_TOKEN', 'demo_totp')
        }
        
        # Initialize service
        print("🚀 Initializing clean service...")
        service = await create_categorized_service(broker_config)
        
        # Get metrics
        metrics = await service.get_metrics()
        print(f"✅ Service initialized!")
        print(f"   📊 Total instruments: {metrics['total_instruments']:,}")
        print(f"   📂 Categories: {metrics['categories_count']}")
        print(f"   🔄 Status: {metrics['download_status']}")
        print()
        
        # Test 1: Get category summary
        print("📋 Test 1: Category Summary")
        print("-" * 40)
        summary = await service.get_category_summary()
        if summary:
            for category, info in summary.items():
                exchanges = ', '.join(info['exchanges'][:3])
                print(f"📂 {category}: {info['count']:,} instruments ({exchanges})")
        print()
        
        # Test 2: Get instruments by category
        print("🔍 Test 2: Get Category Instruments")
        print("-" * 40)
        
        for category in ['EQUITY', 'INDEX', 'OPTIONS']:
            instruments = await service.get_category_instruments(category)
            if instruments:
                print(f"📂 {category}: {len(instruments):,} instruments")
                # Show first 3 as samples
                for i, (symbol_key, inst) in enumerate(instruments.items()):
                    if i >= 3:
                        break
                    print(f"   • {symbol_key}: {inst['name']} (Token: {inst['token']})")
            else:
                print(f"📂 {category}: No instruments found")
        print()
        
        # Test 3: Search functionality
        print("🔎 Test 3: Search Instruments")
        print("-" * 40)
        
        # Search for various patterns
        search_tests = [
            ('NIFTY', None, None),
            ('INFY', 'EQUITY', None),
            ('BANK', None, 'NSE'),
        ]
        
        for query, category, exchange in search_tests:
            filter_text = ""
            if category:
                filter_text += f" in {category}"
            if exchange:
                filter_text += f" on {exchange}"
            
            print(f"🔍 Searching '{query}'{filter_text}:")
            results = await service.search_instruments(query, category, exchange, limit=5)
            
            if results:
                for result in results:
                    print(f"   • {result['symbol']} ({result['exchange']}) - {result['category']}")
                    print(f"     {result['name']} [Token: {result['token']}]")
            else:
                print("   No results found")
        print()
        
        # Test 4: Data structure validation
        print("✅ Test 4: Data Structure Validation")
        print("-" * 40)
        
        # Check if we have the expected instrument data structure
        equity_instruments = await service.get_category_instruments('EQUITY')
        if equity_instruments:
            sample_key = list(equity_instruments.keys())[0]
            sample_inst = equity_instruments[sample_key]
            
            expected_fields = ['token', 'symbol', 'name', 'exchange', 'instrument_type', 'lot_size', 'tick_size']
            missing_fields = [field for field in expected_fields if field not in sample_inst]
            
            if missing_fields:
                print(f"⚠️  Missing fields in instrument data: {missing_fields}")
            else:
                print("✅ All expected fields present in instrument data")
                
            print(f"📊 Sample instrument structure:")
            for field, value in sample_inst.items():
                print(f"   {field}: {value}")
        print()
        
        # Cleanup
        await service.cleanup()
        print("✅ Test completed successfully!")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        logger.exception("Test error")

if __name__ == "__main__":
    asyncio.run(test_clean_service()) 