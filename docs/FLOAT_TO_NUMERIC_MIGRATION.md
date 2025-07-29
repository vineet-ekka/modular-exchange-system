# Float to Numeric Migration Guide

## Overview
This guide explains how to migrate from FLOAT4 (REAL) to NUMERIC data types in PostgreSQL/Supabase to avoid scientific notation display issues with small decimal values like funding rates.

## Problem
- PostgreSQL FLOAT4 displays small numbers (< 0.0001) in scientific notation (e.g., 1e-04)
- This makes funding rates and APR values hard to read in dashboards
- Float types can introduce rounding errors in financial calculations

## Solution Options

### Option 1: Convert to NUMERIC (Recommended)
**File:** `database/convert_to_numeric.sql`

Benefits:
- No scientific notation ever
- Exact decimal representation
- No rounding errors
- Industry standard for financial data

Steps:
1. Run the migration SQL in Supabase SQL Editor
2. Test with a few data uploads
3. Remove scientific notation workarounds from code

### Option 2: Use Formatted Views (Alternative)
**File:** `database/create_formatted_views.sql`

Benefits:
- No schema changes needed
- Can format display as needed
- Original data unchanged

Steps:
1. Create the views in Supabase
2. Use views for dashboards/APIs
3. Original tables remain unchanged

## Data Type Comparison

| Type | Storage | Precision | Speed | Best For |
|------|---------|-----------|-------|----------|
| FLOAT4 | 4 bytes | ~6-9 digits | Fast | Scientific data |
| FLOAT8 | 8 bytes | ~15-17 digits | Fast | High precision science |
| NUMERIC(12,8) | Variable | Exact | Slower | Financial data |
| INTEGER | 4 bytes | Exact | Fastest | Whole numbers |

## Implementation Details

### NUMERIC Format Chosen
- `NUMERIC(12,8)` for funding_rate and apr
  - 12 total digits, 8 after decimal
  - Range: -9999.99999999 to 9999.99999999
  - Perfect for percentages and rates

### Code Changes
- `supabase_manager.py` updated with deprecation notes
- `_fix_scientific_notation()` kept for backward compatibility
- No changes needed to data collection code

### Testing Checklist
- [ ] Run migration SQL in test environment
- [ ] Upload sample data with small values
- [ ] Verify no scientific notation in database
- [ ] Check dashboard displays correctly
- [ ] Test calculations remain accurate
- [ ] Monitor performance (should be negligible impact)

## Rollback Plan
If needed, convert back to FLOAT4:
```sql
ALTER TABLE exchange_data 
  ALTER COLUMN funding_rate TYPE REAL USING funding_rate::REAL,
  ALTER COLUMN apr TYPE REAL USING apr::REAL;
```

## Performance Notes
- NUMERIC is slower than FLOAT for calculations
- For display-only use cases, impact is minimal
- For heavy calculations, consider keeping FLOAT internally