# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

### Added
- Documentation refactoring with dedicated docs/ folder structure
- Comprehensive API reference documentation
- Exchange-specific documentation file
- Archived completed implementation plans

---

## Phase 34: ByBit and Lighter Exchange Integration (2025-10-13)

### Added
- **ByBit Integration**: 663 perpetual contracts (largest single exchange addition)
  - 639 linear perpetual contracts (USDT/USDC-margined)
  - 24 inverse perpetual contracts (USD-margined)
  - V5 API with cursor-based pagination
  - Mixed funding intervals: 4h (52.3%), 8h (38.8%), 1h (5.9%), 2h (3.0%)
  - Rate limit: 50 req/s with automatic pagination handling
  - Base asset normalization handles up to 8-digit multiplier prefixes
- **Lighter Integration**: 91 contracts from DEX aggregator
  - Aggregates funding rates from Binance, OKX, and ByBit
  - 8-hour CEX-standard equivalent rate format
  - Unique market_id system for contract identification
  - 1-hour resolution historical data support
  - Rate conversion logic for CEX-standard alignment
- **Enhanced Dashboard Features**:
  - Exchange Filter System with multi-select and persistence
  - Custom hooks (useExchangeFilter, useFilterPersistence, useFilterURL)
  - New UI cards (APRExtremeCard, DashboardStatsCard, SystemOverviewCard)
  - Arbitrage Historical Chart component
  - Modern UI components (ModernMultiSelect, ModernPagination, ModernTooltip)
  - Filter state synchronization with URL parameters and localStorage

### Changed
- System expansion: Total contracts increased from 1,403 to 2,275 (+62%)
- Asset coverage: Unique assets expanded from 600+ to 656

---

## Phase 33: Redis Cache Implementation (2025-09-23)

### Added
- Redis integration for high-performance caching layer
- TTL strategy: 5s for contracts, 10s for summary data
- Memory limit: 512MB with LRU eviction policy
- Fallback mechanism: Graceful degradation to in-memory cache if Redis unavailable

### Changed
- Performance improvement: <100ms API response times with caching

---

## Phase 32: Aster and Drift Exchange Integration (2025-09-20)

### Added
- **Aster DEX Integration**: 102 perpetual contracts with 4-hour funding intervals
- **Drift Solana DEX**: 61 perpetual contracts with 1-hour funding intervals
- Symbol normalization for Aster prefixes (1000FLOKI → FLOKI, kX → X)
- Drift normalization: Remove -PERP suffix, handle 1M/1K prefixes (1MBONK → BONK)
- Rate limiting: Aster at 40 req/s max, Drift with no strict limits
- Parallel fetching with optimized async/await for both exchanges

### Changed
- Total contracts: System expanded to 1,403 across 6 exchanges

---

## Phase 31: Arbitrage Detection System (2025-09-15)

### Added
- Cross-exchange scanning for real-time arbitrage opportunity detection
- APR spread calculation with automatic profit calculations
- New database table: `arbitrage_spreads` for opportunity tracking
- API endpoint: `/api/arbitrage/opportunities` with filtering capabilities
- Historical tracking of spread statistics over time
- Redis caching with 5s TTL for performance optimization

---

## Phase 30: Z-Score Statistical Monitoring (2025-09-03)

### Added
- Statistical analysis: Z-score calculations for all funding rates
- New database tables: `funding_statistics`, `contract_metadata`
- Zone-based updates: Active zones (|Z|>2) update every 30s, stable every 2min
- Parallel processing: <1s calculation for all 1,297 contracts
- API endpoints: `/api/contracts-with-zscores`, `/api/zscore-summary`
- Percentile rankings: Distribution-independent statistical measures

### Changed
- Performance optimized: <100ms API response times

---

## Phase 29: Funding Interval Display (2025-08-29)

### Added
- Contract details enhancement: Added funding interval column to expanded contract view
- Clear interval display showing funding frequency (1h, 2h, 4h, 8h) for each contract
- API update: Modified `/api/funding-rates-grid` endpoint to include funding_interval_hours

### Changed
- Clean UI: Interval shown only in contract details table for clarity
- Essential information helps traders understand holding costs and funding payment frequency

---

## Phase 28: Dashboard Refresh Fix (2025-08-29)

### Fixed
- Fixed stuck backfill: Corrected backfill status file preventing infinite polling
- Smart polling logic: BackfillProgress component now stops polling at 100% progress
- API auto-fix: Backfill status endpoint automatically corrects inconsistent states
- Removed pre-fetch: Eliminated automatic fetching of 600+ assets on mount

### Changed
- Performance boost: Reduced API calls from ~720/hour to ~120/hour (83% reduction)
- Smart search: Added debounced search with on-demand contract fetching

---

## Phase 27: Step Function Chart Implementation (2025-08-29)

### Added
- Chart accuracy: Replaced smooth curves with step functions for funding rates
- Interval detection: Automatically detects funding intervals (1h, 2h, 4h, 8h)
- Forward fill: Properly handles null values with last known values
- Enhanced tooltips: Shows funding interval, change percentage, and data type
- Visual indicators: Reference lines at actual funding update times

### Changed
- Performance: Disabled animations for better performance with 720+ data points

---

## Phase 26: 1MBABYDOGE Normalization (2025-08-29)

### Added
- 1MBABYDOGE normalization: 1M denomination (1 Million) now properly handled
- Normalization: `1MBABYDOGEUSDT` and `1MBABYDOGEUSDTM` → `BABYDOGE`

