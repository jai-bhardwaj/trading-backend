# Market Data Redis Streamer - Clean Implementation

A clean, modern market data streaming system that connects Angel One WebSocket to Redis Streams for reliable real-time market data distribution.

## 🚀 **Architecture**

```
Angel One WebSocket → AngelOneWebSocketClient → MarketDataRedisStreamer → Redis Streams → Consumers
```

## 📁 **Clean File Structure**

```
market-data-service/
├── angel_one_client.py      # AngelOneWebSocketClient class
├── main.py                  # MarketDataRedisStreamer service
├── redis_consumer.py        # Redis Streams consumer library
├── test_redis_consumer.py   # Consumer library tests
├── consumer_examples.py     # Usage examples
├── config.py                # Angel One credentials
├── requirements.txt         # Python dependencies
├── Dockerfile              # Container configuration
└── README.md               # Documentation
```

## 🔧 **Core Components**

### **1. AngelOneWebSocketClient** (`angel_one_client.py`)
- Clean class-based Angel One WebSocket implementation
- Handles authentication, connection, and callbacks
- No legacy functions - pure class-based approach

### **2. MarketDataRedisStreamer** (`main.py`)
- FastAPI service that streams market data to Redis Streams
- Uses AngelOneWebSocketClient for WebSocket connection
- Publishes structured market data to Redis Streams
- REST API for monitoring and management

### **3. RedisMarketDataConsumer** (`redis_consumer.py`)
- Clean client for consuming market data from Redis Streams
- Supports multiple symbol subscriptions
- Handles message acknowledgment and error recovery
- Provides latest tick retrieval

## 📊 **Market Data Format**

Each tick published to Redis Streams contains:

```json
{
    "symbol": "RELIANCE",
    "token": "2881",
    "ltp": 2456.75,
    "change": 12.50,
    "change_percent": 0.51,
    "high": 2470.00,
    "low": 2440.00,
    "volume": 1234567,
    "bid": 2456.50,
    "ask": 2457.00,
    "open": 2444.25,
    "close": 2444.25,
    "timestamp": "2024-01-15T10:30:45.123456",
    "exchange_timestamp": "2024-01-15T10:30:45.000000"
}
```

## 🔌 **Redis Stream Keys**

- `market_data_stream:{SYMBOL}` - Individual symbol streams
- Examples: 
  - `market_data_stream:RELIANCE`
  - `market_data_stream:TCS`
  - `market_data_stream:INFY`

## 🚀 **Quick Start**

### **1. Start the Service**
```bash
cd /root/app/trading-backend/market-data-service
docker-compose restart market-data-service
```

### **2. Check Health**
```bash
curl http://localhost:8001/health | python3 -m json.tool
```

### **3. Test the System**
```bash
python3 test_redis_consumer.py
```

## 📡 **API Endpoints**

### **Service Information**
- `GET /` - Service info and status
- `GET /health` - Health check
- `GET /stats` - Streaming statistics
- `GET /symbols` - List of tracked symbols
- `POST /subscribe` - Subscribe to additional symbols

### **Example API Calls**
```bash
# Check service health
curl http://localhost:8001/health

# Get streaming stats
curl http://localhost:8001/stats

# Get tracked symbols
curl http://localhost:8001/symbols

# Subscribe to new symbols
curl -X POST http://localhost:8001/subscribe \
  -H "Content-Type: application/json" \
  -d '["HDFC", "ICICIBANK"]'
```

## 🔧 **Using the Redis Consumer**

### **Basic Usage**
```python
from redis_consumer import create_redis_consumer, MarketDataTick

async def main():
    # Create consumer
    consumer = create_redis_consumer("redis://localhost:6379")
    
    # Connect
    await consumer.connect()
    
    # Add message handler
    def handle_tick(tick: MarketDataTick):
        print(f"{tick.symbol}: LTP={tick.ltp}, Change={tick.change_percent:.2f}%")
    
    consumer.add_message_handler(handle_tick)
    
    # Subscribe to symbols
    await consumer.subscribe_to_multiple_symbols(["RELIANCE", "TCS", "INFY"])
    
    # Keep running
    await asyncio.sleep(60)
    
    # Cleanup
    await consumer.disconnect()
```

### **Advanced Usage**
```python
# Subscribe to individual symbols
await consumer.subscribe_to_symbol("RELIANCE")

# Get latest tick
latest_tick = await consumer.get_latest_tick("RELIANCE")

# Get stream information
stream_info = await consumer.get_stream_info("RELIANCE")

# Subscribe to all available streams
await consumer.subscribe_to_all_symbols()
```

## ⚙️ **Configuration**

### **Environment Variables**
- `REDIS_URL` - Redis server URL (default: `redis://trading-redis:6379`)

### **Symbol Configuration**
Symbols are loaded from `/app/data/symbols_to_trade.csv`:

