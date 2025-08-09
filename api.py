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
from dotenv import load_dotenv

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
    'password': os.getenv("POSTGRES_PASSWORD", "postgres")
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
        # Build query with filters - DEFAULT TO BINANCE ONLY
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
            WHERE LOWER(exchange) = 'binance'
        """
        params = []
        
        # Note: exchange filter is now always Binance
        if exchange and exchange.lower() != 'binance':
            # If someone specifically requests another exchange, return empty
            return []
        
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
        # Get overall statistics - BINANCE ONLY
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
                AND LOWER(exchange) = 'binance'
        """)
        
        stats = dict(cur.fetchone())
        
        # Get highest APR contract details - BINANCE ONLY
        cur.execute("""
            SELECT symbol, exchange, apr
            FROM exchange_data
            WHERE apr = (SELECT MAX(apr) FROM exchange_data WHERE apr IS NOT NULL AND LOWER(exchange) = 'binance')
                AND LOWER(exchange) = 'binance'
            LIMIT 1
        """)
        highest = cur.fetchone()
        if highest:
            stats['highest_symbol'] = highest['symbol']
            stats['highest_exchange'] = highest['exchange']
        
        # Get lowest APR contract details - BINANCE ONLY
        cur.execute("""
            SELECT symbol, exchange, apr
            FROM exchange_data
            WHERE apr = (SELECT MIN(apr) FROM exchange_data WHERE apr IS NOT NULL AND LOWER(exchange) = 'binance')
                AND LOWER(exchange) = 'binance'
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
    # Return only Binance
    return ["Binance"]

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
        # Query to get latest funding rate per asset - BINANCE ONLY
        cur.execute("""
            WITH latest_rates AS (
                SELECT DISTINCT ON (base_asset, exchange)
                    base_asset,
                    exchange,
                    funding_rate,
                    apr,
                    last_updated
                FROM exchange_data
                WHERE base_asset IS NOT NULL
                    AND funding_rate IS NOT NULL
                    AND LOWER(exchange) = 'binance'
                ORDER BY base_asset, exchange, last_updated DESC
            )
            SELECT 
                base_asset,
                json_object_agg(
                    exchange, 
                    json_build_object(
                        'funding_rate', funding_rate,
                        'apr', apr
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
                        'apr': float(rates['apr']) if rates['apr'] else None
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
    cur = conn.cursor()
    
    try:
        # Calculate date range
        end_date = datetime.now(timezone.utc)
        start_date = end_date - timedelta(days=days)
        
        # Get historical data from funding_rates_historical table - BINANCE ONLY
        # First check if the table exists
        cur.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = 'funding_rates_historical'
            )
        """)
        
        has_historical = cur.fetchone()['exists']
        
        if has_historical:
            # Use funding_rates_historical table (preferred)
            query = """
                SELECT 
                    exchange,
                    symbol,
                    funding_rate,
                    funding_rate * 365 * 100 / 8 as apr,
                    funding_time
                FROM funding_rates_historical
                WHERE base_asset = %s
                    AND funding_time >= %s
                    AND funding_time <= %s
                    AND LOWER(exchange) = 'binance'
                ORDER BY funding_time DESC, exchange
            """
        else:
            # Fallback to main table if historical doesn't exist - BINANCE ONLY
            query = """
                SELECT 
                    exchange,
                    symbol,
                    funding_rate,
                    apr,
                    last_updated as funding_time
                FROM exchange_data
                WHERE base_asset = %s
                    AND last_updated >= %s
                    AND last_updated <= %s
                    AND LOWER(exchange) = 'binance'
                ORDER BY last_updated DESC, exchange
            """
        
        cur.execute(query, (asset, start_date, end_date))
        results = cur.fetchall()
        
        # Group data by timestamp and exchange
        time_series = {}
        exchanges = set()
        
        for row in results:
            timestamp = row['funding_time'].isoformat() if row['funding_time'] else None
            exchange = row['exchange']
            
            if timestamp not in time_series:
                time_series[timestamp] = {}
            
            time_series[timestamp][exchange] = {
                'funding_rate': float(row['funding_rate']) if row['funding_rate'] else None,
                'apr': float(row['apr']) if row['apr'] else None,
                'symbol': row['symbol']
            }
            exchanges.add(exchange)
        
        # Format for chart display
        chart_data = []
        for timestamp, exchange_data in sorted(time_series.items()):
            data_point = {'timestamp': timestamp}
            for exchange in exchanges:
                if exchange in exchange_data:
                    data_point[exchange] = exchange_data[exchange]['funding_rate']
                else:
                    data_point[exchange] = None
            chart_data.append(data_point)
        
        return {
            'asset': asset,
            'exchanges': list(exchanges),
            'days': days,
            'data_points': len(chart_data),
            'data': chart_data
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cur.close()
        conn.close()

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

if __name__ == "__main__":
    import uvicorn
    print("Starting Exchange Data API...")
    print("API Documentation: http://localhost:8000/docs")
    print("React App CORS: http://localhost:3000")
    uvicorn.run(app, host="0.0.0.0", port=8000)