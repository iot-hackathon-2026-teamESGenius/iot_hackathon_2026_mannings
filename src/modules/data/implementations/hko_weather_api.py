"""
香港天文台 (HKO) 开放数据API接口
获取天气预报、当前天气、天气警告等数据

Author: 谭聪/李泰一 (Data Engineering)
Date: 2026-03-12

API文档: https://www.hko.gov.hk/en/abouthko/opendata_intro.htm
"""

import requests
from datetime import date, datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
import logging

from src.core.data_schema import WeatherDataSchema, WeatherCondition

logger = logging.getLogger(__name__)


# HKO API 端点
HKO_BASE_URL = "https://data.weather.gov.hk/weatherAPI/opendata"

# API 端点映射
API_ENDPOINTS = {
    'current_weather': f"{HKO_BASE_URL}/weather.php?dataType=rhrread&lang=en",
    'forecast_9day': f"{HKO_BASE_URL}/weather.php?dataType=fnd&lang=en",
    'forecast_local': f"{HKO_BASE_URL}/weather.php?dataType=flw&lang=en",
    'warning_summary': f"{HKO_BASE_URL}/weather.php?dataType=warnsum&lang=en",
    'warning_info': f"{HKO_BASE_URL}/weather.php?dataType=warningInfo&lang=en",
}

# 天气图标到天气状况映射
WEATHER_ICON_MAPPING = {
    50: WeatherCondition.SUNNY,      # 阳光充沛
    51: WeatherCondition.SUNNY,      # 间有阳光
    52: WeatherCondition.CLOUDY,     # 短暂阳光
    53: WeatherCondition.CLOUDY,     # 间有阳光，几阵骤雨
    54: WeatherCondition.CLOUDY,     # 短暂阳光，有骤雨
    60: WeatherCondition.CLOUDY,     # 多云
    61: WeatherCondition.CLOUDY,     # 密云
    62: WeatherCondition.RAINY,      # 微雨
    63: WeatherCondition.RAINY,      # 雨
    64: WeatherCondition.HEAVY_RAIN, # 大雨
    65: WeatherCondition.HEAVY_RAIN, # 雷暴
    70: WeatherCondition.SUNNY,      # 天色良好
    71: WeatherCondition.SUNNY,      # 天色良好
    72: WeatherCondition.SUNNY,      # 天色良好
    73: WeatherCondition.SUNNY,      # 天色良好
    74: WeatherCondition.SUNNY,      # 天色良好
    75: WeatherCondition.SUNNY,      # 天色良好
    76: WeatherCondition.CLOUDY,     # 大致多云
    77: WeatherCondition.CLOUDY,     # 天色大致良好
    80: WeatherCondition.HOT,        # 多云，天气炎热
    81: WeatherCondition.HOT,        # 天晴，天气炎热
    82: WeatherCondition.HOT,        # 阳光充沛，天气炎热
    83: WeatherCondition.HOT,        # 天气炎热
    84: WeatherCondition.HOT,        # 天气炎热
    85: WeatherCondition.HOT,        # 天气炎热，有几阵骤雨
    90: WeatherCondition.HOT,        # 天气炎热
    91: WeatherCondition.COLD,       # 寒冷
    92: WeatherCondition.COLD,       # 天气寒冷
    93: WeatherCondition.COLD,       # 寒冷及干燥
}


@dataclass
class HKOCurrentWeather:
    """HKO当前天气数据"""
    update_time: datetime
    temperature: float          # 气温 (°C)
    humidity: int               # 相对湿度 (%)
    weather_icon: int           # 天气图标代码
    weather_condition: str      # 天气状况描述
    uv_index: Optional[float] = None
    rainfall: Optional[float] = None  # 过去一小时降雨量


@dataclass
class HKOForecast:
    """HKO天气预报数据"""
    forecast_date: date
    week: str                   # 星期几
    weather_icon: int           # 天气图标代码
    forecast_wind: str          # 风向风力
    forecast_weather: str       # 天气预报描述
    temp_min: float             # 最低温度
    temp_max: float             # 最高温度
    humidity_min: int           # 最低湿度
    humidity_max: int           # 最高湿度


