#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
简单测试增强的优化器功能
"""

import sys
from pathlib import Path
import numpy as np
from datetime import date, datetime

# 添加项目路径
project_root = Path(__file__).parent
sys.path.append(str(project_root / "src"))

# 直接导入模块
sys.path.append(str(project_root / "src" / "modules" / "routing"))
sys.path.append(str(project_root / "src" / "core"))

from data_schema import OrderDetail, OrderItem, DemandForecast, DeliveryScenario
from scenario_generator import DeliveryScenarioGenerator

def test_scenario_generator_enhancements():
    """测试场景生成器的增强功能"""
    print("🎲 测试场景生成器增强功能...")
    
    # 创建增强配置
    config = {
        'use_prophet_intervals': True,
        'prophet_integration': {
            'use_confidence_intervals': True,
            'interval_sampling_method': 'monte_carlo',
            'monte_carlo_samples': 100,
            'uncertainty_inflation': 1.2,
        },
        'uncertainty_modeling': {
            'enable_demand_correlation': True,
            'enable_weather_uncertainty': True,
            'enable_traffic_uncertainty': True,
            'weather_forecast_accuracy': 0.8,
            'traffic_prediction_accuracy': 0.7,
        }
    }
    
    generator = DeliveryScenarioGenerator(config)
    print("✅ 增强场景生成器创建成功")
    
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
    
    print(f"📊 创建 {len(prophet_forecasts)} 个Prophet预测")
    
    # 测试Prophet集成场景生成
    print("🚀 使用Prophet置信区间生成场景...")
    scenarios = generator.generate_scenarios_with_prophet(prophet_forecasts, num_scenarios=8)
    
    print(f"✅ 生成 {len(scenarios)} 个Prophet场景")
    
    # 验证场景一致性
    valid_scenarios = 0
    for scenario in scenarios:
        is_valid = generator.validate_scenario_consistency(scenario)
        if is_valid:
            valid_scenarios += 1
        print(f"   场景 {scenario.scenario_id}: {'✅ 有效' if is_valid else '❌ 无效'}")
    
    print(f"📊 场景验证结果: {valid_scenarios}/{len(scenarios)} 个场景有效")
    
    # 分析场景特征
    print("\n📋 场景特征分析:")
    total_prob = 0
    for scenario in scenarios:
        print(f"   {scenario.scenario_id}:")
        print(f"     订单数: {len(scenario.orders)}")
        print(f"     概率: {scenario.probability:.3f}")
        print(f"     天气影响: {scenario.weather_impact:.3f}")
        print(f"     交通影响: {scenario.traffic_impact:.3f}")
        total_prob += scenario.probability
    
    print(f"\n📊 总概率: {total_prob:.3f}")
    
    # 测试天气和交通场景生成
    print("\n🌤️ 测试天气场景生成...")
    weather_scenario = generator._generate_weather_scenario()
    print(f"   天气类型: {weather_scenario['type']}")
    print(f"   需求影响: {weather_scenario['impact']:.3f}")
    print(f"   配送影响: {weather_scenario['delivery_impact']:.3f}")
    
    print("\n🚗 测试交通场景生成...")
    traffic_scenario = generator._generate_traffic_scenario()
    print(f"   交通类型: {traffic_scenario['type']}")
    print(f"   影响因子: {traffic_scenario['impact']:.3f}")
    print(f"   延迟因子: {traffic_scenario['delay_factor']:.3f}")
    
    # 测试Beta分布参数估计
    print("\n📈 测试Beta分布参数估计...")
    alpha, beta = generator._estimate_beta_parameters(35.0, 50.0, 70.0)
    print(f"   Beta参数: α={alpha:.2f}, β={beta:.2f}")
    
    return scenarios

def test_prophet_sampling():
    """测试Prophet置信区间采样"""
    print("\n🎯 测试Prophet置信区间采样...")
    
    generator = DeliveryScenarioGenerator()
    
    # 创建测试预测数据
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
    
    # 多次采样测试
    samples = []
    for i in range(10):
        sample = generator._sample_from_prophet_intervals(forecasts_by_store)
        samples.append(sample)
        print(f"   采样 {i+1}: 417={sample['417']:.1f}, 331={sample['331']:.1f}")
    
    # 统计分析
    store_417_samples = [s['417'] for s in samples]
    store_331_samples = [s['331'] for s in samples]
    
    print(f"\n📊 采样统计:")
    print(f"   门店417: 均值={np.mean(store_417_samples):.1f}, 标准差={np.std(store_417_samples):.1f}")
    print(f"   门店331: 均值={np.mean(store_331_samples):.1f}, 标准差={np.std(store_331_samples):.1f}")

if __name__ == "__main__":
    print("🧪 开始测试场景生成器增强功能...")
    
    try:
        # 测试场景生成器增强功能
        scenarios = test_scenario_generator_enhancements()
        
        # 测试Prophet采样
        test_prophet_sampling()
        
        print("\n🎉 所有增强功能测试完成！")
        
    except Exception as e:
        print(f"\n❌ 测试失败: {str(e)}")
        import traceback
        traceback.print_exc()