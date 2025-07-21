# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

A modular cryptocurrency exchange data system that fetches perpetual futures data from multiple exchanges (Backpack, Binance, KuCoin), normalizes it, calculates APR, and can export to CSV or upload to Supabase database.

## Essential Commands

### Running the System
```bash
# Install dependencies
pip install -r requirements.txt

# Set up environment variables
cp .env.example .env  # Then edit with your Supabase credentials

# Run the main system
python main.py

# Run usage examples
python example_usage.py
```

### Configuration
- **Primary configuration**: `config/settings.py` - Toggle exchanges, set display limits, enable/disable features
- **Environment variables**: `.env` file for sensitive credentials (Supabase URL/key)
- **No .env.example exists**: You'll need to create .env manually with:
  ```
  SUPABASE_URL=your_url
  SUPABASE_KEY=your_key
  DATABASE_TABLE_NAME=exchange_data
  ```

## Architecture Overview

### Core Flow
1. **main.py** → ExchangeDataSystem orchestrates the entire flow
2. **ExchangeFactory** → Creates and manages exchange instances based on config
3. **Exchange implementations** → Fetch raw data from APIs (async for Binance open interest)
4. **DataProcessor** → Normalizes data, calculates APR, validates quality
5. **Output** → CSV export and/or Supabase batch upload (UPSERT on exchange+symbol)

### Key Design Patterns

#### Factory Pattern
- `exchange_factory.py` manages all exchange instances
- Easy to add new exchanges by implementing BaseExchange interface

#### Health Monitoring
- Global health tracker monitors API success/failure rates
- 24-hour rolling window for reliability scoring
- Integrated into base_exchange.py for automatic tracking

#### Data Validation
- Business-focused validation (not academic)
- Quality scoring (0-100) instead of verbose warnings
- Focus on: data freshness, exchange coverage, price sanity

#### Performance Optimizations
- Async bulk fetching for Binance open interest (19.5x speedup)
- Architectural filtering removes non-trading contracts before API calls
- Batch database uploads (100 records/batch)

### Data Pipeline

#### Unified Columns
All exchanges normalize to these columns:
- exchange, symbol, base_asset, quote_asset
- funding_rate, funding_interval_hours, apr
- index_price, mark_price, open_interest
- contract_type, market_type

#### APR Calculation
- Formula: `APR = funding_rate * (8760 / funding_interval_hours) * 100`
- Calculated in DataProcessor after data collection
- Handles null values gracefully

## Critical Implementation Details

### Exchange-Specific Quirks
- **Binance**: Separate USD-M and COIN-M markets, filters non-trading contracts
- **KuCoin**: Different funding time field names, millisecond conversions needed
- **Backpack**: Simple REST API, funding interval in milliseconds

### Windows Compatibility
- All Unicode characters replaced with ASCII (no emojis)
- Handles Windows path separators
- Encoding issues resolved

### Database Operations
- Uses UPSERT with conflict on (exchange, symbol)
- Batch uploads for performance
- Datetime columns converted to ISO format strings

## Testing Approach
**Note**: No automated test framework exists. Testing is done by:
1. Running `python main.py` and observing output
2. Database connection test runs automatically
3. Performance metrics tracked manually

## Common Modifications

### Add New Exchange
1. Create `exchanges/newexchange_exchange.py` inheriting from BaseExchange
2. Implement `fetch_data()` and `normalize_data()` methods
3. Add to exchange_classes dict in `exchange_factory.py`
4. Add to EXCHANGES dict in `config/settings.py`

### Change Data Display
- Modify display_columns in `data_processor.py` display_table() method
- Adjust formatting in the same method for new columns
- Update unified_columns if adding new data fields

### Adjust Performance
- `API_DELAY` in settings.py for rate limiting
- Batch size in `supabase_manager.py` (currently 100)
- Max concurrent requests in `binance_exchange.py` (currently 20)

## Important Notes
- System designed for non-coders to modify via settings.py
- Validation focuses on business logic, not data purity
- Health monitoring provides actionable intelligence
- All times internally handled as UTC
- Missing .gitignore and .env.example files in current setup