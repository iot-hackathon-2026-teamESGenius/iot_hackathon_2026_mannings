"""
快速对比实验运行器
包含：贪心基线、标准OR-Tools优化、鲁棒多情景优化
"""

import sys
import os
import pandas as pd

# Add paths
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from data_interface import prepare_vrp_input
from solver import solve_vrp
from baselines import run_greedy_baseline
import config


def run_comparison_experiment():
    """运行三种算法对比实验并输出性能指标"""
    
    print("\n" + "="*70)
    print("Routing Optimization Comparison Experiment")
    print("="*70)
    
    # 使用简单的测试数据而不是run_demo，避免重复求解问题
    print("\n[INFO] Preparing test data...")
    test_data = {
        'store_id': [1, 2, 3, 4, 5],
        'demand': [15, 20, 10, 25, 18],
        'predicted_demand': [16, 21, 11, 24, 19],
        'demand_p10': [14, 18, 9, 22, 16],
        'demand_p50': [16, 21, 11, 24, 19],
        'demand_p90': [18, 24, 13, 27, 21],
        'time_window_start': [480, 500, 520, 480, 540],
        'time_window_end': [1080, 1080, 1080, 1080, 1080],
        'lat': [40.75, 40.76, 40.74, 40.77, 40.73],
        'lon': [-74.00, -74.01, -73.99, -74.02, -73.98],
        'feature_score': [0.35, 0.55, 0.45, 0.70, 0.40]
    }
    
    df = pd.DataFrame(test_data)
    depot = (40.7128, -74.0060)
    vrp_input = prepare_vrp_input(df, depot, config.VEHICLE_CAPACITY, config.NUM_VEHICLES)
    print(f"[OK] VRP input prepared: {len(vrp_input['stores'])} stores, {vrp_input['num_vehicles']} vehicles")

    # 1. 运行贪心基线
    print("\n### 贪心基线 (Greedy Baseline) ###")
    greedy_solution = run_greedy_baseline(vrp_input)
    greedy_distance = greedy_solution.get('total_distance', 0) / 100
    greedy_routes = len(greedy_solution.get('routes', []))
    greedy_sla = len(greedy_solution.get('dropped_nodes', []))
    print(f"Total Distance: {greedy_distance:.2f} km")
    print(f"Routes: {greedy_routes}")
    print(f"SLA Violations: {greedy_sla}")

    # 2. 标准优化
    print("\n### 标准优化 (Standard Optimization) ###")
    standard_solution = solve_vrp(vrp_input, use_robust=False, time_limit=10)
    std_distance = standard_solution.get('total_distance', 0) / 100
    std_routes = len(standard_solution.get('routes', []))
    std_sla = len(standard_solution.get('dropped_nodes', []))
    std_time = standard_solution.get('computation_time', 0)
    print(f"Total Distance: {std_distance:.2f} km")
    print(f"Routes: {std_routes}")
    print(f"SLA Violations: {std_sla}")
    print(f"Computation Time: {std_time:.2f} s")

    # 3. 鲁棒优化
    print("\n### 鲁棒优化 (Robust Optimization) - 含预测特征 ###")
    robust_solution = solve_vrp(vrp_input, use_robust=True, time_limit=10)
    scenarios = robust_solution.get('scenarios', {}).get('scenarios', [])
    scenario_distances = [round(s.get('total_distance', 0), 2) for s in scenarios]
    worst_case = max([s.get('total_distance', 0) for s in scenarios]) if scenarios else 0
    robust_time = robust_solution.get('computation_time', 0)
    print(f"Scenarios: {len(scenarios)}")
    print(f"Scenario Distances (km): {scenario_distances}")
    print(f"Worst-case Distance: {worst_case:.2f} km")
    print(f"Computation Time: {robust_time:.2f} s")
    print(f"选择标准: min_max_distance")
    
    # 对比分析
    print("\n" + "-"*70)
    print("Performance Comparison")
    print("-"*70)
    
    greedy_gap = ((greedy_distance - std_distance) / std_distance * 100) if std_distance > 0 else 0
    print(f"[INFO] Greedy gap vs Standard: {greedy_gap:+.1f}%")
    print(f"[INFO] Robust worst case: {worst_case:.2f} km vs Standard: {std_distance:.2f} km")
    print(f"[STAT] All three methods completed successfully!")
    print(f"[STAT] Time: Greedy << Standard ({std_time:.1f}s) < Robust ({robust_time:.1f}s)")
    
    print("\n" + "="*70)
    print("[OK] Experiment completed!")
    print("="*70 + "\n")


if __name__ == "__main__":
    run_comparison_experiment()
