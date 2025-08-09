-- Create dedicated historical funding rates table
-- This table stores all historical funding rate data from exchanges
-- Optimized for time-series queries and analytics

CREATE TABLE IF NOT EXISTS funding_rates_historical (
    id SERIAL PRIMARY KEY,
    exchange VARCHAR(50) NOT NULL,
    symbol VARCHAR(50) NOT NULL,
    funding_rate NUMERIC(20, 10) NOT NULL,
    funding_time TIMESTAMP WITH TIME ZONE NOT NULL,
    mark_price NUMERIC(20, 10),
    funding_interval_hours INTEGER NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(exchange, symbol, funding_time)
);

-- Create composite index for efficient querying
CREATE INDEX IF NOT EXISTS idx_funding_historical_composite 
ON funding_rates_historical(exchange, symbol, funding_time DESC);

-- Index for time-based queries
CREATE INDEX IF NOT EXISTS idx_funding_historical_time
ON funding_rates_historical(funding_time DESC);

-- Index for symbol-specific queries
CREATE INDEX IF NOT EXISTS idx_funding_historical_symbol
ON funding_rates_historical(symbol);

-- Create materialized view for analytics
CREATE MATERIALIZED VIEW IF NOT EXISTS funding_rate_analytics AS
SELECT 
    exchange,
    symbol,
    DATE(funding_time) as date,
    AVG(funding_rate) as avg_funding_rate,
    STDDEV(funding_rate) as volatility,
    MIN(funding_rate) as min_rate,
    MAX(funding_rate) as max_rate,
    COUNT(*) as data_points,
    AVG(funding_rate * (8760.0 / funding_interval_hours) * 100) as avg_apr
FROM funding_rates_historical
GROUP BY exchange, symbol, DATE(funding_time);

-- Index for the materialized view
CREATE INDEX IF NOT EXISTS idx_funding_analytics_composite
ON funding_rate_analytics(exchange, symbol, date DESC);

-- Function to refresh the materialized view
CREATE OR REPLACE FUNCTION refresh_funding_analytics()
RETURNS void AS $$
BEGIN
    REFRESH MATERIALIZED VIEW CONCURRENTLY funding_rate_analytics;
END;
$$ LANGUAGE plpgsql;

-- Grant permissions
GRANT ALL PRIVILEGES ON funding_rates_historical TO postgres;
GRANT ALL PRIVILEGES ON funding_rate_analytics TO postgres;
GRANT EXECUTE ON FUNCTION refresh_funding_analytics() TO postgres;