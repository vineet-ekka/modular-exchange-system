# Bonkers Plan: Fix Base Asset Normalization for Prefix Tokens

## Problem Summary

Tokens with special prefixes are not properly normalized across exchanges, causing the same asset to appear as multiple different assets in the system:

- **Hyperliquid**: Uses 'k' prefix for micro-cap tokens (e.g., `kSHIB`, `kPEPE`, `kBONK`)
- **Binance**: Uses '1000' or '1000000' prefix for contracts representing thousands/millions of units (e.g., `1000SHIBUSDT`, `1000PEPEUSDC`, `1000000MOGUSDT`)

This prevents proper aggregation and comparison of the same asset across different exchanges.

## Current Incorrect Behavior

| Exchange | Symbol | Current base_asset | Should Be |
|----------|--------|-------------------|-----------|
| Binance | 1000SHIBUSDT | 1000SHIB | SHIB |
| Binance | 1000SHIBUSDC | 1000SHIB | SHIB |
| Hyperliquid | kSHIB | SHIBK | SHIB |
| KuCoin | SHIBUSDT | SHIB | SHIB |
| Binance | 1000PEPEUSDT | 1000PEPE | PEPE |
| Hyperliquid | kPEPE | PEPEK | PEPE |
| Binance | 1000BONKUSDT | 1000BONK | BONK |
| Hyperliquid | kBONK | BONKK | BONK |

## Identified Tokens Requiring Normalization

### Hyperliquid 'k' Prefix Tokens
1. `kBONK` → BONK
2. `kDOGS` → DOGS
3. `kFLOKI` → FLOKI
4. `kLUNC` → LUNC
5. `kNEIRO` → NEIRO
6. `kPEPE` → PEPE
7. `kSHIB` → SHIB

### Binance '1000' Prefix Tokens
1. `1000BONKUSDT` / `1000BONKUSDC` → BONK
2. `1000CATUSDT` → CAT
3. `1000CHEEMSUSDT` → CHEEMS
4. `1000FLOKIUSDT` → FLOKI
5. `1000LUNCUSDT` → LUNC
6. `1000PEPEUSDT` / `1000PEPEUSDC` → PEPE
7. `1000RATSUSDT` → RATS
8. `1000SATSUSDT` → SATS
9. `1000SHIBUSDT` / `1000SHIBUSDC` → SHIB
10. `1000WHYUSDT` → WHY
11. `1000XECUSDT` → XEC
12. `1000XUSDT` → X

### Binance '1000000' Prefix Tokens
1. `1000000BOBUSDT` → BOB
2. `1000000MOGUSDT` → MOG

## Implementation Plan

### 1. Update Hyperliquid Exchange (`exchanges/hyperliquid_exchange.py`)

**Current Code (Line ~129-139):**
```python
def normalize_asset_name(name):
    if pd.isna(name):
        return name
    name = str(name)
    # Handle 'k' prefix (thousands) - keep as is for identification
    if name.startswith('k'):
        return name[1:] + 'K'  # e.g., kPEPE -> PEPEK
    # Handle '@' prefix (indices) - keep for identification
    if name.startswith('@'):
        return 'INDEX' + name[1:]  # e.g., @1 -> INDEX1
    return name
```

**Fix To:**
```python
def normalize_asset_name(name):
    if pd.isna(name):
        return name
    name = str(name)
    # Handle 'k' prefix (thousands) - remove prefix for base asset
    if name.startswith('k'):
        return name[1:]  # e.g., kPEPE -> PEPE
    # Handle '@' prefix (indices) - keep for identification
    if name.startswith('@'):
        return 'INDEX' + name[1:]  # e.g., @1 -> INDEX1
    return name
```

### 2. Update Binance Exchange (`exchanges/binance_exchange.py`)

**Current Code (Line ~326-330):**
```python
normalized = pd.DataFrame({
    'exchange': 'Binance',
    'symbol': df['symbol'],
    'base_asset': df['baseAsset'],
    'quote_asset': df['quoteAsset'],
    ...
```

