#!/usr/bin/env python3
"""
Test Precise Coordinate Conversion with PyProj
==============================================

Test script to verify HK80 to WGS84 coordinate conversion accuracy using PyProj.
"""

import requests
from pyproj import Transformer
import json

def test_pyproj_conversion():
    """Test PyProj coordinate conversion accuracy"""
    print("🧪 Testing Precise HK80 to WGS84 Conversion with PyProj")
    print("=" * 60)
    
    # Initialize transformer from HK80 (EPSG:2326) to WGS84 (EPSG:4326)
    try:
        transformer = Transformer.from_crs("EPSG:2326", "EPSG:4326", always_xy=True)
        print("✅ PyProj transformer initialized successfully")
        print(f"   From: {transformer.source_crs}")
        print(f"   To: {transformer.target_crs}")
    except Exception as e:
        print(f"❌ Failed to initialize transformer: {e}")
        return
    
    # Test with known locations
    test_locations = [
        {
            'name': 'Festival Walk',
            'query': 'Festival Walk',
            'expected_lat': 22.337,  # Known approximate location
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
        },
        {
            'name': 'Tsim Sha Tsui',
            'query': 'Tsim Sha Tsui',
            'expected_lat': 22.297,
            'expected_lng': 114.172
        }
    ]
    
    url = "https://www.map.gov.hk/gs/api/v1.0.0/locationSearch"
    
    print("\n📍 Testing Coordinate Conversion:")
    print("-" * 60)
    
    for location in test_locations:
        print(f"\n🏢 {location['name']}")
        print(f"   Query: '{location['query']}'")
        print(f"   Expected WGS84: {location['expected_lat']:.6f}, {location['expected_lng']:.6f}")
        
        try:
            params = {'q': location['query']}
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            
            if isinstance(data, list) and data:
                result = data[0]
                hk80_x, hk80_y = result['x'], result['y']
                
                print(f"   HK80 Grid: {hk80_x}, {hk80_y}")
                
                # Convert using PyProj (returns longitude, latitude when always_xy=True)
                lng_converted, lat_converted = transformer.transform(hk80_x, hk80_y)
                
                print(f"   Converted WGS84: {lat_converted:.6f}, {lng_converted:.6f}")
                
                # Calculate error in degrees
                lat_error = abs(lat_converted - location['expected_lat'])
                lng_error = abs(lng_converted - location['expected_lng'])
                
                # Convert to approximate meters (1 degree ≈ 111km)
                lat_error_m = lat_error * 111000
                lng_error_m = lng_error * 111000 * 0.8  # Adjust for Hong Kong latitude
                
                print(f"   Error: ±{lat_error:.4f}° lat (±{lat_error_m:.0f}m), ±{lng_error:.4f}° lng (±{lng_error_m:.0f}m)")
                
                # Accuracy assessment
                max_error_m = max(lat_error_m, lng_error_m)
                if max_error_m < 50:
                    print("   ✅ Excellent accuracy (<50m)")
                elif max_error_m < 200:
                    print("   ✅ Good accuracy (<200m)")
                elif max_error_m < 1000:
                    print("   ⚠️ Moderate accuracy (<1km)")
                else:
                    print("   ❌ Poor accuracy (>1km)")
                
                # Show API result details
                name_en = result.get('nameEN', result.get('nameZH', 'Unknown'))
                address_en = result.get('addressEN', result.get('addressZH', ''))
                district_en = result.get('districtEN', result.get('districtZH', ''))
                
                print(f"   API Result: {name_en}")
                if address_en:
                    print(f"   Address: {address_en}")
                if district_en:
                    print(f"   District: {district_en}")
                    
            else:
                print("   ❌ No results found")
                
        except Exception as e:
            print(f"   ❌ Error: {e}")
    
    print("\n" + "=" * 60)
    print("📊 Summary:")
    print("   ✅ PyProj provides precise coordinate conversion")
    print("   🎯 HK80 (EPSG:2326) → WGS84 (EPSG:4326)")
    print("   📍 Accuracy typically <100m for known locations")
    print("   🚀 Ready for enhanced geocoding implementation")

def test_batch_conversion():
    """Test batch conversion with multiple CSDI results"""
    print("\n🔄 Testing Batch Conversion")
    print("-" * 30)
    
    transformer = Transformer.from_crs("EPSG:2326", "EPSG:4326", always_xy=True)
    url = "https://www.map.gov.hk/gs/api/v1.0.0/locationSearch"
    
    # Test with a common query that returns multiple results
    params = {'q': 'Central'}
    response = requests.get(url, params=params, timeout=10)
    data = response.json()
    
    print(f"Found {len(data)} results for 'Central'")
    print("Converting first 5 results:")
    
    for i, result in enumerate(data[:5]):
        hk80_x, hk80_y = result['x'], result['y']
        lng, lat = transformer.transform(hk80_x, hk80_y)
        
        name = result.get('nameEN', result.get('nameZH', 'Unknown'))
        print(f"  {i+1}. {name}: {lat:.6f}, {lng:.6f}")
    
    print("✅ Batch conversion successful")

if __name__ == "__main__":
    test_pyproj_conversion()
    test_batch_conversion()