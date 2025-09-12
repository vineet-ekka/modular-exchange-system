"""
Performance Testing Script
==========================
Tests the performance improvements for the Z-score system.
Target: Z-score calculation <1s, API response <100ms
"""

import time
import requests
import psycopg2
from datetime import datetime
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.zscore_calculator import ZScoreCalculator

# Database connection
DB_CONFIG = {
    'host': 'localhost',
    'port': 5432,
    'database': 'exchange_data',
    'user': 'postgres',
    'password': 'postgres123'
}

# API configuration
API_BASE_URL = 'http://localhost:8000'

def test_zscore_performance():
    """Test Z-score calculation performance. Target: <1 second."""
    print("\n=== Z-Score Calculation Performance Test ===")
    
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        calc = ZScoreCalculator(conn)
        
        # Test full calculation
        print("Testing full Z-score calculation...")
        start = time.time()
        result = calc.process_all_contracts()
        duration = time.time() - start
        
        print(f"Duration: {duration:.2f}s")
        if result:
            print(f"Contracts processed: {result.get('processed', 0)}")
            print(f"Contracts/second: {result.get('contracts_per_second', 0):.1f}")
        
        # Check against target
        if duration < 1.0:
            print(f"PASS: {duration:.2f}s < 1.0s target")
        else:
            print(f"FAIL: {duration:.2f}s > 1.0s target")
        
        conn.close()
        return duration < 1.0
        
    except Exception as e:
        print(f"ERROR: {e}")
        return False

def test_api_performance():
    """Test API response time. Target: <100ms."""
    print("\n=== API Response Time Test ===")
    
    try:
        # Test contracts-with-zscores endpoint
        print("Testing /api/contracts-with-zscores endpoint...")
        
        # First call (no cache)
        start = time.time()
        response = requests.get(f'{API_BASE_URL}/api/contracts-with-zscores')
        duration_first = time.time() - start
        
        if response.status_code != 200:
            print(f"ERROR: API returned status {response.status_code}")
            return False
        
        data = response.json()
        print(f"First call (no cache): {duration_first*1000:.0f}ms")
        print(f"Contracts returned: {len(data.get('contracts', []))}")
        
        # Second call (cached)
        start = time.time()
        response = requests.get(f'{API_BASE_URL}/api/contracts-with-zscores')
        duration_cached = time.time() - start
        print(f"Second call (cached): {duration_cached*1000:.0f}ms")
        
        # Check against target (cached response)
        if duration_cached < 0.1:
            print(f"PASS: {duration_cached*1000:.0f}ms < 100ms target")
        else:
            print(f"FAIL: {duration_cached*1000:.0f}ms > 100ms target")
        
        return duration_cached < 0.1
        
    except Exception as e:
        print(f"ERROR: {e}")
        return False

def test_zone_performance():
    """Test zone-based update performance."""
    print("\n=== Zone-Based Update Performance Test ===")
    
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        calc = ZScoreCalculator(conn)
        
        # Test active zone updates
        print("Testing active zone updates...")
        start = time.time()
        result = calc.process_contracts_by_zone('active')
        duration_active = time.time() - start
        
        print(f"Active zone: {result.get('processed', 0)} contracts in {duration_active:.2f}s")
        
        # Test stable zone updates
        print("Testing stable zone updates...")
        start = time.time()
        result = calc.process_contracts_by_zone('stable')
        duration_stable = time.time() - start
        
        print(f"Stable zone: {result.get('processed', 0)} contracts in {duration_stable:.2f}s")
        
        # Active zone should be much faster (fewer contracts)
        if duration_active < 0.5:
            print(f"PASS: Active zone update < 0.5s")
        else:
            print(f"FAIL: Active zone update > 0.5s")
        
        conn.close()
        return duration_active < 0.5
        
    except Exception as e:
        print(f"ERROR: {e}")
        return False

def check_database_stats():
    """Check database statistics."""
    print("\n=== Database Statistics ===")
    
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()
        
        # Check zone distribution
        cur.execute("""
            SELECT update_zone, COUNT(*) as count
            FROM funding_statistics
            GROUP BY update_zone
        """)
        
        print("Zone distribution:")
        for row in cur.fetchall():
            print(f"  {row[0]}: {row[1]} contracts")
        
        # Check contracts with high Z-scores
        cur.execute("""
            SELECT COUNT(*) as high_zscore_count
            FROM funding_statistics
            WHERE ABS(current_z_score) > 2.0
        """)
        
        result = cur.fetchone()
        print(f"High Z-score contracts (|Z| > 2.0): {result[0]}")
        
        # Check data completeness
        cur.execute("""
            SELECT AVG(completeness_percentage) as avg_completeness
            FROM funding_statistics
        """)
        
        result = cur.fetchone()
        print(f"Average data completeness: {result[0]:.1f}%")
        
        conn.close()
        
    except Exception as e:
        print(f"❌ ERROR: {e}")

def main():
    """Run all performance tests."""
    print("=" * 50)
    print("Z-SCORE SYSTEM PERFORMANCE TEST")
    print("=" * 50)
    print(f"Start time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    results = {
        'zscore_calc': False,
        'api_response': False,
        'zone_updates': False
    }
    
    # Run tests
    results['zscore_calc'] = test_zscore_performance()
    results['api_response'] = test_api_performance()
    results['zone_updates'] = test_zone_performance()
    
    # Check database stats
    check_database_stats()
    
    # Summary
    print("\n" + "=" * 50)
    print("TEST SUMMARY")
    print("=" * 50)
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    for test, result in results.items():
        status = "PASS" if result else "FAIL"
        print(f"{test}: {status}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("\nALL PERFORMANCE TARGETS MET!")
        return 0
    else:
        print(f"\n{total - passed} tests failed. Performance optimization needed.")
        return 1

if __name__ == "__main__":
    sys.exit(main())