"""
OR-Tools路径优化器 - Baseline 实现

该模块实现确定性 CVRPTW，作为鲁棒优化的对比基线

技术栈：Google OR-Tools + NumPy + Pandas
"""
from typing import List, Dict, Any
import numpy as np
import time
import logging

from ortools.constraint_solver import pywrapcp, routing_enums_pb2

from src.core.interfaces import StoreInfo, RoutePlan, IDistanceCalculator, IRoutingOptimizer

logger = logging.getLogger(__name__)

class ORToolsRoutingOptimizer(IRoutingOptimizer):
    """
    基于OR-Tools的路径优化器
    
    实现确定性 CVRPTW (Capacitated Vehicle Routing Problem with Time Windows)
    作为 Baseline 与鲁棒优化进行对比
    """
    
    def __init__(self, time_limit_seconds: int = 60, robustness_level: float = 0.9):
        """
        Args:
            time_limit_seconds: 求解时间限制（秒）
            robustness_level: 鲁棒性水平（在 RobustOptimizer 中使用）
        """
        self.time_limit_seconds = time_limit_seconds
        self.robustness_level = robustness_level
        
        # Depot 位置（默认葵涌）
        self.depot_location = (22.3700, 114.1130)
    
    def optimize_routes(
        self, 
        stores: List[StoreInfo], 
        demands: Dict[str, float],
        vehicles: List[Any],
        distance_calculator: IDistanceCalculator,
        time_windows: bool = True,
        capacity_constraints: bool = True
    ) -> List[RoutePlan]:
        """
        优化路径 - Baseline 实现
        
        实现确定性 CVRPTW，基于单一需求预测值
        """
        start_time = time.time()
        
        if not stores or not vehicles:
            logger.warning("No stores or vehicles provided")
            return []
        
        # 构建距离矩阵
        distance_matrix = self._build_distance_matrix(stores)
        
        # 构建模型
        num_locations = len(stores) + 1  # +1 for depot
        num_vehicles = len(vehicles)
        depot = 0
        
        manager = pywrapcp.RoutingIndexManager(num_locations, num_vehicles, depot)
        routing = pywrapcp.RoutingModel(manager)
        
        # 距离回调
        def distance_callback(from_index, to_index):
            from_node = manager.IndexToNode(from_index)
            to_node = manager.IndexToNode(to_index)
            return int(distance_matrix[from_node][to_node] * 1000)  # 米
        
        transit_callback_index = routing.RegisterTransitCallback(distance_callback)
        routing.SetArcCostEvaluatorOfAllVehicles(transit_callback_index)
        
        # 容量约束
        if capacity_constraints and demands:
            def demand_callback(from_index):
                from_node = manager.IndexToNode(from_index)
                if from_node == 0:
                    return 0
                store = stores[from_node - 1]
                return int(demands.get(store.store_id, 0))
            
            demand_callback_index = routing.RegisterUnaryTransitCallback(demand_callback)
            
            vehicle_capacities = []
            for v in vehicles:
                if hasattr(v, 'capacity'):
                    vehicle_capacities.append(int(v.capacity))
                else:
                    vehicle_capacities.append(100)  # 默认容量
            
            routing.AddDimensionWithVehicleCapacity(
                demand_callback_index,
                0,
                vehicle_capacities,
                True,
                "Capacity"
            )
        
        # 时间窗约束
        if time_windows:
            routing.AddDimension(
                transit_callback_index,
                30,  # 等待时间
                480,  # 最大路径时间
                False,
                "Time"
            )
            
            time_dimension = routing.GetDimensionOrDie("Time")
            
            for location_idx in range(1, num_locations):
                store = stores[location_idx - 1]
                index = manager.NodeToIndex(location_idx)
                
                try:
                    start_min = int(store.time_window_start.split(":")[0]) * 60
                    end_min = int(store.time_window_end.split(":")[0]) * 60
                except:
                    start_min, end_min = 480, 1080
                
                time_dimension.CumulVar(index).SetRange(start_min, end_min)
        
        # 搜索参数
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
        logger.info(f"Optimization completed in {computation_time:.2f}s")
        
        if solution:
            return self._extract_routes(
                manager, routing, solution, stores, vehicles, distance_matrix
            )
        else:
            logger.warning("No solution found")
            return []
    
    def evaluate_routes(
        self, 
        route_plans: List[RoutePlan], 
        actual_performance: Dict[str, Any] = None
    ) -> Dict[str, float]:
        """评估路线"""
        if not route_plans:
            return {"error": "No routes to evaluate"}
        
        return {
            'total_distance_km': sum(r.total_distance_km for r in route_plans),
            'total_cost': sum(r.total_cost for r in route_plans),
            'total_duration_min': sum(r.total_duration_min for r in route_plans),
            'num_routes': len(route_plans),
            'sla_risk_average': np.mean([r.sla_risk_score for r in route_plans]),
            'total_stores': sum(len(r.store_sequence) for r in route_plans)
        }
    
    def robust_optimization(
        self, 
        stores: List[StoreInfo], 
        demand_scenarios: List[Dict[str, float]],
        vehicles: List[Any],
        distance_calculator: IDistanceCalculator,
        robustness_level: float = 0.9
    ) -> List[RoutePlan]:
        """
        鲁棒优化 - 委托给 RobustRoutingOptimizer
        
        建议使用 RobustRoutingOptimizer 获取完整功能
        """
        from .robust_optimizer import RobustRoutingOptimizer
        
        robust_opt = RobustRoutingOptimizer(
            time_limit_seconds=self.time_limit_seconds,
            robustness_level=robustness_level
        )
        
        return robust_opt.robust_optimization(
            stores, demand_scenarios, vehicles, distance_calculator, robustness_level
        )
    
    def _build_distance_matrix(self, stores: List[StoreInfo]) -> List[List[float]]:
        """构建距离矩阵"""
        n = len(stores) + 1
        matrix = [[0.0] * n for _ in range(n)]
        
        locations = [self.depot_location]
        for store in stores:
            locations.append((store.latitude, store.longitude))
        
        for i in range(n):
            for j in range(n):
                if i != j:
                    lat1, lng1 = locations[i]
                    lat2, lng2 = locations[j]
                    # 欧氏距离（简化）
                    dist = np.sqrt((lat1 - lat2)**2 + (lng1 - lng2)**2) * 111
                    matrix[i][j] = dist
        
        return matrix
    
    def _extract_routes(
        self, manager, routing, solution, 
        stores: List[StoreInfo], vehicles: List[Any],
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
            total_demand = 0
            
            prev_index = index
            while not routing.IsEnd(index):
                node = manager.IndexToNode(index)
                
                if node > 0:
                    store = stores[node - 1]
                    store_sequence.append(store.store_id)
                    arrival_times.append(f"{8 + len(store_sequence)}:00")
                    departure_times.append(f"{8 + len(store_sequence)}:15")
                
                prev_node = manager.IndexToNode(prev_index)
                next_index = solution.Value(routing.NextVar(index))
                
                if prev_index != index:
                    dist = distance_matrix[prev_node][node]
                    distances.append(round(dist, 3))
                    total_distance += dist
                
                prev_index = index
                index = next_index
            
            # 返回 depot
            last_node = manager.IndexToNode(prev_index)
            total_distance += distance_matrix[last_node][0]
            
            if store_sequence:
                vehicle_id = vehicles[vehicle_idx].vehicle_id if hasattr(vehicles[vehicle_idx], 'vehicle_id') else f"V{vehicle_idx+1:03d}"
                cost_per_km = vehicles[vehicle_idx].cost_per_km if hasattr(vehicles[vehicle_idx], 'cost_per_km') else 1.0
                
                routes.append(RoutePlan(
                    route_id=f"R{vehicle_idx+1:03d}",
                    vehicle_id=vehicle_id,
                    store_sequence=store_sequence,
                    arrival_times=arrival_times,
                    departure_times=departure_times,
                    distances_km=distances,
                    total_distance_km=round(total_distance, 2),
                    total_duration_min=round(len(store_sequence) * 20 + total_distance * 2, 1),
                    total_cost=round(total_distance * cost_per_km, 2),
                    sla_risk_score=0.1 if len(store_sequence) < 5 else 0.3
                ))
        
        return routes
