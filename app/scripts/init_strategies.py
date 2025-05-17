import sys
import os
from pathlib import Path
import inspect
from datetime import datetime

# Add the parent directory to Python path
sys.path.append(str(Path(__file__).parent.parent))

from app.database import SessionLocal
from app.models import Strategy as StrategyModel

# Dynamically import the strategies module
from importlib import import_module

strategies_module = import_module("app.strategies.strategies")


def load_strategy_classes():
    """Load all strategy classes from the strategies module."""
    strategy_classes = []
    for name, obj in inspect.getmembers(strategies_module):
        if inspect.isclass(obj) and hasattr(obj, "name"):
            strategy_classes.append(obj)
    return strategy_classes


def create_strategy_entries(db):
    """Create database entries for each strategy class."""
    system_user_id = "system"
    for strategy_cls in load_strategy_classes():
        try:
            instance = strategy_cls()
            strategy_data = {
                "name": getattr(instance, "name", strategy_cls.__name__),
                "margin": getattr(instance, "default_margin", 100000.0),
                "marginType": getattr(instance, "default_margin_type", "rupees"),
                "basePrice": getattr(instance, "default_base_price", 1000.0),
                "status": getattr(instance, "default_status", "active"),
                "user_id": system_user_id,
                "lastUpdated": datetime.utcnow(),
            }
            existing = (
                db.query(StrategyModel)
                .filter(
                    StrategyModel.name == strategy_data["name"],
                    StrategyModel.user_id == system_user_id,
                )
                .first()
            )
            if not existing:
                strategy = StrategyModel(**strategy_data)
                db.add(strategy)
                print(f"Added strategy: {strategy_data['name']}")
            else:
                print(f"Strategy already exists: {strategy_data['name']}")
        except Exception as e:
            print(f"Error adding strategy {strategy_cls.__name__}: {e}")


def main():
    """Main function to initialize strategies in the database."""
    db = SessionLocal()
    try:
        create_strategy_entries(db)
        db.commit()
        print("Successfully initialized strategies in the database")
    except Exception as e:
        db.rollback()
        print(f"Error initializing strategies: {e}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
