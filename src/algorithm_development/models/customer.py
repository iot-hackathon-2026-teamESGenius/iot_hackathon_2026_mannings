"""
Customer data model for delivery route optimization
"""

class Customer:
    """
    Represents a customer location with delivery requirements
    """
    
    def __init__(self, customer_id, latitude, longitude, demand, time_window=None, service_time=0):
        """
        Initialize a customer
        
        Args:
            customer_id (int): Unique identifier for the customer
            latitude (float): Latitude coordinate
            longitude (float): Longitude coordinate
            demand (float): Delivery demand/requirement
            time_window (tuple): Optional (earliest, latest) time window for delivery
            service_time (float): Time required to service this customer
        """
        self.id = customer_id
        self.lat = latitude
        self.lon = longitude
        self.demand = demand
        self.time_window = time_window
        self.service_time = service_time
    
    def __repr__(self):
        return f"Customer(id={self.id}, lat={self.lat}, lon={self.lon}, demand={self.demand})"
    
    def to_dict(self):
        """Convert customer to dictionary format"""
        return {
            'id': self.id,
            'lat': self.lat,
            'lon': self.lon,
            'demand': self.demand,
            'time_window': self.time_window,
            'service_time': self.service_time
        }
