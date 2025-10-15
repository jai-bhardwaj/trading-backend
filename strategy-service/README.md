# Strategy Service Architecture

A microservice-based strategy service architecture where each strategy runs in its own isolated Docker container, consuming real-time market data from Redis Streams and publishing trading signals back to Redis.

## Architecture Overview

```
Market Data Service → Redis Streams → Strategy Services → Redis Signals
```

### Components

1. **Market Data Service**: Publishes real-time market data to Redis Streams
2. **Redis Streams**: `market_data_stream:{SYMBOL}` - One stream per symbol
3. **Strategy Services**: Individual Docker containers running trading strategies
4. **Redis Signals**: `strategy_signals` channel - Published trading signals

## Directory Structure

```
strategy-service/
├── base/                          # Base framework
│   ├── base_strategy.py          # Abstract base class
│   ├── market_data_consumer.py   # Redis Stream consumer
│   ├── signal_publisher.py      # Signal publisher
│   └── indicators.py            # Technical indicators
├── shared/                       # Shared models
│   └── models.py                # Data models
├── strategies/                   # Individual strategies
│   └── rsi_dmi_strategy/        # RSI DMI strategy
│       ├── Dockerfile
│       ├── requirements.txt
│       ├── strategy.py
│       └── config.py
└── test_integration.py          # Integration test
```

## Base Strategy Framework

### BaseStrategy Class

All strategies extend the `BaseStrategy` abstract class which provides:

- **Market Data Consumption**: Automatic Redis Stream consumption
- **Signal Publishing**: Automatic signal publishing to Redis
- **Technical Indicators**: Built-in RSI, DMI, SMA, EMA, Bollinger Bands, MACD, Stochastic
- **Health Monitoring**: Built-in health checks and statistics
- **Configuration**: Environment-based configuration

### Key Methods

```python
class BaseStrategy(ABC):
    async def run(self, market_data: Dict[str, MarketDataTick]) -> List[TradingSignal]:
        """Implement your strategy logic here"""
        pass
    
    def get_historical_buffer(self, symbol: str, periods: int = 100) -> List[MarketDataTick]:
        """Get historical market data"""
        pass
    
    def calculate_quantity(self, price: float) -> int:
        """Calculate order quantity"""
        pass
```

## Data Formats

### Market Data Input (Redis Stream)

```json
{
    "symbol": "RELIANCE",
    "token": "2881",
    "ltp": 2500.50,
    "change": 10.50,
    "change_percent": 0.42,
    "high": 2510.00,
    "low": 2490.00,
    "volume": 1000000,
    "bid": 2500.00,
    "ask": 2501.00,
    "open": 2490.00,
    "close": 2490.00,
    "timestamp": "2025-10-15T10:30:00",
    "exchange_timestamp": "2025-10-15T10:29:59"
}
```

### Signal Output (Redis Channel)

```json
{
    "strategy_id": "rsi_dmi_strategy",
    "symbol": "RELIANCE",
    "signal_type": "BUY",
    "confidence": 0.85,
    "price": 2500.50,
    "quantity": 10,
    "timestamp": "2025-10-15T10:30:00",
    "metadata": {
        "rsi": 72.5,
        "di_plus": 28.0,
        "indicators": {...}
    }
}
```

## Running Strategies

### Using Docker Compose

The strategies are defined in `docker-compose.yml`:

```yaml
rsi-dmi-strategy:
  build:
    context: .
    dockerfile: strategy-service/strategies/rsi_dmi_strategy/Dockerfile
  environment:
    STRATEGY_ID: "rsi_dmi_strategy"
    SYMBOLS: "RELIANCE,TCS,INFY,HDFC,ICICIBANK"
    ENTRY_RSI_UL: "70"
    DI_UL: "25"
    RSI_LL: "30"
    CAPITAL: "100000"
  depends_on:
    - redis
    - market-data-service
```

### Environment Variables

- `STRATEGY_ID`: Unique strategy identifier
- `SYMBOLS`: Comma-separated list of symbols to trade
- `REDIS_URL`: Redis connection URL
- `CONSUMER_GROUP`: Redis consumer group name
- `SIGNAL_CHANNEL`: Redis channel for publishing signals
- Strategy-specific parameters (e.g., `ENTRY_RSI_UL`, `DI_UL`)

## Technical Indicators

Built-in technical indicators available to all strategies:

- **RSI**: Relative Strength Index
- **DMI**: Directional Movement Index (+DI, -DI)
- **SMA**: Simple Moving Average
- **EMA**: Exponential Moving Average
- **Bollinger Bands**: Upper, Middle, Lower bands
- **MACD**: Moving Average Convergence Divergence
- **Stochastic**: %K and %D oscillators

## Creating New Strategies

1. Create a new directory under `strategies/`
2. Create `strategy.py` extending `BaseStrategy`
3. Create `Dockerfile` for the strategy
4. Create `requirements.txt` with dependencies
5. Add service to `docker-compose.yml`

### Example Strategy Template

```python
from base.base_strategy import BaseStrategy
from shared.models import TradingSignal, SignalType

class MyStrategy(BaseStrategy):
    async def run(self, market_data):
        signals = []
        
        for symbol in self.symbols:
            if symbol not in market_data:
                continue
                
            # Get historical data
            hist_data = self.get_historical_buffer(symbol, 50)
            
            # Calculate indicators
            rsi_values = self.indicators.calculate_rsi(hist_data, 14)
            
            # Your strategy logic here
            if rsi_values and rsi_values[-1] > 70:
                signal = TradingSignal(
                    strategy_id=self.strategy_id,
                    symbol=symbol,
                    signal_type=SignalType.BUY,
                    confidence=0.8,
                    price=market_data[symbol].ltp,
                    quantity=self.calculate_quantity(market_data[symbol].ltp),
                    timestamp=datetime.now(),
                    metadata={'rsi': rsi_values[-1]}
                )
                signals.append(signal)
        
        return signals
```

## Testing

Run the integration test to verify the complete flow:

```bash
python strategy-service/test_integration.py
```

This test:
1. Checks Redis Streams exist
2. Publishes test market data
3. Subscribes to strategy signals
4. Verifies signals are received

## Migration from Old Architecture

The old `strategy/` folder has been archived to `strategy_old/`. The new architecture provides:

- **Better Isolation**: Each strategy runs in its own container
- **Redis Streams**: Reliable market data streaming
- **Simplified Base Class**: Easier to implement new strategies
- **Built-in Indicators**: No need to implement technical indicators
- **Health Monitoring**: Built-in health checks and statistics

## Monitoring

Each strategy provides health checks and statistics:

- **Health Check**: Docker health check endpoint
- **Statistics**: Signals generated, ticks processed, errors
- **Logging**: Structured logging with strategy identification

## Dependencies

- **Redis**: For streams and pub/sub
- **Python 3.11**: Base runtime
- **redis-py**: Redis client library
- **asyncio**: Async/await support
