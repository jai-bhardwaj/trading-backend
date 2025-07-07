#!/usr/bin/env python3
"""
Analyze strategy orders
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import logging
from sqlalchemy import create_engine, func
from sqlalchemy.orm import sessionmaker
from models_clean import Order, Strategy
from datetime import datetime, timedelta

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def analyze_strategy_orders():
    """Analyze orders by strategy"""
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
        
        # Get orders from last 24 hours
        yesterday = datetime.now() - timedelta(days=1)
        recent_orders = session.query(Order).filter(Order.created_at >= yesterday).all()
        
        logger.info(f"📊 Found {len(recent_orders)} orders in the last 24 hours")
        
        if not recent_orders:
            logger.info("📋 No orders found in the last 24 hours")
            return True
        
        # Group orders by strategy
        strategy_orders = {}
        for order in recent_orders:
            strategy_id = order.strategy_id or "unknown"
            if strategy_id not in strategy_orders:
                strategy_orders[strategy_id] = []
            strategy_orders[strategy_id].append(order)
        
        # Analyze each strategy
        logger.info("📊 Strategy Analysis:")
        logger.info("=" * 50)
        
        for strategy_id, orders in strategy_orders.items():
            logger.info(f"📈 Strategy: {strategy_id}")
            logger.info(f"   Orders: {len(orders)}")
            
            # Count by side
            buy_orders = [o for o in orders if o.side == "BUY"]
            sell_orders = [o for o in orders if o.side == "SELL"]
            logger.info(f"   BUY orders: {len(buy_orders)}")
            logger.info(f"   SELL orders: {len(sell_orders)}")
            
            # Count by status
            status_counts = {}
            for order in orders:
                status = order.status
                status_counts[status] = status_counts.get(status, 0) + 1
            
            logger.info(f"   Status breakdown:")
            for status, count in status_counts.items():
                logger.info(f"     {status}: {count}")
            
            # Total quantity and value
            total_quantity = sum(o.quantity for o in orders)
            total_value = sum(o.quantity * (o.price or 0) for o in orders)
            logger.info(f"   Total quantity: {total_quantity}")
            logger.info(f"   Total value: ₹{total_value:,.2f}")
            
            # Symbols traded
            symbols = set(o.symbol for o in orders)
            logger.info(f"   Symbols traded: {', '.join(symbols)}")
            logger.info("")
        
        # Get all strategies
        strategies = session.query(Strategy).all()
        logger.info(f"📊 Total strategies in database: {len(strategies)}")
        
        session.close()
        return True
        
    except Exception as e:
        logger.error(f"❌ Failed to analyze strategy orders: {e}")
        return False

if __name__ == "__main__":
    success = analyze_strategy_orders()
    if success:
        logger.info("✅ Strategy order analysis completed successfully")
    else:
        logger.error("❌ Strategy order analysis failed")
        sys.exit(1) 