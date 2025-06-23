"""
Real-time Strategy Management System with Signal Generation
High-performance trading strategies with technical analysis
"""

import asyncio
import json
import logging
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Callable
import redis.asyncio as redis
from sqlalchemy import select, update, delete
from sqlalchemy.orm import sessionmaker
import os

from .database import get_db_manager
from .signals import TradingSignal, SignalAction, OrderType, ProductType, create_market_buy_signal, create_limit_order_signal
from decimal import Decimal

logger = logging.getLogger(__name__)

class BaseStrategy:
    """Base strategy class with common functionality and smart memory management"""
    
    def __init__(self, strategy_id: str, name: str, symbols: List[str]):
        self.strategy_id = strategy_id
        self.name = name
        self.symbols = symbols
        self.last_signals = {}
        self.positions = {}
        
        # Use smart memory management instead of direct price_history
        from .memory_manager import get_smart_price_history
        self.smart_memory = get_smart_price_history()
        
        # Register our symbols with the memory manager
        self.smart_memory.register_strategy_symbols(symbols)
        
        # Strategy parameters (can be overridden)
        self.lookback_period = 20
        self.signal_cooldown = 300  # 5 minutes between signals per symbol
        
        logger.info(f"📈 Strategy {self.name} initialized with smart memory management for {len(symbols)} symbols")
        
    async def execute(self, market_data: Dict[str, Dict[str, Any]]) -> List[TradingSignal]:
        """Execute strategy and generate signals"""
        signals = []
        
        try:
            # Update price history with smart memory management
            self._update_price_history_smart(market_data)
            
            # Generate signals for each symbol
            for symbol in self.symbols:
                if symbol in market_data:
                    symbol_signals = await self._generate_symbol_signals(symbol, market_data[symbol])
                    signals.extend(symbol_signals)
            
            return signals
            
        except Exception as e:
            logger.error(f"❌ Error in strategy {self.name}: {e}")
            return []
    
    def _update_price_history_smart(self, market_data: Dict[str, Dict[str, Any]]):
        """Update price history using smart memory management - MEMORY LEAK FIX"""
        # Only process symbols we actually care about
        for symbol in self.symbols:
            if symbol in market_data:
                data = market_data[symbol]
                ltp = data.get('ltp', 0)
                if ltp > 0:
                    # Use smart memory manager - it handles cleanup automatically
                    self.smart_memory.add_price_point(
                        symbol=symbol,
                        price=float(ltp),
                        volume=data.get('volume', 0)
                    )
    
    def _update_price_history(self, market_data: Dict[str, Dict[str, Any]]):
        """DEPRECATED: Old method with memory leak - DO NOT USE"""
        logger.warning("⚠️ Using deprecated _update_price_history - this causes memory leaks!")
        # This method intentionally left empty to prevent usage
    
    async def _generate_symbol_signals(self, symbol: str, data: Dict[str, Any]) -> List[TradingSignal]:
        """Generate signals for specific symbol - to be implemented by subclasses"""
        return []
    
    def _can_generate_signal(self, symbol: str) -> bool:
        """Check if enough time has passed since last signal"""
        if symbol not in self.last_signals:
            return True
        
        last_signal_time = self.last_signals[symbol]
        return (datetime.now() - last_signal_time).total_seconds() > self.signal_cooldown
    
    def _record_signal(self, symbol: str):
        """Record that a signal was generated"""
        self.last_signals[symbol] = datetime.now()

