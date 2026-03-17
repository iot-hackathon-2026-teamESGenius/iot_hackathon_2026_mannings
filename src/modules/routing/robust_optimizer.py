#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
万宁SLA优化系统 - 鲁棒优化器
基于多场景的鲁棒路径优化

创建时间: 2026-03-17
作者: 王晔宸 + 冷爽 (Team ESGenius)
"""

import numpy as np
import pandas as pd
from datetime import datetime
from typing import List, Dict, Optional, Tuple, Any
import logging
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
import copy

import sys
project_root = Path(__file__).parent.parent.parent
sys.path.append(str(project_root))

try:
    from core.interfaces import RobustOptimizer, CVRPTWOptimizer
    from core.data_schema import (
        DeliveryScenario, RouteOptimizationResult, RobustOptimizationResult
    )
    from .ortools_optimizer import ORToolsOptimizer
except ImportError:
    sys.path.append(str(project_root / "src"))
    from core.interfaces import RobustOptimizer, CVRPTWOptimizer
    from core.data_schema import (
        DeliveryScenario, RouteOptimizationResult, RobustOptimizationResult
    )
    from modules.routing.ortools_optimizer import ORToolsOptimizer

logger = logging.getLogger(__name__)

class DeliveryRobustOptimizer(RobustOptimizer):
    """配送鲁棒优化器"""
    
    def __init__(self, base_optimizer: CVRPTWOptimizer = None, config: Dict[str, Any] = None):
        self.config = config or self._get_default_config()
        self.base_optimizer = base_optimizer or ORToolsOptimizer()
        self.optimization_history = []
        
    def _get_default_config(self) -> Dict[str, Any]:
        """获取默认配置"""
        return {
            'selection_strategies': ['min_max', 'expected_value', 'weighted_sum', 'robust_deviation'],
            'risk_tolerance': 0.1,  # 风险容忍度
            'robustness_weight': 0.3,  # 鲁棒性权重
            'performance_weight': 0.7,  # 性能权重
            'confidence_level': 0.95,  # 置信水平
            'max_parallel_optimizations': 4,  # 最大并行优化数
            'scenario_weight_threshold': 0.01,  # 场景权重阈值
            'convergence_tolerance': 0.001,  # 收敛容忍度
            'max_iterations': 10  # 最大迭代次数
        }
    
    def optimize_robust(self, scenarios: List[DeliveryScenario], 
                       strategy: str = "min_max") -> RobustOptimizationResult:
        """执行鲁棒优化"""
        logger.info(f"开始鲁棒优化，场景数: {len(scenarios)}, 策略: {strategy}")
        
        try:
            # 验证输入
            if not scenarios:
                raise ValueError("场景列表不能为空")
            
            if strategy not in self.config['selection_strategies']:
                raise ValueError(f"不支持的选择策略: {strategy}")
            
            # 过滤低权重场景
            filtered_scenarios = self._filter_scenarios(scenarios)
            logger.info(f"过滤后场景数: {len(filtered_scenarios)}")
            
            # 并行优化所有场景
            route_results = self._optimize_all_scenarios(filtered_scenarios)
            
            if not route_results:
                raise ValueError("所有场景优化都失败")
            
            # 选择最优解
            selected_route = self._select_best_solution(route_results, strategy)
            
            # 评估鲁棒性
            robustness_score = self._evaluate_robustness(selected_route, route_results)
            
            # 计算置信水平
            confidence_level = self._calculate_confidence_level(route_results, selected_route)
            
            # 创建结果
            result = RobustOptimizationResult(
                scenarios=filtered_scenarios,
                route_results=route_results,
                selected_route=selected_route,
                selection_strategy=strategy,
                robustness_score=robustness_score,
                confidence_level=confidence_level
            )
            
            # 记录优化历史
            self.optimization_history.append({
                'timestamp': datetime.now(),
                'num_scenarios': len(scenarios),
                'strategy': strategy,
                'robustness_score': robustness_score,
                'total_cost': selected_route.total_cost
            })
            
            logger.info(f"✅ 鲁棒优化完成，鲁棒性分数: {robustness_score:.3f}")
            return result
            
        except Exception as e:
            logger.error(f"鲁棒优化失败: {str(e)}")
            raise
    
    def evaluate_robustness(self, result: RobustOptimizationResult) -> float:
        """评估鲁棒性"""
        try:
            if not result.route_results:
                return 0.0
            
            # 计算性能指标的变异系数
            costs = [r.total_cost for r in result.route_results]
            times = [r.total_time for r in result.route_results]
            distances = [r.total_distance for r in result.route_results]
            
            # 成本鲁棒性
            cost_cv = np.std(costs) / np.mean(costs) if np.mean(costs) > 0 else 0
            
            # 时间鲁棒性
            time_cv = np.std(times) / np.mean(times) if np.mean(times) > 0 else 0
            
            # 距离鲁棒性
            distance_cv = np.std(distances) / np.mean(distances) if np.mean(distances) > 0 else 0
            
            # 综合鲁棒性分数（变异系数越小，鲁棒性越好）
            robustness_score = 1.0 - (cost_cv * 0.5 + time_cv * 0.3 + distance_cv * 0.2)
            
            return max(0.0, min(1.0, robustness_score))
            
        except Exception as e:
            logger.error(f"鲁棒性评估失败: {str(e)}")
            return 0.0
    
    def select_best_solution(self, results: List[RouteOptimizationResult], 
                           strategy: str) -> RouteOptimizationResult:
        """选择最优解"""
        if not results:
            raise ValueError("结果列表不能为空")
        
        logger.info(f"使用策略 {strategy} 选择最优解...")
        
        if strategy == "min_max":
            return self._select_min_max(results)
        elif strategy == "expected_value":
            return self._select_expected_value(results)
        elif strategy == "weighted_sum":
            return self._select_weighted_sum(results)
        elif strategy == "robust_deviation":
            return self._select_robust_deviation(results)
        else:
            logger.warning(f"未知策略 {strategy}，使用默认策略")
            return self._select_expected_value(results)
    
    # ==================== 私有方法 ====================
    
    def _filter_scenarios(self, scenarios: List[DeliveryScenario]) -> List[DeliveryScenario]:
        """过滤低权重场景"""
        threshold = self.config['scenario_weight_threshold']
        filtered = [s for s in scenarios if s.probability >= threshold]
        
        if not filtered:
            # 如果所有场景都被过滤，保留概率最高的几个
            sorted_scenarios = sorted(scenarios, key=lambda x: x.probability, reverse=True)
            filtered = sorted_scenarios[:min(5, len(sorted_scenarios))]
        
        return filtered
    
    def _optimize_all_scenarios(self, scenarios: List[DeliveryScenario]) -> List[RouteOptimizationResult]:
        """并行优化所有场景"""
        logger.info("开始并行优化所有场景...")
        
        results = []
        max_workers = min(self.config['max_parallel_optimizations'], len(scenarios))
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # 提交优化任务
            future_to_scenario = {}
            for scenario in scenarios:
                future = executor.submit(self._optimize_single_scenario, scenario)
                future_to_scenario[future] = scenario
            
            # 收集结果
            for future in as_completed(future_to_scenario):
                scenario = future_to_scenario[future]
                try:
                    result = future.result(timeout=60)  # 60秒超时
                    if result:
                        results.append(result)
                        logger.debug(f"场景 {scenario.scenario_id} 优化完成")
                    else:
                        logger.warning(f"场景 {scenario.scenario_id} 优化失败")
                except Exception as e:
                    logger.error(f"场景 {scenario.scenario_id} 优化异常: {str(e)}")
        
        logger.info(f"并行优化完成，成功 {len(results)}/{len(scenarios)} 个场景")
        return results
    
    def _optimize_single_scenario(self, scenario: DeliveryScenario) -> Optional[RouteOptimizationResult]:
        """优化单个场景"""
        try:
            # 创建车辆数据（简化）
            vehicles = [
                {'id': f'vehicle_{i}', 'capacity': 100} 
                for i in range(self.config.get('max_vehicles', 3))
            ]
            
            # 创建约束
            constraints = {
                'max_route_time': 8 * 60,  # 8小时
                'service_time': 15  # 15分钟
            }
            
            # 执行优化
            result = self.base_optimizer.optimize(scenario.orders, vehicles, constraints)
            result.scenario_id = scenario.scenario_id
            
            return result
            
        except Exception as e:
            logger.error(f"单场景优化失败 {scenario.scenario_id}: {str(e)}")
            return None
    
    def _select_min_max(self, results: List[RouteOptimizationResult]) -> RouteOptimizationResult:
        """Min-Max策略：选择最坏情况下表现最好的解"""
        logger.debug("使用Min-Max策略选择解")
        
        # 找到每个解在所有场景中的最大成本
        max_costs = []
        for result in results:
            max_cost = result.total_cost  # 简化：使用当前成本作为最大成本
            max_costs.append(max_cost)
        
        # 选择最大成本最小的解
        min_max_index = np.argmin(max_costs)
        return results[min_max_index]
    
    def _select_expected_value(self, results: List[RouteOptimizationResult]) -> RouteOptimizationResult:
        """期望值策略：选择期望成本最小的解"""
        logger.debug("使用期望值策略选择解")
        
        # 计算加权平均成本（简化：假设等权重）
        expected_costs = []
        for result in results:
            expected_cost = result.total_cost  # 简化处理
            expected_costs.append(expected_cost)
        
        # 选择期望成本最小的解
        min_expected_index = np.argmin(expected_costs)
        return results[min_expected_index]
    
    def _select_weighted_sum(self, results: List[RouteOptimizationResult]) -> RouteOptimizationResult:
        """加权和策略：平衡性能和鲁棒性"""
        logger.debug("使用加权和策略选择解")
        
        performance_weight = self.config['performance_weight']
        robustness_weight = self.config['robustness_weight']
        
        scores = []
        costs = [r.total_cost for r in results]
        times = [r.total_time for r in results]
        
        # 标准化指标
        min_cost, max_cost = min(costs), max(costs)
        min_time, max_time = min(times), max(times)
        
        for result in results:
            # 性能分数（成本和时间）
            cost_score = 1.0 - (result.total_cost - min_cost) / (max_cost - min_cost + 1e-6)
            time_score = 1.0 - (result.total_time - min_time) / (max_time - min_time + 1e-6)
            performance_score = (cost_score + time_score) / 2
            
            # 鲁棒性分数（简化：基于SLA合规率）
            robustness_score = result.sla_compliance_rate
            
            # 综合分数
            total_score = (performance_weight * performance_score + 
                          robustness_weight * robustness_score)
            scores.append(total_score)
        
        # 选择综合分数最高的解
        best_index = np.argmax(scores)
        return results[best_index]
    
    def _select_robust_deviation(self, results: List[RouteOptimizationResult]) -> RouteOptimizationResult:
        """鲁棒偏差策略：考虑解的稳定性"""
        logger.debug("使用鲁棒偏差策略选择解")
        
        # 计算每个解的偏差分数
        deviation_scores = []
        costs = [r.total_cost for r in results]
        mean_cost = np.mean(costs)
        
        for result in results:
            # 计算与平均值的偏差
            deviation = abs(result.total_cost - mean_cost) / mean_cost
            
            # 偏差越小，分数越高
            deviation_score = 1.0 / (1.0 + deviation)
            deviation_scores.append(deviation_score)
        
        # 选择偏差分数最高的解
        best_index = np.argmax(deviation_scores)
        return results[best_index]
    
    def _evaluate_robustness(self, selected_route: RouteOptimizationResult, 
                           all_results: List[RouteOptimizationResult]) -> float:
        """评估选定路径的鲁棒性"""
        if len(all_results) <= 1:
            return 1.0
        
        # 计算选定解与其他解的性能差异
        selected_cost = selected_route.total_cost
        other_costs = [r.total_cost for r in all_results if r != selected_route]
        
        if not other_costs:
            return 1.0
        
        # 计算相对性能差异
        max_diff = max(abs(cost - selected_cost) / selected_cost for cost in other_costs)
        
        # 转换为鲁棒性分数
        robustness = 1.0 / (1.0 + max_diff)
        
        return robustness
    
    def _calculate_confidence_level(self, all_results: List[RouteOptimizationResult], 
                                  selected_route: RouteOptimizationResult) -> float:
        """计算置信水平"""
        if len(all_results) <= 1:
            return 1.0
        
        # 基于解的一致性计算置信水平
        costs = [r.total_cost for r in all_results]
        selected_cost = selected_route.total_cost
        
        # 计算选定解在所有解中的排名
        better_count = sum(1 for cost in costs if cost <= selected_cost)
        confidence = better_count / len(costs)
        
        return confidence
    
    def get_optimization_history(self) -> List[Dict[str, Any]]:
        """获取优化历史"""
        return self.optimization_history.copy()
    
    def get_robustness_analysis(self, result: RobustOptimizationResult) -> Dict[str, Any]:
        """获取鲁棒性分析报告"""
        if not result.route_results:
            return {}
        
        costs = [r.total_cost for r in result.route_results]
        times = [r.total_time for r in result.route_results]
        distances = [r.total_distance for r in result.route_results]
        sla_rates = [r.sla_compliance_rate for r in result.route_results]
        
        analysis = {
            'cost_statistics': {
                'mean': np.mean(costs),
                'std': np.std(costs),
                'min': np.min(costs),
                'max': np.max(costs),
                'cv': np.std(costs) / np.mean(costs) if np.mean(costs) > 0 else 0
            },
            'time_statistics': {
                'mean': np.mean(times),
                'std': np.std(times),
                'min': np.min(times),
                'max': np.max(times),
                'cv': np.std(times) / np.mean(times) if np.mean(times) > 0 else 0
            },
            'distance_statistics': {
                'mean': np.mean(distances),
                'std': np.std(distances),
                'min': np.min(distances),
                'max': np.max(distances),
                'cv': np.std(distances) / np.mean(distances) if np.mean(distances) > 0 else 0
            },
            'sla_statistics': {
                'mean': np.mean(sla_rates),
                'std': np.std(sla_rates),
                'min': np.min(sla_rates),
                'max': np.max(sla_rates)
            },
            'selected_route_performance': {
                'cost': result.selected_route.total_cost,
                'time': result.selected_route.total_time,
                'distance': result.selected_route.total_distance,
                'sla_rate': result.selected_route.sla_compliance_rate
            },
            'robustness_metrics': {
                'robustness_score': result.robustness_score,
                'confidence_level': result.confidence_level,
                'selection_strategy': result.selection_strategy
            }
        }
        
        return analysis

    # ==================== 公共接口方法 (Design Document Interface) ====================
    
    def optimize_min_max_strategy(self, scenario_solutions: List[RouteOptimizationResult]) -> RouteOptimizationResult:
        """Min-Max鲁棒优化策略：选择最坏情况下表现最好的解"""
        logger.info("执行Min-Max鲁棒优化策略")
        
        if not scenario_solutions:
            raise ValueError("场景解列表不能为空")
        
        return self._select_min_max(scenario_solutions)
    
    def optimize_expected_value_strategy(self, scenario_solutions: List[RouteOptimizationResult], 
                                       probabilities: List[float]) -> RouteOptimizationResult:
        """期望值优化策略：选择期望成本最小的解"""
        logger.info("执行期望值优化策略")
        
        if not scenario_solutions:
            raise ValueError("场景解列表不能为空")
        
        if len(probabilities) != len(scenario_solutions):
            raise ValueError("概率列表长度必须与场景解列表长度相等")
        
        if abs(sum(probabilities) - 1.0) > 1e-6:
            logger.warning(f"概率和不等于1.0: {sum(probabilities):.6f}")
        
        # 计算加权期望成本
        expected_costs = []
        for i, result in enumerate(scenario_solutions):
            expected_cost = result.total_cost * probabilities[i]
            expected_costs.append(expected_cost)
        
        # 选择期望成本最小的解
        min_expected_index = np.argmin(expected_costs)
        return scenario_solutions[min_expected_index]
    
    def optimize_weighted_sum_strategy(self, scenario_solutions: List[RouteOptimizationResult], 
                                     weights: Dict[str, float]) -> RouteOptimizationResult:
        """加权和优化策略：平衡多个目标的优化"""
        logger.info("执行加权和优化策略")
        
        if not scenario_solutions:
            raise ValueError("场景解列表不能为空")
        
        # 使用默认权重如果未提供
        default_weights = {
            'cost': weights.get('cost', 0.4),
            'time': weights.get('time', 0.3),
            'distance': weights.get('distance', 0.2),
            'sla_compliance': weights.get('sla_compliance', 0.1)
        }
        
        # 验证权重和
        weight_sum = sum(default_weights.values())
        if abs(weight_sum - 1.0) > 1e-6:
            logger.warning(f"权重和不等于1.0: {weight_sum:.6f}，进行归一化")
            for key in default_weights:
                default_weights[key] /= weight_sum
        
        # 提取各项指标
        costs = [r.total_cost for r in scenario_solutions]
        times = [r.total_time for r in scenario_solutions]
        distances = [r.total_distance for r in scenario_solutions]
        sla_rates = [r.sla_compliance_rate for r in scenario_solutions]
        
        # 标准化指标（最小-最大标准化）
        def normalize(values):
            min_val, max_val = min(values), max(values)
            if max_val == min_val:
                return [0.0] * len(values)
            return [(val - min_val) / (max_val - min_val) for val in values]
        
        norm_costs = normalize(costs)
        norm_times = normalize(times)
        norm_distances = normalize(distances)
        norm_sla_rates = [1.0 - rate for rate in normalize(sla_rates)]  # 反转SLA（越高越好）
        
        # 计算加权分数
        scores = []
        for i in range(len(scenario_solutions)):
            score = (default_weights['cost'] * norm_costs[i] +
                    default_weights['time'] * norm_times[i] +
                    default_weights['distance'] * norm_distances[i] +
                    default_weights['sla_compliance'] * norm_sla_rates[i])
            scores.append(score)
        
        # 选择分数最低的解（成本类指标，越低越好）
        best_index = np.argmin(scores)
        return scenario_solutions[best_index]
    
    def evaluate_solution_robustness(self, solution: RouteOptimizationResult, 
                                   scenarios: List[DeliveryScenario]) -> float:
        """评估解在多个场景下的鲁棒性"""
        logger.debug("评估解的鲁棒性")
        
        if not scenarios:
            return 1.0
        
        # 模拟解在不同场景下的表现
        performance_scores = []
        
        for scenario in scenarios:
            try:
                # 简化评估：基于场景的需求变化和外部因素影响
                demand_impact = np.mean(list(scenario.demand_forecast.values()))
                weather_impact = abs(scenario.weather_impact)
                traffic_impact = abs(scenario.traffic_impact)
                
                # 计算性能衰减
                base_performance = 1.0
                demand_penalty = min(0.3, demand_impact * 0.01)  # 需求影响
                weather_penalty = min(0.2, weather_impact * 0.5)  # 天气影响
                traffic_penalty = min(0.2, traffic_impact * 0.4)  # 交通影响
                
                scenario_performance = base_performance - demand_penalty - weather_penalty - traffic_penalty
                performance_scores.append(max(0.0, scenario_performance))
                
            except Exception as e:
                logger.warning(f"场景 {scenario.scenario_id} 鲁棒性评估失败: {str(e)}")
                performance_scores.append(0.5)  # 默认中等性能
        
        # 计算鲁棒性分数（最小性能和平均性能的加权平均）
        if performance_scores:
            min_performance = min(performance_scores)
            avg_performance = np.mean(performance_scores)
            robustness = 0.6 * min_performance + 0.4 * avg_performance
        else:
            robustness = 0.0
        
        return max(0.0, min(1.0, robustness))
    
    def calculate_regret_matrix(self, solutions: List[RouteOptimizationResult], 
                              scenarios: List[DeliveryScenario]) -> np.ndarray:
        """计算后悔矩阵用于决策分析"""
        logger.info("计算后悔矩阵")
        
        if not solutions or not scenarios:
            return np.array([])
        
        num_solutions = len(solutions)
        num_scenarios = len(scenarios)
        
        # 初始化后悔矩阵
        regret_matrix = np.zeros((num_solutions, num_scenarios))
        
        # 为每个场景计算所有解的成本
        scenario_costs = np.zeros((num_solutions, num_scenarios))
        
        for j, scenario in enumerate(scenarios):
            for i, solution in enumerate(solutions):
                # 计算解在特定场景下的调整成本
                base_cost = solution.total_cost
                
                # 根据场景特征调整成本
                demand_multiplier = np.mean(list(scenario.demand_forecast.values())) / 10.0
                weather_multiplier = 1.0 + abs(scenario.weather_impact)
                traffic_multiplier = 1.0 + abs(scenario.traffic_impact)
                
                adjusted_cost = base_cost * demand_multiplier * weather_multiplier * traffic_multiplier
                scenario_costs[i, j] = adjusted_cost
        
        # 计算后悔值
        for j in range(num_scenarios):
            # 找到该场景下的最优成本
            best_cost = np.min(scenario_costs[:, j])
            
            # 计算每个解的后悔值
            for i in range(num_solutions):
                regret_matrix[i, j] = scenario_costs[i, j] - best_cost
        
        logger.info(f"后悔矩阵计算完成: {num_solutions}x{num_scenarios}")
        return regret_matrix

# ==================== 工厂函数 ====================

def create_robust_optimizer(base_optimizer: CVRPTWOptimizer = None, 
                          config: Dict[str, Any] = None) -> DeliveryRobustOptimizer:
    """创建鲁棒优化器实例"""
    return DeliveryRobustOptimizer(base_optimizer, config)

# ==================== 测试和演示 ====================

if __name__ == "__main__":
    print("🛡️ 测试鲁棒优化器...")
    
    try:
        # 创建鲁棒优化器
        robust_optimizer = DeliveryRobustOptimizer()
        print("✅ 鲁棒优化器创建成功")
        
        # 创建示例场景（简化）
        from core.data_schema import DeliveryScenario, OrderDetail, OrderItem
        from datetime import date
        
        scenarios = []
        for i in range(3):
            # 创建示例订单
            orders = []
            for j in range(2):
                order = OrderDetail(
                    order_id=f"scenario_{i}_order_{j}",
                    user_id=f"user_{j}",
                    fulfillment_store_code=f"store_{j}",
                    order_date=date.today(),
                    items=[OrderItem(sku_id="sku_1", sku_name="Product 1", quantity=3)],
                    total_quantity=3,
                    unique_sku_count=1
                )
                orders.append(order)
            
            scenario = DeliveryScenario(
                scenario_id=f"scenario_{i}",
                orders=orders,
                demand_forecast={f"store_{j}": 10.0 + i * 5 for j in range(2)},
                weather_impact=0.1 * i,
                traffic_impact=0.05 * i,
                probability=0.33,
                generated_timestamp=datetime.now()
            )
            scenarios.append(scenario)
        
        print(f"📊 创建示例场景: {len(scenarios)} 个场景")
        
        # 执行鲁棒优化
        print("🚀 开始鲁棒优化...")
        result = robust_optimizer.optimize_robust(scenarios, strategy="weighted_sum")
        
        print(f"✅ 鲁棒优化完成!")
        print(f"   选择策略: {result.selection_strategy}")
        print(f"   鲁棒性分数: {result.robustness_score:.3f}")
        print(f"   置信水平: {result.confidence_level:.3f}")
        print(f"   选定路径成本: ¥{result.selected_route.total_cost:.0f}")
        
        # 测试新的公共接口方法
        print("\n🔧 测试公共接口方法...")
        
        # 测试min-max策略
        min_max_solution = robust_optimizer.optimize_min_max_strategy(result.route_results)
        print(f"   Min-Max策略解成本: ¥{min_max_solution.total_cost:.0f}")
        
        # 测试期望值策略
        probabilities = [0.33, 0.33, 0.34]
        expected_value_solution = robust_optimizer.optimize_expected_value_strategy(
            result.route_results, probabilities
        )
        print(f"   期望值策略解成本: ¥{expected_value_solution.total_cost:.0f}")
        
        # 测试加权和策略
        weights = {'cost': 0.4, 'time': 0.3, 'distance': 0.2, 'sla_compliance': 0.1}
        weighted_sum_solution = robust_optimizer.optimize_weighted_sum_strategy(
            result.route_results, weights
        )
        print(f"   加权和策略解成本: ¥{weighted_sum_solution.total_cost:.0f}")
        
        # 测试鲁棒性评估
        robustness_score = robust_optimizer.evaluate_solution_robustness(
            result.selected_route, scenarios
        )
        print(f"   解鲁棒性分数: {robustness_score:.3f}")
        
        # 测试后悔矩阵计算
        regret_matrix = robust_optimizer.calculate_regret_matrix(result.route_results, scenarios)
        print(f"   后悔矩阵形状: {regret_matrix.shape}")
        if regret_matrix.size > 0:
            print(f"   最大后悔值: ¥{np.max(regret_matrix):.0f}")
            print(f"   平均后悔值: ¥{np.mean(regret_matrix):.0f}")
        
        # 获取鲁棒性分析
        analysis = robust_optimizer.get_robustness_analysis(result)
        print(f"\n📊 鲁棒性分析:")
        print(f"   成本变异系数: {analysis['cost_statistics']['cv']:.3f}")
        print(f"   时间变异系数: {analysis['time_statistics']['cv']:.3f}")
        print(f"   平均SLA合规率: {analysis['sla_statistics']['mean']:.3f}")
        
        print("\n🎉 鲁棒优化器测试完成！")
        
    except Exception as e:
        print(f"❌ 测试失败: {str(e)}")
        import traceback
        traceback.print_exc()