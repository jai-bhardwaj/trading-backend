"""
RSI Strategy - Modified to work with live data only
"""
from typing import Dict, Any, List
from datetime import datetime
import numpy as np
from strategy.base import BaseStrategy
import logging

logger = logging.getLogger(__name__)

class RSIStrategy(BaseStrategy):
    def __init__(self, config: Dict[str, Any], market_data_provider):
        super().__init__(config, market_data_provider)
        # Initialize price history for RSI calculation
        self.price_history = {}  # symbol -> list of prices
        self.min_history_length = 14  # Minimum prices needed for RSI
    
    async def run(self, market_data: dict) -> List[Dict]:
        signals = []
        
        for symbol in self.symbols:
            md = market_data.get(symbol)
            current_price = md.ltp if md else None
            
            if current_price is None:
                logger.warning(f"No live price for {symbol}, skipping.")
                continue
            
            # Update price history with current price
            if symbol not in self.price_history:
                self.price_history[symbol] = []
            
            self.price_history[symbol].append(current_price)
            
            # Keep only last 50 prices to avoid memory issues
            if len(self.price_history[symbol]) > 50:
                self.price_history[symbol] = self.price_history[symbol][-50:]
            
            # Calculate RSI if we have enough price history
            if len(self.price_history[symbol]) >= self.min_history_length:
                rsi = self._calculate_rsi(self.price_history[symbol], self.parameters["period"])
                
                signal_type = "HOLD"
                confidence = 0.0
                
                if rsi < self.parameters["oversold"]:
                    signal_type = "BUY"
                    confidence = min(0.8, (self.parameters["oversold"] - rsi) / self.parameters["oversold"])
                elif rsi > self.parameters["overbought"]:
                    signal_type = "SELL"
                    confidence = min(0.8, (rsi - self.parameters["overbought"]) / (100 - self.parameters["overbought"]))
                
                if confidence >= self.parameters.get("min_confidence", 0.6):
                    signals.append({
                        "strategy_id": self.strategy_id,
                        "symbol": symbol,
                        "signal_type": signal_type,
                        "confidence": confidence,
                        "price": current_price,
                        "quantity": self._calculate_position_size(current_price, confidence),
                        "timestamp": datetime.now(),
                        "metadata": {
                            "rsi": rsi, 
                            "period": self.parameters["period"], 
                            "live_price": current_price,
                            "price_history_length": len(self.price_history[symbol])
                        }
                    })
            else:
                logger.debug(f"Insufficient price history for {symbol} ({len(self.price_history[symbol])}/{self.min_history_length})")
        
        return signals

    def _calculate_rsi(self, prices: List[float], period: int) -> float:
        """Calculate RSI using price history"""
        if len(prices) < period + 1:
            return 50.0
        
        # Use the last 'period' prices for calculation
        recent_prices = prices[-period-1:]
        deltas = np.diff(recent_prices)
        
        gains = np.where(deltas > 0, deltas, 0)
        losses = np.where(deltas < 0, -deltas, 0)
        
        avg_gain = np.mean(gains)
        avg_loss = np.mean(losses)
        
        if avg_loss == 0:
            return 100.0
        
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        return rsi

    def _calculate_position_size(self, price: float, confidence: float) -> int:
        base_quantity = self.parameters.get("base_quantity", 100)
        max_quantity = self.parameters.get("max_quantity", 1000)
        min_quantity = self.parameters.get("min_quantity", 1)
        confidence_multiplier = confidence * 2
        quantity = int(base_quantity * confidence_multiplier)
        return max(min_quantity, min(quantity, max_quantity)) 