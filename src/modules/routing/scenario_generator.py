#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
万宁SLA优化系统 - 场景生成器
生成多种配送场景用于鲁棒优化

创建时间: 2026-03-17
作者: 王晔宸 + 冷爽 (Team ESGenius)
"""

import numpy as np
import pandas as pd
from datetime import datetime, date, timedelta
from typing import List, Dict, Optional, Tuple, Any
import logging
from pathlib import Path
import random
from scipy import stats

import sys
project_root = Path(__file__).parent.parent.parent
sys.path.append(str(project_root))

try:
    from core.interfaces import ScenarioGenerator
    from core.data_schema import (
        DeliveryScenario, OrderDetail, WeatherData, TrafficCondition, 
        WeatherCondition, OrderItem, DemandForecast
    )
except ImportError:
    sys.path.append(str(project_root / "src"))
    from core.interfaces import ScenarioGenerator
    from core.data_schema import (
        DeliveryScenario, OrderDetail, WeatherData, TrafficCondition, 
        WeatherCondition, OrderItem, DemandForecast
    )

logger = logging.getLogger(__name__)

class DeliveryScenarioGenerator(ScenarioGenerator):
    """配送场景生成器 - 增强版，支持Prophet置信区间和不确定性建模"""
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or self._get_default_config()
        self.historical_data = None
        self.weather_patterns = None
        self.traffic_patterns = None
        self.prophet_forecasts = {}  # 存储Prophet预测结果
        self.prophet_forecaster = None  # Prophet预测器实例
        
        # 随机种子设置
        if 'random_seed' in self.config:
            np.random.seed(self.config['random_seed'])
            random.seed(self.config['random_seed'])
    
    def _get_default_config(self) -> Dict[str, Any]:
        """获取默认配置"""
        return {
            'scenario_types': ['optimistic', 'realistic', 'pessimistic'],
            'demand_variation_range': (0.7, 1.3),  # 需求变化范围
            'weather_impact_factor': 0.25,  # 天气影响因子（增强）
            'traffic_impact_factor': 0.20,  # 交通影响因子（增强）
            'holiday_impact_factor': 0.30,  # 假期影响因子（增强）
            'uncertainty_levels': [0.1, 0.2, 0.3],  # 不确定性水平
            'correlation_strength': 0.4,  # 门店间需求相关性（增强）
            'min_probability': 0.02,  # 最小场景概率
            'max_scenarios': 25,  # 最大场景数（增加）
            'use_prophet_intervals': True,  # 使用Prophet置信区间
            'confidence_levels': [0.1, 0.5, 0.9],  # P10, P50, P90
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
            # Prophet集成配置
            'prophet_integration': {
                'use_confidence_intervals': True,
                'interval_sampling_method': 'monte_carlo',  # 'monte_carlo' or 'quantile'
                'monte_carlo_samples': 1000,
                'confidence_correlation': 0.3,  # 置信区间间的相关性
                'forecast_horizon_days': 7,
                'uncertainty_inflation': 1.2,  # 不确定性膨胀因子
            },
            # 不确定性建模配置
            'uncertainty_modeling': {
                'enable_demand_correlation': True,
                'enable_weather_uncertainty': True,
                'enable_traffic_uncertainty': True,
                'weather_forecast_accuracy': 0.8,  # 天气预报准确率
                'traffic_prediction_accuracy': 0.7,  # 交通预测准确率
                'seasonal_uncertainty_factor': 0.15,  # 季节性不确定性
                'holiday_uncertainty_factor': 0.25,  # 假期不确定性
            }
        }
    
    def set_prophet_forecaster(self, forecaster) -> None:
        """设置Prophet预测器"""
        self.prophet_forecaster = forecaster
        logger.info("Prophet预测器已设置")
    
    def generate_scenarios_with_prophet(self, prophet_forecasts: List[DemandForecast], 
                                      num_scenarios: int = 10) -> List[DeliveryScenario]:
        """使用Prophet置信区间生成场景"""
        logger.info(f"使用Prophet置信区间生成 {num_scenarios} 个配送场景...")
        
        scenarios = []
        
        try:
            # 按门店组织预测数据
            forecasts_by_store = {}
            for forecast in prophet_forecasts:
                store_code = forecast.store_code
                if store_code not in forecasts_by_store:
                    forecasts_by_store[store_code] = []
                forecasts_by_store[store_code].append(forecast)
            
            # 生成基于置信区间的场景
            for i in range(num_scenarios):
                scenario_id = f"prophet_scenario_{i+1}"
                
                # 从置信区间采样需求
                scenario_demand = self._sample_from_prophet_intervals(forecasts_by_store)
                
                # 生成天气和交通场景
                weather_scenario = self._generate_weather_scenario()
                traffic_scenario = self._generate_traffic_scenario()
                
                # 应用外部因子影响
                adjusted_demand = self._apply_external_factors(
                    scenario_demand, weather_scenario, traffic_scenario
                )
                
                # 生成订单
                orders = self._generate_scenario_orders(adjusted_demand, "prophet_based")
                
                # 计算场景概率
                probability = self._calculate_prophet_scenario_probability(
                    scenario_demand, forecasts_by_store, weather_scenario, traffic_scenario
                )
                
                # 创建场景
                scenario = DeliveryScenario(
                    scenario_id=scenario_id,
                    orders=orders,
                    demand_forecast=adjusted_demand,
                    weather_impact=weather_scenario['impact'],
                    traffic_impact=traffic_scenario['impact'],
                    probability=probability,
                    generated_timestamp=datetime.now()
                )
                
                scenarios.append(scenario)
                logger.debug(f"生成Prophet场景 {scenario_id}: {len(orders)} 个订单, 概率 {probability:.3f}")
            
            # 标准化概率
            scenarios = self._normalize_probabilities(scenarios)
            
            logger.info(f"✅ 成功生成 {len(scenarios)} 个Prophet场景")
            return scenarios
            
        except Exception as e:
            logger.error(f"Prophet场景生成失败: {str(e)}")
            # 回退到标准场景生成
            base_demand = {store: 50.0 for store in forecasts_by_store.keys()}
            return self.generate_scenarios(base_demand, num_scenarios)
    
    def _sample_from_prophet_intervals(self, forecasts_by_store: Dict[str, List[DemandForecast]]) -> Dict[str, float]:
        """从Prophet置信区间采样需求"""
        scenario_demand = {}
        
        prophet_config = self.config['prophet_integration']
        sampling_method = prophet_config.get('interval_sampling_method', 'monte_carlo')
        
        for store_code, forecasts in forecasts_by_store.items():
            if not forecasts:
                scenario_demand[store_code] = 50.0  # 默认值
                continue
            
            # 使用最新的预测
            latest_forecast = forecasts[-1]
            intervals = latest_forecast.confidence_intervals
            
            if sampling_method == 'monte_carlo':
                # 蒙特卡洛采样
                p10, p50, p90 = intervals.get('P10', 0), intervals.get('P50', 0), intervals.get('P90', 0)
                
                # 估算分布参数
                if p90 > p10:
                    # 使用Beta分布近似
                    alpha, beta = self._estimate_beta_parameters(p10, p50, p90)
                    sample = np.random.beta(alpha, beta)
                    demand = p10 + sample * (p90 - p10)
                else:
                    demand = p50
            else:
                # 分位数采样
                quantile = np.random.uniform(0.1, 0.9)
                if quantile <= 0.1:
                    demand = intervals.get('P10', 0)
                elif quantile >= 0.9:
                    demand = intervals.get('P90', 0)
                else:
                    # 线性插值
                    p10, p50, p90 = intervals.get('P10', 0), intervals.get('P50', 0), intervals.get('P90', 0)
                    if quantile <= 0.5:
                        t = (quantile - 0.1) / 0.4
                        demand = p10 + t * (p50 - p10)
                    else:
                        t = (quantile - 0.5) / 0.4
                        demand = p50 + t * (p90 - p50)
            
            # 应用不确定性膨胀
            uncertainty_factor = prophet_config['uncertainty_inflation']
            demand *= np.random.normal(1.0, (uncertainty_factor - 1.0) / 3)
            
            scenario_demand[store_code] = max(0, demand)
        
        return scenario_demand
    
    def _estimate_beta_parameters(self, p10: float, p50: float, p90: float) -> Tuple[float, float]:
        """估算Beta分布参数"""
        if p90 <= p10:
            return 2.0, 2.0  # 默认对称分布
        
        # 标准化到[0,1]区间
        norm_p50 = (p50 - p10) / (p90 - p10)
        
        # 使用矩估计法
        if norm_p50 > 0 and norm_p50 < 1:
            # 简化估计：基于中位数位置
            if norm_p50 < 0.5:
                alpha = 2.0
                beta = alpha * (1 - norm_p50) / norm_p50
            else:
                beta = 2.0
                alpha = beta * norm_p50 / (1 - norm_p50)
        else:
            alpha, beta = 2.0, 2.0
        
        return max(0.5, alpha), max(0.5, beta)
    
    def _generate_weather_scenario(self) -> Dict[str, Any]:
        """生成天气场景"""
        weather_scenarios = self.config['weather_scenarios']
        
        # 根据概率选择天气类型
        weather_types = list(weather_scenarios.keys())
        probabilities = [weather_scenarios[wt]['probability'] for wt in weather_types]
        
        selected_weather = np.random.choice(weather_types, p=probabilities)
        weather_config = weather_scenarios[selected_weather]
        
        # 添加不确定性
        uncertainty_config = self.config['uncertainty_modeling']
        if uncertainty_config['enable_weather_uncertainty']:
            accuracy = uncertainty_config['weather_forecast_accuracy']
            # 天气预报不准确时的影响调整
            impact_noise = np.random.normal(0, (1 - accuracy) * 0.1)
            actual_impact = weather_config['demand_impact'] + impact_noise
        else:
            actual_impact = weather_config['demand_impact']
        
        return {
            'type': selected_weather,
            'impact': actual_impact,
            'delivery_impact': weather_config['delivery_impact'],
            'probability': weather_config['probability']
        }
    
    def _generate_traffic_scenario(self) -> Dict[str, Any]:
        """生成交通场景"""
        traffic_scenarios = self.config['traffic_scenarios']
        
        # 根据概率选择交通状况
        traffic_types = list(traffic_scenarios.keys())
        probabilities = [traffic_scenarios[tt]['probability'] for tt in traffic_types]
        
        selected_traffic = np.random.choice(traffic_types, p=probabilities)
        traffic_config = traffic_scenarios[selected_traffic]
        
        # 添加不确定性
        uncertainty_config = self.config['uncertainty_modeling']
        if uncertainty_config['enable_traffic_uncertainty']:
            accuracy = uncertainty_config['traffic_prediction_accuracy']
            # 交通预测不准确时的影响调整
            delay_noise = np.random.normal(0, (1 - accuracy) * 0.2)
            actual_delay = traffic_config['delay_factor'] + delay_noise
        else:
            actual_delay = traffic_config['delay_factor']
        
        return {
            'type': selected_traffic,
            'impact': (actual_delay - 1.0) * 0.5,  # 转换为影响因子
            'delay_factor': actual_delay,
            'speed_multiplier': traffic_config['speed_multiplier'],
            'probability': traffic_config['probability']
        }
    
    def _apply_external_factors(self, base_demand: Dict[str, float], 
                              weather_scenario: Dict[str, Any], 
                              traffic_scenario: Dict[str, Any]) -> Dict[str, float]:
        """应用外部因子影响"""
        adjusted_demand = {}
        
        weather_impact = weather_scenario['impact']
        traffic_impact = traffic_scenario['impact']
        
        # 获取季节因子
        current_month = datetime.now().month
        if current_month in [3, 4, 5]:
            season = 'spring'
        elif current_month in [6, 7, 8]:
            season = 'summer'
        elif current_month in [9, 10, 11]:
            season = 'autumn'
        else:
            season = 'winter'
        
        seasonal_factor = self.config['seasonal_factors'][season]
        
        for store_code, base_value in base_demand.items():
            # 应用天气影响
            weather_multiplier = 1.0 + weather_impact * self.config['weather_impact_factor']
            
            # 应用交通影响（主要影响配送，间接影响需求）
            traffic_multiplier = 1.0 + traffic_impact * self.config['traffic_impact_factor'] * 0.3
            
            # 应用季节因子
            seasonal_multiplier = seasonal_factor
            
            # 组合所有影响
            total_multiplier = weather_multiplier * traffic_multiplier * seasonal_multiplier
            
            adjusted_demand[store_code] = base_value * total_multiplier
        
        return adjusted_demand
    
    def _calculate_prophet_scenario_probability(self, scenario_demand: Dict[str, float],
                                             forecasts_by_store: Dict[str, List[DemandForecast]],
                                             weather_scenario: Dict[str, Any],
                                             traffic_scenario: Dict[str, Any]) -> float:
        """计算Prophet场景概率"""
        try:
            # 基础概率
            base_prob = 1.0
            
            # 需求概率（基于Prophet置信区间）
            demand_prob = self._calculate_prophet_demand_probability(scenario_demand, forecasts_by_store)
            
            # 天气概率
            weather_prob = weather_scenario['probability']
            
            # 交通概率
            traffic_prob = traffic_scenario['probability']
            
            # 组合概率
            total_prob = base_prob * demand_prob * weather_prob * traffic_prob
            
            return max(self.config['min_probability'], total_prob)
            
        except Exception as e:
            logger.warning(f"Prophet场景概率计算失败: {str(e)}")
            return self.config['min_probability']
    
    def _calculate_prophet_demand_probability(self, scenario_demand: Dict[str, float],
                                           forecasts_by_store: Dict[str, List[DemandForecast]]) -> float:
        """计算基于Prophet的需求概率"""
        if not scenario_demand or not forecasts_by_store:
            return 1.0
        
        total_log_prob = 0.0
        valid_stores = 0
        
        for store_code, demand in scenario_demand.items():
            if store_code not in forecasts_by_store:
                continue
            
            forecasts = forecasts_by_store[store_code]
            if not forecasts:
                continue
            
            latest_forecast = forecasts[-1]
            intervals = latest_forecast.confidence_intervals
            
            p10 = intervals.get('P10', 0)
            p50 = intervals.get('P50', 0)
            p90 = intervals.get('P90', 0)
            
            if p90 > p10:
                # 计算需求在置信区间内的概率密度
                if demand < p10:
                    # 低于P10
                    prob = 0.1 * np.exp(-(p10 - demand) / (p50 - p10))
                elif demand > p90:
                    # 高于P90
                    prob = 0.1 * np.exp(-(demand - p90) / (p90 - p50))
                else:
                    # 在P10-P90之间
                    if demand <= p50:
                        prob = 0.1 + 0.4 * (demand - p10) / (p50 - p10)
                    else:
                        prob = 0.5 + 0.4 * (p90 - demand) / (p90 - p50)
                
                total_log_prob += np.log(max(0.01, prob))
                valid_stores += 1
        
        if valid_stores > 0:
            avg_log_prob = total_log_prob / valid_stores
            return max(0.01, np.exp(avg_log_prob))
        else:
            return 1.0
    
    def generate_scenarios(self, base_demand: Dict[str, float], 
                         num_scenarios: int = 10) -> List[DeliveryScenario]:
        """生成配送场景"""
        logger.info(f"生成 {num_scenarios} 个配送场景...")
        
        scenarios = []
        
        try:
            # 检查是否有Prophet预测数据
            if self.config['use_prophet_intervals'] and self.prophet_forecasts:
                logger.info("使用Prophet置信区间生成场景")
                return self._generate_scenarios_with_prophet_data(base_demand, num_scenarios)
            
            # 生成不同类型的场景
            scenario_types = self._determine_scenario_types(num_scenarios)
            
            for i, scenario_type in enumerate(scenario_types):
                scenario_id = f"scenario_{i+1}_{scenario_type}"
                
                # 生成场景需求
                scenario_demand = self._generate_scenario_demand(base_demand, scenario_type)
                
                # 生成订单
                orders = self._generate_scenario_orders(scenario_demand, scenario_type)
                
                # 计算场景概率
                probability = self._calculate_scenario_probability_simple(scenario_type, num_scenarios)
                
                # 创建场景
                scenario = DeliveryScenario(
                    scenario_id=scenario_id,
                    orders=orders,
                    demand_forecast=scenario_demand,
                    weather_impact=self._generate_weather_impact(scenario_type),
                    traffic_impact=self._generate_traffic_impact(scenario_type),
                    probability=probability,
                    generated_timestamp=datetime.now()
                )
                
                scenarios.append(scenario)
                logger.debug(f"生成场景 {scenario_id}: {len(orders)} 个订单, 概率 {probability:.3f}")
            
            # 标准化概率
            scenarios = self._normalize_probabilities(scenarios)
            
            logger.info(f"✅ 成功生成 {len(scenarios)} 个场景")
            return scenarios
            
        except Exception as e:
            logger.error(f"场景生成失败: {str(e)}")
            raise
    
    def _generate_scenarios_with_prophet_data(self, base_demand: Dict[str, float], 
                                            num_scenarios: int) -> List[DeliveryScenario]:
        """使用Prophet数据生成场景"""
        scenarios = []
        
        # 将Prophet预测转换为场景
        prophet_forecasts_list = []
        for store_code in base_demand.keys():
            if store_code in self.prophet_forecasts:
                prophet_forecasts_list.extend(self.prophet_forecasts[store_code])
        
        if prophet_forecasts_list:
            return self.generate_scenarios_with_prophet(prophet_forecasts_list, num_scenarios)
        else:
            # 回退到标准方法
            return self._generate_standard_scenarios(base_demand, num_scenarios)
    
    def _generate_standard_scenarios(self, base_demand: Dict[str, float], 
                                   num_scenarios: int) -> List[DeliveryScenario]:
        """生成标准场景（不使用Prophet）"""
        scenarios = []
        scenario_types = self._determine_scenario_types(num_scenarios)
        
        for i, scenario_type in enumerate(scenario_types):
            scenario_id = f"standard_scenario_{i+1}_{scenario_type}"
            
            # 生成场景需求
            scenario_demand = self._generate_scenario_demand(base_demand, scenario_type)
            
            # 生成订单
            orders = self._generate_scenario_orders(scenario_demand, scenario_type)
            
            # 计算场景概率
            probability = self._calculate_scenario_probability_simple(scenario_type, num_scenarios)
            
            # 创建场景
            scenario = DeliveryScenario(
                scenario_id=scenario_id,
                orders=orders,
                demand_forecast=scenario_demand,
                weather_impact=self._generate_weather_impact(scenario_type),
                traffic_impact=self._generate_traffic_impact(scenario_type),
                probability=probability,
                generated_timestamp=datetime.now()
            )
            
            scenarios.append(scenario)
        
        return self._normalize_probabilities(scenarios)
    
    def validate_scenario_consistency(self, scenario: DeliveryScenario) -> bool:
        """验证场景一致性"""
        try:
            # 检查基本属性
            if not scenario.scenario_id or not scenario.orders:
                logger.warning(f"场景 {scenario.scenario_id} 缺少基本属性")
                return False
            
            # 检查概率范围
            if not (0.0 <= scenario.probability <= 1.0):
                logger.warning(f"场景 {scenario.scenario_id} 概率超出范围: {scenario.probability}")
                return False
            
            # 检查需求预测一致性
            if not scenario.demand_forecast:
                logger.warning(f"场景 {scenario.scenario_id} 缺少需求预测")
                return False
            
            # 检查订单与需求预测的一致性
            order_stores = set(order.fulfillment_store_code for order in scenario.orders)
            forecast_stores = set(scenario.demand_forecast.keys())
            
            if not order_stores.issubset(forecast_stores):
                missing_stores = order_stores - forecast_stores
                logger.warning(f"场景 {scenario.scenario_id} 订单门店 {missing_stores} 不在需求预测中")
                return False
            
            # 检查影响因子范围
            if not (-1.0 <= scenario.weather_impact <= 1.0):
                logger.warning(f"场景 {scenario.scenario_id} 天气影响超出范围: {scenario.weather_impact}")
                return False
            
            if not (-1.0 <= scenario.traffic_impact <= 1.0):
                logger.warning(f"场景 {scenario.scenario_id} 交通影响超出范围: {scenario.traffic_impact}")
                return False
            
            # 检查订单数据完整性
            for order in scenario.orders:
                if not order.order_id or not order.fulfillment_store_code:
                    logger.warning(f"场景 {scenario.scenario_id} 包含无效订单")
                    return False
                
                if order.total_quantity <= 0 or order.unique_sku_count <= 0:
                    logger.warning(f"场景 {scenario.scenario_id} 订单 {order.order_id} 数量无效")
                    return False
            
            # 检查需求值合理性
            for store_code, demand in scenario.demand_forecast.items():
                if demand < 0:
                    logger.warning(f"场景 {scenario.scenario_id} 门店 {store_code} 需求为负: {demand}")
                    return False
                
                if demand > 1000:  # 假设单店日需求不超过1000
                    logger.warning(f"场景 {scenario.scenario_id} 门店 {store_code} 需求过高: {demand}")
                    return False
            
            return True
            
        except Exception as e:
            logger.error(f"场景一致性验证失败: {str(e)}")
            return False
        """生成配送场景"""
        logger.info(f"生成 {num_scenarios} 个配送场景...")
        
        scenarios = []
        
        try:
            # 生成不同类型的场景
            scenario_types = self._determine_scenario_types(num_scenarios)
            
            for i, scenario_type in enumerate(scenario_types):
                scenario_id = f"scenario_{i+1}_{scenario_type}"
                
                # 生成场景需求
                scenario_demand = self._generate_scenario_demand(base_demand, scenario_type)
                
                # 生成订单
                orders = self._generate_scenario_orders(scenario_demand, scenario_type)
                
                # 计算场景概率
                probability = self._calculate_scenario_probability_simple(scenario_type, num_scenarios)
                
                # 创建场景
                scenario = DeliveryScenario(
                    scenario_id=scenario_id,
                    orders=orders,
                    demand_forecast=scenario_demand,
                    weather_impact=self._generate_weather_impact(scenario_type),
                    traffic_impact=self._generate_traffic_impact(scenario_type),
                    probability=probability,
                    generated_timestamp=datetime.now()
                )
                
                scenarios.append(scenario)
                logger.debug(f"生成场景 {scenario_id}: {len(orders)} 个订单, 概率 {probability:.3f}")
            
            # 标准化概率
            scenarios = self._normalize_probabilities(scenarios)
            
            logger.info(f"✅ 成功生成 {len(scenarios)} 个场景")
            return scenarios
            
        except Exception as e:
            logger.error(f"场景生成失败: {str(e)}")
            raise
    
    def calculate_scenario_probability(self, scenario: DeliveryScenario) -> float:
        """计算场景概率"""
        try:
            # 基础概率
            base_prob = 1.0
            
            # 需求概率
            demand_prob = self._calculate_demand_probability(scenario.demand_forecast)
            
            # 天气概率
            weather_prob = self._calculate_weather_probability(scenario.weather_impact)
            
            # 交通概率
            traffic_prob = self._calculate_traffic_probability(scenario.traffic_impact)
            
            # 组合概率
            total_prob = base_prob * demand_prob * weather_prob * traffic_prob
            
            return max(self.config['min_probability'], total_prob)
            
        except Exception as e:
            logger.warning(f"概率计算失败: {str(e)}")
            return self.config['min_probability']
    
    def incorporate_external_factors(self, scenario: DeliveryScenario, 
                                   weather: WeatherData, 
                                   traffic: List[TrafficCondition]) -> DeliveryScenario:
        """整合外部因子"""
        logger.debug(f"整合外部因子到场景 {scenario.scenario_id}")
        
        try:
            # 计算天气影响
            weather_impact = self._calculate_weather_impact(weather)
            
            # 计算交通影响
            traffic_impact = self._calculate_traffic_impact(traffic)
            
            # 调整需求预测
            adjusted_demand = {}
            for store_code, base_demand in scenario.demand_forecast.items():
                # 应用天气和交通影响
                weather_multiplier = 1.0 + weather_impact * self.config['weather_impact_factor']
                traffic_multiplier = 1.0 + traffic_impact * self.config['traffic_impact_factor']
                
                adjusted_demand[store_code] = base_demand * weather_multiplier * traffic_multiplier
            
            # 重新生成订单
            adjusted_orders = self._generate_scenario_orders(adjusted_demand, "realistic")
            
            # 创建调整后的场景
            adjusted_scenario = DeliveryScenario(
                scenario_id=f"{scenario.scenario_id}_adjusted",
                orders=adjusted_orders,
                demand_forecast=adjusted_demand,
                weather_impact=weather_impact,
                traffic_impact=traffic_impact,
                probability=scenario.probability,
                generated_timestamp=datetime.now()
            )
            
            return adjusted_scenario
            
        except Exception as e:
            logger.error(f"外部因子整合失败: {str(e)}")
            return scenario
    
    # ==================== 私有方法 ====================
    
    def _determine_scenario_types(self, num_scenarios: int) -> List[str]:
        """确定场景类型分布"""
        types = []
        
        # 基础场景类型分布
        type_distribution = {
            'optimistic': 0.2,
            'realistic': 0.6,
            'pessimistic': 0.2
        }
        
        for scenario_type, ratio in type_distribution.items():
            count = int(num_scenarios * ratio)
            types.extend([scenario_type] * count)
        
        # 补充到目标数量
        while len(types) < num_scenarios:
            types.append('realistic')
        
        # 随机打乱
        random.shuffle(types)
        
        return types[:num_scenarios]
    
    def _generate_scenario_demand(self, base_demand: Dict[str, float], 
                                scenario_type: str) -> Dict[str, float]:
        """生成场景需求"""
        scenario_demand = {}
        
        # 根据场景类型设置变化参数
        if scenario_type == 'optimistic':
            mean_multiplier = 1.1
            std_multiplier = 0.1
        elif scenario_type == 'pessimistic':
            mean_multiplier = 0.9
            std_multiplier = 0.15
        else:  # realistic
            mean_multiplier = 1.0
            std_multiplier = 0.12
        
        # 生成相关的需求变化
        store_codes = list(base_demand.keys())
        n_stores = len(store_codes)
        
        if n_stores > 0:
            # 生成相关随机数
            correlation_matrix = self._create_correlation_matrix(n_stores)
            random_factors = np.random.multivariate_normal(
                mean=[mean_multiplier] * n_stores,
                cov=correlation_matrix * (std_multiplier ** 2)
            )
            
            # 应用到各门店
            for i, store_code in enumerate(store_codes):
                multiplier = max(0.5, min(2.0, random_factors[i]))  # 限制在合理范围内
                scenario_demand[store_code] = base_demand[store_code] * multiplier
        
        return scenario_demand
    
    def _generate_scenario_orders(self, demand_forecast: Dict[str, float], 
                                scenario_type: str) -> List[OrderDetail]:
        """生成场景订单"""
        orders = []
        
        for store_code, demand in demand_forecast.items():
            # 将需求转换为订单数量
            num_orders = max(1, int(np.random.poisson(demand)))
            
            for i in range(num_orders):
                # 生成订单商品
                num_items = max(1, int(np.random.poisson(2.5)))  # 平均2.5个商品
                items = []
                
                for j in range(num_items):
                    item = OrderItem(
                        sku_id=f"sku_{j}",
                        sku_name=f"Product {j}",
                        quantity=max(1, int(np.random.poisson(1.5)))
                    )
                    items.append(item)
                
                # 创建订单
                order = OrderDetail(
                    order_id=f"{store_code}_order_{i}",
                    user_id=f"user_{i}",
                    fulfillment_store_code=store_code,
                    order_date=date.today(),
                    items=items,
                    total_quantity=sum(item.quantity for item in items),
                    unique_sku_count=len(items)
                )
                orders.append(order)
        
        return orders
    
    def _create_correlation_matrix(self, n_stores: int) -> np.ndarray:
        """创建门店间需求相关性矩阵"""
        correlation = self.config.get('correlation_strength', 0.4)
        
        # 创建相关性矩阵
        matrix = np.eye(n_stores)
        for i in range(n_stores):
            for j in range(i + 1, n_stores):
                # 随机相关性
                corr_value = np.random.uniform(-correlation, correlation)
                matrix[i, j] = corr_value
                matrix[j, i] = corr_value
        
        # 确保矩阵正定
        eigenvals = np.linalg.eigvals(matrix)
        if np.min(eigenvals) <= 0:
            matrix += (abs(np.min(eigenvals)) + 0.01) * np.eye(n_stores)
        
        return matrix
    
    def _generate_weather_impact(self, scenario_type: str) -> float:
        """生成天气影响"""
        if scenario_type == 'optimistic':
            return np.random.uniform(-0.1, 0.1)  # 天气良好
        elif scenario_type == 'pessimistic':
            return np.random.uniform(0.1, 0.3)   # 恶劣天气
        else:
            return np.random.uniform(-0.05, 0.15)  # 一般天气
    
    def _generate_traffic_impact(self, scenario_type: str) -> float:
        """生成交通影响"""
        if scenario_type == 'optimistic':
            return np.random.uniform(-0.1, 0.05)  # 交通顺畅
        elif scenario_type == 'pessimistic':
            return np.random.uniform(0.1, 0.25)   # 交通拥堵
        else:
            return np.random.uniform(-0.05, 0.1)   # 一般交通
    
    def _calculate_scenario_probability_simple(self, scenario_type: str, 
                                             total_scenarios: int) -> float:
        """简化的场景概率计算"""
        # 基础概率分布
        base_probabilities = {
            'optimistic': 0.2,
            'realistic': 0.6,
            'pessimistic': 0.2
        }
        
        base_prob = base_probabilities.get(scenario_type, 0.33)
        
        # 考虑场景总数
        return base_prob / total_scenarios * 3  # 标准化
    
    def _calculate_demand_probability(self, demand_forecast: Dict[str, float]) -> float:
        """计算需求概率"""
        # 简化实现：基于需求变化程度
        if not demand_forecast:
            return 1.0
        
        demands = list(demand_forecast.values())
        cv = np.std(demands) / np.mean(demands) if np.mean(demands) > 0 else 0
        
        # 变异系数越小，概率越高
        return max(0.1, 1.0 - cv)
    
    def _calculate_weather_probability(self, weather_impact: float) -> float:
        """计算天气概率"""
        # 基于天气影响程度的概率
        abs_impact = abs(weather_impact)
        return max(0.1, 1.0 - abs_impact * 2)
    
    def _calculate_traffic_probability(self, traffic_impact: float) -> float:
        """计算交通概率"""
        # 基于交通影响程度的概率
        abs_impact = abs(traffic_impact)
        return max(0.1, 1.0 - abs_impact * 2)
    
    def _calculate_weather_impact(self, weather: WeatherData) -> float:
        """计算天气影响"""
        impact = 0.0
        
        # 温度影响
        if weather.temperature_high > 30 or weather.temperature_high < 15:
            impact += 0.1
        
        # 降雨影响
        if weather.rainfall > 10:
            impact += 0.2
        elif weather.rainfall > 5:
            impact += 0.1
        
        # 天气状况影响
        if weather.condition == WeatherCondition.STORMY:
            impact += 0.3
        elif weather.condition == WeatherCondition.RAINY:
            impact += 0.15
        elif weather.condition == WeatherCondition.FOGGY:
            impact += 0.1
        
        return min(0.5, impact)  # 限制最大影响
    
    def _calculate_traffic_impact(self, traffic_conditions: List[TrafficCondition]) -> float:
        """计算交通影响"""
        if not traffic_conditions:
            return 0.0
        
        # 计算平均拥堵水平
        avg_congestion = np.mean([tc.congestion_level for tc in traffic_conditions])
        
        # 转换为影响因子
        if avg_congestion >= 4:
            return 0.25
        elif avg_congestion >= 3:
            return 0.15
        elif avg_congestion >= 2:
            return 0.05
        else:
            return -0.05  # 交通顺畅有正面影响
    
    def _normalize_probabilities(self, scenarios: List[DeliveryScenario]) -> List[DeliveryScenario]:
        """标准化场景概率"""
        total_prob = sum(scenario.probability for scenario in scenarios)
        
        if total_prob > 0:
            for scenario in scenarios:
                scenario.probability = scenario.probability / total_prob
        else:
            # 如果总概率为0，平均分配
            uniform_prob = 1.0 / len(scenarios)
            for scenario in scenarios:
                scenario.probability = uniform_prob
        
        return scenarios

# ==================== 工厂函数 ====================

def create_scenario_generator(config: Dict[str, Any] = None) -> DeliveryScenarioGenerator:
    """创建场景生成器实例"""
    return DeliveryScenarioGenerator(config)

# ==================== 测试和演示 ====================

if __name__ == "__main__":
    print("🎲 测试场景生成器...")
    
    # 创建场景生成器
    generator = DeliveryScenarioGenerator()
    print("✅ 场景生成器创建成功")
    
    # 创建基础需求数据
    base_demand = {
        '417': 50.0,
        '331': 45.0,
        '213': 40.0,
        '215': 35.0,
        '878': 30.0
    }
    
    print(f"📊 基础需求数据: {len(base_demand)} 个门店")
    
    try:
        # 生成场景
        print("🚀 生成配送场景...")
        scenarios = generator.generate_scenarios(base_demand, num_scenarios=5)
        
        print(f"✅ 场景生成完成，共 {len(scenarios)} 个场景")
        
        # 显示场景信息
        print("\n📋 场景详情:")
        total_prob = 0
        for scenario in scenarios:
            print(f"   {scenario.scenario_id}:")
            print(f"     订单数: {len(scenario.orders)}")
            print(f"     概率: {scenario.probability:.3f}")
            print(f"     天气影响: {scenario.weather_impact:.3f}")
            print(f"     交通影响: {scenario.traffic_impact:.3f}")
            total_prob += scenario.probability
        
        print(f"\n📊 总概率: {total_prob:.3f}")
        
        # 测试外部因子整合
        print("\n🌤️ 测试外部因子整合...")
        sample_weather = WeatherData(
            date=date.today(),
            temperature_high=28.0,
            temperature_low=22.0,
            humidity=75.0,
            condition=WeatherCondition.RAINY,
            rainfall=8.0
        )
        
        sample_traffic = [
            TrafficCondition(
                timestamp=datetime.now(),
                road_segment="Central-Causeway Bay",
                speed_kmh=25.0,
                congestion_level=3,
                travel_time_minutes=20.0
            )
        ]
        
        adjusted_scenario = generator.incorporate_external_factors(
            scenarios[0], sample_weather, sample_traffic
        )
        
        print(f"✅ 外部因子整合完成")
        print(f"   调整后场景: {adjusted_scenario.scenario_id}")
        print(f"   天气影响: {adjusted_scenario.weather_impact:.3f}")
        print(f"   交通影响: {adjusted_scenario.traffic_impact:.3f}")
        
        print("\n🎉 场景生成器测试完成！")
        
    except Exception as e:
        print(f"❌ 测试失败: {str(e)}")