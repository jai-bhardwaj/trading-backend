"""
Strategy Registry - Registers all available strategies
"""
from typing import Dict, Type, List, Any
from strategy.base import BaseStrategy
from strategy.rsi_dmi_strategy import RSIDMIStrategy
from strategy.btst_momentum_strategy import BTSTMomentumStrategy
from strategy.swing_momentum_strategy import SwingMomentumStrategy
from strategy.rsi_dmi_intraday_strategy import RSIDMIIntradayStrategy
from strategy.test_strategy import TestStrategy

# Registry dict: strategy_id -> strategy class
STRATEGY_REGISTRY: Dict[str, Type[BaseStrategy]] = {}

# List of all available strategies (5 strategies total)
AVAILABLE_STRATEGIES = [
    ("rsi_dmi", RSIDMIStrategy),
    ("btst_momentum", BTSTMomentumStrategy),
    ("swing_momentum", SwingMomentumStrategy),
    ("rsi_dmi_intraday", RSIDMIIntradayStrategy),
    ("test_strategy", TestStrategy),
]

def register_strategies_to_registry():
    for strategy_id, strategy_cls in AVAILABLE_STRATEGIES:
        STRATEGY_REGISTRY[strategy_id] = strategy_cls

def get_strategy_class(strategy_id: str) -> Type[BaseStrategy]:
    return STRATEGY_REGISTRY.get(strategy_id)

def get_all_strategies() -> Dict[str, Dict[str, Any]]:
    """Get all available strategies with their metadata"""
    strategies = {}
    for strategy_id, strategy_cls in AVAILABLE_STRATEGIES:
        strategies[strategy_id] = {
            "name": strategy_cls.__name__,
            "description": strategy_cls.__doc__ or "",
            "type": "CUSTOM",
            "symbols": [],
            "parameters": {},
            "enabled": True
        }
    return strategies

def register_strategies_to_db(db_stub: Any = None):
    # Stub: In a real system, this would persist strategy configs to a DB
    print("[Registry] Registering strategies to DB (stub)")
    for strategy_id, strategy_cls in AVAILABLE_STRATEGIES:
        print(f"[Registry] Registered {strategy_id} to DB") 