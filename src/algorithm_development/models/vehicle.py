"""
Vehicle data model for delivery route optimization
"""

class Vehicle:
    """
    Represents a delivery vehicle with capacity constraints
    """
    
    def __init__(self, vehicle_id, capacity, max_distance=None, max_time=None):
        """
        Initialize a vehicle
        
        Args:
            vehicle_id (int): Unique identifier for the vehicle
            capacity (float): Maximum load capacity
            max_distance (float): Maximum travel distance allowed
            max_time (float): Maximum travel time allowed
        """
        self.id = vehicle_id
        self.capacity = capacity
        self.max_distance = max_distance
        self.max_time = max_time
    
    def __repr__(self):
        return f"Vehicle(id={self.id}, capacity={self.capacity})"
    
    def to_dict(self):
        """Convert vehicle to dictionary format"""
        return {
            'id': self.id,
            'capacity': self.capacity,
            'max_distance': self.max_distance,
            'max_time': self.max_time
        }
