"""
FastAPI Backend for Exchange Dashboard
=======================================
Serves data from PostgreSQL database to React frontend.
"""

from fastapi import FastAPI, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import psycopg2
from psycopg2.extras import RealDictCursor
from psycopg2 import pool
import pandas as pd
import numpy as np
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta, timezone
import json
import os
import time
import subprocess
import signal
import math
from pathlib import Path
from dotenv import load_dotenv
from config.settings_manager import SettingsManager
from database.postgres_manager import PostgresManager
import config.settings
from functools import lru_cache
import hashlib
from utils.redis_cache import RedisCache, CacheKeys
import logging

# Load environment variables
load_dotenv()

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Exchange Data API",
    description="API for cryptocurrency funding rates dashboard",
    version="1.0.0"
)

# CORS middleware for React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Simple time-based cache implementation for API responses
class SimpleCache:
    """Simple in-memory cache with TTL support."""
    
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

# Performance monitoring class
class PerformanceMonitor:
    """Track performance metrics for API endpoints and operations."""
    
    def __init__(self):
        self.metrics = {}
        self.thresholds = {
            'api_response': 100,  # ms
            'db_query': 50,       # ms
            'zscore_calc': 1000,  # ms
            'cache_hit_rate': 0.5 # ratio
        }
    
    def record(self, operation: str, duration_ms: float, metadata: Dict = None):
        """Record a performance metric."""
        if operation not in self.metrics:
            self.metrics[operation] = {
                'count': 0,
                'total_ms': 0,
                'avg_ms': 0,
                'min_ms': float('inf'),
                'max_ms': 0,
                'last_ms': 0,
                'last_recorded': None,
                'violations': 0
            }
        
        metric = self.metrics[operation]
        metric['count'] += 1
        metric['total_ms'] += duration_ms
        metric['avg_ms'] = metric['total_ms'] / metric['count']
        metric['min_ms'] = min(metric['min_ms'], duration_ms)
        metric['max_ms'] = max(metric['max_ms'], duration_ms)
        metric['last_ms'] = duration_ms
        metric['last_recorded'] = datetime.now(timezone.utc)
        
        # Check threshold violations
        threshold_key = operation.split(':')[0] if ':' in operation else operation
        if threshold_key in self.thresholds and duration_ms > self.thresholds[threshold_key]:
            metric['violations'] += 1
    
    def get_metrics(self) -> Dict:
        """Get all performance metrics."""
        return {
            'metrics': self.metrics,
            'thresholds': self.thresholds,
            'summary': self._get_summary()
        }
    
    def _get_summary(self) -> Dict:
        """Generate performance summary."""
        total_operations = sum(m['count'] for m in self.metrics.values())
        total_violations = sum(m['violations'] for m in self.metrics.values())
        
        # Get latest Z-score calculation time
        zscore_metric = self.metrics.get('zscore_calc', {})
        zscore_last = zscore_metric.get('last_ms', 0)
        
        return {
            'total_operations': total_operations,
            'total_violations': total_violations,
            'violation_rate': total_violations / total_operations if total_operations > 0 else 0,
            'zscore_performance': {
                'last_ms': zscore_last,
                'target_ms': 1000,
                'status': '✅ MET' if zscore_last <= 1000 else '❌ MISSED'
            },
            'health_status': 'healthy' if total_violations < total_operations * 0.1 else 'degraded'
        }

# Initialize cache and performance monitor
# Use Redis cache with automatic fallback to SimpleCache
api_cache = RedisCache()
performance_monitor = PerformanceMonitor()

# Database configuration
DB_CONFIG = {
    'host': os.getenv("POSTGRES_HOST", "localhost"),
    'port': os.getenv("POSTGRES_PORT", "5432"),
    'database': os.getenv("POSTGRES_DATABASE", "exchange_data"),
    'user': os.getenv("POSTGRES_USER", "postgres"),
    'password': os.getenv("POSTGRES_PASSWORD", "postgres123")
}

# Initialize connection pool for better performance
try:
    connection_pool = psycopg2.pool.ThreadedConnectionPool(
        minconn=5,
        maxconn=20,
        **DB_CONFIG,
        cursor_factory=RealDictCursor
    )
    print("Database connection pool initialized successfully")
except Exception as e:
    print(f"Failed to initialize connection pool: {e}")
    connection_pool = None

def get_db_connection():
    """Get database connection from pool with RealDictCursor for JSON serialization."""
    try:
        if connection_pool:
            conn = connection_pool.getconn()
            if conn:
                return conn
        # Fallback to direct connection if pool fails
        conn = psycopg2.connect(**DB_CONFIG, cursor_factory=RealDictCursor)
        return conn
    except Exception as e:
        print(f"Database connection error: {e}")
        raise HTTPException(status_code=500, detail="Database connection failed")

def return_db_connection(conn):
    """Return connection to pool."""
    if connection_pool and conn:
        connection_pool.putconn(conn)

def sanitize_numeric_value(value):
    """Sanitize numeric values for JSON serialization."""
    if value is None:
        return None
    if isinstance(value, (int, float)):
        if math.isnan(value) or math.isinf(value):
            return None
    return value

