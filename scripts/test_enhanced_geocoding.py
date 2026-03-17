#!/usr/bin/env python3
"""
Enhanced Geocoding API Test Script
==================================

Test script to verify the availability and accuracy of different geocoding APIs
for Hong Kong addresses before running the full geocoding process.

Author: AI Assistant
Date: 2026-03-17
"""

import requests
import time
import os
import json
from typing import Dict, Optional, Tuple

def test_google_maps_api() -> Dict:
    """Test Google Maps Geocoding API"""
    api_key = os.getenv('GOOGLE_MAPS_API_KEY')
    
    if not api_key:
        return {
            'service': 'Google Maps',
            'status': 'SKIP',
            'message': 'API key not found (set GOOGLE_MAPS_API_KEY)',
            'accuracy': 'N/A'
        }
    
    try:
        url = "https://maps.googleapis.com/maps/api/geocode/json"
        test_address = "Festival Walk, 80 Tat Chee Avenue, Kowloon Tong, Hong Kong"
        
        params = {
            'address': test_address,
            'key': api_key,
            'region': 'hk'
        }
        
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        
        if data['status'] == 'OK' and data['results']:
            location = data['results'][0]['geometry']['location']
            formatted_address = data['results'][0]['formatted_address']
            
            return {
                'service': 'Google Maps',
                'status': 'SUCCESS',
                'message': f"✅ Found: {formatted_address}",
                'coordinates': f"{location['lat']:.6f}, {location['lng']:.6f}",
                'accuracy': 'Very High (±10m)'
            }
        else:
            return {
                'service': 'Google Maps',
                'status': 'FAIL',
                'message': f"❌ API Error: {data.get('status', 'Unknown')}",
                'accuracy': 'N/A'
            }
            
    except Exception as e:
        return {
            'service': 'Google Maps',
            'status': 'ERROR',
            'message': f"❌ Exception: {str(e)}",
            'accuracy': 'N/A'
        }

def test_csdi_api() -> Dict:
    """Test Hong Kong CSDI Location Search API"""
    try:
        url = "https://www.map.gov.hk/gs/api/v1.0.0/locationSearch"
        test_address = "Festival Walk"
        
        params = {'q': test_address}
        
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        
        if data and isinstance(data, list) and len(data) > 0:
            # CSDI API structure may vary, adapt based on actual response
            result = data[0]
            
            return {
                'service': 'Hong Kong CSDI',
                'status': 'SUCCESS',
                'message': f"✅ Found {len(data)} results",
                'coordinates': f"Response: {str(result)[:100]}...",
                'accuracy': 'High (±50m)'
            }
        else:
            return {
                'service': 'Hong Kong CSDI',
                'status': 'FAIL',
                'message': "❌ No results found",
                'accuracy': 'N/A'
            }
            
    except Exception as e:
        return {
            'service': 'Hong Kong CSDI',
            'status': 'ERROR',
            'message': f"❌ Exception: {str(e)}",
            'accuracy': 'N/A'
        }

def test_locationiq_api() -> Dict:
    """Test LocationIQ API"""
    api_key = os.getenv('LOCATIONIQ_API_KEY')
    
    if not api_key:
        return {
            'service': 'LocationIQ',
            'status': 'SKIP',
            'message': 'API key not found (set LOCATIONIQ_API_KEY)',
            'accuracy': 'N/A'
        }
    
    try:
        url = "https://us1.locationiq.com/v1/search.php"
        test_address = "Festival Walk, Kowloon Tong, Hong Kong"
        
        params = {
            'key': api_key,
            'q': test_address,
            'format': 'json',
            'countrycodes': 'hk',
            'limit': 1
        }
        
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        
        if data and isinstance(data, list) and len(data) > 0:
            result = data[0]
            lat, lng = result['lat'], result['lon']
            display_name = result.get('display_name', 'Unknown')
            
            return {
                'service': 'LocationIQ',
                'status': 'SUCCESS',
                'message': f"✅ Found: {display_name[:60]}...",
                'coordinates': f"{lat}, {lng}",
                'accuracy': 'High (±50m)'
            }
        else:
            return {
                'service': 'LocationIQ',
                'status': 'FAIL',
                'message': "❌ No results found",
                'accuracy': 'N/A'
            }
            
    except Exception as e:
        return {
            'service': 'LocationIQ',
            'status': 'ERROR',
            'message': f"❌ Exception: {str(e)}",
            'accuracy': 'N/A'
        }

