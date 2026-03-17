"""
Solver - Main solver and result parser
求解器与结果解析 - 主入口
"""

from typing import Dict, Tuple
import time
from data_interface import load_forecast_data, prepare_vrp_input, validate_input_data
from distance_matrix import compute_matrices_from_vrp_input
from modules.routing.implementations.ortools_optimizer import VRPModel
from modules.routing.implementations.robust_optimizer import RobustOptimizer
from modules.routing.implementations.scenario_generator import ScenarioGenerator
from optimization_result import OptimizationResult, convert_solution_to_github_format
import config


def solve_vrp(
    vrp_input: Dict,
    use_robust: bool = False,
    time_limit: int = None
) -> Dict:
    """
    Main VRP solver function
    主VRP求解函数
    
    Args:
        vrp_input: VRP input dictionary
        use_robust: Use robust optimization
        time_limit: Time limit in seconds
    
    Returns:
        Solution dictionary
    """
    start_time = time.time()
    
    # Validate input
    is_valid, msg = validate_input_data(vrp_input)
    if not is_valid:
        return {'status': 'Error', 'message': msg}
    
    # Set time limit
    if time_limit is None:
        time_limit = config.MAX_SEARCH_TIME
    
    # Robust optimization
    if use_robust:
        # 若启用预测场景或配置了蒙特卡洛/权重，创建自定义场景生成器
        scenario_gen = None
        if config.ENABLE_PREDICTIVE_SCENARIOS or config.MONTE_CARLO_SAMPLES > 0 or config.SCENARIO_WEIGHTS:
            scenario_gen = ScenarioGenerator(
                quantile_keys=config.DEMAND_QUANTILE_COLS,
                feature_key=config.LEARNING_FEATURE_COL,
                feature_weight=config.LEARNING_FEATURE_WEIGHT,
                scenario_weights=config.SCENARIO_WEIGHTS,
                monte_carlo_samples=config.MONTE_CARLO_SAMPLES,
                monte_carlo_std=config.MONTE_CARLO_STD,
                monte_carlo_max_samples=config.MONTE_CARLO_MAX_SAMPLES,
            )

        robust_optimizer = RobustOptimizer(
            vrp_input,
            demand_ratios=config.DEMAND_RATIOS,
            scenario_generator=scenario_gen,  # 传入自定义场景生成器
            enable_parallel=getattr(config, 'ROBUST_ENABLE_PARALLEL', False),
            parallel_workers=getattr(config, 'ROBUST_PARALLEL_WORKERS', 0),
        )
        robust_optimizer.generate_scenarios()
        robust_optimizer.solve_all_scenarios(
            use_euclidean=config.USE_EUCLIDEAN_DISTANCE,
            average_speed=config.VEHICLE_SPEED,
            time_limit=time_limit
        )
        
        solution = robust_optimizer.select_robust_solution(
            criterion=config.ROBUST_SELECTION_CRITERION,
            weights=getattr(config, 'ROBUST_SELECTION_WEIGHTS', None),
        )
        solution['optimization_type'] = 'robust'
        solution['scenarios'] = robust_optimizer.get_scenario_comparison()
    
    # Standard optimization
    else:
        # Compute distance and time matrices
        distance_matrix, time_matrix = compute_matrices_from_vrp_input(
            vrp_input,
            use_euclidean=config.USE_EUCLIDEAN_DISTANCE,
            average_speed=config.VEHICLE_SPEED
        )
        
        # Scale distance matrix
        distance_matrix_scaled = (distance_matrix * 100).astype(int)
        
        # Create and solve VRP model
        vrp_model = VRPModel(vrp_input, distance_matrix_scaled, time_matrix)
        vrp_model.create_model()
        vrp_solution = vrp_model.solve(time_limit)
        
        if vrp_solution:
            solution = vrp_model.get_solution_details()
            solution['optimization_type'] = 'standard'
            solution['distance_matrix'] = distance_matrix
        else:
            solution = {'status': 'No solution found'}
    
    # Add computation time
    solution['computation_time'] = time.time() - start_time
    
    return solution


