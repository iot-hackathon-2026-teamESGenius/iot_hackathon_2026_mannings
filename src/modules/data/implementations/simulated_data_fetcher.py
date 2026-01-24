"""
模拟数据获取器
"""
import pandas as pd
from typing import Dict, Any, List, Tuple
from ...interfaces import IDataFetcher

class SimulatedDataFetcher(IDataFetcher):
    """模拟数据获取器"""
    
    def __init__(self, data_path: str = "data/synthetic/", cache_enabled: bool = True):
        self.data_path = data_path
        self.cache_enabled = cache_enabled
        self.cache = {}
    
    def fetch_weather_data(self, date_range: Tuple[str, str], locations: List[Tuple[float, float]]) -> pd.DataFrame:
        """获取模拟天气数据"""
        import numpy as np
        
        start_date, end_date = pd.to_datetime(date_range[0]), pd.to_datetime(date_range[1])
        dates = pd.date_range(start=start_date, end=end_date, freq='D')
        
        data = []
        for date in dates:
            for lat, lng in locations:
                data.append({
                    'date': date.date(),
                    'latitude': lat,
                    'longitude': lng,
                    'temperature': np.random.normal(25, 5),
                    'humidity': np.random.normal(70, 10),
                    'precipitation': np.random.exponential(1),
                    'weather_condition': np.random.choice(['sunny', 'cloudy', 'rainy'], p=[0.6, 0.3, 0.1])
                })
        
        return pd.DataFrame(data)
    
    def fetch_geospatial_data(self, bounding_box: Tuple[float, float, float, float]) -> Dict:
        """获取模拟地理数据"""
        min_lat, min_lng, max_lat, max_lng = bounding_box
        
        return {
            'type': 'FeatureCollection',
            'features': [
                {
                    'type': 'Feature',
                    'geometry': {
                        'type': 'Point',
                        'coordinates': [
                            (min_lng + max_lng) / 2,
                            (min_lat + max_lat) / 2
                        ]
                    },
                    'properties': {'name': 'Central Hong Kong'}
                }
            ]
        }
    
    def fetch_business_data(self, date_range: Tuple[str, str], data_type: str) -> pd.DataFrame:
        """获取模拟业务数据"""
        import numpy as np
        
        if data_type == "sales":
            # 模拟销售数据
            dates = pd.date_range(start=date_range[0], end=date_range[1], freq='D')
            stores = [f"M{i:03d}" for i in range(1, 11)]
            
            data = []
            for date in dates:
                for store in stores:
                    data.append({
                        'date': date.date(),
                        'store_id': store,
                        'sales': np.random.poisson(100),
                        'customers': np.random.poisson(50)
                    })
            
            return pd.DataFrame(data)
        
        elif data_type == "inventory":
            # 模拟库存数据
            stores = [f"M{i:03d}" for i in range(1, 11)]
            skus = [f"SKU{j:03d}" for j in range(1, 6)]
            
            data = []
            for store in stores:
                for sku in skus:
                    data.append({
                        'store_id': store,
                        'sku_id': sku,
                        'current_stock': np.random.randint(10, 100),
                        'min_stock': 20,
                        'max_stock': 200
                    })
            
            return pd.DataFrame(data)
        
        else:
            raise ValueError(f"Unsupported data type: {data_type}")
    
    def get_config(self) -> Dict[str, Any]:
        return {
            'data_path': self.data_path,
            'cache_enabled': self.cache_enabled
        }
    
    def test_connection(self) -> bool:
        return True