class RSIMomentumStrategy(BaseStrategy):
    """RSI-based momentum strategy"""
    
    def __init__(self):
        super().__init__(
            strategy_id="rsi_momentum", 
            name="RSI Momentum Strategy",
            symbols=["RELIANCE", "TCS", "INFY", "HDFC", "ICICIBANK"]
        )
        self.rsi_period = 14
        self.rsi_oversold = 30
        self.rsi_overbought = 70
        
    async def _generate_symbol_signals(self, symbol: str, data: Dict[str, Any]) -> List[TradingSignal]:
        """Generate RSI-based signals"""
        signals = []
        
        try:
            if not self._can_generate_signal(symbol):
                return signals
            
            # Calculate RSI
            rsi = self._calculate_rsi(symbol)
            if rsi is None:
                return signals
            
            current_price = float(data.get('ltp', 0))
            if current_price <= 0:
                return signals
            
            # Generate buy signal on RSI oversold
            if rsi < self.rsi_oversold and symbol not in self.positions:
                quantity = self._calculate_position_size(current_price)
                
                signal = create_market_buy_signal(
                    symbol=symbol,
                    exchange="NSE",
                    quantity=quantity,
                    strategy_id=self.strategy_id,
                    strategy_name=self.name
                )
                
                signals.append(signal)
                self.positions[symbol] = 'LONG'
                self._record_signal(symbol)
                
                logger.info(f"🔥 RSI BUY Signal: {symbol} @ ₹{current_price:.2f} (RSI: {rsi:.1f})")
            
            # Generate sell signal on RSI overbought  
            elif rsi > self.rsi_overbought and self.positions.get(symbol) == 'LONG':
                quantity = self._calculate_position_size(current_price)
                
                signal = TradingSignal(
                    symbol=symbol,
                    exchange="NSE", 
                    action=SignalAction.SELL,
                    quantity=quantity
                )
                signal.strategy.strategy_id = self.strategy_id
                signal.strategy.strategy_name = self.name
                signal.order_spec.order_type = OrderType.MARKET
                signal.order_spec.product_type = ProductType.INTRADAY
                
                signals.append(signal)
                self.positions[symbol] = None
                self._record_signal(symbol)
                
                logger.info(f"💰 RSI SELL Signal: {symbol} @ ₹{current_price:.2f} (RSI: {rsi:.1f})")
            
            return signals
            
        except Exception as e:
            logger.error(f"❌ Error generating RSI signal for {symbol}: {e}")
            return []
    
    def _calculate_rsi(self, symbol: str) -> Optional[float]:
        """Calculate RSI indicator using smart memory management"""
        # Get prices from smart memory manager
        prices = self.smart_memory.get_prices_only(symbol, self.rsi_period + 1)
        
        if len(prices) < self.rsi_period + 1:
            return None
        
        deltas = np.diff(prices)
        
        gains = np.where(deltas > 0, deltas, 0)
        losses = np.where(deltas < 0, -deltas, 0)
        
        avg_gain = np.mean(gains)
        avg_loss = np.mean(losses)
        
        # SAFE DIVISION WITH PROPER THRESHOLD (Fixed division by zero)
        zero_threshold = 1e-8
        
        if avg_loss < zero_threshold:
            if avg_gain > zero_threshold:
                logger.info(f"RSI({symbol}): Only gains detected, returning 100")
                return 100.0
            else:
                logger.info(f"RSI({symbol}): No significant price movement, returning 50")
                return 50.0
        
        if avg_gain < zero_threshold:
            logger.info(f"RSI({symbol}): Only losses detected, returning 0")
            return 0.0
        
        # Safe RS calculation
        rs = avg_gain / avg_loss
        
        # Protect against extreme values
        if rs > 1e6:
            logger.warning(f"RSI({symbol}): Extremely high RS value, returning 100")
            return 100.0
        
        rsi = 100 - (100 / (1 + rs))
        
        # Ensure valid range
        return max(0.0, min(100.0, rsi))
    
    def _calculate_position_size(self, price: float) -> int:
        """Calculate position size based on price"""
        # Simple position sizing: ₹10,000 per trade
        trade_value = 10000
        quantity = max(1, int(trade_value / price))
        return quantity

