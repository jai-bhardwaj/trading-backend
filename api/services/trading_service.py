"""
Trading Service - Business logic for API endpoints
"""

import logging
from typing import List, Optional, Dict
from datetime import datetime
from models_clean import Strategy, UserStrategyConfig, Order as DBOrder, User
from shared.database import get_db_session
from order.manager import OrderManager
from sqlalchemy import text

logger = logging.getLogger(__name__)

class TradingService:
    """Service layer for trading operations"""
    
    def __init__(self):
        self.order_manager = None
        self._initialized = False
    
    async def initialize(self):
        """Initialize the trading service"""
        try:
            # For now, skip order manager initialization in API mode
            # The order manager is already running in the main trading backend
            logger.info("✅ Trading service initialized (API mode)")
            self._initialized = True
        except Exception as e:
            logger.error(f"❌ Failed to initialize trading service: {e}")
            raise
    
    def get_strategies(self) -> List[Dict]:
        """Get all available strategies"""
        try:
            with get_db_session() as session:
                strategies = session.query(Strategy).all()
                return [
                    {
                        "id": strategy.id,
                        "name": strategy.name,
                        "strategy_type": strategy.strategy_type,
                        "symbols": strategy.symbols,
                        "parameters": strategy.parameters,
                        "enabled": strategy.enabled,
                        "created_at": strategy.created_at,
                        "updated_at": strategy.updated_at
                    }
                    for strategy in strategies
                ]
        except Exception as e:
            logger.error(f"❌ Error getting strategies: {e}")
            return []
    
    def get_user_strategy_configs(self, user_id: str) -> List[Dict]:
        """Get strategy configs for a user"""
        try:
            with get_db_session() as session:
                configs = session.query(UserStrategyConfig).filter_by(user_id=user_id).all()
                return [
                    {
                        "id": config.id,
                        "user_id": config.user_id,
                        "strategy_id": config.strategy_id,
                        "enabled": config.enabled,
                        "risk_limits": config.risk_limits,
                        "order_preferences": config.order_preferences,
                        "created_at": config.created_at,
                        "updated_at": config.updated_at
                    }
                    for config in configs
                ]
        except Exception as e:
            logger.error(f"❌ Error getting user strategy configs: {e}")
            return []
    
    def get_user_strategy_config(self, user_id: str, strategy_id: str) -> Optional[Dict]:
        """Get specific strategy config for a user"""
        try:
            with get_db_session() as session:
                config = session.query(UserStrategyConfig).filter_by(
                    user_id=user_id,
                    strategy_id=strategy_id
                ).first()
                
                if config:
                    return {
                        "id": config.id,
                        "user_id": config.user_id,
                        "strategy_id": config.strategy_id,
                        "enabled": config.enabled,
                        "risk_limits": config.risk_limits,
                        "order_preferences": config.order_preferences,
                        "created_at": config.created_at,
                        "updated_at": config.updated_at
                    }
                return None
        except Exception as e:
            logger.error(f"❌ Error getting user strategy config: {e}")
            return None
    
    def update_user_strategy_config(self, user_id: str, strategy_id: str, updates: Dict) -> Optional[Dict]:
        """Update user strategy config"""
        try:
            with get_db_session() as session:
                config = session.query(UserStrategyConfig).filter_by(
                    user_id=user_id,
                    strategy_id=strategy_id
                ).first()
                
                if not config:
                    # Create new config
                    config = UserStrategyConfig(
                        user_id=user_id,
                        strategy_id=strategy_id,
                        enabled=updates.get("enabled", True),
                        risk_limits=updates.get("risk_limits"),
                        order_preferences=updates.get("order_preferences")
                    )
                    session.add(config)
                else:
                    # Update existing config
                    if "enabled" in updates:
                        config.enabled = updates["enabled"]
                    if "risk_limits" in updates:
                        config.risk_limits = updates["risk_limits"]
                    if "order_preferences" in updates:
                        config.order_preferences = updates["order_preferences"]
                    config.updated_at = datetime.utcnow()
                
                session.commit()
                
                return {
                    "id": config.id,
                    "user_id": config.user_id,
                    "strategy_id": config.strategy_id,
                    "enabled": config.enabled,
                    "risk_limits": config.risk_limits,
                    "order_preferences": config.order_preferences,
                    "created_at": config.created_at,
                    "updated_at": config.updated_at
                }
        except Exception as e:
            logger.error(f"❌ Error updating user strategy config: {e}")
            return None
    
    async def place_order(self, order_request: Dict) -> Dict:
        """Place an order"""
        try:
            # For API mode, we'll simulate order placement
            # In production, this would integrate with the main trading backend
            logger.info(f"📝 API Order Request: {order_request}")
            
            # Simulate order placement
            order_id = f"api_order_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
            
            return {
                "order_id": order_id,
                "status": "placed",
                "broker_order_id": None,
                "message": "Order placed via API (simulated)",
                "error": None
            }
        except Exception as e:
            logger.error(f"❌ Error placing order: {e}")
            return {
                "order_id": "",
                "status": "error",
                "broker_order_id": None,
                "message": "Order placement failed",
                "error": str(e)
            }
    
    def get_user_orders(self, user_id: str) -> List[Dict]:
        """Get orders for a user"""
        try:
            with get_db_session() as session:
                orders = session.query(DBOrder).filter_by(userId=user_id).order_by(DBOrder.createdAt.desc()).all()
                return [
                    {
                        "id": order.id,
                        "user_id": order.userId,
                        "strategy_id": order.strategyId,
                        "symbol": order.symbol,
                        "side": order.side,
                        "order_type": order.orderType,
                        "quantity": order.quantity,
                        "price": order.price,
                        "status": order.status,
                        "broker_order_id": order.brokerOrderId,
                        "created_at": order.createdAt,
                        "updated_at": order.updatedAt
                    }
                    for order in orders
                ]
        except Exception as e:
            logger.error(f"❌ Error getting user orders: {e}")
            return []
    
    def get_user_positions(self, user_id: str) -> List[Dict]:
        """Get positions for a user"""
        try:
            with get_db_session() as session:
                # Import Position model locally to avoid circular imports
                from models_clean import Base
                Position = None
                for table in Base.metadata.tables.values():
                    if table.name == 'positions':
                        # Create a simple query using raw SQL for now
                        result = session.execute(text("SELECT * FROM positions WHERE \"userId\" = :user_id"), {"user_id": user_id})
                        positions = []
                        for row in result:
                            positions.append({
                                "id": row[0],
                                "user_id": row[1],
                                "symbol": row[2],
                                "exchange": row[3],
                                "quantity": row[4],
                                "average_price": float(row[5]) if row[5] else 0.0,
                                "market_value": float(row[6]) if row[6] else 0.0,
                                "pnl": float(row[7]) if row[7] else 0.0,
                                "realized_pnl": float(row[8]) if row[8] else 0.0,
                                "day_change": float(row[9]) if row[9] else 0.0,
                                "day_change_pct": float(row[10]) if row[10] else 0.0,
                                "created_at": row[11],
                                "updated_at": row[12]
                            })
                        return positions
                return []
        except Exception as e:
            logger.error(f"❌ Error getting user positions: {e}")
            return []
    
    def get_user_position(self, user_id: str, symbol: str) -> Optional[Dict]:
        """Get specific position for a user and symbol"""
        try:
            with get_db_session() as session:
                result = session.execute(
                    text("SELECT * FROM positions WHERE \"userId\" = :user_id AND symbol = :symbol"), 
                    {"user_id": user_id, "symbol": symbol}
                )
                row = result.fetchone()
                if row:
                    return {
                        "id": row[0],
                        "user_id": row[1],
                        "symbol": row[2],
                        "exchange": row[3],
                        "quantity": row[4],
                        "average_price": float(row[5]) if row[5] else 0.0,
                        "market_value": float(row[6]) if row[6] else 0.0,
                        "pnl": float(row[7]) if row[7] else 0.0,
                        "realized_pnl": float(row[8]) if row[8] else 0.0,
                        "day_change": float(row[9]) if row[9] else 0.0,
                        "day_change_pct": float(row[10]) if row[10] else 0.0,
                        "created_at": row[11],
                        "updated_at": row[12]
                    }
                return None
        except Exception as e:
            logger.error(f"❌ Error getting user position: {e}")
            return None
    
    def get_user_trades(self, user_id: str) -> List[Dict]:
        """Get trades for a user"""
        try:
            with get_db_session() as session:
                result = session.execute(
                    text("SELECT * FROM trades WHERE \"userId\" = :user_id ORDER BY created_at DESC"), 
                    {"user_id": user_id}
                )
                trades = []
                for row in result:
                    trades.append({
                        "id": row[0],
                        "user_id": row[1],
                        "order_id": row[2],
                        "symbol": row[3],
                        "side": row[4],
                        "quantity": row[5],
                        "price": float(row[6]) if row[6] else 0.0,
                        "net_amount": float(row[7]) if row[7] else 0.0,
                        "trade_timestamp": row[8],
                        "created_at": row[9]
                    })
                return trades
        except Exception as e:
            logger.error(f"❌ Error getting user trades: {e}")
            return []
    
    def get_user_trades_by_symbol(self, user_id: str, symbol: str) -> List[Dict]:
        """Get trades for a user and specific symbol"""
        try:
            with get_db_session() as session:
                result = session.execute(
                    text("SELECT * FROM trades WHERE \"userId\" = :user_id AND symbol = :symbol ORDER BY created_at DESC"), 
                    {"user_id": user_id, "symbol": symbol}
                )
                trades = []
                for row in result:
                    trades.append({
                        "id": row[0],
                        "user_id": row[1],
                        "order_id": row[2],
                        "symbol": row[3],
                        "side": row[4],
                        "quantity": row[5],
                        "price": float(row[6]) if row[6] else 0.0,
                        "net_amount": float(row[7]) if row[7] else 0.0,
                        "trade_timestamp": row[8],
                        "created_at": row[9]
                    })
                return trades
        except Exception as e:
            logger.error(f"❌ Error getting user trades by symbol: {e}")
            return []
    
    def get_health_status(self) -> Dict:
        """Get system health status"""
        try:
            # Test database connection
            with get_db_session() as session:
                session.execute(text("SELECT 1"))
                db_connected = True
        except Exception as e:
            logger.error(f"❌ Database health check failed: {e}")
            db_connected = False
        
        return {
            "status": "healthy" if db_connected else "unhealthy",
            "timestamp": datetime.utcnow(),
            "database_connected": db_connected,
            "redis_connected": True,  # TODO: Add Redis health check
            "trading_system_active": self._initialized
        } 