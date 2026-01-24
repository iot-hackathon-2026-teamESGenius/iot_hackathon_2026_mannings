"""
欧几里得距离计算器
"""
import pandas as pd
import numpy as np
from typing import List, Tuple, Dict, Any
from ...interfaces import IDistanceCalculator

class EuclideanDistanceCalculator(IDistanceCalculator):
    """欧几里得距离计算器"""
    
    def __init__(self, cache_enabled: bool = True):
        self.cache_enabled = cache_enabled
        self.cache = {}
    
    def calculate_distance_matrix(self, origins: List[Tuple[float, float]], 
                                 destinations: List[Tuple[float, float]], 
                                 mode: str = "driving") -> pd.DataFrame:
        """计算欧几里得距离矩阵"""
        
        cache_key = f"{hash(str(origins))}_{hash(str(destinations))}"
        
        if self.cache_enabled and cache_key in self.cache:
            return self.cache[cache_key]
        
        # 计算距离
        distances = []
        durations = []
        
        for orig_lat, orig_lng in origins:
            row_distances = []
            row_durations = []
            
            for dest_lat, dest_lng in destinations:
                # 计算欧几里得距离（简化的球面距离）
                distance_km = self._haversine_distance(orig_lat, orig_lng, dest_lat, dest_lng)
                
                # 估算时间（假设平均速度30km/h）
                duration_min = (distance_km / 30) * 60 if distance_km > 0 else 0
                
                row_distances.append(distance_km)
                row_durations.append(duration_min)
            
            distances.append(row_distances)
            durations.append(row_durations)
        
        # 创建DataFrame
        result = pd.DataFrame({
            'distance_km': [d for row in distances for d in row],
            'duration_min': [t for row in durations for t in row]
        })
        
        if self.cache_enabled:
            self.cache[cache_key] = result
        
        return result
    
    def _haversine_distance(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """计算两点间的Haversine距离（公里）"""
        from math import radians, sin, cos, sqrt, atan2
        
        R = 6371.0  # 地球半径（公里）
        
        lat1_rad = radians(lat1)
        lon1_rad = radians(lon1)
        lat2_rad = radians(lat2)
        lon2_rad = radians(lon2)
        
        dlon = lon2_rad - lon1_rad
        dlat = lat2_rad - lat1_rad
        
        a = sin(dlat / 2)**2 + cos(lat1_rad) * cos(lat2_rad) * sin(dlon / 2)**2
        c = 2 * atan2(sqrt(a), sqrt(1 - a))
        
        return R * c
    
    def get_provider_name(self) -> str:
        return "Euclidean Distance Calculator"
    
    def get_cost_per_request(self) -> float:
        return 0.0  # 本地计算无成本
