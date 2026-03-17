#!/usr/bin/env python3
"""
Enhanced Store Geocoding Script v2 - With Proper HK80 Coordinate Conversion
===========================================================================

This script provides enhanced geocoding for Mannings store locations using multiple APIs
with proper Hong Kong 1980 Grid to WGS84 coordinate conversion.

Supported APIs (in priority order):
1. Google Maps Geocoding API (most accurate, requires API key)
2. Hong Kong CSDI Location Search API (free, government official, HK80 coordinates)
3. LocationIQ API (free tier: 5000 requests/day)
4. OpenStreetMap Nominatim API (free, no limits but rate limited)
5. District center fallback (existing method)

Author: AI Assistant
Date: 2026-03-17
Version: 2.0 - Added HK80 coordinate conversion
"""

import pandas as pd
import requests
import time
import json
import os
from typing import Dict, List, Tuple, Optional
import logging
from urllib.parse import quote

# Try to import coordinate conversion libraries
try:
    from pyproj import Transformer
    HAS_PYPROJ = True
except ImportError:
    HAS_PYPROJ = False
    print("⚠️ pyproj not installed. Install with: pip install pyproj")

try:
    import hk80
    HAS_HK80 = True
except ImportError:
    HAS_HK80 = False
    print("💡 hk80 library not installed. Install with: pip install hk80")

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class CoordinateConverter:
    """Handle coordinate conversion between HK80 and WGS84"""
    
    def __init__(self):
        self.transformer = None
        if HAS_PYPROJ:
            try:
                # Create transformer from HK80 (EPSG:2326) to WGS84 (EPSG:4326)
                self.transformer = Transformer.from_crs("EPSG:2326", "EPSG:4326", always_xy=True)
                logger.info("✅ PyProj transformer initialized for HK80 to WGS84 conversion")
            except Exception as e:
                logger.warning(f"⚠️ Failed to initialize PyProj transformer: {e}")
    
    def hk80_to_wgs84(self, x: float, y: float) -> Tuple[float, float]:
        """
        Convert Hong Kong 1980 Grid coordinates to WGS84
        
        Args:
            x: Easting (Hong Kong Grid)
            y: Northing (Hong Kong Grid)
            
        Returns:
            Tuple of (latitude, longitude) in WGS84
        """
        if self.transformer:
            try:
                # PyProj returns (longitude, latitude) when always_xy=True
                lng, lat = self.transformer.transform(x, y)
                return (lat, lng)
            except Exception as e:
                logger.warning(f"PyProj conversion failed: {e}")
        
        # Fallback to approximate conversion if PyProj fails
        return self._approximate_conversion(x, y)
    
    def _approximate_conversion(self, x: float, y: float) -> Tuple[float, float]:
        """
        Approximate conversion from HK80 to WGS84 (less accurate)
        Based on typical Hong Kong coordinate ranges
        """
        # Hong Kong approximate bounds in HK80:
        # X (Easting): ~800,000 to ~860,000
        # Y (Northing): ~810,000 to ~850,000
        
        # Approximate conversion factors (for reference only)
        # These are rough estimates and should not be used for precise applications
        lat = 22.0 + (y - 815000) / 110000  # Rough latitude conversion
        lng = 114.0 + (x - 830000) / 85000   # Rough longitude conversion
        
        # Clamp to reasonable Hong Kong bounds
        lat = max(22.15, min(22.58, lat))  # Hong Kong latitude range
        lng = max(113.83, min(114.44, lng))  # Hong Kong longitude range
        
        logger.warning(f"Using approximate conversion: HK80({x}, {y}) -> WGS84({lat:.6f}, {lng:.6f})")
        return (lat, lng)

