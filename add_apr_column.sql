-- Add APR column to exchange_data table
-- Run this in Supabase SQL Editor

ALTER TABLE exchange_data 
ADD COLUMN IF NOT EXISTS apr DECIMAL(20, 2);

-- Add comment to explain the column
COMMENT ON COLUMN exchange_data.apr IS 'Annualized Percentage Rate calculated from funding_rate * (8760 / funding_interval_hours) * 100';

-- Verify the column was added
SELECT column_name, data_type 
FROM information_schema.columns 
WHERE table_name = 'exchange_data' 
AND column_name = 'apr';