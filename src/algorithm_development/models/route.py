"""
Route data model for delivery route optimization
"""

class Route:
    """
    Represents a delivery route for a single vehicle
    """
    
    def __init__(self, vehicle_id, depot):
        """
        Initialize a route
        
        Args:
            vehicle_id (int): ID of the vehicle assigned to this route
            depot (tuple): Depot coordinates (lat, lon)
        """
        self.vehicle_id = vehicle_id
        self.depot = depot
        self.customers = []  # List of customer IDs in visit order
        self.total_distance = 0.0
        self.total_time = 0.0
        self.total_load = 0.0
    
    def add_customer(self, customer_id, demand):
        """Add a customer to the route"""
        self.customers.append(customer_id)
        self.total_load += demand
    
    def remove_customer(self, customer_id, demand):
        """Remove a customer from the route"""
        if customer_id in self.customers:
            self.customers.remove(customer_id)
            self.total_load -= demand
    
    def is_feasible(self, vehicle_capacity):
        """Check if route satisfies capacity constraints"""
        return self.total_load <= vehicle_capacity
    
    def __repr__(self):
        return f"Route(vehicle={self.vehicle_id}, customers={len(self.customers)}, distance={self.total_distance:.2f})"
    
    def to_dict(self):
        """Convert route to dictionary format"""
        return {
            'vehicle_id': self.vehicle_id,
            'sequence': self.customers,
            'total_distance': self.total_distance,
            'total_time': self.total_time,
            'load': self.total_load
        }
