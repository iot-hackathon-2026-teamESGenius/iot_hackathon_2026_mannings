#!/usr/bin/env python
"""
验证实验脚本是否能成功运行（快速测试）
"""

import sys
import os

os.chdir(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, 'src')
sys.path.insert(0, 'demo')

print("[INFO] Checking environment and running quick validation...")

try:
    # Check imports
    from data_interface import prepare_vrp_input
    from baselines import run_greedy_baseline
    from solver import solve_vrp
    import config
    import pandas as pd
    print("[OK] All imports successful\n")

    # Create minimal test data
    test_data = {
        'store_id': [1, 2, 3],
        'demand': [15, 20, 10],
        'predicted_demand': [16, 21, 11],
        'demand_p10': [14, 18, 9],
        'demand_p50': [16, 21, 11],
        'demand_p90': [18, 24, 13],
        'time_window_start': [480, 500, 520],
        'time_window_end': [1080, 1080, 1080],
        'lat': [40.75, 40.76, 40.74],
        'lon': [-74.00, -74.01, -73.99],
        'feature_score': [0.5, 0.6, 0.4]
    }

    df = pd.DataFrame(test_data)
    vrp_input = prepare_vrp_input(df, (40.7128, -74.0060), config.VEHICLE_CAPACITY, config.NUM_VEHICLES)
    print(f"[OK] VRP input prepared with {len(vrp_input['stores'])} stores\n")

    # Test each algorithm
    print("="*70)
    print("Testing Three Routing Algorithms")
    print("="*70 + "\n")

    # 1. Greedy Baseline
    print("1. Greedy Baseline:")
    greedy_sol = run_greedy_baseline(vrp_input)
    print(f"   Distance: {greedy_sol['total_distance']/100:.2f} km")
    print(f"   Routes: {len(greedy_sol['routes'])}")
    print(f"   SLA Violations: {len(greedy_sol['dropped_nodes'])}\n")

    # 2. Standard OR-Tools
    print("2. Standard OR-Tools Optimization:")
    std_sol = solve_vrp(vrp_input, use_robust=False, time_limit=5)
    print(f"   Distance: {std_sol['total_distance']/100:.2f} km")
    print(f"   Routes: {len(std_sol['routes'])}")
    print(f"   SLA Violations: {len(std_sol['dropped_nodes'])}")
    print(f"   Time: {std_sol.get('computation_time', 0):.2f} s\n")

    # 3. Robust Optimization with Predictive Features
    print("3. Robust Optimization (with Predictive Features):")
    robust_sol = solve_vrp(vrp_input, use_robust=True, time_limit=5)
    scenarios = robust_sol.get('scenarios', {}).get('scenarios', [])
    print(f"   Scenarios Generated: {len(scenarios)}")
    if scenarios:
        distances = [s['total_distance'] for s in scenarios]
        print(f"   Distances: {[f'{d:.2f}' for d in distances]} km")
        print(f"   Worst-case: {max(distances):.2f} km")
    print(f"   Time: {robust_sol.get('computation_time', 0):.2f} s\n")

    print("="*70)
    print("[OK] All tests passed! Experiment is ready to run.")
    print("="*70)
    print("\nNext: Run 'python run_experiment.py' for full comparison.\n")

except Exception as e:
    print(f"[ERROR] {type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
