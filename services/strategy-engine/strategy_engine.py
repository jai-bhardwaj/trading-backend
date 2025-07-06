#!/usr/bin/env python3
"""
Advanced Strategy Engine - Multi-strategy trading with backtesting
"""

import asyncio
import logging
import json
import time
import math
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable
from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
import redis.asyncio as redis
import httpx
import os
import numpy as np
from dataclasses import dataclass, field
from enum import Enum
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
from shared.common.error_handling import with_circuit_breaker, with_retry
from shared.common.security import AuditLogger
from shared.common.monitoring import MetricsCollector
from contextlib import asynccontextmanager

logger = logging.getLogger(__name__)

class StrategyType(Enum):
    MOVING_AVERAGE = "MOVING_AVERAGE"
    RSI = "RSI"
    MACD = "MACD"
    BOLLINGER_BANDS = "BOLLINGER_BANDS"
    MEAN_REVERSION = "MEAN_REVERSION"
    MOMENTUM = "MOMENTUM"
    ARBITRAGE = "ARBITRAGE"
    PAIRS_TRADING = "PAIRS_TRADING"

class SignalType(Enum):
    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"

@dataclass
class TradingSignal:
    """Trading signal from strategy"""
    strategy_id: str
    symbol: str
    signal_type: SignalType
    confidence: float  # 0.0 to 1.0
    price: float
    quantity: int
    timestamp: datetime
    metadata: Dict = field(default_factory=dict)

@dataclass
class StrategyConfig:
    """Strategy configuration"""
    strategy_id: str
    strategy_type: StrategyType
    symbols: List[str]
    parameters: Dict[str, Any]
    enabled: bool = True
    risk_level: str = "MEDIUM"
    max_position_size: float = 100000.0
    stop_loss_percent: float = 0.05
    take_profit_percent: float = 0.10

@dataclass
class BacktestResult:
    """Backtest result"""
    strategy_id: str
    total_return: float
    sharpe_ratio: float
    max_drawdown: float
    win_rate: float
    total_trades: int
    profit_factor: float
    start_date: datetime
    end_date: datetime
    trades: List[Dict]

