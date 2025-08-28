"""
Test normalization functions for Hyperliquid and Binance exchanges
According to the bonkers plan
"""

# Test Hyperliquid normalization
def test_hyperliquid_normalize_asset_name():
    """Test Hyperliquid asset name normalization"""
    def normalize_asset_name(name):
        if name is None:
            return name
        name = str(name)
        # Handle 'k' prefix (thousands) - remove prefix for base asset
        if name.startswith('k'):
            return name[1:]  # e.g., kPEPE -> PEPE
        # Handle '@' prefix (indices) - keep for identification
        if name.startswith('@'):
            return 'INDEX' + name[1:]  # e.g., @1 -> INDEX1
        return name
    
    # Test cases from the plan
    test_cases = [
        ('kSHIB', 'SHIB'),
        ('kPEPE', 'PEPE'),
        ('kBONK', 'BONK'),
        ('kDOGS', 'DOGS'),
        ('kFLOKI', 'FLOKI'),
        ('kLUNC', 'LUNC'),
        ('kNEIRO', 'NEIRO'),
        ('BTC', 'BTC'),
        ('@1', 'INDEX1'),
    ]
    
    print("Testing Hyperliquid normalization:")
    for input_val, expected in test_cases:
        result = normalize_asset_name(input_val)
        status = "PASS" if result == expected else "FAIL"
        print(f"  {status} {input_val} -> {result} (expected: {expected})")
    print()

# Test Binance normalization
def test_binance_extract_clean_base_asset():
    """Test Binance base asset extraction"""
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
    
    # Test cases from the plan
    test_cases = [
        ('1000SHIBUSDT', '1000SHIB', 'SHIB'),
        ('1000SHIBUSDC', '1000SHIB', 'SHIB'),
        ('1000PEPEUSDT', '1000PEPE', 'PEPE'),
        ('1000PEPEUSDC', '1000PEPE', 'PEPE'),
        ('1000BONKUSDT', '1000BONK', 'BONK'),
        ('1000CATUSDT', '1000CAT', 'CAT'),
        ('1000CHEEMSUSDT', '1000CHEEMS', 'CHEEMS'),
        ('1000FLOKIUSDT', '1000FLOKI', 'FLOKI'),
        ('1000LUNCUSDT', '1000LUNC', 'LUNC'),
        ('1000RATSUSDT', '1000RATS', 'RATS'),
        ('1000SATSUSDT', '1000SATS', 'SATS'),
        ('1000WHYUSDT', '1000WHY', 'WHY'),
        ('1000XECUSDT', '1000XEC', 'XEC'),
        ('1000XUSDT', '1000X', 'X'),
        ('1000000BOBUSDT', '1000000BOB', 'BOB'),
        ('1000000MOGUSDT', '1000000MOG', 'MOG'),
        ('BTCUSDT', 'BTC', 'BTC'),
    ]
    
    print("Testing Binance normalization:")
    for symbol, orig_base, expected in test_cases:
        result = extract_clean_base_asset(symbol, orig_base)
        status = "PASS" if result == expected else "FAIL"
        print(f"  {status} {symbol} (orig: {orig_base}) -> {result} (expected: {expected})")
    print()

if __name__ == "__main__":
    test_hyperliquid_normalize_asset_name()
    test_binance_extract_clean_base_asset()
    print("All tests completed!")