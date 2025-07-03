#!/usr/bin/env python3
"""
Strategy Engine Service - Handles strategy execution and marketplace
Isolated service for strategy management and execution
"""

import asyncio
import logging
import json
import time
from datetime import datetime
from typing import Dict, List, Optional, Any
from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
import redis.asyncio as redis
import httpx
import os
from dataclasses import dataclass, field
from enum import Enum

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration
@dataclass
class StrategyServiceConfig:
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/3")
    USER_SERVICE_URL: str = "http://localhost:8001"
    MARKET_DATA_SERVICE_URL: str = "http://localhost:8002"
    ORDER_SERVICE_URL: str = "http://localhost:8004"
    EXECUTION_INTERVAL: float = 1.0  # Execute strategies every second

config = StrategyServiceConfig()

class StrategyStatus(Enum):
    AVAILABLE = "available"
    ACTIVE = "active"
    PAUSED = "paused"

@dataclass
class StrategyTemplate:
    strategy_id: str
    name: str
    description: str
    category: str
    risk_level: str
    min_capital: float
    expected_return_annual: float
    max_drawdown: float
    symbols: List[str]
    parameters: Dict[str, Any]
    is_active: bool = True

@dataclass
class UserStrategy:
    user_id: str
    strategy_id: str
    status: StrategyStatus
    activated_at: str
    allocation_amount: float = 0.0
    custom_parameters: Dict[str, Any] = field(default_factory=dict)
    total_orders: int = 0
    successful_orders: int = 0
    total_pnl: float = 0.0

