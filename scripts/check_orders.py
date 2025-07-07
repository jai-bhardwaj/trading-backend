#!/usr/bin/env python3
"""
Check orders in database
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import logging
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models_clean import Order
from datetime import datetime, timedelta

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def check_orders():
    """Check orders in the database"""
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
        orders = session.query(Order).filter(Order.created_at >= yesterday).all()
        
        logger.info(f"📊 Found {len(orders)} orders in the last 24 hours")
        
        if orders:
            logger.info("📋 Recent orders:")
            for order in orders:
                logger.info(f"  - {order.order_id}: {order.symbol} {order.side} {order.quantity} @ {order.price}")
                logger.info(f"    Status: {order.status}, Strategy: {order.strategy_id}")
                logger.info(f"    Created: {order.created_at}")
                if order.broker_order_id:
                    logger.info(f"    Broker Order ID: {order.broker_order_id}")
                logger.info("")
        else:
            logger.info("📋 No orders found in the last 24 hours")
        
        # Get all orders count
        total_orders = session.query(Order).count()
        logger.info(f"📊 Total orders in database: {total_orders}")
        
        session.close()
        return True
        
    except Exception as e:
        logger.error(f"❌ Failed to check orders: {e}")
        return False

if __name__ == "__main__":
    success = check_orders()
    if success:
        logger.info("✅ Order check completed successfully")
    else:
        logger.error("❌ Order check failed")
        sys.exit(1) 