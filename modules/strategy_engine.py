#!/usr/bin/env python3
"""
Strategy Engine Module - Trading strategies and signals
Modular component for strategy operations
"""

import asyncio
import logging
import math
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum

logger = logging.getLogger(__name__)

class StrategyType(Enum):
    MOVING_AVERAGE = "MOVING_AVERAGE"
    RSI = "RSI"
    MACD = "MACD"
    BOLLINGER_BANDS = "BOLLINGER_BANDS"
    MEAN_REVERSION = "MEAN_REVERSION"
    MOMENTUM = "MOMENTUM"

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

class StrategyEngineModule:
    """Modular strategy engine"""
    
    def __init__(self):
        self.strategies: Dict[str, StrategyConfig] = {}
        self.signals: List[TradingSignal] = []
        self.price_history: Dict[str, List[float]] = {}
        
    async def initialize(self):
        """Initialize strategy engine module"""
        logger.info("🚀 Initializing Strategy Engine Module...")
        
        # Load default strategies
        await self._load_default_strategies()
        
        logger.info("✅ Strategy Engine Module initialized")
    
    async def _load_default_strategies(self):
        """Load default trading strategies"""
        default_strategies = [
            StrategyConfig(
                strategy_id="ma_crossover",
                strategy_type=StrategyType.MOVING_AVERAGE,
                symbols=["RELIANCE", "TCS", "INFY"],
                parameters={
                    "short_period": 10,
                    "long_period": 20,
                    "min_confidence": 0.7
                }
            ),
            StrategyConfig(
                strategy_id="rsi_strategy",
                strategy_type=StrategyType.RSI,
                symbols=["RELIANCE", "TCS", "INFY"],
                parameters={
                    "period": 14,
                    "oversold": 30,
                    "overbought": 70,
                    "min_confidence": 0.6
                }
            ),
            StrategyConfig(
                strategy_id="momentum_strategy",
                strategy_type=StrategyType.MOMENTUM,
                symbols=["RELIANCE", "TCS", "INFY"],
                parameters={
                    "period": 20,
                    "threshold": 0.02,
                    "min_confidence": 0.5
                }
            )
        ]
        
        for strategy in default_strategies:
            self.strategies[strategy.strategy_id] = strategy
    
    async def add_strategy(self, config: StrategyConfig):
        """Add a new strategy"""
        self.strategies[config.strategy_id] = config
        logger.info(f"Added strategy: {config.strategy_id}")
    
    async def run_strategy(self, strategy_id: str, market_data: Dict) -> List[TradingSignal]:
        """Run a specific strategy"""
        strategy = self.strategies.get(strategy_id)
        if not strategy or not strategy.enabled:
            return []
        
        signals = []
        
        for symbol in strategy.symbols:
            symbol_data = market_data.get(symbol)
            if not symbol_data:
                continue
            
            # Update price history
            await self._update_price_history(symbol, symbol_data["price"])
            
            # Run strategy based on type
            if strategy.strategy_type == StrategyType.MOVING_AVERAGE:
                signal = await self._moving_average_strategy(symbol, symbol_data, strategy.parameters)
            elif strategy.strategy_type == StrategyType.RSI:
                signal = await self._rsi_strategy(symbol, symbol_data, strategy.parameters)
            elif strategy.strategy_type == StrategyType.MOMENTUM:
                signal = await self._momentum_strategy(symbol, symbol_data, strategy.parameters)
            else:
                signal = None
            
            if signal:
                signals.append(signal)
        
        return signals
    
    async def run_all_strategies(self, market_data: Dict) -> List[TradingSignal]:
        """Run all enabled strategies"""
        all_signals = []
        
        for strategy_id in self.strategies:
            signals = await self.run_strategy(strategy_id, market_data)
            all_signals.extend(signals)
        
        return all_signals
    
    async def _moving_average_strategy(self, symbol: str, data: Dict, params: Dict) -> Optional[TradingSignal]:
        """Moving average crossover strategy"""
        try:
            prices = self.price_history.get(symbol, [])
            if len(prices) < params["long_period"]:
                return None
            
            short_period = params["short_period"]
            long_period = params["long_period"]
            
            # Calculate moving averages
            short_ma = sum(prices[-short_period:]) / short_period
            long_ma = sum(prices[-long_period:]) / long_period
            
            current_price = data["price"]
            signal_type = SignalType.HOLD
            confidence = 0.0
            
            # Generate signals
            if short_ma > long_ma and current_price > short_ma:
                signal_type = SignalType.BUY
                confidence = min(0.9, (short_ma - long_ma) / long_ma * 10)
            elif short_ma < long_ma and current_price < short_ma:
                signal_type = SignalType.SELL
                confidence = min(0.9, (long_ma - short_ma) / long_ma * 10)
            
            if confidence >= params.get("min_confidence", 0.7):
                return TradingSignal(
                    strategy_id="ma_crossover",
                    symbol=symbol,
                    signal_type=signal_type,
                    confidence=confidence,
                    price=current_price,
                    quantity=self._calculate_position_size(current_price, confidence),
                    timestamp=datetime.utcnow(),
                    metadata={
                        "short_ma": short_ma,
                        "long_ma": long_ma,
                        "crossover": short_ma - long_ma
                    }
                )
            
            return None
            
        except Exception as e:
            logger.error(f"Error in moving average strategy: {e}")
            return None
    
    async def _rsi_strategy(self, symbol: str, data: Dict, params: Dict) -> Optional[TradingSignal]:
        """RSI strategy"""
        try:
            prices = self.price_history.get(symbol, [])
            if len(prices) < params["period"]:
                return None
            
            # Calculate RSI
            rsi = self._calculate_rsi(prices, params["period"])
            
            current_price = data["price"]
            signal_type = SignalType.HOLD
            confidence = 0.0
            
            # Generate signals
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
            logger.error(f"Error in RSI strategy: {e}")
            return None
    
    async def _momentum_strategy(self, symbol: str, data: Dict, params: Dict) -> Optional[TradingSignal]:
        """Momentum strategy"""
        try:
            prices = self.price_history.get(symbol, [])
            if len(prices) < params["period"]:
                return None
            
            period = params["period"]
            threshold = params["threshold"]
            
            # Calculate momentum
            if len(prices) >= period:
                momentum = (prices[-1] - prices[-period]) / prices[-period]
            else:
                return None
            
            current_price = data["price"]
            signal_type = SignalType.HOLD
            confidence = 0.0
            
            # Generate signals
            if momentum > threshold:
                signal_type = SignalType.BUY
                confidence = min(0.9, momentum / threshold)
            elif momentum < -threshold:
                signal_type = SignalType.SELL
                confidence = min(0.9, abs(momentum) / threshold)
            
            if confidence >= params.get("min_confidence", 0.5):
                return TradingSignal(
                    strategy_id="momentum_strategy",
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
            logger.error(f"Error in momentum strategy: {e}")
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
        
        avg_gain = sum(gains[-period:]) / period
        avg_loss = sum(losses[-period:]) / period
        
        if avg_loss == 0:
            return 100.0
        
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        
        return rsi
    
    def _calculate_position_size(self, price: float, confidence: float) -> int:
        """Calculate position size based on confidence"""
        base_size = 100
        confidence_multiplier = confidence * 2  # 0-2x based on confidence
        return int(base_size * confidence_multiplier)
    
    async def _update_price_history(self, symbol: str, price: float):
        """Update price history for symbol"""
        if symbol not in self.price_history:
            self.price_history[symbol] = []
        
        self.price_history[symbol].append(price)
        
        # Keep only last 100 prices
        if len(self.price_history[symbol]) > 100:
            self.price_history[symbol] = self.price_history[symbol][-100:]
    
    async def get_strategies(self) -> List[Dict[str, Any]]:
        """Get all strategies"""
        return [
            {
                "strategy_id": config.strategy_id,
                "strategy_type": config.strategy_type.value,
                "symbols": config.symbols,
                "parameters": config.parameters,
                "enabled": config.enabled,
                "risk_level": config.risk_level,
                "max_position_size": config.max_position_size
            }
            for config in self.strategies.values()
        ]
    
    async def enable_strategy(self, strategy_id: str):
        """Enable a strategy"""
        if strategy_id in self.strategies:
            self.strategies[strategy_id].enabled = True
            logger.info(f"Enabled strategy: {strategy_id}")
    
    async def disable_strategy(self, strategy_id: str):
        """Disable a strategy"""
        if strategy_id in self.strategies:
            self.strategies[strategy_id].enabled = False
            logger.info(f"Disabled strategy: {strategy_id}")
    
    async def stop(self):
        """Stop strategy engine module"""
        logger.info("🔄 Strategy Engine Module stopped")

# Global strategy engine module instance
strategy_engine_module = StrategyEngineModule() 