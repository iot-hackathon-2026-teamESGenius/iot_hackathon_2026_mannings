"""
Nearest Neighbor Algorithm for Vehicle Routing Problem
A greedy constructive heuristic that builds routes by always selecting the nearest unvisited customer
"""

import time
from ...models.route import Route
from ...models.solution import Solution
from ...utils.distance import calculate_route_distance


class NearestNeighbor:
    """
    Nearest Neighbor algorithm implementation
    Constructs routes by repeatedly selecting the closest unvisited customer
    """
    
    def __init__(self, distance_matrix, customers, vehicles, depot):
        """
        Initialize the Nearest Neighbor algorithm
        
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
        Solve the VRP using Nearest Neighbor algorithm
        
        Returns:
            Solution: Complete solution with routes
        """
        start_time = time.time()
        solution = Solution()
        solution.algorithm_name = "Nearest Neighbor"
        
        # Track unvisited customers
        unvisited = set(range(1, self.n_customers + 1))  # Customer indices (depot is 0)
        vehicle_idx = 0
        
        # Build routes until all customers are visited
        while unvisited and vehicle_idx < len(self.vehicles):
            vehicle = self.vehicles[vehicle_idx]
            route = self._construct_route(vehicle, unvisited)
            
            if route.customers:  # Only add non-empty routes
                solution.add_route(route)
            
            vehicle_idx += 1
        
        # Check if all customers are served
        if unvisited:
            print(f"Warning: {len(unvisited)} customers could not be served due to vehicle constraints")
        
        solution.computation_time = time.time() - start_time
        solution.calculate_metrics()
        
        return solution
    
    def _construct_route(self, vehicle, unvisited):
        """
        Construct a single route using nearest neighbor heuristic
        
        Args:
            vehicle: Vehicle object
            unvisited: Set of unvisited customer indices
        
        Returns:
            Route: Constructed route
        """
        route = Route(vehicle.id, self.depot)
        current_location = 0  # Start at depot
        current_load = 0.0
        
        while unvisited:
            # Find nearest unvisited customer that fits in the vehicle
            nearest_customer = None
            nearest_distance = float('inf')
            
            for customer_idx in unvisited:
                customer = self.customers[customer_idx - 1]  # Adjust for 0-based indexing
                
                # Check capacity constraint
                if current_load + customer.demand <= vehicle.capacity:
                    distance = self.distance_matrix[current_location][customer_idx]
                    if distance < nearest_distance:
                        nearest_distance = distance
                        nearest_customer = customer_idx
            
            # If no feasible customer found, return to depot
            if nearest_customer is None:
                break
            
            # Add customer to route
            customer = self.customers[nearest_customer - 1]
            route.add_customer(customer.id, customer.demand)
            current_load += customer.demand
            route.total_distance += nearest_distance
            
            # Move to customer location
            current_location = nearest_customer
            unvisited.remove(nearest_customer)
        
        # Return to depot
        if route.customers:
            route.total_distance += self.distance_matrix[current_location][0]
        
        return route
    
    def __str__(self):
        return "Nearest Neighbor Algorithm"
