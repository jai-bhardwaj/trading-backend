#!/usr/bin/env python3
"""
Update all strategy files to use IST timezone
This script adds timezone imports and updates datetime usage
"""
import os
import re
from pathlib import Path

def update_strategy_file(file_path):
    """Update a strategy file to use IST timezone"""
    try:
        with open(file_path, 'r') as f:
            content = f.read()
        
        # Check if already updated
        if 'from shared.timezone import' in content:
            print(f"✅ {file_path} already updated")
            return
        
        # Add timezone import after other imports
        import_pattern = r'(from shared\.models import.*?\n)'
        if re.search(import_pattern, content):
            content = re.sub(
                import_pattern,
                r'\1from shared.timezone import get_ist_now, get_ist_timestamp\n',
                content
            )
        else:
            # Add at the top after existing imports
            content = content.replace(
                'from shared.models import MarketDataTick, TradingSignal, SignalType, StrategyConfig',
                'from shared.models import MarketDataTick, TradingSignal, SignalType, StrategyConfig\nfrom shared.timezone import get_ist_now, get_ist_timestamp'
            )
        
        # Replace datetime.now() with get_ist_now()
        content = re.sub(
            r'datetime\.now\(\)',
            'get_ist_now()',
            content
        )
        
        # Replace datetime.now().isoformat() with get_ist_timestamp()
        content = re.sub(
            r'datetime\.now\(\)\.isoformat\(\)',
            'get_ist_timestamp()',
            content
        )
        
        with open(file_path, 'w') as f:
            f.write(content)
        
        print(f"✅ Updated {file_path}")
        
    except Exception as e:
        print(f"❌ Error updating {file_path}: {e}")

def main():
    """Update all strategy files"""
    strategy_dir = Path("/root/app/trading-backend/strategy-service/strategies")
    
    if not strategy_dir.exists():
        print(f"❌ Strategy directory not found: {strategy_dir}")
        return
    
    strategy_files = list(strategy_dir.glob("*/strategy.py"))
    
    if not strategy_files:
        print("❌ No strategy files found")
        return
    
    print(f"🔄 Found {len(strategy_files)} strategy files to update")
    
    for strategy_file in strategy_files:
        update_strategy_file(strategy_file)
    
    print("✅ All strategy files updated with IST timezone")

if __name__ == "__main__":
    main()