def format_solution_output(solution: Dict, vrp_input: Dict = None) -> str:
    """
    Format solution for readable console output
    以汇总清晰的格式输出解决方案
    
    Output Includes:
        - 求解类型（标准 / 鲁棒）
        - 总距离和路线数量
        - 每辆车的下次序列
        - SLA违反是否
        - （鲁棒模式）场景对比
    
    Args:
        solution: VRP求解结果字典
        vrp_input: 原始输入（可选）
    
    Returns:
        格式化的字符串
    """
    if solution.get('status') != 'Success':
        return f"Status: {solution.get('status', 'Unknown')}"
    
    output = []
    output.append("\n" + "=" * 60)
    output.append("ROUTING SOLUTION")
    output.append("=" * 60)
    
    # Summary statistics (汇总统计)
    output.append(f"\nOptimization Type: {solution.get('optimization_type', 'standard').upper()}")
    output.append(f"Total Distance: {solution['total_distance'] / 100:.2f} km")
    output.append(f"Number of Routes: {len(solution['routes'])}")
    output.append(f"Computation Time: {solution.get('computation_time', 0):.2f} seconds")
    
    # SLA violations check (服务水平协议违反检查)
    if solution.get('dropped_nodes'):
        output.append(f"\n[WARN] SLA VIOLATIONS: {len(solution['dropped_nodes'])} stores not served")
        output.append(f"   Dropped stores: {solution['dropped_nodes']}")
    else:
        output.append(f"\n[OK] All stores served within time windows")
    
    # Detailed routes (每条路线的详细信息)
    output.append(f"\n{'-' * 60}")
    output.append("ROUTES DETAILS")
    output.append(f"{'-' * 60}")
    
    for route in solution['routes']:
        output.append(f"\nVehicle {route['vehicle_id']}:")
        
        # Format visit sequence (访问序列)
        sequence_str = " → ".join([
            f"Store {node}" if node != 0 else "Depot"
            for node in route['sequence']
        ])
        output.append(f"  Route: {sequence_str}")
        
        # Route metrics (路线指标)
        output.append(f"  Distance: {route['distance'] / 100:.2f} km")
        output.append(f"  Load: {route['load']:.1f} units")
        
        # Time information (时间信息)
        if route.get('times'):
            output.append(f"  Departure: {route['times'][0]} min")
            output.append(f"  Return: {route['times'][-1]} min")
    
    # Scenario comparison (for robust optimization)
    if solution.get('scenarios'):
        output.append(f"\n{'-' * 60}")
        output.append("SCENARIO COMPARISON")
        output.append(f"{'-' * 60}")
        
        for scenario in solution['scenarios']['scenarios']:
            ratio = scenario.get('demand_ratio', None)
            ratio_display = f"{ratio:.1%}" if isinstance(ratio, (int, float)) else "N/A"
            output.append(f"\nScenario {scenario['scenario_id'] + 1} "
                         f"(Demand: {ratio_display}):")
            output.append(f"  Distance: {scenario['total_distance']:.2f} km")
            output.append(f"  Routes: {scenario['num_routes']}")
            if scenario['sla_violations'] > 0:
                output.append(f"  SLA Violations: {scenario['sla_violations']}")
        
        summary = solution['scenarios']['summary']
        output.append(f"\nSummary Statistics:")
        output.append(f"  Min Distance: {summary['min_distance']:.2f} km")
        output.append(f"  Max Distance: {summary['max_distance']:.2f} km")
        output.append(f"  Avg Distance: {summary['avg_distance']:.2f} km")
        output.append(f"  Std Distance: {summary['std_distance']:.2f} km")
    
    output.append(f"\n{'=' * 60}\n")
    
    return "\n".join(output)


def export_solution_to_dict(solution: Dict) -> Dict:
    """
    Export solution in standardized format for team integration
    导出标准化格式的解决方案供团队集成
    
    Args:
        solution: Solution dictionary
    
    Returns:
        Standardized solution dictionary
    """
    export = {
        'status': solution.get('status', 'Unknown'),
        'routes': [],
        'metrics': {
            'total_distance_km': solution.get('total_distance', 0) / 100,
            'num_vehicles_used': len(solution.get('routes', [])),
            'computation_time_sec': solution.get('computation_time', 0),
            'optimization_type': solution.get('optimization_type', 'standard')
        },
        'sla_violations': solution.get('dropped_nodes', [])
    }
    
    # Format routes
    for route in solution.get('routes', []):
        route_export = {
            'vehicle_id': route['vehicle_id'],
            'store_sequence': [
                node for node in route['sequence'] if node != 0
            ],
            'distance_km': route['distance'] / 100,
            'load_units': route['load'],
            'departure_time_min': route['times'][0] if route.get('times') else None,
            'return_time_min': route['times'][-1] if route.get('times') else None
        }
        export['routes'].append(route_export)
    
    return export