class StrategyEngine:
    """Advanced strategy engine with multiple strategies"""
    
    def __init__(self, redis_client: redis.Redis):
        self.redis_client = redis_client
        self.strategies = {}
        self.active_signals = {}
        self.metrics_collector = MetricsCollector(redis_client)
        self.audit_logger = AuditLogger(redis_client)
        
        # Register strategy implementations
        self.strategy_implementations = {
            StrategyType.MOVING_AVERAGE: self._moving_average_strategy,
            StrategyType.RSI: self._rsi_strategy,
            StrategyType.MACD: self._macd_strategy,
            StrategyType.BOLLINGER_BANDS: self._bollinger_bands_strategy,
            StrategyType.MEAN_REVERSION: self._mean_reversion_strategy,
            StrategyType.MOMENTUM: self._momentum_strategy
        }
    
    async def initialize(self):
        """Initialize strategy engine"""
        # Load default strategies
        await self._load_default_strategies()
        logger.info("✅ Strategy Engine initialized")
    
    async def _load_default_strategies(self):
        """Load default trading strategies"""
        default_strategies = [
            StrategyConfig(
                strategy_id="ma_crossover",
                strategy_type=StrategyType.MOVING_AVERAGE,
                symbols=["RELIANCE", "TCS", "INFY"],
                parameters={
                    "short_window": 10,
                    "long_window": 50,
                    "min_confidence": 0.7
                }
            ),
            StrategyConfig(
                strategy_id="rsi_strategy",
                strategy_type=StrategyType.RSI,
                symbols=["RELIANCE", "TCS", "INFY", "HDFC"],
                parameters={
                    "period": 14,
                    "oversold": 30,
                    "overbought": 70,
                    "min_confidence": 0.6
                }
            ),
            StrategyConfig(
                strategy_id="bollinger_bands",
                strategy_type=StrategyType.BOLLINGER_BANDS,
                symbols=["RELIANCE", "TCS", "INFY"],
                parameters={
                    "period": 20,
                    "std_dev": 2,
                    "min_confidence": 0.65
                }
            )
        ]
        
        for strategy in default_strategies:
            await self.add_strategy(strategy)
    
    async def add_strategy(self, config: StrategyConfig):
        """Add a new trading strategy"""
        key = f"strategy:{config.strategy_id}"
        strategy_data = {
            "strategy_id": config.strategy_id,
            "strategy_type": config.strategy_type.value,
            "symbols": config.symbols,
            "parameters": config.parameters,
            "enabled": config.enabled,
            "risk_level": config.risk_level,
            "max_position_size": config.max_position_size,
            "stop_loss_percent": config.stop_loss_percent,
            "take_profit_percent": config.take_profit_percent
        }
        
        await self.redis_client.setex(
            key,
            86400 * 30,  # 30 days
            json.dumps(strategy_data)
        )
        
        self.strategies[config.strategy_id] = config
        logger.info(f"✅ Added strategy: {config.strategy_id}")
    
    async def run_strategy(self, strategy_id: str, market_data: Dict) -> List[TradingSignal]:
        """Run a specific strategy and generate signals"""
        try:
            if strategy_id not in self.strategies:
                raise ValueError(f"Strategy {strategy_id} not found")
            
            config = self.strategies[strategy_id]
            if not config.enabled:
                return []
            
            strategy_func = self.strategy_implementations.get(config.strategy_type)
            if not strategy_func:
                logger.error(f"❌ Strategy implementation not found: {config.strategy_type}")
                return []
            
            signals = []
            for symbol in config.symbols:
                if symbol in market_data:
                    signal = await strategy_func(symbol, market_data[symbol], config.parameters)
                    if signal:
                        signals.append(signal)
            
            # Record metrics
            await self.metrics_collector.record_metric(
                "strategy_signals",
                len(signals),
                {"strategy_id": strategy_id, "symbols": config.symbols}
            )
            
            return signals
            
        except Exception as e:
            logger.error(f"❌ Strategy execution error: {e}")
            return []
    
    async def run_all_strategies(self, market_data: Dict) -> List[TradingSignal]:
        """Run all active strategies"""
        all_signals = []
        
        for strategy_id in self.strategies:
            signals = await self.run_strategy(strategy_id, market_data)
            all_signals.extend(signals)
        
        return all_signals
    
    async def _moving_average_strategy(self, symbol: str, data: Dict, params: Dict) -> Optional[TradingSignal]:
        """Moving average crossover strategy"""
        try:
            prices = data.get("historical_prices", [])
            if len(prices) < params["long_window"]:
                return None
            
            # Calculate moving averages
            short_ma = np.mean(prices[-params["short_window"]:])
            long_ma = np.mean(prices[-params["long_window"]:])
            
            current_price = prices[-1]
            prev_short_ma = np.mean(prices[-params["short_window"]-1:-1])
            prev_long_ma = np.mean(prices[-params["long_window"]-1:-1])
            
            # Generate signal
            signal_type = SignalType.HOLD
            confidence = 0.0
            
            if short_ma > long_ma and prev_short_ma <= prev_long_ma:
                signal_type = SignalType.BUY
                confidence = min(0.9, abs(short_ma - long_ma) / current_price)
            elif short_ma < long_ma and prev_short_ma >= prev_long_ma:
                signal_type = SignalType.SELL
                confidence = min(0.9, abs(short_ma - long_ma) / current_price)
            
            if confidence >= params.get("min_confidence", 0.7):
                return TradingSignal(
                    strategy_id="ma_crossover",
                    symbol=symbol,
                    signal_type=signal_type,
                    confidence=confidence,
                    price=current_price,
                    quantity=self._calculate_position_size(current_price, confidence),
                    timestamp=datetime.utcnow(),
                    metadata={"short_ma": short_ma, "long_ma": long_ma}
                )
            
            return None
            
        except Exception as e:
            logger.error(f"❌ MA strategy error: {e}")
            return None
    
    async def _rsi_strategy(self, symbol: str, data: Dict, params: Dict) -> Optional[TradingSignal]:
        """RSI strategy"""
        try:
            prices = data.get("historical_prices", [])
            if len(prices) < params["period"]:
                return None
            
            # Calculate RSI
            rsi = self._calculate_rsi(prices, params["period"])
            
            current_price = prices[-1]
            signal_type = SignalType.HOLD
            confidence = 0.0
            
            if rsi < params["oversold"]:
                signal_type = SignalType.BUY
                confidence = (params["oversold"] - rsi) / params["oversold"]
            elif rsi > params["overbought"]:
                signal_type = SignalType.SELL
                confidence = (rsi - params["overbought"]) / (100 - params["overbought"])
            
            if confidence >= params.get("min_confidence", 0.6):
                return TradingSignal(
                    strategy_id="rsi_strategy",
                    symbol=symbol,
                    signal_type=signal_type,
                    confidence=confidence,
                    price=current_price,
                    quantity=self._calculate_position_size(current_price, confidence),
                    timestamp=datetime.utcnow(),
                    metadata={"rsi": rsi}
                )
            
            return None
            
        except Exception as e:
            logger.error(f"❌ RSI strategy error: {e}")
            return None
    
    async def _macd_strategy(self, symbol: str, data: Dict, params: Dict) -> Optional[TradingSignal]:
        """MACD strategy"""
        try:
            prices = data.get("historical_prices", [])
            if len(prices) < 26:
                return None
            
            # Calculate MACD
            ema12 = self._calculate_ema(prices, 12)
            ema26 = self._calculate_ema(prices, 26)
            macd_line = ema12 - ema26
            signal_line = self._calculate_ema([macd_line], 9)
            histogram = macd_line - signal_line
            
            current_price = prices[-1]
            signal_type = SignalType.HOLD
            confidence = 0.0
            
            if histogram > 0 and histogram > params.get("min_histogram", 0):
                signal_type = SignalType.BUY
                confidence = min(0.8, abs(histogram) / current_price)
            elif histogram < 0 and abs(histogram) > params.get("min_histogram", 0):
                signal_type = SignalType.SELL
                confidence = min(0.8, abs(histogram) / current_price)
            
            if confidence >= params.get("min_confidence", 0.6):
                return TradingSignal(
                    strategy_id="macd_strategy",
                    symbol=symbol,
                    signal_type=signal_type,
                    confidence=confidence,
                    price=current_price,
                    quantity=self._calculate_position_size(current_price, confidence),
                    timestamp=datetime.utcnow(),
                    metadata={"macd": macd_line, "signal": signal_line, "histogram": histogram}
                )
            
            return None
            
        except Exception as e:
            logger.error(f"❌ MACD strategy error: {e}")
            return None
    
    async def _bollinger_bands_strategy(self, symbol: str, data: Dict, params: Dict) -> Optional[TradingSignal]:
        """Bollinger Bands strategy"""
        try:
            prices = data.get("historical_prices", [])
            if len(prices) < params["period"]:
                return None
            
            # Calculate Bollinger Bands
            sma = np.mean(prices[-params["period"]:])
            std = np.std(prices[-params["period"]:])
            upper_band = sma + (params["std_dev"] * std)
            lower_band = sma - (params["std_dev"] * std)
            
            current_price = prices[-1]
            signal_type = SignalType.HOLD
            confidence = 0.0
            
            if current_price <= lower_band:
                signal_type = SignalType.BUY
                confidence = (lower_band - current_price) / lower_band
            elif current_price >= upper_band:
                signal_type = SignalType.SELL
                confidence = (current_price - upper_band) / upper_band
            
            if confidence >= params.get("min_confidence", 0.65):
                return TradingSignal(
                    strategy_id="bollinger_bands",
                    symbol=symbol,
                    signal_type=signal_type,
                    confidence=confidence,
                    price=current_price,
                    quantity=self._calculate_position_size(current_price, confidence),
                    timestamp=datetime.utcnow(),
                    metadata={"upper_band": upper_band, "lower_band": lower_band, "sma": sma}
                )
            
            return None
            
        except Exception as e:
            logger.error(f"❌ Bollinger Bands strategy error: {e}")
            return None
    
    async def _mean_reversion_strategy(self, symbol: str, data: Dict, params: Dict) -> Optional[TradingSignal]:
        """Mean reversion strategy"""
        try:
            prices = data.get("historical_prices", [])
            if len(prices) < 20:
                return None
            
            # Calculate mean and standard deviation
            mean_price = np.mean(prices[-20:])
            std_price = np.std(prices[-20:])
            current_price = prices[-1]
            
            # Calculate z-score
            z_score = (current_price - mean_price) / std_price
            
            signal_type = SignalType.HOLD
            confidence = 0.0
            
            if z_score < -1.5:  # Oversold
                signal_type = SignalType.BUY
                confidence = min(0.8, abs(z_score) / 3)
            elif z_score > 1.5:  # Overbought
                signal_type = SignalType.SELL
                confidence = min(0.8, abs(z_score) / 3)
            
            if confidence >= params.get("min_confidence", 0.6):
                return TradingSignal(
                    strategy_id="mean_reversion",
                    symbol=symbol,
                    signal_type=signal_type,
                    confidence=confidence,
                    price=current_price,
                    quantity=self._calculate_position_size(current_price, confidence),
                    timestamp=datetime.utcnow(),
                    metadata={"z_score": z_score, "mean": mean_price}
                )
            
            return None
            
        except Exception as e:
            logger.error(f"❌ Mean reversion strategy error: {e}")
            return None
    
    async def _momentum_strategy(self, symbol: str, data: Dict, params: Dict) -> Optional[TradingSignal]:
        """Momentum strategy"""
        try:
            prices = data.get("historical_prices", [])
            if len(prices) < 10:
                return None
            
            # Calculate momentum (rate of change)
            current_price = prices[-1]
            past_price = prices[-10]
            momentum = (current_price - past_price) / past_price
            
            signal_type = SignalType.HOLD
            confidence = 0.0
            
            if momentum > 0.05:  # 5% positive momentum
                signal_type = SignalType.BUY
                confidence = min(0.8, momentum / 0.2)
            elif momentum < -0.05:  # 5% negative momentum
                signal_type = SignalType.SELL
                confidence = min(0.8, abs(momentum) / 0.2)
            
            if confidence >= params.get("min_confidence", 0.6):
                return TradingSignal(
                    strategy_id="momentum",
                    symbol=symbol,
                    signal_type=signal_type,
                    confidence=confidence,
                    price=current_price,
                    quantity=self._calculate_position_size(current_price, confidence),
                    timestamp=datetime.utcnow(),
                    metadata={"momentum": momentum}
                )
            
            return None
            
        except Exception as e:
            logger.error(f"❌ Momentum strategy error: {e}")
            return None
    
    def _calculate_rsi(self, prices: List[float], period: int) -> float:
        """Calculate RSI"""
        if len(prices) < period + 1:
            return 50.0
        
        gains = []
        losses = []
        
        for i in range(1, len(prices)):
            change = prices[i] - prices[i-1]
            if change > 0:
                gains.append(change)
                losses.append(0)
            else:
                gains.append(0)
                losses.append(abs(change))
        
        avg_gain = np.mean(gains[-period:])
        avg_loss = np.mean(losses[-period:])
        
        if avg_loss == 0:
            return 100.0
        
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        
        return rsi
    
    def _calculate_ema(self, prices: List[float], period: int) -> float:
        """Calculate Exponential Moving Average"""
        if len(prices) < period:
            return prices[-1]
        
        alpha = 2 / (period + 1)
        ema = prices[0]
        
        for price in prices[1:]:
            ema = alpha * price + (1 - alpha) * ema
        
        return ema
    
    def _calculate_position_size(self, price: float, confidence: float) -> int:
        """Calculate position size based on confidence"""
        base_size = 100  # Base position size
        confidence_multiplier = 1 + confidence  # 1.0 to 2.0
        return int(base_size * confidence_multiplier)
    
    async def backtest_strategy(self, strategy_id: str, historical_data: Dict, 
                               start_date: datetime, end_date: datetime) -> BacktestResult:
        """Backtest a strategy"""
        try:
            if strategy_id not in self.strategies:
                raise ValueError(f"Strategy {strategy_id} not found")
            
            config = self.strategies[strategy_id]
            trades = []
            portfolio_value = 100000  # Starting capital
            max_portfolio_value = portfolio_value
            max_drawdown = 0
            
            # Simulate trading
            for date in self._date_range(start_date, end_date):
                if date.strftime("%Y-%m-%d") in historical_data:
                    day_data = historical_data[date.strftime("%Y-%m-%d")]
                    
                    # Run strategy for this day
                    signals = await self.run_strategy(strategy_id, day_data)
                    
                    for signal in signals:
                        if signal.signal_type in [SignalType.BUY, SignalType.SELL]:
                            # Execute trade
                            trade_value = signal.price * signal.quantity
                            
                            if signal.signal_type == SignalType.BUY:
                                portfolio_value -= trade_value
                            else:  # SELL
                                portfolio_value += trade_value
                            
                            trades.append({
                                "date": date.isoformat(),
                                "symbol": signal.symbol,
                                "action": signal.signal_type.value,
                                "price": signal.price,
                                "quantity": signal.quantity,
                                "value": trade_value,
                                "portfolio_value": portfolio_value
                            })
                            
                            # Update max portfolio value and drawdown
                            if portfolio_value > max_portfolio_value:
                                max_portfolio_value = portfolio_value
                            
                            current_drawdown = (max_portfolio_value - portfolio_value) / max_portfolio_value
                            if current_drawdown > max_drawdown:
                                max_drawdown = current_drawdown
            
            # Calculate metrics
            total_return = (portfolio_value - 100000) / 100000
            total_trades = len(trades)
            winning_trades = len([t for t in trades if t["value"] > 0])
            win_rate = winning_trades / total_trades if total_trades > 0 else 0
            
            # Calculate Sharpe ratio (simplified)
            returns = []
            for i in range(1, len(trades)):
                returns.append((trades[i]["portfolio_value"] - trades[i-1]["portfolio_value"]) / trades[i-1]["portfolio_value"])
            
            sharpe_ratio = np.mean(returns) / np.std(returns) if returns and np.std(returns) > 0 else 0
            
            # Calculate profit factor
            gross_profit = sum([t["value"] for t in trades if t["value"] > 0])
            gross_loss = abs(sum([t["value"] for t in trades if t["value"] < 0]))
            profit_factor = gross_profit / gross_loss if gross_loss > 0 else float('inf')
            
            return BacktestResult(
                strategy_id=strategy_id,
                total_return=total_return,
                sharpe_ratio=sharpe_ratio,
                max_drawdown=max_drawdown,
                win_rate=win_rate,
                total_trades=total_trades,
                profit_factor=profit_factor,
                start_date=start_date,
                end_date=end_date,
                trades=trades
            )
            
        except Exception as e:
            logger.error(f"❌ Backtest error: {e}")
            raise
    
    def _date_range(self, start_date: datetime, end_date: datetime):
        """Generate date range"""
        current_date = start_date
        while current_date <= end_date:
            yield current_date
            current_date += timedelta(days=1)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan events for the application"""
    # Startup
    global redis_client, strategy_engine
    
    try:
        logger.info("🚀 Strategy Engine starting up...")
        
        # Connect to Redis
        redis_client = redis.from_url("redis://localhost:6379/7")
        await redis_client.ping()
        logger.info("✅ Redis connected")
        
        # Initialize strategy engine
        strategy_engine = StrategyEngine(redis_client)
        await strategy_engine.initialize()
        
        logger.info("✅ Strategy Engine ready on port 8007")
        
    except Exception as e:
        logger.error(f"❌ Failed to initialize Strategy Engine: {e}")
        raise
    
    yield
    
    # Shutdown
    if redis_client:
        await redis_client.close()
        logger.info("✅ Strategy Engine shutdown complete")

# FastAPI app
app = FastAPI(
    title="Strategy Engine",
    description="Advanced Trading Strategy Engine",
    version="1.0.0",
    lifespan=lifespan
)

# Global components
redis_client = None
strategy_engine = None
security = HTTPBearer()

async def verify_user_token(credentials: HTTPAuthorizationCredentials = Depends(security)) -> str:
    """Verify user token"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                "http://localhost:8001/dashboard",
                headers={"Authorization": f"Bearer {credentials.credentials}"}
            )
            if response.status_code == 200:
                user_data = response.json()
                return user_data.get("user_id")
            else:
                raise HTTPException(status_code=401, detail="Invalid token")
    except Exception as e:
        raise HTTPException(status_code=401, detail="Authentication failed")

