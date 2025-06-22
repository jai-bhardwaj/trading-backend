"""
Real-time Strategy Manager for Live Trading
Handles strategy execution with live market data and real orders
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
import json

from .strategy_manager import StrategyManager
from .strategies import BaseStrategy as TradingStrategy
from .market_data import AngelOneRealTimeManager as MarketDataManager
from .broker_manager import BrokerManager
from .events import EventBus as EventManager

logger = logging.getLogger(__name__)

class RealTimeStrategyManager:
    """
    Real-time strategy manager for live trading
    Executes strategies with live market data and places real orders
    """
    
    def __init__(self, market_data_manager: MarketDataManager, 
                 broker_manager: BrokerManager, event_manager: EventManager):
        self.market_data_manager = market_data_manager
        self.broker_manager = broker_manager
        self.event_manager = event_manager
        self.strategy_manager = StrategyManager()
        self.active_strategies: Dict[str, TradingStrategy] = {}
        self.is_running = False
        
        logger.info("🚀 RealTimeStrategyManager initialized for LIVE TRADING")
    
    def add_strategy(self, strategy_id: str, strategy: TradingStrategy):
        """Add a strategy for real-time execution"""
        self.active_strategies[strategy_id] = strategy
        logger.info(f"✅ Added strategy for live trading: {strategy_id}")
    
    def remove_strategy(self, strategy_id: str):
        """Remove a strategy from execution"""
        if strategy_id in self.active_strategies:
            del self.active_strategies[strategy_id]
            logger.info(f"❌ Removed strategy: {strategy_id}")
    
    async def start_live_trading(self):
        """Start real-time strategy execution with live orders"""
        self.is_running = True
        logger.info("🎯 STARTING LIVE TRADING MODE - REAL ORDERS WILL BE PLACED!")
        
        while self.is_running:
            try:
                # Get latest market data
                current_data = await self.market_data_manager.get_latest_data()
                
                # Execute all active strategies
                for strategy_id, strategy in self.active_strategies.items():
                    try:
                        # Generate trading signals
                        signals = strategy.generate_signals(current_data)
                        
                        # Execute signals as REAL orders
                        for signal in signals:
                            if signal['action'] in ['BUY', 'SELL']:
                                logger.info(f"🔥 LIVE ORDER: {signal['action']} {signal['symbol']} "
                                          f"Qty: {signal.get('quantity', 1)} Price: {signal.get('price', 'MARKET')}")
                                
                                # Place REAL order through broker
                                order_result = await self.broker_manager.place_order(
                                    symbol=signal['symbol'],
                                    action=signal['action'],
                                    quantity=signal.get('quantity', 1),
                                    price=signal.get('price', None),
                                    order_type=signal.get('order_type', 'MARKET')
                                )
                                
                                # Publish order event
                                await self.event_manager.publish('order_placed', {
                                    'strategy_id': strategy_id,
                                    'signal': signal,
                                    'order_result': order_result,
                                    'timestamp': datetime.now().isoformat(),
                                    'mode': 'LIVE'
                                })
                                
                    except Exception as e:
                        logger.error(f"❌ Strategy {strategy_id} error: {e}")
                
                # Wait before next execution cycle
                await asyncio.sleep(2)  # 2-second cycle for live trading
                
            except Exception as e:
                logger.error(f"❌ Real-time trading error: {e}")
                await asyncio.sleep(5)
    
    def stop_live_trading(self):
        """Stop real-time strategy execution"""
        self.is_running = False
        logger.info("🛑 LIVE TRADING STOPPED")
    
    def get_strategy_status(self) -> Dict[str, Any]:
        """Get current status of all strategies"""
        return {
            'total_strategies': len(self.active_strategies),
            'active_strategies': list(self.active_strategies.keys()),
            'is_running': self.is_running,
            'mode': 'LIVE_TRADING',
            'timestamp': datetime.now().isoformat()
        } 