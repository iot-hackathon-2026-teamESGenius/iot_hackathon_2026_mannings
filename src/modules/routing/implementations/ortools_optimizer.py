"""
OR-Tools optimizer wrapper with configurable strategies.
封装 OR-Tools VRP 模型，支持通过 config 调参。
"""

from typing import Dict
import numpy as np
from ortools.constraint_solver import routing_enums_pb2, pywrapcp
import config


# Mapping helpers to keep config string-driven
_FIRST_SOLUTION_MAP = {
    'PATH_CHEAPEST_ARC': routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC,
    'AUTOMATIC': routing_enums_pb2.FirstSolutionStrategy.AUTOMATIC,
    'PARALLEL_CHEAPEST_INSERTION': routing_enums_pb2.FirstSolutionStrategy.PARALLEL_CHEAPEST_INSERTION,
    'SAVINGS': routing_enums_pb2.FirstSolutionStrategy.SAVINGS,
}

_META_MAP = {
    'GUIDED_LOCAL_SEARCH': routing_enums_pb2.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH,
    'AUTOMATIC': routing_enums_pb2.LocalSearchMetaheuristic.AUTOMATIC,
    'TABU_SEARCH': routing_enums_pb2.LocalSearchMetaheuristic.TABU_SEARCH,
    'SIMULATED_ANNEALING': routing_enums_pb2.LocalSearchMetaheuristic.SIMULATED_ANNEALING,
}


class VRPModel:
    """Capacity + Time-Window VRP using OR-Tools."""

    def __init__(self, vrp_input: Dict, distance_matrix: np.ndarray, time_matrix: np.ndarray):
        self.vrp_input = vrp_input
        self.distance_matrix = distance_matrix.astype(int)
        self.time_matrix = time_matrix.astype(int)

        self.num_vehicles = vrp_input['num_vehicles']
        self.depot = 0

        # Demands (0 for depot)
        self.demands = [0]
        for store in vrp_input['stores']:
            self.demands.append(int(store['demand']))

        # Time windows (depot window uses config)
        self.time_windows = [(config.DEPOT_OPEN_TIME, config.DEPOT_CLOSE_TIME)]
        for store in vrp_input['stores']:
            tw = store.get('time_window', (0, 999999))
            self.time_windows.append(tw)

        self.vehicle_capacity = int(vrp_input['vehicle_capacity'])
        self.service_time = config.SERVICE_TIME

        self.manager = None
        self.routing = None
        self.solution = None

    def _add_distance(self):
        def distance_callback(from_index, to_index):
            from_node = self.manager.IndexToNode(from_index)
            to_node = self.manager.IndexToNode(to_index)
            return self.distance_matrix[from_node][to_node]

        idx = self.routing.RegisterTransitCallback(distance_callback)
        self.routing.SetArcCostEvaluatorOfAllVehicles(idx)

    def _add_capacity(self):
        def demand_callback(from_index):
            from_node = self.manager.IndexToNode(from_index)
            return self.demands[from_node]

        idx = self.routing.RegisterUnaryTransitCallback(demand_callback)
        self.routing.AddDimensionWithVehicleCapacity(
            idx,
            0,
            [self.vehicle_capacity] * self.num_vehicles,
            True,
            'Capacity'
        )

    def _add_time_windows(self):
        def time_callback(from_index, to_index):
            from_node = self.manager.IndexToNode(from_index)
            to_node = self.manager.IndexToNode(to_index)
            travel_time = int(self.time_matrix[from_node][to_node])
            service_time = self.service_time if from_node != 0 else 0
            return int(travel_time + service_time)

        idx = self.routing.RegisterTransitCallback(time_callback)
        name = 'Time'
        self.routing.AddDimension(
            idx,
            30,        # waiting slack
            999999,    # horizon
            False,
            name
        )
        time_dimension = self.routing.GetDimensionOrDie(name)

        for loc, tw in enumerate(self.time_windows):
            if loc == self.depot:
                continue
            index = self.manager.NodeToIndex(loc)
            time_dimension.CumulVar(index).SetRange(tw[0], tw[1])

        depot_index = self.manager.NodeToIndex(self.depot)
        time_dimension.CumulVar(depot_index).SetRange(
            self.time_windows[0][0],
            self.time_windows[0][1]
        )
        for v in range(self.num_vehicles):
            start_index = self.routing.Start(v)
            time_dimension.CumulVar(start_index).SetRange(
                self.time_windows[0][0],
                self.time_windows[0][1]
            )

        # Allow drop with penalty
        penalty = getattr(config, 'SLA_VIOLATION_PENALTY', 10000)
        for node in range(1, len(self.distance_matrix)):
            self.routing.AddDisjunction([self.manager.NodeToIndex(node)], penalty)

    def create_model(self):
        self.manager = pywrapcp.RoutingIndexManager(
            len(self.distance_matrix),
            self.num_vehicles,
            self.depot,
        )
        self.routing = pywrapcp.RoutingModel(self.manager)

        self._add_distance()
        self._add_capacity()
        self._add_time_windows()

    def solve(self, time_limit_seconds: int = 30):
        search_parameters = pywrapcp.DefaultRoutingSearchParameters()

        fs_key = getattr(config, 'FIRST_SOLUTION_STRATEGY', 'PATH_CHEAPEST_ARC')
        mh_key = getattr(config, 'LOCAL_SEARCH_METAHEURISTIC', 'GUIDED_LOCAL_SEARCH')
        search_parameters.first_solution_strategy = _FIRST_SOLUTION_MAP.get(fs_key, _FIRST_SOLUTION_MAP['PATH_CHEAPEST_ARC'])
        search_parameters.local_search_metaheuristic = _META_MAP.get(mh_key, _META_MAP['GUIDED_LOCAL_SEARCH'])

        search_parameters.time_limit.seconds = time_limit_seconds
        search_parameters.log_search = bool(getattr(config, 'LOG_SEARCH', False))

        num_workers = int(getattr(config, 'NUM_SEARCH_WORKERS', 0))
        if num_workers > 0:
            search_parameters.number_of_search_workers = num_workers

        solution_limit = int(getattr(config, 'SOLUTION_LIMIT', 0))
        if solution_limit > 0:
            search_parameters.solution_limit = solution_limit
        self.solution = self.routing.SolveWithParameters(search_parameters)
        return self.solution

    def get_solution_details(self) -> Dict:
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
                route_distance += self.routing.GetArcCostForVehicle(previous_index, index, vehicle_id)

            # return to depot
            node_index = self.manager.IndexToNode(index)
            time_var = time_dimension.CumulVar(index)
            arrival_time = self.solution.Value(time_var)
            route['sequence'].append(node_index)
            route['times'].append(arrival_time)

            route['distance'] = route_distance
            route['load'] = route_load

            if len(route['sequence']) > 2:
                solution_dict['routes'].append(route)
                total_distance += route_distance
                total_time += arrival_time

        solution_dict['total_distance'] = total_distance
        solution_dict['total_time'] = total_time

        for node in range(1, len(self.distance_matrix)):
            index = self.manager.NodeToIndex(node)
            if self.solution.Value(self.routing.NextVar(index)) == index:
                solution_dict['dropped_nodes'].append(node)

        return solution_dict
