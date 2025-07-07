"""
Moving Average Crossover Strategy
"""
from typing import Dict, Any, List
from datetime import datetime
import numpy as np
from strategy.base import BaseStrategy
import logging

logger = logging.getLogger(__name__)

class MovingAverageStrategy(BaseStrategy):
    async def run(self, market_data: dict) -> List[Dict]:
        logger.debug(f"Market data received: {len(market_data)} symbols")
        signals = []
        for symbol in self.symbols:
            md = market_data.get(symbol)
            current_price = md.ltp if md else None
            if current_price is None:
                logger.warning(f"No live price for {symbol}, skipping.")
                continue
            # Example: simple price-based signal (replace with your logic)
            signal_type = "HOLD"
            confidence = 0.0
            # Example: if price is above a threshold, buy; below, sell
            threshold = self.parameters.get("threshold", 1000)
            if current_price > threshold:
                signal_type = "BUY"
                confidence = 0.8
            elif current_price < threshold:
                signal_type = "SELL"
                confidence = 0.8
            if confidence >= self.parameters.get("min_confidence", 0.7):
                signals.append({
                    "strategy_id": self.strategy_id,
                    "symbol": symbol,
                    "signal_type": signal_type,
                    "confidence": confidence,
                    "price": current_price,
                    "quantity": self._calculate_position_size(current_price, confidence),
                    "timestamp": datetime.now(),
                    "metadata": {"live_price": current_price}
                })
        return signals

    def _calculate_position_size(self, price: float, confidence: float) -> int:
        base_quantity = self.parameters.get("base_quantity", 100)
        max_quantity = self.parameters.get("max_quantity", 1000)
        min_quantity = self.parameters.get("min_quantity", 1)
        confidence_multiplier = confidence * 2
        quantity = int(base_quantity * confidence_multiplier)
        return max(min_quantity, min(quantity, max_quantity)) 