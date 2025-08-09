-- Create main exchange_data table
CREATE TABLE IF NOT EXISTS exchange_data (
    id SERIAL PRIMARY KEY,
    exchange VARCHAR(50) NOT NULL,
    symbol VARCHAR(50) NOT NULL,
    base_asset VARCHAR(20),
    quote_asset VARCHAR(20),
    funding_rate NUMERIC(20, 10),
    funding_interval_hours INTEGER,
    apr NUMERIC(20, 10),
    index_price NUMERIC(20, 10),
    mark_price NUMERIC(20, 10),
    open_interest NUMERIC(30, 10),
    contract_type VARCHAR(50),
    market_type VARCHAR(50),
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    last_updated TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(exchange, symbol)
);

-- Create historical data table
CREATE TABLE IF NOT EXISTS exchange_data_historical (
    id SERIAL PRIMARY KEY,
    exchange VARCHAR(50) NOT NULL,
    symbol VARCHAR(50) NOT NULL,
    base_asset VARCHAR(20),
    quote_asset VARCHAR(20),
    funding_rate NUMERIC(20, 10),
    funding_interval_hours INTEGER,
    apr NUMERIC(20, 10),
    index_price NUMERIC(20, 10),
    mark_price NUMERIC(20, 10),
    open_interest NUMERIC(30, 10),
    contract_type VARCHAR(50),
    market_type VARCHAR(50),
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_exchange_data_exchange ON exchange_data(exchange);
CREATE INDEX IF NOT EXISTS idx_exchange_data_symbol ON exchange_data(symbol);
CREATE INDEX IF NOT EXISTS idx_exchange_data_base_asset ON exchange_data(base_asset);
CREATE INDEX IF NOT EXISTS idx_exchange_data_apr ON exchange_data(apr DESC);
CREATE INDEX IF NOT EXISTS idx_exchange_data_timestamp ON exchange_data(timestamp DESC);

CREATE INDEX IF NOT EXISTS idx_historical_exchange ON exchange_data_historical(exchange);
CREATE INDEX IF NOT EXISTS idx_historical_symbol ON exchange_data_historical(symbol);
CREATE INDEX IF NOT EXISTS idx_historical_base_asset ON exchange_data_historical(base_asset);
CREATE INDEX IF NOT EXISTS idx_historical_timestamp ON exchange_data_historical(timestamp DESC);

-- Create a view for latest data by symbol
CREATE OR REPLACE VIEW latest_funding_rates AS
SELECT DISTINCT ON (exchange, symbol)
    exchange,
    symbol,
    base_asset,
    quote_asset,
    funding_rate,
    funding_interval_hours,
    apr,
    index_price,
    mark_price,
    open_interest,
    contract_type,
    market_type,
    timestamp,
    last_updated
FROM exchange_data
ORDER BY exchange, symbol, last_updated DESC;

-- Create a view for APR statistics
CREATE OR REPLACE VIEW apr_statistics AS
SELECT 
    base_asset,
    COUNT(DISTINCT symbol) as contract_count,
    COUNT(DISTINCT exchange) as exchange_count,
    AVG(apr) as avg_apr,
    MIN(apr) as min_apr,
    MAX(apr) as max_apr,
    SUM(open_interest) as total_open_interest
FROM exchange_data
GROUP BY base_asset
ORDER BY avg_apr DESC;

-- Grant permissions (adjust as needed)
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO postgres;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO postgres;