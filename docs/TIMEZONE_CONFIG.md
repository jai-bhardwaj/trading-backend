# Trading Backend - IST Timezone Configuration

## Overview
The entire trading backend system is configured to use **IST (Indian Standard Time)** for all services, logs, and data timestamps.

## Configuration Files

### 1. Centralized Timezone Configuration
- **File**: `config/timezone.env`
- **Purpose**: Centralized timezone environment variables
- **Usage**: Can be sourced by scripts or referenced in documentation

### 2. Shared Timezone Utility
- **File**: `shared/timezone.py`
- **Purpose**: Python utility module for IST timezone operations
- **Functions**:
  - `get_ist_now()`: Get current time in IST
  - `get_ist_timestamp()`: Get current timestamp in IST as ISO format
  - `convert_to_ist(dt)`: Convert datetime to IST
  - `format_ist_time(dt)`: Format datetime in IST for logging

## Docker Configuration

### Environment Variables
All Docker services have the following timezone configuration:
```yaml
environment:
  TZ: Asia/Kolkata
```

### Services Updated
- ✅ Redis (`trading-redis`)
- ✅ PostgreSQL (`trading-postgres`)
- ✅ Trading API (`trading-api`)
- ✅ Market Data Service (`market-data-service`)
- ✅ Test Strategy (`test-strategy`)
- ✅ RSI DMI Strategy (`rsi-dmi-strategy`)
- ✅ RSI DMI Intraday Strategy (`rsi-dmi-intraday-strategy`)
- ✅ BTST Momentum Strategy (`btst-momentum-strategy`)
- ✅ Swing Momentum Strategy (`swing-momentum-strategy`)

## Code Updates

### Strategy Files
All strategy files (`strategy.py`) have been updated to:
- Import IST timezone utilities
- Use `get_ist_now()` instead of `datetime.now()`
- Use `get_ist_timestamp()` instead of `datetime.now().isoformat()`

### Base Framework
- **Base Strategy**: Updated to use IST timestamps
- **Signal Publisher**: Updated to use IST timestamps
- **Market Data Consumer**: Updated to use IST timestamps
- **Market Data Service**: Updated to use IST timestamps

### Dependencies
Added `pytz==2025.2` to all strategy `requirements.txt` files for timezone support.

## Verification

### Container Timezone
```bash
docker-compose exec test-strategy date
# Output: Wed Oct 15 13:51:25 IST 2025
```

### Application Logs
All application logs now show IST timestamps:
```
2025-10-15 13:51:21,041 - base.signal_publisher - INFO - 📊 Published signal: RELIANCE BUY @ 0.0
```

### Redis Data
Market data in Redis streams now has IST timestamps:
```
timestamp: 2025-10-15T13:51:33.037256
exchange_timestamp: 2025-10-15T13:51:33
```

## Usage in Code

### Import IST Utilities
```python
from shared.timezone import get_ist_now, get_ist_timestamp, convert_to_ist, format_ist_time
```

### Get Current IST Time
```python
# Get current IST datetime
current_time = get_ist_now()

# Get current IST timestamp as ISO string
timestamp = get_ist_timestamp()
```

### Convert Existing Datetime to IST
```python
# Convert UTC datetime to IST
ist_time = convert_to_ist(utc_datetime)
```

### Format for Logging
```python
# Format datetime for logging
log_time = format_ist_time()  # Uses current time
log_time = format_ist_time(some_datetime)  # Uses specific datetime
```

## Benefits

1. **Consistency**: All services use the same timezone
2. **Clarity**: Logs and data are in local Indian time
3. **Debugging**: Easier to correlate events across services
4. **Compliance**: Aligns with Indian market hours and regulations
5. **Centralized**: Single point of configuration for timezone changes

## Maintenance

To change timezone in the future:
1. Update `config/timezone.env`
2. Update `shared/timezone.py` 
3. Update Docker environment variables
4. Restart all services

The system is now fully configured for IST timezone across all components! 🇮🇳
