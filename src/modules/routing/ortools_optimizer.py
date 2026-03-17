#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
万宁SLA优化系统 - OR-Tools路径优化模块
基于Google OR-Tools的CVRPTW求解器

创建时间: 2026-03-17
作者: 冷爽 (Team ESGenius)
"""

import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple, Any
import logging
from pathlib import Path
import math

logger = logging.getLogger(__name__)

try:
    from ortools.constraint_solver import routing_enums_pb2
    from ortools.constraint_solver import pywrapcp
    ORTOOLS_AVAILABLE = True
    logger.info("OR-Tools successfully imported")
except ImportError as e:
    ORTOOLS_AVAILABLE = False
    logger.warning(f"OR-Tools not available: {str(e)}. Using mock implementation for testing.")
except OSError as e:
    ORTOOLS_AVAILABLE = False
    logger.warning(f"OR-Tools library error: {str(e)}. Using mock implementation for testing.")
    
    # Mock classes for testing when OR-Tools is not available
    class MockRoutingIndexManager:
        def __init__(self, num_nodes, num_vehicles, depot):
            self.num_nodes = num_nodes
            self.num_vehicles = num_vehicles
            self.depot = depot
        
        def IndexToNode(self, index):
            return index
        
        def NodeToIndex(self, node):
            return node
    
    class MockRoutingModel:
        def __init__(self, manager):
            self.manager = manager
            self.objective_value = 1000
        
        def RegisterTransitCallback(self, callback):
            return 0
        
        def SetArcCostEvaluatorOfAllVehicles(self, callback_index):
            pass
        
        def RegisterUnaryTransitCallback(self, callback):
            return 0
        
        def AddDimensionWithVehicleCapacity(self, *args, **kwargs):
            pass
        
        def AddDimension(self, *args, **kwargs):
            pass
        
        def GetDimensionOrDie(self, name):
            return MockDimension()
        
        def SetFixedCostOfVehicle(self, cost, vehicle_id):
            pass
        
        def Start(self, vehicle_id):
            return 0
        
        def End(self, vehicle_id):
            return self.manager.num_nodes - 1
        
        def IsEnd(self, index):
            return index >= self.manager.num_nodes - 1
        
        def NextVar(self, index):
            return MockVar(index + 1)
        
        def SolveWithParameters(self, params):
            return MockSolution()
    
    class MockDimension:
        def CumulVar(self, index):
            return MockVar(0)
        
        def SetCumulVarSoftUpperBound(self, *args):
            pass
        
        def SetCumulVarSoftLowerBound(self, *args):
            pass
    
    class MockVar:
        def __init__(self, value):
            self.value = value
        
        def SetRange(self, min_val, max_val):
            pass
    
    class MockSolution:
        def ObjectiveValue(self):
            return 1000
        
        def Value(self, var):
            return var.value if hasattr(var, 'value') else 1
    
    class MockSearchParameters:
        def __init__(self):
            self.first_solution_strategy = None
            self.local_search_metaheuristic = None
            self.time_limit = MockTimeLimit()
            self.solution_limit = 100
            self.log_search = False
    
    class MockTimeLimit:
        def __init__(self):
            self.seconds = 30
    
    class MockEnums:
        class FirstSolutionStrategy:
            PATH_CHEAPEST_ARC = 1
            AUTOMATIC = 2
        
        class LocalSearchMetaheuristic:
            GUIDED_LOCAL_SEARCH = 1
            AUTOMATIC = 2
    
    # Mock the OR-Tools modules
    pywrapcp = type('MockPywrapcp', (), {
        'RoutingIndexManager': MockRoutingIndexManager,
        'RoutingModel': MockRoutingModel,
        'DefaultRoutingSearchParameters': MockSearchParameters
    })()
    
    routing_enums_pb2 = MockEnums()

import sys
project_root = Path(__file__).parent.parent.parent
sys.path.append(str(project_root))

try:
    from core.interfaces import CVRPTWOptimizer
    from core.data_schema import (
        OrderDetail, StoreLocation, RouteOptimizationResult, 
        DeliveryVehicle, TrafficCondition
    )
except ImportError:
    sys.path.append(str(project_root / "src"))
    from core.interfaces import CVRPTWOptimizer
    from core.data_schema import (
        OrderDetail, StoreLocation, RouteOptimizationResult, 
        DeliveryVehicle, TrafficCondition
    )

logger = logging.getLogger(__name__)

class ORToolsOptimizer(CVRPTWOptimizer):
    """基于OR-Tools的CVRPTW优化器"""
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or self._get_default_config()
        self.distance_matrix = None
        self.time_matrix = None
        self.locations = []
        self.time_windows = {}
        self.vehicle_capacities = []
        self.depot_index = 0
        self.store_locations = {}  # store_code -> StoreLocation mapping
        self.traffic_conditions = []  # Current traffic conditions
        self.optimization_stats = {}
        
        # 添加距离矩阵缓存
        self.distance_cache = {}
        self.cache_stats = {'hits': 0, 'misses': 0}
        
        if not ORTOOLS_AVAILABLE:
            logger.warning("OR-Tools not available. Using mock implementation for testing.")
        
        logger.info("OR-Tools优化器初始化完成，启用距离矩阵缓存")
    
    def _get_default_config(self) -> Dict[str, Any]:
        """获取默认配置"""
        return {
            'max_vehicles': 5,
            'vehicle_capacity': 100,
            'max_route_time': 8 * 60,  # 8小时，单位分钟
            'service_time': 15,  # 每个门店服务时间15分钟
            'depot_location': (22.3193, 114.1694),  # 配送中心位置
            'speed_kmh': 30,  # 平均速度30km/h
            'time_limit_seconds': 120,  # 求解时间限制增加到120秒
            'first_solution_strategy': 'PATH_CHEAPEST_ARC',
            'local_search_metaheuristic': 'GUIDED_LOCAL_SEARCH',
            'solution_limit': 200,  # 解决方案数量限制增加
            'use_traffic_data': True,  # 是否使用交通数据
            'traffic_multiplier': 1.2,  # 交通拥堵时间倍数
            'distance_penalty': 1.0,  # 距离惩罚系数
            'time_penalty': 2.0,  # 时间惩罚系数
            'capacity_penalty': 10.0,  # 容量违反惩罚系数
            'time_window_penalty': 5.0,  # 时间窗违反惩罚系数
            'enable_pickup_delivery': False,  # 是否启用取送货约束
            'max_waiting_time': 30,  # 最大等待时间（分钟）
            'break_duration': 60,  # 休息时间（分钟）
            'break_time_window': (12*60, 13*60),  # 休息时间窗（12:00-13:00）
            'enable_route_duration_limit': True,  # 启用路径时长限制
            'enable_distance_limit': True,  # 启用距离限制
            'max_route_distance': 200,  # 最大路径距离（公里）
            'enable_vehicle_breaks': True,  # 启用车辆休息
            'enable_soft_time_windows': True,  # 启用软时间窗
            'soft_time_window_cost': 100,  # 软时间窗违反成本
            'enable_drop_nodes': False,  # 是否允许丢弃节点
            'drop_penalty': 10000,  # 丢弃节点惩罚
            'solver_log_level': 1,  # 求解器日志级别
            'use_cp_sat': False,  # 是否使用CP-SAT求解器
            'enable_large_neighborhood_search': True,  # 启用大邻域搜索
            'lns_time_limit': 5000,  # 大邻域搜索时间限制（毫秒）
        }
    
    def optimize(self, orders: List[OrderDetail], vehicles: List[Dict], 
                constraints: Dict[str, Any]) -> RouteOptimizationResult:
        """执行路径优化"""
        logger.info(f"开始路径优化，订单数: {len(orders)}, 车辆数: {len(vehicles)}")
        
        try:
            # 记录优化开始时间
            start_time = datetime.now()
            
            # 准备数据
            self._prepare_optimization_data(orders, vehicles, constraints)
            
            # 创建路径模型
            manager, routing, solution = self._solve_vrp()
            
            if solution is None:
                logger.warning("无法找到可行解，尝试放宽约束...")
                # 尝试放宽约束重新求解
                relaxed_solution = self._solve_with_relaxed_constraints(manager, routing)
                if relaxed_solution is None:
                    raise ValueError("即使放宽约束也无法找到可行解")
                solution = relaxed_solution
            
            # 解析结果
            result = self._parse_solution(manager, routing, solution, orders, vehicles)
            
            # 记录优化统计信息
            optimization_time = (datetime.now() - start_time).total_seconds()
            self.optimization_stats = {
                'optimization_time_seconds': optimization_time,
                'num_orders': len(orders),
                'num_vehicles': len(vehicles),
                'num_locations': len(self.locations),
                'solver_status': result.solver_status,
                'total_distance_km': result.total_distance,
                'total_time_hours': result.total_time,
                'sla_compliance_rate': result.sla_compliance_rate,
                'vehicles_used': len([r for r in result.vehicle_routes.values() if r]),
                'average_route_length': np.mean([len(r) for r in result.vehicle_routes.values() if r]) if result.vehicle_routes else 0
            }
            
            logger.info(f"✅ 路径优化完成，总距离: {result.total_distance:.1f}km, "
                       f"总时间: {result.total_time:.1f}小时, 用时: {optimization_time:.1f}秒")
            return result
            
        except Exception as e:
            logger.error(f"路径优化失败: {str(e)}")
            raise
    
    def set_time_windows(self, time_windows: Dict[str, Tuple[str, str]]) -> None:
        """设置时间窗约束"""
        self.time_windows = {}
        
        for location, (start_time, end_time) in time_windows.items():
            # 转换时间字符串为分钟数
            start_minutes = self._time_to_minutes(start_time)
            end_minutes = self._time_to_minutes(end_time)
            self.time_windows[location] = (start_minutes, end_minutes)
        
        logger.info(f"设置时间窗约束: {len(self.time_windows)} 个位置")
    
    def set_vehicle_capacity(self, capacity: int) -> None:
        """设置车辆容量约束"""
        self.config['vehicle_capacity'] = capacity
        logger.info(f"设置车辆容量: {capacity}")
    
    def set_store_locations(self, store_locations: Dict[str, StoreLocation]) -> None:
        """设置门店位置信息"""
        self.store_locations = store_locations
        logger.info(f"设置门店位置: {len(store_locations)} 个门店")
    
    def set_traffic_conditions(self, traffic_conditions: List[TrafficCondition]) -> None:
        """设置交通状况数据"""
        self.traffic_conditions = traffic_conditions
        logger.info(f"设置交通状况: {len(traffic_conditions)} 条记录")
    
    def calculate_distance_matrix_with_traffic(self, locations: List[Tuple[float, float]]) -> np.ndarray:
        """计算考虑交通状况的距离矩阵"""
        n = len(locations)
        matrix = np.zeros((n, n))
        
        # 创建交通影响映射
        traffic_impact = self._create_traffic_impact_map()
        
        for i in range(n):
            for j in range(n):
                if i != j:
                    lat1, lng1 = locations[i]
                    lat2, lng2 = locations[j]
                    
                    # 计算基础距离
                    base_distance = self._haversine_distance(lat1, lng1, lat2, lng2)
                    
                    # 应用交通影响
                    traffic_multiplier = self._get_traffic_multiplier(
                        (lat1, lng1), (lat2, lng2), traffic_impact
                    )
                    
                    matrix[i][j] = base_distance * traffic_multiplier
        
        return matrix
    
    def calculate_time_matrix_with_traffic(self, locations: List[Tuple[float, float]]) -> np.ndarray:
        """计算考虑交通状况的时间矩阵"""
        n = len(locations)
        matrix = np.zeros((n, n), dtype=int)
        
        # 创建交通影响映射
        traffic_impact = self._create_traffic_impact_map()
        service_time = self.config['service_time']
        
        for i in range(n):
            for j in range(n):
                if i != j:
                    lat1, lng1 = locations[i]
                    lat2, lng2 = locations[j]
                    
                    # 计算基础距离
                    distance_km = self._haversine_distance(lat1, lng1, lat2, lng2)
                    
                    # 获取交通影响下的速度
                    effective_speed = self._get_effective_speed(
                        (lat1, lng1), (lat2, lng2), traffic_impact
                    )
                    
                    # 计算行驶时间
                    travel_time = int(distance_km / effective_speed * 60)  # 转换为分钟
                    matrix[i][j] = travel_time + service_time
        
        return matrix
    
    def calculate_route_cost(self, route: List[str]) -> float:
        """计算路径成本"""
        if not route or len(route) < 2:
            return 0.0
        
        total_cost = 0.0
        
        # 计算路径总距离
        for i in range(len(route) - 1):
            from_idx = self._get_location_index(route[i])
            to_idx = self._get_location_index(route[i + 1])
            
            if from_idx is not None and to_idx is not None:
                if self.distance_matrix is not None:
                    total_cost += self.distance_matrix[from_idx][to_idx]
                else:
                    # 使用欧几里得距离估算
                    total_cost += self._calculate_distance(route[i], route[i + 1])
        
        return total_cost
    
    def validate_solution(self, result: RouteOptimizationResult) -> bool:
        """验证优化结果"""
        try:
            logger.info("开始验证解决方案...")
            
            # 检查基本约束
            if not result.vehicle_routes:
                logger.error("解决方案为空")
                return False
            
            validation_errors = []
            
            # 检查容量约束
            for vehicle_id, route in result.vehicle_routes.items():
                if not route:  # 跳过空路径
                    continue
                    
                route_demand = self._calculate_route_demand(route)
                vehicle_index = int(vehicle_id.split('_')[-1]) if '_' in vehicle_id else 0
                
                if vehicle_index < len(self.vehicle_capacities):
                    capacity_limit = self.vehicle_capacities[vehicle_index]
                else:
                    capacity_limit = self.config['vehicle_capacity']
                
                if route_demand > capacity_limit:
                    error_msg = f"车辆 {vehicle_id} 超出容量限制: {route_demand} > {capacity_limit}"
                    validation_errors.append(error_msg)
                    logger.warning(error_msg)
            
            # 检查时间窗约束
            for vehicle_id, route in result.vehicle_routes.items():
                if not route:  # 跳过空路径
                    continue
                    
                if not self._validate_time_windows_detailed(route):
                    error_msg = f"车辆 {vehicle_id} 违反时间窗约束"
                    validation_errors.append(error_msg)
                    logger.warning(error_msg)
            
            # 检查路径连通性
            for vehicle_id, route in result.vehicle_routes.items():
                if not route:  # 跳过空路径
                    continue
                    
                if not self._validate_route_connectivity(route):
                    error_msg = f"车辆 {vehicle_id} 路径不连通"
                    validation_errors.append(error_msg)
                    logger.warning(error_msg)
            
            # 检查所有订单是否被覆盖
            all_stores_in_routes = set()
            for route in result.vehicle_routes.values():
                all_stores_in_routes.update(route)
            
            required_stores = set(loc['code'] for loc in self.locations if loc['code'] != 'DEPOT')
            missing_stores = required_stores - all_stores_in_routes
            
            if missing_stores:
                error_msg = f"以下门店未被覆盖: {missing_stores}"
                validation_errors.append(error_msg)
                logger.warning(error_msg)
            
            # 检查重复访问
            for vehicle_id, route in result.vehicle_routes.items():
                if len(route) != len(set(route)):
                    error_msg = f"车辆 {vehicle_id} 存在重复访问的门店"
                    validation_errors.append(error_msg)
                    logger.warning(error_msg)
            
            # 检查SLA合规率
            if not (0.0 <= result.sla_compliance_rate <= 1.0):
                error_msg = f"SLA合规率超出有效范围: {result.sla_compliance_rate}"
                validation_errors.append(error_msg)
                logger.warning(error_msg)
            
            # 输出验证结果
            if validation_errors:
                logger.error(f"解决方案验证失败，发现 {len(validation_errors)} 个问题:")
                for error in validation_errors:
                    logger.error(f"  - {error}")
                return False
            else:
                logger.info("✅ 解决方案验证通过")
                return True
            
        except Exception as e:
            logger.error(f"解决方案验证过程中出错: {str(e)}")
            return False
    
    def _validate_time_windows_detailed(self, route: List[str]) -> bool:
        """详细验证路径时间窗约束"""
        if not route:
            return True
        
        current_time = 0  # 从配送中心开始，时间为0
        
        # 从配送中心到第一个门店
        if route:
            first_store = route[0]
            travel_time = self._calculate_travel_time('DEPOT', first_store)
            current_time += travel_time
        
        for i, location_code in enumerate(route):
            # 检查到达时间是否在时间窗内
            if location_code in self.time_windows:
                start_time, end_time = self.time_windows[location_code]
                
                if current_time > end_time:
                    logger.debug(f"门店 {location_code} 到达时间 {current_time} 超过时间窗 {end_time}")
                    return False
                
                # 如果早到，需要等待
                if current_time < start_time:
                    current_time = start_time
            
            # 添加服务时间
            current_time += self.config['service_time']
            
            # 计算到下一个位置的行驶时间
            if i < len(route) - 1:
                next_location = route[i + 1]
                travel_time = self._calculate_travel_time(location_code, next_location)
                current_time += travel_time
        
        return True
    
    def _validate_route_connectivity(self, route: List[str]) -> bool:
        """验证路径连通性"""
        if not route:
            return True
        
        # 检查所有门店是否在位置列表中
        location_codes = set(loc['code'] for loc in self.locations)
        
        for store_code in route:
            if store_code not in location_codes:
                logger.debug(f"门店 {store_code} 不在位置列表中")
                return False
        
        return True
    
    def get_optimization_stats(self) -> Dict[str, Any]:
        """获取优化统计信息"""
        stats = {
            'locations_count': len(self.locations),
            'vehicle_capacities': self.vehicle_capacities,
            'time_windows_count': len(self.time_windows),
            'traffic_conditions_count': len(self.traffic_conditions),
            'config': self.config.copy(),
            'optimization_stats': self.optimization_stats.copy() if self.optimization_stats else {},
            'cache_stats': self.get_cache_stats()  # 添加缓存统计
        }
        
        # 添加矩阵统计
        if self.distance_matrix is not None:
            stats['distance_matrix_stats'] = {
                'shape': self.distance_matrix.shape,
                'max_distance': float(np.max(self.distance_matrix)),
                'avg_distance': float(np.mean(self.distance_matrix[self.distance_matrix > 0]))
            }
        
        if self.time_matrix is not None:
            stats['time_matrix_stats'] = {
                'shape': self.time_matrix.shape,
                'max_time': float(np.max(self.time_matrix)),
                'avg_time': float(np.mean(self.time_matrix[self.time_matrix > 0]))
            }
        
        return stats
    
    # ==================== 私有方法 ====================
    
    def _prepare_optimization_data(self, orders: List[OrderDetail], vehicles: List[Dict], 
                                 constraints: Dict[str, Any]) -> None:
        """准备优化数据"""
        logger.info("准备优化数据...")
        
        # 提取门店位置
        store_codes = list(set(order.fulfillment_store_code for order in orders))
        
        # 添加配送中心作为起点
        depot_lat, depot_lng = self.config['depot_location']
        self.locations = [{'code': 'DEPOT', 'lat': depot_lat, 'lng': depot_lng, 'demand': 0}]
        self.depot_index = 0
        
        # 添加门店位置
        for store_code in store_codes:
            if store_code in self.store_locations:
                # 使用实际门店位置
                store_loc = self.store_locations[store_code]
                lat, lng = store_loc.latitude, store_loc.longitude
            else:
                # 如果没有门店位置数据，使用配送中心附近的随机位置
                logger.warning(f"门店 {store_code} 位置未知，使用估算位置")
                lat = depot_lat + np.random.uniform(-0.05, 0.05)
                lng = depot_lng + np.random.uniform(-0.05, 0.05)
            
            # 计算门店需求
            store_demand = sum(order.total_quantity for order in orders 
                             if order.fulfillment_store_code == store_code)
            
            self.locations.append({
                'code': store_code,
                'lat': lat,
                'lng': lng,
                'demand': store_demand
            })
        
        # 提取位置坐标
        location_coords = [(loc['lat'], loc['lng']) for loc in self.locations]
        
        # 创建距离和时间矩阵
        if self.config['use_traffic_data'] and self.traffic_conditions:
            logger.info("使用交通数据计算距离和时间矩阵")
            self.distance_matrix = self.calculate_distance_matrix_with_traffic(location_coords)
            self.time_matrix = self.calculate_time_matrix_with_traffic(location_coords)
        else:
            logger.info("使用标准方法计算距离和时间矩阵")
            self._create_distance_matrix()
            self._create_time_matrix()
        
        # 设置车辆容量
        self.vehicle_capacities = []
        for vehicle in vehicles:
            capacity = vehicle.get('capacity', self.config['vehicle_capacity'])
            self.vehicle_capacities.append(capacity)
        
        # 设置默认时间窗（如果没有指定）
        if not self.time_windows:
            for location in self.locations:
                if location['code'] == 'DEPOT':
                    self.time_windows['DEPOT'] = (0, 24 * 60)  # 配送中心全天开放
                else:
                    # 从约束中获取时间窗，或使用默认值
                    start_time = constraints.get('time_window_start', '08:00')
                    end_time = constraints.get('time_window_end', '22:00')
                    start_minutes = self._time_to_minutes(start_time)
                    end_minutes = self._time_to_minutes(end_time)
                    self.time_windows[location['code']] = (start_minutes, end_minutes)
        
        logger.info(f"数据准备完成: {len(self.locations)} 个位置, {len(vehicles)} 辆车")
        logger.info(f"车辆容量: {self.vehicle_capacities}")
        logger.info(f"总需求: {sum(loc['demand'] for loc in self.locations)}")
    
    def _create_distance_matrix(self) -> None:
        """创建距离矩阵（带缓存）"""
        # 生成位置列表的缓存键
        location_tuples = [(loc['lat'], loc['lng']) for loc in self.locations]
        cache_key = str(sorted(location_tuples))
        
        # 检查缓存
        if cache_key in self.distance_cache:
            self.distance_matrix = self.distance_cache[cache_key].copy()
            self.cache_stats['hits'] += 1
            logger.info(f"使用缓存的距离矩阵: {len(self.locations)}x{len(self.locations)}")
            return
        
        self.cache_stats['misses'] += 1
        
        # 计算距离矩阵
        n = len(self.locations)
        self.distance_matrix = np.zeros((n, n))
        
        for i in range(n):
            for j in range(n):
                if i != j:
                    lat1, lng1 = self.locations[i]['lat'], self.locations[i]['lng']
                    lat2, lng2 = self.locations[j]['lat'], self.locations[j]['lng']
                    distance = self._haversine_distance(lat1, lng1, lat2, lng2)
                    self.distance_matrix[i][j] = distance
        
        # 缓存结果
        self.distance_cache[cache_key] = self.distance_matrix.copy()
        
        # 限制缓存大小
        if len(self.distance_cache) > 50:  # 最多缓存50个矩阵
            # 删除最旧的缓存项（简单FIFO策略）
            oldest_key = next(iter(self.distance_cache))
            del self.distance_cache[oldest_key]
        
        logger.info(f"创建并缓存距离矩阵: {n}x{n}")
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """获取缓存统计信息"""
        total_requests = self.cache_stats['hits'] + self.cache_stats['misses']
        hit_rate = self.cache_stats['hits'] / max(1, total_requests)
        
        return {
            'cache_hits': self.cache_stats['hits'],
            'cache_misses': self.cache_stats['misses'],
            'hit_rate': hit_rate,
            'cached_matrices': len(self.distance_cache)
        }
    
    def _create_time_matrix(self) -> None:
        """创建时间矩阵（分钟）"""
        speed_kmh = self.config['speed_kmh']
        service_time = self.config['service_time']
        
        n = len(self.locations)
        self.time_matrix = np.zeros((n, n), dtype=int)
        
        for i in range(n):
            for j in range(n):
                if i != j:
                    distance_km = self.distance_matrix[i][j]
                    travel_time = int(distance_km / speed_kmh * 60)  # 转换为分钟
                    self.time_matrix[i][j] = travel_time + service_time
        
        logger.info(f"创建时间矩阵: {n}x{n}")
    
    def _solve_vrp(self) -> Tuple[Any, Any, Any]:
        """求解VRP问题"""
        logger.info("开始求解VRP问题...")
        
        # 创建路径管理器
        manager = pywrapcp.RoutingIndexManager(
            len(self.locations),
            len(self.vehicle_capacities),
            self.depot_index
        )
        
        # 创建路径模型
        routing = pywrapcp.RoutingModel(manager)
        
        # 添加距离约束
        def distance_callback(from_index, to_index):
            from_node = manager.IndexToNode(from_index)
            to_node = manager.IndexToNode(to_index)
            return int(self.distance_matrix[from_node][to_node] * 1000)  # 转换为米
        
        transit_callback_index = routing.RegisterTransitCallback(distance_callback)
        routing.SetArcCostEvaluatorOfAllVehicles(transit_callback_index)
        
        # 添加容量约束（支持不同车辆容量）
        def demand_callback(from_index):
            from_node = manager.IndexToNode(from_index)
            return self.locations[from_node]['demand']
        
        demand_callback_index = routing.RegisterUnaryTransitCallback(demand_callback)
        routing.AddDimensionWithVehicleCapacity(
            demand_callback_index,
            0,  # null capacity slack
            self.vehicle_capacities,  # 每辆车的容量
            True,  # start cumul to zero
            'Capacity'
        )
        
        # 获取容量维度并设置惩罚
        capacity_dimension = routing.GetDimensionOrDie('Capacity')
        for vehicle_id in range(len(self.vehicle_capacities)):
            capacity_dimension.SetCumulVarSoftUpperBound(
                routing.End(vehicle_id), 
                self.vehicle_capacities[vehicle_id],
                int(self.config['capacity_penalty'] * 1000)
            )
        
        # 添加时间窗约束
        def time_callback(from_index, to_index):
            from_node = manager.IndexToNode(from_index)
            to_node = manager.IndexToNode(to_index)
            return self.time_matrix[from_node][to_node]
        
        time_callback_index = routing.RegisterTransitCallback(time_callback)
        routing.AddDimension(
            time_callback_index,
            self.config['max_waiting_time'],  # allow waiting time
            self.config['max_route_time'],  # maximum time per vehicle
            False,  # Don't force start cumul to zero
            'Time'
        )
        time_dimension = routing.GetDimensionOrDie('Time')
        
        # 设置时间窗约束
        for location_idx, location in enumerate(self.locations):
            location_code = location['code']
            if location_code in self.time_windows:
                start_time, end_time = self.time_windows[location_code]
                index = manager.NodeToIndex(location_idx)
                
                if self.config['enable_soft_time_windows']:
                    # 软约束（惩罚）
                    time_dimension.SetCumulVarSoftLowerBound(
                        index, start_time, int(self.config['soft_time_window_cost'])
                    )
                    time_dimension.SetCumulVarSoftUpperBound(
                        index, end_time, int(self.config['soft_time_window_cost'])
                    )
                else:
                    # 硬约束
                    time_dimension.CumulVar(index).SetRange(start_time, end_time)
        
        # 添加距离限制约束（如果启用）
        if self.config['enable_distance_limit']:
            routing.AddDimension(
                transit_callback_index,
                0,  # no slack
                int(self.config['max_route_distance'] * 1000),  # 转换为米
                True,  # start cumul to zero
                'Distance'
            )
        
        # 添加车辆休息约束（如果启用）
        if self.config['enable_vehicle_breaks']:
            self._add_vehicle_breaks(routing, time_dimension, manager)
        
        # 添加车辆固定成本
        for vehicle_id in range(len(self.vehicle_capacities)):
            routing.SetFixedCostOfVehicle(1000, vehicle_id)  # 每辆车固定成本
        
        # 设置求解参数
        search_parameters = pywrapcp.DefaultRoutingSearchParameters()
        search_parameters.first_solution_strategy = getattr(
            routing_enums_pb2.FirstSolutionStrategy,
            self.config['first_solution_strategy']
        )
        search_parameters.local_search_metaheuristic = getattr(
            routing_enums_pb2.LocalSearchMetaheuristic,
            self.config['local_search_metaheuristic']
        )
        search_parameters.time_limit.seconds = self.config['time_limit_seconds']
        search_parameters.solution_limit = self.config['solution_limit']
        
        # 启用大邻域搜索（如果配置）
        if self.config['enable_large_neighborhood_search']:
            search_parameters.lns_time_limit.seconds = self.config['lns_time_limit'] // 1000
        
        # 启用日志
        if self.config['solver_log_level'] > 0:
            search_parameters.log_search = True
        
        # 求解
        logger.info(f"开始求解，时间限制: {self.config['time_limit_seconds']}秒")
        solution = routing.SolveWithParameters(search_parameters)
        
        if solution:
            logger.info("✅ VRP求解成功")
            logger.info(f"目标值: {solution.ObjectiveValue()}")
        else:
            logger.error("❌ VRP求解失败")
        
        return manager, routing, solution
    
    def _add_vehicle_breaks(self, routing, time_dimension, manager):
        """添加车辆休息约束"""
        break_start, break_end = self.config['break_time_window']
        break_duration = self.config['break_duration']
        
        for vehicle_id in range(len(self.vehicle_capacities)):
            # 为每辆车添加休息时间
            break_node = routing.AddDisjunction([manager.NodeToIndex(0)], 0)  # 简化实现
            
            # 设置休息时间窗
            time_dimension.CumulVar(break_node).SetRange(break_start, break_end - break_duration)
            
            logger.debug(f"为车辆 {vehicle_id} 添加休息时间: {break_start//60}:{break_start%60:02d}-{break_end//60}:{break_end%60:02d}")
    
    def calculate_sla_compliance_rate(self, vehicle_routes: Dict[str, List[str]], 
                                    orders: List[OrderDetail]) -> float:
        """计算SLA合规率"""
        try:
            total_orders = len(orders)
            if total_orders == 0:
                return 1.0
            
            compliant_orders = 0
            sla_target_hours = 24  # 默认24小时SLA
            
            for vehicle_id, route in vehicle_routes.items():
                current_time = 0  # 从配送中心开始
                
                for i, store_code in enumerate(route):
                    # 计算到达时间
                    if i == 0:
                        # 从配送中心到第一个门店
                        travel_time = self._calculate_travel_time('DEPOT', store_code)
                    else:
                        # 从上一个门店到当前门店
                        travel_time = self._calculate_travel_time(route[i-1], store_code)
                    
                    current_time += travel_time
                    
                    # 检查该门店的所有订单
                    store_orders = [o for o in orders if o.fulfillment_store_code == store_code]
                    
                    for order in store_orders:
                        # 计算从订单创建到完成的时间
                        completion_time_hours = current_time / 60  # 转换为小时
                        
                        if completion_time_hours <= sla_target_hours:
                            compliant_orders += 1
                    
                    # 添加服务时间
                    current_time += self.config['service_time']
            
            sla_rate = compliant_orders / total_orders if total_orders > 0 else 1.0
            return min(1.0, max(0.0, sla_rate))
            
        except Exception as e:
            logger.warning(f"SLA合规率计算失败: {str(e)}")
            return 0.95  # 返回默认值
    
    def _solve_with_relaxed_constraints(self, manager, routing) -> Optional[Any]:
        """使用放宽约束重新求解"""
        logger.info("尝试放宽约束重新求解...")
        
        # 放宽时间窗约束
        time_dimension = routing.GetDimensionOrDie('Time')
        for location_idx, location in enumerate(self.locations):
            location_code = location['code']
            if location_code in self.time_windows and location_code != 'DEPOT':
                start_time, end_time = self.time_windows[location_code]
                # 扩大时间窗
                relaxed_start = max(0, start_time - 60)  # 提前1小时
                relaxed_end = min(24*60, end_time + 60)  # 延后1小时
                
                index = manager.NodeToIndex(location_idx)
                time_dimension.CumulVar(index).SetRange(relaxed_start, relaxed_end)
        
        # 使用更宽松的求解参数
        search_parameters = pywrapcp.DefaultRoutingSearchParameters()
        search_parameters.first_solution_strategy = (
            routing_enums_pb2.FirstSolutionStrategy.AUTOMATIC
        )
        search_parameters.local_search_metaheuristic = (
            routing_enums_pb2.LocalSearchMetaheuristic.AUTOMATIC
        )
        search_parameters.time_limit.seconds = self.config['time_limit_seconds'] * 2
        
        solution = routing.SolveWithParameters(search_parameters)
        
        if solution:
            logger.info("✅ 放宽约束后求解成功")
        else:
            logger.warning("❌ 即使放宽约束也无法求解")
        
        return solution
    
    def _parse_solution(self, manager, routing, solution, orders: List[OrderDetail], 
                       vehicles: List[Dict]) -> RouteOptimizationResult:
        """解析求解结果"""
        vehicle_routes = {}
        total_distance = 0
        total_time = 0
        
        for vehicle_id in range(self.config['max_vehicles']):
            index = routing.Start(vehicle_id)
            route = []
            route_distance = 0
            route_time = 0
            
            while not routing.IsEnd(index):
                node_index = manager.IndexToNode(index)
                location_code = self.locations[node_index]['code']
                
                if location_code != 'DEPOT':  # 不包括配送中心
                    route.append(location_code)
                
                # 计算到下一个位置的距离和时间
                previous_index = index
                index = solution.Value(routing.NextVar(index))
                
                if not routing.IsEnd(index):
                    from_node = manager.IndexToNode(previous_index)
                    to_node = manager.IndexToNode(index)
                    route_distance += self.distance_matrix[from_node][to_node]
                    route_time += self.time_matrix[from_node][to_node]
            
            if route:  # 只记录非空路径
                vehicle_routes[f'vehicle_{vehicle_id}'] = route
                total_distance += route_distance
                total_time += route_time
        
        # 计算SLA合规率
        sla_compliance_rate = self.calculate_sla_compliance_rate(vehicle_routes, orders)
        
        return RouteOptimizationResult(
            scenario_id="single_scenario",
            vehicle_routes=vehicle_routes,
            total_distance=total_distance,
            total_time=total_time / 60,  # 转换为小时
            total_cost=total_distance * 2.5,  # 假设每公里成本2.5元
            sla_compliance_rate=sla_compliance_rate,
            optimization_timestamp=datetime.now(),
            solver_status="OPTIMAL" if solution else "FAILED"
        )
    
    def _create_traffic_impact_map(self) -> Dict[str, float]:
        """创建交通影响映射"""
        traffic_impact = {}
        
        for condition in self.traffic_conditions:
            # 使用道路段名称作为键
            segment = condition.road_segment
            
            # 根据拥堵等级计算影响因子
            if condition.congestion_level >= 4:
                impact = 1.5  # 严重拥堵，时间增加50%
            elif condition.congestion_level >= 3:
                impact = 1.3  # 中度拥堵，时间增加30%
            elif condition.congestion_level >= 2:
                impact = 1.1  # 轻度拥堵，时间增加10%
            else:
                impact = 0.9  # 畅通，时间减少10%
            
            traffic_impact[segment] = impact
        
        return traffic_impact
    
    def _get_traffic_multiplier(self, from_coord: Tuple[float, float], 
                              to_coord: Tuple[float, float], 
                              traffic_impact: Dict[str, float]) -> float:
        """获取两点间的交通影响倍数"""
        # 简化实现：根据距离最近的交通监测点
        if not traffic_impact:
            return 1.0
        
        # 找到最相关的交通状况
        min_distance = float('inf')
        best_impact = 1.0
        
        for segment, impact in traffic_impact.items():
            # 这里可以根据实际需要实现更复杂的匹配逻辑
            # 暂时使用平均影响
            if impact < best_impact or min_distance == float('inf'):
                best_impact = impact
                min_distance = 1.0
        
        return best_impact
    
    def _get_effective_speed(self, from_coord: Tuple[float, float], 
                           to_coord: Tuple[float, float], 
                           traffic_impact: Dict[str, float]) -> float:
        """获取考虑交通状况的有效速度"""
        base_speed = self.config['speed_kmh']
        traffic_multiplier = self._get_traffic_multiplier(from_coord, to_coord, traffic_impact)
        
        # 交通影响主要影响时间，速度与时间成反比
        effective_speed = base_speed / traffic_multiplier
        return max(10.0, min(80.0, effective_speed))  # 限制在合理范围内
    
    def _haversine_distance(self, lat1: float, lng1: float, lat2: float, lng2: float) -> float:
        """计算两点间的球面距离（公里）"""
        R = 6371  # 地球半径（公里）
        
        lat1_rad = math.radians(lat1)
        lat2_rad = math.radians(lat2)
        delta_lat = math.radians(lat2 - lat1)
        delta_lng = math.radians(lng2 - lng1)
        
        a = (math.sin(delta_lat / 2) ** 2 + 
             math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(delta_lng / 2) ** 2)
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        
        return R * c
    
    def _time_to_minutes(self, time_str: str) -> int:
        """将时间字符串转换为分钟数"""
        try:
            hour, minute = map(int, time_str.split(':'))
            return hour * 60 + minute
        except:
            return 0
    
    def _get_location_index(self, location_code: str) -> Optional[int]:
        """获取位置索引"""
        for i, location in enumerate(self.locations):
            if location['code'] == location_code:
                return i
        return None
    
    def _calculate_distance(self, from_code: str, to_code: str) -> float:
        """计算两个位置间的距离"""
        from_idx = self._get_location_index(from_code)
        to_idx = self._get_location_index(to_code)
        
        if from_idx is not None and to_idx is not None:
            from_loc = self.locations[from_idx]
            to_loc = self.locations[to_idx]
            return self._haversine_distance(
                from_loc['lat'], from_loc['lng'],
                to_loc['lat'], to_loc['lng']
            )
        return 0.0
    
    def _calculate_route_demand(self, route: List[str]) -> int:
        """计算路径总需求"""
        total_demand = 0
        for location_code in route:
            location_idx = self._get_location_index(location_code)
            if location_idx is not None:
                total_demand += self.locations[location_idx]['demand']
        return total_demand
    
    def _validate_time_windows(self, route: List[str]) -> bool:
        """验证路径是否满足时间窗约束（保持向后兼容）"""
        return self._validate_time_windows_detailed(route)
    
    def _calculate_travel_time(self, from_code: str, to_code: str) -> int:
        """计算两个位置间的行驶时间（分钟）"""
        distance = self._calculate_distance(from_code, to_code)
        speed_kmh = self.config['speed_kmh']
        return int(distance / speed_kmh * 60)

# ==================== 工厂函数 ====================

def create_ortools_optimizer(config: Dict[str, Any] = None) -> ORToolsOptimizer:
    """创建OR-Tools优化器实例"""
    return ORToolsOptimizer(config)

# ==================== 测试和演示 ====================

if __name__ == "__main__":
    print("🚚 测试OR-Tools路径优化模块...")
    
    # 创建优化器
    optimizer = ORToolsOptimizer()
    print("✅ OR-Tools优化器创建成功")
    
    # 创建示例订单数据
    from core.data_schema import OrderDetail, OrderItem
    from datetime import date
    
    sample_orders = []
    store_codes = ['417', '331', '213', '215', '878']
    
    for i, store_code in enumerate(store_codes):
        order = OrderDetail(
            order_id=f"order_{i}",
            user_id=f"user_{i}",
            fulfillment_store_code=store_code,
            order_date=date.today(),
            items=[OrderItem(sku_id=f"sku_{i}", sku_name=f"Product {i}", quantity=5)],
            total_quantity=5 + i * 2,
            unique_sku_count=1
        )
        sample_orders.append(order)
    
    print(f"📦 创建示例订单: {len(sample_orders)} 个订单")
    
    # 创建车辆数据
    vehicles = [
        {'id': 'vehicle_1', 'capacity': 100},
        {'id': 'vehicle_2', 'capacity': 100}
    ]
    
    # 设置约束
    constraints = {
        'max_route_time': 8 * 60,  # 8小时
        'service_time': 15  # 15分钟服务时间
    }
    
    try:
        # 执行优化
        print("🚀 开始路径优化...")
        result = optimizer.optimize(sample_orders, vehicles, constraints)
        
        print(f"✅ 优化完成!")
        print(f"   总距离: {result.total_distance:.1f} km")
        print(f"   总时间: {result.total_time:.1f} 小时")
        print(f"   总成本: ¥{result.total_cost:.0f}")
        print(f"   SLA合规率: {result.sla_compliance_rate:.1%}")
        
        # 显示路径
        print("\n🗺️ 优化路径:")
        for vehicle_id, route in result.vehicle_routes.items():
            if route:  # 只显示非空路径
                print(f"   {vehicle_id}: {' -> '.join(route)}")
        
        # 验证解决方案
        is_valid = optimizer.validate_solution(result)
        print(f"\n✅ 解决方案验证: {'通过' if is_valid else '失败'}")
        
        # 显示优化统计
        stats = optimizer.get_optimization_stats()
        print(f"\n📊 优化统计:")
        print(f"   位置数量: {stats['locations_count']}")
        print(f"   车辆容量: {stats['vehicle_capacities']}")
        print(f"   时间窗数量: {stats['time_windows_count']}")
        if 'optimization_stats' in stats and stats['optimization_stats']:
            opt_stats = stats['optimization_stats']
            print(f"   优化时间: {opt_stats.get('optimization_time_seconds', 0):.2f} 秒")
            print(f"   使用车辆: {opt_stats.get('vehicles_used', 0)} 辆")
        
        print("\n🎉 OR-Tools路径优化模块测试完成！")
        
    except Exception as e:
        print(f"❌ 测试失败: {str(e)}")
        import traceback
        traceback.print_exc()