# Clean Categorized Market Data Service

A clean, production-ready implementation for organizing AngelOne instruments into categorized buckets with pure Redis storage.

## 🎯 Features

- **Pure Redis Implementation**: No database schema changes required
- **Clean Categorization**: Instruments organized into 6 logical categories
- **High Performance**: Efficient Redis-based storage and retrieval
- **Daily Auto-Updates**: Scheduled 9:00 AM instrument refreshes
- **Smart Search**: Search across categories with filtering
- **Clean API**: Simple, intuitive interface

## 📂 Instrument Categories

All **115,563** AngelOne instruments are organized into these categories:

| Category | Count | Description | Exchanges |
|----------|--------|-------------|-----------|
| **EQUITY** | 17,924 | Cash equity stocks | NSE, BSE |
| **OPTIONS** | 95,043 | All option contracts | NSE, BSE, MCX, CDS, BFO, NCO |
| **FUTURES** | 1,825 | All future contracts | NSE, BSE, MCX, CDS, BFO, NCO |
| **COMMODITY** | 554 | Commodity instruments | MCX, NCDEX |
| **CURRENCY** | 93 | Currency instruments | CDS |
| **INDEX** | 124 | Index instruments | NSE, BSE, MCX, CDS, NCDEX |

## 🚀 Quick Start

### 1. Setup Environment

```bash
# Set your AngelOne credentials
export ANGELONE_API_KEY="your_api_key"
export ANGELONE_CLIENT_ID="your_client_id"  
export ANGELONE_PASSWORD="your_password"
export ANGELONE_TOTP_TOKEN="your_totp_secret"
```

### 2. Initialize Service

```python
from app.services.categorized_redis_market_data import create_categorized_service

# Create broker config
broker_config = {
    'api_key': os.getenv('ANGELONE_API_KEY'),
    'client_id': os.getenv('ANGELONE_CLIENT_ID'),
    'password': os.getenv('ANGELONE_PASSWORD'),
    'totp_token': os.getenv('ANGELONE_TOTP_TOKEN')
}

# Initialize service
service = await create_categorized_service(broker_config)
```

### 3. Basic Usage

```python
# Get category summary
summary = await service.get_category_summary()
print(f"EQUITY: {summary['EQUITY']['count']:,} instruments")

# Get instruments by category
equity_instruments = await service.get_category_instruments('EQUITY')
print(f"Found {len(equity_instruments):,} equity instruments")

# Search instruments
results = await service.search_instruments('NIFTY', category='INDEX')
for result in results:
    print(f"{result['symbol']} - {result['name']}")

# Search with filters
bank_stocks = await service.search_instruments('BANK', category='EQUITY', exchange='NSE')
```

## 🗂️ Data Structure

Each instrument is stored with the following clean structure:

```json
{
  "token": "1333",
  "symbol": "HDFCBANK-EQ", 
  "name": "HDFC Bank Ltd",
  "exchange": "NSE",
  "instrument_type": "EQUITY",
  "lot_size": 1,
  "tick_size": 0.05
}
```

## 🔍 API Reference

### Core Methods

#### `get_category_summary()`
Get overview of all categories with counts and exchanges.

#### `get_category_instruments(category: str)`
Get all instruments from a specific category.
- `category`: 'EQUITY', 'OPTIONS', 'FUTURES', 'COMMODITY', 'CURRENCY', 'INDEX'

#### `search_instruments(query, category=None, exchange=None, limit=50)`
Search instruments with optional filters.
- `query`: Search term (matches symbol or name)
- `category`: Filter by category (optional)
- `exchange`: Filter by exchange (optional)  
- `limit`: Maximum results (default: 50)

#### `get_metrics()`
Get service performance metrics.

### Redis Keys

The service uses these Redis keys:

- `instruments:category:equity` - Equity instruments
- `instruments:category:options` - Options instruments  
- `instruments:category:futures` - Futures instruments
- `instruments:category:commodity` - Commodity instruments
- `instruments:category:currency` - Currency instruments
- `instruments:category:index` - Index instruments
- `instruments:summary` - Category summary
- `instruments:last_update` - Last update timestamp
- `instruments:raw` - Raw instrument data backup

## 🔄 Data Updates

### Automatic Updates
- Daily at 9:00 AM IST (before market opening)
- Downloads fresh instruments from AngelOne API
- Automatically categorizes and stores in Redis

### Manual Updates
```python
# Force update
await service.download_and_categorize()
```

### Organization Script
Use the organization script to process existing data:

```bash
python organize_instruments.py
```

## 🧪 Testing

Run the test suite to verify functionality:

```bash
python test_clean_service.py
```

This will test:
- Service initialization
- Category loading
- Search functionality  
- Data structure validation

## 📊 Performance

- **Fast Retrieval**: Redis-based storage provides millisecond access
- **Memory Efficient**: Clean data structure reduces memory usage
- **Scalable**: Can handle 100K+ instruments efficiently
- **Categorized Access**: Quick filtering by instrument type

## 🛠️ Scripts

| Script | Purpose |
|--------|---------|
| `organize_instruments.py` | Organize existing instruments into categories |
| `test_clean_service.py` | Test service functionality |
| `app/services/categorized_redis_market_data.py` | Main service implementation |

## 🎯 Use Cases

### Trading Applications
```python
# Get all NSE equity stocks
equity = await service.get_category_instruments('EQUITY')
nse_stocks = {k: v for k, v in equity.items() if v['exchange'] == 'NSE'}

# Find option contracts for a stock
nifty_options = await service.search_instruments('NIFTY', category='OPTIONS')
```

### Analytics
```python
# Get instruments by exchange
summary = await service.get_category_summary()
for category, info in summary.items():
    print(f"{category}: {', '.join(info['exchanges'])}")
```

### Symbol Management
```python
# Search for specific symbols
results = await service.search_instruments('INFY', category='EQUITY')
if results:
    token = results[0]['token']
    # Use token for trading/data subscription
```

## ✅ Benefits

1. **No Database Overhead**: Pure Redis implementation
2. **Clean Organization**: Logical instrument categorization
3. **High Performance**: Fast Redis-based access
4. **Auto-Updates**: Daily data refresh
5. **Easy Integration**: Simple, clean API
6. **Production Ready**: Robust error handling and logging

## 🔧 Configuration

The service can be configured with:

- **Redis URL**: Default `redis://localhost:6379`
- **Update Schedule**: Default daily at 9:00 AM
- **Category Mapping**: Customizable instrument type mapping

## 📈 Monitoring

Monitor service health with:

```python
metrics = await service.get_metrics()
print(f"Total instruments: {metrics['total_instruments']:,}")
print(f"Categories: {metrics['categories_count']}")
print(f"Last update: {metrics['last_update']}")
print(f"Status: {metrics['download_status']}")
```

---

This implementation provides a clean, efficient solution for managing AngelOne instruments with proper categorization and no database dependencies. 