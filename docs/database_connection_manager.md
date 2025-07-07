# Centralized Database Connection Manager

## Overview

The trading backend system now uses a centralized database connection manager to prevent connection pool exhaustion and provide a single point of database access across all modules.

## Benefits

### 1. **Connection Pool Management**
- **Pool Size**: 5 maintained connections
- **Max Overflow**: 10 additional connections when needed
- **Connection Validation**: Pre-ping connections before use
- **Connection Recycling**: Recycle connections after 1 hour
- **Thread Safety**: Scoped sessions for concurrent access

### 2. **Resource Efficiency**
- **Single Connection Pool**: All modules share the same connection pool
- **Automatic Cleanup**: Connections are automatically closed and returned to the pool
- **Connection Reuse**: Reduces database connection overhead
- **Memory Optimization**: Prevents connection leaks

### 3. **Error Handling**
- **Automatic Rollback**: Failed transactions are automatically rolled back
- **Connection Recovery**: Invalid connections are automatically replaced
- **Graceful Degradation**: System continues working even if some connections fail

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Database Manager                        │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────┐ │
│  │   Connection    │  │   Session       │  │   Scoped    │ │
│  │     Pool        │  │   Factory       │  │   Session   │ │
│  └─────────────────┘  └─────────────────┘  └─────────────┘ │
└─────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────┐
│                    Application Modules                      │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐        │
│  │   Config    │  │   User      │  │   Order     │        │
│  │   Loader    │  │   Service   │  │   Manager   │        │
│  └─────────────┘  └─────────────┘  └─────────────┘        │
└─────────────────────────────────────────────────────────────┘
```

## Usage

### Basic Usage

```python
from shared.database import get_db_session, get_db_scoped_session

# Regular session (auto-commit, auto-close)
with get_db_session() as session:
    result = session.query(User).all()
    # Session automatically commits and closes

# Scoped session (thread-safe)
with get_db_scoped_session() as session:
    result = session.query(User).all()
    # Session automatically commits and removes from registry
```

### Testing Connection

```python
from shared.database import test_db_connection

if test_db_connection():
    print("Database connection successful")
else:
    print("Database connection failed")
```

### Cleanup

```python
from shared.database import close_db_connections

# Close all connections (call on application shutdown)
close_db_connections()
```

## Configuration

### Environment Variables

```bash
# Optional: Override default database URL
export DATABASE_URL="postgresql+psycopg2://user:pass@host:port/db?sslmode=require"
```

### Connection Pool Settings

```python
# Current settings in shared/database.py
pool_size=5          # Number of connections to maintain
max_overflow=10      # Additional connections when needed
pool_pre_ping=True   # Validate connections before use
pool_recycle=3600    # Recycle connections after 1 hour
```

## Modules Updated

### 1. **Config Loader** (`shared/config.py`)
- Removed individual database connection
- Uses centralized `get_db_session()`
- Loads strategies from database

### 2. **User Service** (`shared/user_service.py`)
- Removed individual database connection
- Uses centralized `get_db_session()`
- Fetches active users from PostgreSQL

### 3. **Order Manager** (`order/manager.py`)
- Removed individual database connection
- Uses centralized `get_db_session()`
- Saves orders to database

## Testing

Run the comprehensive test suite:

```bash
python scripts/test_db_connection.py
```

This tests:
- ✅ Basic database connection
- ✅ Config loader with database
- ✅ User service with database
- ✅ Order manager with database
- ✅ Concurrent database access

## Performance Benefits

### Before (Multiple Connections)
```
Module 1: 1 connection
Module 2: 1 connection
Module 3: 1 connection
Module 4: 1 connection
Total: 4+ connections
```

### After (Centralized Pool)
```
All Modules: Shared connection pool (5-15 connections)
Total: 5-15 connections (efficiently shared)
```

## Monitoring

### Connection Pool Status

```python
from shared.database import get_db_engine

engine = get_db_engine()
pool = engine.pool

print(f"Pool size: {pool.size()}")
print(f"Checked out connections: {pool.checkedout()}")
print(f"Overflow connections: {pool.overflow()}")
```

### Logging

The database manager provides detailed logging:
- Connection initialization
- Session creation/cleanup
- Error handling
- Connection pool status

## Best Practices

1. **Always use context managers**: `with get_db_session() as session:`
2. **Handle exceptions properly**: Let the context manager handle rollback
3. **Don't hold sessions**: Sessions are automatically closed
4. **Use scoped sessions for threads**: `get_db_scoped_session()`
5. **Test connections**: Use `test_db_connection()` for health checks

## Migration Notes

- All existing database code continues to work
- No breaking changes to existing APIs
- Improved performance and reliability
- Better resource management
- Enhanced error handling

## Troubleshooting

### Common Issues

1. **Connection Timeout**
   - Check network connectivity
   - Verify database URL
   - Increase connection timeout

2. **Pool Exhaustion**
   - Increase `pool_size` and `max_overflow`
   - Check for connection leaks
   - Monitor connection usage

3. **Authentication Errors**
   - Verify database credentials
   - Check SSL configuration
   - Ensure proper permissions

### Debug Mode

Enable SQL logging:

```python
# In shared/database.py, set echo=True
self._engine = create_engine(
    db_url,
    poolclass=QueuePool,
    pool_size=5,
    max_overflow=10,
    pool_pre_ping=True,
    pool_recycle=3600,
    echo=True  # Enable SQL logging
)
``` 