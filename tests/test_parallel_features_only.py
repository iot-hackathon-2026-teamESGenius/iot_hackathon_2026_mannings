#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试并行处理功能（不依赖OR-Tools）
验证缓存、性能监控等核心功能
"""

import sys
import time
import numpy as np
from pathlib import Path
from datetime import datetime, date

# 添加项目路径
project_root = Path(__file__).parent
sys.path.append(str(project_root))
sys.path.append(str(project_root / "src"))

def test_caching_classes():
    """测试缓存类功能"""
    print("🧪 测试缓存类功能")
    
    # 导入缓存类
    from src.modules.routing.robust_optimizer import DistanceMatrixCache, OptimizationCache, PerformanceMonitor
    
    # 测试距离矩阵缓存
    print("测试距离矩阵缓存...")
    distance_cache = DistanceMatrixCache(max_size=5)
    
    # 创建测试位置
    locations1 = [(22.3193, 114.1694), (22.2783, 114.1747), (22.3964, 114.1095)]
    locations2 = [(22.4818, 114.1302), (22.2587, 114.1314), (22.3526, 114.1277)]
    
    # 创建测试矩阵
    matrix1 = np.random.rand(3, 3)
    matrix2 = np.random.rand(3, 3)
    
    # 测试存储和获取
    distance_cache.put(locations1, matrix1)
    distance_cache.put(locations2, matrix2)
    
    cached_matrix1 = distance_cache.get(locations1)
    cached_matrix2 = distance_cache.get(locations2)
    
    assert np.array_equal(cached_matrix1, matrix1), "距离矩阵缓存存储/获取失败"
    assert np.array_equal(cached_matrix2, matrix2), "距离矩阵缓存存储/获取失败"
    
    print("✅ 距离矩阵缓存测试通过")
    
    # 测试缓存统计
    stats = distance_cache.get_stats()
    print(f"   缓存大小: {stats['cache_size']}")
    print(f"   内存使用: {stats['memory_usage_mb']:.2f}MB")
    
    return True

def test_performance_monitor():
    """测试性能监控器"""
    print("\n🧪 测试性能监控器")
    
    from src.modules.routing.robust_optimizer import PerformanceMonitor
    
    monitor = PerformanceMonitor()
    
    # 开始监控
    monitor.start_monitoring()
    
    # 模拟一些操作
    time.sleep(0.1)
    monitor.record_scenario_processed()
    monitor.record_cache_hit()
    monitor.record_cache_miss()
    monitor.record_scenario_processed()
    
    time.sleep(0.1)
    
    # 结束监控
    metrics = monitor.finish_monitoring()
    
    print(f"✅ 性能监控测试完成")
    print(f"   优化时间: {metrics.optimization_time:.3f}秒")
    print(f"   处理场景数: {metrics.scenarios_processed}")
    print(f"   缓存命中: {metrics.cache_hits}")
    print(f"   缓存未命中: {metrics.cache_misses}")
    print(f"   内存使用: {metrics.memory_usage_mb:.1f}MB")
    
    return True

if __name__ == "__main__":
    print("🚀 测试并行处理核心功能")
    print("=" * 50)
    
    try:
        test_caching_classes()
        test_performance_monitor()
        
        print("\n" + "=" * 50)
        print("🎉 核心功能测试完成！")
        
    except Exception as e:
        print(f"❌ 测试失败: {str(e)}")
        import traceback
        traceback.print_exc()