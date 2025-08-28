import requests
import json
from datetime import datetime

# Test different endpoints
endpoints = [
    ('1D', 'http://localhost:8000/api/historical-funding-by-asset/BTC?timeRange=1D'),
    ('7D', 'http://localhost:8000/api/historical-funding-by-asset/BTC?timeRange=7D'),
    ('30D', 'http://localhost:8000/api/historical-funding-by-asset/BTC?timeRange=30D')
]

for period, url in endpoints:
    try:
        response = requests.get(url)
        data = response.json()
        
        print(f'\n{period} Data for BTC:')
        print(f'  Exchanges: {data.get("exchanges", [])}')
        print(f'  Data points: {data.get("data_points", 0)}')
        print(f'  Contracts: {data.get("contracts", [])}')
        
        # Check if Hyperliquid is present
        if 'Hyperliquid' in data.get('exchanges', []):
            print('  ✓ Hyperliquid is in exchanges list')
            
            # Check if we have actual data
            if 'data' in data and data['data']:
                # Count data points with values
                total_points = len(data['data'])
                points_with_data = 0
                
                for point in data['data']:
                    # Check if any contract has data
                    has_data = any(
                        v is not None 
                        for k, v in point.items() 
                        if k != 'timestamp' and not k.endswith('_apr')
                    )
                    if has_data:
                        points_with_data += 1
                
                print(f'  Data coverage: {points_with_data}/{total_points} points have data')
                
                # Show last data point
                last_point = data['data'][-1] if data['data'] else None
                if last_point:
                    print(f'  Last timestamp: {last_point.get("timestamp")}')
                    contracts_with_data = [
                        k for k, v in last_point.items() 
                        if k != 'timestamp' and not k.endswith('_apr') and v is not None
                    ]
                    if contracts_with_data:
                        print(f'  Contracts with data: {contracts_with_data}')
        else:
            print('  ✗ Hyperliquid NOT in exchanges list')
            
    except Exception as e:
        print(f'\n{period}: Error - {e}')

# Check the grid endpoint
print('\n\nChecking Grid Endpoint:')
try:
    response = requests.get('http://localhost:8000/api/funding-rates-grid')
    data = response.json()
    
    if 'data' in data:
        grid_data = data['data']
        hyperliquid_entries = [d for d in grid_data if d.get('exchange') == 'hyperliquid']
        
        print(f'Total grid entries: {len(grid_data)}')
        print(f'Hyperliquid entries: {len(hyperliquid_entries)}')
        
        if hyperliquid_entries:
            print('\nFirst 5 Hyperliquid entries:')
            for entry in hyperliquid_entries[:5]:
                print(f'  {entry.get("symbol")}: Rate={entry.get("funding_rate")}')
    else:
        print('No data field in response')
        
except Exception as e:
    print(f'Grid error: {e}')