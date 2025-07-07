"""
Configuration loader for dynamic symbol and strategy management
"""

import csv
import json
import os
import logging
from typing import Dict, List, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class SymbolConfig:
    symbol: str
    token: str
    exchange: str
    lot_size: int
    min_quantity: int
    enabled: bool

@dataclass
class StrategyConfig:
    strategy_id: str
    strategy_type: str
    symbols: List[str]
    parameters: Dict
    enabled: bool

class ConfigLoader:
    """Loads configurations from CSV and JSON files"""
    
    def __init__(self, symbols_file: str = "data/symbols.csv", strategies_file: str = "data/strategies.json"):
        self.symbols_file = symbols_file
        self.strategies_file = strategies_file
        self.symbols: Dict[str, SymbolConfig] = {}
        self.strategies: Dict[str, StrategyConfig] = {}
    
    def load_symbols(self) -> Dict[str, SymbolConfig]:
        """Load symbol configurations from CSV"""
        try:
            if not os.path.exists(self.symbols_file):
                logger.warning(f"⚠️ Symbols file not found: {self.symbols_file}")
                return {}
            
            with open(self.symbols_file, 'r') as file:
                reader = csv.DictReader(file)
                for row in reader:
                    symbol_config = SymbolConfig(
                        symbol=row['symbol'],
                        token=row['token'],
                        exchange=row['exchange'],
                        lot_size=int(row['lot_size']),
                        min_quantity=int(row['min_quantity']),
                        enabled=row['enabled'].lower() == 'true'
                    )
                    self.symbols[symbol_config.symbol] = symbol_config
            
            logger.info(f"✅ Loaded {len(self.symbols)} symbols from {self.symbols_file}")
            return self.symbols
            
        except Exception as e:
            logger.error(f"❌ Error loading symbols: {e}")
            return {}
    
    def load_strategies(self) -> Dict[str, StrategyConfig]:
        """Load strategy configurations from JSON"""
        try:
            if not os.path.exists(self.strategies_file):
                logger.warning(f"⚠️ Strategies file not found: {self.strategies_file}, using defaults")
                return self._get_default_strategies()
            
            with open(self.strategies_file, 'r') as file:
                strategies_data = json.load(file)
                
            for strategy_data in strategies_data:
                strategy_config = StrategyConfig(
                    strategy_id=strategy_data['strategy_id'],
                    strategy_type=strategy_data['strategy_type'],
                    symbols=strategy_data['symbols'],
                    parameters=strategy_data['parameters'],
                    enabled=strategy_data['enabled']
                )
                self.strategies[strategy_config.strategy_id] = strategy_config
            
            logger.info(f"✅ Loaded {len(self.strategies)} strategies from {self.strategies_file}")
            return self.strategies
            
        except Exception as e:
            logger.error(f"❌ Error loading strategies: {e}")
            return self._get_default_strategies()
    
    def _get_default_strategies(self) -> Dict[str, StrategyConfig]:
        """Get default strategy configurations"""
        default_strategies = {
            "ma_crossover": StrategyConfig(
                strategy_id="ma_crossover",
                strategy_type="moving_average",
                symbols=["RELIANCE-EQ", "TCS-EQ", "INFY-EQ"],
                parameters={"short_window": 10, "long_window": 50, "min_confidence": 0.7},
                enabled=True
            ),
            "rsi_strategy": StrategyConfig(
                strategy_id="rsi_strategy", 
                strategy_type="rsi",
                symbols=["RELIANCE-EQ", "TCS-EQ", "INFY-EQ", "HDFC-EQ"],
                parameters={"period": 14, "oversold": 30, "overbought": 70, "min_confidence": 0.6},
                enabled=True
            )
        }
        self.strategies = default_strategies
        logger.info("✅ Using default strategy configurations")
        return default_strategies
    
    def get_enabled_symbols(self) -> List[str]:
        """Get list of enabled symbols"""
        return [symbol for symbol, config in self.symbols.items() if config.enabled]
    
    def get_enabled_strategies(self) -> List[str]:
        """Get list of enabled strategies"""
        return [strategy_id for strategy_id, config in self.strategies.items() if config.enabled]
    
    def get_symbol_config(self, symbol: str) -> Optional[SymbolConfig]:
        """Get configuration for a specific symbol"""
        return self.symbols.get(symbol)
    
    def get_strategy_config(self, strategy_id: str) -> Optional[StrategyConfig]:
        """Get configuration for a specific strategy"""
        return self.strategies.get(strategy_id) 