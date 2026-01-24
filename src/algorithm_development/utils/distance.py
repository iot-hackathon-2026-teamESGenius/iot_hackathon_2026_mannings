"""
Distance calculation utilities for route optimization
"""

import math

def haversine_distance(lat1, lon1, lat2, lon2):
    """
    Calculate the great circle distance between two points on Earth
    using the Haversine formula
    
    Args:
        lat1, lon1: Coordinates of first point
        lat2, lon2: Coordinates of second point
    
    Returns:
        float: Distance in kilometers
    """
    R = 6371  # Earth's radius in kilometers
    
    # Convert degrees to radians
    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    delta_lat = math.radians(lat2 - lat1)
    delta_lon = math.radians(lon2 - lon1)
    
    # Haversine formula
    a = math.sin(delta_lat / 2)**2 + \
        math.cos(lat1_rad) * math.cos(lat2_rad) * \
        math.sin(delta_lon / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    
    distance = R * c
    return distance


def euclidean_distance(x1, y1, x2, y2):
    """
    Calculate Euclidean distance between two points
    
    Args:
        x1, y1: Coordinates of first point
        x2, y2: Coordinates of second point
    
    Returns:
        float: Euclidean distance
    """
    return math.sqrt((x2 - x1)**2 + (y2 - y1)**2)


def manhattan_distance(x1, y1, x2, y2):
    """
    Calculate Manhattan distance between two points
    
    Args:
        x1, y1: Coordinates of first point
        x2, y2: Coordinates of second point
    
    Returns:
        float: Manhattan distance
    """
    return abs(x2 - x1) + abs(y2 - y1)


def create_distance_matrix(locations, distance_function=haversine_distance):
    """
    Create a distance matrix for all locations
    
    Args:
        locations: List of (lat, lon) or (x, y) tuples
        distance_function: Function to calculate distance
    
    Returns:
        list: 2D distance matrix
    """
    n = len(locations)
    matrix = [[0.0] * n for _ in range(n)]
    
    for i in range(n):
        for j in range(i + 1, n):
            dist = distance_function(
                locations[i][0], locations[i][1],
                locations[j][0], locations[j][1]
            )
            matrix[i][j] = dist
            matrix[j][i] = dist
    
    return matrix


def calculate_route_distance(route_sequence, distance_matrix):
    """
    Calculate total distance for a route sequence
    
    Args:
        route_sequence: List of location indices in visit order
        distance_matrix: 2D distance matrix
    
    Returns:
        float: Total distance
    """
    total_distance = 0.0
    for i in range(len(route_sequence) - 1):
        total_distance += distance_matrix[route_sequence[i]][route_sequence[i + 1]]
    return total_distance
