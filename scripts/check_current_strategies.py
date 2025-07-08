#!/usr/bin/env python3
"""
Check current strategies in the database
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dotenv import load_dotenv
load_dotenv()
import logging
from shared.database import get_db_session
from models_clean import Strategy, StrategyConfig

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def check_current_strategies():
    """Check current strategies in the database"""
    try:
        logger.info("🔍 Checking current strategies in database...")
        
        with get_db_session() as session:
            strategies = session.query(Strategy).all()
            configs = session.query(StrategyConfig).all()
            
            logger.info(f"📊 Found {len(strategies)} strategies:")
            for strategy in strategies:
                logger.info(f"  - {strategy.id}: {strategy.name} ({strategy.strategy_type})")
                logger.info(f"    Symbols: {strategy.symbols}")
                logger.info(f"    Enabled: {strategy.enabled}")
                logger.info(f"    Parameters: {strategy.parameters}")
                logger.info("")
            
            logger.info(f"📊 Found {len(configs)} strategy configs:")
            for config in configs:
                logger.info(f"  - Strategy ID: {config.strategy_id}")
                logger.info(f"    Name: {config.name}")
                logger.info(f"    Class: {config.class_name}")
                logger.info(f"    Module: {config.module_path}")
                logger.info(f"    Status: {config.status}")
                logger.info("")
                
    except Exception as e:
        logger.error(f"❌ Error checking strategies: {e}")
        return False
    
    return True

if __name__ == "__main__":
    check_current_strategies() 