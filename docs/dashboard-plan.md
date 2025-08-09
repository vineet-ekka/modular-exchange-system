# Dashboard Implementation Plan - Funding Rate System

## ✅ ALL PHASES (1-5) COMPLETE - ASSET GRID VIEW DEPLOYED

## Executive Summary

This document outlines the comprehensive funding rate system implementation, including the successfully completed historical data collection (Phases 1-4) and the newly deployed simplified asset grid view (Phase 5). The system fetches historical data from exchange APIs, stores it in PostgreSQL, and provides streamlined visualization. Phase 1-4 handles 350+ Binance perpetual contracts with historical sparklines. Phase 5 has been successfully implemented, providing a clean, focused asset-based view showing funding rates across all exchanges in a single row per asset, inspired by CoinGlass but simplified for optimal user experience.

**Latest Updates (2025-08-08)**:
- Removed overlapping Debug component for cleaner UI
- Reverted historical chart to simple line visualization (removed complex color-coding)
- Dashboard runs smoothly with all services operational

## System Requirements

### Core Objectives
- **Primary Use Cases**:
  - Analyze funding rate trends over time
  - Measure volatility in funding rates
  - Calculate historical APR
  - Create visualizations
  - Compute simple moving averages (SMA)

### Specifications
- **Time Range**: 1 month rolling window (current time to 30 days ago)
- **Coverage**: All perpetual contracts/pairs
  - Binance: 541 contracts (505 USD-M and 36 COIN-M)
  - Other exchanges: Disabled by default (KuCoin, Kraken, Backpack, Deribit available)
- **Update Frequency**: Real-time 30-second updates
  - Live data collection every 30 seconds
  - Dashboard auto-refresh every 30 seconds
  - Background historical refresh on startup
  - Perfect synchronization between data and UI
- **Historical Data**: 
  - Initial backfill: 80,000+ records for 30 days
  - Background refresh: Complete 30-day update on every startup
  - UPSERT operations prevent duplicates
- **Supported Exchanges**: Binance (enabled), KuCoin, Kraken, Backpack, Deribit (available)
- **Simplified Startup**: One-command launch with `python start.py`
  - Instant dashboard access (no waiting)
  - Background historical data refresh (~5 minutes)

## Architecture Design

### System Components

```
┌─────────────────────────────────────────────┐
│          Scheduler Service                  │
│  (Tracks funding intervals per contract)    │
└─────────────┬───────────────────────────────┘
              │
              ▼
┌─────────────────────────────────────────────┐
│      Historical Data Fetcher                │
│  (Exchange-specific API implementations)    │
└─────────────┬───────────────────────────────┘
              │
              ▼
┌─────────────────────────────────────────────┐
│         Data Processor                      │
│  (Normalization, APR calc, validation)      │
└─────────────┬───────────────────────────────┘
              │
              ▼
┌─────────────────────────────────────────────┐
│         PostgreSQL Database                 │
│  (Historical table with analytics views)    │
└─────────────┬───────────────────────────────┘
              │
              ▼
┌─────────────────────────────────────────────┐
│         Analytics Engine                    │
│  (Trends, volatility, SMA calculations)     │
└─────────────┬───────────────────────────────┘
              │
              ▼
┌─────────────────────────────────────────────┐
│      Dashboard/Visualization Layer          │
│  (Charts, metrics, real-time updates)       │
└─────────────────────────────────────────────┘
```

## Implementation Phases

### Phase 1: Binance Integration (Week 1)

#### 1.1 Historical API Implementation
- Extend existing `exchanges/binance_exchange.py` class
- Implement Binance's historical funding rate endpoints
  - USD-M Futures: `GET /fapi/v1/fundingRate`
  - COIN-M Futures: `GET /dapi/v1/fundingRate`
  - Parameters: symbol, startTime, endTime, limit (max 1000)
- Auto-detect funding intervals from timestamp gaps (4h or 8h)
- Implement rate limiting (500 requests per 5 minutes shared limit)

