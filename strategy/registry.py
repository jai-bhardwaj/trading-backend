"""
Strategy Registry - Registers all available strategies
"""
from typing import Dict, Type, List, Any
from strategy.base import BaseStrategy
from strategy.moving_average import MovingAverageStrategy
from strategy.rsi import RSIStrategy
from strategy.test_strategy import TestStrategy

# Registry dict: strategy_id -> strategy class
STRATEGY_REGISTRY: Dict[str, Type[BaseStrategy]] = {}

# List of all available strategies (add new ones here)
AVAILABLE_STRATEGIES = [
    ("ma_crossover", MovingAverageStrategy),
    ("rsi_strategy", RSIStrategy),
    ("test_strategy", TestStrategy),
]

def register_strategies_to_registry():
    for strategy_id, strategy_cls in AVAILABLE_STRATEGIES:
        STRATEGY_REGISTRY[strategy_id] = strategy_cls

def get_strategy_class(strategy_id: str) -> Type[BaseStrategy]:
    return STRATEGY_REGISTRY.get(strategy_id)

def register_strategies_to_db(db_stub: Any = None):
    # Stub: In a real system, this would persist strategy configs to a DB
    print("[Registry] Registering strategies to DB (stub)")
    for strategy_id, strategy_cls in AVAILABLE_STRATEGIES:
        print(f"[Registry] Registered {strategy_id} to DB") 