@app.get("/health")
async def health_check():
    """Service health check"""
    try:
        await redis_client.ping()
        return {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "active_strategies": len(strategy_engine.strategies) if strategy_engine else 0
        }
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Service unhealthy: {e}")

@app.post("/run-strategy")
async def run_strategy(
    strategy_id: str,
    market_data: Dict,
    current_user: str = Depends(verify_user_token)
):
    """Run a specific strategy"""
    if not strategy_engine:
        raise HTTPException(status_code=503, detail="Strategy engine not initialized")
    
    try:
        signals = await strategy_engine.run_strategy(strategy_id, market_data)
        return {
            "strategy_id": strategy_id,
            "signals": [
                {
                    "symbol": signal.symbol,
                    "signal_type": signal.signal_type.value,
                    "confidence": signal.confidence,
                    "price": signal.price,
                    "quantity": signal.quantity,
                    "timestamp": signal.timestamp.isoformat(),
                    "metadata": signal.metadata
                }
                for signal in signals
            ]
        }
        
    except Exception as e:
        logger.error(f"Error running strategy: {e}")
        raise HTTPException(status_code=500, detail="Failed to run strategy")

@app.post("/run-all-strategies")
async def run_all_strategies(
    market_data: Dict,
    current_user: str = Depends(verify_user_token)
):
    """Run all active strategies"""
    if not strategy_engine:
        raise HTTPException(status_code=503, detail="Strategy engine not initialized")
    
    try:
        signals = await strategy_engine.run_all_strategies(market_data)
        return {
            "total_signals": len(signals),
            "signals": [
                {
                    "strategy_id": signal.strategy_id,
                    "symbol": signal.symbol,
                    "signal_type": signal.signal_type.value,
                    "confidence": signal.confidence,
                    "price": signal.price,
                    "quantity": signal.quantity,
                    "timestamp": signal.timestamp.isoformat(),
                    "metadata": signal.metadata
                }
                for signal in signals
            ]
        }
        
    except Exception as e:
        logger.error(f"Error running all strategies: {e}")
        raise HTTPException(status_code=500, detail="Failed to run strategies")

