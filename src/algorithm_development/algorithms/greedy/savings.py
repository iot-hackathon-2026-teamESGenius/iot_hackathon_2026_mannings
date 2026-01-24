"""
Savings Algorithm (Clarke-Wright) for Vehicle Routing Problem
A classical heuristic that merges routes based on distance savings
"""

import time
from ...models.route import Route
from ...models.solution import Solution


class SavingsAlgorithm:
    """
    Clarke-Wright Savings Algorithm implementation
    Constructs routes by merging them based on maximum savings
    """
    
    def __init__(self, distance_matrix, customers, vehicles, depot):
        """
        Initialize the Savings algorithm
        
        Args:
            distance_matrix: 2D distance matrix (depot at index 0)
            customers: List of Customer objects
            vehicles: List of Vehicle objects
            depot: Depot coordinates (lat, lon)
        """
        self.distance_matrix = distance_matrix
        self.customers = customers
        self.vehicles = vehicles
        self.depot = depot
        self.n_customers = len(customers)
    
    def solve(self):
        """
        Solve the VRP using Savings algorithm
        
        Returns:
            Solution: Complete solution with routes
        """
        start_time = time.time()
        solution = Solution()
        solution.algorithm_name = "Clarke-Wright Savings"
        
        # Step 1: Calculate savings for all customer pairs
        savings = self._calculate_savings()
        
        # Sort savings in descending order
        savings.sort(key=lambda x: x[2], reverse=True)
        
        # Step 2: Initialize routes (each customer in separate route)
        routes = self._initialize_routes()
        
        # Step 3: Merge routes based on savings
        routes = self._merge_routes(routes, savings)
        
        # Step 4: Build solution
        for route in routes:
            if route.customers:
                solution.add_route(route)
        
        solution.computation_time = time.time() - start_time
        solution.calculate_metrics()
        
        return solution
    
    def _calculate_savings(self):
        """
        Calculate savings for merging each pair of customers
        Saving(i,j) = distance(0,i) + distance(0,j) - distance(i,j)
        
        Returns:
            list: List of (customer_i, customer_j, saving) tuples
        """
        savings = []
        
        for i in range(1, self.n_customers + 1):
            for j in range(i + 1, self.n_customers + 1):
                saving = (self.distance_matrix[0][i] + 
                         self.distance_matrix[0][j] - 
                         self.distance_matrix[i][j])
                savings.append((i, j, saving))
        
        return savings
    
    def _initialize_routes(self):
        """
        Initialize with each customer in a separate route
        
        Returns:
            dict: Dictionary mapping customer_id to route
        """
        routes = {}
        
        for idx, customer in enumerate(self.customers):
            vehicle = self.vehicles[0]  # Use first vehicle as template
            route = Route(vehicle.id, self.depot)
            route.add_customer(customer.id, customer.demand)
            
            # Calculate distance: depot -> customer -> depot
            customer_idx = idx + 1  # Adjust for depot at index 0
            route.total_distance = (self.distance_matrix[0][customer_idx] + 
                                   self.distance_matrix[customer_idx][0])
            
            routes[customer.id] = route
        
        return routes
    
    def _merge_routes(self, routes, savings):
        """
        Merge routes based on savings while respecting constraints
        
        Args:
            routes: Dictionary of routes
            savings: Sorted list of savings
        
        Returns:
            list: List of merged routes
        """
        # Track which vehicle is assigned to each route
        vehicle_assignments = {}
        available_vehicles = list(self.vehicles)
        
        for customer_id in routes:
            if available_vehicles:
                routes[customer_id].vehicle_id = available_vehicles[0].id
                vehicle_assignments[customer_id] = available_vehicles[0]
        
        # Process savings
        for i, j, saving in savings:
            customer_i = self.customers[i - 1]
            customer_j = self.customers[j - 1]
            
            # Check if customers are in different routes
            if customer_i.id not in routes or customer_j.id not in routes:
                continue
            
            route_i = routes[customer_i.id]
            route_j = routes[customer_j.id]
            
            # Skip if same route
            if route_i == route_j:
                continue
            
            # Check if customers are at the end/start of their routes
            if not self._can_merge(route_i, route_j, customer_i.id, customer_j.id):
                continue
            
            # Check capacity constraint
            total_load = route_i.total_load + route_j.total_load
            vehicle = vehicle_assignments.get(customer_i.id, self.vehicles[0])
            
            if total_load <= vehicle.capacity:
                # Merge routes
                merged_route = self._merge_two_routes(route_i, route_j, i, j)
                
                # Update routes dictionary
                for customer_id in merged_route.customers:
                    routes[customer_id] = merged_route
        
        # Return unique routes
        unique_routes = list({id(route): route for route in routes.values()}.values())
        return unique_routes
    
    def _can_merge(self, route_i, route_j, customer_i_id, customer_j_id):
        """
        Check if two routes can be merged (customers must be at route ends)
        
        Args:
            route_i, route_j: Routes to check
            customer_i_id, customer_j_id: Customer IDs
        
        Returns:
            bool: True if routes can be merged
        """
        # Customer i must be at the end of route_i and customer j at the start of route_j
        # or vice versa
        return ((route_i.customers[-1] == customer_i_id and route_j.customers[0] == customer_j_id) or
                (route_i.customers[0] == customer_i_id and route_j.customers[-1] == customer_j_id))
    
    def _merge_two_routes(self, route_i, route_j, idx_i, idx_j):
        """
        Merge two routes
        
        Args:
            route_i, route_j: Routes to merge
            idx_i, idx_j: Customer indices in distance matrix
        
        Returns:
            Route: Merged route
        """
        merged_route = Route(route_i.vehicle_id, self.depot)
        
        # Merge customer lists
        merged_route.customers = route_i.customers + route_j.customers
        merged_route.total_load = route_i.total_load + route_j.total_load
        
        # Recalculate distance
        merged_route.total_distance = (
            route_i.total_distance + 
            route_j.total_distance - 
            self.distance_matrix[0][idx_i] - 
            self.distance_matrix[0][idx_j] +
            self.distance_matrix[idx_i][idx_j]
        )
        
        return merged_route
    
    def __str__(self):
        return "Clarke-Wright Savings Algorithm"