#### 1.2 Contract Metadata Collection
- Fetch all Binance perpetual contracts from exchange info
- Filter for PERPETUAL contract type only
- Process both USD-M and COIN-M markets
- Track funding interval per contract (auto-detected)

#### 1.3 Batch Fetching Strategy
- Use 30-day time ranges to minimize API calls
- Process symbols in batches to stay within rate limits
- Store last fetched timestamp per symbol
- Implement hourly scheduler with on-demand updates

### Phase 2: Data Management (Week 1-2)

#### 2.1 Database Schema Updates
```sql
-- New dedicated historical funding rates table
CREATE TABLE funding_rates_historical (
    id SERIAL PRIMARY KEY,
    exchange VARCHAR(50) NOT NULL,
    symbol VARCHAR(50) NOT NULL,
    funding_rate NUMERIC(20, 10) NOT NULL,
    funding_time TIMESTAMP WITH TIME ZONE NOT NULL,
    mark_price NUMERIC(20, 10),
    funding_interval_hours INTEGER NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(exchange, symbol, funding_time)
);

-- Analytics materialized views
CREATE MATERIALIZED VIEW funding_rate_analytics AS
SELECT 
    exchange,
    symbol,
    DATE(funding_time) as date,
    AVG(funding_rate) as avg_funding_rate,
    STDDEV(funding_rate) as volatility,
    MIN(funding_rate) as min_rate,
    MAX(funding_rate) as max_rate,
    COUNT(*) as data_points
FROM funding_rates_historical
GROUP BY exchange, symbol, DATE(funding_time);

-- Index for performance
CREATE INDEX idx_funding_historical_composite 
ON funding_rates_historical(exchange, symbol, funding_time DESC);
```

#### 2.2 Data Retention Policy
- Keep detailed data for 3 months
- Aggregate older data to daily summaries
- Archive data older than 1 year

### Phase 3: API Implementation (Week 2)

#### 3.1 FastAPI Endpoints
Add to existing `api.py`:
```python
# Historical funding rate endpoints
GET /api/historical-funding/{symbol}
  - Query params: start_time, end_time
  - Returns funding rates from database
  - Triggers async update if data is stale

GET /api/funding-sparkline/{symbol}
  - Returns last 24-48 hours of rates
  - Optimized for dashboard sparkline charts
```

#### 3.2 Data Freshness Strategy
- Hybrid approach: Show database data immediately
- Check for updates asynchronously
- Update database in background if new data available
- Track last_updated timestamp per symbol

### Phase 4: Visualization Dashboard (Week 2-3)

#### 4.1 Frontend Components
- **Current + Historical Display**: 
  - Large number showing current funding rate
  - Sparkline chart showing last 24-48 hours
  - Color coding (green for positive, red for negative)
- **Simple Filtering**:
  - Symbol selector
  - Time range picker (24h, 7d, 30d)
- **Table Enhancement**:
  - Add sparkline column to existing funding table
  - Show trend direction with arrows

#### 4.2 Update Strategy
- Dashboard and data collector both run on 30-second cycles
- Real-time synchronization between data collection and UI
- Fetch current rates + sparkline data together
- Automatic startup with simplified launcher script

## Data Flow Example

### Initial Backfill (One-time)
```python
# Pseudocode for initial 30-day backfill
def backfill_binance_historical():
    # Get all perpetual contracts
    usdm_contracts = get_binance_perpetuals('USD-M')
    coinm_contracts = get_binance_perpetuals('COIN-M')
    
    for contract in usdm_contracts + coinm_contracts:
        # Fetch 30 days in one request (max 1000 records)
        historical_data = fetch_funding_history(
            symbol=contract.symbol,
            start_time=datetime.now() - timedelta(days=30),
            end_time=datetime.now(),
            limit=1000
        )
        
        # Auto-detect funding interval from timestamps
        interval = detect_funding_interval(historical_data)
        
        # Store in funding_rates_historical table
        store_historical_funding(historical_data, interval)
```