```csv
symbol_name,enabled
RELIANCE,true
TCS,true
INFY,true
```

### **Angel One Credentials**
Set in `config.py`:

```python
API_KEY = 'your_api_key'
USERNAME = 'your_username'
PIN = 'your_pin'
TOKEN = 'your_totp_secret'
```

## 📈 **Monitoring**

### **Health Check Response**
```json
{
    "status": "healthy",
    "timestamp": "2024-01-15T10:30:45.123456",
    "redis_connected": true,
    "ws_connected": true,
    "symbols_tracked": 3,
    "tick_count": 1234,
    "last_tick_time": "2024-01-15T10:30:45.000000",
    "has_credentials": true
}
```

### **Statistics Response**
```json
{
    "symbols_tracked": 3,
    "symbols": ["RELIANCE", "TCS", "INFY"],
    "ws_connected": true,
    "tick_count": 1234,
    "last_tick_time": "2024-01-15T10:30:45.000000",
    "running": true,
    "has_credentials": true,
    "redis_connected": true
}
```

## 🔄 **Symbol Management**

### **Adding New Symbols**
1. **Via CSV**: Add to `symbols_to_trade.csv` and restart service
2. **Via API**: Use `POST /subscribe` endpoint
3. **Via Code**: Update `symbol_tokens` mapping in `main.py`

### **Symbol-Token Mapping**
```python
symbol_tokens = {
    "RELIANCE": "2881",
    "TCS": "11536", 
    "INFY": "408065",
    "HDFC": "1333",
    "ICICIBANK": "4963",
    # ... more symbols
}
```

## 🧪 **Testing**

### **Consumer Library Tests**
```bash
python3 test_redis_consumer.py
```

### **Usage Examples**
```bash
python3 consumer_examples.py
```

### **Service Health Check**
```bash
curl http://localhost:8001/health | python3 -m json.tool
```

### **Service Statistics**
```bash
curl http://localhost:8001/stats | python3 -m json.tool
```

## ⚠️ **Important Notes**

1. **Market Hours**: WebSocket only works during market hours (9:15 AM - 3:30 PM IST)
2. **Authentication**: Ensure valid Angel One credentials in `config.py`
3. **Redis Server**: Ensure Redis server is running and accessible
4. **Token Format**: Use correct exchange types (1=NSE CM, 2=BSE CM, etc.)

## 🔧 **Troubleshooting**

### **Common Issues**

1. **No Ticks Received**
   - Check if market is open
   - Verify symbol-token mapping
   - Check WebSocket connection status

2. **Redis Connection Failed**
   - Ensure Redis server is running
   - Check REDIS_URL configuration
   - Verify network connectivity

3. **Authentication Failed**
   - Check Angel One credentials
   - Verify TOTP secret
   - Ensure API key is valid

### **Logs**
- Service logs: Docker logs
- Angel One logs: `ANGEL_WEBSOCKET_{date}.log`
- Redis logs: Redis server logs

## 🎯 **Benefits of Redis Streams System**

1. **Clean Architecture** - Modular, maintainable design
2. **Class-Based** - Professional, reusable components
3. **Redis Streams** - Reliable message delivery with persistence
4. **REST API** - Easy monitoring and management
5. **Error Handling** - Comprehensive error management
6. **Scalability** - Easy to extend and scale
7. **Testing** - Built-in test scripts
8. **Persistence** - Messages are stored and can be replayed
9. **Consumer Groups** - Multiple consumers can process the same stream

## 🔗 **Integration Examples**

### **With Trading Strategies**
```python
from redis_consumer import create_redis_consumer

async def trading_strategy():
    consumer = create_redis_consumer()
    await consumer.connect()
    
    def handle_tick(tick):
        if tick.symbol == "RELIANCE" and tick.change_percent > 2:
            # Trigger buy signal
            pass
    
    consumer.add_message_handler(handle_tick)
    await consumer.subscribe_to_symbol("RELIANCE")
```

### **With Database Storage**
```python
async def store_ticks():
    consumer = create_redis_consumer()
    await consumer.connect()
    
    def store_tick(tick):
        # Store in database
        db.insert_tick(tick)
    
    consumer.add_message_handler(store_tick)
    await consumer.subscribe_to_multiple_symbols(["RELIANCE", "TCS"])
```

## 🚀 **Redis Streams Advantages**

1. **Persistence** - Messages are stored and survive restarts
2. **Consumer Groups** - Multiple consumers can process streams independently
3. **Message Acknowledgment** - Reliable message processing
4. **Stream Trimming** - Automatic cleanup of old messages
5. **Range Queries** - Efficient historical data access
6. **Backpressure Handling** - Built-in flow control
7. **Clustering** - Redis Cluster support for high availability

This Redis Streams system provides a clean, professional, and scalable foundation for real-time market data streaming! 🎉