"""
Run routing optimization on real DFI.zip data.
先跑最小样例，再跑真实DFI数据（门店TopN聚合）。
"""

import math
import os
import sys

import pandas as pd

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, 'src'))

from src import config
from src.data_interface import load_dfi_zip_as_forecast_data, prepare_vrp_input
from src.solver import solve_vrp, format_solution_output


def run_minimal_smoke_test() -> None:
    print("\n[STEP 1] Minimal sample smoke test")
    sample = pd.DataFrame(
        {
            'store_id': [1, 2, 3],
            'demand': [12, 18, 15],
            'predicted_demand': [13, 19, 16],
            'demand_p10': [10, 16, 13],
            'demand_p50': [13, 19, 16],
            'demand_p90': [15, 22, 18],
            'time_window_start': [8 * 60, 8 * 60 + 30, 9 * 60],
            'time_window_end': [19 * 60, 20 * 60, 20 * 60],
            'lat': [22.3190, 22.3250, 22.3110],
            'lon': [114.1690, 114.1810, 114.1600],
            'feature_score': [0.4, 0.7, 0.5],
        }
    )
    vrp_input = prepare_vrp_input(sample, (22.3700, 114.1130), vehicle_capacity=60, num_vehicles=3)
    solution = solve_vrp(vrp_input, use_robust=True, time_limit=5)
    print(format_solution_output(solution))


def run_dfi_real_data(top_n_stores: int = 20, target_date: str = None) -> None:
    print("\n[STEP 2] Real DFI dataset test")
    zip_path = os.path.join(os.path.dirname(ROOT), 'DFI.zip')
    if not os.path.exists(zip_path):
        raise FileNotFoundError(f"DFI.zip not found: {zip_path}")

    df = load_dfi_zip_as_forecast_data(
        zip_path=zip_path,
        target_date=target_date,
        top_n_stores=top_n_stores,
    )

    total_demand = float(df['demand'].sum())
    num_vehicles = max(5, min(20, int(math.ceil(top_n_stores / 2))))
    vehicle_capacity = int(math.ceil(total_demand / max(num_vehicles * 0.9, 1.0)))

    print(f"[INFO] Target date: {target_date or 'latest in DFI'}")
    print(f"[INFO] Stores: {len(df)}, total demand: {total_demand:.1f}")
    print(f"[INFO] Vehicles: {num_vehicles}, capacity each: {vehicle_capacity}")

    vrp_input = prepare_vrp_input(
        df,
        depot_location=(22.3700, 114.1130),
        vehicle_capacity=vehicle_capacity,
        num_vehicles=num_vehicles,
    )
    solution = solve_vrp(vrp_input, use_robust=True, time_limit=min(config.MAX_SEARCH_TIME, 15))
    print(format_solution_output(solution))


if __name__ == '__main__':
    run_minimal_smoke_test()
    run_dfi_real_data(top_n_stores=20)
