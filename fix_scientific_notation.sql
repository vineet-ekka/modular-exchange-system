-- Fix Scientific Notation in Supabase Tables
-- This script converts float4 columns to NUMERIC to prevent scientific notation display
-- Run this in your Supabase SQL Editor

-- First, let's check the actual data ranges to determine appropriate precision
-- This helps us understand what NUMERIC precision we need

-- Check funding_rate ranges
SELECT 
  'funding_rate' as column_name,
  MIN(funding_rate) as min_value,
  MAX(funding_rate) as max_value,
  COUNT(*) as total_rows,
  COUNT(CASE WHEN ABS(funding_rate) > 1 THEN 1 END) as values_above_1,
  COUNT(CASE WHEN ABS(funding_rate) > 10 THEN 1 END) as values_above_10
FROM exchange_data
WHERE funding_rate IS NOT NULL;

-- Check APR ranges (this is likely where the large values are)
SELECT 
  'apr' as column_name,
  MIN(apr) as min_value,
  MAX(apr) as max_value,
  COUNT(*) as total_rows,
  COUNT(CASE WHEN ABS(apr) > 999999 THEN 1 END) as values_above_million,
  COUNT(CASE WHEN ABS(apr) > 99999 THEN 1 END) as values_above_100k,
  COUNT(CASE WHEN ABS(apr) > 9999 THEN 1 END) as values_above_10k
FROM exchange_data
WHERE apr IS NOT NULL;

-- Show some extreme APR values to understand the data
SELECT exchange, symbol, funding_rate, apr
FROM exchange_data
WHERE ABS(apr) > 10000
ORDER BY ABS(apr) DESC
LIMIT 10;

-- Based on the above results, use appropriate precision:
-- NUMERIC(precision, scale) where precision = total digits, scale = decimal places

-- Convert funding_rate (should be small values)
ALTER TABLE exchange_data 
  ALTER COLUMN funding_rate TYPE NUMERIC(24,18);  -- Allows ±999999.999999999999999999

-- Convert APR (can have very large values due to annualization)
-- If APR can be in millions, we need more precision
ALTER TABLE exchange_data 
  ALTER COLUMN apr TYPE NUMERIC(20,6);  -- Allows ±99,999,999,999,999.999999

-- Same for historical table
ALTER TABLE exchange_data_historical
  ALTER COLUMN funding_rate TYPE NUMERIC(24,18),
  ALTER COLUMN apr TYPE NUMERIC(20,6);

-- Optional: Convert price columns if they show scientific notation
-- ALTER TABLE exchange_data 
--   ALTER COLUMN index_price TYPE NUMERIC(18,8),
--   ALTER COLUMN mark_price TYPE NUMERIC(18,8);
-- 
-- ALTER TABLE exchange_data_historical
--   ALTER COLUMN index_price TYPE NUMERIC(18,8),
--   ALTER COLUMN mark_price TYPE NUMERIC(18,8);

-- Verify the changes
SELECT column_name, data_type, numeric_precision, numeric_scale 
FROM information_schema.columns 
WHERE table_name = 'exchange_data' 
AND column_name IN ('funding_rate', 'apr', 'index_price', 'mark_price');