class MovingAverageCrossStrategy(BaseStrategy):
    """Moving average crossover strategy"""
    
    def __init__(self):
        super().__init__(
            strategy_id="ma_cross",
            name="MA Cross Strategy", 
            symbols=["SBIN", "LT", "ITC", "AXISBANK", "HDFCBANK"]
        )
        self.fast_period = 5
        self.slow_period = 20
        
    async def _generate_symbol_signals(self, symbol: str, data: Dict[str, Any]) -> List[TradingSignal]:
        """Generate MA crossover signals"""
        signals = []
        
        try:
            if not self._can_generate_signal(symbol):
                return signals
            
            # Calculate moving averages
            fast_ma = self._calculate_ma(symbol, self.fast_period)
            slow_ma = self._calculate_ma(symbol, self.slow_period)
            
            if fast_ma is None or slow_ma is None:
                return signals
            
            current_price = float(data.get('ltp', 0))
            if current_price <= 0:
                return signals
            
            # Previous MAs for crossover detection
            prev_fast_ma = self._calculate_ma(symbol, self.fast_period, offset=1)
            prev_slow_ma = self._calculate_ma(symbol, self.slow_period, offset=1)
            
            if prev_fast_ma is None or prev_slow_ma is None:
                return signals
            
            # Bullish crossover: fast MA crosses above slow MA
            if (fast_ma > slow_ma and prev_fast_ma <= prev_slow_ma and 
                symbol not in self.positions):
                
                quantity = self._calculate_position_size(current_price)
                
                signal = create_market_buy_signal(
                    symbol=symbol,
                    exchange="NSE",
                    quantity=quantity,
                    strategy_id=self.strategy_id,
                    strategy_name=self.name
                )
                
                signals.append(signal)
                self.positions[symbol] = 'LONG'
                self._record_signal(symbol)
                
                logger.info(f"📈 MA Cross BUY: {symbol} @ ₹{current_price:.2f} (Fast: {fast_ma:.2f}, Slow: {slow_ma:.2f})")
            
            # Bearish crossover: fast MA crosses below slow MA
            elif (fast_ma < slow_ma and prev_fast_ma >= prev_slow_ma and 
                  self.positions.get(symbol) == 'LONG'):
                
                quantity = self._calculate_position_size(current_price)
                
                signal = TradingSignal(
                    symbol=symbol,
                    exchange="NSE",
                    action=SignalAction.SELL,
                    quantity=quantity
                )
                signal.strategy.strategy_id = self.strategy_id
                signal.strategy.strategy_name = self.name
                signal.order_spec.order_type = OrderType.MARKET
                signal.order_spec.product_type = ProductType.INTRADAY
                
                signals.append(signal)
                self.positions[symbol] = None
                self._record_signal(symbol)
                
                logger.info(f"📉 MA Cross SELL: {symbol} @ ₹{current_price:.2f} (Fast: {fast_ma:.2f}, Slow: {slow_ma:.2f})")
            
            return signals
            
        except Exception as e:
            logger.error(f"❌ Error generating MA signal for {symbol}: {e}")
            return []
    
    def _calculate_ma(self, symbol: str, period: int, offset: int = 0) -> Optional[float]:
        """Calculate moving average using smart memory management"""
        # Get prices from smart memory manager
        all_prices = self.smart_memory.get_prices_only(symbol)
        
        if len(all_prices) < period + offset:
            return None
        
        end_idx = len(all_prices) - offset
        start_idx = end_idx - period
        
        if start_idx < 0:
            return None
        
        prices = all_prices[start_idx:end_idx]
        return np.mean(prices) if prices else None
    
    def _calculate_position_size(self, price: float) -> int:
        """Calculate position size based on price"""
        trade_value = 15000  # ₹15,000 per trade
        quantity = max(1, int(trade_value / price))
        return quantity

