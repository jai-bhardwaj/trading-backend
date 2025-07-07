"""
RSI Strategy
"""
from typing import Dict, Any, List
from datetime import datetime
import numpy as np
from strategy.base import BaseStrategy
import logging

class RSIStrategy(BaseStrategy):
    async def run(self, market_data: dict) -> List[Dict]:
        signals = []
        logger = logging.getLogger(__name__)
        for symbol in self.symbols:
            md = market_data.get(symbol)
            current_price = md.ltp if md else None
            if current_price is None:
                logger.warning(f"No live price for {symbol}, skipping.")
                continue
            historical_data = await self.market_data_provider.get_historical_data(
                symbol, "1D", self.parameters["period"] + 10
            )
            if not historical_data or len(historical_data) < self.parameters["period"]:
                logger.warning(f"No historical data for {symbol}, skipping.")
                continue
            prices = [float(candle["close"]) for candle in historical_data]
            rsi = self._calculate_rsi(prices, self.parameters["period"])
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
                    "metadata": {"rsi": rsi, "period": self.parameters["period"], "live_price": current_price}
                })
        return signals

    def _calculate_rsi(self, prices: List[float], period: int) -> float:
        if len(prices) < period + 1:
            return 50.0
        deltas = np.diff(prices)
        gains = np.where(deltas > 0, deltas, 0)
        losses = np.where(deltas < 0, -deltas, 0)
        avg_gain = np.mean(gains[-period:])
        avg_loss = np.mean(losses[-period:])
        if avg_loss == 0:
            return 100.0
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        return rsi

    def _calculate_position_size(self, price: float, confidence: float) -> int:
        base_quantity = 100
        confidence_multiplier = confidence * 2
        quantity = int(base_quantity * confidence_multiplier)
        return max(1, min(quantity, 1000)) 