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
from dataclasses import dataclass, field
import logging
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed, ProcessPoolExecutor
import copy
import time
import threading
import hashlib
import pickle
from functools import lru_cache
import psutil
import gc
from collections import defaultdict

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
    try:
        from core.interfaces import RobustOptimizer, CVRPTWOptimizer
        from core.data_schema import (
            DeliveryScenario, RouteOptimizationResult, RobustOptimizationResult
        )
        from modules.routing.ortools_optimizer import ORToolsOptimizer
    except ImportError as e:
        # 如果OR-Tools不可用，创建一个简单的mock优化器
        logger.warning(f"OR-Tools optimizer not available: {e}")
        
        class MockOptimizer:
            def optimize(self, orders, vehicles, constraints):
                # 返回一个简单的mock结果
                from core.data_schema import RouteOptimizationResult
                return RouteOptimizationResult(
                    scenario_id="mock",
                    vehicle_routes={"vehicle_0": [order.fulfillment_store_code for order in orders[:5]]},
                    total_distance=100.0,
                    total_time=120.0,
                    total_cost=200.0,
                    sla_compliance_rate=0.95,
                    optimization_timestamp=datetime.now(),
                    solver_status="MOCK_OPTIMAL"
                )
        
        ORToolsOptimizer = MockOptimizer
        
        # 创建基础接口类
        class RobustOptimizer:
            pass
        
        class CVRPTWOptimizer:
            pass

logger = logging.getLogger(__name__)


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


class OptimizationCache:
    """优化结果缓存管理器"""
    
    def __init__(self, max_size: int = 50):
        self.cache = {}
        self.access_times = {}
        self.max_size = max_size
        self.lock = threading.Lock()
    
    def _generate_scenario_key(self, scenario: DeliveryScenario) -> str:
        """生成场景的哈希键"""
        scenario_data = {
            'orders': [(o.order_id, o.total_quantity) for o in scenario.orders],
            'demand_forecast': scenario.demand_forecast,
            'weather_impact': scenario.weather_impact,
            'traffic_impact': scenario.traffic_impact
        }
        scenario_str = str(sorted(scenario_data.items()))
        return hashlib.md5(scenario_str.encode()).hexdigest()
    
    def get(self, scenario: DeliveryScenario) -> Optional[RouteOptimizationResult]:
        """获取缓存的优化结果"""
        key = self._generate_scenario_key(scenario)
        with self.lock:
            if key in self.cache:
                self.access_times[key] = time.time()
                return copy.deepcopy(self.cache[key])
            return None
    
    def put(self, scenario: DeliveryScenario, result: RouteOptimizationResult) -> None:
        """存储优化结果到缓存"""
        key = self._generate_scenario_key(scenario)
        with self.lock:
            if len(self.cache) >= self.max_size:
                # LRU淘汰策略
                oldest_key = min(self.access_times.keys(), key=lambda k: self.access_times[k])
                del self.cache[oldest_key]
                del self.access_times[oldest_key]
            
            self.cache[key] = copy.deepcopy(result)
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
                'hit_rate': 0.0  # 需要在使用时计算
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
        
        # 计算并行效率（简化版本）
        if self.current_metrics.scenarios_processed > 0:
            ideal_time = self.current_metrics.optimization_time / self.current_metrics.scenarios_processed
            self.current_metrics.parallel_efficiency = min(1.0, ideal_time / self.current_metrics.optimization_time)
        
        # 保存到历史记录
        with self.lock:
            self.metrics_history.append(copy.deepcopy(self.current_metrics))
            # 只保留最近100次记录
            if len(self.metrics_history) > 100:
                self.metrics_history = self.metrics_history[-100:]
        
        return self.current_metrics
    
    def get_average_metrics(self, last_n: int = 10) -> Dict[str, float]:
        """获取最近N次的平均指标"""
        with self.lock:
            if not self.metrics_history:
                return {}
            
            recent_metrics = self.metrics_history[-last_n:]
            return {
                'avg_optimization_time': np.mean([m.optimization_time for m in recent_metrics]),
                'avg_memory_usage_mb': np.mean([m.memory_usage_mb for m in recent_metrics]),
                'avg_cpu_usage_percent': np.mean([m.cpu_usage_percent for m in recent_metrics]),
                'avg_throughput': np.mean([m.throughput_scenarios_per_second for m in recent_metrics]),
                'avg_parallel_efficiency': np.mean([m.parallel_efficiency for m in recent_metrics]),
                'cache_hit_rate': (
                    sum(m.cache_hits for m in recent_metrics) / 
                    max(1, sum(m.cache_hits + m.cache_misses for m in recent_metrics))
                )
            }


