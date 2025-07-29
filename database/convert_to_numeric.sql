-- Convert float columns to NUMERIC to avoid scientific notation display
-- This migration converts funding_rate and apr columns from REAL (float4) to NUMERIC
-- NUMERIC(12,8) allows for values up to 9999.99999999 with 8 decimal places
-- Perfect for funding rates (e.g., 0.00010000 for 0.01%) and APR percentages

-- Convert main exchange_data table
ALTER TABLE exchange_data 
  ALTER COLUMN funding_rate TYPE NUMERIC(12,8) USING funding_rate::NUMERIC(12,8),
  ALTER COLUMN apr TYPE NUMERIC(12,8) USING apr::NUMERIC(12,8);

-- Convert historical table if it exists
ALTER TABLE exchange_data_historical
  ALTER COLUMN funding_rate TYPE NUMERIC(12,8) USING funding_rate::NUMERIC(12,8),
  ALTER COLUMN apr TYPE NUMERIC(12,8) USING apr::NUMERIC(12,8);

-- Optional: Also convert price columns if they show scientific notation
-- Uncomment if needed:
-- ALTER TABLE exchange_data 
--   ALTER COLUMN index_price TYPE NUMERIC(20,8) USING index_price::NUMERIC(20,8),
--   ALTER COLUMN mark_price TYPE NUMERIC(20,8) USING mark_price::NUMERIC(20,8);
-- 
-- ALTER TABLE exchange_data_historical
--   ALTER COLUMN index_price TYPE NUMERIC(20,8) USING index_price::NUMERIC(20,8),
--   ALTER COLUMN mark_price TYPE NUMERIC(20,8) USING mark_price::NUMERIC(20,8);

-- Note: NUMERIC(20,8) for prices allows values up to 999,999,999,999.99999999
-- which covers all cryptocurrency prices including Bitcoin