**Fix To:**
```python
# Add helper function before normalize_data method
def extract_clean_base_asset(symbol, original_base_asset):
    """
    Extract the actual base asset without multiplier prefixes.
    
    Examples:
    - 1000SHIBUSDT -> SHIB
    - 1000000MOGUSDT -> MOG
    - BTCUSDT -> BTC (unchanged)
    """
    if symbol.startswith('1000000'):
        # Remove the 1000000 prefix and any quote currency suffix
        clean = symbol[7:]  # Remove '1000000'
        # Remove common quote currencies
        for suffix in ['USDT', 'USDC', 'BUSD', 'USD']:
            if clean.endswith(suffix):
                return clean[:-len(suffix)]
        return clean
    elif symbol.startswith('1000'):
        # Remove the 1000 prefix and any quote currency suffix
        clean = symbol[4:]  # Remove '1000'
        # Remove common quote currencies
        for suffix in ['USDT', 'USDC', 'BUSD', 'USD']:
            if clean.endswith(suffix):
                return clean[:-len(suffix)]
        return clean
    else:
        # Return the original base asset for normal symbols
        return original_base_asset

# Update normalize_data method
normalized = pd.DataFrame({
    'exchange': 'Binance',
    'symbol': df['symbol'],
    'base_asset': df.apply(lambda row: extract_clean_base_asset(row['symbol'], row['baseAsset']), axis=1),
    'quote_asset': df['quoteAsset'],
    ...
```

### 3. Optional Enhancement: Add Units Multiplier Field

Consider adding a `units_multiplier` field to track contract sizes:

```python
# In database schema
units_multiplier INTEGER DEFAULT 1

# In normalization
def get_units_multiplier(symbol):
    if symbol.startswith('1000000'):
        return 1000000
    elif symbol.startswith('1000') or symbol.startswith('k'):
        return 1000
    return 1
```

## Testing Strategy

### 1. Unit Tests
Create test cases for the normalization functions:

```python
test_cases = [
    # Binance cases
    ('1000SHIBUSDT', 'SHIB'),
    ('1000PEPEUSDC', 'PEPE'),
    ('1000000MOGUSDT', 'MOG'),
    ('BTCUSDT', 'BTC'),
    
    # Hyperliquid cases  
    ('kSHIB', 'SHIB'),
    ('kPEPE', 'PEPE'),
    ('BTC', 'BTC'),
]
```

### 2. Integration Tests
- Fetch live data from both exchanges
- Verify base assets are normalized correctly
- Check database queries group assets properly

### 3. Verification Queries
```sql
-- Check if SHIB is properly grouped
SELECT exchange, symbol, base_asset 
FROM exchange_data 
WHERE base_asset = 'SHIB'
ORDER BY exchange, symbol;

-- Should return:
-- Binance | 1000SHIBUSDT | SHIB
-- Binance | 1000SHIBUSDC | SHIB  
-- Hyperliquid | kSHIB | SHIB
-- KuCoin | SHIBUSDT | SHIB
```

## Expected Outcomes

1. **Unified Asset View**: Users can see all SHIB, PEPE, BONK, etc. contracts grouped together regardless of exchange-specific prefixes

2. **Accurate Cross-Exchange Comparison**: Funding rates for the same asset can be properly compared across exchanges

3. **Improved Dashboard Display**: The dashboard will correctly show aggregated data for each asset

4. **Preserved Exchange Functionality**: Original symbols remain intact for API calls to each exchange

## Implementation Order

1. **Phase 1**: Update Hyperliquid normalization (simpler change)
2. **Phase 2**: Update Binance normalization (more complex with multiple prefix types)
3. **Phase 3**: Test with live data
4. **Phase 4**: Deploy and monitor

## Rollback Plan

If issues arise:
1. Revert the normalization functions to original code
2. Clear cached data
3. Re-run data collection with original logic

## Notes

- The original symbol must be preserved for API calls to exchanges
- Only the `base_asset` field should be normalized
- This change affects both real-time and historical data collection
- Consider running a migration script to update existing database records