class EnhancedGeocoder:
    """Enhanced geocoding class with multiple API support and coordinate conversion"""
    
    def __init__(self):
        self.google_api_key = os.getenv('GOOGLE_MAPS_API_KEY')
        self.locationiq_api_key = os.getenv('LOCATIONIQ_API_KEY')
        self.converter = CoordinateConverter()
        
        # API endpoints
        self.google_url = "https://maps.googleapis.com/maps/api/geocode/json"
        self.csdi_url = "https://www.map.gov.hk/gs/api/v1.0.0/locationSearch"
        self.locationiq_url = "https://us1.locationiq.com/v1/search.php"
        self.nominatim_url = "https://nominatim.openstreetmap.org/search"
        
        # District centers as fallback
        self.district_centers = {
            'Central & Western': (22.284, 114.158),
            'Wan Chai': (22.277, 114.173),
            'Eastern': (22.281, 114.225),
            'Southern': (22.246, 114.169),
            'Yau Tsim Mong': (22.304, 114.172),
            'Sham Shui Po': (22.330, 114.162),
            'Kowloon City': (22.328, 114.191),
            'Wong Tai Sin': (22.342, 114.195),
            'Kwun Tong': (22.312, 114.226),
            'Tsuen Wan': (22.371, 114.113),
            'Tuen Mun': (22.391, 114.003),
            'Yuen Long': (22.445, 114.034),
            'North': (22.494, 114.138),
            'Tai Po': (22.451, 114.171),
            'Sha Tin': (22.387, 114.195),
            'Sai Kung': (22.381, 114.274),
            'Kwai Tsing': (22.357, 114.131),
            'Island': (22.266, 113.944)  # For airport and outlying islands
        }
        
        # Rate limiting
        self.last_request_time = {}
        self.min_intervals = {
            'google': 0.1,      # 10 requests per second
            'csdi': 0.5,        # 2 requests per second (conservative)
            'locationiq': 1.0,  # 1 request per second for free tier
            'nominatim': 1.0    # 1 request per second (Nominatim policy)
        }
        
        # Statistics
        self.stats = {
            'google_success': 0,
            'csdi_success': 0,
            'locationiq_success': 0,
            'nominatim_success': 0,
            'district_fallback': 0,
            'total_failed': 0
        }
    
    def _rate_limit(self, api_name: str):
        """Implement rate limiting for API calls"""
        current_time = time.time()
        if api_name in self.last_request_time:
            time_since_last = current_time - self.last_request_time[api_name]
            min_interval = self.min_intervals.get(api_name, 1.0)
            if time_since_last < min_interval:
                sleep_time = min_interval - time_since_last
                time.sleep(sleep_time)
        self.last_request_time[api_name] = time.time()
    
    def _clean_address(self, address: str) -> str:
        """Clean and prepare address for geocoding"""
        # Remove extra whitespace and normalize
        address = ' '.join(address.split())
        
        # Add Hong Kong if not present
        if 'Hong Kong' not in address and 'H.K.' not in address:
            address += ', Hong Kong'
        
        return address
    
    def geocode_google(self, address: str) -> Optional[Tuple[float, float, str]]:
        """Geocode using Google Maps API"""
        if not self.google_api_key:
            return None
        
        try:
            self._rate_limit('google')
            
            params = {
                'address': self._clean_address(address),
                'key': self.google_api_key,
                'region': 'hk',
                'language': 'en'
            }
            
            response = requests.get(self.google_url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            
            if data['status'] == 'OK' and data['results']:
                location = data['results'][0]['geometry']['location']
                formatted_address = data['results'][0]['formatted_address']
                self.stats['google_success'] += 1
                return (location['lat'], location['lng'], f"SUCCESS_GOOGLE: {formatted_address}")
            
        except Exception as e:
            logger.warning(f"Google API error for '{address}': {e}")
        
        return None
    
    def geocode_csdi(self, address: str) -> Optional[Tuple[float, float, str]]:
        """Geocode using Hong Kong CSDI API with proper coordinate conversion"""
        try:
            self._rate_limit('csdi')
            
            params = {
                'q': self._clean_address(address)
            }
            
            response = requests.get(self.csdi_url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            
            if isinstance(data, list) and data:
                # Use first result (best match)
                result = data[0]
                
                if 'x' in result and 'y' in result:
                    # Convert from HK80 to WGS84
                    hk80_x, hk80_y = result['x'], result['y']
                    lat, lng = self.converter.hk80_to_wgs84(hk80_x, hk80_y)
                    
                    # Get location name
                    name_en = result.get('nameEN', result.get('nameZH', 'CSDI Result'))
                    address_en = result.get('addressEN', result.get('addressZH', ''))
                    
                    self.stats['csdi_success'] += 1
                    return (lat, lng, f"SUCCESS_CSDI: {name_en} - {address_en}")
            
        except Exception as e:
            logger.warning(f"CSDI API error for '{address}': {e}")
        
        return None
    
    def geocode_locationiq(self, address: str) -> Optional[Tuple[float, float, str]]:
        """Geocode using LocationIQ API"""
        if not self.locationiq_api_key:
            return None
        
        try:
            self._rate_limit('locationiq')
            
            params = {
                'key': self.locationiq_api_key,
                'q': self._clean_address(address),
                'format': 'json',
                'countrycodes': 'hk',
                'limit': 1,
                'addressdetails': 1
            }
            
            response = requests.get(self.locationiq_url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            
            if data and isinstance(data, list) and len(data) > 0:
                result = data[0]
                lat, lng = float(result['lat']), float(result['lon'])
                display_name = result.get('display_name', 'LocationIQ Result')
                self.stats['locationiq_success'] += 1
                return (lat, lng, f"SUCCESS_LOCATIONIQ: {display_name}")
            
        except Exception as e:
            logger.warning(f"LocationIQ API error for '{address}': {e}")
        
        return None
    
    def geocode_nominatim(self, address: str) -> Optional[Tuple[float, float, str]]:
        """Geocode using OpenStreetMap Nominatim API"""
        try:
            self._rate_limit('nominatim')
            
            params = {
                'q': self._clean_address(address),
                'format': 'json',
                'countrycodes': 'hk',
                'limit': 1,
                'addressdetails': 1
            }
            
            headers = {
                'User-Agent': 'Mannings-Store-Geocoding/2.0 (enhanced-geocoding@example.com)'
            }
            
            response = requests.get(self.nominatim_url, params=params, headers=headers, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            
            if data and isinstance(data, list) and len(data) > 0:
                result = data[0]
                lat, lng = float(result['lat']), float(result['lon'])
                display_name = result.get('display_name', 'Nominatim Result')
                self.stats['nominatim_success'] += 1
                return (lat, lng, f"SUCCESS_NOMINATIM: {display_name}")
            
        except Exception as e:
            logger.warning(f"Nominatim API error for '{address}': {e}")
        
        return None
    
    def geocode_district_fallback(self, district: str) -> Tuple[float, float, str]:
        """Fallback to district center coordinates"""
        if district in self.district_centers:
            lat, lng = self.district_centers[district]
            self.stats['district_fallback'] += 1
            return (lat, lng, f"SUCCESS_DISTRICT_CENTER: {district} center approximation")
        else:
            # Default to Central if district not found
            lat, lng = self.district_centers['Central & Western']
            self.stats['district_fallback'] += 1
            return (lat, lng, f"SUCCESS_DISTRICT_CENTER: Default Central location (district '{district}' not found)")
    
    def geocode_address(self, address: str, district: str) -> Tuple[float, float, str, str]:
        """
        Geocode an address using multiple APIs in priority order
        
        Returns:
            Tuple of (latitude, longitude, status, note)
        """
        logger.info(f"Geocoding: {address}")
        
        # Try APIs in priority order
        apis = [
            ('Google Maps', self.geocode_google),
            ('CSDI', self.geocode_csdi),
            ('LocationIQ', self.geocode_locationiq),
            ('Nominatim', self.geocode_nominatim)
        ]
        
        for api_name, geocode_func in apis:
            result = geocode_func(address)
            if result:
                lat, lng, status = result
                logger.info(f"✅ Success with {api_name}: {lat:.6f}, {lng:.6f}")
                return (lat, lng, status.split(':')[0], status)
        
        # All APIs failed, use district fallback
        logger.warning(f"⚠️ All APIs failed for '{address}', using district fallback")
        lat, lng, status = self.geocode_district_fallback(district)
        return (lat, lng, status.split(':')[0], status)

def main():
    """Main execution function"""
    logger.info("🚀 Starting Enhanced Store Geocoding v2.0")
    
    # Check dependencies
    if not HAS_PYPROJ:
        logger.warning("⚠️ PyProj not installed. HK80 coordinate conversion will use approximate method.")
        logger.info("💡 Install with: pip install pyproj")
    
    # Check for API keys
    google_key = os.getenv('GOOGLE_MAPS_API_KEY')
    locationiq_key = os.getenv('LOCATIONIQ_API_KEY')
    
    logger.info("📋 API Key Status:")
    logger.info(f"  Google Maps: {'✅ Available' if google_key else '❌ Not set'}")
    logger.info(f"  LocationIQ: {'✅ Available' if locationiq_key else '❌ Not set'}")
    logger.info(f"  CSDI: ✅ Free (no key required)")
    logger.info(f"  Nominatim: ✅ Free (no key required)")
    
    # Load store data
    try:
        df = pd.read_csv('data/dfi/raw/dim_store.csv')
        logger.info(f"📊 Loaded {len(df)} stores from dim_store.csv")
    except FileNotFoundError:
        logger.error("❌ Could not find data/dfi/raw/dim_store.csv")
        return
    
    # Initialize geocoder
    geocoder = EnhancedGeocoder()
    
    # Prepare results
    results = []
    
    # Process each store
    for idx, row in df.iterrows():
        store_code = row['store \ncode']  # Note the column name format
        district = row['18 Districts']
        address = row['ADDRESS']
        
        logger.info(f"🏪 Processing store {idx+1}/{len(df)}: {store_code}")
        
        # Geocode the address
        lat, lng, status, note = geocoder.geocode_address(address, district)
        
        # Store result
        results.append({
            'store_code': store_code,
            'district': district,
            'address': address,
            'latitude': lat,
            'longitude': lng,
            'geocode_status': status,
            'note': note
        })
        
        # Progress update every 10 stores
        if (idx + 1) % 10 == 0:
            logger.info(f"📈 Progress: {idx+1}/{len(df)} stores processed")
    
    # Create results DataFrame
    results_df = pd.DataFrame(results)
    
    # Save results
    output_file = 'data/dfi/processed/store_coordinates_enhanced_v2.csv'
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    results_df.to_csv(output_file, index=False, encoding='utf-8')
    
    # Print statistics
    logger.info("📊 Geocoding Statistics:")
    logger.info(f"  Google Maps: {geocoder.stats['google_success']} successes")
    logger.info(f"  CSDI: {geocoder.stats['csdi_success']} successes")
    logger.info(f"  LocationIQ: {geocoder.stats['locationiq_success']} successes")
    logger.info(f"  Nominatim: {geocoder.stats['nominatim_success']} successes")
    logger.info(f"  District Fallback: {geocoder.stats['district_fallback']} used")
    
    # Calculate success rates
    total_stores = len(results_df)
    precise_geocoding = (geocoder.stats['google_success'] + 
                        geocoder.stats['csdi_success'] + 
                        geocoder.stats['locationiq_success'] + 
                        geocoder.stats['nominatim_success'])
    
    precise_rate = (precise_geocoding / total_stores) * 100
    
    logger.info(f"🎯 Results Summary:")
    logger.info(f"  Total stores: {total_stores}")
    logger.info(f"  Precise geocoding: {precise_geocoding} ({precise_rate:.1f}%)")
    logger.info(f"  District fallback: {geocoder.stats['district_fallback']} ({(geocoder.stats['district_fallback']/total_stores)*100:.1f}%)")
    logger.info(f"  Output saved to: {output_file}")
    
    logger.info("✅ Enhanced geocoding v2.0 completed!")

if __name__ == "__main__":
    main()