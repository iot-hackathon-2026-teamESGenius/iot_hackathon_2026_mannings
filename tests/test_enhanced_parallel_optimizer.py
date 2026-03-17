#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试增强版并行鲁棒优化器
验证缓存、性能监控和并行处理功能
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

from src.modules.routing.robust_optimizer import DeliveryRobustOptimizer
from src.modules.routing.ortools_optimizer import ORToolsOptimizer
from src.core.data_schema import DeliveryScenario, OrderDetail


def create_test_orders(num_orders: int = 10) -> list:
    """创建测试订单"""
    orders = []
    
    # 香港地区的测试坐标
    hk_locations = [
        (22.3193, 114.1694),  # 中环
        (22.2783, 114.1747),  # 铜锣湾
        (22.3964, 114.1095),  # 沙田
        (22.4818, 114.1302),  # 大埔
        (22.2587, 114.1314),  # 黄竹坑
        (22.3526, 114.1277),  # 九龙塘
        (22.3193, 114.2644),  # 将军澳
        (22.4964, 114.1376),  # 粉岭
        (22.2446, 114.2252),  # 西贡
        (22.4629, 114.0631),  # 元朗
    ]
    
    for i in range(num_orders):
        lat, lng = hk_locations[i % len(hk_locations)]
        # 添加一些随机偏移
        lat += np.random.uniform(-0.01, 0.01)
        lng += np.random.uniform(-0.01, 0.01)
        
        order = OrderDetail(
            order_id=f"ORDER_{i:03d}",
            user_id=f"USER_{i:03d}",
            fulfillment_store_code=f"STORE_{i:03d}",
            order_date=date.today(),
            items=[],
            total_quantity=np.random.randint(1, 10),
            unique_sku_count=np.random.randint(1, 5),
            priority=np.random.randint(1, 4)
        )
        
        orders.append(order)
    
    return orders


def create_test_scenarios(num_scenarios: int = 15) -> list:
    """创建测试场景"""
    scenarios = []
    
    for i in range(num_scenarios):
        # 每个场景有不同数量的订单
        num_orders = np.random.randint(5, 15)
        orders = create_test_orders(num_orders)
        
        scenario = DeliveryScenario(
            scenario_id=f"SCENARIO_{i:03d}",
            orders=orders,
            demand_forecast={f"STORE_{j:03d}": np.random.uniform(0.8, 1.2) for j in range(num_orders)},
            weather_impact=np.random.uniform(-0.2, 0.2),
            traffic_impact=np.random.uniform(-0.3, 0.3),
            probability=np.random.uniform(0.05, 0.15),
            generated_timestamp=datetime.now()
        )
        
        scenarios.append(scenario)
    
    return scenarios


def test_basic_parallel_processing():
    """测试基本并行处理功能"""
    print("🧪 测试基本并行处理功能")
    
    # 创建优化器
    config = {
        'max_parallel_optimizations': 4,
        'performance_monitoring': True,
        'enable_gc_optimization': True,
        'adaptive_parallelism': True
    }
    
    optimizer = DeliveryRobustOptimizer(config=config)
    
    # 创建测试场景
    scenarios = create_test_scenarios(10)
    
    print(f"创建了 {len(scenarios)} 个测试场景")
    
    # 执行优化
    start_time = time.time()
    result = optimizer.optimize_robust(scenarios, strategy='min_max')
    end_time = time.time()
    
    print(f"✅ 优化完成，耗时: {end_time - start_time:.2f}秒")
    print(f"   鲁棒性分数: {result.robustness_score:.3f}")
    print(f"   置信水平: {result.confidence_level:.3f}")
    print(f"   处理场景数: {result.scenarios_evaluated}")
    
    return optimizer


def test_caching_performance():
    """测试缓存性能"""
    print("\n🧪 测试缓存性能")
    
    config = {
        'max_parallel_optimizations': 4,
        'distance_cache_size': 20,
        'optimization_cache_size': 15,
        'performance_monitoring': True
    }
    
    optimizer = DeliveryRobustOptimizer(config=config)
    
    # 创建相同的场景进行重复优化
    scenarios = create_test_scenarios(8)
    
    # 第一次优化（无缓存）
    print("第一次优化（建立缓存）...")
    start_time = time.time()
    result1 = optimizer.optimize_robust(scenarios, strategy='expected_value')
    time1 = time.time() - start_time
    
    # 第二次优化（使用缓存）
    print("第二次优化（使用缓存）...")
    start_time = time.time()
    result2 = optimizer.optimize_robust(scenarios, strategy='expected_value')
    time2 = time.time() - start_time
    
    print(f"✅ 缓存测试完成")
    print(f"   第一次优化耗时: {time1:.2f}秒")
    print(f"   第二次优化耗时: {time2:.2f}秒")
    print(f"   性能提升: {((time1 - time2) / time1 * 100):.1f}%")
    
    # 获取缓存统计
    cache_stats = optimizer.get_performance_stats()['cache_stats']
    print(f"   缓存命中率: {cache_stats['cache_hit_rate']:.3f}")
    
    return optimizer


