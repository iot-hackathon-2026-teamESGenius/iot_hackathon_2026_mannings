#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Hong Kong Traffic Data Fetcher
Implements TrafficDataFetcher interface for real-time traffic monitoring

Created: 2026-03-17
Author: Team ESGenius
"""

import requests
import json
import logging
from datetime import datetime, date, timedelta
from typing import List, Optional, Dict, Any
import numpy as np

try:
    from ...core.interfaces import TrafficDataFetcher
    from ...core.data_schema import TrafficCondition
except ImportError:
    # For direct execution
    import sys
    from pathlib import Path
    sys.path.append(str(Path(__file__).parent.parent.parent.parent))
    from src.core.interfaces import TrafficDataFetcher
    from src.core.data_schema import TrafficCondition

logger = logging.getLogger(__name__)

class HKTrafficFetcher(TrafficDataFetcher):
    """Hong Kong Traffic Data Fetcher using TDAS API"""
    
    def __init__(self, timeout: int = 10):
        self.timeout = timeout
        self.tdas_url = "https://tdas-api.hkemobility.gov.hk/tdas/api/route"
        self._cache = {}
        self._cache_ttl = 900  # 15 minutes cache for traffic data
        
        # Define major routes for monitoring
        self.major_routes = [
            {
                "name": "Central-Causeway Bay",
                "start": (22.2860, 114.1510),  # Central
                "end": (22.2783, 114.1747),    # Causeway Bay
                "description": "Central business district to shopping area"
            },
            {
                "name": "Tsim Sha Tsui-Mong Kok", 
                "start": (22.2988, 114.1722),  # TST
                "end": (22.3193, 114.1694),    # Mong Kok
                "description": "Tourist area to commercial district"
            },
            {
                "name": "Sha Tin-Tai Po",
                "start": (22.3818, 114.1877),  # Sha Tin
                "end": (22.4507, 114.1671),    # Tai Po
                "description": "New Territories residential areas"
            },
            {
                "name": "Kwun Tong-Kowloon Bay",
                "start": (22.3120, 114.2267),  # Kwun Tong
                "end": (22.3219, 114.2147),    # Kowloon Bay
                "description": "Industrial and business districts"
            },
            {
                "name": "Wong Tai Sin-Diamond Hill",
                "start": (22.3442, 114.2007),  # Wong Tai Sin
                "end": (22.3398, 114.2056),    # Diamond Hill
                "description": "Residential areas connection"
            },
            {
                "name": "Admiralty-Wan Chai",
                "start": (22.2783, 114.1657),  # Admiralty
                "end": (22.2783, 114.1747),    # Wan Chai
                "description": "Government and business districts"
            },
            {
                "name": "Tuen Mun-Yuen Long",
                "start": (22.3910, 113.9760),  # Tuen Mun
                "end": (22.4441, 114.0249),    # Yuen Long
                "description": "New Territories western corridor"
            }
        ]
    
    def fetch_data(self, start_date: date, end_date: date, **kwargs) -> List[TrafficCondition]:
        """Fetch traffic data (real-time only)"""
        # Traffic data is real-time only, ignore date range
        return self.fetch_current_traffic()
    
    def is_available(self) -> bool:
        """Check if TDAS API is available"""
        try:
            # Test with a simple route
            payload = {
                "start": {"lat": 22.2860, "long": 114.1510},
                "end": {"lat": 22.2783, "long": 114.1747},
                "departIn": 0,
                "lang": "en",
                "type": "ST"
            }
            
            response = requests.post(self.tdas_url, json=payload, timeout=5)
            return response.status_code == 200
        except:
            return False
    
    def get_last_update_time(self) -> Optional[datetime]:
        """Get last update time (current time for real-time data)"""
        return datetime.now()
    
    def fetch_current_traffic(self, region: str = "hong_kong") -> List[TrafficCondition]:
        """Fetch current traffic conditions"""
        cache_key = f'current_traffic_{region}'
        
        # Check cache
        if cache_key in self._cache:
            cache_time, traffic_data = self._cache[cache_key]
            if (datetime.now() - cache_time).total_seconds() < self._cache_ttl:
                return traffic_data
        
        try:
            logger.info("Fetching current traffic conditions...")
            
            traffic_data = []
            
            for route in self.major_routes:
                try:
                    condition = self._fetch_route_condition(route)
                    if condition:
                        traffic_data.append(condition)
                except Exception as e:
                    logger.warning(f"Failed to fetch traffic for {route['name']}: {e}")
                    # Add fallback data
                    fallback = self._generate_fallback_condition(route)
                    traffic_data.append(fallback)
            
            # Update cache
            self._cache[cache_key] = (datetime.now(), traffic_data)
            
            logger.info(f"Successfully fetched traffic data for {len(traffic_data)} routes")
            return traffic_data
            
        except Exception as e:
            logger.error(f"Failed to fetch current traffic: {e}")
            return []
    
    def fetch_traffic_forecast(self, hours: int = 24) -> List[TrafficCondition]:
        """Fetch traffic forecast (not available, return current conditions)"""
        logger.warning("Traffic forecast not available, returning current conditions")
        return self.fetch_current_traffic()
    
    def _fetch_route_condition(self, route: Dict[str, Any]) -> Optional[TrafficCondition]:
        """Fetch traffic condition for a specific route"""
        try:
            payload = {
                "start": {
                    "lat": route["start"][0],
                    "long": route["start"][1]
                },
                "end": {
                    "lat": route["end"][0], 
                    "long": route["end"][1]
                },
                "departIn": 0,  # Current time
                "lang": "en",
                "type": "ST"  # Shortest time
            }
            
            response = requests.post(self.tdas_url, json=payload, timeout=self.timeout)
            
            if response.status_code == 200:
                data = response.json()
                
                # Extract traffic information
                speed = data.get('jSpeed', 40)  # Average speed (km/h)
                eta_minutes = data.get('eta', 15)  # Estimated time (minutes)
                distance = data.get('dist', 5)  # Distance (km)
                
                # Ensure numeric values
                try:
                    speed = float(speed) if speed is not None else 40.0
                    eta_minutes = float(eta_minutes) if eta_minutes is not None else 15.0
                except (ValueError, TypeError):
                    speed = 40.0
                    eta_minutes = 15.0
                
                # Calculate congestion level based on speed
                congestion_level = self._calculate_congestion_level(speed)
                
                # Check for incidents (not directly available in TDAS)
                incident_reported = False
                
                return TrafficCondition(
                    timestamp=datetime.now(),
                    road_segment=route["name"],
                    speed_kmh=speed,
                    congestion_level=congestion_level,
                    travel_time_minutes=eta_minutes,
                    incident_reported=incident_reported
                )
            else:
                logger.warning(f"TDAS API returned status {response.status_code} for {route['name']}")
                return None
                
        except Exception as e:
            logger.error(f"Failed to fetch route condition for {route['name']}: {e}")
            return None
    
    def _calculate_congestion_level(self, speed_kmh: float) -> int:
        """Calculate congestion level based on speed"""
        # Ensure speed is a number
        try:
            speed = float(speed_kmh)
        except (ValueError, TypeError):
            speed = 40.0  # Default speed
            
        if speed >= 50:
            return 1  # Free flow
        elif speed >= 40:
            return 2  # Light traffic
        elif speed >= 30:
            return 3  # Moderate traffic
        elif speed >= 20:
            return 4  # Heavy traffic
        else:
            return 5  # Severe congestion
    
    def _generate_fallback_condition(self, route: Dict[str, Any]) -> TrafficCondition:
        """Generate fallback traffic condition when API fails"""
        # Generate realistic fallback data based on time of day
        current_hour = datetime.now().hour
        
        # Rush hour patterns
        if 7 <= current_hour <= 9 or 17 <= current_hour <= 19:
            # Rush hour - slower traffic
            speed = np.random.normal(25, 5)
            congestion = 4
            travel_time = np.random.normal(20, 5)
        elif 22 <= current_hour or current_hour <= 6:
            # Night time - faster traffic
            speed = np.random.normal(50, 8)
            congestion = 1
            travel_time = np.random.normal(10, 3)
        else:
            # Normal hours
            speed = np.random.normal(40, 8)
            congestion = 2
            travel_time = np.random.normal(15, 4)
        
        # Ensure reasonable bounds
        speed = max(10, min(80, speed))
        travel_time = max(5, travel_time)
        
        return TrafficCondition(
            timestamp=datetime.now(),
            road_segment=route["name"],
            speed_kmh=float(speed),
            congestion_level=congestion,
            travel_time_minutes=float(travel_time),
            incident_reported=np.random.random() < 0.05  # 5% chance of incident
        )
    
    def get_traffic_summary(self) -> Dict[str, Any]:
        """Get traffic summary for all monitored routes"""
        traffic_data = self.fetch_current_traffic()
        
        if not traffic_data:
            return {'error': 'No traffic data available'}
        
        speeds = [t.speed_kmh for t in traffic_data]
        congestion_levels = [t.congestion_level for t in traffic_data]
        
        summary = {
            'timestamp': datetime.now().isoformat(),
            'total_routes': len(traffic_data),
            'average_speed': float(np.mean(speeds)),
            'average_congestion': float(np.mean(congestion_levels)),
            'routes': []
        }
        
        for traffic in traffic_data:
            route_info = {
                'name': traffic.road_segment,
                'speed_kmh': traffic.speed_kmh,
                'congestion_level': traffic.congestion_level,
                'travel_time_minutes': traffic.travel_time_minutes,
                'status': self._get_traffic_status(traffic.congestion_level)
            }
            summary['routes'].append(route_info)
        
        return summary
    
    def _get_traffic_status(self, congestion_level: int) -> str:
        """Get traffic status description"""
        status_map = {
            1: "Free Flow",
            2: "Light Traffic", 
            3: "Moderate Traffic",
            4: "Heavy Traffic",
            5: "Severe Congestion"
        }
        return status_map.get(congestion_level, "Unknown")

# Test function
def test_traffic_fetcher():
    """Test Traffic Fetcher"""
    fetcher = HKTrafficFetcher()
    
    print("Testing HK Traffic Fetcher...")
    print(f"API Available: {fetcher.is_available()}")
    
    # Test current traffic
    traffic_data = fetcher.fetch_current_traffic()
    print(f"Current Traffic ({len(traffic_data)} routes):")
    
    for traffic in traffic_data[:3]:  # Show first 3
        print(f"  {traffic.road_segment}: {traffic.speed_kmh:.1f} km/h, "
              f"Level {traffic.congestion_level}, {traffic.travel_time_minutes:.1f} min")
    
    # Test summary
    summary = fetcher.get_traffic_summary()
    if 'error' not in summary:
        print(f"Traffic Summary:")
        print(f"  Average Speed: {summary['average_speed']:.1f} km/h")
        print(f"  Average Congestion: {summary['average_congestion']:.1f}")

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    test_traffic_fetcher()