# Exchange Documentation

Detailed documentation for all supported exchanges in the modular exchange system.

## Overview

**Total Coverage:**
- **Active Exchanges**: 13 (6 CEX, 7 DEX)
- **Disabled Exchanges**: 2 (EdgeX, ApeX) + 1 ready (Kraken)
- **Total Contracts**: 2,014+ perpetual futures
- **Unique Assets**: ~656+ consolidated across all exchanges

---

## Centralized Exchanges (CEX)

### Binance (592 contracts)
- **Funding Intervals**: 1h, 4h, 8h
- **Market Types**: USD-M (USDT-margined) and COIN-M (coin-margined)
- **Base Asset Normalization**: Handles `1000`, `1000000`, and `1MBABYDOGE` prefixes
- **API**: Separate endpoints for USD-M and COIN-M futures
- **Rate Limit**: 40 requests/second
- **Historical Data**: Unlimited time range available

### KuCoin (522 contracts)
- **Funding Intervals**: 1h, 2h, 4h, 8h
- **Base Asset Normalization**: Handles `1000000`, `10000`, `1000` prefixes (checked in order)
- **Special Cases**: `1000X` → `X` (X token), `XBT` → `BTC`
- **Rate Limit**: 30 requests/second
- **Historical Data**: Recent data only from API

### ByBit (667 contracts)
- **Funding Intervals**: 1h, 2h, 4h, 8h
- **Market Types**: Linear (USDT/USDC-margined) and Inverse (USD-margined)
- **Base Asset Normalization**: Handles up to 8-digit multiplier prefixes
- **API**: V5 API with cursor-based pagination
- **Rate Limit**: 50 requests/second
- **Historical Data**: 200 records per request with pagination

### MEXC (826 contracts)
- **Funding Intervals**: 8h (standard)
- **Features**: Bulk fetching optimization with fallback to batch processing
- **Base Asset Normalization**: Handles numerical prefixes (`1000`, `10000`, `1000000`) and `k` prefix
- **API**: REST API with contract details endpoint
- **Rate Limit**: Standard rate limiting with batch optimization
- **Historical Data**: Available via API

### Backpack (63 contracts)
- **Funding Intervals**: 1h (all contracts)
- **Market Type**: USDC-margined contracts
- **Base Asset Normalization**: Handles `k` prefix (e.g., `kBONK_USDC_PERP` → `BONK`)
- **Historical Data**: 7+ months available
- **Rate Limit**: ~20 requests/second

### Deribit (20 contracts)
- **Funding Intervals**: 8h
- **Market Type**: Options-focused exchange with perpetuals
- **API**: JSON-RPC API integration
- **Features**: Comprehensive options and perpetuals support
- **Base Asset Normalization**: Standard format from API

---

## Decentralized Exchanges (DEX)

### Hyperliquid (182 contracts)
- **Funding Intervals**: 1h (all contracts)
- **Platform**: DEX with 1-hour funding intervals
- **Base Asset Normalization**: Handles `k` prefix (e.g., `kPEPE` → `PEPE`)
- **Special Notations**: `k` prefix, `@` prefix for some contracts
- **Open Interest**: Reported in base asset units
- **Authentication**: No authentication required

### Drift (51 contracts)
- **Funding Intervals**: 1h
- **Platform**: Solana-based DEX
- **Base Asset Normalization**: Handles `1M` (millions) and `1K` (thousands) prefixes, removes `-PERP` suffix
- **Symbol Format**: XXX-PERP format
- **Features**: Excludes betting markets (perpetuals only)
- **Rate Limit**: No strict limits

### Aster (123 contracts)
- **Funding Intervals**: 4h
- **Platform**: DEX with async/parallel fetching
- **Base Asset Normalization**: Handles `1000`, `k` prefixes
- **Market Type**: USDT-margined perpetual contracts
- **Rate Limit**: 40 requests/second maximum
- **Features**: Optimized for performance

### Lighter (91 contracts)
- **Funding Intervals**: 8h (CEX-standard equivalent)
- **Platform**: DEX aggregator combining rates from Binance, OKX, ByBit
- **Base Asset Normalization**: Handles standard multiplier prefixes (`1000000`, `100000`, `10000`, `1000`, `100`, `k`, `1M`)
- **Rate Conversion**: Divides API rate by 8 for CEX-standard alignment
- **Market ID**: Unique numeric market_id for each contract
- **Historical Data**: 1-hour resolution (up to 1000 records per request)