### Ongoing Updates
```python
# Hourly scheduler + on-demand updates
def update_funding_rates():
    for symbol in get_all_symbols():
        last_funding = get_last_funding_time(symbol)
        
        # Fetch only new funding rates since last update
        new_rates = fetch_funding_history(
            symbol=symbol,
            start_time=last_funding,
            end_time=datetime.now()
        )
        
        if new_rates:
            store_historical_funding(new_rates)
            
# Also triggered when dashboard requests data
def on_dashboard_request(symbol):
    if is_data_stale(symbol):
        update_funding_rates_for_symbol(symbol)
```

## Migration Strategy

### Step 1: Parallel Running (Testing)
1. Deploy new historical system alongside existing continuous polling
2. Compare data accuracy and completeness
3. Validate analytics calculations

### Step 2: Gradual Transition
1. Switch Binance to historical API only
2. Monitor for 1 week
3. Address any issues

### Step 3: Complete Migration
1. Migrate remaining exchanges one by one
2. Deprecate continuous polling system
3. Clean up old code and dependencies

## Performance Considerations

### API Rate Limits
- **Binance**: 500 requests per 5 minutes (shared limit)
- **Strategy**: Batch by time range (30-day requests), minimize API calls
- **Optimization**: ~350 symbols can be fetched within rate limits using batching

### Database Optimization
- Start simple - PostgreSQL can handle ~40,000 records easily
- Add indexes only if performance issues arise
- Consider partitioning only after millions of records

### Scalability
- Design for horizontal scaling
- Use async operations for API calls
- Implement connection pooling

## Success Metrics

### Technical KPIs
- Data completeness: >99.5%
- Update latency: <1 minute from funding time
- API error rate: <0.1%
- Dashboard load time: <2 seconds

### Business KPIs
- Historical data coverage: 30 days minimum
- Number of tracked contracts: 350+ for Binance
- Data freshness: <1 hour for all symbols
- Dashboard responsiveness: Immediate with async updates

## Risk Mitigation

### Technical Risks
- **API Changes**: Monitor exchange announcements, implement adapters
- **Rate Limiting**: Implement backoff, consider paid tiers if needed
- **Data Gaps**: Store raw responses, implement recovery mechanisms

### Operational Risks
- **System Downtime**: Implement health checks, alerting
- **Data Quality**: Validation layers, anomaly detection
- **Scaling Issues**: Load testing, capacity planning

## Phase 5: Simplified Asset Grid View (Updated - 2025)

### Design Mockup
A complete HTML wireframe mockup has been created at `dashboard-wireframe-mockup.html` showing the simplified interface design with focus on essential features only.

### 5.1 Asset-Based Funding Rate Grid (Simplified)
Implement a streamlined view showing funding rates for each asset across all exchanges in a single row, inspired by CoinGlass interface.

#### Grid View Features
- **Rows**: Base assets (BTC, ETH, SOL, XRP, DOGE, etc.)
- **Columns**: Each exchange shows current funding rate
- **Color Coding**: Green (positive), Red (negative), Gray (N/A)
- **Sorting**: By asset name or any exchange column
- **Click Action**: Opens historical detail view
- **Search**: Filter assets by name

#### API Endpoint: `/api/funding-rates-grid`
```sql
-- Query to get latest funding rate per asset per exchange
SELECT 
    base_asset,
    exchange,
    AVG(funding_rate) as funding_rate,
    AVG(apr) as apr
FROM exchange_data
WHERE base_asset IS NOT NULL
GROUP BY base_asset, exchange
ORDER BY base_asset, exchange;
```

### 5.2 Historical Detail View (Click from Grid)
When clicking an asset row, display comprehensive historical data similar to CoinGlass.

