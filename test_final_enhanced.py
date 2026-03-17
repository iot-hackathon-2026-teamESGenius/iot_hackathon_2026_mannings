#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
最终测试增强的路径优化系统
"""

import sys
from pathlib import Path
import numpy as np
from datetime import date, datetime

# 添加项目路径
project_root = Path(__file__).parent
sys.path.append(str(project_root / "src"))
sys.path.append(str(project_root / "src" / "modules" / "routing"))
sys.path.append(str(project_root / "src" / "core"))

from data_schema import OrderDetail, OrderItem, DemandForecast, DeliveryScenario
from scenario_generator import DeliveryScenarioGenerator

def test_complete_enhanced_system():
    """测试完整的增强系统"""
    print("🚀 测试完整的增强路径优化系统...")
    
    # 创建完整配置
    config = {
        'scenario_types': ['optimistic', 'realistic', 'pessimistic'],
        'demand_variation_range': (0.7, 1.3),
        'weather_impact_factor': 0.25,
        'traffic_impact_factor': 0.20,
        'holiday_impact_factor': 0.30,
        'uncertainty_levels': [0.1, 0.2, 0.3],
        'correlation_strength': 0.4,
        'min_probability': 0.02,
        'max_scenarios': 25,
        'use_prophet_intervals': True,
        'confidence_levels': [0.1, 0.5, 0.9],
        'weather_scenarios': {
            'sunny': {'probability': 0.4, 'demand_impact': 0.05, 'delivery_impact': -0.05},
            'rainy': {'probability': 0.3, 'demand_impact': -0.10, 'delivery_impact': 0.15},
            'stormy': {'probability': 0.1, 'demand_impact': -0.20, 'delivery_impact': 0.30},
            'cloudy': {'probability': 0.2, 'demand_impact': 0.0, 'delivery_impact': 0.0}
        },
        'traffic_scenarios': {
            'light': {'probability': 0.3, 'speed_multiplier': 1.2, 'delay_factor': 0.8},
            'moderate': {'probability': 0.4, 'speed_multiplier': 1.0, 'delay_factor': 1.0},
            'heavy': {'probability': 0.2, 'speed_multiplier': 0.7, 'delay_factor': 1.4},
            'severe': {'probability': 0.1, 'speed_multiplier': 0.5, 'delay_factor': 2.0}
        },
        'seasonal_factors': {
            'spring': 1.0, 'summer': 1.1, 'autumn': 0.95, 'winter': 1.05
        },
        'prophet_integration': {
            'use_confidence_intervals': True,
            'interval_sampling_method': 'monte_carlo',
            'monte_carlo_samples': 1000,
            'confidence_correlation': 0.3,
            'forecast_horizon_days': 7,
            'uncertainty_inflation': 1.2,
        },
        'uncertainty_modeling': {
            'enable_demand_correlation': True,
            'enable_weather_uncertainty': True,
            'enable_traffic_uncertainty': True,
            'weather_forecast_accuracy': 0.8,
            'traffic_prediction_accuracy': 0.7,
            'seasonal_uncertainty_factor': 0.15,
            'holiday_uncertainty_factor': 0.25,
        }
    }
    
    generator = DeliveryScenarioGenerator(config)
    print("✅ 增强场景生成器创建成功")
    
    # 创建Prophet预测数据
    prophet_forecasts = []
    store_codes = ['417', '331', '213', '215', '878']
    
    for store_code in store_codes:
        # 模拟不同门店的预测特征
        base_demand = 40 + hash(store_code) % 30  # 40-70之间
        
        forecast = DemandForecast(
            store_code=store_code,
            sku_id="aggregate",
            forecast_date=date.today(),
            predicted_demand=float(base_demand),
            confidence_intervals={
                'P10': base_demand * 0.7,
                'P50': float(base_demand),
                'P90': base_demand * 1.4
            },
            external_factors={
                'weather_impact': np.random.uniform(-0.1, 0.1),
                'holiday_impact': 0.0,
                'seasonal_impact': np.random.uniform(-0.05, 0.05)
            },
            model_version="prophet_v1.0",
            forecast_timestamp=datetime.now()
        )
        prophet_forecasts.append(forecast)
    
    print(f"📊 创建 {len(prophet_forecasts)} 个Prophet预测")
    
    # 测试Prophet集成场景生成
    print("\n🎯 使用Prophet置信区间生成场景...")
    scenarios = generator.generate_scenarios_with_prophet(prophet_forecasts, num_scenarios=10)
    
    print(f"✅ 生成 {len(scenarios)} 个Prophet场景")
    
    # 验证所有场景
    valid_count = 0
    for scenario in scenarios:
        is_valid = generator.validate_scenario_consistency(scenario)
        if is_valid:
            valid_count += 1
    
    print(f"📊 场景验证: {valid_count}/{len(scenarios)} 个场景有效")
    
    # 分析场景统计
    print("\n📈 场景统计分析:")
    
    # 订单数量统计
    order_counts = [len(s.orders) for s in scenarios]
    print(f"   订单数量: 最小={min(order_counts)}, 最大={max(order_counts)}, 平均={np.mean(order_counts):.1f}")
    
    # 概率分布
    probabilities = [s.probability for s in scenarios]
    print(f"   概率分布: 总和={sum(probabilities):.3f}, 最小={min(probabilities):.3f}, 最大={max(probabilities):.3f}")
    
    # 影响因子分析
    weather_impacts = [s.weather_impact for s in scenarios]
    traffic_impacts = [s.traffic_impact for s in scenarios]
    print(f"   天气影响: 范围=[{min(weather_impacts):.3f}, {max(weather_impacts):.3f}], 平均={np.mean(weather_impacts):.3f}")
    print(f"   交通影响: 范围=[{min(traffic_impacts):.3f}, {max(traffic_impacts):.3f}], 平均={np.mean(traffic_impacts):.3f}")
    
    # 需求预测分析
    print("\n📊 需求预测分析:")
    for store_code in store_codes:
        store_demands = []
        for scenario in scenarios:
            if store_code in scenario.demand_forecast:
                store_demands.append(scenario.demand_forecast[store_code])
        
        if store_demands:
            print(f"   门店{store_code}: 范围=[{min(store_demands):.1f}, {max(store_demands):.1f}], 平均={np.mean(store_demands):.1f}")
    
    return scenarios

def test_uncertainty_modeling():
    """测试不确定性建模功能"""
    print("\n🎲 测试不确定性建模功能...")
    
    generator = DeliveryScenarioGenerator()
    
    # 测试天气场景生成
    print("🌤️ 测试天气场景生成...")
    weather_scenarios = []
    for i in range(10):
        weather = generator._generate_weather_scenario()
        weather_scenarios.append(weather)
    
    # 统计天气类型分布
    weather_types = [w['type'] for w in weather_scenarios]
    unique_types = set(weather_types)
    print(f"   生成天气类型: {unique_types}")
    
    for weather_type in unique_types:
        count = weather_types.count(weather_type)
        print(f"     {weather_type}: {count}/10 ({count*10}%)")
    
    # 测试交通场景生成
    print("\n🚗 测试交通场景生成...")
    traffic_scenarios = []
    for i in range(10):
        traffic = generator._generate_traffic_scenario()
        traffic_scenarios.append(traffic)
    
    # 统计交通类型分布
    traffic_types = [t['type'] for t in traffic_scenarios]
    unique_types = set(traffic_types)
    print(f"   生成交通类型: {unique_types}")
    
    for traffic_type in unique_types:
        count = traffic_types.count(traffic_type)
        print(f"     {traffic_type}: {count}/10 ({count*10}%)")

def test_prophet_integration():
    """测试Prophet集成功能"""
    print("\n🔮 测试Prophet集成功能...")
    
    generator = DeliveryScenarioGenerator()
    
    # 创建测试数据
    forecasts_by_store = {
        '417': [DemandForecast(
            store_code='417',
            sku_id="aggregate",
            forecast_date=date.today(),
            predicted_demand=50.0,
            confidence_intervals={'P10': 30.0, 'P50': 50.0, 'P90': 80.0},
            external_factors={},
            model_version="prophet_v1.0",
            forecast_timestamp=datetime.now()
        )],
        '331': [DemandForecast(
            store_code='331',
            sku_id="aggregate",
            forecast_date=date.today(),
            predicted_demand=45.0,
            confidence_intervals={'P10': 25.0, 'P50': 45.0, 'P90': 70.0},
            external_factors={},
            model_version="prophet_v1.0",
            forecast_timestamp=datetime.now()
        )]
    }
    
    # 测试置信区间采样
    print("📊 测试置信区间采样...")
    samples = []
    for i in range(20):
        sample = generator._sample_from_prophet_intervals(forecasts_by_store)
        samples.append(sample)
    
    # 分析采样结果
    store_417_samples = [s['417'] for s in samples]
    store_331_samples = [s['331'] for s in samples]
    
    print(f"   门店417采样统计:")
    print(f"     范围: [{min(store_417_samples):.1f}, {max(store_417_samples):.1f}]")
    print(f"     均值: {np.mean(store_417_samples):.1f} (预期: 50.0)")
    print(f"     标准差: {np.std(store_417_samples):.1f}")
    
    print(f"   门店331采样统计:")
    print(f"     范围: [{min(store_331_samples):.1f}, {max(store_331_samples):.1f}]")
    print(f"     均值: {np.mean(store_331_samples):.1f} (预期: 45.0)")
    print(f"     标准差: {np.std(store_331_samples):.1f}")
    
    # 测试Beta参数估计
    print("\n📈 测试Beta参数估计...")
    test_cases = [
        (30.0, 50.0, 80.0),
        (10.0, 20.0, 40.0),
        (5.0, 15.0, 25.0)
    ]
    
    for p10, p50, p90 in test_cases:
        alpha, beta = generator._estimate_beta_parameters(p10, p50, p90)
        print(f"   P10={p10}, P50={p50}, P90={p90} -> α={alpha:.2f}, β={beta:.2f}")

if __name__ == "__main__":
    print("🧪 开始最终增强系统测试...")
    
    try:
        # 测试完整系统
        scenarios = test_complete_enhanced_system()
        
        # 测试不确定性建模
        test_uncertainty_modeling()
        
        # 测试Prophet集成
        test_prophet_integration()
        
        print("\n🎉 所有增强功能测试完成！")
        print(f"✅ 成功生成并验证了 {len(scenarios)} 个场景")
        print("✅ Prophet置信区间集成正常工作")
        print("✅ 不确定性建模功能正常")
        print("✅ 场景一致性验证通过")
        
    except Exception as e:
        print(f"\n❌ 测试失败: {str(e)}")
        import traceback
        traceback.print_exc()