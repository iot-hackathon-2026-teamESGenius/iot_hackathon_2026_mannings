"""
Solution data model for delivery route optimization
"""

class Solution:
    """
    Represents a complete solution with multiple routes
    """
    
    def __init__(self):
        """Initialize an empty solution"""
        self.routes = []
        self.total_distance = 0.0
        self.total_time = 0.0
        self.vehicles_used = 0
        self.computation_time = 0.0
        self.algorithm_name = ""
    
    def add_route(self, route):
        """Add a route to the solution"""
        self.routes.append(route)
        self.total_distance += route.total_distance
        self.total_time += route.total_time
        self.vehicles_used = len(self.routes)
    
    def calculate_metrics(self):
        """Calculate solution metrics"""
        self.total_distance = sum(route.total_distance for route in self.routes)
        self.total_time = sum(route.total_time for route in self.routes)
        self.vehicles_used = len(self.routes)
    
    def is_valid(self, customers):
        """Check if solution is valid (all customers served exactly once)"""
        served_customers = set()
        for route in self.routes:
            for customer_id in route.customers:
                if customer_id in served_customers:
                    return False  # Customer served multiple times
                served_customers.add(customer_id)
        
        return len(served_customers) == len(customers)
    
    def __repr__(self):
        return f"Solution(routes={len(self.routes)}, distance={self.total_distance:.2f}, time={self.computation_time:.4f}s)"
    
    def to_dict(self):
        """Convert solution to dictionary format"""
        return {
            'routes': [route.to_dict() for route in self.routes],
            'metrics': {
                'total_distance': self.total_distance,
                'total_time': self.total_time,
                'vehicles_used': self.vehicles_used,
                'computation_time': self.computation_time,
                'algorithm': self.algorithm_name
            }
        }
