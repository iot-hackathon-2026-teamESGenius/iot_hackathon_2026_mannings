"""
距离计算器测试
"""
import pytest
import pandas as pd
from src.modules.distance.implementations.euclidean_calculator import EuclideanDistanceCalculator

def test_euclidean_calculator():
    """测试欧几里得距离计算器"""
    calculator = EuclideanDistanceCalculator(cache_enabled=False)
    
    origins = [(22.3193, 114.1694), (22.3287, 114.1883)]
    destinations = [(22.3372, 114.1521), (22.3105, 114.1829)]
    
    result = calculator.calculate_distance_matrix(origins, destinations)
    
    # 验证结果格式
    assert isinstance(result, pd.DataFrame)
    assert 'distance_km' in result.columns
    assert 'duration_min' in result.columns
    assert len(result) == len(origins) * len(destinations)
    
    # 验证距离值
    distances = result['distance_km'].values
    assert all(distances > 0)
    assert all(distances < 100)  # 香港范围内应该小于100公里

def test_provider_name():
    """测试提供商名称"""
    calculator = EuclideanDistanceCalculator()
    assert calculator.get_provider_name() == "Euclidean Distance Calculator"

def test_cost_per_request():
    """测试请求成本"""
    calculator = EuclideanDistanceCalculator()
    assert calculator.get_cost_per_request() == 0.0

def test_cache():
    """测试缓存功能"""
    calculator = EuclideanDistanceCalculator(cache_enabled=True)
    
    origins = [(22.3193, 114.1694)]
    destinations = [(22.3287, 114.1883)]
    
    result1 = calculator.calculate_distance_matrix(origins, destinations)
    result2 = calculator.calculate_distance_matrix(origins, destinations)
    
    # 验证两次结果相同（缓存生效）
    pd.testing.assert_frame_equal(result1, result2)

if __name__ == "__main__":
    pytest.main([__file__, '-v'])
