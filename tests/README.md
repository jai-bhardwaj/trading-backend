# Trading Backend Test Suite

A comprehensive, modular test suite for the trading backend system covering unit tests, integration tests, performance tests, and security tests.

## 🏗️ Test Architecture

The test suite is organized into modular components:

```
tests/
├── conftest.py                 # Shared fixtures and configuration
├── unit/                       # Unit tests for individual components
│   ├── test_auth_service.py
│   ├── test_market_data_service.py
│   ├── test_order_management_service.py
│   ├── test_risk_management_service.py
│   ├── test_strategy_engine_service.py
│   └── test_portfolio_service.py
├── integration/                # Integration tests for workflows
│   └── test_trading_workflow.py
├── performance/                # Performance and load tests
│   └── test_performance_benchmarks.py
├── security/                   # Security validation tests
│   └── test_security_validation.py
├── run_tests.py               # Test runner script
└── README.md                  # This file
```

## 🚀 Quick Start

### Prerequisites

1. **Install dependencies:**

   ```bash
   pip install -r requirements-test.txt
   ```

2. **Start Redis server:**

   ```bash
   redis-server
   ```

3. **Run all tests:**
   ```bash
   python tests/run_tests.py
   ```

### Test Runner Options

```bash
# Run specific test types
python tests/run_tests.py --type unit
python tests/run_tests.py --type integration
python tests/run_tests.py --type security
python tests/run_tests.py --type performance

# Run with coverage
python tests/run_tests.py --coverage

# Run specific test file
python tests/run_tests.py --test tests/unit/test_auth_service.py

# Run tests with specific markers
python tests/run_tests.py --marker "unit"
python tests/run_tests.py --marker "integration"
python tests/run_tests.py --marker "security"
python tests/run_tests.py --marker "performance"

# Setup environment only
python tests/run_tests.py --setup-only
```

## 📋 Test Categories

### Unit Tests (`tests/unit/`)

Test individual components in isolation with mocked dependencies.

**Coverage:**

- Authentication and authorization
- Market data processing
- Order management logic
- Risk assessment algorithms
- Strategy execution
- Portfolio calculations

**Example:**

```python
@pytest.mark.unit
async def test_place_order_success(self, mock_order_data):
    """Test successful order placement."""
    with patch('services.order_management.order_manager.OrderManager') as mock_manager:
        mock_manager.return_value.place_order.return_value = {
            "status": "success",
            "order_id": mock_order_data["order_id"]
        }

        result = await mock_manager.return_value.place_order(mock_order_data)

        assert result["status"] == "success"
        assert result["order_id"] == mock_order_data["order_id"]
```

### Integration Tests (`tests/integration/`)

Test complete workflows and service interactions.

**Coverage:**

- Complete trading workflows
- Order placement to execution
- Portfolio updates
- Strategy execution flows
- Risk monitoring workflows

**Example:**

```python
@pytest.mark.integration
async def test_buy_order_workflow(self, test_user, test_broker, clean_redis):
    """Test complete buy order workflow."""
    # Tests authentication → market data → risk check → order placement → portfolio update
```

### Performance Tests (`tests/performance/`)

Test system performance under various load conditions.

**Coverage:**

- Load testing
- Stress testing
- Throughput benchmarks
- Latency measurements
- Memory usage monitoring
- Concurrent user simulation

**Example:**

```python
@pytest.mark.performance
async def test_market_data_load(self, clean_redis):
    """Test market data service performance under load."""
    # Tests 100 concurrent requests with performance assertions
```

### Security Tests (`tests/security/`)

Test security measures and vulnerability prevention.

**Coverage:**

- Authentication security
- Authorization controls
- Input validation
- Data protection
- Session management
- API security

**Example:**

```python
@pytest.mark.security
async def test_sql_injection_prevention(self):
    """Test SQL injection prevention."""
    malicious_inputs = [
        "'; DROP TABLE users; --",
        "' OR '1'='1"
    ]
    # Tests that malicious inputs are properly rejected
```

## 🔧 Test Configuration

### Shared Fixtures (`conftest.py`)

The test suite provides comprehensive fixtures for:

- **Redis connections** with automatic cleanup
- **Mock data** for users, orders, portfolios, etc.
- **Test environment** setup and teardown
- **External API mocking**
- **Database test data**

### Test Markers

Tests are categorized using pytest markers:

- `@pytest.mark.unit` - Unit tests
- `@pytest.mark.integration` - Integration tests
- `@pytest.mark.performance` - Performance tests
- `@pytest.mark.security` - Security tests
- `@pytest.mark.e2e` - End-to-end tests

### Environment Variables

Tests use these environment variables:

```bash
TESTING=true
REDIS_URL=redis://localhost:6379/1
MOCK_EXTERNAL_APIS=true
LOG_LEVEL=DEBUG
```

## 📊 Test Data Management

### Mock Data Fixtures

The test suite provides realistic mock data:

```python
@pytest.fixture
def mock_user_data():
    return {
        "user_id": "test_user_123",
        "username": "testuser",
        "email": "test@example.com",
        "password_hash": "hashed_password_123",
        "is_active": True
    }

@pytest.fixture
def mock_order_data():
    return {
        "order_id": "order_123",
        "user_id": "test_user_123",
        "symbol": "RELIANCE",
        "quantity": 100,
        "price": 2500.00,
        "order_type": "BUY"
    }
```

