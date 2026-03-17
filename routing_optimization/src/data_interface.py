"""
Data interface for loading forecast data
输入数据接口 - 对接预测模块输出
"""

import pandas as pd
import re
import zipfile
from typing import Dict, List, Tuple
import config


def load_forecast_data(file_path: str = None) -> pd.DataFrame:
    """
    Load forecast data from prediction module
    从预测模块加载数据
    
    Required columns:
        - store_id: Store identifier
        - demand: Delivery demand (or predicted_demand if provided)
        - time_window_start: Earliest delivery time (minutes from depot open)
        - time_window_end: Latest delivery time (minutes from depot open)

    Optional predictive columns (used when present):
        - predicted_demand: Point forecast for demand
        - demand_p10 / demand_p50 / demand_p90: Quantile forecasts
        - feature_score: Learning-enhanced feature (0-1 range)
    
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
            'lon',
            config.PREDICTED_DEMAND_COL,
            config.DEMAND_QUANTILE_COLS['low'],
            config.DEMAND_QUANTILE_COLS['mid'],
            config.DEMAND_QUANTILE_COLS['high'],
            config.LEARNING_FEATURE_COL
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
        base_demand = float(row.get(config.PREDICTED_DEMAND_COL, row['demand']))

        store = {
            'id': int(row['store_id']),
            'demand': base_demand,
            'time_window': (
                int(row['time_window_start']),
                int(row['time_window_end'])
            )
        }
        
        # Add coordinates if available
        if 'lat' in df.columns and 'lon' in df.columns:
            store['lat'] = float(row['lat'])
            store['lon'] = float(row['lon'])

        # Optional predictive fields
        quantiles = config.DEMAND_QUANTILE_COLS
        if quantiles['low'] in df.columns and not pd.isnull(row.get(quantiles['low'], None)):
            store[quantiles['low']] = float(row[quantiles['low']])
        if quantiles['mid'] in df.columns and not pd.isnull(row.get(quantiles['mid'], None)):
            store[quantiles['mid']] = float(row[quantiles['mid']])
        if quantiles['high'] in df.columns and not pd.isnull(row.get(quantiles['high'], None)):
            store[quantiles['high']] = float(row[quantiles['high']])

        if config.LEARNING_FEATURE_COL in df.columns and not pd.isnull(row.get(config.LEARNING_FEATURE_COL, None)):
            store[config.LEARNING_FEATURE_COL] = float(row[config.LEARNING_FEATURE_COL])

        if config.PREDICTED_DEMAND_COL in df.columns and not pd.isnull(row.get(config.PREDICTED_DEMAND_COL, None)):
            store[config.PREDICTED_DEMAND_COL] = float(row[config.PREDICTED_DEMAND_COL])
        
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


def _normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    renamed = {}
    for col in df.columns:
        new_col = re.sub(r"\s+", " ", str(col)).strip().lower()
        renamed[col] = new_col
    return df.rename(columns=renamed)


def _parse_time_window_from_store_row(row: pd.Series, default_window: Tuple[int, int]) -> Tuple[int, int]:
    # dim_store uses columns like "Business Hrs 1" and "Business Hrs 1.1"
    candidate_cols = [
        'business hrs 1.1',
        'business hrs 2.1',
        'business hrs 3.1',
    ]
    for c in candidate_cols:
        val = str(row.get(c, '')).strip()
        m = re.match(r'^(\d{1,2}):(\d{2})-(\d{1,2}):(\d{2})$', val)
        if not m:
            continue
        h1, mm1, h2, mm2 = map(int, m.groups())
        return h1 * 60 + mm1, h2 * 60 + mm2
    return default_window


def _stable_store_coords(store_code: int) -> Tuple[float, float]:
    # Deterministic pseudo coordinates around Hong Kong center for routing distance consistency.
    center_lat, center_lon = 22.3193, 114.1694
    seed = int(store_code) * 2654435761 % (2**32)
    lat_off = (((seed >> 8) % 10000) / 10000.0 - 0.5) * 0.25
    lon_off = (((seed >> 20) % 10000) / 10000.0 - 0.5) * 0.30
    return center_lat + lat_off, center_lon + lon_off


def load_dfi_zip_as_forecast_data(
    zip_path: str,
    target_date: str = None,
    top_n_stores: int = 25,
    demand_col: str = 'total_quantity_cnt',
    default_time_window: Tuple[int, int] = (8 * 60, 21 * 60),
) -> pd.DataFrame:
    """
    Convert DFI zip dataset to forecast dataframe compatible with VRP pipeline.

    Args:
        zip_path: Path to DFI.zip
        target_date: Date string (YYYY-MM-DD). If None, use latest date in orders.
        top_n_stores: Keep top N stores by aggregated demand.
        demand_col: Demand aggregation column in order detail table.
        default_time_window: Fallback time window if store business hours unavailable.

    Returns:
        DataFrame ready for prepare_vrp_input.
    """
    with zipfile.ZipFile(zip_path) as zf:
        order_file = [n for n in zf.namelist() if 'case_study_order_detail' in n][0]
        store_file = [n for n in zf.namelist() if 'dim_store' in n][0]

        with zf.open(order_file) as f:
            orders = pd.read_csv(f)
        with zf.open(store_file) as f:
            stores = pd.read_csv(f)

    orders = _normalize_columns(orders)
    stores = _normalize_columns(stores)

    if 'dt' not in orders.columns or 'fulfillment_store_code' not in orders.columns:
        raise ValueError('DFI order detail file missing required columns: dt, fulfillment_store_code')
    if demand_col not in orders.columns:
        raise ValueError(f"DFI order detail file missing demand column: {demand_col}")

    orders['dt'] = pd.to_datetime(orders['dt'], errors='coerce')
    orders = orders.dropna(subset=['dt'])

    if target_date is None:
        target_ts = orders['dt'].max().normalize()
    else:
        target_ts = pd.to_datetime(target_date).normalize()

    day_orders = orders[orders['dt'].dt.normalize() == target_ts].copy()
    if day_orders.empty:
        raise ValueError(f'No records found in DFI data for date: {target_ts.date()}')

    agg = (
        day_orders
        .groupby('fulfillment_store_code', as_index=False)[demand_col]
        .sum()
        .rename(columns={'fulfillment_store_code': 'store_id', demand_col: 'demand'})
    )
    agg = agg.sort_values('demand', ascending=False).head(top_n_stores)

    store_code_col = 'store code' if 'store code' in stores.columns else None
    if store_code_col is None:
        # Keep compatibility with unusual newline-based source names
        for col in stores.columns:
            if col.replace(' ', '') == 'storecode':
                store_code_col = col
                break

    if store_code_col:
        stores = stores.rename(columns={store_code_col: 'store_id'})
        merged = agg.merge(stores, on='store_id', how='left')
    else:
        merged = agg.copy()

    rows = []
    for _, row in merged.iterrows():
        store_id = int(row['store_id'])
        demand = float(max(row['demand'], 0.0))
        tw_start, tw_end = _parse_time_window_from_store_row(row, default_time_window)
        lat, lon = _stable_store_coords(store_id)
        rows.append({
            'store_id': store_id,
            'demand': demand,
            'predicted_demand': demand,
            'demand_p10': demand * 0.9,
            'demand_p50': demand,
            'demand_p90': demand * 1.1,
            'time_window_start': tw_start,
            'time_window_end': tw_end,
            'lat': lat,
            'lon': lon,
        })

    df = pd.DataFrame(rows)
    if df.empty:
        raise ValueError('No valid store-level demand rows generated from DFI data')

    # feature_score normalized by demand percentile for scenario learning factor.
    if len(df) == 1:
        df['feature_score'] = 0.5
    else:
        ranks = df['demand'].rank(method='average', pct=True)
        df['feature_score'] = ranks.clip(0.0, 1.0)

    return df