class MeanReversionStrategy(BaseStrategy):
    """Mean reversion strategy using Bollinger Bands"""
    
    def __init__(self):
        super().__init__(
            strategy_id="mean_reversion",
            name="Mean Reversion Strategy",
            symbols=["RELIANCE", "HDFC", "TCS", "INFY", "ICICIBANK"]
        )
        self.bb_period = 20
        self.bb_std = 2.0
        
    async def _generate_symbol_signals(self, symbol: str, data: Dict[str, Any]) -> List[TradingSignal]:
        """Generate mean reversion signals using Bollinger Bands"""
        signals = []
        
        try:
            if not self._can_generate_signal(symbol):
                return signals
            
            # Calculate Bollinger Bands
            bb_upper, bb_middle, bb_lower = self._calculate_bollinger_bands(symbol)
            
            if bb_upper is None:
                return signals
            
            current_price = float(data.get('ltp', 0))
            if current_price <= 0:
                return signals
            
            # Buy signal: price touches lower band (oversold)
            if current_price <= bb_lower and symbol not in self.positions:
                quantity = self._calculate_position_size(current_price)
                
                signal = create_market_buy_signal(
                    symbol=symbol,
                    exchange="NSE",
                    quantity=quantity,
                    strategy_id=self.strategy_id,
                    strategy_name=self.name
                )
                
                signals.append(signal)
                self.positions[symbol] = 'LONG'
                self._record_signal(symbol)
                
                logger.info(f"🎯 Mean Reversion BUY: {symbol} @ ₹{current_price:.2f} (BB Lower: {bb_lower:.2f})")
            
            # Sell signal: price touches upper band (overbought) 
            elif current_price >= bb_upper and self.positions.get(symbol) == 'LONG':
                quantity = self._calculate_position_size(current_price)
                
                signal = TradingSignal(
                    symbol=symbol,
                    exchange="NSE",
                    action=SignalAction.SELL,
                    quantity=quantity
                )
                signal.strategy.strategy_id = self.strategy_id
                signal.strategy.strategy_name = self.name
                signal.order_spec.order_type = OrderType.MARKET
                signal.order_spec.product_type = ProductType.INTRADAY
                
                signals.append(signal)
                self.positions[symbol] = None
                self._record_signal(symbol)
                
                logger.info(f"💎 Mean Reversion SELL: {symbol} @ ₹{current_price:.2f} (BB Upper: {bb_upper:.2f})")
            
            return signals
            
        except Exception as e:
            logger.error(f"❌ Error generating mean reversion signal for {symbol}: {e}")
            return []
    
    def _calculate_bollinger_bands(self, symbol: str) -> tuple:
        """Calculate Bollinger Bands using smart memory management"""
        # Get prices from smart memory manager
        prices = self.smart_memory.get_prices_only(symbol, self.bb_period)
        
        if len(prices) < self.bb_period:
            return None, None, None
        
        middle = np.mean(prices)
        std = np.std(prices)
        
        upper = middle + (self.bb_std * std)
        lower = middle - (self.bb_std * std)
        
        return upper, middle, lower
    
    def _calculate_position_size(self, price: float) -> int:
        """Calculate position size based on price"""
        trade_value = 12000  # ₹12,000 per trade
        quantity = max(1, int(trade_value / price))
        return quantity