### Database Cleanup

Tests automatically clean up test data:

- Redis database is flushed before each test
- Test users and brokers are created and cleaned up
- Temporary files are removed
- Mock services are reset

## 🎯 Running Specific Tests

### Run by Service

```bash
# Auth service tests
pytest tests/unit/test_auth_service.py -v

# Market data tests
pytest tests/unit/test_market_data_service.py -v

# Order management tests
pytest tests/unit/test_order_management_service.py -v
```

### Run by Test Type

```bash
# All unit tests
pytest tests/unit/ -v

# All integration tests
pytest tests/integration/ -v

# All performance tests
pytest tests/performance/ -v

# All security tests
pytest tests/security/ -v
```

### Run with Coverage

```bash
# Run with coverage report
pytest tests/ --cov=services --cov=shared --cov-report=html

# View coverage report
open htmlcov/index.html
```

## 🔍 Test Debugging

### Verbose Output

```bash
pytest tests/ -v -s --tb=long
```

### Debug Specific Test

```bash
# Run single test with debug output
pytest tests/unit/test_auth_service.py::TestAuthenticationService::test_authenticate_user_success -v -s

# Run with print statements
pytest tests/ -v -s --capture=no
```

### Test Isolation

```bash
# Run tests in isolation
pytest tests/ --dist=no

# Run tests sequentially
pytest tests/ -n0
```

## 📈 Performance Testing

### Load Testing

```bash
# Run load tests
pytest tests/performance/test_performance_benchmarks.py::TestLoadTesting -v

# Run with specific parameters
pytest tests/performance/ -k "test_market_data_load" -v
```

### Benchmark Results

Performance tests provide detailed metrics:

- **Latency**: Average, 95th percentile, 99th percentile
- **Throughput**: Requests per second
- **Memory Usage**: Peak memory consumption
- **CPU Usage**: Processor utilization
- **Success Rate**: Percentage of successful operations

## 🔒 Security Testing

### Vulnerability Scanning

```bash
# Run security tests
pytest tests/security/ -v

# Run specific security test
pytest tests/security/test_security_validation.py::TestInputValidationSecurity::test_sql_injection_prevention -v
```

### Security Coverage

Security tests validate:

- **Authentication**: Password hashing, JWT tokens, brute force protection
- **Authorization**: Role-based access, resource ownership
- **Input Validation**: SQL injection, XSS prevention, data type validation
- **Data Protection**: Encryption, masking, audit logging
- **Session Security**: Session management, concurrent session control
- **API Security**: CORS, request signatures, rate limiting

## 🛠️ Continuous Integration

### GitHub Actions Example

```yaml
name: Tests
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    services:
      redis:
        image: redis
        ports:
          - 6379:6379
    steps:
      - uses: actions/checkout@v2
      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: 3.11
      - name: Install dependencies
        run: pip install -r requirements-test.txt
      - name: Run tests
        run: python tests/run_tests.py --coverage
```

## 📝 Test Development

### Adding New Tests

1. **Unit Tests**: Add to appropriate service file in `tests/unit/`
2. **Integration Tests**: Add to `tests/integration/test_trading_workflow.py`
3. **Performance Tests**: Add to `tests/performance/test_performance_benchmarks.py`
4. **Security Tests**: Add to `tests/security/test_security_validation.py`

### Test Naming Convention

- Test classes: `Test[ServiceName]`
- Test methods: `test_[functionality]_[scenario]`
- Example: `test_place_order_success`, `test_authenticate_user_invalid_credentials`

### Best Practices

1. **Use descriptive test names**
2. **Test both success and failure scenarios**
3. **Mock external dependencies**
4. **Clean up test data**
5. **Use appropriate assertions**
6. **Add performance benchmarks for critical paths**

## 🐛 Troubleshooting

### Common Issues

1. **Redis Connection Failed**

   ```bash
   # Start Redis server
   redis-server
   ```

2. **Import Errors**

   ```bash
   # Install dependencies
   pip install -r requirements-test.txt
   ```

3. **Test Timeouts**

   ```bash
   # Increase timeout
   pytest tests/ --timeout=600
   ```

4. **Memory Issues**
   ```bash
   # Run tests with memory monitoring
   pytest tests/ --maxfail=1
   ```

### Debug Mode

```bash
# Run with debug logging
LOG_LEVEL=DEBUG pytest tests/ -v -s

# Run specific test with debug
pytest tests/unit/test_auth_service.py::TestAuthenticationService::test_authenticate_user_success -v -s --pdb
```

## 📚 Additional Resources

- [pytest Documentation](https://docs.pytest.org/)
- [pytest-asyncio](https://pytest-asyncio.readthedocs.io/)
- [Redis Testing](https://redis.io/topics/testing)
- [Performance Testing Best Practices](https://martinfowler.com/articles/microservice-testing/)

## 🤝 Contributing

When adding new tests:

1. Follow the existing patterns and structure
2. Add appropriate test markers
3. Include both positive and negative test cases
4. Add performance tests for critical paths
5. Update this README if adding new test categories
