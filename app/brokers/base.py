# app/brokers/base.py
# Re-exporting the interface for potentially cleaner imports elsewhere
# Or this file could contain shared broker utility functions in a larger app.
from app.core.interfaces import Balance, BrokerInterface, Order, Position
from abc import ABC, abstractmethod

# No code needed here unless you add shared utilities


class BaseBroker(ABC):
    @abstractmethod
    def place_order(
        self, symbol: str, order_type: str, quantity: float, price: float
    ) -> str:
        """
        Place an order with the broker

        Args:
            symbol: The trading symbol (e.g., "AAPL")
            order_type: The type of order ("buy" or "sell")
            quantity: The quantity to trade
            price: The price at which to trade

        Returns:
            str: The broker's order ID
        """
        pass
