#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试增强的OR-Tools优化器和场景生成器
"""

import sys
from pathlib import Path
import numpy as np
from datetime import date, datetime

# 添加项目路径
project_root = Path(__file__).parent
sys.path.append(str(project_root / "src"))

from core.data_schema import OrderDetail, OrderItem, DemandForecast, DeliveryScenario
from modules.routing.scenario_generator import DeliveryScenarioGenerator
from modules.routing.ortools_optimizer import ORToolsOptimizer

def test_enhanced_scenario_generator():
    """测试增强的场景生成器"""
    print("🎲 测试增强的场景生成器...")
    
    # 创建场景生成器
    config = {
        'use_prophet_intervals': True,
        'prophet_integration': {
            'use_confidence_intervals': True,
            'interval_sampling_method': 'monte_carlo',
            'monte_carlo_samples': 100,
        }
    }
    generator = DeliveryScenarioGenerator(config)
    
    # 创建模拟Prophet预测数据
    prophet_forecasts = []
    store_codes = ['417', '331', '213', '215', '878']
    
    for store_code in store_codes:
        forecast = DemandForecast(
            store_code=store_code,
            sku_id="aggregate",
            forecast_date=date.today(),
            predicted_demand=50.0,
            confidence_intervals={
                'P10': 35.0,
                'P50': 50.0,
                'P90': 70.0
            },
            external_factors={'weather_impact': 0.1, 'holiday_impact': 0.0},
            model_version="prophet_v1.0",
            forecast_timestamp=datetime.now()
        )
        prophet_forecasts.append(forecast)
    
    # 使用Prophet预测生成场景
    scenarios = generator.generate_scenarios_with_prophet(prophet_forecasts, num_scenarios=5)
    
    print(f"✅ 生成 {len(scenarios)} 个Prophet场景")
    
    # 验证场景一致性
    for scenario in scenarios:
        is_valid = generator.validate_scenario_consistency(scenario)
        print(f"   场景 {scenario.scenario_id}: {'✅ 有效' if is_valid else '❌ 无效'}")
    
    return scenarios

def test_enhanced_optimizer():
    """测试增强的OR-Tools优化器"""
    print("\n🚚 测试增强的OR-Tools优化器...")
    
    # 创建优化器配置
    config = {
        'time_limit_seconds': 30,
        'enable_soft_time_windows': True,
        'enable_route_duration_limit': True,
        'enable_distance_limit': True,
        'solver_log_level': 0  # 减少日志输出
    }
    
    optimizer = ORToolsOptimizer(config)
    
    # 创建示例订单
    orders = []
    store_codes = ['417', '331', '213', '215', '878']
    
    for i, store_code in enumerate(store_codes):
        order = OrderDetail(
            order_id=f"order_{i}",
            user_id=f"user_{i}",
            fulfillment_store_code=store_code,
            order_date=date.today(),
            items=[OrderItem(sku_id=f"sku_{i}", sku_name=f"Product {i}", quantity=5)],
            total_quantity=10 + i * 2,
            unique_sku_count=1
        )
        orders.append(order)
    
    # 创建车辆
    vehicles = [
        {'id': 'vehicle_1', 'capacity': 100},
        {'id': 'vehicle_2', 'capacity': 100}
    ]
    
    # 设置约束
    constraints = {
        'max_route_time': 8 * 60,
        'time_window_start': '08:00',
        'time_window_end': '18:00'
    }
    
    try:
        # 执行优化
        result = optimizer.optimize(orders, vehicles, constraints)
        
        print(f"✅ 优化完成")
        print(f"   求解状态: {result.solver_status}")
        print(f"   总距离: {result.total_distance:.1f} km")
        print(f"   总时间: {result.total_time:.1f} 小时")
        print(f"   SLA合规率: {result.sla_compliance_rate:.1%}")
        
        # 验证解决方案
        is_valid = optimizer.validate_solution(result)
        print(f"   解决方案验证: {'✅ 通过' if is_valid else '❌ 失败'}")
        
        # 显示优化统计
        stats = optimizer.get_optimization_stats()
        print(f"   位置数量: {stats['locations_count']}")
        print(f"   车辆容量: {stats['vehicle_capacities']}")
        
        return result
        
    except Exception as e:
        print(f"❌ 优化失败: {str(e)}")
        return None

def test_integration():
    """测试场景生成器和优化器的集成"""
    print("\n🔗 测试场景生成器和优化器集成...")
    
    # 生成场景
    scenarios = test_enhanced_scenario_generator()
    
    if not scenarios:
        print("❌ 场景生成失败")
        return
    
    # 对每个场景进行优化
    optimizer = ORToolsOptimizer({'solver_log_level': 0})
    
    optimization_results = []
    
    for i, scenario in enumerate(scenarios[:3]):  # 只测试前3个场景
        print(f"\n   优化场景 {scenario.scenario_id}...")
        
        vehicles = [
            {'id': 'vehicle_1', 'capacity': 150},
            {'id': 'vehicle_2', 'capacity': 150}
        ]
        
        constraints = {
            'max_route_time': 10 * 60,  # 增加时间限制
            'time_window_start': '06:00',
            'time_window_end': '20:00'
        }
        
        try:
            result = optimizer.optimize(scenario.orders, vehicles, constraints)
            optimization_results.append(result)
            
            print(f"     ✅ 场景优化完成: {result.total_distance:.1f}km, SLA: {result.sla_compliance_rate:.1%}")
            
        except Exception as e:
            print(f"     ❌ 场景优化失败: {str(e)}")
    
    print(f"\n✅ 集成测试完成，成功优化 {len(optimization_results)} 个场景")
    
    # 比较不同场景的优化结果
    if optimization_results:
        distances = [r.total_distance for r in optimization_results]
        sla_rates = [r.sla_compliance_rate for r in optimization_results]
        
        print(f"   距离范围: {min(distances):.1f} - {max(distances):.1f} km")
        print(f"   SLA范围: {min(sla_rates):.1%} - {max(sla_rates):.1%}")

if __name__ == "__main__":
    print("🧪 开始测试增强的路径优化系统...")
    
    try:
        # 测试场景生成器
        test_enhanced_scenario_generator()
        
        # 测试优化器
        test_enhanced_optimizer()
        
        # 测试集成
        test_integration()
        
        print("\n🎉 所有测试完成！")
        
    except Exception as e:
        print(f"\n❌ 测试失败: {str(e)}")
        import traceback
        traceback.print_exc()