#### Historical View Components
- **Multi-Line Chart**: Funding rates over time for all exchanges
  - Simple continuous line for each exchange
  - Default exchange colors (Binance yellow, others gray)
  - Time range selector (1D, 7D, 30D)
  - Y-axis: Funding rate percentage
  - X-axis: Time with scroll
  
- **Data Table**: Exact values at each timestamp
  - Rows: Timestamps (8-hour intervals)
  - Columns: Exchange funding rates
  - Color-coded values (green positive, red negative)
  - Export to CSV functionality

#### API Endpoint: `/api/historical-funding-by-asset/{asset}`
```python
# Returns 30-day historical for specific asset across all exchanges
{
  "asset": "BTC",
  "exchanges": ["Binance", "KuCoin", "Kraken", "Backpack", "Deribit"],
  "data": [
    {
      "timestamp": "2025-07-29 00:00",
      "Binance": 0.0713,
      "KuCoin": 0.0489,
      "Kraken": -0.1634,
      "Backpack": 0.0471,
      "Deribit": 0.0671
    }
  ]
}
```

### 5.3 Implementation Files

#### New Components
1. **AssetFundingGrid.tsx** - Main grid view component (simplified)
2. **HistoricalFundingView.tsx** - Historical chart and table

#### Modified Files
1. **api.py** - Add two new endpoints
2. **App.tsx** - Single view implementation (no toggle needed)
3. **api.ts** - Add new API functions

### 5.4 Benefits Over Current Implementation
- **Reduced Complexity**: ~200 asset rows vs 1400+ contracts
- **Better Comparison**: All exchanges visible at once
- **Arbitrage Detection**: Easy to spot rate differences
- **Professional UI**: Similar to industry-standard CoinGlass
- **Performance**: Optimized queries and rendering

### 5.5 Simplified Implementation Strategy
1. Single focused view - Asset-based grid only
2. No view toggles or modes - cleaner UX
3. Direct replacement of contract view
4. Streamlined user experience without options paralysis

## Implementation Status

### ✅ Completed (2025-08-07)
- [x] Extended BinanceExchange class with historical methods
- [x] Created funding_rates_historical table with indexes
- [x] Implemented 30-day backfill for all symbols
- [x] Set up hourly update scheduler
- [x] Added FastAPI endpoints for historical data
- [x] Implemented hybrid data freshness strategy
- [x] Created sparkline component for dashboard
- [x] Integrated historical data with existing table
- [x] Added error handling and retry logic
- [x] Created comprehensive documentation
- [x] Implemented performance monitoring

### ✅ Completed (2025-08-08)
- [x] Phase 5.1: Simplified asset-based funding grid component
- [x] Phase 5.2: Historical detail view with multi-exchange chart
- [x] Phase 5.3: Search and filter functionality
- [x] Phase 5.4: Performance optimization for large datasets
- [x] Phase 5.5: Clean, single-view implementation
- [x] Simplified startup script (`start.py`) with one-command launch
- [x] Real-time 30-second data collection integrated
- [x] Automatic dependency installation
- [x] Cross-platform compatibility (Windows/Mac/Linux)
- [x] Debug logging and refresh button added to dashboard
- [x] **Background historical backfill**: 30-day refresh runs in background
- [x] **Instant startup**: Dashboard opens immediately with existing data
- [x] **Lock file protection**: Prevents duplicate backfill processes
- [x] **Initial data population**: 80,213 historical records loaded
- [x] **Debug component removed**: Fixed overlapping UI elements
- [x] **Historical chart reverted**: Removed color-coded funding rate lines (kept simple)

### 📋 Future Enhancements (Post-MVP)
- [ ] Predicted funding rates column
- [ ] Volume-weighted average rates
- [ ] Alert system for rate changes
- [ ] Mobile-responsive grid layout
- [ ] CSV export functionality

### Files Created/Modified

