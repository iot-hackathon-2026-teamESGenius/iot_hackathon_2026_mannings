#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
HKO Weather Data Fetcher
Implements WeatherDataFetcher interface for Hong Kong Observatory API

Created: 2026-03-17
Author: Team ESGenius
"""

import requests
import logging
from datetime import datetime, date, timedelta
from typing import List, Optional, Dict, Any

try:
    from ...core.interfaces import WeatherDataFetcher
    from ...core.data_schema import WeatherData, WeatherCondition
except ImportError:
    # For direct execution
    import sys
    from pathlib import Path
    sys.path.append(str(Path(__file__).parent.parent.parent.parent))
    from src.core.interfaces import WeatherDataFetcher
    from src.core.data_schema import WeatherData, WeatherCondition

logger = logging.getLogger(__name__)

class HKOWeatherFetcher(WeatherDataFetcher):
    """Hong Kong Observatory Weather Data Fetcher"""
    
    def __init__(self, timeout: int = 10):
        self.timeout = timeout
        self.base_url = "https://data.weather.gov.hk/weatherAPI/opendata"
        self._cache = {}
        self._cache_ttl = 3600  # 1 hour cache
        
        # Weather icon to condition mapping
        self.icon_mapping = {
            50: WeatherCondition.SUNNY,      # 阳光充沛
            51: WeatherCondition.SUNNY,      # 间有阳光
            52: WeatherCondition.CLOUDY,     # 短暂阳光
            53: WeatherCondition.CLOUDY,     # 间有阳光，几阵骤雨
            54: WeatherCondition.CLOUDY,     # 短暂阳光，有骤雨
            60: WeatherCondition.CLOUDY,     # 多云
            61: WeatherCondition.CLOUDY,     # 密云
            62: WeatherCondition.RAINY,      # 微雨
            63: WeatherCondition.RAINY,      # 雨
            64: WeatherCondition.STORMY,     # 大雨
            65: WeatherCondition.STORMY,     # 雷暴
            70: WeatherCondition.SUNNY,      # 天色良好
            71: WeatherCondition.SUNNY,      # 天色良好
            72: WeatherCondition.SUNNY,      # 天色良好
            73: WeatherCondition.SUNNY,      # 天色良好
            74: WeatherCondition.SUNNY,      # 天色良好
            75: WeatherCondition.SUNNY,      # 天色良好
            76: WeatherCondition.CLOUDY,     # 大致多云
            77: WeatherCondition.CLOUDY,     # 天色大致良好
            80: WeatherCondition.SUNNY,      # 多云，天气炎热
            81: WeatherCondition.SUNNY,      # 天晴，天气炎热
            82: WeatherCondition.SUNNY,      # 阳光充沛，天气炎热
            83: WeatherCondition.SUNNY,      # 天气炎热
            84: WeatherCondition.SUNNY,      # 天气炎热
            85: WeatherCondition.CLOUDY,     # 天气炎热，有几阵骤雨
            90: WeatherCondition.SUNNY,      # 天气炎热
            91: WeatherCondition.CLOUDY,     # 寒冷
            92: WeatherCondition.CLOUDY,     # 天气寒冷
            93: WeatherCondition.CLOUDY,     # 寒冷及干燥
        }
    
    def fetch_data(self, start_date: date, end_date: date, **kwargs) -> List[WeatherData]:
        """Fetch weather data for date range"""
        try:
            # For HKO, we can only get current + 9-day forecast
            forecasts = self.fetch_weather_forecast(days=9)
            
            # Filter by date range
            filtered = []
            for forecast in forecasts:
                if start_date <= forecast.date <= end_date:
                    filtered.append(forecast)
            
            return filtered
        except Exception as e:
            logger.error(f"Failed to fetch weather data: {e}")
            return []
    
    def is_available(self) -> bool:
        """Check if HKO API is available"""
        try:
            url = f"{self.base_url}/weather.php?dataType=rhrread&lang=en"
            response = requests.get(url, timeout=5)
            return response.status_code == 200
        except:
            return False
    
    def get_last_update_time(self) -> Optional[datetime]:
        """Get last update time from HKO"""
        try:
            url = f"{self.base_url}/weather.php?dataType=rhrread&lang=en"
            response = requests.get(url, timeout=self.timeout)
            response.raise_for_status()
            
            data = response.json()
            update_time_str = data.get('updateTime', '')
            
            if update_time_str:
                return datetime.strptime(update_time_str, '%Y-%m-%dT%H:%M:%S+08:00')
        except Exception as e:
            logger.error(f"Failed to get last update time: {e}")
        
        return None
    
    def fetch_current_weather(self) -> WeatherData:
        """Fetch current weather conditions"""
        try:
            url = f"{self.base_url}/weather.php?dataType=rhrread&lang=en"
            response = requests.get(url, timeout=self.timeout)
            response.raise_for_status()
            
            data = response.json()
            
            # Parse temperature (Hong Kong Observatory station)
            temperature = 25.0  # default
            for temp_item in data.get('temperature', {}).get('data', []):
                if temp_item.get('place') == 'Hong Kong Observatory':
                    temperature = float(temp_item.get('value', 25.0))
                    break
            
            # Parse humidity
            humidity_data = data.get('humidity', {}).get('data', [])
            humidity = float(humidity_data[0].get('value', 70)) if humidity_data else 70.0
            
            # Parse weather icon
            weather_icon = data.get('icon', [50])[0] if data.get('icon') else 50
            condition = self.icon_mapping.get(weather_icon, WeatherCondition.CLOUDY)
            
            # Parse rainfall
            rainfall_data = data.get('rainfall', {}).get('data', [])
            rainfall = 0.0
            if rainfall_data:
                rainfall = float(rainfall_data[0].get('max', 0))
            
            return WeatherData(
                date=date.today(),
                temperature_high=temperature,
                temperature_low=temperature,  # Current temp as both high/low
                humidity=humidity,
                condition=condition,
                rainfall=rainfall
            )
            
        except Exception as e:
            logger.error(f"Failed to fetch current weather: {e}")
            # Return default weather data
            return WeatherData(
                date=date.today(),
                temperature_high=25.0,
                temperature_low=20.0,
                humidity=70.0,
                condition=WeatherCondition.CLOUDY,
                rainfall=0.0
            )
    
    def fetch_weather_forecast(self, days: int = 7) -> List[WeatherData]:
        """Fetch weather forecast for specified days"""
        try:
            url = f"{self.base_url}/weather.php?dataType=fnd&lang=en"
            response = requests.get(url, timeout=self.timeout)
            response.raise_for_status()
            
            data = response.json()
            forecasts = []
            
            for item in data.get('weatherForecast', []):
                try:
                    # Parse date
                    date_str = item.get('forecastDate', '')
                    forecast_date = datetime.strptime(date_str, '%Y%m%d').date()
                    
                    # Parse temperatures
                    temp_max = float(item.get('forecastMaxtemp', {}).get('value', 30))
                    temp_min = float(item.get('forecastMintemp', {}).get('value', 20))
                    
                    # Parse humidity
                    humidity_max = int(item.get('forecastMaxrh', {}).get('value', 90))
                    humidity_min = int(item.get('forecastMinrh', {}).get('value', 60))
                    humidity_avg = (humidity_max + humidity_min) / 2
                    
                    # Parse weather condition
                    weather_icon = item.get('ForecastIcon', 50)
                    condition = self.icon_mapping.get(weather_icon, WeatherCondition.CLOUDY)
                    
                    forecast = WeatherData(
                        date=forecast_date,
                        temperature_high=temp_max,
                        temperature_low=temp_min,
                        humidity=humidity_avg,
                        condition=condition,
                        rainfall=0.0  # HKO forecast doesn't include specific rainfall amounts
                    )
                    forecasts.append(forecast)
                    
                    # Limit to requested days
                    if len(forecasts) >= days:
                        break
                        
                except Exception as e:
                    logger.warning(f"Failed to parse forecast item: {e}")
                    continue
            
            return forecasts
            
        except Exception as e:
            logger.error(f"Failed to fetch weather forecast: {e}")
            return []
    
    def fetch_historical_weather(self, start_date: date, end_date: date) -> List[WeatherData]:
        """Fetch historical weather data (limited for HKO)"""
        logger.warning("HKO API does not provide historical weather data")
        return []

# Test function
def test_hko_fetcher():
    """Test HKO Weather Fetcher"""
    fetcher = HKOWeatherFetcher()
    
    print("Testing HKO Weather Fetcher...")
    print(f"API Available: {fetcher.is_available()}")
    
    # Test current weather
    current = fetcher.fetch_current_weather()
    print(f"Current Weather: {current.temperature_high}°C, {current.condition.value}")
    
    # Test forecast
    forecasts = fetcher.fetch_weather_forecast(days=5)
    print(f"Forecast ({len(forecasts)} days):")
    for f in forecasts:
        print(f"  {f.date}: {f.temperature_low}-{f.temperature_high}°C, {f.condition.value}")

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    test_hko_fetcher()