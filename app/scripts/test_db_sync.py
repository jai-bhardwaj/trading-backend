import asyncio
import uuid
import time
from app.database import get_database_manager, initialize_database
from app.models.base import Order
from app.queue.redis_client import get_redis_connection

async def main():
    # Ensure DB is initialized
    await initialize_database()
    db_manager = get_database_manager()
    redis_client = get_redis_connection()

    # Create a test order
    order_id = str(uuid.uuid4())
    order_key = f"order:{order_id}"
    order_data = {
        "id": order_id,
        "user_id": "test_user",
        "symbol": "AAPL",
        "exchange": "NASDAQ",
        "side": "BUY",
        "order_type": "MARKET",
        "product_type": "INTRADAY",
        "quantity": "10",
        "price": "150.0",
        "status": "PENDING",
        "created_at": str(time.strftime('%Y-%m-%dT%H:%M:%S')),
    }
    redis_client.hset(order_key, mapping=order_data)
    redis_client.sadd("orders:pending_sync", order_id)
    print(f"Test order {order_id} added to Redis and marked for sync.")

    # Wait for the sync worker to run
    print("Waiting 3 seconds for DB sync worker...")
    await asyncio.sleep(3)

    # Check if the order is in the database
    async with db_manager.get_async_session() as session:
        db_order = await session.get(Order, order_id)
        if db_order:
            print(f"Order {order_id} was synced to the database!")
            print(f"Order DB fields: symbol={db_order.symbol}, quantity={db_order.quantity}, price={db_order.price}, status={db_order.status}")
        else:
            print(f"Order {order_id} was NOT found in the database. Sync failed.")

if __name__ == "__main__":
    asyncio.run(main()) 