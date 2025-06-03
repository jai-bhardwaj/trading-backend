"""
Sample Momentum Strategy - Example Implementation

This strategy demonstrates how to:
1. Inherit from BaseStrategy
2. Implement required abstract methods
3. Use market data for signal generation
4. Manage positions and risk
"""

import asyncio
import logging
from typing import Dict, List, Any
from datetime import datetime, timedelta
from collections import defaultdict, deque

from app.strategies.base_strategy import BaseStrategy

logger = logging.getLogger(__name__)

class SampleMomentumStrategy(BaseStrategy):
    """
    Simple momentum strategy that:
    1. Monitors Bank Nifty and top bank stocks
    2. Calculates price momentum using moving averages
    3. Enters long positions on bullish momentum
    4. Exits positions on bearish momentum or stop loss
    """
    
    def __init__(self, strategy_id: str, config: Dict[str, Any], 
                 market_data_service, redis_client):
        super().__init__(strategy_id, config, market_data_service, redis_client)
        
        # Strategy-specific data
        self.price_history: Dict[str, deque] = defaultdict(lambda: deque(maxlen=20))
        self.last_signals: Dict[str, str] = {}  # Track last signal per instrument
        self.entry_prices: Dict[str, float] = {}
        
        # Strategy parameters
        self.momentum_period = config.get('momentum_period', 10)
        self.entry_threshold = config.get('entry_threshold', 0.5)  # % momentum threshold
        self.stop_loss_pct = config.get('stop_loss_pct', 2.0)  # % stop loss
        self.take_profit_pct = config.get('take_profit_pct', 3.0)  # % take profit
        self.max_positions = config.get('max_positions', 3)
        self.position_size = config.get('position_size', 10000)  # INR per position
        
        # Target instruments
        self.target_symbols = config.get('target_symbols', ['BANKNIFTY', 'BANK', 'NIFTY'])
        
    async def initialize(self):
        """Initialize the momentum strategy"""
        
        logger.info(f"🚀 Initializing Momentum Strategy")
        logger.info(f"   📊 Target symbols: {self.target_symbols}")
        logger.info(f"   📈 Momentum period: {self.momentum_period}")
        logger.info(f"   🎯 Entry threshold: {self.entry_threshold}%")
        logger.info(f"   🛡️  Stop loss: {self.stop_loss_pct}%")
        
        # Find instruments to monitor
        instruments_to_monitor = []
        
        for symbol in self.target_symbols:
            # Get equity instruments
            equity_instruments = await self.market_data_service.search_instruments(
                symbol, category='EQUITY', limit=5
            )
            instruments_to_monitor.extend(equity_instruments)
            
            # Get futures if available
            futures_instruments = await self.market_data_service.search_instruments(
                symbol, category='FUTURES', limit=2
            )
            instruments_to_monitor.extend(futures_instruments)
        
        # Subscribe to instruments
        tokens_to_subscribe = [inst['token'] for inst in instruments_to_monitor]
        await self.subscribe_to_instruments(tokens_to_subscribe)
        
        # Store instrument details for reference
        self.instruments = {inst['token']: inst for inst in instruments_to_monitor}
        
        logger.info(f"📡 Monitoring {len(tokens_to_subscribe)} instruments")
        
    async def on_market_data(self, token: str, data: Dict[str, Any]):
        """Process incoming market data"""
        
        ltp = data.get('ltp')
        if not ltp:
            return
        
        # Update price history
        self.price_history[token].append(ltp)
        
        # Calculate momentum if we have enough data
        if len(self.price_history[token]) >= self.momentum_period:
            momentum = self.calculate_momentum(token)
            
            # Store momentum in custom metrics
            if 'momentum' not in self.metrics['custom_metrics']:
                self.metrics['custom_metrics']['momentum'] = {}
            self.metrics['custom_metrics']['momentum'][token] = momentum
    
    def calculate_momentum(self, token: str) -> float:
        """Calculate price momentum as percentage change over period"""
        
        prices = list(self.price_history[token])
        if len(prices) < self.momentum_period:
            return 0.0
        
        # Simple momentum: % change from N periods ago
        old_price = prices[-self.momentum_period]
        current_price = prices[-1]
        
        momentum = ((current_price - old_price) / old_price) * 100
        return momentum
    
    async def generate_signals(self) -> List[Dict[str, Any]]:
        """Generate trading signals based on momentum"""
        
        signals = []
        
        for token in self.subscribed_tokens:
            if len(self.price_history[token]) < self.momentum_period:
                continue
            
            momentum = self.calculate_momentum(token)
            current_price = self.price_history[token][-1]
            instrument = self.instruments.get(token)
            
            if not instrument:
                continue
            
            # Check for entry signals
            if not self.is_position_open(token) and len(self.positions) < self.max_positions:
                
                # Bullish momentum signal
                if (momentum > self.entry_threshold and 
                    self.last_signals.get(token) != 'BUY'):
                    
                    # Calculate position size
                    quantity = max(1, int(self.position_size / current_price))
                    
                    signals.append({
                        'type': 'BUY',
                        'symbol': instrument['symbol'],
                        'token': token,
                        'quantity': quantity,
                        'price': current_price,
                        'reason': f'Bullish momentum: {momentum:.2f}%'
                    })
                    
                    self.last_signals[token] = 'BUY'
                    self.entry_prices[token] = current_price
            
            # Check for exit signals
            elif self.is_position_open(token):
                position = self.get_position(token)
                entry_price = position.avg_price
                
                # Stop loss
                loss_pct = ((current_price - entry_price) / entry_price) * 100
                if loss_pct <= -self.stop_loss_pct:
                    signals.append({
                        'type': 'SELL',
                        'symbol': instrument['symbol'],
                        'token': token,
                        'quantity': position.quantity,
                        'price': current_price,
                        'reason': f'Stop loss: {loss_pct:.2f}%'
                    })
                    self.last_signals[token] = 'SELL'
                
                # Take profit
                elif loss_pct >= self.take_profit_pct:
                    signals.append({
                        'type': 'SELL',
                        'symbol': instrument['symbol'],
                        'token': token,
                        'quantity': position.quantity,
                        'price': current_price,
                        'reason': f'Take profit: {loss_pct:.2f}%'
                    })
                    self.last_signals[token] = 'SELL'
                
                # Bearish momentum reversal
                elif (momentum < -self.entry_threshold and 
                      self.last_signals.get(token) != 'SELL'):
                    signals.append({
                        'type': 'SELL',
                        'symbol': instrument['symbol'],
                        'token': token,
                        'quantity': position.quantity,
                        'price': current_price,
                        'reason': f'Bearish momentum: {momentum:.2f}%'
                    })
                    self.last_signals[token] = 'SELL'
        
        # Log signals
        for signal in signals:
            logger.info(f"📊 Signal: {signal['type']} {signal['symbol']} "
                       f"x{signal['quantity']} @ {signal['price']:.2f} - {signal['reason']}")
        
        return signals
    
    async def on_strategy_iteration(self):
        """Called at the end of each strategy iteration"""
        
        # Log current status every 60 iterations (roughly 1 minute)
        if hasattr(self, '_iteration_count'):
            self._iteration_count += 1
        else:
            self._iteration_count = 1
        
        if self._iteration_count % 60 == 0:
            await self.log_strategy_status()
    
    async def log_strategy_status(self):
        """Log current strategy status"""
        
        portfolio_value = self.get_portfolio_value()
        total_pnl = self.metrics.get('total_pnl', 0)
        positions_count = len(self.positions)
        
        logger.info(f"📈 Strategy Status: Portfolio={portfolio_value:.2f} "
                   f"PnL={total_pnl:.2f} Positions={positions_count}")
        
        # Log top momentum instruments
        momentum_data = self.metrics['custom_metrics'].get('momentum', {})
        if momentum_data:
            sorted_momentum = sorted(momentum_data.items(), 
                                   key=lambda x: x[1], reverse=True)[:3]
            
            logger.info("🔥 Top momentum instruments:")
            for token, momentum in sorted_momentum:
                instrument = self.instruments.get(token)
                if instrument:
                    logger.info(f"   {instrument['symbol']}: {momentum:.2f}%")
    
    async def on_position_opened(self, position):
        """Called when a new position is opened"""
        logger.info(f"📍 Position opened: {position.symbol} "
                   f"x{position.quantity} @ {position.avg_price:.2f}")
    
    async def on_position_closed(self, position, pnl: float):
        """Called when a position is closed"""
        await super().on_position_closed(position, pnl)
        
        pnl_pct = (pnl / (position.avg_price * position.quantity)) * 100
        status = "✅ WIN" if pnl > 0 else "❌ LOSS"
        
        logger.info(f"🔚 Position closed: {position.symbol} "
                   f"PnL={pnl:.2f} ({pnl_pct:.2f}%) {status}")
    
    def get_strategy_info(self) -> Dict[str, Any]:
        """Get strategy-specific information"""
        
        momentum_data = self.metrics['custom_metrics'].get('momentum', {})
        
        # Get current momentum for monitored instruments
        current_momentum = []
        for token, momentum in momentum_data.items():
            instrument = self.instruments.get(token)
            if instrument:
                current_momentum.append({
                    'symbol': instrument['symbol'],
                    'token': token,
                    'momentum': momentum,
                    'price': self.price_history[token][-1] if self.price_history[token] else 0,
                    'has_position': self.is_position_open(token)
                })
        
        # Sort by momentum
        current_momentum.sort(key=lambda x: x['momentum'], reverse=True)
        
        return {
            'strategy_type': 'momentum',
            'parameters': {
                'momentum_period': self.momentum_period,
                'entry_threshold': self.entry_threshold,
                'stop_loss_pct': self.stop_loss_pct,
                'take_profit_pct': self.take_profit_pct,
                'max_positions': self.max_positions,
                'position_size': self.position_size
            },
            'monitored_instruments': len(self.subscribed_tokens),
            'current_momentum': current_momentum[:10],  # Top 10
            'risk_metrics': self.get_risk_metrics()
        } 