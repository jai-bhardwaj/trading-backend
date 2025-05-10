# app/brokers/mock_broker.py
import uuid
import asyncio
import random
import datetime
from typing import Dict, List, Any, Optional
import logging
import copy

from app.core.interfaces import BrokerInterface, Order, Position, Balance

logger = logging.getLogger(__name__)

class MockBroker(BrokerInterface):
    """
    A mock broker implementation for paper trading and testing.
    Simulates order placement, fills, positions, and balance in memory.
    """
    # Class level storage (simple approach, state lost on restart)
    _user_data: Dict[str, Dict[str, Any]] = {} # { user_id: {"orders": {}, "positions": {}, "balance": {}} }

    def __init__(self):
        self._initialized_users: set[str] = set() # Track initialized users for this instance
        logger.info("MockBroker instance created")

    async def initialize(self, user_id: str, config: Dict[str, Any]):
        """Initializes mock data for a specific user."""
        if user_id in self._initialized_users:
            logger.info(f"MockBroker already initialized for user {user_id}")
            return

        logger.info(f"Initializing MockBroker for user {user_id} with config: {config}")
        # Initialize user data if not already present (class level)
        if user_id not in MockBroker._user_data:
            initial_balance = config.get('initial_balance', 100000.0)
            MockBroker._user_data[user_id] = {
                "orders": {}, # {internal_order_id: Order}
                "positions": {}, # {symbol: Position}
                "balance": Balance(available_cash=initial_balance, margin_used=0.0, total_balance=initial_balance),
                "trades": [] # List of trade dicts
            }
            logger.info(f"Created initial mock data for user {user_id} with balance {initial_balance}")
        else:
             logger.info(f"User {user_id} data already exists in MockBroker.")

        self._initialized_users.add(user_id)
        await asyncio.sleep(0.01) # Simulate async init
        logger.info(f"MockBroker initialized for user {user_id}.")

    def _get_user_data(self, user_id: str) -> Dict[str, Any]:
        """Safely retrieves data for a user, raising error if not initialized."""
        if user_id not in self._initialized_users:
             raise RuntimeError(f"MockBroker not initialized for user {user_id}")
        if user_id not in MockBroker._user_data:
            # This shouldn't happen if initialize was called, but defensive check
            raise RuntimeError(f"Mock data structure not found for initialized user {user_id}")
        return MockBroker._user_data[user_id]

    async def place_order(self, order: Order) -> Dict[str, Any]:
        """Simulates placing an order."""
        user_data = self._get_user_data(order.user_id)

        # Assign an internal ID and timestamp
        order.internal_order_id = f"mock_{uuid.uuid4()}"
        order.order_timestamp = datetime.datetime.now(datetime.timezone.utc)
        order.last_update_timestamp = order.order_timestamp
        order.status = "ACCEPTED" # Simulate immediate acceptance

        logger.info(f"MockBroker: Received order {order.internal_order_id} for user {order.user_id}: {order.side} {order.quantity} {order.symbol} @ {order.order_type}")

        # Basic validation simulation (already done in Order init, could add more)
        if order.order_type == 'LIMIT' and order.price is None:
            order.status = "REJECTED"
            order.status_message = "Price required for limit order"
            user_data["orders"][order.internal_order_id] = copy.deepcopy(order) # Store rejected order
            logger.warning(f"MockBroker: Order {order.internal_order_id} REJECTED: {order.status_message}")
            return {"broker_order_id": None, "status": order.status, "message": order.status_message}

        # Store the accepted order
        user_data["orders"][order.internal_order_id] = copy.deepcopy(order)
        logger.info(f"MockBroker: Order {order.internal_order_id} ACCEPTED.")

        # Simulate asynchronous fill
        asyncio.create_task(self._simulate_fill(order.internal_order_id, order.user_id))

        # Return broker_order_id as the internal ID for mock
        return {"broker_order_id": order.internal_order_id, "status": order.status, "message": "Order accepted by mock broker"}

    async def _simulate_fill(self, internal_order_id: str, user_id: str):
        """Internal method to simulate order fills after a delay."""
        await asyncio.sleep(random.uniform(0.1, 0.5)) # Short delay

        try:
            user_data = self._get_user_data(user_id) # Re-check initialization
        except RuntimeError:
            logger.error(f"MockBroker: User {user_id} data not found during fill simulation for {internal_order_id}.")
            return

        orders = user_data["orders"]
        if internal_order_id not in orders:
            logger.warning(f"MockBroker: Order {internal_order_id} not found for fill simulation (maybe cancelled?).")
            return

        order = orders[internal_order_id]

        # Don't fill if cancelled or rejected
        if order.status not in ["ACCEPTED", "OPEN"]: # Add more states if needed
             logger.info(f"MockBroker: Order {internal_order_id} not in fillable state ({order.status}). Skipping fill.")
             return

        # --- Simulate Fill Logic ---
        # Simple simulation: full fill at simulated price
        # A more complex sim would handle partial fills, price slippage based on type etc.
        fill_qty = order.quantity
        simulated_market_price = random.uniform(98.5, 101.5) # Dummy price range

        if order.order_type == 'MARKET':
            fill_price = simulated_market_price
        elif order.order_type == 'LIMIT':
            # Basic limit fill simulation
            if (order.side == 'BUY' and order.price >= simulated_market_price) or \
               (order.side == 'SELL' and order.price <= simulated_market_price):
                fill_price = order.price # Assume filled at limit price
            else:
                # Limit order not met by simulated market price
                logger.info(f"MockBroker: Limit order {internal_order_id} ({order.price}) not filled at simulated price {simulated_market_price:.2f}")
                # Order remains OPEN - don't change status here unless IOC logic is added
                # For simplicity, we'll just not fill it in this run. A real sim needs state tracking.
                # Let's change status to OPEN to indicate it wasn't filled yet.
                order.status = "OPEN"
                order.last_update_timestamp = datetime.datetime.now(datetime.timezone.utc)
                return
        # Add SL/SL-M simulation if needed (check trigger price against simulated_market_price)
        else: # SL, SL-M etc. - Just use simulated price for now
             fill_price = simulated_market_price # Needs proper trigger logic

        # Update Order State
        order.status = "COMPLETE"
        order.filled_quantity = fill_qty
        order.average_price = fill_price
        order.last_update_timestamp = datetime.datetime.now(datetime.timezone.utc)
        order.broker_order_id = order.internal_order_id # For mock, they are the same

        logger.info(f"MockBroker: Order {internal_order_id} COMPLETE! Qty: {fill_qty}, AvgPrice: {fill_price:.2f}")

        # Update Positions and Balance
        positions = user_data["positions"]
        balance = user_data["balance"]
        symbol = order.symbol # Use the full symbol including exchange if needed for uniqueness

        # Create position if it doesn't exist
        if symbol not in positions:
            positions[symbol] = Position(
                symbol=order.symbol,
                exchange=order.exchange,
                product_type=order.product_type,
                quantity=0,
                average_price=0.0
            )

        current_pos = positions[symbol]
        current_qty = current_pos.quantity
        current_avg = current_pos.average_price

        # Calculate new position average price
        if order.side == 'BUY':
            new_qty = current_qty + fill_qty
            if new_qty != 0:
                new_avg = ((current_avg * current_qty) + (fill_price * fill_qty)) / new_qty
            else:
                new_avg = 0.0 # Reset avg price if position is closed
            balance.available_cash -= fill_qty * fill_price # Reduce cash
        else: # SELL
            new_qty = current_qty - fill_qty
            if new_qty != 0:
                # Avg price calculation for shorts can be tricky. Simple avg for now.
                # A proper system tracks buy/sell avg separately or uses FIFO/LIFO.
                # If reducing position size, avg price doesn't change until position reverses.
                if (current_qty > 0 and new_qty > 0) or (current_qty < 0 and new_qty < 0):
                     new_avg = current_avg # Avg price remains same when reducing long/short
                elif new_qty == 0:
                     new_avg = 0.0 # Position closed
                else: # Position reversed (e.g., long to short) or initiated
                     new_avg = fill_price # Avg price becomes the price of the reversing/initiating trade
            else:
                new_avg = 0.0 # Position closed
            balance.available_cash += fill_qty * fill_price # Increase cash

        # Update position object
        current_pos.quantity = new_qty
        current_pos.average_price = new_avg if abs(new_qty) > 1e-9 else 0.0 # Handle potential float issues near zero

        # Remove position if quantity is zero
        if abs(new_qty) < 1e-9:
             del positions[symbol]
             logger.info(f"MockBroker: Position closed for {symbol}")

        # Update total balance (simple equity = cash for mock)
        balance.total_balance = balance.available_cash # In reality, add portfolio value

        logger.info(f"MockBroker: User {user_id} New Position {symbol}: Qty={new_qty}, AvgPx={new_avg:.2f}, Balance: {balance.available_cash:.2f}")

        # Record the trade
        trade = {
            "trade_id": f"mock_trade_{uuid.uuid4()}",
            "broker_order_id": order.broker_order_id,
            "symbol": order.symbol,
            "exchange": order.exchange,
            "side": order.side,
            "quantity": fill_qty,
            "price": fill_price,
            "product_type": order.product_type,
            "order_type": order.order_type,
            "trade_timestamp": order.last_update_timestamp,
        }
        user_data["trades"].append(trade)

    async def cancel_order(self, user_id: str, broker_order_id: str, variety: Optional[str] = None) -> Dict[str, Any]:
        """Simulates cancelling an order."""
        user_data = self._get_user_data(user_id)
        internal_order_id = broker_order_id # In mock, broker_order_id is our internal ID

        logger.info(f"MockBroker: Received cancel request for order {internal_order_id}")
        if internal_order_id in user_data["orders"]:
            order = user_data["orders"][internal_order_id]
            # Can only cancel orders that are pending or open
            if order.status in ["ACCEPTED", "OPEN", "PENDING"]: # Add more cancellable states if needed
                order.status = 'CANCELLED'
                order.last_update_timestamp = datetime.datetime.now(datetime.timezone.utc)
                logger.info(f"MockBroker: Order {internal_order_id} cancelled.")
                return {"broker_order_id": internal_order_id, "status": order.status}
            else:
                logger.warning(f"MockBroker: Order {internal_order_id} cannot be cancelled in state {order.status}.")
                return {"broker_order_id": internal_order_id, "status": order.status, "message": "Cannot cancel order in its current state"}
        else:
            logger.error(f"MockBroker: Order {internal_order_id} not found for cancellation.")
            return {"broker_order_id": internal_order_id, "status": "NOT_FOUND"}

    async def get_order_status(self, user_id: str, broker_order_id: str) -> Dict[str, Any]:
        """Gets the status of a specific mock order."""
        user_data = self._get_user_data(user_id)
        internal_order_id = broker_order_id

        if internal_order_id in user_data["orders"]:
            order = user_data["orders"][internal_order_id]
            # Return a dictionary representation of the order state
            return order.__dict__ # Simple approach for mock; could map to a cleaner dict
        else:
             logger.warning(f"MockBroker: Order {internal_order_id} not found for user {user_id}")
             return {"status": "NOT_FOUND", "broker_order_id": internal_order_id}

    async def get_order_history(self, user_id: str) -> List[Dict[str, Any]]:
        """Gets the history of all mock orders for the user."""
        user_data = self._get_user_data(user_id)
        # Return dictionary representations of all orders
        return [order.__dict__ for order in user_data["orders"].values()]

    async def get_positions(self, user_id: str) -> List[Dict[str, Any]]:
        """Gets current mock positions for the user."""
        user_data = self._get_user_data(user_id)
        # Return dictionary representations of current positions
        return [pos.__dict__ for pos in user_data["positions"].values()]

    async def get_balance(self, user_id: str) -> Dict[str, Any]:
        """Gets mock account balance for the user."""
        user_data = self._get_user_data(user_id)
        # Return dictionary representation of the balance
        return user_data["balance"].__dict__

    async def get_trade_history(self, user_id: str) -> List[Dict[str, Any]]:
        """Gets the history of mock trades for the user."""
        user_data = self._get_user_data(user_id)
        return user_data["trades"]