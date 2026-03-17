#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
独立测试缓存和性能监控功能
不依赖复杂的导入链
"""

import time
import numpy as np
import threading
import hashlib
import pickle
from functools import lru_cache
import psutil
import gc
from collections import defaultdict
from dataclasses import dataclass
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime


@dataclass
class PerformanceMetrics:
    """性能监控指标"""
    optimization_time: float = 0.0
    memory_usage_mb: float = 0.0
    cpu_usage_percent: float = 0.0
    scenarios_processed: int = 0
    cache_hits: int = 0
    cache_misses: int = 0
    parallel_efficiency: float = 0.0
    throughput_scenarios_per_second: float = 0.0


class DistanceMatrixCache:
    """距离矩阵缓存管理器"""
    
    def __init__(self, max_size: int = 100):
        self.cache = {}
        self.access_times = {}
        self.max_size = max_size
        self.lock = threading.Lock()
    
    def _generate_key(self, locations: List[Tuple[float, float]]) -> str:
        """生成位置列表的哈希键"""
        locations_str = str(sorted(locations))
        return hashlib.md5(locations_str.encode()).hexdigest()
    
    def get(self, locations: List[Tuple[float, float]]) -> Optional[np.ndarray]:
        """获取缓存的距离矩阵"""
        key = self._generate_key(locations)
        with self.lock:
            if key in self.cache:
                self.access_times[key] = time.time()
                return self.cache[key].copy()
            return None
    
    def put(self, locations: List[Tuple[float, float]], matrix: np.ndarray) -> None:
        """存储距离矩阵到缓存"""
        key = self._generate_key(locations)
        with self.lock:
            if len(self.cache) >= self.max_size:
                # LRU淘汰策略
                oldest_key = min(self.access_times.keys(), key=lambda k: self.access_times[k])
                del self.cache[oldest_key]
                del self.access_times[oldest_key]
            
            self.cache[key] = matrix.copy()
            self.access_times[key] = time.time()
    
    def clear(self) -> None:
        """清空缓存"""
        with self.lock:
            self.cache.clear()
            self.access_times.clear()
    
    def get_stats(self) -> Dict[str, Any]:
        """获取缓存统计信息"""
        with self.lock:
            return {
                'cache_size': len(self.cache),
                'max_size': self.max_size,
                'memory_usage_mb': sum(matrix.nbytes for matrix in self.cache.values()) / (1024 * 1024)
            }


class PerformanceMonitor:
    """性能监控器"""
    
    def __init__(self):
        self.metrics_history = []
        self.current_metrics = PerformanceMetrics()
        self.start_time = None
        self.lock = threading.Lock()
    
    def start_monitoring(self) -> None:
        """开始监控"""
        self.start_time = time.time()
        self.current_metrics = PerformanceMetrics()
    
    def record_scenario_processed(self) -> None:
        """记录处理的场景数"""
        with self.lock:
            self.current_metrics.scenarios_processed += 1
    
    def record_cache_hit(self) -> None:
        """记录缓存命中"""
        with self.lock:
            self.current_metrics.cache_hits += 1
    
    def record_cache_miss(self) -> None:
        """记录缓存未命中"""
        with self.lock:
            self.current_metrics.cache_misses += 1
    
    def finish_monitoring(self) -> PerformanceMetrics:
        """结束监控并返回指标"""
        if self.start_time is None:
            return self.current_metrics
        
        end_time = time.time()
        self.current_metrics.optimization_time = end_time - self.start_time
        
        # 获取系统资源使用情况
        process = psutil.Process()
        self.current_metrics.memory_usage_mb = process.memory_info().rss / (1024 * 1024)
        self.current_metrics.cpu_usage_percent = process.cpu_percent()
        
        # 计算吞吐量
        if self.current_metrics.optimization_time > 0:
            self.current_metrics.throughput_scenarios_per_second = (
                self.current_metrics.scenarios_processed / self.current_metrics.optimization_time
            )
        
        return self.current_metrics


def test_distance_cache():
    """测试距离矩阵缓存"""
    print("🧪 测试距离矩阵缓存")
    
    cache = DistanceMatrixCache(max_size=5)
    
    # 创建测试位置
    locations1 = [(22.3193, 114.1694), (22.2783, 114.1747), (22.3964, 114.1095)]
    locations2 = [(22.4818, 114.1302), (22.2587, 114.1314), (22.3526, 114.1277)]
    
    # 创建测试矩阵
    matrix1 = np.random.rand(3, 3)
    matrix2 = np.random.rand(3, 3)
    
    # 测试存储和获取
    cache.put(locations1, matrix1)
    cache.put(locations2, matrix2)
    
    cached_matrix1 = cache.get(locations1)
    cached_matrix2 = cache.get(locations2)
    
    assert np.array_equal(cached_matrix1, matrix1), "距离矩阵缓存存储/获取失败"
    assert np.array_equal(cached_matrix2, matrix2), "距离矩阵缓存存储/获取失败"
    
    # 测试缓存未命中
    locations3 = [(22.1, 114.1), (22.2, 114.2)]
    cached_matrix3 = cache.get(locations3)
    assert cached_matrix3 is None, "应该返回None（缓存未命中）"
    
    print("✅ 距离矩阵缓存测试通过")
    
    # 测试缓存统计
    stats = cache.get_stats()
    print(f"   缓存大小: {stats['cache_size']}")
    print(f"   内存使用: {stats['memory_usage_mb']:.2f}MB")
    
    return True


def test_performance_monitor():
    """测试性能监控器"""
    print("\n🧪 测试性能监控器")
    
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
    print(f"   吞吐量: {metrics.throughput_scenarios_per_second:.2f} scenarios/s")
    
    return True


def test_cache_lru_eviction():
    """测试LRU缓存淘汰策略"""
    print("\n🧪 测试LRU缓存淘汰策略")
    
    cache = DistanceMatrixCache(max_size=3)
    
    # 添加3个缓存项
    for i in range(3):
        locations = [(22.3 + i * 0.1, 114.1 + i * 0.1)]
        matrix = np.random.rand(1, 1)
        cache.put(locations, matrix)
        time.sleep(0.01)  # 确保时间戳不同
    
    assert cache.get_stats()['cache_size'] == 3, "缓存大小应该为3"
    
    # 添加第4个项，应该淘汰最旧的
    locations4 = [(22.6, 114.4)]
    matrix4 = np.random.rand(1, 1)
    cache.put(locations4, matrix4)
    
    assert cache.get_stats()['cache_size'] == 3, "缓存大小应该仍为3"
    
    # 第一个项应该被淘汰
    first_locations = [(22.3, 114.1)]
    assert cache.get(first_locations) is None, "第一个项应该被淘汰"
    
    print("✅ LRU缓存淘汰策略测试通过")
    
    return True


def test_concurrent_cache_access():
    """测试并发缓存访问"""
    print("\n🧪 测试并发缓存访问")
    
    cache = DistanceMatrixCache(max_size=10)
    results = []
    
    def worker(worker_id):
        """工作线程函数"""
        locations = [(22.3 + worker_id * 0.1, 114.1 + worker_id * 0.1)]
        matrix = np.random.rand(2, 2)
        
        # 存储
        cache.put(locations, matrix)
        
        # 获取
        cached_matrix = cache.get(locations)
        
        # 验证
        if cached_matrix is not None and np.array_equal(cached_matrix, matrix):
            results.append(True)
        else:
            results.append(False)
    
    # 创建多个线程
    import threading
    threads = []
    for i in range(5):
        thread = threading.Thread(target=worker, args=(i,))
        threads.append(thread)
        thread.start()
    
    # 等待所有线程完成
    for thread in threads:
        thread.join()
    
    assert all(results), "所有线程应该成功完成缓存操作"
    
    print("✅ 并发缓存访问测试通过")
    print(f"   缓存大小: {cache.get_stats()['cache_size']}")
    
    return True


if __name__ == "__main__":
    print("🚀 测试缓存和性能监控功能")
    print("=" * 50)
    
    try:
        test_distance_cache()
        test_performance_monitor()
        test_cache_lru_eviction()
        test_concurrent_cache_access()
        
        print("\n" + "=" * 50)
        print("🎉 所有测试完成！缓存和性能监控功能正常")
        
    except Exception as e:
        print(f"❌ 测试失败: {str(e)}")
        import traceback
        traceback.print_exc()