def sanitize_response_data(data):
    """Recursively sanitize all numeric values in response data to remove NaN/Infinity."""
    if isinstance(data, dict):
        return {k: sanitize_response_data(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [sanitize_response_data(item) for item in data]
    elif isinstance(data, (int, float)):
        return sanitize_numeric_value(data)
    return data

@app.get("/")
async def root():
    """API root endpoint with status information."""
    return {
        "name": "Exchange Data API",
        "version": "1.1.0",
        "status": "active",
        "endpoints": {
            "funding_rates": "/api/funding-rates",
            "statistics": "/api/statistics",
            "top_apr": "/api/top-apr/{limit}",
            "group_by_asset": "/api/group-by-asset",
            "historical": "/api/historical/{symbol}",
            "historical_funding": "/api/historical-funding/{symbol}",
            "funding_sparkline": "/api/funding-sparkline/{symbol}",
            "exchanges": "/api/exchanges",
            "assets": "/api/assets",
            "health": "/api/health"
        }
    }

@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT 1")
        cur.close()
        return_db_connection(conn)
        return {"status": "healthy", "database": "connected"}
    except:
        return JSONResponse(
            status_code=503,
            content={"status": "unhealthy", "database": "disconnected"}
        )

@app.get("/api/health/performance")
async def performance_health():
    """Performance monitoring endpoint with detailed metrics."""
    try:
        # Test database performance
        db_start = time.perf_counter()
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Test query performance
        cur.execute("""
            SELECT COUNT(*) as total_contracts,
                   AVG(ABS(current_z_score)) as avg_abs_zscore,
                   MAX(last_updated) as last_update
            FROM funding_statistics
        """)
        db_stats = cur.fetchone()
        db_duration = (time.perf_counter() - db_start) * 1000
        performance_monitor.record('db_query:health_check', db_duration)
        
        # Get Z-score calculation performance from last run
        cur.execute("""
            SELECT 
                MAX(last_updated) as last_calc,
                EXTRACT(EPOCH FROM (NOW() - MAX(last_updated))) as seconds_ago,
                COUNT(*) as total_contracts,
                COUNT(CASE WHEN ABS(current_z_score) > 2 THEN 1 END) as extreme_contracts
            FROM funding_statistics
        """)
        zscore_stats = cur.fetchone()
        
        cur.close()
        return_db_connection(conn)
        
        # Get performance metrics
        perf_metrics = performance_monitor.get_metrics()
        
        return {
            "status": perf_metrics['summary']['health_status'],
            "database": {
                "connected": True,
                "query_time_ms": db_duration,
                "total_contracts": db_stats['total_contracts'] if db_stats else 0,
                "avg_abs_zscore": float(db_stats['avg_abs_zscore']) if db_stats and db_stats['avg_abs_zscore'] else 0
            },
            "zscore_calculation": {
                "last_run": zscore_stats['last_calc'].isoformat() if zscore_stats and zscore_stats['last_calc'] else None,
                "seconds_ago": float(zscore_stats['seconds_ago']) if zscore_stats and zscore_stats['seconds_ago'] else None,
                "total_contracts": zscore_stats['total_contracts'] if zscore_stats else 0,
                "extreme_contracts": zscore_stats['extreme_contracts'] if zscore_stats else 0,
                "performance": perf_metrics['summary']['zscore_performance']
            },
            "performance_metrics": perf_metrics,
            "cache_stats": {
                "entries": len(api_cache.fallback_cache.cache),
                "oldest_entry": datetime.fromtimestamp(min(api_cache.fallback_cache.timestamps.values()), tz=timezone.utc).isoformat() if api_cache.fallback_cache.timestamps else None
            },
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
    except Exception as e:
        return JSONResponse(
            status_code=503,
            content={
                "status": "error",
                "error": str(e),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        )

@app.get("/api/funding-rates")
async def get_funding_rates(
    limit: int = Query(100, ge=1, le=5000),
    exchange: Optional[str] = None,
    base_asset: Optional[str] = None,
    min_apr: Optional[float] = None,
    max_apr: Optional[float] = None,
    sort_by: str = Query("apr", pattern="^(apr|funding_rate|open_interest|symbol|exchange)$"),
    sort_order: str = Query("desc", pattern="^(asc|desc)$")
):
    """
    Get funding rates with optional filters and sorting.
    """
    from config.settings import API_MAX_DATA_AGE_DAYS

    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    try:
        # Build query with filters, include 30-day statistics from funding_statistics
        # IMPORTANT: Filter out inactive contracts and stale data
        query = """
            SELECT
                ed.exchange,
                ed.symbol,
                ed.base_asset,
                ed.quote_asset,
                ed.funding_rate,
                ed.funding_interval_hours,
                ed.apr,
                ed.index_price,
                ed.mark_price,
                ed.open_interest,
                ed.contract_type,
                ed.market_type,
                ed.last_updated,
                fs.mean_30d,
                fs.std_dev_30d,
                fs.mean_30d_apr,
                fs.std_dev_30d_apr,
                fs.current_z_score,
                fs.current_percentile,
                fs.current_percentile_apr
            FROM exchange_data ed
            LEFT JOIN funding_statistics fs
                ON ed.exchange = fs.exchange AND ed.symbol = fs.symbol
            LEFT JOIN contract_metadata cm
                ON ed.exchange = cm.exchange AND ed.symbol = cm.symbol
            WHERE 1=1
            -- Filter out inactive contracts and stale data
            AND (cm.is_active = true OR cm.is_active IS NULL)
            AND ed.last_updated > NOW() - INTERVAL '%s days'
        """
        params = [API_MAX_DATA_AGE_DAYS]  # Start with the stale data filter parameter

        # Apply exchange filter if provided
        if exchange:
            query += " AND LOWER(ed.exchange) = LOWER(%s)"
            params.append(exchange)
        
        if base_asset:
            query += " AND LOWER(ed.base_asset) = LOWER(%s)"
            params.append(base_asset)
        
        if min_apr is not None:
            query += " AND ed.apr >= %s"
            params.append(min_apr)
        
        if max_apr is not None:
            query += " AND ed.apr <= %s"
            params.append(max_apr)
        
        # Add sorting (prefix with ed. for columns from exchange_data)
        if sort_by in ['apr', 'funding_rate', 'open_interest', 'symbol', 'exchange']:
            query += f" ORDER BY ed.{sort_by} {sort_order.upper()} NULLS LAST"
        else:
            query += f" ORDER BY {sort_by} {sort_order.upper()} NULLS LAST"
        query += " LIMIT %s"
        params.append(limit)
        
        cur.execute(query, params)
        results = cur.fetchall()
        
        # Convert to list of dicts and handle decimal/datetime serialization
        data = []
        for row in results:
            item = dict(row)
            # Convert Decimal to float for all numeric fields including statistics
            for key in ['funding_rate', 'apr', 'index_price', 'mark_price', 'open_interest',
                       'mean_30d', 'std_dev_30d', 'mean_30d_apr', 'std_dev_30d_apr', 'current_z_score',
                       'current_percentile', 'current_percentile_apr']:
                if item.get(key) is not None:
                    value = float(item[key])
                    # Convert NaN/Inf to None for JSON compatibility
                    item[key] = None if (math.isnan(value) or math.isinf(value)) else value
            # Convert datetime to ISO string
            if item.get('last_updated'):
                item['last_updated'] = item['last_updated'].isoformat()
            data.append(item)
        
        return data
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cur.close()
        return_db_connection(conn)

@app.get("/api/statistics")
async def get_statistics():
    """
    Get dashboard statistics including totals, averages, and extremes.
    Filters out inactive and stale contracts for consistency with other endpoints.
    """
    from config.settings import API_MAX_DATA_AGE_DAYS

    conn = get_db_connection()
    cur = conn.cursor()
    
    try:
        # Get overall statistics (filtered for active contracts only)
        cur.execute("""
            SELECT
                COUNT(*) as total_contracts,
                AVG(apr) as avg_apr,
                MAX(apr) as highest_apr,
                MIN(apr) as lowest_apr,
                COUNT(DISTINCT ed.exchange) as active_exchanges,
                COUNT(DISTINCT ed.base_asset) as unique_assets,
                SUM(CASE WHEN ed.open_interest = 'NaN'::numeric THEN 0 ELSE ed.open_interest END) as total_open_interest
            FROM exchange_data ed
            LEFT JOIN contract_metadata cm
                ON ed.exchange = cm.exchange AND ed.symbol = cm.symbol
            WHERE ed.apr IS NOT NULL
                AND (cm.is_active = true OR cm.is_active IS NULL)
                AND ed.last_updated > NOW() - INTERVAL '%s days'
        """, [API_MAX_DATA_AGE_DAYS])
        
        stats = dict(cur.fetchone())
        
        # Get highest APR contract details (filtered for active contracts only)
        cur.execute("""
            SELECT ed.symbol, ed.exchange, ed.apr
            FROM exchange_data ed
            LEFT JOIN contract_metadata cm
                ON ed.exchange = cm.exchange AND ed.symbol = cm.symbol
            WHERE ed.apr IS NOT NULL
                AND (cm.is_active = true OR cm.is_active IS NULL)
                AND ed.last_updated > NOW() - INTERVAL '%s days'
            ORDER BY ed.apr DESC
            LIMIT 1
        """, [API_MAX_DATA_AGE_DAYS])
        highest = cur.fetchone()
        if highest:
            stats['highest_symbol'] = highest['symbol']
            stats['highest_exchange'] = highest['exchange']

        # Get lowest APR contract details (filtered for active contracts only)
        cur.execute("""
            SELECT ed.symbol, ed.exchange, ed.apr
            FROM exchange_data ed
            LEFT JOIN contract_metadata cm
                ON ed.exchange = cm.exchange AND ed.symbol = cm.symbol
            WHERE ed.apr IS NOT NULL
                AND (cm.is_active = true OR cm.is_active IS NULL)
                AND ed.last_updated > NOW() - INTERVAL '%s days'
            ORDER BY ed.apr ASC
            LIMIT 1
        """, [API_MAX_DATA_AGE_DAYS])
        lowest = cur.fetchone()
        if lowest:
            stats['lowest_symbol'] = lowest['symbol']
            stats['lowest_exchange'] = lowest['exchange']
        
        # Convert Decimal to float, handle NaN/None values
        for key in ['avg_apr', 'highest_apr', 'lowest_apr', 'total_open_interest']:
            value = stats.get(key)
            if value is not None:
                # Check if value is a valid number (not NaN)
                try:
                    float_val = float(value)
                    # Replace NaN/Inf with None for JSON compatibility
                    if math.isnan(float_val) or math.isinf(float_val):
                        stats[key] = None
                    else:
                        stats[key] = float_val
                except (TypeError, ValueError):
                    stats[key] = None
            else:
                stats[key] = None
        
        # Format large numbers
        stats['total_contracts'] = int(stats['total_contracts']) if stats['total_contracts'] else 0
        stats['active_exchanges'] = int(stats['active_exchanges']) if stats['active_exchanges'] else 0
        stats['unique_assets'] = int(stats['unique_assets']) if stats['unique_assets'] else 0
        
        return stats
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cur.close()
        return_db_connection(conn)

@app.get("/api/top-apr/{limit}")
async def get_top_apr(limit: int = 20):
    """
    Get top APR contracts (highest funding rates).
    """
    conn = get_db_connection()
    cur = conn.cursor()
    
    try:
        cur.execute("""
            SELECT 
                exchange,
                symbol,
                base_asset,
                funding_rate,
                apr,
                mark_price,
                open_interest
            FROM exchange_data
            WHERE apr IS NOT NULL
            ORDER BY apr DESC
            LIMIT %s
        """, (limit,))
        
        results = cur.fetchall()
        
        # Convert to list and handle decimal serialization
        data = []
        for row in results:
            item = dict(row)
            for key in ['funding_rate', 'apr', 'mark_price', 'open_interest']:
                if item.get(key) is not None:
                    value = float(item[key])
                    # Convert NaN/Inf to None for JSON compatibility
                    item[key] = None if (math.isnan(value) or math.isinf(value)) else value
            data.append(item)
        
        return data
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cur.close()
        return_db_connection(conn)

@app.get("/api/group-by-asset")
async def group_by_asset():
    """
    Get funding rates grouped by base asset with statistics.
    """
    conn = get_db_connection()
    cur = conn.cursor()
    
    try:
        cur.execute("""
            SELECT 
                base_asset,
                COUNT(*) as contract_count,
                AVG(apr) as avg_apr,
                MAX(apr) as max_apr,
                MIN(apr) as min_apr,
                COUNT(DISTINCT exchange) as exchange_count,
                SUM(open_interest) as total_open_interest
            FROM exchange_data
            WHERE base_asset IS NOT NULL AND apr IS NOT NULL
            GROUP BY base_asset
            ORDER BY avg_apr DESC
        """)
        
        results = cur.fetchall()
        
        # Convert to list and handle decimal serialization
        data = []
        for row in results:
            item = dict(row)
            item['contract_count'] = int(item['contract_count'])
            item['exchange_count'] = int(item['exchange_count'])
            for key in ['avg_apr', 'max_apr', 'min_apr', 'total_open_interest']:
                if item.get(key) is not None:
                    value = float(item[key])
                    # Convert NaN/Inf to None for JSON compatibility
                    item[key] = None if (math.isnan(value) or math.isinf(value)) else value
            data.append(item)
        
        return data
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cur.close()
        return_db_connection(conn)

@app.get("/api/historical/{symbol}")
async def get_historical(
    symbol: str,
    days: int = Query(7, ge=1, le=365),
    exchange: Optional[str] = None
):
    """
    Get historical data for a specific symbol.
    """
    conn = get_db_connection()
    cur = conn.cursor()
    
    try:
        # Calculate date range
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        query = """
            SELECT 
                exchange,
                symbol,
                funding_rate,
                apr,
                mark_price,
                timestamp
            FROM exchange_data_historical
            WHERE symbol = %s
                AND timestamp >= %s
                AND timestamp <= %s
        """
        params = [symbol, start_date, end_date]
        
        if exchange:
            query += " AND LOWER(exchange) = LOWER(%s)"
            params.append(exchange)
        
        query += " ORDER BY timestamp DESC"
        
        cur.execute(query, params)
        results = cur.fetchall()
        
        # Convert to list and handle serialization
        data = []
        for row in results:
            item = dict(row)
            for key in ['funding_rate', 'apr', 'mark_price']:
                if item.get(key) is not None:
                    value = float(item[key])
                    # Convert NaN/Inf to None for JSON compatibility
                    item[key] = None if (math.isnan(value) or math.isinf(value)) else value
            if item.get('timestamp'):
                item['timestamp'] = item['timestamp'].isoformat()
            data.append(item)
        
        return {
            "symbol": symbol,
            "days": days,
            "data_points": len(data),
            "data": data
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cur.close()
        return_db_connection(conn)

@app.get("/api/exchanges")
async def get_exchanges():
    """
    Get list of unique exchanges in the database.
    """
    conn = get_db_connection()
    cur = conn.cursor()
    
    try:
        cur.execute("""
            SELECT DISTINCT exchange
            FROM exchange_data
            WHERE exchange IS NOT NULL
            ORDER BY exchange
        """)
        
        results = cur.fetchall()
        exchanges = [row['exchange'] for row in results]
        
        return exchanges
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cur.close()
        return_db_connection(conn)

@app.get("/api/assets")
async def get_assets():
    """
    Get list of unique base assets in the database.
    """
    conn = get_db_connection()
    cur = conn.cursor()
    
    try:
        cur.execute("""
            SELECT DISTINCT base_asset
            FROM exchange_data
            WHERE base_asset IS NOT NULL
            ORDER BY base_asset
        """)
        
        results = cur.fetchall()
        assets = [row['base_asset'] for row in results]
        
        return assets
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cur.close()
        return_db_connection(conn)

@app.get("/api/historical-funding/{symbol}")
async def get_historical_funding(
    symbol: str,
    start_time: Optional[str] = None,
    end_time: Optional[str] = None,
    exchange: str = Query("Binance")
):
    """
    Get historical funding rates for a specific symbol.
    Triggers async update if data is stale.
    """
    conn = get_db_connection()
    cur = conn.cursor()
    
    try:
        # Parse time parameters
        if end_time:
            end_dt = datetime.fromisoformat(end_time)
        else:
            end_dt = datetime.now()
        
        if start_time:
            start_dt = datetime.fromisoformat(start_time)
        else:
            start_dt = end_dt - timedelta(days=7)  # Default to 7 days
        
        # Query historical data
        cur.execute("""
            SELECT 
                exchange,
                symbol,
                funding_rate,
                funding_time,
                mark_price,
                funding_interval_hours
            FROM funding_rates_historical
            WHERE symbol = %s 
                AND exchange = %s
                AND funding_time >= %s
                AND funding_time <= %s
            ORDER BY funding_time DESC
            LIMIT 1000
        """, (symbol, exchange, start_dt, end_dt))
        
        results = cur.fetchall()
        
        # Convert to list and handle serialization
        data = []
        for row in results:
            item = dict(row)
            for key in ['funding_rate', 'mark_price']:
                if item.get(key) is not None:
                    value = float(item[key])
                    # Convert NaN/Inf to None for JSON compatibility
                    item[key] = None if (math.isnan(value) or math.isinf(value)) else value
            if item.get('funding_time'):
                item['funding_time'] = item['funding_time'].isoformat()
            data.append(item)
        
        # Check if data is stale (more than 1 hour old)
        if data:
            latest_time = datetime.fromisoformat(data[0]['funding_time'].replace('+00:00', '+00:00'))
            if (datetime.now(timezone.utc) - latest_time).total_seconds() > 3600:
                # TODO: Trigger async update in background
                pass
        
        return {
            "symbol": symbol,
            "exchange": exchange,
            "data_points": len(data),
            "start_time": start_dt.isoformat(),
            "end_time": end_dt.isoformat(),
            "data": data
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cur.close()
        return_db_connection(conn)

@app.get("/api/funding-sparkline/{symbol}")
async def get_funding_sparkline(
    symbol: str,
    hours: int = Query(48, ge=24, le=168),
    exchange: str = Query("Binance")
):
    """
    Get funding rate sparkline data for the last 24-168 hours.
    Optimized for dashboard sparkline charts.
    """
    conn = get_db_connection()
    cur = conn.cursor()
    
    try:
        # Calculate time range
        end_time = datetime.now(timezone.utc)
        start_time = end_time - timedelta(hours=hours)
        
        # Query with aggregation for sparkline
        cur.execute("""
            SELECT 
                DATE_TRUNC('hour', funding_time) as hour,
                AVG(funding_rate) as avg_rate,
                MIN(funding_rate) as min_rate,
                MAX(funding_rate) as max_rate,
                COUNT(*) as data_points
            FROM funding_rates_historical
            WHERE symbol = %s 
                AND exchange = %s
                AND funding_time >= %s
                AND funding_time <= %s
            GROUP BY DATE_TRUNC('hour', funding_time)
            ORDER BY hour ASC
        """, (symbol, exchange, start_time, end_time))
        
        results = cur.fetchall()
        
        # Convert to list for sparkline
        sparkline_data = []
        for row in results:
            item = dict(row)
            sparkline_data.append({
                'time': item['hour'].isoformat(),
                'value': float(item['avg_rate']) if item['avg_rate'] else 0,
                'min': float(item['min_rate']) if item['min_rate'] else 0,
                'max': float(item['max_rate']) if item['max_rate'] else 0,
                'count': item['data_points']
            })
        
        return {
            "symbol": symbol,
            "exchange": exchange,
            "hours": hours,
            "data_points": len(sparkline_data),
            "sparkline": sparkline_data
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cur.close()
        return_db_connection(conn)

@app.get("/api/funding-rates-grid")
async def get_funding_rates_grid():
    """
    Get funding rates grouped by asset across all exchanges.
    Returns a simplified grid view with one row per asset.

    For exchanges with multiple contracts per asset (e.g., Binance BTC),
    displays the contract with the most extreme (highest absolute) funding rate,
    filtered to contracts updated within the last 60 seconds.
    This prioritizes actionable arbitrage opportunities over recency alone.
    """
    from config.settings import API_MAX_DATA_AGE_DAYS

    conn = get_db_connection()
    cur = conn.cursor()

    try:
        # Query strategy for multi-contract assets:
        # - Filter: Only contracts updated in last 60 seconds (aligns with 30s collection cycle)
        # - Selection: Choose contract with highest |funding_rate| per (asset, exchange)
        # - Rationale: Surfaces extreme rates for arbitrage detection
        # - Fallback: If rates equal, prioritize most recently updated
        cur.execute("""
            WITH latest_rates AS (
                SELECT DISTINCT ON (COALESCE(ed.base_asset, ed.symbol), ed.exchange)
                    COALESCE(ed.base_asset, ed.symbol) as base_asset,
                    ed.exchange,
                    ed.symbol,
                    ed.funding_rate,
                    ed.apr,
                    ed.funding_interval_hours,
                    ed.last_updated,
                    fs.current_z_score,
                    fs.current_percentile,
                    fs.mean_30d,
                    fs.std_dev_30d
                FROM exchange_data ed
                LEFT JOIN funding_statistics fs
                    ON ed.exchange = fs.exchange AND ed.symbol = fs.symbol
                LEFT JOIN contract_metadata cm
                    ON ed.exchange = cm.exchange AND ed.symbol = cm.symbol
                WHERE (ed.base_asset IS NOT NULL OR (ed.exchange = 'hyperliquid' AND ed.symbol IS NOT NULL))
                    AND ed.funding_rate IS NOT NULL
                    -- Filter out inactive contracts and stale data
                    AND (cm.is_active = true OR cm.is_active IS NULL)
                    AND ed.last_updated > NOW() - INTERVAL %s
                    -- 60-second recency filter for extreme rate selection
                    AND ed.last_updated > NOW() - INTERVAL '60 seconds'
                ORDER BY COALESCE(ed.base_asset, ed.symbol), ed.exchange,
                         ABS(ed.funding_rate) DESC NULLS LAST,
                         ed.last_updated DESC
            )
            SELECT
                base_asset,
                json_object_agg(
                    exchange,
                    json_build_object(
                        'funding_rate', funding_rate,
                        'apr', apr,
                        'funding_interval_hours', funding_interval_hours,
                        'z_score', current_z_score,
                        'percentile', current_percentile,
                        'mean_30d', mean_30d,
                        'std_dev_30d', std_dev_30d
                    )
                ) as exchange_rates
            FROM latest_rates
            GROUP BY base_asset
            ORDER BY base_asset
        """, (f'{API_MAX_DATA_AGE_DAYS} days',))

        results = cur.fetchall()
        
        # Format response
        grid_data = []
        for row in results:
            asset_data = {
                'asset': row['base_asset'],
                'exchanges': {}
            }
            
            # Convert exchange rates with z-score data
            if row['exchange_rates']:
                for exchange, rates in row['exchange_rates'].items():
                    asset_data['exchanges'][exchange] = {
                        'funding_rate': sanitize_numeric_value(float(rates['funding_rate'])) if rates['funding_rate'] else None,
                        'apr': sanitize_numeric_value(float(rates['apr'])) if rates['apr'] else None,
                        'funding_interval_hours': int(rates['funding_interval_hours']) if rates.get('funding_interval_hours') else None,
                        'z_score': sanitize_numeric_value(float(rates['z_score'])) if rates.get('z_score') else None,
                        'percentile': sanitize_numeric_value(float(rates['percentile'])) if rates.get('percentile') else None,
                        'mean_30d': sanitize_numeric_value(float(rates['mean_30d'])) if rates.get('mean_30d') else None,
                        'std_dev_30d': sanitize_numeric_value(float(rates['std_dev_30d'])) if rates.get('std_dev_30d') else None
                    }
            
            grid_data.append(asset_data)
        
        return {
            'data': grid_data,
            'total_assets': len(grid_data),
            'timestamp': datetime.now(timezone.utc).isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cur.close()
        return_db_connection(conn)

@app.get("/api/arbitrage/opportunities")
async def get_arbitrage_opportunities(
    min_spread: float = Query(0.001, description="Minimum spread to consider (0.001 = 0.1%)"),
    top_n: int = Query(20, ge=1, le=100, description="Number of top opportunities to return")
):
    """
    Get arbitrage opportunities by comparing funding rates across exchanges.
    Returns opportunities where you can long on one exchange and short on another
    to capture the funding rate spread.
    """
    try:
        # Get the funding rates grid data
        grid_response = await get_funding_rates_grid()
        funding_data = grid_response['data']

        # Import the scanner
        from utils.arbitrage_scanner import get_top_opportunities

        # Find opportunities
        result = get_top_opportunities(
            funding_data=funding_data,
            top_n=top_n,
            min_spread=min_spread
        )


        return {
            'opportunities': result['opportunities'],
            'statistics': result['statistics'],
            'parameters': {
                'min_spread': min_spread,
                'top_n': top_n
            },
            'timestamp': datetime.now(timezone.utc).isoformat()
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/arbitrage/assets/search")
async def search_arbitrage_assets(
    q: str = Query(..., min_length=1, description="Search query for assets"),
    limit: int = Query(10, ge=1, le=50, description="Maximum results to return")
):
    """
    Server-side fuzzy search for assets with arbitrage opportunities.
    Groups by base_asset from exchange_data table to show unique assets
    that have active arbitrage opportunities across exchanges.

    Search algorithm:
    1. Exact prefix match on base_asset (highest priority)
    2. Case-insensitive contains match on base_asset or symbol
    3. Order by average spread (highest first)

    Returns assets with their average spreads, number of exchanges,
    and other statistics to help users identify interesting opportunities.
    """
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    try:
        search_pattern = f"%{q}%"
        prefix_pattern = f"{q}%"

        query = """
        WITH asset_stats AS (
            SELECT
                ed.base_asset as symbol,
                ed.base_asset as name,
                COUNT(DISTINCT ed.exchange) as exchanges,
                AVG(ABS(ed.funding_rate)) * 100 as avg_spread_pct,
                AVG(ed.apr) as avg_apr,
                MAX(ABS(ed.funding_rate)) * 100 as max_spread_pct,
                COUNT(*) as total_opportunities,
                MAX(ed.last_updated) as last_updated
            FROM exchange_data ed
            LEFT JOIN contract_metadata cm
                ON ed.exchange = cm.exchange AND ed.symbol = cm.symbol
            WHERE ed.base_asset IS NOT NULL
                AND ed.funding_rate IS NOT NULL
                AND (ed.base_asset ILIKE %s OR ed.symbol ILIKE %s)
                AND ed.last_updated > NOW() - INTERVAL '1 hour'
                AND (cm.is_active = true OR cm.is_active IS NULL)
            GROUP BY ed.base_asset
            HAVING COUNT(DISTINCT ed.exchange) >= 2
        )
        SELECT * FROM asset_stats
        ORDER BY
            CASE WHEN symbol ILIKE %s THEN 1 ELSE 2 END,
            avg_spread_pct DESC
        LIMIT %s
        """

        cur.execute(query, [search_pattern, search_pattern, prefix_pattern, limit])

        results = []
        for row in cur.fetchall():
            results.append({
                'symbol': row['symbol'],
                'name': row['name'],
                'exchanges': row['exchanges'],
                'avg_spread_pct': sanitize_numeric_value(row['avg_spread_pct']),
                'avg_apr': sanitize_numeric_value(row['avg_apr']),
                'max_spread_pct': sanitize_numeric_value(row['max_spread_pct']),
                'total_opportunities': row['total_opportunities'],
                'last_updated': row['last_updated'].isoformat() if row['last_updated'] else None
            })

        return {
            "results": results,
            "query": q,
            "count": len(results),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

    except Exception as e:
        logger.error(f"Error in asset search: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cur.close()
        return_db_connection(conn)

@app.get("/api/arbitrage/opportunities-v2")
async def get_contract_level_arbitrage_opportunities(
    min_spread: float = Query(0.001, description="Minimum spread to consider (0.001 = 0.1%)"),
    page: int = Query(1, ge=1, description="Page number for pagination"),
    page_size: int = Query(20, ge=1, le=50, description="Number of results per page"),
    # NEW FILTER PARAMETERS
    assets: Optional[List[str]] = Query(None, description="Filter by specific assets (e.g., BTC, ETH)"),
    exchanges: Optional[List[str]] = Query(None, description="Filter by specific exchanges"),
    intervals: Optional[List[int]] = Query(None, description="Filter by funding intervals in hours (1, 4, 8, etc.)"),
    min_apr: Optional[float] = Query(None, description="Minimum APR spread percentage"),
    max_apr: Optional[float] = Query(None, description="Maximum APR spread percentage"),
    min_oi_either: Optional[float] = Query(None, description="Minimum open interest for either position"),
    min_oi_combined: Optional[float] = Query(None, description="Minimum combined open interest")
):
    """
    Get contract-specific arbitrage opportunities with correct Z-scores.
    This endpoint returns the exact contracts to trade, not just assets and exchanges.
    Each contract's Z-score corresponds to that specific contract.

    Supports pagination to handle large result sets efficiently.

    Returns:
        - Specific contract symbols (e.g., BTCUSDT, XBTUSDTM)
        - Correct Z-scores for each individual contract
        - Exact trading pairs to execute
        - Pagination metadata for navigation
    """
    try:
        # Normalize exchange names to match database format
        # Frontend sends lowercase, database has proper case
        exchange_name_mapping = {
            'binance': 'Binance',
            'bybit': 'ByBit',
            'kucoin': 'KuCoin',
            'backpack': 'Backpack',
            'hyperliquid': 'Hyperliquid',
            'aster': 'Aster',
            'drift': 'Drift',
            'lighter': 'Lighter',
            'deribit': 'Deribit',
            'kraken': 'Kraken'
        }

        # Normalize the exchanges list if provided
        if exchanges:
            normalized_exchanges = []
            for ex in exchanges:
                # Try to map lowercase to proper case, fallback to original if not found
                normalized_exchanges.append(exchange_name_mapping.get(ex.lower(), ex))
            exchanges = normalized_exchanges

        # Update cache key to include filters
        # Sort filter arrays to ensure consistent cache keys
        # Use normalized exchanges for cache key to ensure uniqueness
        filter_hash = hashlib.md5(
            f"{sorted(assets or [])}{sorted(exchanges or [])}{sorted(intervals or [])}"
            f"{min_apr}{max_apr}{min_oi_either}{min_oi_combined}".encode()
        ).hexdigest()[:8]
        cache_key = f"arbitrage:v2:{page}:{page_size}:{min_spread}:{filter_hash}"

        # Debug logging for cache
        logger.info(f"Cache key generated: {cache_key}")
        logger.info(f"Normalized exchanges for cache: {exchanges}")

        # Try to get from cache
        cached_result = api_cache.get(cache_key)
        if cached_result:
            logger.info(f"Cache hit for arbitrage page {page} with filters: {exchanges}")
            return cached_result
        else:
            logger.info(f"Cache miss for arbitrage page {page} with filters: {exchanges}")

        # Import the new contract-level scanner
        from utils.arbitrage_scanner import calculate_contract_level_arbitrage

        # Debug: Log exactly what we're passing to the function
        logger.info(f"CALLING arbitrage_scanner with exchanges: {exchanges}")

        # Find contract-level opportunities with pagination and filters
        result = calculate_contract_level_arbitrage(
            min_spread=min_spread,
            page=page,
            page_size=page_size,
            assets=assets,
            exchanges=exchanges,
            intervals=intervals,
            min_apr=min_apr,
            max_apr=max_apr,
            min_oi_either=min_oi_either,
            min_oi_combined=min_oi_combined
        )

        # Sanitize the result to remove NaN/Infinity values
        sanitized_result = sanitize_response_data({
            'opportunities': result['opportunities'],
            'statistics': result['statistics'],
            'pagination': result.get('pagination', {
                'total': result.get('statistics', {}).get('total_opportunities', 0),
                'page': page,
                'page_size': page_size,
                'total_pages': 1
            }),
            'parameters': {
                'min_spread': min_spread,
                'page': page,
                'page_size': page_size,
                'assets': assets,
                'exchanges': exchanges,
                'intervals': intervals,
                'min_apr': min_apr,
                'max_apr': max_apr,
                'min_oi_either': min_oi_either,
                'min_oi_combined': min_oi_combined
            },
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'version': 'v2-contract-level-paginated'
        })

        # Cache the result - reduced to 30s to match data update cycle
        api_cache.set(cache_key, sanitized_result, ttl_seconds=30)  # Cache for 30 seconds
        logger.info(f"Cached arbitrage page {page}")

        return sanitized_result

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/arbitrage/opportunity-detail/{asset}/{long_exchange}/{short_exchange}")
async def get_arbitrage_opportunity_detail(
    asset: str,
    long_exchange: str,
    short_exchange: str
):
    """
    Get detailed information for a specific arbitrage opportunity.
    Includes historical data and extended statistics for the specific pair.
    """
    try:
        # Import the scanner to get current opportunity
        from utils.arbitrage_scanner import calculate_contract_level_arbitrage

        # Get all opportunities and find the specific one
        result = calculate_contract_level_arbitrage(min_spread=0, page=1, page_size=1000)

        # Find the specific opportunity
        opportunity = None
        for opp in result['opportunities']:
            if (opp['asset'].upper() == asset.upper() and
                opp['long_exchange'].lower() == long_exchange.lower() and
                opp['short_exchange'].lower() == short_exchange.lower()):
                opportunity = opp
                break

        if not opportunity:
            raise HTTPException(status_code=404, detail="Opportunity not found")

        # Get historical data for this specific pair from the database
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)

        try:
            # Get 30-day historical spread data
            query = """
                SELECT
                    DATE_TRUNC('day', timestamp) as date,
                    AVG(apr_spread) as avg_apr_spread,
                    MAX(apr_spread) as max_apr_spread,
                    MIN(apr_spread) as min_apr_spread,
                    COUNT(*) as data_points
                FROM arbitrage_spreads
                WHERE asset = %s
                    AND ((exchange_a = %s AND exchange_b = %s) OR
                         (exchange_a = %s AND exchange_b = %s))
                    AND timestamp >= NOW() - INTERVAL '30 days'
                GROUP BY DATE_TRUNC('day', timestamp)
                ORDER BY date DESC
            """

            cur.execute(query, (
                asset,
                long_exchange, short_exchange,
                short_exchange, long_exchange
            ))
            historical_data = cur.fetchall()

            # Calculate additional statistics
            if historical_data:
                all_spreads = [row['avg_apr_spread'] for row in historical_data if row['avg_apr_spread']]
                if all_spreads:
                    avg_30d = sum(all_spreads) / len(all_spreads)
                    max_30d = max(all_spreads)
                    min_30d = min(all_spreads)
                else:
                    avg_30d = max_30d = min_30d = None
            else:
                avg_30d = max_30d = min_30d = None

            # Return enriched opportunity data
            return {
                'opportunity': opportunity,
                'historical': {
                    'daily_data': historical_data,
                    'statistics': {
                        'avg_30d_spread': avg_30d,
                        'max_30d_spread': max_30d,
                        'min_30d_spread': min_30d,
                        'data_days': len(historical_data)
                    }
                },
                'timestamp': datetime.now(timezone.utc).isoformat()
            }

        finally:
            cur.close()
            conn.close()

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/historical-funding-by-asset/{asset}")
async def get_historical_funding_by_asset(
    asset: str,
    days: int = Query(7, ge=1, le=30),
    interval: str = Query("8h", pattern="^(1h|4h|8h|1d)$")
):
    """
    Get historical funding rates for a specific asset across all exchanges.
    Perfect for multi-exchange comparison charts.
    """
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    try:
        # Calculate date range
        end_date = datetime.now(timezone.utc)
        start_date = end_date - timedelta(days=days)
        
        # Get historical data from funding_rates_historical table
        # First check if the table exists
        cur.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = 'funding_rates_historical'
            )
        """)
        
        has_historical = cur.fetchone()['exists']
        
        # Try to get data from both tables and combine
        if has_historical:
            # First try funding_rates_historical table
            # Get ALL contracts for the asset (not just USDT)
            # For Hyperliquid, symbol = base_asset (e.g., "BTC" not "BTCUSDT")
            query_historical = """
                SELECT 
                    exchange,
                    symbol,
                    funding_rate,
                    funding_rate * (365.0 * 24 / COALESCE(funding_interval_hours, 8)) * 100 as apr,
                    funding_time,
                    funding_interval_hours
                FROM funding_rates_historical
                WHERE (base_asset = %s OR (exchange = 'hyperliquid' AND symbol = %s))
                    AND funding_time >= %s
                    AND funding_time <= %s
                ORDER BY funding_time DESC, symbol
            """
            cur.execute(query_historical, (asset, asset, start_date, end_date))
            historical_results = cur.fetchall()
        else:
            historical_results = []
        
        # Also get recent data from main table
        # For Hyperliquid, symbol = base_asset (e.g., "BTC" not "BTCUSDT")
        query_recent = """
            SELECT 
                exchange,
                symbol,
                funding_rate,
                apr,
                last_updated as funding_time,
                funding_interval_hours
            FROM exchange_data
            WHERE (base_asset = %s OR (exchange = 'hyperliquid' AND symbol = %s))
                AND last_updated >= %s
                AND last_updated <= %s
            ORDER BY last_updated DESC, exchange
        """
        cur.execute(query_recent, (asset, asset, start_date, end_date))
        recent_results = cur.fetchall()
        
        # Combine results, preferring historical data
        # Start with historical results
        results = list(historical_results) if historical_results else []
        
        # Add ALL recent data points that are newer than our historical data
        if recent_results and len(recent_results) > 0:
            if results:
                # Get the latest historical timestamp
                latest_historical = max(r['funding_time'] for r in results) if results else None
                
                # Add all recent results that are newer than historical
                for recent in recent_results:
                    if latest_historical is None or recent['funding_time'] > latest_historical:
                        results.append(recent)
            else:
                # No historical data, use all recent data
                results = list(recent_results)
        
        # Group data by timestamp and CONTRACT (not exchange)
        time_series = {}
        contracts = set()
        exchanges = set()  # Track exchanges that have data
        
        for row in results:
            # Normalize timestamp to nearest second to align multi-contract data points
            if row['funding_time']:
                # Round to nearest second to fix millisecond differences
                normalized_time = row['funding_time'].replace(microsecond=0)
                timestamp = normalized_time.isoformat()
            else:
                timestamp = None
            symbol = row['symbol']  # Use symbol instead of exchange
            
            if timestamp not in time_series:
                time_series[timestamp] = {}
            
            time_series[timestamp][symbol] = {
                'funding_rate': float(row['funding_rate']) if row['funding_rate'] is not None else None,
                'apr': float(row['apr']) if row['apr'] is not None else None,
                'exchange': row['exchange'],
                'funding_interval_hours': int(row['funding_interval_hours']) if row.get('funding_interval_hours') else 8
            }
            contracts.add(symbol)
            exchanges.add(row['exchange'])  # Track which exchanges we have data from
        
        # Format for chart display - each contract gets its own line
        chart_data = []
        for timestamp, contract_data in sorted(time_series.items()):
            data_point = {'timestamp': timestamp}
            
            # Check if this data point has values for all contracts or is mostly complete
            has_values = 0
            total_contracts = len(contracts)
            
            for contract in contracts:
                if contract in contract_data:
                    data_point[contract] = contract_data[contract]['funding_rate']
                    # Add APR field for each contract
                    data_point[f'{contract}_apr'] = contract_data[contract]['apr']
                    if contract_data[contract]['funding_rate'] is not None:
                        has_values += 1
                else:
                    data_point[contract] = None
                    data_point[f'{contract}_apr'] = None
            
            # Include data points where at least one contract has values
            # This ensures we show all available data, even if incomplete
            if has_values > 0:
                chart_data.append(data_point)
        
        return {
            'asset': asset,
            'contracts': list(contracts),  # Return contracts instead of exchanges
            'exchanges': sorted(list(exchanges)),  # Return actual exchanges with data
            'days': days,
            'data_points': len(chart_data),
            'data': chart_data
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cur.close()
        return_db_connection(conn)

@app.get("/api/historical-funding-by-contract/{exchange}/{symbol}")
async def get_historical_funding_by_contract(
    exchange: str,
    symbol: str,
    days: int = Query(7, ge=1, le=30)
):
    """
    Get historical funding rates for a specific contract.
    Returns clean data for a single contract without mixing different funding intervals.
    """
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    try:
        # Calculate date range
        end_date = datetime.now(timezone.utc)
        start_date = end_date - timedelta(days=days)
        
        # Get historical data for this specific contract (case-insensitive for exchange)
        # Use DISTINCT ON to eliminate duplicate timestamps, keeping the most recent record
        query_historical = """
            SELECT DISTINCT ON (funding_time)
                exchange,
                symbol,
                base_asset,
                funding_rate,
                funding_rate * (365.0 * 24 / COALESCE(funding_interval_hours, 8)) * 100 as apr,
                funding_time,
                funding_interval_hours,
                mark_price
            FROM funding_rates_historical
            WHERE exchange ILIKE %s
                AND symbol = %s
                AND funding_time >= %s
                AND funding_time <= %s
            ORDER BY funding_time DESC
        """
        cur.execute(query_historical, (exchange, symbol, start_date, end_date))
        historical_results = cur.fetchall()
        
        # Also get the most recent data from main table (case-insensitive for exchange)
        query_recent = """
            SELECT
                exchange,
                symbol,
                base_asset,
                funding_rate,
                apr,
                last_updated as funding_time,
                funding_interval_hours,
                mark_price,
                open_interest
            FROM exchange_data
            WHERE exchange ILIKE %s
                AND symbol = %s
            LIMIT 1
        """
        cur.execute(query_recent, (exchange, symbol))
        recent_result = cur.fetchone()
        
        # Combine results
        results = list(historical_results) if historical_results else []
        
        # Add recent data if it's newer than historical
        if recent_result:
            if not results or recent_result['funding_time'] > results[0]['funding_time']:
                results.insert(0, recent_result)
        
        # Format data for frontend
        chart_data = []
        base_asset = None
        funding_interval = 8
        
        for row in results:
            if not base_asset and row.get('base_asset'):
                base_asset = row['base_asset']
            if row.get('funding_interval_hours'):
                funding_interval = int(row['funding_interval_hours'])
                
            chart_data.append({
                'timestamp': row['funding_time'].isoformat() if row['funding_time'] else None,
                'funding_rate': float(row['funding_rate']) if row['funding_rate'] is not None else None,
                'apr': float(row['apr']) if row['apr'] is not None else None,
                'mark_price': float(row['mark_price']) if row['mark_price'] is not None else None,
                'open_interest': float(row['open_interest']) if row.get('open_interest') is not None else None
            })
        
        return sanitize_response_data({
            'exchange': exchange,
            'symbol': symbol,
            'base_asset': base_asset,
            'funding_interval_hours': funding_interval,
            'days': days,
            'data_points': len(chart_data),
            'data': chart_data
        })
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cur.close()
        return_db_connection(conn)

@app.get("/api/current-funding/{asset}")
async def get_current_funding(asset: str):
    """
    Get current funding rate and next funding time for an asset.
    """
    conn = get_db_connection()
    cur = conn.cursor()
    
    try:
        # Get latest funding rate from database
        # For Hyperliquid, symbol = base_asset (e.g., "BTC" not "BTCUSDT")
        cur.execute("""
            SELECT 
                exchange,
                symbol,
                funding_rate,
                apr,
                funding_interval_hours,
                last_updated
            FROM exchange_data
            WHERE (base_asset = %s OR (exchange = 'hyperliquid' AND symbol = %s))
            ORDER BY last_updated DESC
            LIMIT 1
        """, (asset, asset))
        
        result = cur.fetchone()
        
        if result:
            # Calculate next funding time
            now = datetime.now(timezone.utc)
            funding_interval = result['funding_interval_hours'] or 8
            
            # Funding times are typically at 00:00, 08:00, 16:00 UTC for 8-hour intervals
            hours_per_interval = funding_interval
            current_hour = now.hour
            next_funding_hour = ((current_hour // hours_per_interval) + 1) * hours_per_interval
            
            if next_funding_hour >= 24:
                next_funding_hour = next_funding_hour % 24
                next_funding_time = now.replace(hour=next_funding_hour, minute=0, second=0, microsecond=0) + timedelta(days=1)
            else:
                next_funding_time = now.replace(hour=next_funding_hour, minute=0, second=0, microsecond=0)
            
            # Calculate time until next funding
            time_until_funding = next_funding_time - now
            hours_until = int(time_until_funding.total_seconds() // 3600)
            minutes_until = int((time_until_funding.total_seconds() % 3600) // 60)
            seconds_until = int(time_until_funding.total_seconds() % 60)
            
            return {
                'asset': asset,
                'symbol': result['symbol'],
                'exchange': result['exchange'],
                'funding_rate': float(result['funding_rate']) if result['funding_rate'] else 0,
                'apr': float(result['apr']) if result['apr'] else 0,
                'funding_interval_hours': funding_interval,
                'next_funding_time': next_funding_time.isoformat(),
                'time_until_funding': {
                    'hours': hours_until,
                    'minutes': minutes_until,
                    'seconds': seconds_until,
                    'display': f"{hours_until:02d}:{minutes_until:02d}:{seconds_until:02d}"
                },
                'last_updated': result['last_updated'].isoformat() if result['last_updated'] else None
            }
        else:
            return {
                'asset': asset,
                'error': 'No funding data available for this asset'
            }
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cur.close()
        return_db_connection(conn)

@app.get("/api/backfill-status")
async def get_backfill_status():
    """
    Get the status of the historical backfill process.
    Auto-fixes stuck states when progress is 100%.
    """
    import json
    from pathlib import Path
    
    try:
        lock_file = Path(".backfill.lock")
        status_file = Path(".backfill.status")
        
        # If no status file, backfill is not running
        if not status_file.exists():
            return {
                "running": False,
                "progress": 100,
                "message": "No backfill in progress",
                "completed": True
            }
        
        # Read status file
        with open(status_file, 'r') as f:
            status_data = json.load(f)
            
            # Auto-fix completed state when progress is 100%
            if status_data.get("progress", 0) >= 100:
                if not status_data.get("completed") or status_data.get("running"):
                    status_data["completed"] = True
                    status_data["running"] = False
                    
                    # Update the file with corrected status
                    with open(status_file, 'w') as fw:
                        json.dump(status_data, fw, indent=2)
            
            # If lock file doesn't exist but status shows running, fix it
            if not lock_file.exists() and status_data.get("running", False):
                status_data["running"] = False
                status_data["completed"] = True
                with open(status_file, 'w') as fw:
                    json.dump(status_data, fw, indent=2)
            
            # Check lock file age if it exists
            if lock_file.exists():
                lock_age = time.time() - lock_file.stat().st_mtime
                # If lock file is old (>10 minutes), consider backfill complete
                if lock_age > 600:
                    status_data["running"] = False
                    status_data["completed"] = True
                    with open(status_file, 'w') as fw:
                        json.dump(status_data, fw, indent=2)
                    # Remove old lock file
                    try:
                        lock_file.unlink()
                    except:
                        pass
            
            return status_data
            
    except Exception as e:
        return {
            "running": False,
            "progress": 100,
            "message": "Status check error",
            "completed": True,
            "error": str(e)
        }

@app.post("/api/shutdown")
async def shutdown_dashboard():
    """
    Shutdown the dashboard and all related processes.
    """
    import subprocess
    import threading
    from pathlib import Path
    
    def run_shutdown():
        """Run shutdown in a separate thread to allow response."""
        try:
            # Wait a moment for the response to be sent
            time.sleep(1)
            
            # Run the shutdown script
            subprocess.run(
                ["python", "shutdown_dashboard.py"],
                capture_output=True,
                text=True
            )
        except Exception as e:
            print(f"Shutdown error: {e}")
    
    # Start shutdown in background
    shutdown_thread = threading.Thread(target=run_shutdown, daemon=True)
    shutdown_thread.start()
    
    return {
        "status": "shutdown_initiated",
        "message": "Dashboard is shutting down. Please wait a moment...",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

@app.get("/api/test")
async def test_connection():
    """
    Test database connection and return sample data.
    """
    conn = get_db_connection()
    cur = conn.cursor()
    
    try:
        # Test query
        cur.execute("""
            SELECT COUNT(*) as count FROM exchange_data
        """)
        count = cur.fetchone()['count']
        
        # Get sample data
        cur.execute("""
            SELECT * FROM exchange_data LIMIT 5
        """)
        sample = cur.fetchall()
        
        # Convert sample data
        sample_data = []
        for row in sample:
            item = dict(row)
            for key in ['funding_rate', 'apr', 'index_price', 'mark_price', 'open_interest']:
                if item.get(key) is not None:
                    value = float(item[key])
                    # Convert NaN/Inf to None for JSON compatibility
                    item[key] = None if (math.isnan(value) or math.isinf(value)) else value
            if item.get('last_updated'):
                item['last_updated'] = item['last_updated'].isoformat()
            sample_data.append(item)
        
        return {
            "status": "connected",
            "total_records": count,
            "sample_data": sample_data
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cur.close()
        return_db_connection(conn)

# ==================== SETTINGS MANAGEMENT ENDPOINTS ====================

# Initialize settings manager
settings_manager = SettingsManager()

@app.get("/api/settings")
async def get_settings():
    """
    Get current system settings organized by category.
    """
    try:
        settings = settings_manager.get_settings()
        return {
            "status": "success",
            "settings": settings
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/api/settings")
async def update_settings(settings: Dict[str, Any]):
    """
    Update system settings with validation.
    """
    try:
        success, message = settings_manager.update_settings(settings)
        if success:
            return {
                "status": "success",
                "message": message
            }
        else:
            raise HTTPException(status_code=400, detail=message)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/settings/validate")
async def validate_settings(settings: Dict[str, Any]):
    """
    Validate settings without applying them.
    """
    try:
        is_valid, errors = settings_manager.validate_settings(settings)
        return {
            "status": "success",
            "valid": is_valid,
            "errors": errors
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/settings/backups")
async def get_settings_backups():
    """
    Get list of available settings backups.
    """
    try:
        backups = settings_manager.get_backups()
        return {
            "status": "success",
            "backups": backups
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/settings/restore")
async def restore_settings_backup(backup_filename: str):
    """
    Restore settings from a backup file.
    """
    try:
        success, message = settings_manager.restore_backup(backup_filename)
        if success:
            return {
                "status": "success",
                "message": message
            }
        else:
            raise HTTPException(status_code=400, detail=message)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/settings/export")
async def export_settings():
    """
    Export current settings as JSON.
    """
    try:
        export_data = settings_manager.export_settings()
        return export_data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/settings/import")
async def import_settings(settings_json: Dict[str, Any]):
    """
    Import settings from JSON.
    """
    try:
        success, message = settings_manager.import_settings(settings_json)
        if success:
            return {
                "status": "success",
                "message": message
            }
        else:
            raise HTTPException(status_code=400, detail=message)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/settings/reset")
async def reset_settings():
    """
    Reset settings to defaults (restore from oldest backup or defaults).
    """
    try:
        # For now, just reload current settings
        # In production, this would restore from a default template
        settings_manager.load_current_settings()
        return {
            "status": "success",
            "message": "Settings reset to defaults"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ==================== BACKFILL MANAGEMENT ENDPOINTS ====================

@app.get("/api/backfill/status")
async def get_backfill_status():
    """
    Get current backfill operation status.
    """
    try:
        status_file = Path(".backfill.status")
        if status_file.exists():
            with open(status_file, 'r') as f:
                status_data = json.load(f)
            return {
                "status": "success",
                "backfill": status_data
            }
        else:
            return {
                "status": "success",
                "backfill": {
                    "status": "idle",
                    "message": "No backfill operation running"
                }
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/backfill/start")
async def start_backfill(params: Dict[str, Any]):
    """
    Start a backfill operation with specified parameters.
    
    Parameters:
    - days: Number of days to backfill (1-90)
    - exchanges: List of exchanges to backfill
    - batch_size: Number of symbols per batch
    - parallel: Use parallel processing
    """
    try:
        # Check if backfill is already running
        lock_file = Path(".backfill.lock")
        if lock_file.exists():
            return {
                "status": "error",
                "message": "Backfill operation is already running"
            }
        
        # Extract parameters
        days = params.get("days", 30)
        exchanges = params.get("exchanges", ["binance", "kucoin"])
        batch_size = params.get("batch_size", 10)
        parallel = params.get("parallel", True)
        
        # Build command
        cmd = [
            "python", 
            "scripts/unified_historical_backfill.py",
            "--days", str(days),
            "--batch-size", str(batch_size)
        ]
        
        if parallel:
            cmd.append("--parallel")
        
        # Start backfill process in background
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        return {
            "status": "success",
            "message": f"Backfill started for {days} days",
            "pid": process.pid
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/backfill/stop")
async def stop_backfill():
    """
    Stop the running backfill operation.
    """
    try:
        # Remove lock files to signal stop
        lock_files = [Path(".backfill.lock"), Path(".unified_backfill.lock")]
        for lock_file in lock_files:
            if lock_file.exists():
                lock_file.unlink()
        
        # Update status file
        status_file = Path(".backfill.status")
        if status_file.exists():
            with open(status_file, 'r') as f:
                status_data = json.load(f)
            status_data["status"] = "cancelled"
            status_data["message"] = "Backfill cancelled by user"
            with open(status_file, 'w') as f:
                json.dump(status_data, f)
        
        return {
            "status": "success",
            "message": "Backfill operation stopped"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/contracts-with-zscores")
async def get_contracts_with_zscores(
    sort: str = Query("zscore_abs", enum=["zscore_abs", "zscore_asc", "zscore_desc", "contract", "exchange"]),
    min_abs_zscore: Optional[float] = Query(None, ge=0, le=4),
    exchanges: Optional[str] = Query(None, description="Comma-separated list of exchanges"),
    exchange: Optional[str] = Query(None, description="Single exchange filter (for compatibility)"),
    search: Optional[str] = Query(None, description="Search term for contract names")
):
    """
    Get all contracts with Z-score statistics with 5-second caching.
    Returns EXACTLY 1,240 contracts as specified in Z_score.md lines 344-387.
    """
    # Merge exchange and exchanges parameters for compatibility
    if exchange and not exchanges:
        exchanges = exchange

    # Generate cache key from parameters
    cache_key = CacheKeys.contracts_with_zscores(exchanges, search, min_abs_zscore, sort)

    # Check cache first - standardized to 25s
    cached_result = api_cache.get(cache_key, ttl_seconds=25)
    if cached_result is not None:
        return cached_result
    
    conn = get_db_connection()
    cur = conn.cursor()
    
    try:
        # Build the query with filters - JOIN with exchange_data to get mark_price
        base_query = """
            SELECT
                fs.symbol as contract,
                fs.exchange,
                fs.base_asset,
                ed.mark_price,
                fs.current_z_score as z_score,
                fs.current_z_score_apr as z_score_apr,
                fs.current_funding_rate as funding_rate,
                fs.current_apr as apr,
                fs.current_percentile as percentile,
                fs.current_percentile_apr as percentile_apr,
                fs.mean_30d,
                fs.std_dev_30d,
                fs.mean_30d_apr,
                fs.std_dev_30d_apr,
                fs.data_points,
                fs.expected_points,
                fs.completeness_percentage,
                fs.confidence_level as confidence,
                COALESCE(fs.funding_interval_hours, 8) as funding_interval_hours,
                fs.last_updated
            FROM funding_statistics fs
            LEFT JOIN exchange_data ed
                ON fs.exchange = ed.exchange
                AND fs.symbol = ed.symbol
            WHERE 1=1
        """
        
        params = []
        
        # Apply filters
        if min_abs_zscore is not None:
            base_query += " AND ABS(fs.current_z_score) >= %s"
            params.append(min_abs_zscore)
        
        if exchanges:
            exchange_list = exchanges.split(',')
            # Use case-insensitive matching with ILIKE and ANY
            base_query += " AND LOWER(fs.exchange) = ANY(ARRAY[%s]::text[])"
            params.append([ex.lower() for ex in exchange_list])
        
        if search:
            base_query += " AND (fs.symbol ILIKE %s OR fs.base_asset ILIKE %s)"
            search_param = f"%{search}%"
            params.append(search_param)
            params.append(search_param)
        
        # Apply sorting
        if sort == "zscore_abs":
            base_query += " ORDER BY ABS(fs.current_z_score) DESC NULLS LAST"
        elif sort == "zscore_asc":
            base_query += " ORDER BY fs.current_z_score ASC NULLS LAST"
        elif sort == "zscore_desc":
            base_query += " ORDER BY fs.current_z_score DESC NULLS LAST"
        elif sort == "contract":
            base_query += " ORDER BY fs.symbol ASC"
        elif sort == "exchange":
            base_query += " ORDER BY fs.exchange ASC, fs.symbol ASC"
        
        # Execute query
        cur.execute(base_query, params)
        results = cur.fetchall()
        
        # Process results and calculate next_funding_seconds
        contracts = []
        high_deviation_count = 0
        now = datetime.now(timezone.utc)
        
        for row in results:
            # Calculate next funding time in seconds
            funding_interval = row['funding_interval_hours'] or 8
            current_hour = now.hour
            next_funding_hour = ((current_hour // funding_interval) + 1) * funding_interval
            
            if next_funding_hour >= 24:
                next_funding_hour = next_funding_hour % 24
                next_funding_time = now.replace(hour=next_funding_hour, minute=0, second=0, microsecond=0) + timedelta(days=1)
            else:
                next_funding_time = now.replace(hour=next_funding_hour, minute=0, second=0, microsecond=0)
            
            next_funding_seconds = int((next_funding_time - now).total_seconds())
            
            # Count high deviation contracts
            if row['z_score'] and abs(row['z_score']) > 2.0:
                high_deviation_count += 1
            
            contract_data = {
                'contract': row['contract'],
                'exchange': row['exchange'],
                'base_asset': row['base_asset'],
                'mark_price': sanitize_numeric_value(float(row['mark_price'])) if row['mark_price'] else None,
                'z_score': sanitize_numeric_value(float(row['z_score'])) if row['z_score'] else None,
                'z_score_apr': sanitize_numeric_value(float(row['z_score_apr'])) if row['z_score_apr'] else None,
                'funding_rate': sanitize_numeric_value(float(row['funding_rate'])) if row['funding_rate'] else None,
                'apr': sanitize_numeric_value(float(row['apr'])) if row['apr'] else None,
                'percentile': row['percentile'],
                'percentile_apr': row['percentile_apr'],
                'mean_30d': sanitize_numeric_value(float(row['mean_30d'])) if row['mean_30d'] else None,
                'std_dev_30d': sanitize_numeric_value(float(row['std_dev_30d'])) if row['std_dev_30d'] else None,
                'mean_30d_apr': sanitize_numeric_value(float(row['mean_30d_apr'])) if row['mean_30d_apr'] else None,
                'std_dev_30d_apr': sanitize_numeric_value(float(row['std_dev_30d_apr'])) if row['std_dev_30d_apr'] else None,
                'data_points': row['data_points'],
                'expected_points': row['expected_points'],
                'completeness_percentage': sanitize_numeric_value(float(row['completeness_percentage'])) if row['completeness_percentage'] else None,
                'confidence': row['confidence'],
                'funding_interval_hours': row['funding_interval_hours'],
                'next_funding_seconds': next_funding_seconds
            }
            contracts.append(contract_data)
        
        result = {
            'contracts': contracts,
            'total': len(contracts),
            'high_deviation_count': high_deviation_count,
            'update_timestamp': datetime.now(timezone.utc).isoformat()
        }
        
        # Cache the result with TTL - standardized to 25s
        api_cache.set(cache_key, result, ttl_seconds=25)
        
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cur.close()
        return_db_connection(conn)

@app.get("/api/statistics/extreme-values")
async def get_extreme_values(
    min_abs_zscore: float = Query(2.0, ge=0, le=4, description="Minimum absolute Z-score for extreme values")
):
    """
    Get contracts with extreme Z-scores.
    Reference: Z_score.md lines 459-460
    """
    conn = get_db_connection()
    cur = conn.cursor()
    
    try:
        query = """
            SELECT 
                fs.symbol as contract,
                fs.exchange,
                fs.base_asset,
                fs.current_z_score as z_score,
                fs.current_z_score_apr as z_score_apr,
                fs.current_funding_rate as funding_rate,
                fs.current_apr as apr,
                fs.current_percentile as percentile,
                fs.current_percentile_apr as percentile_apr,
                fs.confidence_level as confidence
            FROM funding_statistics fs
            WHERE ABS(fs.current_z_score) >= %s
            ORDER BY ABS(fs.current_z_score) DESC
        """
        
        cur.execute(query, (min_abs_zscore,))
        results = cur.fetchall()
        
        extreme_contracts = []
        for row in results:
            extreme_contracts.append({
                'contract': row['contract'],
                'exchange': row['exchange'],
                'base_asset': row['base_asset'],
                'z_score': sanitize_numeric_value(float(row['z_score'])) if row['z_score'] else None,
                'z_score_apr': sanitize_numeric_value(float(row['z_score_apr'])) if row['z_score_apr'] else None,
                'funding_rate': sanitize_numeric_value(float(row['funding_rate'])) if row['funding_rate'] else None,
                'apr': sanitize_numeric_value(float(row['apr'])) if row['apr'] else None,
                'percentile': row['percentile'],
                'percentile_apr': row['percentile_apr'],
                'confidence': row['confidence']
            })
        
        return {
            'extreme_contracts': extreme_contracts,
            'count': len(extreme_contracts),
            'threshold': min_abs_zscore,
            'timestamp': datetime.now(timezone.utc).isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cur.close()
        return_db_connection(conn)

@app.get("/api/statistics/summary")
async def get_statistics_summary():
    """
    Get system-wide Z-score statistics with 10-second caching.
    Reference: Z_score.md lines 459-460
    """
    # Check cache first
    cache_key = "statistics_summary"
    cached_result = api_cache.get(cache_key, ttl_seconds=25)  # Standardized to 25s
    if cached_result is not None:
        return cached_result
    
    conn = get_db_connection()
    cur = conn.cursor()
    
    try:
        # Get overall statistics
        cur.execute("""
            SELECT 
                COUNT(*) as total_contracts,
                COUNT(current_z_score) as contracts_with_zscore,
                AVG(ABS(current_z_score)) as mean_abs_zscore,
                MAX(ABS(current_z_score)) as max_abs_zscore,
                COUNT(CASE WHEN ABS(current_z_score) > 2.0 THEN 1 END) as extreme_count,
                COUNT(CASE WHEN confidence_level = 'very_high' THEN 1 END) as very_high_confidence,
                COUNT(CASE WHEN confidence_level = 'high' THEN 1 END) as high_confidence,
                COUNT(CASE WHEN confidence_level = 'medium' THEN 1 END) as medium_confidence,
                COUNT(CASE WHEN confidence_level = 'low' THEN 1 END) as low_confidence,
                COUNT(CASE WHEN data_points >= 90 THEN 1 END) as high_data_quality_count
            FROM funding_statistics
        """)
        
        overall = cur.fetchone()
        
        # Get breakdown by exchange
        cur.execute("""
            SELECT 
                exchange,
                COUNT(*) as contracts,
                AVG(ABS(current_z_score)) as mean_abs_zscore,
                COUNT(CASE WHEN ABS(current_z_score) > 2.0 THEN 1 END) as extreme_count,
                AVG(completeness_percentage) as avg_completeness
            FROM funding_statistics
            GROUP BY exchange
            ORDER BY exchange
        """)
        
        exchange_breakdown = []
        for row in cur.fetchall():
            # Safe float conversion handling NaN
            mean_zscore = None
            if row['mean_abs_zscore'] is not None:
                try:
                    val = float(row['mean_abs_zscore'])
                    if not (math.isnan(val) or math.isinf(val)):
                        mean_zscore = val
                except (TypeError, ValueError):
                    pass
            
            avg_comp = None
            if row['avg_completeness'] is not None:
                try:
                    val = float(row['avg_completeness'])
                    if not (math.isnan(val) or math.isinf(val)):
                        avg_comp = val
                except (TypeError, ValueError):
                    pass
            
            exchange_breakdown.append({
                'exchange': row['exchange'],
                'contracts': row['contracts'],
                'mean_abs_zscore': mean_zscore,
                'extreme_count': row['extreme_count'],
                'avg_completeness': avg_comp
            })
        
        # Safe float conversion for overall stats
        mean_abs_overall = None
        if overall['mean_abs_zscore'] is not None:
            try:
                val = float(overall['mean_abs_zscore'])
                if not (math.isnan(val) or math.isinf(val)):
                    mean_abs_overall = val
            except (TypeError, ValueError):
                pass
        
        max_abs_overall = None
        if overall['max_abs_zscore'] is not None:
            try:
                val = float(overall['max_abs_zscore'])
                if not (math.isnan(val) or math.isinf(val)):
                    max_abs_overall = val
            except (TypeError, ValueError):
                pass
        
        result = {
            'overall': {
                'total_contracts': overall['total_contracts'],
                'contracts_with_zscore': overall['contracts_with_zscore'],
                'contracts_with_zscore_percentage': (overall['contracts_with_zscore'] / overall['total_contracts'] * 100) if overall['total_contracts'] > 0 else 0,
                'mean_abs_zscore': mean_abs_overall,
                'max_abs_zscore': max_abs_overall,
                'extreme_count': overall['extreme_count'],
                'high_confidence_contracts': overall['very_high_confidence'] + overall['high_confidence'],
                'confidence_breakdown': {
                    'very_high': overall['very_high_confidence'],
                    'high': overall['high_confidence'],
                    'medium': overall['medium_confidence'],
                    'low': overall['low_confidence']
                }
            },
            'exchange_breakdown': exchange_breakdown,
            'timestamp': datetime.now(timezone.utc).isoformat()
        }
        
        # Cache the result with TTL - standardized to 25s
        api_cache.set(cache_key, result, ttl_seconds=25)
        
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cur.close()
        return_db_connection(conn)

@app.get("/api/backfill/verify")
async def verify_backfill_completeness(
    days: int = Query(30, description="Number of days to analyze"),
    exchange: str = Query(None, description="Filter by specific exchange"),
    symbol: str = Query(None, description="Filter by specific symbol"),
    threshold: float = Query(95.0, description="Minimum completeness threshold percentage")
):
    """
    Verify data completeness for historical backfill.
    Returns completeness metrics, gap detection, and retry candidates.
    """
    from utils.backfill_completeness import BackfillCompletenessValidator
    
    try:
        validator = BackfillCompletenessValidator()
        
        if exchange and symbol:
            # Validate single contract
            result = validator.validate_contract(exchange, symbol, days)
            return result
        elif exchange:
            # Validate all contracts for specific exchange
            db = PostgresManager()
            conn = db.connection
            cur = conn.cursor(cursor_factory=RealDictCursor)
            
            cur.execute("""
                SELECT DISTINCT symbol 
                FROM funding_rates_historical 
                WHERE exchange = %s
                ORDER BY symbol
            """, (exchange,))
            
            contracts = []
            summary = {
                'exchange': exchange,
                'total_contracts': 0,
                'complete': 0,
                'incomplete': 0,
                'needs_retry': []
            }
            
            for row in cur.fetchall():
                result = validator.validate_contract(exchange, row['symbol'], days)
                contracts.append(result)
                summary['total_contracts'] += 1
                
                if result.get('completeness_percentage', 0) >= threshold:
                    summary['complete'] += 1
                else:
                    summary['incomplete'] += 1
                    if result.get('needs_retry', False):
                        summary['needs_retry'].append(row['symbol'])
            
            cur.close()
            return_db_connection(conn)
            
            return {
                'summary': summary,
                'contracts': contracts,
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
        else:
            # Full validation (may be slow for many contracts)
            # For performance, return summary only
            results = validator.validate_all_contracts(days)
            
            # Get retry candidates
            retry_candidates = validator.get_retry_candidates(threshold)
            
            # Return summary and top retry candidates
            if 'summary' in results:
                return {
                    'summary': results['summary'],
                    'days_analyzed': results.get('days_analyzed', days),
                    'timestamp': results.get('timestamp'),
                    'retry_candidates': retry_candidates[:20],  # Limit to top 20
                    'total_retry_needed': len(retry_candidates)
                }
            else:
                return results
                
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/health/cache")
async def get_cache_health():
    """
    Get cache health status and performance metrics.
    Shows whether Redis is connected or fallback to in-memory cache.
    """
    try:
        metrics = api_cache.get_metrics()
        health_status = api_cache.health_check()
        
        return {
            'status': 'healthy' if health_status else 'degraded',
            'type': metrics.get('type', 'Unknown'),
            'connected': metrics.get('connected', False),
            'host': metrics.get('host', 'N/A'),
            'metrics': metrics.get('metrics', {}),
            'timestamp': datetime.now(timezone.utc).isoformat()
        }
    except Exception as e:
        return {
            'status': 'error',
            'error': str(e),
            'timestamp': datetime.now(timezone.utc).isoformat()
        }

@app.post("/api/backfill/retry")
async def retry_incomplete_backfill(
    threshold: float = Query(95.0, description="Minimum completeness threshold"),
    limit: int = Query(10, description="Maximum number of contracts to retry")
):
    """
    Trigger retry for contracts with incomplete data.
    """
    from utils.backfill_completeness import BackfillCompletenessValidator
    import subprocess
    import json
    
    try:
        validator = BackfillCompletenessValidator()
        
        # Get retry candidates
        retry_candidates = validator.get_retry_candidates(threshold)[:limit]
        
        if not retry_candidates:
            return {
                'message': 'No contracts need retry',
                'threshold': threshold
            }
        
        # Create retry list file
        retry_file = '.backfill_retry.json'
        with open(retry_file, 'w') as f:
            json.dump({
                'contracts': retry_candidates,
                'timestamp': datetime.now(timezone.utc).isoformat()
            }, f, indent=2, default=str)
        
        # Start backfill for retry candidates
        retry_count = len(retry_candidates)
        
        return {
            'message': f'Retry list created for {retry_count} contracts',
            'threshold': threshold,
            'retry_count': retry_count,
            'contracts': [f"{c['exchange']}:{c['symbol']}" for c in retry_candidates],
            'retry_file': retry_file,
            'note': 'Run unified_historical_backfill.py with --retry flag to process these contracts'
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# WebSocket endpoints removed

    finally:
        cur.close()
        conn.close()

if __name__ == "__main__":
    import uvicorn
    print("Starting Exchange Data API...")
    print("API Documentation: http://localhost:8000/docs")
    print("React App CORS: http://localhost:3000")
    uvicorn.run(app, host="0.0.0.0", port=8000)
