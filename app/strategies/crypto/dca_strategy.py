"""
Dollar Cost Averaging (DCA) Strategy for Cryptocurrency
"""

from ..base import BaseStrategy
from ..registry import StrategyRegistry, AssetClass

@StrategyRegistry.register("dca_crypto", AssetClass.CRYPTO)
class DCAStrategy(BaseStrategy):
    """Placeholder DCA strategy"""
    
    def initialize(self):
        pass
    
    def process_market_data(self, market_data):
        return None
    
    def calculate_position_size(self, signal, current_balance):
        return 0 