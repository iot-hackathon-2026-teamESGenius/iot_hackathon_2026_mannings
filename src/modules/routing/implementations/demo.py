"""
路径优化Demo脚本

运行方式:
    cd /home/yeah/iot_hackathon_2026_mannings
    conda activate mannings-sla
    python -m src.modules.routing.implementations.demo
"""
import sys
from pathlib import Path

# 添加项目根目录
project_root = Path(__file__).parent.parent.parent.parent.parent
sys.path.insert(0, str(project_root))

import numpy as np
from datetime import datetime

from src.core.interfaces import StoreInfo, DemandForecast
from src.modules.routing.implementations.ortools_optimizer import ORToolsRoutingOptimizer
from src.modules.routing.implementations.robust_optimizer import (
    RobustRoutingOptimizer, VehicleInfo
)
from src.modules.routing.implementations.scenario_generator import ScenarioGenerator

def generate_mock_stores(n_stores: int = 8) -> list:
    """生成模拟门店数据"""
    stores = []
    
    # 香港区域门店位置
    base_locations = [
        ("M001", "Mannings Tsim Sha Tsui", 22.2988, 114.1722),
        ("M002", "Mannings Causeway Bay", 22.2800, 114.1830),
        ("M003", "Mannings Central", 22.2820, 114.1580),
        ("M004", "Mannings Mongkok", 22.3193, 114.1694),
        ("M005", "Mannings Sha Tin", 22.3817, 114.1877),
        ("M006", "Mannings Tuen Mun", 22.3908, 113.9728),
        ("M007", "Mannings Kwun Tong", 22.3100, 114.2260),
        ("M008", "Mannings Yuen Long", 22.4450, 114.0220),
    ]
    
    for i, (store_id, name, lat, lng) in enumerate(base_locations[:n_stores]):
        stores.append(StoreInfo(
            store_id=store_id,
            name=name,
            address=f"{name}, Hong Kong",
            latitude=lat,
            longitude=lng,
            time_window_start="08:00",
            time_window_end="18:00",
            capacity=100.0
        ))
    
    return stores

def generate_mock_demands(stores: list) -> dict:
    """生成模拟需求数据"""
    demands = {}
    for store in stores:
        demands[store.store_id] = np.random.randint(10, 50)
    return demands

def generate_mock_forecasts(stores: list) -> list:
    """生成模拟预测结果"""
    forecasts = []
    for store in stores:
        base_demand = np.random.randint(20, 60)
        forecasts.append(DemandForecast(
            store_id=store.store_id,
            sku_id="ALL",
            date=datetime.now().strftime("%Y-%m-%d"),
            forecast_demand=base_demand,
            lower_bound=base_demand * 0.85,
            upper_bound=base_demand * 1.15,
            confidence=0.9
        ))
    return forecasts

def generate_mock_vehicles(n_vehicles: int = 5) -> list:
    """生成模拟车辆数据"""
    vehicles = []
    for i in range(n_vehicles):
        vehicles.append(VehicleInfo(
            vehicle_id=f"V{i+1:03d}",
            capacity=100.0,
            cost_per_km=1.5,
            max_route_time_min=480
        ))
    return vehicles

def run_baseline_demo():
    """运行Baseline优化Demo"""
    print("=" * 60)
    print("Baseline Optimization (Deterministic CVRPTW)")
    print("=" * 60)
    
    # 准备数据
    stores = generate_mock_stores(8)
    demands = generate_mock_demands(stores)
    vehicles = generate_mock_vehicles(5)
    
    print(f"\n门店数量: {len(stores)}")
    print(f"车辆数量: {len(vehicles)}")
    print(f"总需求量: {sum(demands.values())} 单位")
    
    # 创建优化器
    optimizer = ORToolsRoutingOptimizer(time_limit_seconds=10)
    
    # 运行优化
    print("\n正在求解...")
    routes = optimizer.optimize_routes(
        stores=stores,
        demands=demands,
        vehicles=vehicles,
        distance_calculator=None,
        time_windows=True,
        capacity_constraints=True
    )
    
    # 输出结果
    print(f"\n生成路线数量: {len(routes)}")
    for route in routes:
        print(f"\n{route.vehicle_id}: Depot → {' → '.join(route.store_sequence)} → Depot")
        print(f"  总距离: {route.total_distance_km:.2f} km")
        print(f"  总成本: ${route.total_cost:.2f}")
        print(f"  SLA风险: {route.sla_risk_score:.2%}")
    
    # 评估
    metrics = optimizer.evaluate_routes(routes)
    print("\n整体指标:")
    for key, value in metrics.items():
        print(f"  {key}: {value}")
    
    return routes

