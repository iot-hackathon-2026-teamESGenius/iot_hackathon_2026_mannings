#!/usr/bin/env python3
"""
Test Coordinate Conversion
=========================

Test script to verify HK80 to WGS84 coordinate conversion accuracy.
"""

import requests

def test_csdi_coordinate_conversion():
    """Test CSDI API and coordinate conversion"""
    print("🧪 Testing CSDI API Coordinate Conversion")
    print("=" * 50)
    
    # Test with known locations
    test_locations = [
        {
            'name': 'Festival Walk',
            'query': 'Festival Walk',
            'expected_lat': 22.337,  # Approximate known location
            'expected_lng': 114.174
        },
        {
            'name': 'Times Square',
            'query': 'Times Square Causeway Bay',
            'expected_lat': 22.278,
            'expected_lng': 114.182
        },
        {
            'name': 'IFC Mall',
            'query': 'IFC Mall Central',
            'expected_lat': 22.285,
            'expected_lng': 114.158
        }
    ]
    
    url = "https://www.map.gov.hk/gs/api/v1.0.0/locationSearch"
    
    for location in test_locations:
        print(f"\n📍 Testing: {location['name']}")
        print(f"   Query: {location['query']}")
        print(f"   Expected: {location['expected_lat']:.6f}, {location['expected_lng']:.6f}")
        
        try:
            params = {'q': location['query']}
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            
            if isinstance(data, list) and data:
                result = data[0]
                hk80_x, hk80_y = result['x'], result['y']
                
                print(f"   HK80 Coordinates: {hk80_x}, {hk80_y}")
                
                # Simple approximate conversion for testing
                lat_approx = 22.0 + (hk80_y - 815000) / 110000
                lng_approx = 114.0 + (hk80_x - 830000) / 85000
                
                print(f"   Converted (approx): {lat_approx:.6f}, {lng_approx:.6f}")
                
                # Calculate error
                lat_error = abs(lat_approx - location['expected_lat'])
                lng_error = abs(lng_approx - location['expected_lng'])
                
                print(f"   Error: ±{lat_error:.3f}° lat, ±{lng_error:.3f}° lng")
                
                if lat_error < 0.01 and lng_error < 0.01:
                    print("   ✅ Good accuracy (<0.01°)")
                elif lat_error < 0.05 and lng_error < 0.05:
                    print("   ⚠️ Moderate accuracy (<0.05°)")
                else:
                    print("   ❌ Poor accuracy (>0.05°)")
                    
                # Show location name from API
                name_en = result.get('nameEN', result.get('nameZH', 'Unknown'))
                print(f"   API Result: {name_en}")
                
            else:
                print("   ❌ No results found")
                
        except Exception as e:
            print(f"   ❌ Error: {e}")
    
    print("\n💡 Notes:")
    print("   - Approximate conversion is used for testing")
    print("   - Install 'pyproj' for precise conversion: pip install pyproj")
    print("   - Errors <0.01° (~1km) are acceptable for most applications")
    print("   - Errors <0.001° (~100m) are excellent for store locations")

if __name__ == "__main__":
    test_csdi_coordinate_conversion()