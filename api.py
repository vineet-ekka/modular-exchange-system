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
import pandas as pd
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta, timezone
import json
import os
import time
import subprocess
import signal
from pathlib import Path
from dotenv import load_dotenv
from config.settings_manager import SettingsManager
from database.postgres_manager import PostgresManager

# Load environment variables
load_dotenv()

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

# Database configuration
DB_CONFIG = {
    'host': os.getenv("POSTGRES_HOST", "localhost"),
    'port': os.getenv("POSTGRES_PORT", "5432"),
    'database': os.getenv("POSTGRES_DATABASE", "exchange_data"),
    'user': os.getenv("POSTGRES_USER", "postgres"),
    'password': os.getenv("POSTGRES_PASSWORD", "postgres123")
}

def get_db_connection():
    """Create database connection with RealDictCursor for JSON serialization."""
    try:
        conn = psycopg2.connect(**DB_CONFIG, cursor_factory=RealDictCursor)
        return conn
    except Exception as e:
        print(f"Database connection error: {e}")
        raise HTTPException(status_code=500, detail="Database connection failed")

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
        conn.close()
        return {"status": "healthy", "database": "connected"}
    except:
        return JSONResponse(
            status_code=503,
            content={"status": "unhealthy", "database": "disconnected"}
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
    conn = get_db_connection()
    cur = conn.cursor()
    
    try:
        # Build query with filters
        query = """
            SELECT 
                exchange,
                symbol,
                base_asset,
                quote_asset,
                funding_rate,
                funding_interval_hours,
                apr,
                index_price,
                mark_price,
                open_interest,
                contract_type,
                market_type,
                last_updated
            FROM exchange_data
            WHERE 1=1
        """
        params = []
        
        # Apply exchange filter if provided
        if exchange:
            query += " AND LOWER(exchange) = LOWER(%s)"
            params.append(exchange)
        
        if base_asset:
            query += " AND LOWER(base_asset) = LOWER(%s)"
            params.append(base_asset)
        
        if min_apr is not None:
            query += " AND apr >= %s"
            params.append(min_apr)
        
        if max_apr is not None:
            query += " AND apr <= %s"
            params.append(max_apr)
        
        # Add sorting
        query += f" ORDER BY {sort_by} {sort_order.upper()} NULLS LAST"
        query += " LIMIT %s"
        params.append(limit)
        
        cur.execute(query, params)
        results = cur.fetchall()
        
        # Convert to list of dicts and handle decimal/datetime serialization
        data = []
        for row in results:
            item = dict(row)
            # Convert Decimal to float
            for key in ['funding_rate', 'apr', 'index_price', 'mark_price', 'open_interest']:
                if item.get(key) is not None:
                    item[key] = float(item[key])
            # Convert datetime to ISO string
            if item.get('last_updated'):
                item['last_updated'] = item['last_updated'].isoformat()
            data.append(item)
        
        return data
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cur.close()
        conn.close()

@app.get("/api/statistics")
async def get_statistics():
    """
    Get dashboard statistics including totals, averages, and extremes.
    """
    conn = get_db_connection()
    cur = conn.cursor()
    
    try:
        # Get overall statistics
        cur.execute("""
            SELECT 
                COUNT(*) as total_contracts,
                AVG(apr) as avg_apr,
                MAX(apr) as highest_apr,
                MIN(apr) as lowest_apr,
                COUNT(DISTINCT exchange) as active_exchanges,
                COUNT(DISTINCT base_asset) as unique_assets,
                SUM(open_interest) as total_open_interest
            FROM exchange_data
            WHERE apr IS NOT NULL
        """)
        
        stats = dict(cur.fetchone())
        
        # Get highest APR contract details
        cur.execute("""
            SELECT symbol, exchange, apr
            FROM exchange_data
            WHERE apr = (SELECT MAX(apr) FROM exchange_data WHERE apr IS NOT NULL)
            LIMIT 1
        """)
        highest = cur.fetchone()
        if highest:
            stats['highest_symbol'] = highest['symbol']
            stats['highest_exchange'] = highest['exchange']
        
        # Get lowest APR contract details
        cur.execute("""
            SELECT symbol, exchange, apr
            FROM exchange_data
            WHERE apr = (SELECT MIN(apr) FROM exchange_data WHERE apr IS NOT NULL)
            LIMIT 1
        """)
        lowest = cur.fetchone()
        if lowest:
            stats['lowest_symbol'] = lowest['symbol']
            stats['lowest_exchange'] = lowest['exchange']
        
        # Convert Decimal to float
        for key in ['avg_apr', 'highest_apr', 'lowest_apr', 'total_open_interest']:
            if stats.get(key) is not None:
                stats[key] = float(stats[key])
        
        # Format large numbers
        stats['total_contracts'] = int(stats['total_contracts']) if stats['total_contracts'] else 0
        stats['active_exchanges'] = int(stats['active_exchanges']) if stats['active_exchanges'] else 0
        stats['unique_assets'] = int(stats['unique_assets']) if stats['unique_assets'] else 0
        
        return stats
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cur.close()
        conn.close()

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
                    item[key] = float(item[key])
            data.append(item)
        
        return data
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cur.close()
        conn.close()

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
                    item[key] = float(item[key])
            data.append(item)
        
        return data
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cur.close()
        conn.close()

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
                    item[key] = float(item[key])
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
        conn.close()

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
        conn.close()

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
        conn.close()

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
                    item[key] = float(item[key])
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
        conn.close()

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
        conn.close()

@app.get("/api/funding-rates-grid")
async def get_funding_rates_grid():
    """
    Get funding rates grouped by asset across all exchanges.
    Returns a simplified grid view with one row per asset.
    """
    conn = get_db_connection()
    cur = conn.cursor()
    
    try:
        # Query to get latest funding rate per asset across all exchanges
        # For Hyperliquid, symbol = base_asset (both are same, e.g., "BTC")
        # Also get the most common funding interval for each asset-exchange pair
        cur.execute("""
            WITH latest_rates AS (
                SELECT DISTINCT ON (COALESCE(base_asset, symbol), exchange)
                    COALESCE(base_asset, symbol) as base_asset,
                    exchange,
                    funding_rate,
                    apr,
                    funding_interval_hours,
                    last_updated
                FROM exchange_data
                WHERE (base_asset IS NOT NULL OR (exchange = 'hyperliquid' AND symbol IS NOT NULL))
                    AND funding_rate IS NOT NULL
                ORDER BY COALESCE(base_asset, symbol), exchange, last_updated DESC
            )
            SELECT 
                base_asset,
                json_object_agg(
                    exchange, 
                    json_build_object(
                        'funding_rate', funding_rate,
                        'apr', apr,
                        'funding_interval_hours', funding_interval_hours
                    )
                ) as exchange_rates
            FROM latest_rates
            GROUP BY base_asset
            ORDER BY base_asset
        """)
        
        results = cur.fetchall()
        
        # Format response
        grid_data = []
        for row in results:
            asset_data = {
                'asset': row['base_asset'],
                'exchanges': {}
            }
            
            # Convert exchange rates
            if row['exchange_rates']:
                for exchange, rates in row['exchange_rates'].items():
                    asset_data['exchanges'][exchange] = {
                        'funding_rate': float(rates['funding_rate']) if rates['funding_rate'] else None,
                        'apr': float(rates['apr']) if rates['apr'] else None,
                        'funding_interval_hours': int(rates['funding_interval_hours']) if rates.get('funding_interval_hours') else None
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
        conn.close()

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
        conn.close()

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
        
        # Get historical data for this specific contract
        query_historical = """
            SELECT 
                exchange,
                symbol,
                base_asset,
                funding_rate,
                funding_rate * (365.0 * 24 / COALESCE(funding_interval_hours, 8)) * 100 as apr,
                funding_time,
                funding_interval_hours,
                mark_price
            FROM funding_rates_historical
            WHERE exchange = %s 
                AND symbol = %s
                AND funding_time >= %s
                AND funding_time <= %s
            ORDER BY funding_time DESC
        """
        cur.execute(query_historical, (exchange, symbol, start_date, end_date))
        historical_results = cur.fetchall()
        
        # Also get the most recent data from main table
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
            WHERE exchange = %s 
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
        
        return {
            'exchange': exchange,
            'symbol': symbol,
            'base_asset': base_asset,
            'funding_interval_hours': funding_interval,
            'days': days,
            'data_points': len(chart_data),
            'data': chart_data
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cur.close()
        conn.close()

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
        conn.close()

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
                    item[key] = float(item[key])
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
        conn.close()

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


if __name__ == "__main__":
    import uvicorn
    print("Starting Exchange Data API...")
    print("API Documentation: http://localhost:8000/docs")
    print("React App CORS: http://localhost:3000")
    uvicorn.run(app, host="0.0.0.0", port=8000)