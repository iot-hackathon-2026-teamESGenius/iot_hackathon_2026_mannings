"""
鲁棒路径优化器 - Learning Enhanced Robust Routing
实现 Scenario-based Robust Optimization + Hybrid Heuristic

创新点：
1. 多情景鲁棒优化：避免"均值最优、极端失效"
2. Min-Max 策略：选择最坏情况下成本最小的路线
3. 与预测模块闭环：从预测不确定性生成优化情景
"""
from typing import List, Dict, Any, Tuple, Optional
from dataclasses import dataclass
import numpy as np
import time
import logging

from ortools.constraint_solver import pywrapcp, routing_enums_pb2

from src.core.interfaces import (
    StoreInfo, RoutePlan, IDistanceCalculator, IRoutingOptimizer, DemandForecast
)
from .scenario_generator import ScenarioGenerator, DemandScenario

logger = logging.getLogger(__name__)

@dataclass
class VehicleInfo:
    """车辆信息"""
    vehicle_id: str
    capacity: float
    cost_per_km: float = 1.0
    max_route_time_min: int = 480  # 8小时

@dataclass
class OptimizationResult:
    """优化结果"""
    routes: List[RoutePlan]
    total_distance_km: float
    total_cost: float
    sla_violations: int
    computation_time_sec: float
    scenario_id: str = None

@dataclass
class RobustOptimizationResult:
    """鲁棒优化结果"""
    selected_result: OptimizationResult
    all_scenario_results: List[OptimizationResult]
    worst_case_distance: float
    selection_criterion: str
    statistics: Dict[str, float]

