"""
Data validation utilities for route optimization
"""

def validate_input_data(data):
    """
    Validate input data structure and constraints
    
    Args:
        data (dict): Input data dictionary
    
    Returns:
        tuple: (is_valid, error_message)
    """
    # Check required keys
    required_keys = ['depot', 'customers', 'vehicles']
    for key in required_keys:
        if key not in data:
            return False, f"Missing required key: {key}"
    
    # Validate depot
    depot = data['depot']
    if 'lat' not in depot or 'lon' not in depot:
        return False, "Depot must have 'lat' and 'lon' coordinates"
    
    # Validate customers
    customers = data['customers']
    if not customers:
        return False, "No customers provided"
    
    for i, customer in enumerate(customers):
        if 'id' not in customer:
            return False, f"Customer {i} missing 'id'"
        if 'lat' not in customer or 'lon' not in customer:
            return False, f"Customer {customer.get('id', i)} missing coordinates"
        if 'demand' not in customer:
            return False, f"Customer {customer.get('id', i)} missing 'demand'"
        if customer['demand'] < 0:
            return False, f"Customer {customer.get('id', i)} has negative demand"
    
    # Validate vehicles
    vehicles = data['vehicles']
    if not vehicles:
        return False, "No vehicles provided"
    
    for i, vehicle in enumerate(vehicles):
        if 'id' not in vehicle:
            return False, f"Vehicle {i} missing 'id'"
        if 'capacity' not in vehicle:
            return False, f"Vehicle {vehicle.get('id', i)} missing 'capacity'"
        if vehicle['capacity'] <= 0:
            return False, f"Vehicle {vehicle.get('id', i)} has non-positive capacity"
    
    # Check if total demand can be satisfied by total capacity
    total_demand = sum(c['demand'] for c in customers)
    total_capacity = sum(v['capacity'] for v in vehicles)
    if total_demand > total_capacity:
        return False, f"Total demand ({total_demand}) exceeds total capacity ({total_capacity})"
    
    return True, "Input data is valid"


def check_capacity_constraint(route_load, vehicle_capacity):
    """
    Check if route satisfies capacity constraint
    
    Args:
        route_load (float): Current load on the route
        vehicle_capacity (float): Vehicle capacity
    
    Returns:
        bool: True if constraint is satisfied
    """
    return route_load <= vehicle_capacity


def check_time_window_constraint(arrival_time, time_window):
    """
    Check if arrival time satisfies time window constraint
    
    Args:
        arrival_time (float): Arrival time at customer
        time_window (tuple): (earliest, latest) time window
    
    Returns:
        bool: True if constraint is satisfied
    """
    if time_window is None:
        return True
    earliest, latest = time_window
    return earliest <= arrival_time <= latest
