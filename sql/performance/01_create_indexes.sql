-- Performance Optimization Indexes for Funding Rate Dashboard
-- =========================================================
-- These indexes improve query performance for the most common access patterns

-- 1. Composite index for exchange and symbol lookups (most common query pattern)
CREATE INDEX IF NOT EXISTS idx_exchange_data_exchange_symbol 
ON exchange_data(exchange, symbol);

-- 2. Index for APR-based sorting (used in all funding rates endpoint)
CREATE INDEX IF NOT EXISTS idx_exchange_data_apr_desc 
ON exchange_data(apr DESC NULLS LAST);

-- 3. Index for base asset grouping (used in grouped funding rates)
CREATE INDEX IF NOT EXISTS idx_exchange_data_base_asset 
ON exchange_data(base_asset);

-- 4. Composite index for asset filtering with APR sorting
CREATE INDEX IF NOT EXISTS idx_exchange_data_base_asset_apr 
ON exchange_data(base_asset, apr DESC);

-- 5. Index for timestamp-based queries (data freshness checks)
CREATE INDEX IF NOT EXISTS idx_exchange_data_updated_at 
ON exchange_data(updated_at DESC);

-- 6. Index for open interest sorting and filtering
CREATE INDEX IF NOT EXISTS idx_exchange_data_open_interest 
ON exchange_data(open_interest DESC NULLS LAST)
WHERE open_interest IS NOT NULL;

-- 7. Composite index for exchange and base asset (exchange comparison queries)
CREATE INDEX IF NOT EXISTS idx_exchange_data_exchange_base_asset 
ON exchange_data(exchange, base_asset);

-- Historical table indexes
-- ========================

-- 8. Composite index for historical queries by asset and time
CREATE INDEX IF NOT EXISTS idx_historical_base_asset_timestamp 
ON exchange_data_historical(base_asset, timestamp DESC);

-- 9. Index for exchange-specific historical queries
CREATE INDEX IF NOT EXISTS idx_historical_exchange_timestamp 
ON exchange_data_historical(exchange, base_asset, timestamp DESC);

-- 10. Index for time-range queries
CREATE INDEX IF NOT EXISTS idx_historical_timestamp 
ON exchange_data_historical(timestamp DESC);

-- 11. Partial index for recent data (last 30 days) - most accessed
CREATE INDEX IF NOT EXISTS idx_historical_recent 
ON exchange_data_historical(base_asset, timestamp DESC)
WHERE timestamp > NOW() - INTERVAL '30 days';

-- Performance statistics
-- =====================
-- Run ANALYZE to update table statistics for query planner
ANALYZE exchange_data;
ANALYZE exchange_data_historical;

-- Verify indexes were created
SELECT 
    schemaname,
    tablename,
    indexname,
    indexdef
FROM pg_indexes
WHERE tablename IN ('exchange_data', 'exchange_data_historical')
ORDER BY tablename, indexname;