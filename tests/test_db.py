import psycopg2
from psycopg2.extras import RealDictCursor
import os
from dotenv import load_dotenv

load_dotenv()

DB_CONFIG = {
    'host': os.getenv("POSTGRES_HOST", "localhost"),
    'port': os.getenv("POSTGRES_PORT", "5432"),
    'database': os.getenv("POSTGRES_DATABASE", "exchange_data"),
    'user': os.getenv("POSTGRES_USER", "postgres"),
    'password': os.getenv("POSTGRES_PASSWORD", "postgres")
}

print("Connecting with config:", DB_CONFIG)

try:
    conn = psycopg2.connect(**DB_CONFIG, cursor_factory=RealDictCursor)
    cur = conn.cursor()
    
    # Test query
    cur.execute("SELECT COUNT(*) as count FROM exchange_data")
    result = cur.fetchone()
    print(f"Total records in exchange_data: {result['count']}")
    
    # Get sample data
    cur.execute("SELECT exchange, symbol, funding_rate FROM exchange_data LIMIT 5")
    rows = cur.fetchall()
    print("\nSample data:")
    for row in rows:
        print(f"  {row['exchange']}: {row['symbol']} - {row['funding_rate']}")
    
    # Test the exact query from the API
    cur.execute("""
        SELECT DISTINCT exchange
        FROM exchange_data
        WHERE exchange IS NOT NULL
        ORDER BY exchange
    """)
    exchanges = cur.fetchall()
    print(f"\nDistinct exchanges: {[e['exchange'] for e in exchanges]}")
    
    cur.close()
    conn.close()
    print("\nDatabase connection successful!")
    
except Exception as e:
    print(f"Error: {e}")