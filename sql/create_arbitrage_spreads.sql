-- Create tables for arbitrage spread history and statistics
-- This tracks historical funding rate spreads between exchange pairs
-- Used to calculate z-scores and percentiles for arbitrage opportunities

-- Drop existing objects if needed (for clean install)
DROP MATERIALIZED VIEW IF EXISTS mv_arbitrage_spread_stats CASCADE;
DROP TABLE IF EXISTS arbitrage_spreads_historical CASCADE;

-- Historical spread tracking table
CREATE TABLE IF NOT EXISTS arbitrage_spreads_historical (
    id SERIAL PRIMARY KEY,
    asset VARCHAR(50) NOT NULL,
    exchange_long VARCHAR(50) NOT NULL,
    exchange_short VARCHAR(50) NOT NULL,
    long_rate NUMERIC(20,10),
    short_rate NUMERIC(20,10),
    funding_rate_spread NUMERIC(20,10),
    apr_spread NUMERIC(20,10),
    recorded_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(asset, exchange_long, exchange_short, recorded_at)
);

-- Indexes for fast queries
CREATE INDEX idx_spread_hist_lookup ON arbitrage_spreads_historical(asset, exchange_long, exchange_short, recorded_at DESC);
CREATE INDEX idx_spread_hist_time ON arbitrage_spreads_historical(recorded_at DESC);
CREATE INDEX idx_spread_hist_asset ON arbitrage_spreads_historical(asset);

-- Materialized view for spread statistics (refreshed every 5 minutes)
CREATE MATERIALIZED VIEW IF NOT EXISTS mv_arbitrage_spread_stats AS
SELECT
    asset,
    LEAST(exchange_long, exchange_short) as exchange_a,
    GREATEST(exchange_long, exchange_short) as exchange_b,
    AVG(ABS(funding_rate_spread)) as mean_spread,
    STDDEV(ABS(funding_rate_spread)) as std_dev_spread,
    AVG(apr_spread) as mean_apr_spread,
    STDDEV(apr_spread) as std_dev_apr_spread,
    PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY ABS(funding_rate_spread)) as median_spread,
    PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY ABS(funding_rate_spread)) as p95_spread,
    PERCENTILE_CONT(0.99) WITHIN GROUP (ORDER BY ABS(funding_rate_spread)) as p99_spread,
    MIN(ABS(funding_rate_spread)) as min_spread,
    MAX(ABS(funding_rate_spread)) as max_spread,
    COUNT(*) as data_points,
    MAX(recorded_at) as last_updated
FROM arbitrage_spreads_historical
WHERE recorded_at >= NOW() - INTERVAL '30 days'
    AND funding_rate_spread IS NOT NULL
GROUP BY asset, exchange_long, exchange_short
HAVING COUNT(*) >= 10;

-- Create unique index for fast lookups
CREATE UNIQUE INDEX ON mv_arbitrage_spread_stats(asset, exchange_a, exchange_b);

-- Grant permissions (adjust as needed for your database user)
GRANT SELECT ON arbitrage_spreads_historical TO postgres;
GRANT INSERT ON arbitrage_spreads_historical TO postgres;
GRANT SELECT ON mv_arbitrage_spread_stats TO postgres;

-- Function to clean old data (keep 60 days)
CREATE OR REPLACE FUNCTION clean_old_spread_history()
RETURNS void AS $$
BEGIN
    DELETE FROM arbitrage_spreads_historical
    WHERE recorded_at < NOW() - INTERVAL '60 days';
END;
$$ LANGUAGE plpgsql;

-- Add comment for documentation
COMMENT ON TABLE arbitrage_spreads_historical IS 'Historical funding rate spreads between exchange pairs for statistical analysis';
COMMENT ON MATERIALIZED VIEW mv_arbitrage_spread_stats IS 'Pre-calculated statistics for arbitrage spreads, refreshed every 5 minutes';