-- RPC function to get grouped funding rates
-- This function aggregates funding rates by base asset with statistics

CREATE OR REPLACE FUNCTION get_grouped_funding_rates()
RETURNS TABLE (
    base_asset VARCHAR,
    asset_name VARCHAR,
    contract_count BIGINT,
    avg_apr NUMERIC,
    min_apr NUMERIC,
    max_apr NUMERIC,
    exchange_count BIGINT,
    total_open_interest NUMERIC,
    latest_update TIMESTAMP WITH TIME ZONE
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        ed.base_asset,
        MAX(ed.base_asset) as asset_name, -- Will be replaced with proper names in the service
        COUNT(*) as contract_count,
        AVG(ed.apr::NUMERIC) as avg_apr,
        MIN(ed.apr::NUMERIC) as min_apr,
        MAX(ed.apr::NUMERIC) as max_apr,
        COUNT(DISTINCT ed.exchange) as exchange_count,
        SUM(COALESCE(ed.open_interest::NUMERIC, 0)) as total_open_interest,
        MAX(ed.last_updated) as latest_update
    FROM exchange_data ed
    GROUP BY ed.base_asset
    ORDER BY avg_apr DESC;
END;
$$ LANGUAGE plpgsql;

-- RPC function to get historical aggregated data
CREATE OR REPLACE FUNCTION get_historical_aggregated(
    p_asset VARCHAR,
    p_start_time TIMESTAMP WITH TIME ZONE,
    p_interval VARCHAR,
    p_exchange VARCHAR DEFAULT NULL
)
RETURNS TABLE (
    time_bucket TIMESTAMP WITH TIME ZONE,
    exchange VARCHAR,
    avg_apr NUMERIC,
    min_apr NUMERIC,
    max_apr NUMERIC,
    data_points BIGINT
) AS $$
BEGIN
    -- Convert interval string to PostgreSQL interval
    DECLARE
        v_interval INTERVAL;
    BEGIN
        v_interval := CASE p_interval
            WHEN 'hour' THEN INTERVAL '1 hour'
            WHEN '4 hours' THEN INTERVAL '4 hours'
            WHEN 'day' THEN INTERVAL '1 day'
            ELSE INTERVAL '1 hour'
        END;
        
        RETURN QUERY
        SELECT 
            date_trunc(p_interval, h.timestamp) as time_bucket,
            h.exchange,
            AVG(h.apr::NUMERIC) as avg_apr,
            MIN(h.apr::NUMERIC) as min_apr,
            MAX(h.apr::NUMERIC) as max_apr,
            COUNT(*) as data_points
        FROM exchange_data_historical h
        WHERE h.base_asset = p_asset
            AND h.timestamp >= p_start_time
            AND (p_exchange IS NULL OR h.exchange = p_exchange)
        GROUP BY date_trunc(p_interval, h.timestamp), h.exchange
        ORDER BY time_bucket DESC, h.exchange;
    END;
END;
$$ LANGUAGE plpgsql;

-- RPC function to execute SQL (for creating indexes - requires appropriate permissions)
-- This should only be used in development or by admin users
CREATE OR REPLACE FUNCTION execute_sql(query TEXT)
RETURNS VOID AS $$
BEGIN
    -- Security check: Only allow specific operations
    IF query ILIKE '%CREATE INDEX%' OR query ILIKE '%DROP INDEX%' THEN
        EXECUTE query;
    ELSE
        RAISE EXCEPTION 'Only index operations are allowed';
    END IF;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Grant necessary permissions (adjust based on your database user)
-- GRANT EXECUTE ON FUNCTION get_grouped_funding_rates() TO your_app_user;
-- GRANT EXECUTE ON FUNCTION get_historical_aggregated(VARCHAR, TIMESTAMP WITH TIME ZONE, VARCHAR, VARCHAR) TO your_app_user;
-- GRANT EXECUTE ON FUNCTION execute_sql(TEXT) TO your_admin_user;