"""
Greedy baseline heuristics for VRP
简易贪心基线算法
"""

from typing import Dict, List, Set
from distance_matrix import compute_matrices_from_vrp_input
import config


def _build_greedy_routes(vrp_input: Dict) -> Dict:
    """贪心路由构建算法：逐车辆按最近可行店点扩展路线
    用作性能基线，对比OR-Tools优化的改进效果"""
    # 计算距离矩阵和时间矩阵
    distance_matrix, time_matrix = compute_matrices_from_vrp_input(
        vrp_input,
        use_euclidean=config.USE_EUCLIDEAN_DISTANCE,
        average_speed=config.VEHICLE_SPEED,
    )

    # 初始化：所有门店（除仓库外）为未访问
    unvisited: Set[int] = set(range(1, len(vrp_input["stores"]) + 1))
    total_distance = 0.0
    total_time = 0
    routes: List[Dict] = []

    # 逐车辆构建路线
    for vehicle_id in range(vrp_input["num_vehicles"]):
        if not unvisited:
            break

        # 初始化路线（从仓库开始）
        sequence = [0]
        times = [0]
        load = 0.0
        current = 0  # 当前位置（初始为仓库）
        elapsed = 0  # 经过的时间
        route_distance = 0.0

        # 贪心扩展路线：重复选择最近可行的店点
        while True:
            candidates = []  # 可行候选店点列表
            for node in list(unvisited):
                store = vrp_input["stores"][node - 1]
                demand = store["demand"]
                
                # 检查容量约束
                if load + demand > vrp_input["vehicle_capacity"]:
                    continue

                # 检查时间窗口约束
                travel = time_matrix[current][node]
                arrival = elapsed + travel
                tw_start, tw_end = store.get("time_window", (0, 999999))
                wait = max(0, tw_start - arrival)  # 等待时间（若需早到）
                finish = arrival + wait + (config.SERVICE_TIME if node != 0 else 0)
                
                # 若能在时间窗内完成，加入候选列表
                if finish <= tw_end:
                    candidates.append((distance_matrix[current][node], node, finish, arrival))

            # 无可行候选，路线完成
            if not candidates:
                break

            # 选择距离最近的候选（贪心策略）
            candidates.sort(key=lambda x: x[0])
            _, chosen, finish_time, arrival_time = candidates[0]
            route_distance += distance_matrix[current][chosen]
            elapsed = finish_time
            load += vrp_input["stores"][chosen - 1]["demand"]
            sequence.append(chosen)
            times.append(int(finish_time))
            unvisited.remove(chosen)
            current = chosen

        # 返回仓库完成路线
        route_distance += distance_matrix[current][0]
        elapsed += time_matrix[current][0]
        sequence.append(0)
        times.append(int(elapsed))

        # 记录路线信息
        routes.append(
            {
                "vehicle_id": vehicle_id,
                "sequence": sequence,
                "distance": int(round(route_distance * 100)),
                "load": load,
                "times": times,
            }
        )
        total_distance += route_distance
        total_time = max(total_time, int(elapsed))

    # 未访问的门店（由于容量或时间窗限制）
    dropped_nodes = sorted(unvisited)

    return {
        "status": "Success",
        "optimization_type": "greedy_baseline",
        "routes": routes,
        "total_distance": int(round(total_distance * 100)),
        "total_time": total_time,
        "dropped_nodes": dropped_nodes,
        "distance_matrix": distance_matrix,
    }


def run_greedy_baseline(vrp_input: Dict) -> Dict:
    """贪心基线求解器入口函数
    返回格式与OR-Tools解相同，便于对比"""
    return _build_greedy_routes(vrp_input)
