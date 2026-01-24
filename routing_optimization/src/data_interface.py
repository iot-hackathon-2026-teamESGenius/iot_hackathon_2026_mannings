"""
Data interface for loading forecast data
输入数据接口 - 对接预测模块输出
"""

import pandas as pd
from typing import Dict, List, Tuple


def load_forecast_data(file_path: str = None) -> pd.DataFrame:
    """
    Load forecast data from prediction module
    从预测模块加载数据
    
    Required columns:
        - store_id: Store identifier
        - demand: Delivery demand
        - time_window_start: Earliest delivery time (minutes from depot open)
        - time_window_end: Latest delivery time (minutes from depot open)
    
    Args:
        file_path: Path to forecast data file (CSV or Excel)
    
    Returns:
        DataFrame with standardized columns
    """
    if file_path is None:
        # Return empty template
        return pd.DataFrame(columns=[
            'store_id',
            'demand',
            'time_window_start',
            'time_window_end',
            'lat',
            'lon'
        ])
    
    # Load data
    if file_path.endswith('.csv'):
        df = pd.read_csv(file_path)
    elif file_path.endswith(('.xls', '.xlsx')):
        df = pd.read_excel(file_path)
    else:
        raise ValueError(f"Unsupported file format: {file_path}")
    
    # Validate required columns
    required_cols = ['store_id', 'demand', 'time_window_start', 'time_window_end']
    missing_cols = [col for col in required_cols if col not in df.columns]
    
    if missing_cols:
        raise ValueError(f"Missing required columns: {missing_cols}")
    
    # Validate data types and ranges
    if df['demand'].isnull().any() or (df['demand'] < 0).any():
        raise ValueError("Demand values must be non-negative and non-null")
    
    if df['time_window_start'].isnull().any() or df['time_window_end'].isnull().any():
        raise ValueError("Time window values cannot be null")
    
    if (df['time_window_start'] > df['time_window_end']).any():
        raise ValueError("time_window_start must be <= time_window_end")
    
    return df


def prepare_vrp_input(
    df: pd.DataFrame,
    depot_location: Tuple[float, float],
    vehicle_capacity: float,
    num_vehicles: int
) -> Dict:
    """
    Prepare input data for VRP solver
    准备VRP求解器的输入数据
    
    Args:
        df: Forecast data DataFrame
        depot_location: (lat, lon) of depot
        vehicle_capacity: Capacity of each vehicle
        num_vehicles: Number of available vehicles
    
    Returns:
        Dictionary with VRP input format
    """
    vrp_input = {
        'depot': {
            'lat': depot_location[0],
            'lon': depot_location[1]
        },
        'stores': [],
        'vehicles': [],
        'num_vehicles': num_vehicles,
        'vehicle_capacity': vehicle_capacity
    }
    
    # Add stores
    for idx, row in df.iterrows():
        store = {
            'id': int(row['store_id']),
            'demand': float(row['demand']),
            'time_window': (
                int(row['time_window_start']),
                int(row['time_window_end'])
            )
        }
        
        # Add coordinates if available
        if 'lat' in df.columns and 'lon' in df.columns:
            store['lat'] = float(row['lat'])
            store['lon'] = float(row['lon'])
        
        vrp_input['stores'].append(store)
    
    # Add vehicles
    for i in range(num_vehicles):
        vrp_input['vehicles'].append({
            'id': i,
            'capacity': vehicle_capacity
        })
    
    return vrp_input


def validate_input_data(vrp_input: Dict) -> Tuple[bool, str]:
    """
    Validate VRP input data
    验证输入数据的完整性和合理性
    
    Args:
        vrp_input: VRP input dictionary
    
    Returns:
        (is_valid, error_message)
    """
    # Check depot
    if 'depot' not in vrp_input:
        return False, "Missing depot information"
    
    # Check stores
    if 'stores' not in vrp_input or len(vrp_input['stores']) == 0:
        return False, "No stores provided"
    
    # Check vehicles
    if 'num_vehicles' not in vrp_input or vrp_input['num_vehicles'] <= 0:
        return False, "Invalid number of vehicles"
    
    # Check capacity feasibility
    total_demand = sum(store['demand'] for store in vrp_input['stores'])
    total_capacity = vrp_input['vehicle_capacity'] * vrp_input['num_vehicles']
    
    if total_demand > total_capacity:
        return False, f"Total demand ({total_demand}) exceeds total capacity ({total_capacity})"
    
    return True, "Input data is valid"