def run_robust_demo():
    """运行鲁棒优化Demo"""
    print("\n" + "=" * 60)
    print("Robust Optimization (Scenario-based)")
    print("=" * 60)
    
    # 准备数据
    stores = generate_mock_stores(8)
    forecasts = generate_mock_forecasts(stores)
    vehicles = generate_mock_vehicles(5)
    
    print(f"\n门店数量: {len(stores)}")
    print(f"车辆数量: {len(vehicles)}")
    
    # 创建鲁棒优化器
    robust_optimizer = RobustRoutingOptimizer(
        time_limit_seconds=10,
        robustness_level=0.9,
        demand_ratios=[0.9, 1.0, 1.1],
        selection_criterion="min_max_distance"
    )
    
    # 从预测结果进行鲁棒优化
    print("\n正在进行多情景鲁棒优化...")
    result = robust_optimizer.robust_optimization_from_forecasts(
        stores=stores,
        forecasts=forecasts,
        vehicles=vehicles,
        distance_calculator=None,
        use_confidence_bounds=False
    )
    
    if result:
        print(f"\n情景数量: {result.statistics['total_scenarios']}")
        print(f"计算时间: {result.statistics['total_computation_time']:.2f}s")
        print(f"选择标准: {result.selection_criterion}")
        
        print("\n各情景结果:")
        for sr in result.all_scenario_results:
            print(f"  {sr.scenario_id}: 距离={sr.total_distance_km:.2f}km, 路线={len(sr.routes)}条")
        
        print(f"\n统计摘要:")
        print(f"  最小距离: {result.statistics['min_distance']:.2f} km")
        print(f"  最大距离: {result.statistics['max_distance']:.2f} km")
        print(f"  平均距离: {result.statistics['avg_distance']:.2f} km")
        print(f"  标准差: {result.statistics['std_distance']:.2f} km")
        
        print(f"\n选中方案 ({result.selected_result.scenario_id}):")
        for route in result.selected_result.routes:
            print(f"  {route.vehicle_id}: Depot → {' → '.join(route.store_sequence)} → Depot")
            print(f"    距离: {route.total_distance_km:.2f} km, 成本: ${route.total_cost:.2f}")
    else:
        print("优化失败，未找到可行解")

def run_comparison():
    """运行对比实验"""
    print("\n" + "=" * 60)
    print("Baseline vs Robust Optimization Comparison")
    print("=" * 60)
    
    # 准备相同的数据
    stores = generate_mock_stores(8)
    forecasts = generate_mock_forecasts(stores)
    vehicles = generate_mock_vehicles(5)
    
    # 基准需求
    base_demands = {f.store_id: f.forecast_demand for f in forecasts}
    
    # Baseline
    baseline_opt = ORToolsRoutingOptimizer(time_limit_seconds=10)
    baseline_routes = baseline_opt.optimize_routes(
        stores, base_demands, vehicles, None
    )
    baseline_metrics = baseline_opt.evaluate_routes(baseline_routes)
    
    # Robust
    robust_opt = RobustRoutingOptimizer(time_limit_seconds=10)
    robust_result = robust_opt.robust_optimization_from_forecasts(
        stores, forecasts, vehicles, None
    )
    
    print("\n对比结果:")
    print("-" * 40)
    print(f"{'指标':<20} {'Baseline':<15} {'Robust':<15}")
    print("-" * 40)
    
    if robust_result:
        robust_metrics = robust_opt.evaluate_routes(robust_result.selected_result.routes)
        
        print(f"{'总距离 (km)':<20} {baseline_metrics['total_distance_km']:<15.2f} {robust_metrics['total_distance_km']:<15.2f}")
        print(f"{'总成本 ($)':<20} {baseline_metrics['total_cost']:<15.2f} {robust_metrics['total_cost']:<15.2f}")
        print(f"{'路线数量':<20} {baseline_metrics['num_routes']:<15} {robust_metrics['num_routes']:<15}")
        print(f"{'平均SLA风险':<20} {baseline_metrics['sla_risk_average']:<15.2%} {robust_metrics['avg_sla_risk']:<15.2%}")
        print(f"{'最坏情况距离':<20} {'-':<15} {robust_result.worst_case_distance:<15.2f}")
    
    print("-" * 40)

if __name__ == "__main__":
    print("路径优化模块 Demo")
    print("技术方案: Learning Enhanced Robust Routing")
    print("创新点: Scenario-based Robust Optimization")
    print()
    
    # 运行Demo
    run_baseline_demo()
    run_robust_demo()
    run_comparison()
