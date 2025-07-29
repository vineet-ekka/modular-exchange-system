-- Alternative solution: Create formatted views if you cannot modify column types
-- This creates views that format float values to avoid scientific notation display
-- Use these views for dashboards and APIs that need clean decimal display

-- Formatted view for main exchange_data table
CREATE OR REPLACE VIEW exchange_data_formatted AS
SELECT 
  exchange,
  symbol,
  base_asset,
  quote_asset,
  -- Format funding_rate to 8 decimal places without scientific notation
  CASE 
    WHEN funding_rate IS NULL THEN NULL
    ELSE to_char(funding_rate, 'FM0.00000000')
  END as funding_rate,
  funding_interval_hours,
  -- Format APR to 6 decimal places (it's a percentage)
  CASE 
    WHEN apr IS NULL THEN NULL
    ELSE to_char(apr, 'FM0.000000')
  END as apr,
  -- Format prices to 2 decimal places for readability
  CASE 
    WHEN index_price IS NULL THEN NULL
    ELSE to_char(index_price, 'FM999999999999.99')
  END as index_price,
  CASE 
    WHEN mark_price IS NULL THEN NULL
    ELSE to_char(mark_price, 'FM999999999999.99')
  END as mark_price,
  -- Format open interest without decimal places
  CASE 
    WHEN open_interest IS NULL THEN NULL
    ELSE to_char(open_interest, 'FM999999999999999')
  END as open_interest,
  contract_type,
  market_type
FROM exchange_data;

-- Formatted view for historical table
CREATE OR REPLACE VIEW exchange_data_historical_formatted AS
SELECT 
  exchange,
  symbol,
  base_asset,
  quote_asset,
  -- Format funding_rate to 8 decimal places without scientific notation
  CASE 
    WHEN funding_rate IS NULL THEN NULL
    ELSE to_char(funding_rate, 'FM0.00000000')
  END as funding_rate,
  funding_interval_hours,
  -- Format APR to 6 decimal places (it's a percentage)
  CASE 
    WHEN apr IS NULL THEN NULL
    ELSE to_char(apr, 'FM0.000000')
  END as apr,
  -- Format prices to 2 decimal places for readability
  CASE 
    WHEN index_price IS NULL THEN NULL
    ELSE to_char(index_price, 'FM999999999999.99')
  END as index_price,
  CASE 
    WHEN mark_price IS NULL THEN NULL
    ELSE to_char(mark_price, 'FM999999999999.99')
  END as mark_price,
  -- Format open interest without decimal places
  CASE 
    WHEN open_interest IS NULL THEN NULL
    ELSE to_char(open_interest, 'FM999999999999999')
  END as open_interest,
  contract_type,
  market_type,
  timestamp
FROM exchange_data_historical;

-- Note: The 'FM' prefix removes leading/trailing spaces and zeros
-- Adjust decimal places as needed for your use case