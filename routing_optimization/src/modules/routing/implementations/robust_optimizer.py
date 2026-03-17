"""
Scenario-based robust optimizer with predictive features.
"""

import copy
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Optional, Tuple
import numpy as np

try:
    # Script-mode import path (keeps backward compatibility)
    from distance_matrix import compute_matrices_from_vrp_input
    from modules.routing.implementations.ortools_optimizer import VRPModel
except ImportError:
    # Package-mode import path
    from src.distance_matrix import compute_matrices_from_vrp_input
    from .ortools_optimizer import VRPModel


class RobustOptimizer:
    """Solve multiple demand scenarios and pick a robust plan."""

    def __init__(
        self,
        base_vrp_input: Dict,
        demand_ratios: Optional[List[float]] = None,
        scenario_generator: Optional[object] = None,
        enable_parallel: bool = False,
        parallel_workers: int = 0,
    ) -> None:
        self.base_vrp_input = base_vrp_input
        self.demand_ratios = demand_ratios or [0.9, 1.0, 1.1]
        self.scenario_generator = scenario_generator
        self.enable_parallel = enable_parallel
        self.parallel_workers = parallel_workers
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

    def _solve_single_scenario(
        self,
        scenario_input: Dict,
        idx: int,
        use_euclidean: bool,
        average_speed: float,
        time_limit: int,
    ) -> Optional[Dict]:
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

        if not solution:
            print("  [FAIL] No solution found")
            return None

        details = vrp_model.get_solution_details()
        details['scenario_id'] = idx
        details['demand_ratio'] = ratio
        details['scenario_name'] = scenario_name
        details['distance_matrix'] = distance_matrix
        details['scenario_weight'] = float(scenario_input.get('scenario_weight', 1.0))

        print(f"  [OK] Total Distance: {details['total_distance'] / 100:.2f} km")
        print(f"  [OK] Routes: {len(details['routes'])}")
        if details['dropped_nodes']:
            print(f"  [WARN] SLA Violations: {len(details['dropped_nodes'])} nodes")
        return details

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
        if self.enable_parallel and len(self.scenarios) > 1:
            workers = self.parallel_workers if self.parallel_workers and self.parallel_workers > 0 else min(4, len(self.scenarios))
            print(f"[INFO] Parallel solving enabled, workers={workers}")
            ordered_results: Dict[int, Dict] = {}
            with ThreadPoolExecutor(max_workers=workers) as executor:
                future_to_idx = {
                    executor.submit(
                        self._solve_single_scenario,
                        scenario_input,
                        idx,
                        use_euclidean,
                        average_speed,
                        time_limit,
                    ): idx
                    for idx, scenario_input in enumerate(self.scenarios)
                }

                for future in as_completed(future_to_idx):
                    idx = future_to_idx[future]
                    details = future.result()
                    if details is not None:
                        ordered_results[idx] = details

            self.scenario_solutions = [ordered_results[i] for i in sorted(ordered_results.keys())]
        else:
            for idx, scenario_input in enumerate(self.scenarios):
                details = self._solve_single_scenario(
                    scenario_input,
                    idx,
                    use_euclidean,
                    average_speed,
                    time_limit,
                )
                if details is not None:
                    self.scenario_solutions.append(details)

        print(f"\n{'='*60}\n")
        return self.scenario_solutions

    def _score_solution(self, sol: Dict, criterion: str, weights: Optional[Dict[str, float]] = None) -> Tuple[float, Dict[str, float]]:
        total_distance = float(sol.get('total_distance', 0.0))
        route_max = float(max((route.get('distance', 0.0) for route in sol.get('routes', [])), default=0.0))
        sla_violations = float(len(sol.get('dropped_nodes', [])))
        route_count = float(len(sol.get('routes', [])))
        scenario_weight = float(sol.get('scenario_weight', 1.0))

        if criterion == 'min_max_distance':
            score = route_max
        elif criterion == 'min_avg_distance':
            score = total_distance
        elif criterion == 'min_sla_violation':
            score = sla_violations
        elif criterion == 'weighted_sum':
            w = weights or {}
            # Default: prioritize SLA, then distance and route balance.
            w_dist = float(w.get('distance', 0.5))
            w_max = float(w.get('max_route', 0.2))
            w_sla = float(w.get('sla', 0.3))
            score = w_dist * total_distance + w_max * route_max + w_sla * sla_violations * 100.0
        else:
            score = total_distance

        score = score * scenario_weight
        metrics = {
            'total_distance': total_distance,
            'max_route_distance': route_max,
            'sla_violations': sla_violations,
            'route_count': route_count,
            'scenario_weight': scenario_weight,
            'score': score,
        }
        return score, metrics

    def _pareto_select(self) -> Tuple[int, Dict]:
        metric_rows = []
        for idx, sol in enumerate(self.scenario_solutions):
            _, metrics = self._score_solution(sol, 'weighted_sum')
            metric_rows.append((idx, metrics))

        pareto_idxs: List[int] = []
        for i, (_, m_i) in enumerate(metric_rows):
            dominated = False
            for j, (_, m_j) in enumerate(metric_rows):
                if i == j:
                    continue
                non_worse_all = (
                    m_j['total_distance'] <= m_i['total_distance'] and
                    m_j['max_route_distance'] <= m_i['max_route_distance'] and
                    m_j['sla_violations'] <= m_i['sla_violations']
                )
                strictly_better_any = (
                    m_j['total_distance'] < m_i['total_distance'] or
                    m_j['max_route_distance'] < m_i['max_route_distance'] or
                    m_j['sla_violations'] < m_i['sla_violations']
                )
                if non_worse_all and strictly_better_any:
                    dominated = True
                    break
            if not dominated:
                pareto_idxs.append(i)

        if not pareto_idxs:
            pareto_idxs = [0]

        best_idx = min(
            pareto_idxs,
            key=lambda i: metric_rows[i][1]['total_distance'] + metric_rows[i][1]['max_route_distance'] + metric_rows[i][1]['sla_violations'] * 100.0,
        )
        return best_idx, {'pareto_front_indices': pareto_idxs}

    def select_robust_solution(self, criterion: str = 'min_max_distance', weights: Optional[Dict[str, float]] = None) -> Dict:
        if not self.scenario_solutions:
            return {'status': 'No solutions available'}

        print(f"Selection Criterion: {criterion}\n")

        selection_metadata: Dict = {}
        if criterion == 'pareto':
            best_idx, selection_metadata = self._pareto_select()
            robust_solution = self.scenario_solutions[best_idx]
            print(f"Selected: Scenario {best_idx + 1} (pareto)")
            print(f"Pareto front: {[i + 1 for i in selection_metadata.get('pareto_front_indices', [])]}")
        else:
            scored = []
            for idx, sol in enumerate(self.scenario_solutions):
                score, metrics = self._score_solution(sol, criterion, weights)
                scored.append((idx, score, metrics))

            best_idx = min(scored, key=lambda x: x[1])[0]
            robust_solution = self.scenario_solutions[best_idx]
            best_metrics = [m for i, _, m in scored if i == best_idx][0]
            print(f"Selected: Scenario {best_idx + 1}")
            print(f"Score: {best_metrics['score']:.2f}")
            print(f"Distance: {best_metrics['total_distance'] / 100:.2f} km")
            print(f"Max Route: {best_metrics['max_route_distance'] / 100:.2f} km")
            print(f"SLA violations: {int(best_metrics['sla_violations'])}")

            if criterion not in {'min_max_distance', 'min_avg_distance', 'min_sla_violation', 'weighted_sum'}:
                print("[WARN] Unknown criterion, defaulting to distance-oriented scoring")

        robust_solution['selection_criterion'] = criterion
        robust_solution['selection_metadata'] = selection_metadata

        return robust_solution

    def get_scenario_comparison(self) -> Dict:
        comparison = {'scenarios': [], 'summary': {}}
        for sol in self.scenario_solutions:
            comparison['scenarios'].append({
                'scenario_id': sol['scenario_id'],
                'scenario_name': sol.get('scenario_name', f"scenario_{sol['scenario_id']}"),
                'demand_ratio': sol['demand_ratio'],
                'scenario_weight': sol.get('scenario_weight', 1.0),
                'total_distance': sol['total_distance'] / 100,
                'max_route_distance': max((route.get('distance', 0) for route in sol.get('routes', [])), default=0) / 100,
                'num_routes': len(sol['routes']),
                'sla_violations': len(sol.get('dropped_nodes', [])),
            })

        if comparison['scenarios']:
            distances = [s['total_distance'] for s in comparison['scenarios']]
            max_routes = [s['max_route_distance'] for s in comparison['scenarios']]
            sla_values = [s['sla_violations'] for s in comparison['scenarios']]
            comparison['summary'] = {
                'min_distance': min(distances),
                'max_distance': max(distances),
                'avg_distance': float(np.mean(distances)),
                'std_distance': float(np.std(distances)),
                'avg_max_route_distance': float(np.mean(max_routes)),
                'max_sla_violations': int(max(sla_values)),
            }
        return comparison
