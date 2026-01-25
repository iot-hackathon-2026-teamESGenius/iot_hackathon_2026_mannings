"""
Quick comparison experiment runner
快速对比实验运行器
"""

import sys
import os

# Add paths
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'demo'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from demo.run_demo import run_demo_with_mock_data

def run_comparison_experiment():
    """Run and format comparison experiment results"""
    
    print("\n" + "="*70)
    print("🔬 路径优化对比实验 - ROUTING OPTIMIZATION COMPARISON")
    print("="*70)
    
    # Run demo
    print("\n⏳ Running experiments...")
    standard_solution, robust_solution = run_demo_with_mock_data()
    
    # Format results
    print("\n" + "="*70)
    print("📊 实验结果对比 - EXPERIMENT RESULTS")
    print("="*70)
    
    # Standard optimization results
    print("\n### 标准优化 (Standard Optimization) ###")
    std_distance = standard_solution.get('total_distance', 0) / 100
    std_routes = len(standard_solution.get('routes', []))
    std_sla = len(standard_solution.get('dropped_nodes', []))
    std_time = standard_solution.get('computation_time', 0)
    
    print(f"Total Distance: {std_distance:.2f} km")
    print(f"Routes: {std_routes}")
    print(f"SLA Violations: {std_sla}")
    print(f"Computation Time: {std_time:.2f} s")
    
    # Robust optimization results
    print("\n### 鲁棒优化 (Robust Optimization) - 需求波动 ±10% ###")
    scenarios = robust_solution.get('scenarios', {}).get('scenarios', [])
    scenario_distances = [s['total_distance'] for s in scenarios]
    worst_case = max(scenario_distances) if scenario_distances else 0
    total_sla = sum(s.get('sla_violations', 0) for s in scenarios)
    robust_time = robust_solution.get('computation_time', 0)
    
    print(f"Scenario Distances: {scenario_distances} km")
    print(f"Worst-case Distance: {worst_case:.2f} km")
    print(f"SLA Violations: {total_sla}")
    print(f"Computation Time: {robust_time:.2f} s")
    print(f"选择标准: min_max_distance (默认)")
    
    # Comparison summary
    print("\n" + "-"*70)
    print("💡 对比分析 (Comparison Analysis)")
    print("-"*70)
    
    improvement = ((std_distance - worst_case) / std_distance * 100) if std_distance > 0 else 0
    
    if worst_case < std_distance:
        print(f"✅ 鲁棒优化在最坏情况下比标准优化改进了 {-improvement:.1f}%")
    elif worst_case > std_distance:
        print(f"⚠️  鲁棒优化最坏距离比标准优化增加了 {improvement:.1f}%")
        print(f"    但鲁棒方案可应对需求波动，降低SLA风险")
    else:
        print(f"➡️  两种方案距离相同")
    
    print(f"\n📈 场景稳定性: 标准差 = {robust_solution.get('scenarios', {}).get('summary', {}).get('std_distance', 0):.2f} km")
    print(f"🚗 车辆使用: 标准优化 {std_routes} 辆, 鲁棒优化 {len(robust_solution.get('routes', []))} 辆")
    
    print("\n" + "="*70)
    print("✅ 实验完成!")
    print("="*70 + "\n")

if __name__ == "__main__":
    run_comparison_experiment()
