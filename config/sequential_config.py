"""
Sequential Collection Configuration
====================================
Configure the order and timing of exchange data collection.
"""

# Exchange collection schedule
# Format: (exchange_name, delay_seconds)
# The first exchange starts immediately (0s), subsequent exchanges are delayed
EXCHANGE_SCHEDULE = [
    ("binance", 0),       # Starts immediately
    ("kucoin", 30),       # Starts 30s after collection begins
    ("bybit", 90),        # Starts 90s after collection begins (696 contracts)
    ("backpack", 120),    # Starts 120s after collection begins
    ("hyperliquid", 180), # Starts 180s after collection begins (1-hour funding)
    ("aster", 210),       # Starts 210s after collection begins
    ("drift", 240),       # Starts 240s after collection begins (Solana DEX, 1-hour funding)
    ("lighter", 265),     # Starts 265s after collection begins (blockchain DEX)
    ("pacifica", 270),    # Starts 270s after collection begins (Pacifica Finance)
    ("paradex", 275),     # Starts 275s after collection begins (Starknet DEX)
    ("kraken", 300),      # Would start 300s after collection begins (when enabled)
    ("deribit", 330),     # Would start 330s after collection begins (when enabled)
]

# Alternative schedules for different scenarios
SCHEDULES = {
    # Default: Stagger exchanges evenly
    "default": EXCHANGE_SCHEDULE,
    
    # Fast: Minimal delays for quick collection
    "fast": [
        ("binance", 0),
        ("kucoin", 10),
        ("bybit", 15),
        ("backpack", 20),
        ("hyperliquid", 30),
        ("aster", 35),
        ("drift", 40),
        ("lighter", 45),
        ("pacifica", 50),
        ("paradex", 52),
        ("kraken", 55),
        ("deribit", 60),
    ],
    
    # Conservative: Longer delays to minimize API load
    "conservative": [
        ("binance", 0),
        ("kucoin", 60),
        ("bybit", 120),
        ("backpack", 180),
        ("hyperliquid", 240),
        ("aster", 270),
        ("drift", 300),
        ("lighter", 330),
        ("pacifica", 360),
        ("paradex", 365),
        ("kraken", 390),
        ("deribit", 420),
    ],
    
    # Priority: Collect most important exchanges first with minimal delay
    "priority": [
        ("binance", 0),     # Highest volume
        ("kucoin", 5),      # Second highest
        ("bybit", 8),       # Third highest (696 contracts)
        ("hyperliquid", 10), # DEX with hourly funding
        ("aster", 12),      # DEX
        ("drift", 15),      # Solana DEX with hourly funding
        ("lighter", 18),    # Blockchain DEX
        ("pacifica", 20),   # Pacifica Finance
        ("paradex", 22),    # Starknet DEX
        ("backpack", 50),   # Lower priority
        ("kraken", 55),     # Lower priority
        ("deribit", 60),    # Lower priority
    ],
}

# Active schedule selection
ACTIVE_SCHEDULE = "default"

def get_exchange_schedule():
    """
    Get the active exchange collection schedule.
    
    Returns:
        List of tuples (exchange_name, delay_seconds)
    """
    return SCHEDULES.get(ACTIVE_SCHEDULE, SCHEDULES["default"])

def get_exchange_delay(exchange_name: str) -> int:
    """
    Get the delay for a specific exchange.
    
    Args:
        exchange_name: Name of the exchange
        
    Returns:
        Delay in seconds, or None if exchange not in schedule
    """
    schedule = get_exchange_schedule()
    for name, delay in schedule:
        if name.lower() == exchange_name.lower():
            return delay
    return None