### Pacifica (25 contracts)
- **Funding Intervals**: 1h
- **Platform**: Pacifica Finance DEX
- **Features**: Rich data including funding rates, prices, and open interest
- **API**: REST API with prices endpoint
- **Base Asset Normalization**: Standard format from API

### Hibachi (20 contracts)
- **Funding Intervals**: 8h
- **Platform**: High-performance, privacy-focused DEX
- **Features**: Combines speed of centralized platforms with cryptographic integrity
- **Known Markets**: BTC, ETH, SOL with up to 5x leverage
- **API**: REST API with market data endpoints

### dYdX (199 contracts)
- **Funding Intervals**: 8h
- **Platform**: dYdX v4 DEX
- **API**: Indexer API for perpetual market data
- **Features**: Active market filtering, comprehensive perpetual support
- **Base Asset Normalization**: Extracts from ticker format (e.g., "BTC-USD" → "BTC")

---

## Disabled Exchanges

### EdgeX and ApeX
- **Status**: Disabled - API not accessible
- **Reason**: API endpoints unavailable or authentication issues

### Kraken
- **Status**: Ready but disabled
- **Contracts**: Implementation available for 353 contracts
- **Reason**: Can be enabled when needed

---

## Adding a New Exchange

Follow these steps to integrate a new exchange:

### 1. Create Exchange Implementation

Create `exchanges/new_exchange.py`:

```python
from exchanges.base_exchange import BaseExchange

class NewExchange(BaseExchange):
    def fetch_data(self):
        # Implement API call with rate limiting
        pass

    def normalize_data(self, raw_data):
        # Convert to standard 12-column format
        pass
```

### 2. Register in Factory

Update `exchanges/exchange_factory.py`:

```python
from exchanges.new_exchange import NewExchange
# Add to imports and exchange_classes dict
```

### 3. Enable in Configuration

Update `config/settings.py`:

```python
EXCHANGES = {
    'new_exchange': {'enabled': True, 'rate_limit': 30}
}
```

### 4. Test Implementation

```bash
python -c "from exchanges.new_exchange import NewExchange; e=NewExchange(); print(len(e.fetch_data()))"
```

---

## Exchange Comparison Table

| Exchange | Type | Contracts | Intervals | Rate Limit | Historical Data |
|----------|------|-----------|-----------|------------|-----------------|
| Binance | CEX | 592 | 1h, 4h, 8h | 40 req/s | Unlimited |
| KuCoin | CEX | 522 | 1h, 2h, 4h, 8h | 30 req/s | Recent only |
| ByBit | CEX | 667 | 1h, 2h, 4h, 8h | 50 req/s | 200 per page |
| MEXC | CEX | 826 | 8h | Standard | Available |
| Backpack | CEX | 63 | 1h | 20 req/s | 7+ months |
| Deribit | CEX | 20 | 8h | Standard | Available |
| Hyperliquid | DEX | 182 | 1h | None | N/A |
| Drift | DEX | 51 | 1h | None | N/A |
| Aster | DEX | 123 | 4h | 40 req/s | N/A |
| Lighter | DEX | 91 | 8h | Standard | 1h resolution |
| Pacifica | DEX | 25 | 1h | Standard | N/A |
| Hibachi | DEX | 20 | 8h | Standard | N/A |
| dYdX | DEX | 199 | 8h | Standard | N/A |

---

## Symbol Normalization Reference

Each exchange uses different multiplier conventions. The system automatically normalizes these:

- **Numerical prefixes**: `1000SHIB` → `SHIB`, `10000CAT` → `CAT`, `1000000MOG` → `MOG`
- **Million denomination**: `1MBABYDOGE` → `BABYDOGE`
- **Thousand denomination**: `1K` prefix (Drift: `1KMEW` → `MEW`)
- **K-prefix tokens**: `kPEPE` → `PEPE`, `kBONK` → `BONK` (Hyperliquid, Backpack, Aster, MEXC)
- **Special cases**:
  - KuCoin: `1000X` → `X` (X token with 1000x denomination, not a multiplier)
  - KuCoin: `XBT` → `BTC` (Bitcoin symbol mapping)
  - MEXC: Removes numerical prefixes during fetch (`1000BONK` → `BONK`)
  - Drift: Removes `-PERP` suffix (`SOL-PERP` → `SOL`)