class HKOWeatherAPI:
    """
    香港天文台开放数据API客户端
    """
    
    def __init__(self, timeout: int = 10):
        self.timeout = timeout
        self._cache = {}
        self._cache_ttl = 3600  # 缓存1小时
    
    def _make_request(self, endpoint_key: str) -> Dict:
        """发送API请求"""
        url = API_ENDPOINTS.get(endpoint_key)
        if not url:
            raise ValueError(f"Unknown endpoint: {endpoint_key}")
        
        try:
            response = requests.get(url, timeout=self.timeout)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"HKO API request failed: {e}")
            raise
    
    def get_current_weather(self) -> HKOCurrentWeather:
        """
        获取当前天气状况
        API: rhrread (Regional Weather)
        """
        data = self._make_request('current_weather')
        
        # 解析更新时间
        update_time_str = data.get('updateTime', '')
        try:
            update_time = datetime.strptime(update_time_str, '%Y-%m-%dT%H:%M:%S+08:00')
        except:
            update_time = datetime.now()
        
        # 获取温度 (香港天文台站点)
        temperature = None
        for temp_item in data.get('temperature', {}).get('data', []):
            if temp_item.get('place') == 'Hong Kong Observatory':
                temperature = temp_item.get('value')
                break
        if temperature is None and data.get('temperature', {}).get('data'):
            temperature = data['temperature']['data'][0].get('value')
        
        # 获取湿度
        humidity = data.get('humidity', {}).get('data', [{}])[0].get('value', 0)
        
        # 获取天气图标
        weather_icon = data.get('icon', [50])[0] if data.get('icon') else 50
        
        # 获取天气描述
        weather_condition = data.get('generalSituation', 'Unknown')
        
        # 获取UV指数
        uv_data = data.get('uvindex', {}).get('data', [])
        uv_index = uv_data[0].get('value') if uv_data else None
        
        # 获取降雨量
        rainfall = data.get('rainfall', {}).get('data', [{}])[0].get('max', 0)
        
        return HKOCurrentWeather(
            update_time=update_time,
            temperature=float(temperature) if temperature else 25.0,
            humidity=int(humidity) if humidity else 70,
            weather_icon=weather_icon,
            weather_condition=weather_condition,
            uv_index=float(uv_index) if uv_index else None,
            rainfall=float(rainfall) if rainfall else None
        )
    
    def get_9day_forecast(self) -> List[HKOForecast]:
        """
        获取9天天气预报
        API: fnd (9-day Weather Forecast)
        """
        data = self._make_request('forecast_9day')
        
        forecasts = []
        for item in data.get('weatherForecast', []):
            try:
                # 解析日期
                date_str = item.get('forecastDate', '')
                forecast_date = datetime.strptime(date_str, '%Y%m%d').date()
                
                forecast = HKOForecast(
                    forecast_date=forecast_date,
                    week=item.get('week', ''),
                    weather_icon=item.get('ForecastIcon', 50),
                    forecast_wind=item.get('forecastWind', ''),
                    forecast_weather=item.get('forecastWeather', ''),
                    temp_min=float(item.get('forecastMintemp', {}).get('value', 20)),
                    temp_max=float(item.get('forecastMaxtemp', {}).get('value', 30)),
                    humidity_min=int(item.get('forecastMinrh', {}).get('value', 60)),
                    humidity_max=int(item.get('forecastMaxrh', {}).get('value', 90))
                )
                forecasts.append(forecast)
            except Exception as e:
                logger.warning(f"Failed to parse forecast item: {e}")
                continue
        
        return forecasts
    
    def get_weather_warnings(self) -> Dict[str, Any]:
        """
        获取生效中的天气警告
        API: warnsum (Warning Summary)
        """
        try:
            data = self._make_request('warning_summary')
            return data
        except:
            return {}
    
    def has_active_warning(self, warning_type: str = None) -> bool:
        """
        检查是否有生效的天气警告
        warning_type: 'WTCSGNL'(台风), 'WRAIN'(暴雨), 'WHOT'(酷热), 'WCOLD'(寒冷)
        """
        warnings = self.get_weather_warnings()
        
        if not warnings:
            return False
        
        if warning_type:
            return warning_type in warnings
        
        return len(warnings) > 0
    
    def to_weather_schema(self, forecast: HKOForecast) -> WeatherDataSchema:
        """
        将HKO预报转换为标准WeatherDataSchema
        """
        # 映射天气图标到天气状况
        weather_condition = WEATHER_ICON_MAPPING.get(
            forecast.weather_icon, 
            WeatherCondition.CLOUDY
        )
        
        # 检查警告
        warnings = self.get_weather_warnings()
        
        return WeatherDataSchema(
            date=forecast.forecast_date,
            location="Hong Kong",
            temperature_max=forecast.temp_max,
            temperature_min=forecast.temp_min,
            temperature_avg=(forecast.temp_max + forecast.temp_min) / 2,
            humidity=(forecast.humidity_max + forecast.humidity_min) / 2,
            rainfall=None,  # 预报中没有具体降雨量
            weather_condition=weather_condition,
            weather_icon=forecast.weather_icon,
            has_typhoon_signal='WTCSGNL' in warnings,
            has_rainstorm_warning='WRAIN' in warnings,
            has_hot_weather_warning='WHOT' in warnings,
            has_cold_weather_warning='WCOLD' in warnings
        )
    
    def get_weather_for_forecast(self, target_date: date) -> Optional[WeatherDataSchema]:
        """
        获取指定日期的天气数据 (用于需求预测)
        """
        forecasts = self.get_9day_forecast()
        
        for forecast in forecasts:
            if forecast.forecast_date == target_date:
                return self.to_weather_schema(forecast)
        
        # 如果目标日期不在9天预报范围内，返回None
        return None


# ==================== 测试函数 ====================

def test_hko_api():
    """测试HKO API"""
    api = HKOWeatherAPI()
    
    print("=" * 60)
    print("HKO Weather API Test")
    print("=" * 60)
    
    # 测试当前天气
    print("\n1. Current Weather:")
    try:
        current = api.get_current_weather()
        print(f"   Temperature: {current.temperature}°C")
        print(f"   Humidity: {current.humidity}%")
        print(f"   Weather Icon: {current.weather_icon}")
        print(f"   Update Time: {current.update_time}")
    except Exception as e:
        print(f"   Error: {e}")
    
    # 测试9天预报
    print("\n2. 9-Day Forecast:")
    try:
        forecasts = api.get_9day_forecast()
        for f in forecasts[:3]:  # 只显示前3天
            print(f"   {f.forecast_date} ({f.week}): {f.temp_min}-{f.temp_max}°C, Icon: {f.weather_icon}")
    except Exception as e:
        print(f"   Error: {e}")
    
    # 测试天气警告
    print("\n3. Weather Warnings:")
    try:
        warnings = api.get_weather_warnings()
        if warnings:
            print(f"   Active warnings: {list(warnings.keys())}")
        else:
            print("   No active warnings")
    except Exception as e:
        print(f"   Error: {e}")
    
    print("\n" + "=" * 60)
    print("HKO API Test Complete")
    print("=" * 60)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    test_hko_api()
