"""
Redis Cache Manager for Exchange Data API
Provides distributed caching with automatic fallback to in-memory cache
"""

import redis
import json
import time
import os
from typing import Any, Optional, Dict
from datetime import datetime, timezone
import logging

logger = logging.getLogger(__name__)


class RedisCache:
    """Redis cache with automatic fallback to SimpleCache."""
    
    def __init__(self, host: str = None, port: int = None, db: int = 0, password: str = None):
        """Initialize Redis cache with connection parameters."""
        self.host = host or os.getenv('REDIS_HOST', 'localhost')
        self.port = port or int(os.getenv('REDIS_PORT', 6379))
        self.db = db or int(os.getenv('REDIS_DB', 0))
        self.password = password or os.getenv('REDIS_PASSWORD', None)
        
        # Performance metrics
        self.metrics = {
            'hits': 0,
            'misses': 0,
            'errors': 0,
            'fallback_count': 0
        }
        
        # Try to establish Redis connection
        self.redis_client = None
        self.fallback_cache = SimpleCache()  # Fallback to in-memory cache
        self._connect()
    
    def _connect(self) -> bool:
        """Establish connection to Redis server."""
        try:
            # Create connection pool for better performance
            pool = redis.ConnectionPool(
                host=self.host,
                port=self.port,
                db=self.db,
                password=self.password,
                socket_connect_timeout=2,
                socket_timeout=2,
                max_connections=10,
                decode_responses=True
            )
            
            self.redis_client = redis.Redis(connection_pool=pool)
            
            # Test connection
            self.redis_client.ping()
            logger.info(f"Redis cache connected to {self.host}:{self.port}")
            return True
            
        except (redis.ConnectionError, redis.TimeoutError) as e:
            logger.warning(f"Redis connection failed: {e}. Using in-memory cache fallback.")
            self.redis_client = None
            self.metrics['errors'] += 1
            return False
    
    def get(self, key: str, ttl_seconds: int = 5) -> Optional[Any]:
        """Get value from cache with automatic fallback."""
        try:
            # Try Redis first
            if self.redis_client:
                try:
                    value = self.redis_client.get(key)
                    if value:
                        self.metrics['hits'] += 1
                        # Deserialize JSON data
                        return json.loads(value)
                    else:
                        self.metrics['misses'] += 1
                        return None
                        
                except (redis.ConnectionError, redis.TimeoutError) as e:
                    logger.debug(f"Redis get error: {e}")
                    self.metrics['errors'] += 1
                    self.redis_client = None  # Mark as disconnected
        
        except Exception as e:
            logger.error(f"Unexpected cache get error: {e}")
            self.metrics['errors'] += 1
        
        # Fallback to in-memory cache
        self.metrics['fallback_count'] += 1
        return self.fallback_cache.get(key, ttl_seconds)
    
    def set(self, key: str, value: Any, ttl_seconds: int = 5) -> bool:
        """Set value in cache with TTL."""
        try:
            # Try Redis first
            if self.redis_client:
                try:
                    # Serialize to JSON
                    json_value = json.dumps(value, default=str)
                    self.redis_client.setex(key, ttl_seconds, json_value)
                    return True
                    
                except (redis.ConnectionError, redis.TimeoutError) as e:
                    logger.debug(f"Redis set error: {e}")
                    self.metrics['errors'] += 1
                    self.redis_client = None  # Mark as disconnected
        
        except Exception as e:
            logger.error(f"Unexpected cache set error: {e}")
            self.metrics['errors'] += 1
        
        # Fallback to in-memory cache
        self.fallback_cache.set(key, value)
        return True
    
    def delete(self, key: str) -> bool:
        """Delete key from cache."""
        try:
            if self.redis_client:
                self.redis_client.delete(key)
            self.fallback_cache.cache.pop(key, None)
            self.fallback_cache.timestamps.pop(key, None)
            return True
        except Exception as e:
            logger.error(f"Cache delete error: {e}")
            return False
    
    def clear(self) -> bool:
        """Clear all cache entries."""
        try:
            if self.redis_client:
                self.redis_client.flushdb()
            self.fallback_cache.clear()
            return True
        except Exception as e:
            logger.error(f"Cache clear error: {e}")
            return False
    
    def get_metrics(self) -> Dict:
        """Get cache performance metrics."""
        hit_rate = self.metrics['hits'] / (self.metrics['hits'] + self.metrics['misses']) if (self.metrics['hits'] + self.metrics['misses']) > 0 else 0
        
        return {
            'type': 'Redis' if self.redis_client else 'SimpleCache (fallback)',
            'connected': self.redis_client is not None,
            'host': f"{self.host}:{self.port}" if self.redis_client else 'in-memory',
            'metrics': {
                'hits': self.metrics['hits'],
                'misses': self.metrics['misses'],
                'hit_rate': round(hit_rate, 3),
                'errors': self.metrics['errors'],
                'fallback_count': self.metrics['fallback_count']
            }
        }
    
    def health_check(self) -> bool:
        """Check if Redis is healthy and reconnect if needed."""
        if not self.redis_client:
            # Try to reconnect
            return self._connect()
        
        try:
            self.redis_client.ping()
            return True
        except:
            self.redis_client = None
            return self._connect()


class SimpleCache:
    """Simple in-memory cache with TTL support (fallback cache)."""
    
    def __init__(self):
        self.cache = {}
        self.timestamps = {}
    
    def get(self, key: str, ttl_seconds: int = 5) -> Optional[Any]:
        """Get cached value if not expired."""
        if key not in self.cache:
            return None
        
        # Check if cache expired
        if time.time() - self.timestamps[key] > ttl_seconds:
            del self.cache[key]
            del self.timestamps[key]
            return None
        
        return self.cache[key]
    
    def set(self, key: str, value: Any) -> None:
        """Set cache value with current timestamp."""
        self.cache[key] = value
        self.timestamps[key] = time.time()
    
    def clear(self) -> None:
        """Clear all cache entries."""
        self.cache.clear()
        self.timestamps.clear()


# Cache key generators for consistency
class CacheKeys:
    """Standard cache key generators for API endpoints."""
    
    @staticmethod
    def contracts_with_zscores(exchange: str = None, base_asset: str = None, 
                              min_abs_zscore: float = None, sort_by: str = None) -> str:
        """Generate cache key for contracts with z-scores endpoint."""
        parts = ['contracts_zscores']
        if exchange:
            parts.append(f'ex:{exchange}')
        if base_asset:
            parts.append(f'ba:{base_asset}')
        if min_abs_zscore is not None:
            parts.append(f'mz:{min_abs_zscore}')
        if sort_by:
            parts.append(f'sb:{sort_by}')
        return ':'.join(parts)
    
    @staticmethod
    def statistics_summary() -> str:
        """Generate cache key for statistics summary."""
        return 'statistics_summary'
    
    @staticmethod
    def extreme_values(threshold: float = 2.0, limit: int = 20) -> str:
        """Generate cache key for extreme values endpoint."""
        return f'extreme_values:t{threshold}:l{limit}'
    
    @staticmethod
    def funding_rates_grid(exchange: str = None, symbol: str = None) -> str:
        """Generate cache key for funding rates grid."""
        parts = ['funding_grid']
        if exchange:
            parts.append(f'ex:{exchange}')
        if symbol:
            parts.append(f's:{symbol}')
        return ':'.join(parts)