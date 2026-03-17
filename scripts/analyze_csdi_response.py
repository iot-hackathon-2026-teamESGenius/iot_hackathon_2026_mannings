#!/usr/bin/env python3
"""
Analyze CSDI API Response Structure
==================================
"""

import requests
import json

def analyze_csdi_api():
    """Analyze CSDI API response structure"""
    url = 'https://www.map.gov.hk/gs/api/v1.0.0/locationSearch'
    params = {'q': 'Festival Walk'}
    
    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        print('CSDI API Response Analysis:')
        print('=' * 40)
        print(f'Response type: {type(data)}')
        print(f'Number of results: {len(data) if isinstance(data, list) else "Not a list"}')
        
        if isinstance(data, list) and data:
            print(f'First result keys: {list(data[0].keys())}')
            print('\nFirst result:')
            print(json.dumps(data[0], indent=2, ensure_ascii=False))
            
            # Check coordinates
            first_result = data[0]
            x, y = first_result.get('x', 0), first_result.get('y', 0)
            print(f'\nCoordinates: x={x}, y={y}')
            
            # Hong Kong Grid coordinates are typically 6-digit numbers
            if x > 100000 and y > 100000:
                print('⚠️ Coordinates appear to be Hong Kong Grid format, need conversion to WGS84')
                
                # Approximate conversion (for reference only)
                # Proper conversion requires official transformation parameters
                lat_approx = 22.0 + (y - 800000) / 111000
                lng_approx = 114.0 + (x - 800000) / 111000 / 0.8
                print(f'Approximate WGS84: {lat_approx:.6f}, {lng_approx:.6f}')
            else:
                print('✅ Coordinates appear to be WGS84 format')
                
        print('\nTesting multiple addresses:')
        test_addresses = [
            'Central',
            'Tsim Sha Tsui',
            'Causeway Bay',
            'Mong Kok'
        ]
        
        for addr in test_addresses:
            params = {'q': addr}
            response = requests.get(url, params=params, timeout=10)
            data = response.json()
            count = len(data) if isinstance(data, list) else 0
            print(f'  {addr}: {count} results')
            
    except Exception as e:
        print(f'Error: {e}')

if __name__ == "__main__":
    analyze_csdi_api()