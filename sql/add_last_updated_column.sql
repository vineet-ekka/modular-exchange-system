-- Add last_updated column to exchange_data table
-- This column tracks when each funding rate entry was last updated

ALTER TABLE exchange_data 
ADD COLUMN IF NOT EXISTS last_updated TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP;

-- Create an index on last_updated for better query performance
CREATE INDEX IF NOT EXISTS idx_exchange_data_last_updated 
ON exchange_data(last_updated DESC);

-- Update existing rows to have the current timestamp
UPDATE exchange_data 
SET last_updated = CURRENT_TIMESTAMP 
WHERE last_updated IS NULL;

-- Add a trigger to automatically update the last_updated column
CREATE OR REPLACE FUNCTION update_last_updated_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.last_updated = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Create the trigger
DROP TRIGGER IF EXISTS update_exchange_data_last_updated ON exchange_data;
CREATE TRIGGER update_exchange_data_last_updated 
BEFORE UPDATE ON exchange_data 
FOR EACH ROW 
EXECUTE FUNCTION update_last_updated_column();

-- Add comment to the column
COMMENT ON COLUMN exchange_data.last_updated IS 'Timestamp of when this record was last updated';