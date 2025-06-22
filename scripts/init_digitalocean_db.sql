-- DigitalOcean Database Initialization Script
-- Run this script once against your DigitalOcean managed database

-- Create database schema for trading system
-- Note: DigitalOcean manages the database itself, we just create tables

-- Users table - trader accounts
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    username VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    is_active BOOLEAN DEFAULT true,
    risk_multiplier DECIMAL(3,2) DEFAULT 1.00,
    max_daily_loss DECIMAL(12,2) DEFAULT 10000.00,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Strategies table - available trading strategies
CREATE TABLE IF NOT EXISTS strategies (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(100) UNIQUE NOT NULL,
    description TEXT,
    is_active BOOLEAN DEFAULT true,
    risk_level INTEGER DEFAULT 3 CHECK (risk_level BETWEEN 1 AND 5),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- User strategies - which strategies each user has enabled
CREATE TABLE IF NOT EXISTS user_strategies (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    strategy_id UUID NOT NULL REFERENCES strategies(id) ON DELETE CASCADE,
    is_enabled BOOLEAN DEFAULT true,
    quantity_multiplier DECIMAL(5,2) DEFAULT 1.00,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, strategy_id)
);

-- User broker credentials - encrypted API keys per user
CREATE TABLE IF NOT EXISTS user_broker_credentials (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    broker_name VARCHAR(50) NOT NULL,
    api_key TEXT NOT NULL,
    api_secret TEXT NOT NULL,
    totp_secret TEXT,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, broker_name)
);

-- Order executions - complete audit trail
CREATE TABLE IF NOT EXISTS order_executions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id),
    strategy_id UUID NOT NULL REFERENCES strategies(id),
    signal_id VARCHAR(100) NOT NULL,
    symbol VARCHAR(50) NOT NULL,
    action VARCHAR(10) NOT NULL CHECK (action IN ('BUY', 'SELL')),
    quantity INTEGER NOT NULL,
    order_type VARCHAR(20) NOT NULL,
    price DECIMAL(15,4),
    broker_order_id VARCHAR(100),
    status VARCHAR(20) DEFAULT 'PENDING',
    executed_at TIMESTAMP WITH TIME ZONE,
    filled_quantity INTEGER DEFAULT 0,
    filled_price DECIMAL(15,4),
    commission DECIMAL(10,4) DEFAULT 0.00,
    error_message TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Performance Indexes for sub-millisecond lookups (critical for 100-500 users)
CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);
CREATE INDEX IF NOT EXISTS idx_users_active ON users(is_active);

CREATE INDEX IF NOT EXISTS idx_strategies_name ON strategies(name);
CREATE INDEX IF NOT EXISTS idx_strategies_active ON strategies(is_active);

CREATE INDEX IF NOT EXISTS idx_user_strategies_user_enabled ON user_strategies(user_id, is_enabled);
CREATE INDEX IF NOT EXISTS idx_user_strategies_strategy_enabled ON user_strategies(strategy_id, is_enabled);

CREATE INDEX IF NOT EXISTS idx_user_broker_creds_user_broker ON user_broker_credentials(user_id, broker_name);
CREATE INDEX IF NOT EXISTS idx_user_broker_creds_active ON user_broker_credentials(user_id, is_active);

CREATE INDEX IF NOT EXISTS idx_order_executions_user_strategy ON order_executions(user_id, strategy_id);
CREATE INDEX IF NOT EXISTS idx_order_executions_signal ON order_executions(signal_id);
CREATE INDEX IF NOT EXISTS idx_order_executions_symbol_time ON order_executions(symbol, created_at);
CREATE INDEX IF NOT EXISTS idx_order_executions_status ON order_executions(status);
CREATE INDEX IF NOT EXISTS idx_order_executions_created_at ON order_executions(created_at);

-- Insert default strategies for testing
INSERT INTO strategies (name, description, risk_level) VALUES
    ('RSI Momentum', 'Buy when RSI < 30, sell when RSI > 70', 3),
    ('Moving Average Cross', 'Trade on 5/20 period MA crossovers', 2),
    ('Mean Reversion', 'Bollinger Band bounce strategy', 4)
ON CONFLICT (name) DO NOTHING;

-- Create a test user for development
INSERT INTO users (username, email, risk_multiplier, max_daily_loss) VALUES
    ('test_trader', 'test@trading.local', 1.0, 5000.00)
ON CONFLICT (username) DO NOTHING;

-- Enable all strategies for test user
INSERT INTO user_strategies (user_id, strategy_id, quantity_multiplier)
SELECT u.id, s.id, 1.0
FROM users u
CROSS JOIN strategies s
WHERE u.username = 'test_trader'
ON CONFLICT (user_id, strategy_id) DO NOTHING;

-- Display table status
SELECT 
    schemaname,
    tablename,
    attname,
    n_distinct,
    correlation
FROM pg_stats 
WHERE schemaname = 'public' 
    AND tablename IN ('users', 'strategies', 'user_strategies', 'user_broker_credentials', 'order_executions')
ORDER BY tablename, attname; 