class RealTimeStrategyManager:
    """
    Real-time strategy management with signal generation
    """
    
    def __init__(self, database_url: str = None, redis_url: str = "redis://localhost:6379/0"):
        self.database_url = database_url or os.getenv('DATABASE_URL')
        self.db_manager = get_db_manager(database_url)
        self.redis_url = redis_url
        self.redis_client = None
        self.redis_subscriber = None
        
        # Strategy instances 
        self.active_strategies = {
            'rsi_momentum': RSIMomentumStrategy(),
            'ma_cross': MovingAverageCrossStrategy(),
            'mean_reversion': MeanReversionStrategy()
        }
        
        # In-memory cache for ultra-fast access
        self.strategy_cache: Dict[str, Dict[str, Any]] = {}
        self.cache_version = 0
        
        # Callbacks for strategy changes
        self.change_callbacks: List[Callable] = []
        
        # Control flags
        self.is_running = False
        self._monitor_task = None
        
        logger.info(f"🏗️ RealTimeStrategyManager initialized with {len(self.active_strategies)} strategies")
        
    async def initialize(self):
        """Initialize the real-time strategy manager"""
        try:
            # Initialize database tables (shared instance)
            self.db_manager.create_tables()
            
            # Initialize Redis
            try:
                self.redis_client = redis.from_url(self.redis_url, decode_responses=True)
                await self.redis_client.ping()
                logger.info("✅ Redis connection established for strategy cache")
            except Exception as e:
                logger.warning(f"⚠️ Redis connection failed: {e}")
                logger.info("📝 Strategy cache will work without Redis pub/sub")
                self.redis_client = None
            
            # Load initial strategies from database
            await self.reload_strategies_from_db()
            
            # Start real-time monitoring
            await self.start_monitoring()
            
            logger.info("🚀 Real-time Strategy Manager initialized")
            logger.info(f"📊 Loaded {len(self.strategy_cache)} strategies from shared DB pool")
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize strategy manager: {e}")
            raise
    
    async def execute_strategies(self, market_data: Dict[str, Dict[str, Any]]) -> List[TradingSignal]:
        """Execute all active strategies and collect signals"""
        all_signals = []
        
        try:
            for strategy_id, strategy in self.active_strategies.items():
                try:
                    signals = await strategy.execute(market_data)
                    all_signals.extend(signals)
                    
                    if signals:
                        logger.info(f"📈 Strategy {strategy_id} generated {len(signals)} signals")
                        
                except Exception as e:
                    logger.error(f"❌ Error executing strategy {strategy_id}: {e}")
            
            return all_signals
            
        except Exception as e:
            logger.error(f"❌ Error in strategy execution: {e}")
            return []
    
    async def reload_strategies_from_db(self):
        """Reload all strategies from database using shared connection pool"""
        try:
            session = self.db_manager.get_session()
            
            try:
                # For now, load hardcoded strategies since we don't have TradingStrategyConfig table
                # In production, this would query the database
                hardcoded_strategies = {
                    'rsi_momentum': {
                        'id': 'rsi_momentum',
                        'name': 'RSI Momentum Strategy',
                        'class_name': 'RSIMomentumStrategy',
                        'module_path': 'src.core.strategies',
                        'config': {},
                        'status': 'ACTIVE',
                        'auto_start': True,
                        'updated_at': datetime.now().isoformat()
                    },
                    'ma_cross': {
                        'id': 'ma_cross',
                        'name': 'MA Cross Strategy',
                        'class_name': 'MovingAverageCrossStrategy',
                        'module_path': 'src.core.strategies',
                        'config': {},
                        'status': 'ACTIVE',
                        'auto_start': True,
                        'updated_at': datetime.now().isoformat()
                    },
                    'mean_reversion': {
                        'id': 'mean_reversion',
                        'name': 'Mean Reversion Strategy',
                        'class_name': 'MeanReversionStrategy',
                        'module_path': 'src.core.strategies',
                        'config': {},
                        'status': 'ACTIVE',
                        'auto_start': True,
                        'updated_at': datetime.now().isoformat()
                    }
                }
                
                # Update cache
                old_cache = self.strategy_cache.copy()
                self.strategy_cache = hardcoded_strategies.copy()
                
                # Increment cache version
                self.cache_version += 1
                
                # Log changes
                added = set(self.strategy_cache.keys()) - set(old_cache.keys())
                removed = set(old_cache.keys()) - set(self.strategy_cache.keys())
                updated = []
                
                for name in set(self.strategy_cache.keys()) & set(old_cache.keys()):
                    if self.strategy_cache[name]['updated_at'] != old_cache[name]['updated_at']:
                        updated.append(name)
                
                if added or removed or updated:
                    logger.info(f"🔄 Strategy cache updated:")
                    if added:
                        logger.info(f"   ➕ Added: {list(added)}")
                    if removed:
                        logger.info(f"   ➖ Removed: {list(removed)}")
                    if updated:
                        logger.info(f"   🔧 Updated: {updated}")
                    
                    # Notify callbacks of changes
                    await self._notify_callbacks('strategies_reloaded', {
                        'added': list(added),
                        'removed': list(removed),
                        'updated': updated,
                        'cache_version': self.cache_version,
                        'pool_status': self.db_manager.get_pool_status()
                    })
                
            finally:
                session.close()
            
        except Exception as e:
            logger.error(f"❌ Failed to reload strategies: {e}")
            raise
    
    async def start_monitoring(self):
        """Start real-time monitoring for strategy changes"""
        if self.is_running:
            return
        
        self.is_running = True
        
        # Start Redis pub/sub monitoring
        self._monitor_task = asyncio.create_task(self._monitor_strategy_changes())
        
        logger.info("🔍 Real-time strategy monitoring started")
    
    async def stop_monitoring(self):
        """Stop real-time monitoring"""
        self.is_running = False
        
        if self._monitor_task:
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                pass
        
        if self.redis_subscriber:
            await self.redis_subscriber.close()
        
        logger.info("⏹️ Real-time strategy monitoring stopped")
    
    async def _monitor_strategy_changes(self):
        """Monitor Redis pub/sub for strategy changes"""
        if not self.redis_client:
            logger.info("📝 Redis pub/sub monitoring disabled (Redis not available)")
            return
            
        try:
            pubsub = self.redis_client.pubsub()
            await pubsub.subscribe('strategy_changes')
            logger.info("👂 Listening for strategy changes on Redis pub/sub...")
            
            async for message in pubsub.listen():
                if message['type'] == 'message':
                    try:
                        data = json.loads(message['data'])
                        await self._handle_strategy_change(data)
                    except Exception as e:
                        logger.error(f"❌ Error processing strategy change: {e}")
        except Exception as e:
            logger.warning(f"⚠️ Redis pub/sub monitoring failed: {e}")
            logger.info("📝 Strategy changes will be detected through other means")
    
    async def _handle_strategy_change(self, change_data: Dict[str, Any]):
        """Handle a strategy change notification"""
        try:
            change_type = change_data.get('type')
            strategy_name = change_data.get('strategy_name')
            
            logger.info(f"🔔 Strategy change received: {change_type} for {strategy_name}")
            
            # Reload strategies from database
            await self.reload_strategies_from_db()
            
        except Exception as e:
            logger.error(f"❌ Error handling strategy change: {e}")
    
    async def _notify_callbacks(self, event_type: str, data: Dict[str, Any]):
        """Notify registered callbacks of changes"""
        for callback in self.change_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(event_type, data)
                else:
                    callback(event_type, data)
            except Exception as e:
                logger.error(f"❌ Error in strategy change callback: {e}")
    
    def register_change_callback(self, callback: Callable):
        """Register callback for strategy changes"""
        self.change_callbacks.append(callback)
        logger.info(f"📝 Registered strategy change callback: {callback.__name__}")
    
    def get_strategy(self, name: str) -> Optional[Dict[str, Any]]:
        """Get strategy by name"""
        return self.strategy_cache.get(name)
    
    def get_all_strategies(self) -> Dict[str, Dict[str, Any]]:
        """Get all cached strategies"""
        return self.strategy_cache.copy()
    
    def get_active_strategies(self) -> Dict[str, Dict[str, Any]]:
        """Get only active strategies"""
        return {
            name: data for name, data in self.strategy_cache.items()
            if data.get('status') == 'ACTIVE'
        }
    
    def get_cache_version(self) -> int:
        """Get current cache version"""
        return self.cache_version
    
    async def force_reload(self) -> int:
        """Force reload strategies and return new cache version"""
        await self.reload_strategies_from_db()
        return self.cache_version
    
    def get_db_pool_status(self) -> Dict[str, Any]:
        """Get database pool status from shared manager"""
        return self.db_manager.get_pool_status() 