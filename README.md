# Trading Backend - Minimal PubSub Architecture

A clean, minimal trading backend that demonstrates the complete flow from strategy signal generation to order execution using Redis pub/sub and Angel One broker integration.

## Architecture

```
Strategy Engine → Redis Pub/Sub → Signal Subscriber → Order Manager → Angel One Broker
```

### Components

1. **Strategy Engine** (`strategy/`)
   - Generates trading signals using live market data from Angel One
   - Publishes signals to Redis pub/sub channel
   - Supports multiple strategies (Moving Average, RSI, etc.)

2. **Signal Subscriber** (`order/subscriber.py`)
   - Listens to Redis pub/sub for strategy signals
   - Processes signals for multiple users
   - Creates order requests

3. **Order Manager** (`order/manager.py`)
   - Executes orders with Angel One broker
   - Supports both paper trading and live trading
   - Manages order lifecycle

4. **Market Data Provider** (`strategy/market_data.py`)
   - Fetches live market data from Angel One
   - Provides historical data for strategy calculations

## Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Set Environment Variables

Copy `env.template` to `.env` and configure:

```bash
cp env.template .env
```

Edit `.env` with your Angel One credentials:

```env
# Angel One API Configuration
ANGEL_ONE_API_KEY=your_api_key
ANGEL_ONE_CLIENT_CODE=your_client_code
ANGEL_ONE_PASSWORD=your_password
ANGEL_ONE_TOTP_SECRET=your_totp_secret

# Redis Configuration
REDIS_URL=redis://localhost:6379/2

# Trading Configuration
PAPER_TRADING=true
```

### 3. Start Redis

```bash
redis-server --daemonize yes
```

### 4. Run Tests

```bash
python tests/test_complete_flow.py
```

## Usage

### Strategy Engine

```python
from strategy.engine import StrategyEngine

# Initialize
engine = StrategyEngine()
await engine.initialize()

# Run strategies
signals = await engine.run_all_strategies()

# Continuous execution
await engine.start_continuous_execution(interval_seconds=60)
```

### Signal Subscriber

```python
from order.subscriber import SignalSubscriber
from order.manager import OrderManager

# Initialize
order_manager = OrderManager(paper_trading=True)
await order_manager.initialize()

subscriber = SignalSubscriber()
await subscriber.initialize(order_manager)

# Start listening
await subscriber.start_listening()
```

### Order Manager

```python
from order.manager import OrderManager

# Initialize (paper trading)
order_manager = OrderManager(paper_trading=True)
await order_manager.initialize()

# Execute order
result = await order_manager.execute_order({
    "user_id": "user_001",
    "symbol": "RELIANCE",
    "side": "BUY",
    "order_type": "MARKET",
    "quantity": 100,
    "price": 2500.0
})
```

## Configuration

### Environment Variables

- `ANGEL_ONE_API_KEY`: Your Angel One API key
- `ANGEL_ONE_CLIENT_CODE`: Your Angel One client code
- `ANGEL_ONE_PASSWORD`: Your Angel One password
- `ANGEL_ONE_TOTP_SECRET`: Your Angel One TOTP secret
- `REDIS_URL`: Redis connection URL
- `PAPER_TRADING`: Enable/disable paper trading mode

### Strategy Configuration

Strategies are configured in `strategy/engine.py`:

```python
StrategyConfig(
    strategy_id="ma_crossover",
    strategy_type=StrategyType.MOVING_AVERAGE,
    symbols=["RELIANCE", "TCS", "INFY"],
    parameters={
        "short_window": 10,
        "long_window": 50,
        "min_confidence": 0.7
    }
)
```

## Testing

### Complete Flow Test

```bash
python tests/test_complete_flow.py
```

This test demonstrates:
1. Strategy signal generation
2. Signal publishing to Redis
3. Signal subscription and processing
4. Order execution
5. Continuous execution

### Individual Component Tests

```bash
# Test strategy engine
python -c "import asyncio; from strategy.engine import StrategyEngine; asyncio.run(StrategyEngine().initialize())"

# Test order manager
python -c "import asyncio; from order.manager import OrderManager; asyncio.run(OrderManager().initialize())"
```

## Architecture Benefits

1. **Decoupled**: Strategy engine and order execution are completely separate
2. **Scalable**: Can run multiple subscribers for different user groups
3. **Reliable**: Redis pub/sub ensures no signals are lost
4. **Testable**: Each component can be tested independently
5. **Configurable**: Easy to switch between paper and live trading

## File Structure

```
trading-backend/
├── strategy/
│   ├── __init__.py
│   ├── engine.py          # Strategy engine
│   └── market_data.py     # Market data provider
├── order/
│   ├── __init__.py
│   ├── manager.py         # Order manager
│   └── subscriber.py      # Signal subscriber
├── shared/
│   ├── __init__.py
│   └── models.py          # Shared data models
├── tests/
│   └── test_complete_flow.py
├── data/
│   └── symbol_token_map.json
├── requirements.txt
├── env.template
└── README.md
```

## Next Steps

1. **Add more strategies** in `strategy/engine.py`
2. **Implement real user service** in `order/subscriber.py`
3. **Add risk management** in `order/manager.py`
4. **Add monitoring and metrics**
5. **Deploy with Docker**

## Support

For issues or questions, please check the logs and ensure all environment variables are properly configured.
