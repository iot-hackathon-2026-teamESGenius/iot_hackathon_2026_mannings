"""
Minimal Demo - Run Routing Optimization
最小可运行示例 (Stage 1 关键交付)
"""

import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../src'))

from data_interface import prepare_vrp_input
from solver import solve_vrp, format_solution_output, export_solution_to_dict
import config
import pandas as pd


def run_demo_with_mock_data(return_input: bool = False):
    """
    Run demo with mock data
    使用Mock数据运行演示
    """
    print("\n" + "=" * 60)
    print("ROUTING OPTIMIZATION DEMO - Stage 1")
    print("=" * 60)
    
    # Step 1: Create mock forecast data
    print("\nStep 1: Loading Mock Data...")
    
    mock_data = {
        'store_id': [1, 2, 3, 4, 5, 6, 7],
        'demand': [15, 20, 10, 25, 18, 12, 22],
        'predicted_demand': [16, 21, 11, 24, 19, 13, 23],
        'demand_p10': [14, 18, 9, 22, 16, 11, 20],
        'demand_p50': [16, 21, 11, 24, 19, 13, 23],
        'demand_p90': [18, 24, 13, 27, 21, 15, 25],
        'time_window_start': [480, 500, 520, 480, 540, 500, 520],  # 8:00-9:00 AM
        'time_window_end': [1080, 1080, 1080, 1080, 1080, 1080, 1080],  # 6:00 PM
        'lat': [40.75, 40.76, 40.74, 40.77, 40.73, 40.72, 40.78],
        'lon': [-74.00, -74.01, -73.99, -74.02, -73.98, -74.01, -73.97],
        'feature_score': [0.35, 0.55, 0.45, 0.70, 0.40, 0.60, 0.50]  # 学习增强特征（0-1）
    }
    
    df = pd.DataFrame(mock_data)
    print(f"[OK] Loaded {len(df)} stores")
    print(f"  Total demand: {df['demand'].sum()} units")
    print(f"  Includes: predicted_demand, quantile forecasts (p10/p50/p90), feature_score")
    
    # Step 2: Prepare VRP input
    print("\nStep 2: Preparing VRP Input...")
    
    depot_location = (40.7128, -74.0060)  # NYC coordinates
    vehicle_capacity = config.VEHICLE_CAPACITY
    num_vehicles = config.NUM_VEHICLES
    
    # 准备VRP输入（自动使用预测需求和保留预测列）
    vrp_input = prepare_vrp_input(df, depot_location, vehicle_capacity, num_vehicles)
    print(f"[OK] Depot: {depot_location}")
    print(f"[OK] Vehicles: {num_vehicles} x {vehicle_capacity} capacity")
    
    # Step 3: Run Standard Optimization
    print("\n" + "=" * 60)
    print("STANDARD OPTIMIZATION")
    print("=" * 60)
    
    standard_solution = solve_vrp(vrp_input, use_robust=False, time_limit=10)
    print(format_solution_output(standard_solution, vrp_input))
    
    # Step 4: Run Robust Optimization
    print("\n" + "=" * 60)
    print("ROBUST OPTIMIZATION (Innovation)")
    print("=" * 60)
    
    robust_solution = solve_vrp(vrp_input, use_robust=True, time_limit=10)
    print(format_solution_output(robust_solution, vrp_input))
    
    # Step 5: Export solution
    print("\nStep 5: Exporting Solution for Team Integration...")
    export_data = export_solution_to_dict(robust_solution)
    print("✓ Solution exported in standardized format")
    print(f"  Format: {config.OUTPUT_FORMAT}")
    
    if return_input:
        return vrp_input, standard_solution, robust_solution
    return standard_solution, robust_solution


def run_simple_demo():
    """
    Simplified demo for quick testing
    简化版演示用于快速测试
    """
    print("\n" + "=" * 60)
    print("SIMPLE ROUTING DEMO")
    print("=" * 60)
    
    # Create minimal problem
    vrp_input = {
        'depot': {'lat': 40.7128, 'lon': -74.0060},
        'stores': [
            {'id': 1, 'demand': 20, 'time_window': (480, 1080), 'lat': 40.75, 'lon': -74.00},
            {'id': 2, 'demand': 15, 'time_window': (500, 1080), 'lat': 40.76, 'lon': -74.01},
            {'id': 3, 'demand': 25, 'time_window': (480, 1080), 'lat': 40.74, 'lon': -73.99},
        ],
        'vehicles': [
            {'id': 0, 'capacity': 100},
            {'id': 1, 'capacity': 100}
        ],
        'num_vehicles': 2,
        'vehicle_capacity': 100
    }
    
    print(f"\nProblem Size:")
    print(f"  Stores: {len(vrp_input['stores'])}")
    print(f"  Vehicles: {vrp_input['num_vehicles']}")
    
    # Solve
    solution = solve_vrp(vrp_input, use_robust=False, time_limit=5)
    
    # Display results
    if solution.get('status') == 'Success':
        print(f"\n[OK] Solution Found!")
        print(f"  Total Distance: {solution['total_distance'] / 100:.2f} km")
        print(f"  Routes: {len(solution['routes'])}")
        
        for route in solution['routes']:
            sequence = [f"Store {n}" if n != 0 else "Depot" for n in route['sequence']]
            print(f"\n  Vehicle {route['vehicle_id']}: {' → '.join(sequence)}")
            print(f"    Distance: {route['distance'] / 100:.2f} km")
            print(f"    Load: {route['load']:.0f}/{vrp_input['vehicle_capacity']}")
    else:
        print(f"\n✗ {solution.get('message', 'No solution found')}")


if __name__ == "__main__":
    # Check if ortools is installed
    try:
        import ortools
        print("[OK] OR-Tools is installed")
    except ImportError:
        print("✗ OR-Tools not installed. Please run: pip install ortools")
        sys.exit(1)
    
    # Run demo
    print("\nChoose demo mode:")
    print("  1. Simple Demo (3 stores)")
    print("  2. Full Demo with Robust Optimization (7 stores)")
    
    choice = input("\nEnter choice (1 or 2): ").strip()
    
    if choice == "1":
        run_simple_demo()
    elif choice == "2":
        run_demo_with_mock_data()
    else:
        print("Invalid choice. Running simple demo...")
        run_simple_demo()