class BaseStrategy:
    """Base class for all trading strategies"""
    
    def __init__(self, strategy_id: str, config: Dict[str, Any]):
        self.strategy_id = strategy_id
        self.config = config
        self.symbols = config.get("symbols", [])
        self.last_execution = 0
        self.execution_count = 0
        
    async def should_execute(self, market_data: Dict[str, Any]) -> bool:
        """Check if strategy should execute based on market conditions"""
        # Base implementation - execute every minute
        return time.time() - self.last_execution > 60
    
    async def execute(self, market_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Execute strategy logic - to be implemented by subclasses"""
        raise NotImplementedError
    
    async def post_execute(self, signal: Optional[Dict[str, Any]]):
        """Post-execution cleanup"""
        self.last_execution = time.time()
        self.execution_count += 1

class RSIDMIStrategy(BaseStrategy):
    """RSI + DMI strategy implementation"""
    
    def __init__(self, strategy_id: str, config: Dict[str, Any]):
        super().__init__(strategy_id, config)
        self.price_history = {}
        
    async def execute(self, market_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Execute RSI + DMI strategy"""
        signals = []
        
        for symbol in self.symbols:
            symbol_data = market_data.get(symbol, {})
            if not symbol_data:
                continue
                
            current_price = symbol_data.get("ltp", 0)
            if current_price <= 0:
                continue
                
            # Store price history
            if symbol not in self.price_history:
                self.price_history[symbol] = []
            
            self.price_history[symbol].append({
                "price": current_price,
                "timestamp": time.time()
            })
            
            # Keep only last 14 periods for RSI calculation
            if len(self.price_history[symbol]) > 14:
                self.price_history[symbol] = self.price_history[symbol][-14:]
            
            # Calculate RSI (simplified)
            rsi = self._calculate_rsi(symbol)
            if rsi is None:
                continue
                
            # Generate signals
            if rsi > 70 and symbol_data.get("change_percent", 0) > 2:
                signals.append({
                    "strategy_id": self.strategy_id,
                    "symbol": symbol,
                    "action": "BUY",
                    "quantity": 10,
                    "price": current_price,
                    "reason": f"RSI oversold: {rsi:.2f}",
                    "timestamp": datetime.utcnow().isoformat()
                })
            elif rsi < 30 and symbol_data.get("change_percent", 0) < -2:
                signals.append({
                    "strategy_id": self.strategy_id,
                    "symbol": symbol,
                    "action": "SELL",
                    "quantity": 10,
                    "price": current_price,
                    "reason": f"RSI overbought: {rsi:.2f}",
                    "timestamp": datetime.utcnow().isoformat()
                })
        
        return {"signals": signals} if signals else None
    
    def _calculate_rsi(self, symbol: str) -> Optional[float]:
        """Calculate RSI for symbol"""
        prices = self.price_history.get(symbol, [])
        if len(prices) < 14:
            return None
            
        gains, losses = [], []
        for i in range(1, len(prices)):
            change = prices[i]["price"] - prices[i-1]["price"]
            if change > 0:
                gains.append(change)
                losses.append(0)
            else:
                gains.append(0)
                losses.append(abs(change))
        
        if not gains or not losses:
            return None
            
        avg_gain = sum(gains) / len(gains)
        avg_loss = sum(losses) / len(losses)
        
        if avg_loss == 0:
            return 100
            
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        return rsi

class SwingMomentumStrategy(BaseStrategy):
    """Swing momentum strategy"""
    
    async def execute(self, market_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Execute swing momentum strategy"""
        signals = []
        
        for symbol in self.symbols:
            symbol_data = market_data.get(symbol, {})
            if not symbol_data:
                continue
                
            change_percent = symbol_data.get("change_percent", 0)
            volume = symbol_data.get("volume", 0)
            current_price = symbol_data.get("ltp", 0)
            
            # Momentum signals
            if change_percent > 4 and volume > 1000000:
                signals.append({
                    "strategy_id": self.strategy_id,
                    "symbol": symbol,
                    "action": "BUY",
                    "quantity": 5,
                    "price": current_price,
                    "reason": f"Strong momentum: {change_percent:.2f}%",
                    "timestamp": datetime.utcnow().isoformat()
                })
        
        return {"signals": signals} if signals else None

class BTSTMomentumStrategy(BaseStrategy):
    """Buy Today Sell Tomorrow momentum strategy"""
    
    async def execute(self, market_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Execute BTST strategy"""
        signals = []
        current_hour = datetime.now().hour
        
        # Only execute in last 2 hours of trading (2-4 PM)
        if current_hour < 14 or current_hour > 16:
            return None
            
        for symbol in self.symbols:
            symbol_data = market_data.get(symbol, {})
            if not symbol_data:
                continue
                
            change_percent = symbol_data.get("change_percent", 0)
            volume = symbol_data.get("volume", 0)
            current_price = symbol_data.get("ltp", 0)
            
            # Late day momentum
            if change_percent > 3 and volume > 2000000:
                signals.append({
                    "strategy_id": self.strategy_id,
                    "symbol": symbol,
                    "action": "BUY",
                    "quantity": 8,
                    "price": current_price,
                    "reason": f"BTST momentum: {change_percent:.2f}%",
                    "timestamp": datetime.utcnow().isoformat()
                })
        
        return {"signals": signals} if signals else None

class StrategyMarketplace:
    """Manages available strategies and user activations"""
    
    def __init__(self, redis_client):
        self.redis_client = redis_client
        self.available_strategies = {}
        self.user_strategies = {}
        self.strategy_instances = {}
        
    async def initialize(self):
        """Initialize marketplace with default strategies"""
        self.available_strategies = {
            "rsi_dmi": StrategyTemplate(
                strategy_id="rsi_dmi",
                name="RSI DMI Strategy",
                description="Entry: RSI > 70 + DMI confirmation | Exit: RSI < 30",
                category="Technical",
                risk_level="Medium",
                min_capital=50000.0,
                expected_return_annual=15.0,
                max_drawdown=8.0,
                symbols=["RELIANCE", "TCS", "INFY", "HDFC", "ICICIBANK"],
                parameters={"rsi_period": 14, "rsi_oversold": 30, "rsi_overbought": 70}
            ),
            "swing_momentum": StrategyTemplate(
                strategy_id="swing_momentum",
                name="Swing Momentum 4%",
                description="Entry: 4% momentum + bullish signals | Exit: 2 days or stop loss",
                category="Momentum",
                risk_level="High",
                min_capital=100000.0,
                expected_return_annual=25.0,
                max_drawdown=12.0,
                symbols=["RELIANCE", "TCS", "INFY", "HDFC", "ICICIBANK", "WIPRO"],
                parameters={"momentum_threshold": 4.0, "volume_threshold": 1000000}
            ),
            "btst_momentum": StrategyTemplate(
                strategy_id="btst_momentum",
                name="BTST Momentum",
                description="Entry: Late day momentum + volume | Exit: Next day morning",
                category="Intraday",
                risk_level="High",
                min_capital=200000.0,
                expected_return_annual=30.0,
                max_drawdown=15.0,
                symbols=["RELIANCE", "TCS", "INFY"],
                parameters={"late_day_threshold": 3.0, "volume_threshold": 2000000}
            )
        }
        
        # Create strategy instances
        for strategy_id, template in self.available_strategies.items():
            if strategy_id == "rsi_dmi":
                self.strategy_instances[strategy_id] = RSIDMIStrategy(strategy_id, template.parameters)
            elif strategy_id == "swing_momentum":
                self.strategy_instances[strategy_id] = SwingMomentumStrategy(strategy_id, template.parameters)
            elif strategy_id == "btst_momentum":
                self.strategy_instances[strategy_id] = BTSTMomentumStrategy(strategy_id, template.parameters)
        
        logger.info(f"✅ Initialized {len(self.available_strategies)} strategies")
    
    async def activate_user_strategy(self, user_id: str, strategy_id: str, allocation: float = 0.0) -> bool:
        """Activate strategy for user"""
        if strategy_id not in self.available_strategies:
            return False
            
        user_strategy = UserStrategy(
            user_id=user_id,
            strategy_id=strategy_id,
            status=StrategyStatus.ACTIVE,
            activated_at=datetime.utcnow().isoformat(),
            allocation_amount=allocation
        )
        
        if user_id not in self.user_strategies:
            self.user_strategies[user_id] = {}
        
        self.user_strategies[user_id][strategy_id] = user_strategy
        
        # Cache in Redis
        await self.redis_client.setex(
            f"user_strategy:{user_id}:{strategy_id}",
            86400,  # 24 hours
            json.dumps(user_strategy.__dict__)
        )
        
        logger.info(f"✅ Activated strategy {strategy_id} for user {user_id}")
        return True
    
    async def deactivate_user_strategy(self, user_id: str, strategy_id: str) -> bool:
        """Deactivate strategy for user"""
        if user_id in self.user_strategies and strategy_id in self.user_strategies[user_id]:
            self.user_strategies[user_id][strategy_id].status = StrategyStatus.PAUSED
            
            # Update in Redis
            await self.redis_client.delete(f"user_strategy:{user_id}:{strategy_id}")
            
            logger.info(f"🛑 Deactivated strategy {strategy_id} for user {user_id}")
            return True
        
        return False
    
    def get_marketplace_data(self) -> List[Dict]:
        """Get all available strategies for marketplace"""
        return [strategy.__dict__ for strategy in self.available_strategies.values()]
    
    def get_user_active_strategies(self, user_id: str) -> List[Dict]:
        """Get user's active strategies"""
        if user_id not in self.user_strategies:
            return []
        
        return [
            {**strategy.__dict__, **self.available_strategies[strategy.strategy_id].__dict__}
            for strategy in self.user_strategies[user_id].values()
            if strategy.status == StrategyStatus.ACTIVE
        ]
    
    async def execute_user_strategies(self, user_id: str, market_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Execute all active strategies for a user"""
        if user_id not in self.user_strategies:
            return []
        
        all_signals = []
        
        for strategy_id, user_strategy in self.user_strategies[user_id].items():
            if user_strategy.status != StrategyStatus.ACTIVE:
                continue
                
            strategy_instance = self.strategy_instances.get(strategy_id)
            if not strategy_instance:
                continue
            
            try:
                if await strategy_instance.should_execute(market_data):
                    result = await strategy_instance.execute(market_data)
                    if result and result.get("signals"):
                        # Add user context to signals
                        for signal in result["signals"]:
                            signal["user_id"] = user_id
                            signal["allocation_amount"] = user_strategy.allocation_amount
                        all_signals.extend(result["signals"])
                    
                    await strategy_instance.post_execute(result)
                    
            except Exception as e:
                logger.error(f"Error executing strategy {strategy_id} for user {user_id}: {e}")
        
        return all_signals

# Initialize FastAPI app
app = FastAPI(
    title="Strategy Engine Service",
    description="Strategy Execution and Marketplace Management",
    version="1.0.0"
)

# Global components
redis_client = None
marketplace = None
security = HTTPBearer()

# Authentication helper
async def verify_user_token(credentials: HTTPAuthorizationCredentials = Depends(security)) -> str:
    """Verify user token with user service"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{config.USER_SERVICE_URL}/dashboard",
                headers={"Authorization": f"Bearer {credentials.credentials}"}
            )
            if response.status_code == 200:
                user_data = response.json()
                return user_data.get("user_id")
            else:
                raise HTTPException(status_code=401, detail="Invalid token")
    except Exception as e:
        raise HTTPException(status_code=401, detail="Authentication failed")

@app.on_event("startup")
async def startup_event():
    """Initialize strategy service"""
    global redis_client, marketplace
    
    try:
        logger.info("🚀 Strategy Engine Service starting up...")
        
        # Connect to Redis
        redis_client = redis.from_url(config.REDIS_URL)
        await redis_client.ping()
        logger.info("✅ Redis connected")
        
        # Initialize marketplace
        marketplace = StrategyMarketplace(redis_client)
        await marketplace.initialize()
        
        logger.info("✅ Strategy Engine Service ready on port 8003")
        
    except Exception as e:
        logger.error(f"❌ Failed to initialize Strategy Engine Service: {e}")
        raise

@app.get("/health")
async def health_check():
    """Service health check"""
    try:
        await redis_client.ping()
        return {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "available_strategies": len(marketplace.available_strategies) if marketplace else 0
        }
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Service unhealthy: {e}")

@app.get("/marketplace")
async def get_marketplace():
    """Get all available strategies"""
    if not marketplace:
        raise HTTPException(status_code=503, detail="Strategy marketplace not initialized")
    
    strategies = marketplace.get_marketplace_data()
    return {
        "strategies": strategies,
        "total_strategies": len(strategies),
        "timestamp": datetime.utcnow().isoformat()
    }

@app.post("/user/activate/{strategy_id}")
async def activate_strategy(
    strategy_id: str,
    allocation_data: Dict[str, Any] = {},
    current_user: str = Depends(verify_user_token)
):
    """Activate strategy for user"""
    if not marketplace:
        raise HTTPException(status_code=503, detail="Strategy marketplace not initialized")
    
    allocation_amount = allocation_data.get("allocation_amount", 0.0)
    
    success = await marketplace.activate_user_strategy(current_user, strategy_id, allocation_amount)
    if success:
        return {
            "message": f"Strategy {strategy_id} activated successfully",
            "user_id": current_user,
            "strategy_id": strategy_id,
            "allocation_amount": allocation_amount
        }
    else:
        raise HTTPException(status_code=400, detail="Failed to activate strategy")

@app.post("/user/deactivate/{strategy_id}")
async def deactivate_strategy(
    strategy_id: str,
    current_user: str = Depends(verify_user_token)
):
    """Deactivate strategy for user"""
    if not marketplace:
        raise HTTPException(status_code=503, detail="Strategy marketplace not initialized")
    
    success = await marketplace.deactivate_user_strategy(current_user, strategy_id)
    if success:
        return {
            "message": f"Strategy {strategy_id} deactivated successfully",
            "user_id": current_user,
            "strategy_id": strategy_id
        }
    else:
        raise HTTPException(status_code=400, detail="Failed to deactivate strategy")

@app.get("/user/strategies")
async def get_user_strategies(current_user: str = Depends(verify_user_token)):
    """Get user's active strategies"""
    if not marketplace:
        raise HTTPException(status_code=503, detail="Strategy marketplace not initialized")
    
    strategies = marketplace.get_user_active_strategies(current_user)
    return {
        "user_id": current_user,
        "active_strategies": strategies,
        "count": len(strategies),
        "timestamp": datetime.utcnow().isoformat()
    }

@app.post("/execute/{user_id}")
async def execute_strategies_for_user(user_id: str, market_data: Dict[str, Any]):
    """Execute strategies for a specific user (internal endpoint)"""
    if not marketplace:
        raise HTTPException(status_code=503, detail="Strategy marketplace not initialized")
    
    signals = await marketplace.execute_user_strategies(user_id, market_data)
    return {
        "user_id": user_id,
        "signals": signals,
        "signal_count": len(signals),
        "timestamp": datetime.utcnow().isoformat()
    }

@app.get("/")
async def service_info():
    """Service information"""
    return {
        "service": "Strategy Engine Service",
        "version": "1.0.0",
        "status": "operational",
        "available_strategies": len(marketplace.available_strategies) if marketplace else 0,
        "endpoints": [
            "GET /marketplace",
            "POST /user/activate/{strategy_id}",
            "POST /user/deactivate/{strategy_id}",
            "GET /user/strategies",
            "POST /execute/{user_id}",
            "GET /health"
        ]
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8003) 