@app.post("/backtest")
async def backtest_strategy(
    strategy_id: str,
    historical_data: Dict,
    start_date: str,
    end_date: str,
    current_user: str = Depends(verify_user_token)
):
    """Backtest a strategy"""
    if not strategy_engine:
        raise HTTPException(status_code=503, detail="Strategy engine not initialized")
    
    try:
        start_dt = datetime.fromisoformat(start_date)
        end_dt = datetime.fromisoformat(end_date)
        
        result = await strategy_engine.backtest_strategy(
            strategy_id, historical_data, start_dt, end_dt
        )
        
        return {
            "strategy_id": result.strategy_id,
            "total_return": result.total_return,
            "sharpe_ratio": result.sharpe_ratio,
            "max_drawdown": result.max_drawdown,
            "win_rate": result.win_rate,
            "total_trades": result.total_trades,
            "profit_factor": result.profit_factor,
            "start_date": result.start_date.isoformat(),
            "end_date": result.end_date.isoformat(),
            "trades": result.trades
        }
        
    except Exception as e:
        logger.error(f"Error backtesting strategy: {e}")
        raise HTTPException(status_code=500, detail="Failed to backtest strategy")

@app.post("/strategies")
async def add_strategy(
    strategy_config: Dict,
    current_user: str = Depends(verify_user_token)
):
    """Add a new strategy"""
    if not strategy_engine:
        raise HTTPException(status_code=503, detail="Strategy engine not initialized")
    
    try:
        config = StrategyConfig(
            strategy_id=strategy_config["strategy_id"],
            strategy_type=StrategyType(strategy_config["strategy_type"]),
            symbols=strategy_config["symbols"],
            parameters=strategy_config["parameters"],
            enabled=strategy_config.get("enabled", True),
            risk_level=strategy_config.get("risk_level", "MEDIUM"),
            max_position_size=strategy_config.get("max_position_size", 100000.0),
            stop_loss_percent=strategy_config.get("stop_loss_percent", 0.05),
            take_profit_percent=strategy_config.get("take_profit_percent", 0.10)
        )
        
        await strategy_engine.add_strategy(config)
        return {"message": "Strategy added successfully"}
        
    except Exception as e:
        logger.error(f"Error adding strategy: {e}")
        raise HTTPException(status_code=500, detail="Failed to add strategy")

@app.get("/strategies")
async def get_strategies(current_user: str = Depends(verify_user_token)):
    """Get all strategies"""
    if not strategy_engine:
        raise HTTPException(status_code=503, detail="Strategy engine not initialized")
    
    try:
        strategies = []
        for strategy_id, config in strategy_engine.strategies.items():
            strategies.append({
                "strategy_id": config.strategy_id,
                "strategy_type": config.strategy_type.value,
                "symbols": config.symbols,
                "parameters": config.parameters,
                "enabled": config.enabled,
                "risk_level": config.risk_level
            })
        
        return {"strategies": strategies}
        
    except Exception as e:
        logger.error(f"Error getting strategies: {e}")
        raise HTTPException(status_code=500, detail="Failed to get strategies")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8007) 