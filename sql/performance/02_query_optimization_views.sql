-- Materialized Views for Query Performance Optimization
-- =====================================================
-- Pre-computed aggregations to speed up common queries

-- 1. Grouped funding rates by base asset (refreshed every 5 minutes)
CREATE MATERIALIZED VIEW IF NOT EXISTS mv_grouped_funding_rates AS
SELECT 
    base_asset,
    COUNT(DISTINCT exchange) as exchange_count,
    COUNT(*) as contract_count,
    AVG(apr) as avg_apr,
    MIN(apr) as min_apr,
    MAX(apr) as max_apr,
    SUM(open_interest) as total_open_interest,
    MAX(updated_at) as last_updated
FROM exchange_data
WHERE apr IS NOT NULL
GROUP BY base_asset;

-- Create index on materialized view
CREATE INDEX IF NOT EXISTS idx_mv_grouped_base_asset 
ON mv_grouped_funding_rates(base_asset);

CREATE INDEX IF NOT EXISTS idx_mv_grouped_avg_apr 
ON mv_grouped_funding_rates(avg_apr DESC);

-- 2. Top funding rates view (for quick access to extremes)
CREATE MATERIALIZED VIEW IF NOT EXISTS mv_top_funding_rates AS
SELECT 
    symbol,
    exchange,
    base_asset,
    quote_asset,
    funding_rate,
    apr,
    open_interest,
    updated_at,
    'highest' as category
FROM exchange_data
WHERE apr IS NOT NULL
ORDER BY apr DESC
LIMIT 100
UNION ALL
SELECT 
    symbol,
    exchange,
    base_asset,
    quote_asset,
    funding_rate,
    apr,
    open_interest,
    updated_at,
    'lowest' as category
FROM exchange_data
WHERE apr IS NOT NULL
ORDER BY apr ASC
LIMIT 100;

-- Indexes for top rates view
CREATE INDEX IF NOT EXISTS idx_mv_top_rates_category 
ON mv_top_funding_rates(category, apr DESC);

-- 3. Exchange summary statistics
CREATE MATERIALIZED VIEW IF NOT EXISTS mv_exchange_stats AS
SELECT 
    exchange,
    COUNT(DISTINCT symbol) as symbol_count,
    COUNT(DISTINCT base_asset) as asset_count,
    AVG(apr) as avg_apr,
    SUM(open_interest) as total_open_interest,
    MAX(updated_at) as last_updated
FROM exchange_data
WHERE apr IS NOT NULL
GROUP BY exchange;

-- Index for exchange stats
CREATE INDEX IF NOT EXISTS idx_mv_exchange_stats_exchange 
ON mv_exchange_stats(exchange);

-- 4. Recent historical aggregates (hourly for last 24h, daily for last 30d)
CREATE MATERIALIZED VIEW IF NOT EXISTS mv_historical_aggregates AS
WITH hourly_data AS (
    SELECT 
        base_asset,
        exchange,
        date_trunc('hour', timestamp) as period,
        'hourly' as resolution,
        AVG(apr) as avg_apr,
        MIN(apr) as min_apr,
        MAX(apr) as max_apr,
        COUNT(*) as data_points
    FROM exchange_data_historical
    WHERE timestamp > NOW() - INTERVAL '24 hours'
    GROUP BY base_asset, exchange, date_trunc('hour', timestamp)
),
daily_data AS (
    SELECT 
        base_asset,
        exchange,
        date_trunc('day', timestamp) as period,
        'daily' as resolution,
        AVG(apr) as avg_apr,
        MIN(apr) as min_apr,
        MAX(apr) as max_apr,
        COUNT(*) as data_points
    FROM exchange_data_historical
    WHERE timestamp > NOW() - INTERVAL '30 days'
        AND timestamp <= NOW() - INTERVAL '24 hours'
    GROUP BY base_asset, exchange, date_trunc('day', timestamp)
)
SELECT * FROM hourly_data
UNION ALL
SELECT * FROM daily_data;

-- Indexes for historical aggregates
CREATE INDEX IF NOT EXISTS idx_mv_hist_agg_lookup 
ON mv_historical_aggregates(base_asset, resolution, period DESC);

-- Refresh functions for materialized views
-- =======================================

-- Function to refresh all materialized views
CREATE OR REPLACE FUNCTION refresh_all_materialized_views()
RETURNS void AS $$
BEGIN
    REFRESH MATERIALIZED VIEW CONCURRENTLY mv_grouped_funding_rates;
    REFRESH MATERIALIZED VIEW CONCURRENTLY mv_top_funding_rates;
    REFRESH MATERIALIZED VIEW CONCURRENTLY mv_exchange_stats;
    REFRESH MATERIALIZED VIEW CONCURRENTLY mv_historical_aggregates;
END;
$$ LANGUAGE plpgsql;

-- Schedule periodic refresh (example for pg_cron extension)
-- This would need to be set up based on your PostgreSQL configuration
-- SELECT cron.schedule('refresh-materialized-views', '*/5 * * * *', 'SELECT refresh_all_materialized_views();');