class DeliveryRobustOptimizer(RobustOptimizer):
    """配送鲁棒优化器"""
    
    def __init__(self, base_optimizer: CVRPTWOptimizer = None, config: Dict[str, Any] = None):
        self.config = config or self._get_default_config()
        self.base_optimizer = base_optimizer or ORToolsOptimizer()
        self.optimization_history = []
        
        # 初始化缓存和监控组件
        self.distance_cache = DistanceMatrixCache(max_size=self.config.get('distance_cache_size', 100))
        self.optimization_cache = OptimizationCache(max_size=self.config.get('optimization_cache_size', 50))
        self.performance_monitor = PerformanceMonitor()
        
        # 统计信息
        self.optimization_stats = defaultdict(int)
        self.cache_stats = {'hits': 0, 'misses': 0}
        
        logger.info("鲁棒优化器初始化完成，启用缓存和性能监控")
        
    def _get_default_config(self) -> Dict[str, Any]:
        """获取默认配置"""
        return {
            'selection_strategies': ['min_max', 'expected_value', 'weighted_sum', 'robust_deviation'],
            'risk_tolerance': 0.1,  # 风险容忍度
            'robustness_weight': 0.3,  # 鲁棒性权重
            'performance_weight': 0.7,  # 性能权重
            'confidence_level': 0.95,  # 置信水平
            'max_parallel_optimizations': min(8, psutil.cpu_count()),  # 最大并行优化数，基于CPU核心数
            'scenario_weight_threshold': 0.01,  # 场景权重阈值
            'convergence_tolerance': 0.001,  # 收敛容忍度
            'max_iterations': 10,  # 最大迭代次数
            
            # 新增性能和缓存配置
            'distance_cache_size': 100,  # 距离矩阵缓存大小
            'optimization_cache_size': 50,  # 优化结果缓存大小
            'enable_process_pool': False,  # 是否启用进程池（CPU密集型任务）
            'chunk_size': 5,  # 批处理大小
            'timeout_per_scenario': 120,  # 单个场景优化超时时间（秒）
            'memory_limit_mb': 2048,  # 内存使用限制（MB）
            'enable_gc_optimization': True,  # 是否启用垃圾回收优化
            'performance_monitoring': True,  # 是否启用性能监控
            'adaptive_parallelism': True,  # 是否启用自适应并行度
        }
    
    def optimize_robust(self, scenarios: List[DeliveryScenario], 
                       strategy: str = "min_max") -> RobustOptimizationResult:
        """执行鲁棒优化"""
        # 开始性能监控
        if self.config.get('performance_monitoring', True):
            self.performance_monitor.start_monitoring()
        
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
            
            # 自适应调整并行度
            if self.config.get('adaptive_parallelism', True):
                self._adjust_parallelism(len(filtered_scenarios))
            
            # 并行优化所有场景（使用增强版本）
            start_time = time.time()
            route_results = self._optimize_all_scenarios_enhanced(filtered_scenarios)
            optimization_time = time.time() - start_time
            
            if not route_results:
                raise ValueError("所有场景优化都失败")
            
            logger.info(f"场景优化完成，成功 {len(route_results)}/{len(filtered_scenarios)} 个场景，耗时 {optimization_time:.2f}秒")
            
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
                'total_cost': selected_route.total_cost,
                'optimization_time': optimization_time
            })
            
            # 更新统计信息
            self.optimization_stats['total_optimizations'] += 1
            self.optimization_stats['total_scenarios_processed'] += len(filtered_scenarios)
            self.optimization_stats['total_optimization_time'] += optimization_time
            
            logger.info(f"✅ 鲁棒优化完成，鲁棒性分数: {robustness_score:.3f}")
            return result
            
        except Exception as e:
            logger.error(f"鲁棒优化失败: {str(e)}")
            raise
        finally:
            # 结束性能监控
            if self.config.get('performance_monitoring', True):
                metrics = self.performance_monitor.finish_monitoring()
                logger.info(f"性能指标 - 优化时间: {metrics.optimization_time:.2f}s, "
                          f"内存使用: {metrics.memory_usage_mb:.1f}MB, "
                          f"吞吐量: {metrics.throughput_scenarios_per_second:.2f} scenarios/s")
            
            # 垃圾回收优化
            if self.config.get('enable_gc_optimization', True):
                gc.collect()
    
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
            # 检查缓存
            cached_result = self.optimization_cache.get(scenario)
            if cached_result:
                self.cache_stats['hits'] += 1
                self.performance_monitor.record_cache_hit()
                logger.debug(f"场景 {scenario.scenario_id} 使用缓存结果")
                return cached_result
            
            self.cache_stats['misses'] += 1
            self.performance_monitor.record_cache_miss()
            
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
            
            # 缓存结果
            self.optimization_cache.put(scenario, result)
            self.performance_monitor.record_scenario_processed()
            
            return result
            
        except Exception as e:
            logger.error(f"单场景优化失败 {scenario.scenario_id}: {str(e)}")
            return None
    
    def _optimize_all_scenarios_enhanced(self, scenarios: List[DeliveryScenario]) -> List[RouteOptimizationResult]:
        """增强版并行优化所有场景"""
        logger.info("开始增强版并行优化所有场景...")
        
        results = []
        max_workers = min(self.config['max_parallel_optimizations'], len(scenarios))
        timeout_per_scenario = self.config.get('timeout_per_scenario', 120)
        chunk_size = self.config.get('chunk_size', 5)
        
        # 检查内存使用情况
        process = psutil.Process()
        initial_memory = process.memory_info().rss / (1024 * 1024)  # MB
        memory_limit = self.config.get('memory_limit_mb', 2048)
        
        logger.info(f"初始内存使用: {initial_memory:.1f}MB, 限制: {memory_limit}MB")
        
        # 选择执行器类型
        use_process_pool = (
            self.config.get('enable_process_pool', False) and 
            len(scenarios) > 10 and 
            max_workers > 2
        )
        
        executor_class = ProcessPoolExecutor if use_process_pool else ThreadPoolExecutor
        logger.info(f"使用 {'进程池' if use_process_pool else '线程池'} 执行器，工作线程数: {max_workers}")
        
        # 分批处理场景
        scenario_chunks = [scenarios[i:i + chunk_size] for i in range(0, len(scenarios), chunk_size)]
        
        with executor_class(max_workers=max_workers) as executor:
            for chunk_idx, chunk in enumerate(scenario_chunks):
                logger.debug(f"处理批次 {chunk_idx + 1}/{len(scenario_chunks)}, 场景数: {len(chunk)}")
                
                # 提交优化任务
                future_to_scenario = {}
                for scenario in chunk:
                    future = executor.submit(self._optimize_single_scenario_with_monitoring, scenario)
                    future_to_scenario[future] = scenario
                
                # 收集结果
                for future in as_completed(future_to_scenario, timeout=timeout_per_scenario * len(chunk)):
                    scenario = future_to_scenario[future]
                    try:
                        result = future.result(timeout=timeout_per_scenario)
                        if result:
                            results.append(result)
                            logger.debug(f"场景 {scenario.scenario_id} 优化完成")
                        else:
                            logger.warning(f"场景 {scenario.scenario_id} 优化失败")
                    except Exception as e:
                        logger.error(f"场景 {scenario.scenario_id} 优化异常: {str(e)}")
                
                # 检查内存使用情况
                current_memory = process.memory_info().rss / (1024 * 1024)
                if current_memory > memory_limit:
                    logger.warning(f"内存使用超限 ({current_memory:.1f}MB > {memory_limit}MB)，触发垃圾回收")
                    gc.collect()
                    current_memory = process.memory_info().rss / (1024 * 1024)
                    logger.info(f"垃圾回收后内存使用: {current_memory:.1f}MB")
        
        final_memory = process.memory_info().rss / (1024 * 1024)
        logger.info(f"并行优化完成，成功 {len(results)}/{len(scenarios)} 个场景")
        logger.info(f"内存使用变化: {initial_memory:.1f}MB -> {final_memory:.1f}MB")
        
        return results
    
    def _optimize_single_scenario_with_monitoring(self, scenario: DeliveryScenario) -> Optional[RouteOptimizationResult]:
        """带监控的单场景优化"""
        start_time = time.time()
        try:
            result = self._optimize_single_scenario(scenario)
            if result:
                optimization_time = time.time() - start_time
                logger.debug(f"场景 {scenario.scenario_id} 优化耗时: {optimization_time:.2f}s")
            return result
        except Exception as e:
            optimization_time = time.time() - start_time
            logger.error(f"场景 {scenario.scenario_id} 优化失败 (耗时: {optimization_time:.2f}s): {str(e)}")
            return None
    
    def _adjust_parallelism(self, num_scenarios: int) -> None:
        """自适应调整并行度"""
        if not self.config.get('adaptive_parallelism', True):
            return
        
        # 基于场景数量和系统资源调整并行度
        cpu_count = psutil.cpu_count()
        memory_gb = psutil.virtual_memory().total / (1024 ** 3)
        
        # 计算推荐的并行度
        if num_scenarios <= 5:
            recommended_workers = min(2, cpu_count)
        elif num_scenarios <= 20:
            recommended_workers = min(4, cpu_count)
        else:
            recommended_workers = min(cpu_count, int(memory_gb * 2))
        
        # 更新配置
        old_workers = self.config['max_parallel_optimizations']
        self.config['max_parallel_optimizations'] = recommended_workers
        
        if old_workers != recommended_workers:
            logger.info(f"自适应调整并行度: {old_workers} -> {recommended_workers} "
                       f"(场景数: {num_scenarios}, CPU: {cpu_count}, 内存: {memory_gb:.1f}GB)")
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """获取性能统计信息"""
        cache_stats = {
            'distance_cache': self.distance_cache.get_stats(),
            'optimization_cache': self.optimization_cache.get_stats(),
            'cache_hit_rate': (
                self.cache_stats['hits'] / 
                max(1, self.cache_stats['hits'] + self.cache_stats['misses'])
            )
        }
        
        performance_stats = self.performance_monitor.get_average_metrics()
        
        return {
            'optimization_stats': dict(self.optimization_stats),
            'cache_stats': cache_stats,
            'performance_metrics': performance_stats,
            'system_info': {
                'cpu_count': psutil.cpu_count(),
                'memory_gb': psutil.virtual_memory().total / (1024 ** 3),
                'current_memory_usage_mb': psutil.Process().memory_info().rss / (1024 * 1024)
            }
        }
    
    def clear_caches(self) -> None:
        """清空所有缓存"""
        self.distance_cache.clear()
        self.optimization_cache.clear()
        self.cache_stats = {'hits': 0, 'misses': 0}
        logger.info("所有缓存已清空")
    
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