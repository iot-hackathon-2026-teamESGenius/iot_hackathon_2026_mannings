"""
Robust Optimizer - Scenario-based Robust Optimization (创新点)
多情景鲁棒优化 - 核心创新模块
"""

import numpy as np
from typing import Dict, List
from vrp_model import VRPModel
from distance_matrix import compute_matrices_from_vrp_input
import copy


class RobustOptimizer:
    """
    Scenario-based Robust Optimization
    基于场景的鲁棒优化器 - 对需求不确定性进行建模
    """
    
    def __init__(self, base_vrp_input: Dict, demand_ratios: List[float] = None):
        """
        Initialize Robust Optimizer
        
        Args:
            base_vrp_input: Base VRP input with nominal demands
            demand_ratios: List of demand multipliers for scenarios
                          e.g., [0.9, 1.0, 1.1] for -10%, nominal, +10%
        """
        self.base_vrp_input = base_vrp_input
        self.demand_ratios = demand_ratios or [0.9, 1.0, 1.1]
        self.scenarios = []
        self.scenario_solutions = []
    
    def generate_scenarios(self) -> List[Dict]:
        """
        Generate demand scenarios based on demand ratios
        生成多个需求场景―核心创新点
        
        Process:
            1. 对每个需求比例（如0.9》1.0、1.1）
            2. 创建深拷贝的根据VRP数据
            3. 应用该比例调整所有客户的需求
        
        Returns:
            List of VRP input dictionaries with adjusted demands
        """
        self.scenarios = []
        
        # 为每一个需求比例创建场景
        for ratio in self.demand_ratios:
            # 深拷贝：不修改原始数据
            scenario_input = copy.deepcopy(self.base_vrp_input)
            
            # 应用需求比例
            for store in scenario_input['stores']:
                store['demand'] = store['demand'] * ratio
            
            self.scenarios.append(scenario_input)
        
        return self.scenarios
    
    def solve_all_scenarios(
        self,
        use_euclidean: bool = True,
        average_speed: float = 40.0,
        time_limit: int = 30
    ) -> List[Dict]:
        """
        Solve VRP for all scenarios
        对所有场景求解VRP
        
        Args:
            use_euclidean: Use Euclidean distance
            average_speed: Average vehicle speed
            time_limit: Time limit per scenario
        
        Returns:
            List of solution dictionaries
        """
        print(f"\n{'='*60}")
        print(f"Robust Optimization: Solving {len(self.scenarios)} scenarios")
        print(f"{'='*60}\n")
        
        self.scenario_solutions = []
        
        for idx, scenario_input in enumerate(self.scenarios):
            ratio = self.demand_ratios[idx]
            print(f"Scenario {idx + 1}: Demand ratio = {ratio:.1%}")
            
            # Compute distance and time matrices
            distance_matrix, time_matrix = compute_matrices_from_vrp_input(
                scenario_input,
                use_euclidean,
                average_speed
            )
            
            # Scale distance matrix for OR-Tools
            distance_matrix_scaled = (distance_matrix * 100).astype(int)
            
            # Create and solve VRP model
            vrp_model = VRPModel(scenario_input, distance_matrix_scaled, time_matrix)
            vrp_model.create_model()
            solution = vrp_model.solve(time_limit)
            
            if solution:
                solution_details = vrp_model.get_solution_details()
                solution_details['scenario_id'] = idx
                solution_details['demand_ratio'] = ratio
                solution_details['distance_matrix'] = distance_matrix
                self.scenario_solutions.append(solution_details)
                
                print(f"  ✓ Total Distance: {solution_details['total_distance'] / 100:.2f} km")
                print(f"  ✓ Routes: {len(solution_details['routes'])}")
                if solution_details['dropped_nodes']:
                    print(f"  ⚠ SLA Violations: {len(solution_details['dropped_nodes'])} nodes")
            else:
                print(f"  ✗ No solution found")
        
        print(f"\n{'='*60}\n")
        return self.scenario_solutions
    
    def select_robust_solution(self, criterion: str = 'min_max_distance') -> Dict:
        """
        Select most robust solution across all scenarios
        从多个场景中选择最鲁棒的方案―核心创新点
        
        Robustness Criterion:
            - 'min_max_distance': 最小化最嬲情冶内距离
              (会选择突提事项中提性底气的方案)
            - 'min_avg_distance': 最小化平均距离
              (会选择整体上最优的方案)
            - 'min_sla_violation': 最小化SLA违反数
              (会优先保证服务水平)
        
        Returns:
            Selected robust solution dictionary
        """
        if not self.scenario_solutions:
            return {'status': 'No solutions available'}
        
        print(f"Selection Criterion: {criterion}\n")
        
        if criterion == 'min_max_distance':
            # 选择最嬲情冶距离最短的方案
            # 这确保即使需求波动，也不会出现急剧払的情形
            max_distances = []
            for sol in self.scenario_solutions:
                max_dist = max(route['distance'] for route in sol['routes']) if sol['routes'] else 0
                max_distances.append(max_dist)
            
            best_idx = np.argmin(max_distances)
            robust_solution = self.scenario_solutions[best_idx]
            
            print(f"Selected: Scenario {best_idx + 1}")
            print(f"Worst-case route distance: {max_distances[best_idx] / 100:.2f} km")
        
        elif criterion == 'min_avg_distance':
            # 选择整体成本最优的方案
            avg_distances = [sol['total_distance'] for sol in self.scenario_solutions]
            best_idx = np.argmin(avg_distances)
            robust_solution = self.scenario_solutions[best_idx]
            
            print(f"Selected: Scenario {best_idx + 1}")
            print(f"Average total distance: {avg_distances[best_idx] / 100:.2f} km")
        
        elif criterion == 'min_sla_violation':
            # 选择最不容易失信的方案(最剠时候)
            violation_counts = [
                len(sol.get('dropped_nodes', [])) 
                for sol in self.scenario_solutions
            ]
            best_idx = np.argmin(violation_counts)
            robust_solution = self.scenario_solutions[best_idx]
            
            print(f"Selected: Scenario {best_idx + 1}")
            print(f"SLA violations: {violation_counts[best_idx]}")
        
        else:
            # 默认：使用标准场景
            robust_solution = self.scenario_solutions[len(self.demand_ratios) // 2]
            print(f"Using nominal scenario (default)")
        
        return robust_solution
    
    def get_scenario_comparison(self) -> Dict:
        """
        Get comparison metrics across all scenarios
        获取所有场景的对比指标
        
        Returns:
            Comparison dictionary
        """
        comparison = {
            'scenarios': [],
            'summary': {}
        }
        
        for sol in self.scenario_solutions:
            scenario_metrics = {
                'scenario_id': sol['scenario_id'],
                'demand_ratio': sol['demand_ratio'],
                'total_distance': sol['total_distance'] / 100,
                'num_routes': len(sol['routes']),
                'sla_violations': len(sol.get('dropped_nodes', []))
            }
            comparison['scenarios'].append(scenario_metrics)
        
        # Summary statistics
        distances = [s['total_distance'] for s in comparison['scenarios']]
        comparison['summary'] = {
            'min_distance': min(distances),
            'max_distance': max(distances),
            'avg_distance': np.mean(distances),
            'std_distance': np.std(distances)
        }
        
        return comparison