#### Phases 1-4 (Historical System)
1. **exchanges/binance_exchange.py** - Added historical funding rate methods
2. **sql/02_create_historical_funding_table.sql** - Database schema
3. **database/postgres_manager.py** - Historical data upload methods
4. **binance_historical_backfill.py** - Initial backfill script
5. **apply_historical_migration.py** - Database migration script
6. **historical_updater.py** - Hourly update scheduler
7. **api.py** - Added `/api/historical-funding/{symbol}` and `/api/funding-sparkline/{symbol}`
8. **dashboard/src/components/Charts/Sparkline.tsx** - Sparkline component
9. **dashboard/src/components/Tables/EnhancedFundingTable.tsx** - Table with sparklines
10. **dashboard/src/services/api.ts** - Historical data API functions
11. **HISTORICAL_IMPLEMENTATION.md** - Complete implementation guide

#### Phase 5 (Asset Grid View) - Completed 2025-08-08
12. **api.py** - Added `/api/funding-rates-grid` and `/api/historical-funding-by-asset/{asset}`
13. **dashboard/src/components/Grid/AssetFundingGrid.tsx** - Main asset grid component
14. **dashboard/src/components/Grid/HistoricalFundingView.tsx** - Historical detail modal (simple line chart)
15. **dashboard/src/App.tsx** - Updated to use asset grid as primary view, removed Debug component
16. **dashboard/src/services/api.ts** - Added grid API functions
17. **PHASE5_IMPLEMENTATION.md** - Phase 5 implementation documentation

#### Background Historical System - Completed 2025-08-08
18. **start.py** - Enhanced with `start_background_historical_backfill()` function
19. **run_backfill.py** - Wrapper script for proper imports
20. **scripts/binance_historical_backfill.py** - Fixed logging format issues
21. **.backfill.lock** - Lock file prevents duplicate processes

### Deployment Instructions

#### Quick Start (Recommended)
```bash
# One-command startup with instant access
python start.py

# Or on Windows, double-click:
start.bat
```

**What happens:**
1. Dashboard opens immediately (no waiting)
2. Shows existing data from database
3. Background process refreshes 30-day historical data
4. Dashboard auto-updates every 30 seconds

#### First-Time Setup (If No Data Exists)
```bash
# Run once to populate historical data
python run_backfill.py --days 30

# Then use normal startup
python start.py
```

#### Manual Deployment (Advanced)
1. Initial historical backfill: `python run_backfill.py --days 30`
2. Start services individually:
   - PostgreSQL: `docker-compose up -d postgres`
   - API Server: `python api.py`
   - Dashboard: `cd dashboard && npm start`
   - Data Collector: `python main.py --loop --interval 30 --quiet`
   - Historical Updater (optional): `python scripts/historical_updater.py`

## Conclusion

### Completed Features (Phases 1-4)
The historical funding rate system has been successfully implemented with the following capabilities:
- Fetching and storing 30 days of historical funding rates for all Binance perpetuals
- Automatically updating data hourly to maintain freshness
- Serving historical data through optimized API endpoints
- Displaying sparkline visualizations in the dashboard
- Handling 350+ contracts efficiently within rate limits

### Completed (Phase 5 - Asset Grid View + Real-Time System)
The simplified asset grid view has been successfully deployed with:
- ✅ Clean, focused interface showing funding rates by asset
- ✅ Professional grid layout inspired by CoinGlass with essential features only
- ✅ Click-through historical charts showing multi-exchange comparisons
- ✅ Reduced complexity from 1400+ contracts to ~469 unique assets
- ✅ Streamlined user experience optimized for arbitrage detection
- ✅ Search and sort functionality for easy navigation
- ✅ Real-time updates every 30 seconds (both data and UI)
- ✅ Responsive design for all screen sizes
- ✅ One-command startup with automatic dependency management
- ✅ **Background historical refresh**: Complete 30-day update on every startup
- ✅ **Instant dashboard access**: No waiting for data to load
- ✅ **541 Binance contracts** tracked with current market data
- ✅ **80,213 historical records** populated and maintained