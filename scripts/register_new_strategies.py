#!/usr/bin/env python3
"""
Register new strategies to database - Clear existing and add new 5 strategies
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dotenv import load_dotenv
load_dotenv()
import logging
import uuid
from shared.database import get_db_session
from models_clean import Strategy, StrategyConfig
from strategy.registry import get_all_strategies

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def clear_existing_strategies():
    """Clear all existing strategies from database"""
    try:
        with get_db_session() as session:
            # Delete all strategy configs first
            config_count = session.query(StrategyConfig).delete()
            logger.info(f"🗑️ Deleted {config_count} strategy configs")
            
            # Delete all strategies
            strategy_count = session.query(Strategy).delete()
            logger.info(f"🗑️ Deleted {strategy_count} strategies")
            
            session.commit()
            logger.info("✅ All existing strategies cleared")
            
    except Exception as e:
        logger.error(f"❌ Error clearing strategies: {e}")
        return False
    
    return True

def register_new_strategies():
    """Register the new 5 strategies to database"""
    try:
        # Get all available strategies
        strategies = get_all_strategies()
        logger.info(f"📊 Found {len(strategies)} strategies to register")
        
        with get_db_session() as session:
            registered_count = 0
            
            for strategy_id, strategy_info in strategies.items():
                try:
                    # Create strategy
                    strategy = Strategy(
                        id=strategy_id,
                        name=strategy_info.get("name", strategy_id),
                        strategy_type=strategy_info.get("type", "CUSTOM"),
                        symbols=strategy_info.get("symbols", []),
                        parameters=strategy_info.get("parameters", {}),
                        enabled=strategy_info.get("enabled", True)
                    )
                    
                    session.add(strategy)
                    
                    # Create strategy config with proper ID
                    config = StrategyConfig(
                        id=str(uuid.uuid4()),  # Generate unique ID
                        strategy_id=strategy_id,
                        name=f"{strategy_info.get('name', strategy_id)} Config",
                        class_name=strategy_info.get("name", strategy_id),
                        module_path=f"strategy.{strategy_id}",
                        config_json=strategy_info.get("parameters", {}),
                        status="ACTIVE",
                        auto_start=False
                    )
                    
                    session.add(config)
                    session.commit()
                    
                    logger.info(f"✅ Registered strategy: {strategy_id}")
                    registered_count += 1
                    
                except Exception as e:
                    logger.error(f"❌ Error registering strategy {strategy_id}: {e}")
                    session.rollback()
            
            logger.info(f"✅ Registration complete! Registered {registered_count} strategies")
            return True
            
    except Exception as e:
        logger.error(f"❌ Failed to register strategies: {e}")
        return False

def main():
    """Main function to clear and register strategies"""
    logger.info("🚀 Starting strategy registration process...")
    
    # Step 1: Clear existing strategies
    logger.info("📋 Step 1: Clearing existing strategies...")
    if not clear_existing_strategies():
        logger.error("❌ Failed to clear existing strategies")
        return False
    
    # Step 2: Register new strategies
    logger.info("📋 Step 2: Registering new strategies...")
    if not register_new_strategies():
        logger.error("❌ Failed to register new strategies")
        return False
    
    logger.info("🎉 Strategy registration completed successfully!")
    logger.info("📊 New strategies registered:")
    strategies = get_all_strategies()
    for strategy_id, strategy_info in strategies.items():
        logger.info(f"  - {strategy_id}: {strategy_info['name']}")
    
    return True

if __name__ == "__main__":
    main() 