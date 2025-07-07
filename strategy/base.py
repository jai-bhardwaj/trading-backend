"""
Base class for all trading strategies
"""
from typing import Dict, Any, List, Optional
from datetime import datetime
from strategy.market_data import MarketDataProvider, MarketData

class BaseStrategy:
    def __init__(self, config: Dict[str, Any], market_data_provider: MarketDataProvider):
        self.config = config
        self.market_data_provider = market_data_provider
        self.strategy_id = config.get("strategy_id", self.__class__.__name__)
        self.symbols = config.get("symbols", [])
        self.parameters = config.get("parameters", {})
        self.enabled = config.get("enabled", True)

    async def run(self) -> List[Dict]:
        """
        Run the strategy and return a list of trading signals.
        Each signal is a dict with keys: symbol, signal_type, confidence, price, quantity, timestamp, metadata
        """
        raise NotImplementedError("Each strategy must implement the run() method.")

    def get_config(self) -> Dict[str, Any]:
        return self.config

    def __repr__(self):
        return f"<{self.__class__.__name__} id={self.strategy_id} enabled={self.enabled}>" 