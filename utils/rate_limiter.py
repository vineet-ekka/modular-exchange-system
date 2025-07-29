"""
Rate Limiter for Exchange APIs
===============================
Implements per-exchange rate limiting with token bucket algorithm
and automatic backoff on 429 responses.
"""

import time
import threading
from collections import defaultdict
from typing import Dict, Optional


class RateLimiter:
    """
    Token bucket rate limiter with per-exchange limits.
    
    Supports:
    - Per-exchange rate limits
    - Token bucket algorithm for smooth rate limiting
    - Automatic backoff on 429 responses
    - Thread-safe operations
    """
    
    def __init__(self):
        """Initialize rate limiter with default exchange limits."""
        # Exchange-specific rate limits (requests per second)
        self.rate_limits = {
            'binance': 40,      # 2400/min = 40/sec
            'kucoin': 10,       # 100/10s = 10/sec
            'backpack': 10,     # Conservative default
            'deribit': 10,      # Conservative estimate
            'kraken': 15,       # 60/10s public = 6/sec, but we fetch multiple endpoints
            'default': 5        # Default for unknown exchanges
        }
        
        # Token buckets for each exchange
        self.buckets = defaultdict(lambda: {
            'tokens': 0,
            'last_update': time.time(),
            'backoff_until': 0
        })
        
        # Thread lock for bucket updates
        self.lock = threading.Lock()
        
        # Initialize buckets with full tokens
        for exchange in self.rate_limits:
            self.buckets[exchange]['tokens'] = self.rate_limits.get(exchange, self.rate_limits['default'])
    
    def get_rate_limit(self, exchange: str) -> float:
        """
        Get the rate limit for a specific exchange.
        
        Args:
            exchange: Exchange name
            
        Returns:
            Requests per second limit
        """
        return self.rate_limits.get(exchange, self.rate_limits['default'])
    
    def set_rate_limit(self, exchange: str, requests_per_second: float):
        """
        Set a custom rate limit for an exchange.
        
        Args:
            exchange: Exchange name
            requests_per_second: Maximum requests per second
        """
        self.rate_limits[exchange] = requests_per_second
        with self.lock:
            if exchange not in self.buckets:
                self.buckets[exchange]['tokens'] = requests_per_second
    
    def acquire(self, exchange: str, tokens: float = 1.0) -> float:
        """
        Acquire tokens from the bucket, waiting if necessary.
        
        Args:
            exchange: Exchange name
            tokens: Number of tokens to acquire (default 1)
            
        Returns:
            Time waited in seconds
        """
        exchange = exchange.lower()
        rate_limit = self.get_rate_limit(exchange)
        wait_time = 0
        
        with self.lock:
            bucket = self.buckets[exchange]
            current_time = time.time()
            
            # Check if we're in backoff period
            if current_time < bucket['backoff_until']:
                wait_time = bucket['backoff_until'] - current_time
                time.sleep(wait_time)
                current_time = time.time()
            
            # Refill tokens based on time elapsed
            time_elapsed = current_time - bucket['last_update']
            bucket['tokens'] = min(
                rate_limit,
                bucket['tokens'] + time_elapsed * rate_limit
            )
            bucket['last_update'] = current_time
            
            # Wait if not enough tokens
            if bucket['tokens'] < tokens:
                tokens_needed = tokens - bucket['tokens']
                additional_wait = tokens_needed / rate_limit
                wait_time += additional_wait
                time.sleep(additional_wait)
                
                # Update tokens after waiting
                bucket['tokens'] = 0
                bucket['last_update'] = time.time()
            else:
                bucket['tokens'] -= tokens
        
        return wait_time
    
    def handle_429(self, exchange: str, retry_after: Optional[float] = None):
        """
        Handle 429 (Too Many Requests) response.
        
        Args:
            exchange: Exchange name
            retry_after: Seconds to wait (from Retry-After header)
        """
        with self.lock:
            bucket = self.buckets[exchange.lower()]
            
            # Default backoff: 60 seconds if no Retry-After header
            backoff_time = retry_after if retry_after else 60
            
            # Set backoff period
            bucket['backoff_until'] = time.time() + backoff_time
            
            # Reset tokens to 0
            bucket['tokens'] = 0
            
        print(f"! Rate limit hit for {exchange}. Backing off for {backoff_time:.1f} seconds")
    
    def reset(self, exchange: str):
        """
        Reset the rate limiter for a specific exchange.
        
        Args:
            exchange: Exchange name
        """
        with self.lock:
            rate_limit = self.get_rate_limit(exchange)
            self.buckets[exchange.lower()] = {
                'tokens': rate_limit,
                'last_update': time.time(),
                'backoff_until': 0
            }
    
    def get_status(self) -> Dict[str, Dict]:
        """
        Get current status of all rate limiters.
        
        Returns:
            Dictionary with status for each exchange
        """
        status = {}
        current_time = time.time()
        
        with self.lock:
            for exchange, bucket in self.buckets.items():
                if exchange == 'default':
                    continue
                    
                in_backoff = current_time < bucket['backoff_until']
                backoff_remaining = max(0, bucket['backoff_until'] - current_time)
                
                status[exchange] = {
                    'tokens_available': bucket['tokens'],
                    'rate_limit': self.get_rate_limit(exchange),
                    'in_backoff': in_backoff,
                    'backoff_remaining': backoff_remaining if in_backoff else 0
                }
        
        return status
    
    def wait_if_needed(self, exchange: str) -> float:
        """
        Convenience method to wait based on rate limits without acquiring tokens.
        Useful for checking if we should wait before making a request.
        
        Args:
            exchange: Exchange name
            
        Returns:
            Time until next request can be made (0 if ready now)
        """
        exchange = exchange.lower()
        
        with self.lock:
            bucket = self.buckets[exchange]
            current_time = time.time()
            
            # Check backoff
            if current_time < bucket['backoff_until']:
                return bucket['backoff_until'] - current_time
            
            # Check tokens
            if bucket['tokens'] < 1:
                rate_limit = self.get_rate_limit(exchange)
                return (1 - bucket['tokens']) / rate_limit
            
            return 0


# Global rate limiter instance
rate_limiter = RateLimiter()