def test_performance_monitoring():
    """测试性能监控功能"""
    print("\n🧪 测试性能监控功能")
    
    config = {
        'max_parallel_optimizations': 6,
        'performance_monitoring': True,
        'adaptive_parallelism': True,
        'enable_gc_optimization': True
    }
    
    optimizer = DeliveryRobustOptimizer(config=config)
    
    # 创建不同大小的场景集进行测试
    scenario_counts = [5, 10, 15]
    
    for count in scenario_counts:
        print(f"\n测试 {count} 个场景的优化...")
        scenarios = create_test_scenarios(count)
        
        start_time = time.time()
        result = optimizer.optimize_robust(scenarios, strategy='weighted_sum')
        end_time = time.time()
        
        print(f"   优化耗时: {end_time - start_time:.2f}秒")
        print(f"   场景数: {len(scenarios)}")
        print(f"   成功率: {len(result.all_routes)}/{len(scenarios)}")
    
    # 获取性能统计
    perf_stats = optimizer.get_performance_stats()
    print(f"\n📊 性能统计摘要:")
    
    if 'performance_metrics' in perf_stats:
        metrics = perf_stats['performance_metrics']
        print(f"   平均优化时间: {metrics.get('avg_optimization_time', 0):.2f}秒")
        print(f"   平均内存使用: {metrics.get('avg_memory_usage_mb', 0):.1f}MB")
        print(f"   平均吞吐量: {metrics.get('avg_throughput', 0):.2f} scenarios/s")
        print(f"   平均并行效率: {metrics.get('avg_parallel_efficiency', 0):.3f}")
    
    if 'optimization_stats' in perf_stats:
        opt_stats = perf_stats['optimization_stats']
        print(f"   总优化次数: {opt_stats.get('total_optimizations', 0)}")
        print(f"   总处理场景数: {opt_stats.get('total_scenarios_processed', 0)}")
    
    return optimizer


def test_adaptive_parallelism():
    """测试自适应并行度调整"""
    print("\n🧪 测试自适应并行度调整")
    
    config = {
        'adaptive_parallelism': True,
        'performance_monitoring': True
    }
    
    optimizer = DeliveryRobustOptimizer(config=config)
    
    # 测试不同场景数量下的并行度调整
    scenario_counts = [3, 8, 20, 30]
    
    for count in scenario_counts:
        print(f"\n测试 {count} 个场景...")
        scenarios = create_test_scenarios(count)
        
        # 记录调整前的并行度
        old_parallelism = optimizer.config['max_parallel_optimizations']
        
        # 执行优化（会触发自适应调整）
        start_time = time.time()
        result = optimizer.optimize_robust(scenarios, strategy='min_max')
        end_time = time.time()
        
        new_parallelism = optimizer.config['max_parallel_optimizations']
        
        print(f"   场景数: {count}")
        print(f"   并行度调整: {old_parallelism} -> {new_parallelism}")
        print(f"   优化耗时: {end_time - start_time:.2f}秒")
        print(f"   成功场景数: {len(result.all_routes)}")
    
    return optimizer


def test_memory_management():
    """测试内存管理功能"""
    print("\n🧪 测试内存管理功能")
    
    config = {
        'max_parallel_optimizations': 4,
        'memory_limit_mb': 512,  # 设置较低的内存限制进行测试
        'enable_gc_optimization': True,
        'chunk_size': 3
    }
    
    optimizer = DeliveryRobustOptimizer(config=config)
    
    # 创建较大的场景集
    scenarios = create_test_scenarios(20)
    
    print(f"创建了 {len(scenarios)} 个场景进行内存管理测试")
    
    start_time = time.time()
    result = optimizer.optimize_robust(scenarios, strategy='robust_deviation')
    end_time = time.time()
    
    print(f"✅ 内存管理测试完成")
    print(f"   优化耗时: {end_time - start_time:.2f}秒")
    print(f"   处理场景数: {len(result.all_routes)}/{len(scenarios)}")
    
    # 获取系统信息
    system_info = optimizer.get_performance_stats()['system_info']
    print(f"   当前内存使用: {system_info['current_memory_usage_mb']:.1f}MB")
    
    return optimizer


def main():
    """主测试函数"""
    print("🚀 开始测试增强版并行鲁棒优化器")
    print("=" * 60)
    
    try:
        # 测试基本并行处理
        optimizer1 = test_basic_parallel_processing()
        
        # 测试缓存性能
        optimizer2 = test_caching_performance()
        
        # 测试性能监控
        optimizer3 = test_performance_monitoring()
        
        # 测试自适应并行度
        optimizer4 = test_adaptive_parallelism()
        
        # 测试内存管理
        optimizer5 = test_memory_management()
        
        print("\n" + "=" * 60)
        print("🎉 所有测试完成！增强版并行优化器功能正常")
        
        # 显示最终统计
        final_stats = optimizer5.get_performance_stats()
        print(f"\n📈 最终性能统计:")
        print(f"   系统CPU核心数: {final_stats['system_info']['cpu_count']}")
        print(f"   系统内存: {final_stats['system_info']['memory_gb']:.1f}GB")
        print(f"   当前内存使用: {final_stats['system_info']['current_memory_usage_mb']:.1f}MB")
        
        if 'cache_stats' in final_stats:
            cache_info = final_stats['cache_stats']
            print(f"   缓存命中率: {cache_info['cache_hit_rate']:.3f}")
            print(f"   距离缓存大小: {cache_info['distance_cache']['cache_size']}")
            print(f"   优化缓存大小: {cache_info['optimization_cache']['cache_size']}")
        
    except Exception as e:
        print(f"❌ 测试失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return False
    
    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)