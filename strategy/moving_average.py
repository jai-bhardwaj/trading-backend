"""
Moving Average Crossover Strategy
"""
from typing import Dict, Any, List
from datetime import datetime
import numpy as np
from strategy.base import BaseStrategy

class MovingAverageStrategy(BaseStrategy):
    async def run(self) -> List[Dict]:
        signals = []
        for symbol in self.symbols:
            # Get historical data for moving average calculation
            historical_data = await self.market_data_provider.get_historical_data(
                symbol, "1D", self.parameters["long_window"]
            )
            if len(historical_data) < self.parameters["long_window"]:
                continue
            prices = [float(candle["close"]) for candle in historical_data]
            short_ma = np.mean(prices[-self.parameters["short_window"]:])
            long_ma = np.mean(prices[-self.parameters["long_window"]:])
            current_price = prices[-1]
            prev_short_ma = np.mean(prices[-self.parameters["short_window"]-1:-1])
            prev_long_ma = np.mean(prices[-self.parameters["long_window"]-1:-1])
            signal_type = "HOLD"
            confidence = 0.0
            if short_ma > long_ma and prev_short_ma <= prev_long_ma:
                signal_type = "BUY"
                confidence = min(0.9, abs(short_ma - long_ma) / current_price)
            elif short_ma < long_ma and prev_short_ma >= prev_long_ma:
                signal_type = "SELL"
                confidence = min(0.9, abs(short_ma - long_ma) / current_price)
            if confidence >= self.parameters.get("min_confidence", 0.7):
                signals.append({
                    "strategy_id": self.strategy_id,
                    "symbol": symbol,
                    "signal_type": signal_type,
                    "confidence": confidence,
                    "price": current_price,
                    "quantity": self._calculate_position_size(current_price, confidence),
                    "timestamp": datetime.now(),
                    "metadata": {"short_ma": short_ma, "long_ma": long_ma}
                })
        return signals

    def _calculate_position_size(self, price: float, confidence: float) -> int:
        base_quantity = 100
        confidence_multiplier = confidence * 2
        quantity = int(base_quantity * confidence_multiplier)
        return max(1, min(quantity, 1000)) 