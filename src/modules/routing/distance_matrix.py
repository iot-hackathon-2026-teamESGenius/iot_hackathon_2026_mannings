"""
Distance and time matrix calculation
距离/时间矩阵计算 (初期可用欧式距离)
"""

import numpy as np
from typing import List, Tuple
import math


def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculate great circle distance using Haversine formula
    使用Haversine公式计算球面距离
    
    Args:
        lat1, lon1: First location coordinates
        lat2, lon2: Second location coordinates
    
    Returns:
        Distance in kilometers
    """
    R = 6371  # Earth radius in kilometers
    
    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    
    a = (math.sin(dlat / 2) ** 2 +
         math.cos(lat1_rad) * math.cos(lat2_rad) * 
         math.sin(dlon / 2) ** 2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    
    return R * c


def euclidean_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculate Euclidean distance
    计算欧几里得距离 (适用于小范围配送)
    
    Args:
        lat1, lon1: First location coordinates
        lat2, lon2: Second location coordinates
    
    Returns:
        Euclidean distance
    """
    return math.sqrt((lat2 - lat1) ** 2 + (lon2 - lon1) ** 2)


def create_distance_matrix(
    locations: List[Tuple[float, float]],
    use_euclidean: bool = True
) -> np.ndarray:
    """
    Create distance matrix for all locations
    创建所有地点之间的距离矩阵
    
    Args:
        locations: List of (lat, lon) tuples, first is depot
        use_euclidean: Use Euclidean distance if True, otherwise Haversine
    
    Returns:
        NxN distance matrix (numpy array)
    """
    n = len(locations)
    matrix = np.zeros((n, n))
    
    distance_func = euclidean_distance if use_euclidean else haversine_distance
    
    for i in range(n):
        for j in range(i + 1, n):
            dist = distance_func(
                locations[i][0], locations[i][1],
                locations[j][0], locations[j][1]
            )
            matrix[i][j] = dist
            matrix[j][i] = dist
    
    return matrix


def create_time_matrix(
    distance_matrix: np.ndarray,
    average_speed: float = 40.0
) -> np.ndarray:
    """
    Convert distance matrix to time matrix
    将距离矩阵转换为时间矩阵
    
    Args:
        distance_matrix: Distance matrix in km
        average_speed: Average vehicle speed in km/h
    
    Returns:
        Time matrix in minutes
    """
    # Time = Distance / Speed * 60 (convert to minutes)
    time_matrix = (distance_matrix / average_speed) * 60
    # Use ceil to avoid zero-minute edges; keep diagonal at 0
    time_matrix = np.where(np.eye(time_matrix.shape[0], dtype=bool), 0, np.ceil(time_matrix))
    return time_matrix.astype(int)


def scale_distance_matrix(distance_matrix: np.ndarray, scale_factor: int = 100) -> np.ndarray:
    """
    Scale distance matrix for OR-Tools integer arithmetic
    为OR-Tools整数运算缩放距离矩阵
    
    Args:
        distance_matrix: Original distance matrix
        scale_factor: Scaling factor (e.g., 100 for 2 decimal precision)
    
    Returns:
        Scaled integer distance matrix
    """
    return (distance_matrix * scale_factor).astype(int)


def extract_locations_from_vrp_input(vrp_input: dict) -> List[Tuple[float, float]]:
    """
    Extract location coordinates from VRP input
    从VRP输入数据中提取位置坐标
    
    Args:
        vrp_input: VRP input dictionary
    
    Returns:
        List of (lat, lon) tuples, depot first
    """
    locations = []
    
    # Add depot
    depot = vrp_input['depot']
    locations.append((depot['lat'], depot['lon']))
    
    # Add stores
    for store in vrp_input['stores']:
        if 'lat' in store and 'lon' in store:
            locations.append((store['lat'], store['lon']))
        else:
            # Generate random location if not provided (for testing)
            locations.append((depot['lat'] + np.random.uniform(-0.1, 0.1),
                            depot['lon'] + np.random.uniform(-0.1, 0.1)))
    
    return locations


def compute_matrices_from_vrp_input(
    vrp_input: dict,
    use_euclidean: bool = True,
    average_speed: float = 40.0
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Compute distance and time matrices from VRP input
    从VRP输入计算距离和时间矩阵
    
    Args:
        vrp_input: VRP input dictionary
        use_euclidean: Use Euclidean distance if True
        average_speed: Average speed in km/h
    
    Returns:
        (distance_matrix, time_matrix)
    """
    # Extract locations
    locations = extract_locations_from_vrp_input(vrp_input)
    
    # Create distance matrix
    distance_matrix = create_distance_matrix(locations, use_euclidean)
    
    # Create time matrix
    time_matrix = create_time_matrix(distance_matrix, average_speed)
    
    return distance_matrix, time_matrix