### Fixed
- Unified display: Both Binance and KuCoin 1MBABYDOGE contracts now grouped under BABYDOGE asset
- Denomination recognition: System correctly identifies 1M as a denomination prefix

---

## Phase 25: 1000X Token Normalization Fix (2025-08-28)

### Fixed
- Fixed 1000X token: Special handling for KuCoin's 1000XUSDTM contract
- Normalization: 1000X correctly normalized to "X" (representing X token with 1000x denomination)
- Unified display: X token now appears consistently across Binance and KuCoin
- Edge case handling: Added explicit check for baseCurrency='1000X' from KuCoin API

---

## Phase 24: Documentation Enhancement (2025-08-28)

### Added
- Enhanced CLAUDE.md: Improved guidance for Claude Code instances
- Background process monitoring: Instructions for managing background processes
- Windows support: Better Windows-specific commands and alternatives
- Dependency clarity: Added missing package installations (fastapi, uvicorn, psutil)
- Troubleshooting: Expanded debugging and status checking commands

---

## Phase 23: Data Collector Reliability (2025-08-28)

### Added
- Improved startup: Better error handling in `start.py`
- Process monitoring: Verifies data collector starts successfully
- Logging support: Output redirected to `data_collector.log`
- Windows compatibility: Fixed console window issues on Windows
- Status feedback: Clear indication if collector fails to start

---

## Phase 22: Dashboard Search Enhancement (2025-08-28)

### Added
- Enhanced search functionality: Can now search both assets and contracts
- Auto-expansion: Assets automatically expand when contracts match search
- Visual highlighting: Matching contracts highlighted with blue border
- Search modes: Search by asset name, contract symbol, exchange, or partial matches
- Pre-fetching: All contract data pre-loaded for instant search results

---

## Phase 21: Base Asset Normalization (2025-08-28)

### Fixed
- Fixed prefix token normalization across all exchanges
- Unified asset display (no more duplicates like "1000BONK" and "BONK")
- Proper handling of all prefix patterns:
  - Binance: `1000` and `1000000` prefixes
  - KuCoin: `1000000`, `10000`, and `1000` prefixes (checked in order)
  - Hyperliquid & Backpack: `k` prefix tokens
- Fixed edge cases like `10000CATUSDTM` → `CAT`, `1000000MOGUSDTM` → `MOG`

---

## Phase 16-20: Recent Improvements (2025-08-21)

### Added
- Synchronized historical windows
- Contract-specific countdown timers
- X-axis improvements for charts

### Fixed
- Bug fixes for historical page
- Performance optimizations

---

## Phase 15: Hyperliquid Integration (2025-08-18)

### Added
- 173 DEX perpetual contracts
- 1-hour funding intervals
- Open interest USD conversion

### Fixed
- API fixes for contract naming (2025-08-27)

---

## Phase 14: Backpack Integration (2025-08-15)

### Added
- 39 perpetual contracts added
- Historical backfill implementation

### Fixed
- Chart and data fixes

---

## Phase 13: Settings Management (2025-08-14)

### Added
- Web-based settings interface
- Hot-reload configuration
- Backup/restore functionality
- Import/export settings

---

## Phase 11-12: Multi-Exchange Support (2025-08-13)

### Added
- KuCoin integration (472 contracts)
- Sequential collection implementation
- Symbol normalization (XBT → BTC)
- Unified backfill scripts

---

## Phase 7-10: System Improvements (2025-08-12)

### Added
- Backfill progress indicator
- Dashboard shutdown button
- APR display implementation
- Dynamic OI units

### Fixed
- Critical funding interval detection fix
- Multi-contract chart enhancements

---

## Phase 6: Enhanced Historical Page (2025-08-11)

### Added
- Live funding ticker
- Countdown timer to next funding
- Combined chart and table view

---

## Phase 5: Asset Grid View (2025-08-08)

### Added
- Simplified from 1400+ contracts to 600+ assets
- CoinGlass-inspired interface design
- One-command startup implementation

---

## Phase 1-4: Core System (2025-08-07)

### Added
- Binance integration with 541 contracts
- PostgreSQL database setup
- FastAPI backend implementation
- React dashboard foundation
- Historical data collection system

---

## Critical Fixes Summary

1. **Funding Interval Detection**: Fixed 333 contracts with incorrect APR
2. **Multi-Contract Chart Alignment**: Timestamp normalization
3. **COIN-M Contract Display**: Base asset extraction
4. **Historical Data Completeness**: Zero value handling
5. **Open Interest Display**: Dynamic unit formatting
6. **Base Asset Normalization**: Fixed duplicate assets in dashboard (e.g., "1000BONK" and "BONK" now unified)
7. **Dashboard Search**: Can now search both assets and contracts with auto-expansion
8. **Data Collector Startup**: Improved reliability with logging and error handling
9. **Documentation Enhancement**: Improved CLAUDE.md for better Claude Code integration
10. **1000X Token Fix**: Correctly normalizes KuCoin's 1000XUSDTM to "X" instead of "1000X"
11. **1MBABYDOGE Normalization**: Added support for 1M (1 Million) denomination prefix
12. **Step Function Charts**: Accurate representation of funding rate changes with proper intervals
13. **Dashboard Refresh Fix**: Eliminated constant refreshing from stuck backfill status
14. **Funding Interval Display**: Added clear display of funding frequency for each contract
