-- Query Performance Monitoring Setup
-- =================================
-- Tools and views for monitoring query performance

-- 1. Enable query statistics collection (requires superuser)
-- Note: These should be set in postgresql.conf for persistence
-- ALTER SYSTEM SET shared_preload_libraries = 'pg_stat_statements';
-- ALTER SYSTEM SET pg_stat_statements.track = 'all';
-- ALTER SYSTEM SET pg_stat_statements.max = 10000;

-- Create extension if not exists (requires superuser privileges)
CREATE EXTENSION IF NOT EXISTS pg_stat_statements;

-- 2. View for monitoring slow queries
CREATE OR REPLACE VIEW v_slow_queries AS
SELECT 
    query,
    calls,
    total_exec_time,
    mean_exec_time,
    min_exec_time,
    max_exec_time,
    stddev_exec_time,
    rows,
    100.0 * shared_blks_hit / NULLIF(shared_blks_hit + shared_blks_read, 0) AS hit_percent
FROM pg_stat_statements
WHERE query NOT LIKE '%pg_stat_statements%'
    AND mean_exec_time > 100  -- Queries averaging over 100ms
ORDER BY mean_exec_time DESC
LIMIT 50;

-- 3. View for most frequent queries
CREATE OR REPLACE VIEW v_frequent_queries AS
SELECT 
    query,
    calls,
    total_exec_time,
    mean_exec_time,
    rows,
    rows / NULLIF(calls, 0) as avg_rows
FROM pg_stat_statements
WHERE query NOT LIKE '%pg_stat_statements%'
ORDER BY calls DESC
LIMIT 50;

-- 4. View for queries with poor cache hit rates
CREATE OR REPLACE VIEW v_poor_cache_queries AS
SELECT 
    query,
    calls,
    shared_blks_hit,
    shared_blks_read,
    100.0 * shared_blks_hit / NULLIF(shared_blks_hit + shared_blks_read, 0) AS hit_percent,
    mean_exec_time
FROM pg_stat_statements
WHERE shared_blks_hit + shared_blks_read > 1000  -- Significant block access
    AND 100.0 * shared_blks_hit / NULLIF(shared_blks_hit + shared_blks_read, 0) < 90  -- Less than 90% hit rate
ORDER BY shared_blks_read DESC
LIMIT 50;

-- 5. Table for logging query performance over time
CREATE TABLE IF NOT EXISTS query_performance_log (
    id SERIAL PRIMARY KEY,
    logged_at TIMESTAMP DEFAULT NOW(),
    query_hash BIGINT,
    query_text TEXT,
    calls BIGINT,
    total_time DOUBLE PRECISION,
    mean_time DOUBLE PRECISION,
    min_time DOUBLE PRECISION,
    max_time DOUBLE PRECISION,
    rows BIGINT,
    hit_percent DOUBLE PRECISION
);

-- Index for performance log
CREATE INDEX IF NOT EXISTS idx_query_performance_log_time 
ON query_performance_log(logged_at DESC);

CREATE INDEX IF NOT EXISTS idx_query_performance_log_hash 
ON query_performance_log(query_hash, logged_at DESC);

-- 6. Function to log current query performance
CREATE OR REPLACE FUNCTION log_query_performance()
RETURNS void AS $$
BEGIN
    INSERT INTO query_performance_log (
        query_hash,
        query_text,
        calls,
        total_time,
        mean_time,
        min_time,
        max_time,
        rows,
        hit_percent
    )
    SELECT 
        queryid,
        query,
        calls,
        total_exec_time,
        mean_exec_time,
        min_exec_time,
        max_exec_time,
        rows,
        100.0 * shared_blks_hit / NULLIF(shared_blks_hit + shared_blks_read, 0)
    FROM pg_stat_statements
    WHERE calls > 10  -- Only log queries called more than 10 times
        AND query NOT LIKE '%pg_stat_statements%';
END;
$$ LANGUAGE plpgsql;

-- 7. View for identifying missing indexes
CREATE OR REPLACE VIEW v_missing_indexes AS
SELECT 
    schemaname,
    tablename,
    attname,
    n_distinct,
    correlation
FROM pg_stats
WHERE schemaname = 'public'
    AND n_distinct > 100
    AND correlation < 0.1
    AND tablename IN ('exchange_data', 'exchange_data_historical')
ORDER BY n_distinct DESC;

-- 8. Function to analyze query execution plan
CREATE OR REPLACE FUNCTION analyze_query_plan(query_text TEXT)
RETURNS TABLE(plan_line TEXT) AS $$
BEGIN
    RETURN QUERY
    EXECUTE 'EXPLAIN (ANALYZE, BUFFERS, FORMAT TEXT) ' || query_text;
END;
$$ LANGUAGE plpgsql;

-- 9. Dashboard query performance summary
CREATE OR REPLACE VIEW v_dashboard_performance_summary AS
SELECT 
    'Total Queries' as metric,
    COUNT(*)::TEXT as value
FROM pg_stat_statements
UNION ALL
SELECT 
    'Avg Query Time (ms)',
    ROUND(AVG(mean_exec_time), 2)::TEXT
FROM pg_stat_statements
UNION ALL
SELECT 
    'Slowest Query Time (ms)',
    ROUND(MAX(max_exec_time), 2)::TEXT
FROM pg_stat_statements
UNION ALL
SELECT 
    'Cache Hit Rate (%)',
    ROUND(100.0 * SUM(shared_blks_hit) / NULLIF(SUM(shared_blks_hit + shared_blks_read), 0), 2)::TEXT
FROM pg_stat_statements;

-- 10. Reset statistics function (use carefully)
-- SELECT pg_stat_statements_reset();