def test_nominatim_api() -> Dict:
    """Test OpenStreetMap Nominatim API"""
    try:
        url = "https://nominatim.openstreetmap.org/search"
        test_address = "Festival Walk, Kowloon Tong, Hong Kong"
        
        params = {
            'q': test_address,
            'format': 'json',
            'countrycodes': 'hk',
            'limit': 1
        }
        
        headers = {
            'User-Agent': 'Mannings-Store-Geocoding-Test/1.0 (test@example.com)'
        }
        
        response = requests.get(url, params=params, headers=headers, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        
        if data and isinstance(data, list) and len(data) > 0:
            result = data[0]
            lat, lng = result['lat'], result['lon']
            display_name = result.get('display_name', 'Unknown')
            
            return {
                'service': 'Nominatim (OSM)',
                'status': 'SUCCESS',
                'message': f"✅ Found: {display_name[:60]}...",
                'coordinates': f"{lat}, {lng}",
                'accuracy': 'Medium (±100m)'
            }
        else:
            return {
                'service': 'Nominatim (OSM)',
                'status': 'FAIL',
                'message': "❌ No results found",
                'accuracy': 'N/A'
            }
            
    except Exception as e:
        return {
            'service': 'Nominatim (OSM)',
            'status': 'ERROR',
            'message': f"❌ Exception: {str(e)}",
            'accuracy': 'N/A'
        }

def main():
    """Main test function"""
    print("🧪 Enhanced Geocoding API Test")
    print("=" * 50)
    print()
    
    # Test addresses
    print("📍 Test Address: Festival Walk, Kowloon Tong")
    print("🎯 Expected Location: ~22.337°N, 114.174°E")
    print()
    
    # Check API keys
    print("🔑 API Key Status:")
    google_key = os.getenv('GOOGLE_MAPS_API_KEY')
    locationiq_key = os.getenv('LOCATIONIQ_API_KEY')
    print(f"  Google Maps: {'✅ Set' if google_key else '❌ Not set'}")
    print(f"  LocationIQ:  {'✅ Set' if locationiq_key else '❌ Not set'}")
    print()
    
    # Run tests
    tests = [
        test_google_maps_api,
        test_csdi_api,
        test_locationiq_api,
        test_nominatim_api
    ]
    
    results = []
    
    for test_func in tests:
        print(f"Testing {test_func.__name__.replace('test_', '').replace('_api', '').title()}...")
        result = test_func()
        results.append(result)
        time.sleep(1)  # Rate limiting
    
    # Display results
    print("\n📊 Test Results:")
    print("=" * 80)
    
    for result in results:
        status_icon = {
            'SUCCESS': '✅',
            'FAIL': '❌',
            'ERROR': '⚠️',
            'SKIP': '⏭️'
        }.get(result['status'], '❓')
        
        print(f"{status_icon} {result['service']:<20} | {result['status']:<8} | {result['accuracy']}")
        print(f"   {result['message']}")
        if 'coordinates' in result and result['status'] == 'SUCCESS':
            print(f"   📍 Coordinates: {result['coordinates']}")
        print()
    
    # Summary
    successful_tests = sum(1 for r in results if r['status'] == 'SUCCESS')
    total_tests = len([r for r in results if r['status'] != 'SKIP'])
    
    print("📈 Summary:")
    print(f"  Successful APIs: {successful_tests}/{total_tests}")
    
    if successful_tests == 0:
        print("  ⚠️  No APIs are working. Check network connection and API keys.")
    elif successful_tests < total_tests:
        print("  ✅ Some APIs are working. Enhanced geocoding will use available APIs.")
    else:
        print("  🎉 All APIs are working! Enhanced geocoding will achieve best results.")
    
    print("\n🚀 Next Steps:")
    if google_key:
        print("  1. ✅ Google Maps API ready - expect highest accuracy")
    else:
        print("  1. 💡 Consider getting Google Maps API key for best results")
        print("     Visit: https://console.cloud.google.com/")
    
    if locationiq_key:
        print("  2. ✅ LocationIQ API ready - good free backup")
    else:
        print("  2. 💡 Consider getting LocationIQ API key for free high-quality geocoding")
        print("     Visit: https://locationiq.com/")
    
    print("  3. 🏃 Run: python scripts/geocode_stores_enhanced.py")
    print("  4. 📊 Check results in: data/dfi/processed/store_coordinates_enhanced.csv")

if __name__ == "__main__":
    main()