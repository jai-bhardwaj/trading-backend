#!/usr/bin/env python3
"""
Organize AngelOne Instruments - Clean Implementation

This script properly organizes instruments from the AngelOne data format
into clean categories based on instrument_type.
"""

import asyncio
import json
import redis.asyncio as aioredis
from collections import defaultdict
from datetime import datetime
from pathlib import Path

async def organize_instruments():
    """Organize instruments into clean categories"""
    
    print("🔄 Organizing AngelOne instruments...")
    print("=" * 50)
    
    # Connect to Redis
    redis_client = aioredis.from_url('redis://localhost:6379', encoding='utf-8', decode_responses=True)
    
    try:
        # Try to get instruments data from Redis first
        raw_data = await redis_client.get('instruments:angelone')
        instruments = None
        data_source = "Redis"
        
        if raw_data:
            instruments = json.loads(raw_data)
        else:
            # Fallback to loading from file
            print("📁 No Redis data found, checking data/instruments directory...")
            data_source = "file"
            instruments = load_instruments_from_file()
        
        if not instruments:
            print("❌ No instruments data found in Redis or files")
            print("💡 Run the download script first to get instrument data")
            return
        
        print(f"📊 Found {len(instruments):,} total instruments from {data_source}")
        
        # Define clean category mapping
        CATEGORIES = {
            'EQUITY': ['EQUITY'],
            'OPTIONS': ['OPTSTK', 'OPTIDX', 'OPTCUR', 'OPTFUT', 'OPTBLN', 'OPTIRC'],
            'FUTURES': ['FUTSTK', 'FUTIDX', 'FUTCOM', 'FUTCUR', 'FUTENR', 'FUTBAS', 'FUTBLN', 'FUTIRC', 'FUTIRT'],
            'COMMODITY': ['COMDTY'],
            'CURRENCY': ['UNDCUR', 'UNDIRC', 'UNDIRD', 'UNDIRT'],
            'INDEX': ['INDEX', 'AMXIDX']
        }
        
        # Initialize category containers
        organized_data = {cat: {} for cat in CATEGORIES.keys()}
        type_analysis = defaultdict(int)
        unknown_types = set()
        
        # Process each instrument
        for token, instrument in instruments.items():
            # Extract and clean data
            inst_type = instrument.get('instrument_type', '').strip() or 'EQUITY'
            symbol = instrument.get('symbol', '').strip()
            name = instrument.get('name', symbol).strip()
            exchange = instrument.get('exchange', '').strip()
            lot_size = instrument.get('lot_size', 1)
            tick_size = instrument.get('tick_size', 0.05)
            
            # Count instrument types
            type_analysis[inst_type] += 1
            
            # Find target category
            target_category = None
            for category, types in CATEGORIES.items():
                if inst_type in types:
                    target_category = category
                    break
            
            if not target_category:
                unknown_types.add(inst_type)
                continue
            
            # Create clean symbol key
            symbol_key = f"{symbol}:{exchange}" if exchange else symbol
            
            # Store in organized format
            organized_data[target_category][symbol_key] = {
                'token': token,
                'symbol': symbol,
                'name': name,
                'exchange': exchange,
                'instrument_type': inst_type,
                'lot_size': lot_size,
                'tick_size': tick_size
            }
        
        # Display analysis
        print("\n📊 Instrument Type Analysis:")
        print("-" * 30)
        for inst_type, count in sorted(type_analysis.items(), key=lambda x: x[1], reverse=True):
            status = "✅" if any(inst_type in types for types in CATEGORIES.values()) else "❓"
            print(f"  {status} {inst_type or '(empty)'}: {count:,}")
        
        if unknown_types:
            print(f"\n⚠️  Unknown instrument types: {', '.join(sorted(unknown_types))}")
        
        print(f"\n📂 Organized Categories:")
        print("-" * 30)
        total_organized = 0
        for category, instruments_dict in organized_data.items():
            if instruments_dict:
                count = len(instruments_dict)
                total_organized += count
                print(f"  📁 {category}: {count:,} instruments")
                
                # Show sample symbols
                samples = list(instruments_dict.keys())[:3]
                for sample in samples:
                    inst = instruments_dict[sample]
                    print(f"    • {sample}: {inst['name']} ({inst['exchange']})")
        
        print(f"\n📈 Organization Summary:")
        print(f"  Total instruments: {len(instruments):,}")
        print(f"  Successfully organized: {total_organized:,}")
        print(f"  Categories created: {len([cat for cat, data in organized_data.items() if data])}")
        
        # Store organized data in Redis
        print(f"\n💾 Storing organized data in Redis...")
        pipeline = redis_client.pipeline()
        
        # Store each category
        for category, instruments_dict in organized_data.items():
            if instruments_dict:
                key = f"instruments:category:{category.lower()}"
                pipeline.set(key, json.dumps(instruments_dict))
                print(f"  📁 Storing {category}: {len(instruments_dict):,} instruments")
        
        # Create summary
        summary = {}
        for category, instruments_dict in organized_data.items():
            if instruments_dict:
                # Get unique exchanges
                exchanges = set()
                for inst in instruments_dict.values():
                    if inst['exchange']:
                        exchanges.add(inst['exchange'])
                
                summary[category] = {
                    'count': len(instruments_dict),
                    'exchanges': sorted(list(exchanges)),
                    'sample_symbols': list(instruments_dict.keys())[:5]
                }
        
        # Store summary and metadata
        pipeline.set("instruments:summary", json.dumps(summary))
        pipeline.set("instruments:last_update", datetime.now().isoformat())
        pipeline.set("instruments:raw", json.dumps(instruments))  # Keep backup
        
        # Execute all Redis operations
        await pipeline.execute()
        
        print(f"\n✅ Successfully organized {len(instruments):,} instruments!")
        print(f"🎯 Categories created: {len(summary)}")
        
        # Show final summary
        print(f"\n📋 Final Category Summary:")
        print("-" * 30)
        for category, info in summary.items():
            exchanges = ', '.join(info['exchanges'][:3])
            if len(info['exchanges']) > 3:
                exchanges += f" (+{len(info['exchanges'])-3} more)"
            print(f"  📂 {category}: {info['count']:,} instruments")
            print(f"     Exchanges: {exchanges}")
    
    except Exception as e:
        print(f"❌ Error during organization: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        await redis_client.close()

def load_instruments_from_file() -> dict:
    """Load instruments from the most recent file in data/instruments"""
    try:
        instruments_dir = Path("data/instruments")
        if not instruments_dir.exists():
            print(f"📁 Directory {instruments_dir} does not exist")
            return {}
        
        # Find the most recent instruments file
        instrument_files = list(instruments_dir.glob("instruments_*.json"))
        if not instrument_files:
            print(f"📁 No instrument files found in {instruments_dir}")
            return {}
        
        # Sort by filename (date) and get the latest
        latest_file = sorted(instrument_files)[-1]
        print(f"📄 Loading instruments from {latest_file}")
        
        # Load and return the data
        with open(latest_file, 'r', encoding='utf-8') as f:
            return json.load(f)
            
    except Exception as e:
        print(f"❌ Error loading instruments from file: {e}")
        return {}

if __name__ == "__main__":
    asyncio.run(organize_instruments()) 