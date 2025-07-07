"""
Configuration loader for dynamic symbol and strategy management
"""

import csv
import json
import os
import logging
from typing import Dict, List, Optional
from dataclasses import dataclass
from models_clean import Strategy, StrategyConfig as DBStrategyConfig
from shared.database import get_db_session

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
    """Loads configurations from CSV and the database"""
    
    def __init__(self, symbols_file: str = "data/symbols_to_trade.csv"):
        self.symbols_file = symbols_file
        self.symbols: Dict[str, SymbolConfig] = {}
        self.strategies: Dict[str, StrategyConfig] = {}
    
    def load_symbols(self) -> Dict[str, SymbolConfig]:
        """Load symbol configurations from instruments_latest.json and filter by symbols_to_trade.csv"""
        try:
            # Load instruments data from JSON
            instruments_data = {}
            try:
                with open("data/instruments_latest.json", "r") as f:
                    instruments = json.load(f)
                    for inst in instruments:
                        symbol = inst.get("symbol")
                        token = inst.get("token")
                        if symbol and token:
                            instruments_data[symbol] = {
                                "token": token,
                                "exchange": inst.get("exch_seg", "NSE"),
                                "lot_size": int(float(inst.get("lotsize", 1)))
                            }
                logger.info(f"✅ Loaded {len(instruments_data)} instruments from instruments_latest.json")
            except Exception as e:
                logger.error(f"❌ Error loading instruments: {e}")
                return {}
            
            # Load symbols to trade from CSV
            symbols_to_trade = set()
            try:
                with open(self.symbols_file, 'r') as file:
                    reader = csv.DictReader(file)
                    for row in reader:
                        symbol_name = row['symbol_name']
                        enabled = row['enabled'].lower() == 'true'
                        if enabled:
                            # Map CSV symbol to JSON symbol format (add -EQ suffix)
                            json_symbol = f"{symbol_name}-EQ"
                            symbols_to_trade.add(json_symbol)
                logger.info(f"✅ Loaded {len(symbols_to_trade)} symbols to trade from {self.symbols_file}")
            except Exception as e:
                logger.error(f"❌ Error loading symbols to trade: {e}")
                return {}
            
            # Create symbol configs for symbols that exist in both JSON and CSV
            for symbol in symbols_to_trade:
                if symbol in instruments_data:
                    inst_data = instruments_data[symbol]
                    symbol_config = SymbolConfig(
                        symbol=symbol,
                        token=inst_data["token"],
                        exchange=inst_data["exchange"],
                        lot_size=inst_data["lot_size"],
                        min_quantity=1,
                        enabled=True
                    )
                    self.symbols[symbol] = symbol_config
                    logger.info(f"✅ Added symbol: {symbol} (token: {inst_data['token']})")
                else:
                    logger.warning(f"⚠️ Symbol {symbol} not found in instruments data")
            
            logger.info(f"✅ Loaded {len(self.symbols)} symbols from instruments_latest.json filtered by {self.symbols_file}")
            return self.symbols
            
        except Exception as e:
            logger.error(f"❌ Error loading symbols: {e}")
            return {}
    
    def load_strategies(self) -> Dict[str, StrategyConfig]:
        """Load strategy configurations from the database"""
        try:
            with get_db_session() as session:
                strategies = session.query(Strategy).all()
                configs = session.query(DBStrategyConfig).all()
                config_map = {c.strategy_id: c for c in configs}
                for strategy in strategies:
                    config = config_map.get(strategy.id)
                    if not config:
                        continue
                    # Build a StrategyConfig-like object
                    strategy_config = StrategyConfig(
                        strategy_id=strategy.id,
                        strategy_type=strategy.strategy_type,
                        symbols=strategy.symbols,
                        parameters=strategy.parameters,
                        enabled=strategy.enabled
                    )
                    self.strategies[strategy.id] = strategy_config
            logger.info(f"✅ Loaded {len(self.strategies)} strategies from database")
            return self.strategies
        except Exception as e:
            logger.error(f"❌ Error loading strategies from database: {e}")
            return {}
    
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