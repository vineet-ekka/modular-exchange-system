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
    ("backpack", 120),    # Starts 120s after collection begins
    ("hyperliquid", 180), # Starts 180s after collection begins (1-hour funding)
    ("kraken", 210),      # Would start 210s after collection begins (when enabled)
    ("deribit", 240),     # Would start 240s after collection begins (when enabled)
]

# Alternative schedules for different scenarios
SCHEDULES = {
    # Default: Stagger exchanges evenly
    "default": EXCHANGE_SCHEDULE,
    
    # Fast: Minimal delays for quick collection
    "fast": [
        ("binance", 0),
        ("kucoin", 10),
        ("backpack", 20),
        ("hyperliquid", 30),
        ("kraken", 40),
        ("deribit", 50),
    ],
    
    # Conservative: Longer delays to minimize API load
    "conservative": [
        ("binance", 0),
        ("kucoin", 60),
        ("backpack", 180),
        ("hyperliquid", 240),
        ("kraken", 300),
        ("deribit", 360),
    ],
    
    # Priority: Collect most important exchanges first with minimal delay
    "priority": [
        ("binance", 0),     # Highest volume
        ("kucoin", 5),      # Second highest
        ("hyperliquid", 10), # DEX with hourly funding
        ("backpack", 45),   # Lower priority
        ("kraken", 50),     # Lower priority
        ("deribit", 55),    # Lower priority
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