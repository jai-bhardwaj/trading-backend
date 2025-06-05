# Trading Backend - Industrial Architecture

A comprehensive, industrial-grade algorithmic trading backend system built with clean architecture principles, focusing on scalability, maintainability, and reliability.

## 🏗️ Architecture Overview

This project follows **Clean Architecture** principles with clear separation of concerns:

- **Domain Layer** (`src/trading/core/`): Core business logic, entities, and repository interfaces
- **Application Layer** (`src/trading/application/`): Use cases, application services, and orchestration
- **Infrastructure Layer** (`src/trading/infrastructure/`): External concerns (database, brokers, queues)
- **Presentation Layer** (`src/trading/presentation/`): API endpoints, CLI commands, WebSocket handlers

## ✨ Key Features

- 🏛️ **Clean Architecture** with SOLID principles
- 🔄 **Event-Driven Architecture** with domain events
- 💉 **Dependency Injection** for loose coupling
- 📊 **Comprehensive Monitoring** with metrics and tracing
- 🔒 **Security-First** design with proper authentication
- 🧪 **Test-Driven Development** with >90% coverage
- 🐳 **Containerized** deployment ready
- 📈 **Multi-Broker Support** (Angel One, Zerodha, etc.)
- ⚡ **Real-Time Processing** with WebSocket support
- 🛡️ **Advanced Risk Management**

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- PostgreSQL 14+
- Redis 6+
- Docker (optional)

### Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd trading-backend
   ```

2. **Set up virtual environment**
   ```bash
   make venv
   source .venv/bin/activate
   ```

3. **Install dependencies**
   ```bash
   make install-dev
   ```

4. **Configure environment**
   ```bash
   cp env.example .env
   # Edit .env with your configuration
   ```

5. **Set up database**
   ```bash
   make migrate
   make seed
   ```

6. **Run the application**
   ```bash
   make run-dev
   ```

The API will be available at `http://localhost:8000`

## 📁 Project Structure

```
trading-backend/
├── src/trading/                    # Main source code
│   ├── core/                       # Domain layer
│   │   ├── entities/               # Business entities
│   │   ├── services/               # Business services
│   │   ├── repositories/           # Repository interfaces
│   │   └── exceptions/             # Custom exceptions
│   ├── infrastructure/             # Infrastructure layer
│   │   ├── database/               # Database implementations
│   │   ├── brokers/                # Broker implementations
│   │   ├── queues/                 # Queue implementations
│   │   └── monitoring/             # Monitoring implementations
│   ├── application/                # Application layer
│   │   ├── services/               # Application services
│   │   ├── handlers/               # Command/Query handlers
│   │   └── events/                 # Event handlers
│   ├── presentation/               # Presentation layer
│   │   ├── api/                    # REST API
│   │   ├── websocket/              # WebSocket endpoints
│   │   └── cli/                    # CLI commands
│   └── shared/                     # Shared utilities
│       ├── config/                 # Configuration management
│       ├── logging/                # Logging setup
│       ├── utils/                  # Utility functions
│       └── types/                  # Type definitions
├── tests/                          # Test suite
├── docs/                           # Documentation
├── deploy/                         # Deployment files
├── config/                         # Configuration files
└── scripts/                        # Utility scripts
```

## 🛠️ Development

### Available Commands

```bash
# Development
make install-dev          # Install development dependencies
make run-dev              # Run development server
make run-worker           # Run celery worker
make run-scheduler        # Run celery beat scheduler

# Code Quality
make format               # Format code with black and isort
make lint                 # Run linting checks
make type-check          # Run type checking with mypy
make security-check      # Run security checks

# Testing
make test                # Run all tests
make test-unit           # Run unit tests
make test-integration    # Run integration tests
make test-e2e           # Run end-to-end tests
make coverage           # Generate coverage report

# Database
make migrate            # Run database migrations
make migrate-create     # Create new migration
make seed              # Seed database with sample data

# Docker
make docker-build      # Build Docker image
make docker-run        # Run application in Docker
make docker-compose-up # Start all services

# Documentation
make docs              # Build documentation
make docs-serve        # Serve documentation locally

# Deployment
make deploy-staging    # Deploy to staging
make deploy-prod      # Deploy to production
```

### Code Style

This project follows strict code quality standards:

- **Black** for code formatting
- **isort** for import sorting
- **flake8** for linting
- **mypy** for type checking
- **bandit** for security analysis

