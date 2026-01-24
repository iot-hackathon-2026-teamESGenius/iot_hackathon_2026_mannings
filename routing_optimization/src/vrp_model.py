"""
VRP Model using Google OR-Tools
使用Google OR-Tools构建VRP+Time Window模型
"""

from ortools.constraint_solver import routing_enums_pb2
from ortools.constraint_solver import pywrapcp
import numpy as np
from typing import Dict, List, Tuple


class VRPModel:
    """
    CVRPTW Model using Google OR-Tools
    带容量和时间窗口约束的车辆路径问题模型
    """
    
    def __init__(self, vrp_input: Dict, distance_matrix: np.ndarray, time_matrix: np.ndarray):
        """
        Initialize VRP Model
        
        Args:
            vrp_input: VRP input data dictionary
            distance_matrix: Distance matrix (scaled to integers)
            time_matrix: Time matrix in minutes
        """
        self.vrp_input = vrp_input
        self.distance_matrix = distance_matrix.astype(int)
        self.time_matrix = time_matrix.astype(int)
        
        self.num_vehicles = vrp_input['num_vehicles']
        self.depot = 0  # Depot is always index 0
        
        # Extract demands
        self.demands = [0]  # Depot has 0 demand
        for store in vrp_input['stores']:
            self.demands.append(int(store['demand']))
        
        # Extract time windows
        self.time_windows = [(0, 999999)]  # Depot has flexible time window
        for store in vrp_input['stores']:
            tw = store.get('time_window', (0, 999999))
            self.time_windows.append(tw)
        
        # Vehicle capacity
        self.vehicle_capacity = int(vrp_input['vehicle_capacity'])
        
        # Service time per location
        self.service_time = 15  # 15 minutes per stop
        
        # Initialize OR-Tools components
        self.manager = None
        self.routing = None
        self.solution = None
    
    def create_model(self):
        """
        Create OR-Tools routing model with constraints
        创建OR-Tools路由模型：包含距离、容量、时间窗口约束
        """
        # Step 1: Initialize routing index manager
        # 创建路由索引管理器（管理节点-客户映射）
        self.manager = pywrapcp.RoutingIndexManager(
            len(self.distance_matrix),  # 总节点数（仓库+门店）
            self.num_vehicles,           # 车辆数量
            self.depot                   # 仓库索引（通常为0）
        )
        
        # Step 2: Create routing model
        # 创建路由模型
        self.routing = pywrapcp.RoutingModel(self.manager)
        
        # Step 3: Add distance callback and set as cost
        # 添加距离回调函数：定义节点间的距离
        def distance_callback(from_index, to_index):
            # 将路由索引转换回节点索引
            from_node = self.manager.IndexToNode(from_index)
            to_node = self.manager.IndexToNode(to_index)
            return self.distance_matrix[from_node][to_node]
        
        distance_callback_index = self.routing.RegisterTransitCallback(distance_callback)
        # 设置距离为成本函数（优化目标）
        self.routing.SetArcCostEvaluatorOfAllVehicles(distance_callback_index)
        
        # Step 4: Add capacity constraint
        # 添加容量约束：每个车辆的容量限制
        def demand_callback(from_index):
            from_node = self.manager.IndexToNode(from_index)
            return self.demands[from_node]  # 返回该节点的需求量
        
        demand_callback_index = self.routing.RegisterUnaryTransitCallback(demand_callback)
        self.routing.AddDimensionWithVehicleCapacity(
            demand_callback_index,
            0,  # Null capacity slack (无额外容量缓冲)
            [self.vehicle_capacity] * self.num_vehicles,  # 每辆车的最大容量
            True,  # Start cumul to zero (从0开始累计)
            'Capacity'  # 约束名称
        )
        
        # Step 5: Add time dimension with time windows
        # 添加时间维度约束：处理时间窗口和行驶时间
        def time_callback(from_index, to_index):
            from_node = self.manager.IndexToNode(from_index)
            to_node = self.manager.IndexToNode(to_index)
            travel_time = self.time_matrix[from_node][to_node]
            # 添加服务时间（仓库无服务时间）
            service_time = self.service_time if from_node != 0 else 0
            return travel_time + service_time
        
        time_callback_index = self.routing.RegisterTransitCallback(time_callback)
        
        # 创建时间维度
        time_dimension_name = 'Time'
        self.routing.AddDimension(
            time_callback_index,
            30,          # 最大等待时间（分钟）
            999999,      # 每辆车的最大总时间
            False,       # 不强制起始时间为0
            time_dimension_name
        )
        
        time_dimension = self.routing.GetDimensionOrDie(time_dimension_name)
        
        # Step 6: Set time windows for each location
        # 为每个位置设置时间窗口
        for location_idx, time_window in enumerate(self.time_windows):
            if location_idx == self.depot:
                continue  # 跳过仓库（在步骤7单独处理）
            index = self.manager.NodeToIndex(location_idx)
            # 设置该客户的可访问时间范围
            time_dimension.CumulVar(index).SetRange(time_window[0], time_window[1])
        
        # Step 7: Set depot time constraints
        # 设置仓库的运营时间窗口
        depot_index = self.manager.NodeToIndex(self.depot)
        time_dimension.CumulVar(depot_index).SetRange(
            self.time_windows[0][0],
            self.time_windows[0][1]
        )
        
        # 为每辆车的出发点设置时间约束
        for vehicle_id in range(self.num_vehicles):
            start_index = self.routing.Start(vehicle_id)
            time_dimension.CumulVar(start_index).SetRange(
                self.time_windows[0][0],
                self.time_windows[0][1]
            )
        
        # Step 8: Add SLA violation penalty
        # 添加SLA违反惩罚：无法按时送达的客户需要付出高成本
        penalty = 10000  # 极高的惩罚值，使求解器尽量避免违反
        for node in range(1, len(self.distance_matrix)):
            # 允许节点被"丢弃"（不访问），但要付出penalty代价
            self.routing.AddDisjunction([self.manager.NodeToIndex(node)], penalty)
    
    def solve(self, time_limit_seconds: int = 30):
        """
        Solve the VRP model using OR-Tools solver
        使用OR-Tools求解VRP问题
        
        Args:
            time_limit_seconds: 最大求解时间（秒）
        
        Returns:
            Solution object from OR-Tools
        """
        # Step 1: Configure search parameters
        # 配置搜索参数
        search_parameters = pywrapcp.DefaultRoutingSearchParameters()
        
        # 初始化策略：PATH_CHEAPEST_ARC快速构建初始解
        search_parameters.first_solution_strategy = (
            routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC
        )
        
        # 局部搜索元启发式：GUIDED_LOCAL_SEARCH用于改进初始解
        search_parameters.local_search_metaheuristic = (
            routing_enums_pb2.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH
        )
        
        # 设置最大求解时间
        search_parameters.time_limit.seconds = time_limit_seconds
        
        # Step 2: Solve the problem
        # 运行求解器
        self.solution = self.routing.SolveWithParameters(search_parameters)
        
        return self.solution
    
    def get_solution_details(self) -> Dict:
        """
        Extract solution details
        提取解决方案详情
        
        Returns:
            Dictionary with solution details
        """
        if not self.solution:
            return {'status': 'No solution found'}
        
        solution_dict = {
            'status': 'Success',
            'total_distance': 0,
            'total_time': 0,
            'routes': [],
            'dropped_nodes': []
        }
        
        time_dimension = self.routing.GetDimensionOrDie('Time')
        total_distance = 0
        total_time = 0
        
        for vehicle_id in range(self.num_vehicles):
            index = self.routing.Start(vehicle_id)
            route = {
                'vehicle_id': vehicle_id,
                'sequence': [],
                'distance': 0,
                'load': 0,
                'times': []
            }
            
            route_distance = 0
            route_load = 0
            
            while not self.routing.IsEnd(index):
                node_index = self.manager.IndexToNode(index)
                route_load += self.demands[node_index]
                
                time_var = time_dimension.CumulVar(index)
                arrival_time = self.solution.Value(time_var)
                
                route['sequence'].append(node_index)
                route['times'].append(arrival_time)
                
                previous_index = index
                index = self.solution.Value(self.routing.NextVar(index))
                route_distance += self.routing.GetArcCostForVehicle(
                    previous_index, index, vehicle_id
                )
            
            # Add final node (return to depot)
            node_index = self.manager.IndexToNode(index)
            time_var = time_dimension.CumulVar(index)
            arrival_time = self.solution.Value(time_var)
            route['sequence'].append(node_index)
            route['times'].append(arrival_time)
            
            route['distance'] = route_distance
            route['load'] = route_load
            
            if len(route['sequence']) > 2:  # Only add non-empty routes
                solution_dict['routes'].append(route)
                total_distance += route_distance
                total_time += arrival_time
        
        solution_dict['total_distance'] = total_distance
        solution_dict['total_time'] = total_time
        
        # Check for dropped nodes (SLA violations)
        for node in range(1, len(self.distance_matrix)):
            index = self.manager.NodeToIndex(node)
            if self.solution.Value(self.routing.NextVar(index)) == index:
                solution_dict['dropped_nodes'].append(node)
        
        return solution_dict
