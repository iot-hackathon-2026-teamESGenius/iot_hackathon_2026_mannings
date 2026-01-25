"""
Scenario-based robust optimizer with predictive features.
"""

import copy
from typing import Dict, List, Optional
import numpy as np
from distance_matrix import compute_matrices_from_vrp_input
from modules.routing.implementations.ortools_optimizer import VRPModel


class RobustOptimizer:
    """Solve multiple demand scenarios and pick a robust plan."""

    def __init__(
        self,
        base_vrp_input: Dict,
        demand_ratios: Optional[List[float]] = None,
        scenario_generator: Optional[object] = None,
    ) -> None:
        self.base_vrp_input = base_vrp_input
        self.demand_ratios = demand_ratios or [0.9, 1.0, 1.1]
        self.scenario_generator = scenario_generator
        self.scenarios: List[Dict] = []
        self.scenario_solutions: List[Dict] = []

    def generate_scenarios(self) -> List[Dict]:
        """Generate demand scenarios using generator or ratio fallback."""
        self.scenarios = []
        if self.scenario_generator:
            self.scenarios = self.scenario_generator.generate(self.base_vrp_input, self.demand_ratios)
            return self.scenarios

        for ratio in self.demand_ratios:
            scenario_input = copy.deepcopy(self.base_vrp_input)
            for store in scenario_input['stores']:
                store['demand'] = store['demand'] * ratio
            scenario_input['scenario_name'] = f"ratio_{ratio:.2f}"
            scenario_input['scenario_ratio'] = ratio
            self.scenarios.append(scenario_input)
        return self.scenarios

    def solve_all_scenarios(
        self,
        use_euclidean: bool = True,
        average_speed: float = 40.0,
        time_limit: int = 30,
    ) -> List[Dict]:
        print(f"\n{'='*60}")
        print(f"Robust Optimization: Solving {len(self.scenarios)} scenarios")
        print(f"{'='*60}\n")

        self.scenario_solutions = []
        for idx, scenario_input in enumerate(self.scenarios):
            ratio = scenario_input.get('scenario_ratio', None)
            scenario_name = scenario_input.get('scenario_name', f"scenario_{idx+1}")
            ratio_display = f" = {ratio:.1%}" if ratio is not None else ""
            print(f"Scenario {idx + 1} ({scenario_name}){ratio_display}")

            distance_matrix, time_matrix = compute_matrices_from_vrp_input(
                scenario_input,
                use_euclidean,
                average_speed,
            )
            distance_matrix_scaled = (distance_matrix * 100).astype(int)

            vrp_model = VRPModel(scenario_input, distance_matrix_scaled, time_matrix)
            vrp_model.create_model()
            solution = vrp_model.solve(time_limit)

            if solution:
                details = vrp_model.get_solution_details()
                details['scenario_id'] = idx
                details['demand_ratio'] = ratio
                details['scenario_name'] = scenario_name
                details['distance_matrix'] = distance_matrix
                self.scenario_solutions.append(details)

                print(f"  [OK] Total Distance: {details['total_distance'] / 100:.2f} km")
                print(f"  [OK] Routes: {len(details['routes'])}")
                if details['dropped_nodes']:
                    print(f"  [WARN] SLA Violations: {len(details['dropped_nodes'])} nodes")
            else:
                print("  [FAIL] No solution found")

        print(f"\n{'='*60}\n")
        return self.scenario_solutions

    def select_robust_solution(self, criterion: str = 'min_max_distance') -> Dict:
        if not self.scenario_solutions:
            return {'status': 'No solutions available'}

        print(f"Selection Criterion: {criterion}\n")

        if criterion == 'min_max_distance':
            max_distances = []
            for sol in self.scenario_solutions:
                route_max = max(route['distance'] for route in sol['routes']) if sol['routes'] else 0
                max_distances.append(route_max)
            best_idx = int(np.argmin(max_distances))
            robust_solution = self.scenario_solutions[best_idx]
            print(f"Selected: Scenario {best_idx + 1}")
            print(f"Worst-case route distance: {max_distances[best_idx] / 100:.2f} km")

        elif criterion == 'min_avg_distance':
            avg_distances = [sol['total_distance'] for sol in self.scenario_solutions]
            best_idx = int(np.argmin(avg_distances))
            robust_solution = self.scenario_solutions[best_idx]
            print(f"Selected: Scenario {best_idx + 1}")
            print(f"Average total distance: {avg_distances[best_idx] / 100:.2f} km")

        elif criterion == 'min_sla_violation':
            violation_counts = [len(sol.get('dropped_nodes', [])) for sol in self.scenario_solutions]
            best_idx = int(np.argmin(violation_counts))
            robust_solution = self.scenario_solutions[best_idx]
            print(f"Selected: Scenario {best_idx + 1}")
            print(f"SLA violations: {violation_counts[best_idx]}")

        else:
            robust_solution = self.scenario_solutions[len(self.demand_ratios) // 2]
            print("Using nominal scenario (default)")

        return robust_solution

    def get_scenario_comparison(self) -> Dict:
        comparison = {'scenarios': [], 'summary': {}}
        for sol in self.scenario_solutions:
            comparison['scenarios'].append({
                'scenario_id': sol['scenario_id'],
                'scenario_name': sol.get('scenario_name', f"scenario_{sol['scenario_id']}"),
                'demand_ratio': sol['demand_ratio'],
                'total_distance': sol['total_distance'] / 100,
                'num_routes': len(sol['routes']),
                'sla_violations': len(sol.get('dropped_nodes', [])),
            })

        if comparison['scenarios']:
            distances = [s['total_distance'] for s in comparison['scenarios']]
            comparison['summary'] = {
                'min_distance': min(distances),
                'max_distance': max(distances),
                'avg_distance': float(np.mean(distances)),
                'std_distance': float(np.std(distances)),
            }
        return comparison