Run `make pre-commit` before committing changes.

## 🔧 Configuration

### Environment Variables

Key environment variables (see `env.example` for complete list):

```bash
# Environment
ENVIRONMENT=development
DEBUG=true

# Database
DB_HOST=localhost
DB_PASSWORD=your_password

# Broker Credentials
ANGEL_ONE_API_KEY=your_api_key
ANGEL_ONE_CLIENT_ID=your_client_id
ANGEL_ONE_PASSWORD=your_password
ANGEL_ONE_TOTP_SECRET=your_totp_secret

# Security
SECRET_KEY=your_secret_key
```

### Configuration Files

Environment-specific configurations in `config/`:

- `development.yaml` - Development settings
- `staging.yaml` - Staging settings
- `production.yaml` - Production settings

## 📊 API Documentation

### REST API

The API follows RESTful principles with comprehensive OpenAPI documentation:

- **Swagger UI**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`

### Key Endpoints

```
GET    /health                    # Health check
POST   /api/v1/orders            # Create order
GET    /api/v1/orders            # List orders
GET    /api/v1/orders/{id}       # Get order details
PUT    /api/v1/orders/{id}       # Update order
DELETE /api/v1/orders/{id}       # Cancel order

GET    /api/v1/positions         # List positions
GET    /api/v1/strategies        # List strategies
POST   /api/v1/strategies        # Create strategy
```

### WebSocket API

Real-time data streams:

```
ws://localhost:8000/ws/orders     # Order updates
ws://localhost:8000/ws/positions  # Position updates
ws://localhost:8000/ws/market     # Market data
```

## 📈 Monitoring & Observability

### Metrics

- **Prometheus** metrics at `/metrics`
- Custom business metrics for orders, positions, and strategies
- Performance metrics for API endpoints

### Logging

- **Structured logging** with JSON format
- **Correlation IDs** for request tracing
- **Log levels**: DEBUG, INFO, WARNING, ERROR, CRITICAL

### Health Checks

- **Liveness probe**: `/health`
- **Readiness probe**: `/health/ready`
- **Database connectivity**: `/health/db`
- **Redis connectivity**: `/health/redis`

## 🐳 Deployment

### Docker

```bash
# Build image
make docker-build

# Run with docker-compose
make docker-compose-up
```

### Kubernetes

Kubernetes manifests available in `deploy/k8s/`:

```bash
kubectl apply -f deploy/k8s/
```

### Production Considerations

- Use environment-specific configuration files
- Set up proper secrets management
- Configure load balancing and auto-scaling
- Set up monitoring and alerting
- Implement backup and disaster recovery

## 🔒 Security

### Authentication & Authorization

- **JWT tokens** for API authentication
- **Role-based access control** (RBAC)
- **API rate limiting**
- **CORS configuration**

### Security Best Practices

- Secrets stored in environment variables
- Database connections use SSL
- API endpoints protected with authentication
- Input validation and sanitization
- Security headers in HTTP responses

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Run quality checks (`make pre-commit`)
5. Commit your changes (`git commit -m 'Add amazing feature'`)
6. Push to the branch (`git push origin feature/amazing-feature`)
7. Open a Pull Request

### Development Guidelines

- Follow clean architecture principles
- Update documentation
- Follow code style guidelines
- Add proper logging and monitoring

## 📚 Documentation

- **Architecture**: `docs/architecture/`
- **API Reference**: `docs/api/`
- **Deployment Guide**: `docs/deployment/`
- **User Guide**: `docs/user_guide/`

Build documentation locally:

```bash
make docs-serve
```

## 🐛 Troubleshooting

### Common Issues

1. **Database Connection Issues**
   ```bash
   # Check database status
   make health-check
   
   # Reset database
   make migrate-downgrade
   make migrate
   ```

2. **Redis Connection Issues**
   ```bash
   # Check Redis status
   redis-cli ping
   
   # Restart Redis
   sudo systemctl restart redis
   ```

3. **Import Errors**
   ```bash
   # Reinstall dependencies
   make clean
   make install-dev
   ```

### Logs

Check application logs:

```bash
# Tail logs
make logs

# Check specific log file
tail -f logs/trading.log
```

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- FastAPI for the excellent web framework
- SQLAlchemy for robust ORM capabilities
- Pydantic for data validation
- The Python trading community for inspiration

---

For more information, please refer to the [documentation](docs/) or open an issue. 