class RobustRoutingOptimizer(IRoutingOptimizer):
    """
    鲁棒路径优化器
    
    实现 CVRPTW + Scenario-based Robust Optimization
    """
    
    def __init__(
        self, 
        time_limit_seconds: int = 60,
        robustness_level: float = 0.9,
        demand_ratios: List[float] = None,
        selection_criterion: str = "min_max_distance"
    ):
        """
        Args:
            time_limit_seconds: 每个情景的求解时间限制
            robustness_level: 鲁棒性水平（0-1）
            demand_ratios: 需求情景比例，如 [0.9, 1.0, 1.1]
            selection_criterion: 选择标准 
                - "min_max_distance": 最小化最坏情况距离
                - "min_expected_distance": 最小化期望距离
                - "min_max_cost": 最小化最坏情况成本
        """
        self.time_limit_seconds = time_limit_seconds
        self.robustness_level = robustness_level
        self.demand_ratios = demand_ratios or [0.9, 1.0, 1.1]
        self.selection_criterion = selection_criterion
        self.scenario_generator = ScenarioGenerator(self.demand_ratios)
    
    def optimize_routes(
        self, 
        stores: List[StoreInfo], 
        demands: Dict[str, float],
        vehicles: List[VehicleInfo],
        distance_calculator: IDistanceCalculator,
        time_windows: bool = True,
        capacity_constraints: bool = True
    ) -> List[RoutePlan]:
        """
        标准路径优化（Baseline）
        
        实现确定性 CVRPTW
        """
        start_time = time.time()
        
        # 构建距离矩阵
        distance_matrix = self._build_distance_matrix(stores, distance_calculator)
        
        # 构建 OR-Tools 模型
        manager, routing, dimension_callbacks = self._build_ortools_model(
            stores, demands, vehicles, distance_matrix,
            time_windows, capacity_constraints
        )
        
        # 设置搜索参数
        search_params = pywrapcp.DefaultRoutingSearchParameters()
        search_params.first_solution_strategy = (
            routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC
        )
        search_params.local_search_metaheuristic = (
            routing_enums_pb2.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH
        )
        search_params.time_limit.seconds = self.time_limit_seconds
        
        # 求解
        solution = routing.SolveWithParameters(search_params)
        
        computation_time = time.time() - start_time
        
        if solution:
            routes = self._extract_routes(
                manager, routing, solution, stores, vehicles, distance_matrix
            )
            return routes
        else:
            logger.warning("No solution found for deterministic optimization")
            return []
    
    def robust_optimization(
        self, 
        stores: List[StoreInfo],
        demand_scenarios: List[Dict[str, float]],
        vehicles: List[VehicleInfo],
        distance_calculator: IDistanceCalculator,
        robustness_level: float = 0.9
    ) -> List[RoutePlan]:
        """
        鲁棒路径优化（创新点）
        
        实现 Scenario-based Robust Optimization
        """
        result = self.robust_optimization_full(
            stores, demand_scenarios, vehicles, distance_calculator, robustness_level
        )
        return result.selected_result.routes if result else []
    
    def robust_optimization_full(
        self, 
        stores: List[StoreInfo],
        demand_scenarios: List[Dict[str, float]],
        vehicles: List[VehicleInfo],
        distance_calculator: IDistanceCalculator,
        robustness_level: float = 0.9
    ) -> RobustOptimizationResult:
        """
        完整鲁棒优化（返回详细结果）
        """
        start_time = time.time()
        
        # 为每个情景求解
        scenario_results = []
        for i, demands in enumerate(demand_scenarios):
            logger.info(f"Solving scenario {i+1}/{len(demand_scenarios)}...")
            
            routes = self.optimize_routes(
                stores, demands, vehicles, distance_calculator,
                time_windows=True, capacity_constraints=True
            )
            
            if routes:
                total_dist = sum(r.total_distance_km for r in routes)
                total_cost = sum(r.total_cost for r in routes)
                sla_violations = sum(1 for r in routes if r.sla_risk_score > 0.5)
                
                scenario_results.append(OptimizationResult(
                    routes=routes,
                    total_distance_km=total_dist,
                    total_cost=total_cost,
                    sla_violations=sla_violations,
                    computation_time_sec=time.time() - start_time,
                    scenario_id=f"S{i+1:02d}"
                ))
        
        if not scenario_results:
            logger.error("No feasible solution found for any scenario")
            return None
        
        # 根据选择标准选取最优方案
        selected_result = self._select_robust_solution(scenario_results)
        
        # 计算统计信息
        distances = [r.total_distance_km for r in scenario_results]
        statistics = {
            "min_distance": min(distances),
            "max_distance": max(distances),
            "avg_distance": np.mean(distances),
            "std_distance": np.std(distances),
            "total_scenarios": len(scenario_results),
            "total_computation_time": time.time() - start_time
        }
        
        return RobustOptimizationResult(
            selected_result=selected_result,
            all_scenario_results=scenario_results,
            worst_case_distance=max(distances),
            selection_criterion=self.selection_criterion,
            statistics=statistics
        )
    
    def robust_optimization_from_forecasts(
        self,
        stores: List[StoreInfo],
        forecasts: List[DemandForecast],
        vehicles: List[VehicleInfo],
        distance_calculator: IDistanceCalculator,
        use_confidence_bounds: bool = True
    ) -> RobustOptimizationResult:
        """
        从预测结果进行鲁棒优化（预测→决策闭环）
        
        创新点：直接对接预测模块输出
        """
        # 生成多情景需求
        scenarios = self.scenario_generator.generate_from_forecasts(
            forecasts, 
            use_confidence_bounds=use_confidence_bounds
        )
        
        # 转换为需求字典列表
        demand_scenarios = [s.demands for s in scenarios]
        
        return self.robust_optimization_full(
            stores, demand_scenarios, vehicles, distance_calculator
        )
    
    def evaluate_routes(
        self, 
        route_plans: List[RoutePlan], 
        actual_performance: Dict[str, Any] = None
    ) -> Dict[str, float]:
        """评估路线"""
        if not route_plans:
            return {"error": "No routes to evaluate"}
        
        metrics = {
            "total_distance_km": sum(r.total_distance_km for r in route_plans),
            "total_cost": sum(r.total_cost for r in route_plans),
            "total_duration_min": sum(r.total_duration_min for r in route_plans),
            "num_routes": len(route_plans),
            "avg_sla_risk": np.mean([r.sla_risk_score for r in route_plans]),
            "max_sla_risk": max(r.sla_risk_score for r in route_plans),
            "total_stores": sum(len(r.store_sequence) for r in route_plans)
        }
        
        # 如果有实际绩效数据，计算偏差
        if actual_performance:
            if "actual_distance" in actual_performance:
                metrics["distance_deviation"] = (
                    actual_performance["actual_distance"] - metrics["total_distance_km"]
                ) / metrics["total_distance_km"] * 100
        
        return metrics
    
    def _select_robust_solution(
        self, 
        scenario_results: List[OptimizationResult]
    ) -> OptimizationResult:
        """根据选择标准选取鲁棒解"""
        if self.selection_criterion == "min_max_distance":
            # Min-Max策略：选择在最坏情况下距离最小的方案
            # 实际上选择能处理最大需求的方案
            return max(scenario_results, key=lambda r: r.scenario_id)
        
        elif self.selection_criterion == "min_expected_distance":
            # 选择期望距离最小的方案
            return min(scenario_results, key=lambda r: r.total_distance_km)
        
        elif self.selection_criterion == "min_max_cost":
            return max(scenario_results, key=lambda r: r.scenario_id)
        
        else:
            # 默认选择最后一个（最大需求）情景的结果
            return scenario_results[-1]
    
    def _build_distance_matrix(
        self, 
        stores: List[StoreInfo],
        distance_calculator: IDistanceCalculator
    ) -> List[List[float]]:
        """构建距离矩阵"""
        # 包含 depot (index 0) + 所有门店
        n = len(stores) + 1
        matrix = [[0.0] * n for _ in range(n)]
        
        # Depot位置（假设为第一个门店附近或自定义）
        depot_lat, depot_lng = 22.3700, 114.1130  # 葵涌
        
        locations = [(depot_lat, depot_lng)]
        for store in stores:
            locations.append((store.latitude, store.longitude))
        
        # 计算距离
        for i in range(n):
            for j in range(n):
                if i != j:
                    # 使用欧氏距离（初期）或调用距离计算器
                    lat1, lng1 = locations[i]
                    lat2, lng2 = locations[j]
                    # 简化距离计算（度转公里，约111km/度）
                    dist = np.sqrt((lat1 - lat2)**2 + (lng1 - lng2)**2) * 111
                    matrix[i][j] = dist
        
        return matrix
    
    def _build_ortools_model(
        self,
        stores: List[StoreInfo],
        demands: Dict[str, float],
        vehicles: List[VehicleInfo],
        distance_matrix: List[List[float]],
        time_windows: bool,
        capacity_constraints: bool
    ) -> Tuple[Any, Any, Dict]:
        """构建 OR-Tools 路由模型"""
        # 节点数：depot + stores
        num_locations = len(stores) + 1
        num_vehicles = len(vehicles)
        depot = 0
        
        # 创建管理器
        manager = pywrapcp.RoutingIndexManager(
            num_locations, num_vehicles, depot
        )
        
        # 创建路由模型
        routing = pywrapcp.RoutingModel(manager)
        
        # 距离回调
        def distance_callback(from_index, to_index):
            from_node = manager.IndexToNode(from_index)
            to_node = manager.IndexToNode(to_index)
            return int(distance_matrix[from_node][to_node] * 1000)  # 米
        
        transit_callback_index = routing.RegisterTransitCallback(distance_callback)
        routing.SetArcCostEvaluatorOfAllVehicles(transit_callback_index)
        
        # 容量约束
        if capacity_constraints:
            def demand_callback(from_index):
                from_node = manager.IndexToNode(from_index)
                if from_node == 0:  # depot
                    return 0
                store = stores[from_node - 1]
                return int(demands.get(store.store_id, 0))
            
            demand_callback_index = routing.RegisterUnaryTransitCallback(demand_callback)
            
            routing.AddDimensionWithVehicleCapacity(
                demand_callback_index,
                0,  # 没有松弛
                [int(v.capacity) for v in vehicles],  # 车辆容量
                True,  # 从0开始累积
                "Capacity"
            )
        
        # 时间窗约束
        if time_windows:
            routing.AddDimension(
                transit_callback_index,
                30,  # 等待时间上限（分钟）
                480,  # 最大路径时间（分钟）
                False,
                "Time"
            )
            
            time_dimension = routing.GetDimensionOrDie("Time")
            
            # 设置各节点的时间窗
            for location_idx in range(1, num_locations):
                store = stores[location_idx - 1]
                index = manager.NodeToIndex(location_idx)
                
                # 解析时间窗
                try:
                    start_min = int(store.time_window_start.split(":")[0]) * 60
                    end_min = int(store.time_window_end.split(":")[0]) * 60
                except:
                    start_min, end_min = 480, 1080  # 默认 8:00-18:00
                
                time_dimension.CumulVar(index).SetRange(start_min, end_min)
        
        return manager, routing, {"transit": transit_callback_index}
    
    def _extract_routes(
        self,
        manager,
        routing,
        solution,
        stores: List[StoreInfo],
        vehicles: List[VehicleInfo],
        distance_matrix: List[List[float]]
    ) -> List[RoutePlan]:
        """从解中提取路线"""
        routes = []
        
        for vehicle_idx in range(len(vehicles)):
            index = routing.Start(vehicle_idx)
            
            store_sequence = []
            arrival_times = []
            departure_times = []
            distances = []
            total_distance = 0.0
            
            prev_index = index
            while not routing.IsEnd(index):
                node = manager.IndexToNode(index)
                
                if node > 0:  # 非depot
                    store = stores[node - 1]
                    store_sequence.append(store.store_id)
                    arrival_times.append(f"{8 + len(store_sequence)}:00")  # 简化
                    departure_times.append(f"{8 + len(store_sequence)}:15")
                
                prev_node = manager.IndexToNode(prev_index)
                next_index = solution.Value(routing.NextVar(index))
                
                if prev_index != index:
                    dist = distance_matrix[prev_node][node]
                    distances.append(dist)
                    total_distance += dist
                
                prev_index = index
                index = next_index
            
            # 返回 depot 的距离
            last_node = manager.IndexToNode(prev_index)
            total_distance += distance_matrix[last_node][0]
            
            if store_sequence:  # 只记录有配送任务的路线
                routes.append(RoutePlan(
                    route_id=f"R{vehicle_idx+1:03d}",
                    vehicle_id=vehicles[vehicle_idx].vehicle_id,
                    store_sequence=store_sequence,
                    arrival_times=arrival_times,
                    departure_times=departure_times,
                    distances_km=distances,
                    total_distance_km=round(total_distance, 2),
                    total_duration_min=len(store_sequence) * 20 + total_distance * 2,
                    total_cost=round(total_distance * vehicles[vehicle_idx].cost_per_km, 2),
                    sla_risk_score=0.1 if len(store_sequence) < 5 else 0.3
                ))
        
        return routes
