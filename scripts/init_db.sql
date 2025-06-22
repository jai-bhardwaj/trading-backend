-- Trading System Database Initialization
-- Production-optimized schema with indexes

-- Create extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_stat_statements";

-- Create database (if running as superuser)
-- CREATE DATABASE trading_db OWNER trading_user;

-- Connect to trading database
\c trading_db;

-- Grant privileges to trading user
GRANT ALL PRIVILEGES ON DATABASE trading_db TO trading_user;
GRANT ALL PRIVILEGES ON SCHEMA public TO trading_user;

-- Set timezone
SET timezone = 'UTC';

-- Create users table
CREATE TABLE IF NOT EXISTS users (
    user_id VARCHAR(50) PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    name VARCHAR(255) NOT NULL,
    api_key VARCHAR(255) UNIQUE NOT NULL,
    total_capital DECIMAL(15,2) DEFAULT 100000.00,
    risk_tolerance VARCHAR(20) DEFAULT 'medium',
    status VARCHAR(20) DEFAULT 'ACTIVE',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create strategies table
CREATE TABLE IF NOT EXISTS strategies (
    strategy_id VARCHAR(50) PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    category VARCHAR(50),
    risk_level VARCHAR(20),
    min_capital DECIMAL(15,2),
    expected_return_annual DECIMAL(5,2),
    max_drawdown DECIMAL(5,2),
    symbols TEXT[], -- Array of symbols
    parameters JSONB,
    status VARCHAR(20) DEFAULT 'ACTIVE',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create user_strategies table (CORE TABLE)
CREATE TABLE IF NOT EXISTS user_strategies (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(50) NOT NULL,
    strategy_id VARCHAR(50) NOT NULL,
    enabled BOOLEAN DEFAULT true,
    quantity_multiplier DECIMAL(5,2) DEFAULT 1.0,
    max_position_size DECIMAL(15,2),
    risk_multiplier DECIMAL(5,2) DEFAULT 1.0,
    custom_parameters JSONB,
    activated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
    FOREIGN KEY (strategy_id) REFERENCES strategies(strategy_id) ON DELETE CASCADE,
    UNIQUE(user_id, strategy_id)
);

-- Create user_broker_credentials table
CREATE TABLE IF NOT EXISTS user_broker_credentials (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(50) NOT NULL,
    broker_name VARCHAR(50) NOT NULL,
    client_id VARCHAR(255),
    encrypted_api_key TEXT,
    encrypted_secret_key TEXT,
    encrypted_password TEXT,
    encrypted_totp_secret TEXT,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
    UNIQUE(user_id, broker_name)
);

-- Create order_executions table (AUDIT TRAIL)
CREATE TABLE IF NOT EXISTS order_executions (
    id SERIAL PRIMARY KEY,
    order_id VARCHAR(50) UNIQUE NOT NULL,
    user_id VARCHAR(50) NOT NULL,
    strategy_id VARCHAR(50) NOT NULL,
    signal_id VARCHAR(50),
    symbol VARCHAR(20) NOT NULL,
    side VARCHAR(10) NOT NULL, -- BUY/SELL
    quantity INTEGER NOT NULL,
    order_type VARCHAR(20) NOT NULL,
    price DECIMAL(12,2),
    status VARCHAR(20) NOT NULL,
    broker_order_id VARCHAR(100),
    filled_price DECIMAL(12,2),
    filled_quantity INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    filled_at TIMESTAMP,
    error_message TEXT,
    
    FOREIGN KEY (user_id) REFERENCES users(user_id),
    FOREIGN KEY (strategy_id) REFERENCES strategies(strategy_id)
);

-- Create indexes for performance
-- User strategies lookup (CRITICAL for signal fanout)
CREATE INDEX IF NOT EXISTS idx_user_strategies_strategy_enabled 
    ON user_strategies(strategy_id, enabled) WHERE enabled = true;

CREATE INDEX IF NOT EXISTS idx_user_strategies_user_enabled 
    ON user_strategies(user_id, enabled) WHERE enabled = true;

-- Order executions indexes
CREATE INDEX IF NOT EXISTS idx_order_executions_user_created 
    ON order_executions(user_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_order_executions_strategy_created 
    ON order_executions(strategy_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_order_executions_symbol_created 
    ON order_executions(symbol, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_order_executions_status 
    ON order_executions(status);

CREATE INDEX IF NOT EXISTS idx_order_executions_signal_id 
    ON order_executions(signal_id) WHERE signal_id IS NOT NULL;

-- Users index
CREATE INDEX IF NOT EXISTS idx_users_status ON users(status);
CREATE INDEX IF NOT EXISTS idx_users_api_key ON users(api_key);

-- Strategies index
CREATE INDEX IF NOT EXISTS idx_strategies_status ON strategies(status);
CREATE INDEX IF NOT EXISTS idx_strategies_category ON strategies(category);

-- Insert default strategies
INSERT INTO strategies (strategy_id, name, description, category, risk_level, min_capital, expected_return_annual, max_drawdown, symbols, parameters, status)
VALUES 
    ('rsi_momentum', 'RSI Momentum Strategy', 'Buy oversold (RSI < 30), sell overbought (RSI > 70)', 'momentum', 'medium', 10000, 15.5, 8.2, 
     ARRAY['RELIANCE', 'TCS', 'INFY', 'HDFC', 'ICICIBANK'], 
     '{"rsi_period": 14, "oversold": 30, "overbought": 70}'::jsonb, 'ACTIVE'),
    
    ('ma_cross', 'Moving Average Cross Strategy', '5/20 MA crossover signals', 'trend_following', 'low', 15000, 12.3, 6.1,
     ARRAY['SBIN', 'LT', 'ITC', 'AXISBANK', 'HDFCBANK'],
     '{"fast_period": 5, "slow_period": 20}'::jsonb, 'ACTIVE'),
    
    ('mean_reversion', 'Mean Reversion Strategy', 'Bollinger Band bounce signals', 'mean_reversion', 'medium', 12000, 18.7, 9.4,
     ARRAY['RELIANCE', 'HDFC', 'TCS', 'INFY', 'ICICIBANK'],
     '{"bb_period": 20, "bb_std": 2.0}'::jsonb, 'ACTIVE')
ON CONFLICT (strategy_id) DO NOTHING;

-- Insert test users (remove in production)
INSERT INTO users (user_id, email, name, api_key, total_capital, risk_tolerance, status)
VALUES 
    ('user_001', 'trader1@trading.local', 'Test Trader 1', 'test_api_key_001', 500000, 'medium', 'ACTIVE'),
    ('user_002', 'trader2@trading.local', 'Test Trader 2', 'test_api_key_002', 1000000, 'high', 'ACTIVE'),
    ('user_003', 'trader3@trading.local', 'Test Trader 3', 'test_api_key_003', 250000, 'low', 'ACTIVE')
ON CONFLICT (user_id) DO NOTHING;

-- Enable strategies for test users
INSERT INTO user_strategies (user_id, strategy_id, enabled, quantity_multiplier, max_position_size)
VALUES 
    ('user_001', 'rsi_momentum', true, 1.0, 50000),
    ('user_001', 'ma_cross', true, 0.8, 40000),
    ('user_002', 'rsi_momentum', true, 2.0, 100000),
    ('user_002', 'mean_reversion', true, 1.5, 75000),
    ('user_003', 'ma_cross', true, 0.5, 25000)
ON CONFLICT (user_id, strategy_id) DO NOTHING;

-- Create function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Create triggers for updated_at
CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_strategies_updated_at BEFORE UPDATE ON strategies
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_user_strategies_updated_at BEFORE UPDATE ON user_strategies
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_user_broker_credentials_updated_at BEFORE UPDATE ON user_broker_credentials
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Grant permissions to trading_user
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO trading_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO trading_user;
GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA public TO trading_user;

-- Analyze tables for better query planning
ANALYZE users;
ANALYZE strategies;
ANALYZE user_strategies;
ANALYZE user_broker_credentials;
ANALYZE order_executions;

-- Success message
\echo 'Trading database initialized successfully!'
\echo 'Tables created: users, strategies, user_strategies, user_broker_credentials, order_executions'
\echo 'Indexes created for optimal performance'
\echo 'Test data inserted (remove in production)' 