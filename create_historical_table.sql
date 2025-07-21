-- Create historical data table for time-series analysis
-- This table uses INSERT operations (no UPSERT) to preserve all historical records

CREATE TABLE IF NOT EXISTS exchange_data_historical (
    -- Primary key
    id BIGSERIAL PRIMARY KEY,
    
    -- Timestamp for historical tracking
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    -- Exchange and symbol identifiers
    exchange VARCHAR(50) NOT NULL,
    symbol VARCHAR(50) NOT NULL,
    base_asset VARCHAR(20),
    quote_asset VARCHAR(20),
    
    -- Funding rate data
    funding_rate DECIMAL(20, 10),
    funding_interval_hours DECIMAL(10, 2),
    apr DECIMAL(20, 2),  -- Annual Percentage Rate
    
    -- Price data
    index_price DECIMAL(20, 8),
    mark_price DECIMAL(20, 8),
    
    -- Volume data
    open_interest DECIMAL(30, 8),
    
    -- Contract metadata
    contract_type VARCHAR(50),
    market_type VARCHAR(50),
    
    -- Indexes for performance
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create indexes for efficient querying
CREATE INDEX idx_exchange_data_historical_timestamp ON exchange_data_historical(timestamp DESC);
CREATE INDEX idx_exchange_data_historical_exchange ON exchange_data_historical(exchange);
CREATE INDEX idx_exchange_data_historical_symbol ON exchange_data_historical(symbol);
CREATE INDEX idx_exchange_data_historical_exchange_symbol ON exchange_data_historical(exchange, symbol);
CREATE INDEX idx_exchange_data_historical_composite ON exchange_data_historical(exchange, symbol, timestamp DESC);

-- Grant permissions (adjust based on your Supabase setup)
-- GRANT ALL ON exchange_data_historical TO authenticated;
-- GRANT ALL ON exchange_data_historical TO service_role;

-- Add comment to table
COMMENT ON TABLE exchange_data_historical IS 'Historical time-series data for cryptocurrency perpetual futures';
COMMENT ON COLUMN exchange_data_historical.timestamp IS 'When this data was collected';
COMMENT ON COLUMN exchange_data_historical.apr IS 'Annualized funding rate percentage';