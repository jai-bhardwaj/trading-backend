#!/usr/bin/env python3
"""
Register strategies to database
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dotenv import load_dotenv
load_dotenv()
import logging
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models_clean import Strategy, StrategyConfig
from strategy.registry import get_all_strategies

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def register_strategies_to_db():
    """Register all available strategies to the database"""
    try:
        # Get database URL from environment
        db_url = os.getenv("DATABASE_URL")
        if not db_url:
            logger.error("❌ DATABASE_URL environment variable not set")
            return False
        
        # Create database connection
        engine = create_engine(db_url)
        Session = sessionmaker(bind=engine)
        session = Session()
        
        logger.info("✅ Connected to database")
        
        # Get all available strategies
        strategies = get_all_strategies()
        logger.info(f"📊 Found {len(strategies)} strategies to register")
        
        registered_count = 0
        
        for strategy_id, strategy_info in strategies.items():
            try:
                # Check if strategy already exists
                existing_strategy = session.query(Strategy).filter(Strategy.id == strategy_id).first()
                
                if existing_strategy:
                    logger.info(f"⏭️ Strategy {strategy_id} already exists, skipping")
                    continue
                
                # Create new strategy
                strategy = Strategy(
                    id=strategy_id,
                    name=strategy_info.get("name", strategy_id),
                    description=strategy_info.get("description", ""),
                    strategy_type=strategy_info.get("type", "CUSTOM"),
                    symbols=strategy_info.get("symbols", []),
                    parameters=strategy_info.get("parameters", {}),
                    enabled=strategy_info.get("enabled", True)
                )
                
                session.add(strategy)
                
                # Create strategy config
                config = StrategyConfig(
                    strategy_id=strategy_id,
                    parameters=strategy_info.get("parameters", {}),
                    enabled=strategy_info.get("enabled", True)
                )
                
                session.add(config)
                session.commit()
                
                logger.info(f"✅ Registered strategy: {strategy_id}")
                registered_count += 1
                
            except Exception as e:
                logger.error(f"❌ Error registering strategy {strategy_id}: {e}")
                session.rollback()
        
        logger.info(f"✅ Registration complete! Registered {registered_count} new strategies")
        session.close()
        return True
        
    except Exception as e:
        logger.error(f"❌ Failed to register strategies: {e}")
        return False

if __name__ == "__main__":
    success = register_strategies_to_db()
    if success:
        logger.info("🎉 Strategy registration completed successfully")
    else:
        logger.error("❌ Strategy registration failed")
        sys.exit(1) 