"""
决策规划路由 - 适配前端补货计划和车队调度页面
"""
from fastapi import APIRouter, HTTPException, Query, Depends, Body
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime, date, timedelta
from pathlib import Path
import numpy as np
import uuid
import pandas as pd

from src import config as routing_config
from src.data_interface import prepare_vrp_input, load_dfi_zip_as_forecast_data
from src.solver import solve_vrp, export_solution_to_dict

router = APIRouter()

# ==================== 请求/响应模型 ====================

class ReplenishmentPlanItem(BaseModel):
    """补货计划条目"""
    plan_id: str
    dc_id: str
    dc_name: str
    ecdc_id: str
    ecdc_name: str
    sku_id: str
    sku_name: str
    recommended_qty: float
    actual_qty: Optional[float] = None
    replenishment_date: str
    status: str  # pending / approved / adjusted / rejected
    is_feasible: bool
    infeasible_reason: Optional[str] = None
    reviewer: Optional[str] = None
    review_time: Optional[str] = None
    adjustment_reason: Optional[str] = None

class AdjustmentRequest(BaseModel):
    """补货量调整请求"""
    new_qty: float
    reason: str
    operator: str

class ApprovalRequest(BaseModel):
    """审核请求"""
    approved: bool
    reviewer: str
    reject_reason: Optional[str] = None

class ScheduleItem(BaseModel):
    """调度计划条目"""
    vehicle_id: str
    driver_name: str
    driver_phone: str
    departure_time: str
    departure_window: str
    store_list: List[str]
    store_names: List[str]
    estimated_duration_min: float
    estimated_cost: float
    status: str  # pending / in_progress / completed / abnormal
    abnormal_reason: Optional[str] = None

class ScheduleAdjustmentRequest(BaseModel):
    """调度调整请求"""
    store_list: Optional[List[str]] = None
    departure_time: Optional[str] = None
    driver_id: Optional[str] = None
    operator: str


class OptimizeRoutesRequest(BaseModel):
    """路径优化请求（保持字段稳定，新增可选控制参数）"""
    use_real_data: bool = True
    zip_path: Optional[str] = None
    target_date: Optional[str] = None
    top_n_stores: int = 15
    num_vehicles: Optional[int] = None
    vehicle_capacity: Optional[int] = None
    use_robust: bool = True
    time_limit: int = 10
    use_haversine: bool = True
    update_schedules: bool = True

# ==================== 模拟数据 ====================

MOCK_DCS = {"DC01": "主配送中心"}
MOCK_ECDCS = {"ECDC01": "葵涌电商中心", "ECDC02": "荃湾电商中心"}
MOCK_SKUS = {
    "SKU001": "维他命C 1000mg",
    "SKU002": "感冒灵颗粒",
    "SKU003": "洗手液 500ml",
    "SKU004": "口罩 50片装",
    "SKU005": "消毒湿巾"
}
MOCK_STORES = {
    "M001": ("Mannings Tsim Sha Tsui", 22.2988, 114.1722),
    "M002": ("Mannings Causeway Bay", 22.2800, 114.1830),
    "M003": ("Mannings Central", 22.2820, 114.1580),
    "M004": ("Mannings Mongkok", 22.3193, 114.1694),
    "M005": ("Mannings Sha Tin", 22.3817, 114.1877)
}
MOCK_VEHICLES = {
    "V001": {"driver": "陈大文", "phone": "9123****"},
    "V002": {"driver": "李小明", "phone": "9456****"},
    "V003": {"driver": "王志强", "phone": "9789****"}
}

# 模拟数据存储
REPLENISHMENT_PLANS: Dict[str, ReplenishmentPlanItem] = {}
SCHEDULES: Dict[str, ScheduleItem] = {}

def init_mock_data():
    """初始化模拟数据"""
    global REPLENISHMENT_PLANS, SCHEDULES
    
    # 生成补货计划
    for ecdc_id, ecdc_name in MOCK_ECDCS.items():
        for sku_id, sku_name in MOCK_SKUS.items():
            plan_id = f"REP-{ecdc_id}-{sku_id}-{date.today().isoformat()}"
            recommended = np.random.randint(50, 200)
            is_feasible = np.random.random() > 0.2
            
            REPLENISHMENT_PLANS[plan_id] = ReplenishmentPlanItem(
                plan_id=plan_id,
                dc_id="DC01",
                dc_name=MOCK_DCS["DC01"],
                ecdc_id=ecdc_id,
                ecdc_name=ecdc_name,
                sku_id=sku_id,
                sku_name=sku_name,
                recommended_qty=recommended,
                actual_qty=None,
                replenishment_date=date.today().isoformat(),
                status="pending",
                is_feasible=is_feasible,
                infeasible_reason="超出ECDC处理能力" if not is_feasible else None
            )
    
    # 生成调度计划
    routes = [
        (["M001", "M003", "M005"], "08:00", "08:00-10:00"),
        (["M002", "M004"], "09:00", "09:00-11:00"),
        (["M001", "M002", "M003"], "14:00", "14:00-16:00")
    ]
    
    for i, (stores, dep_time, window) in enumerate(routes):
        vehicle_id = f"V00{i+1}"
        vehicle = MOCK_VEHICLES[vehicle_id]
        
        SCHEDULES[vehicle_id] = ScheduleItem(
            vehicle_id=vehicle_id,
            driver_name=vehicle["driver"],
            driver_phone=vehicle["phone"],
            departure_time=dep_time,
            departure_window=window,
            store_list=stores,
            store_names=[MOCK_STORES[s][0] for s in stores],
            estimated_duration_min=60 + len(stores) * 20,
            estimated_cost=100 + len(stores) * 25,
            status=np.random.choice(["pending", "in_progress", "completed", "abnormal"], 
                                     p=[0.3, 0.4, 0.2, 0.1]),
            abnormal_reason="交通拥堵延迟30分钟" if np.random.random() < 0.1 else None
        )

# 初始化
init_mock_data()

# ==================== 补货计划API ====================

@router.get("/replenishment")
async def get_replenishment_plans(
    date_from: Optional[str] = Query(None, description="开始日期"),
    date_to: Optional[str] = Query(None, description="结束日期"),
    dc_id: Optional[str] = Query(None, description="DC ID"),
    ecdc_id: Optional[str] = Query(None, description="ECDC ID"),
    status: Optional[str] = Query(None, description="状态"),
    sku_id: Optional[str] = Query(None, description="SKU ID")
):
    """
    获取补货计划列表
    """
    plans = list(REPLENISHMENT_PLANS.values())
    
    # 筛选
    if ecdc_id:
        plans = [p for p in plans if p.ecdc_id == ecdc_id]
    if status:
        plans = [p for p in plans if p.status == status]
    if sku_id:
        plans = [p for p in plans if p.sku_id == sku_id]
    
    # 统计
    stats = {
        "total": len(plans),
        "pending": len([p for p in plans if p.status == "pending"]),
        "approved": len([p for p in plans if p.status == "approved"]),
        "adjusted": len([p for p in plans if p.status == "adjusted"]),
        "infeasible": len([p for p in plans if not p.is_feasible])
    }
    
    return {
        "success": True,
        "data": {
            "plans": [p.dict() for p in plans],
            "statistics": stats
        }
    }

@router.put("/replenishment/{plan_id}/adjust")
async def adjust_replenishment(
    plan_id: str,
    request: AdjustmentRequest
):
    """
    调整补货数量
    """
    if plan_id not in REPLENISHMENT_PLANS:
        raise HTTPException(status_code=404, detail="补货计划不存在")
    
    plan = REPLENISHMENT_PLANS[plan_id]
    
    # 更新
    plan.actual_qty = request.new_qty
    plan.adjustment_reason = request.reason
    plan.status = "adjusted"
    
    return {
        "success": True,
        "message": "补货数量已调整",
        "data": plan.dict()
    }

@router.put("/replenishment/{plan_id}/approve")
async def approve_replenishment(
    plan_id: str,
    request: ApprovalRequest
):
    """
    审核补货计划
    """
    if plan_id not in REPLENISHMENT_PLANS:
        raise HTTPException(status_code=404, detail="补货计划不存在")
    
    plan = REPLENISHMENT_PLANS[plan_id]
    
    # 更新
    plan.reviewer = request.reviewer
    plan.review_time = datetime.now().isoformat()
    
    if request.approved:
        plan.status = "approved"
        if plan.actual_qty is None:
            plan.actual_qty = plan.recommended_qty
    else:
        plan.status = "rejected"
        plan.infeasible_reason = request.reject_reason
    
    return {
        "success": True,
        "message": "审核完成",
        "data": plan.dict()
    }

# ==================== 车队调度API ====================

def _build_mock_routing_dataframe() -> pd.DataFrame:
    rows = []
    for i, (store_id, info) in enumerate(MOCK_STORES.items()):
        demand = float(18 + i * 4)
        rows.append({
            'store_id': int(store_id.replace('M', '')),
            'demand': demand,
            'predicted_demand': demand,
            'demand_p10': demand * 0.9,
            'demand_p50': demand,
            'demand_p90': demand * 1.1,
            'time_window_start': 8 * 60,
            'time_window_end': 20 * 60,
            'lat': float(info[1]),
            'lon': float(info[2]),
            'feature_score': float(min(1.0, 0.3 + i * 0.12)),
        })
    return pd.DataFrame(rows)


def _format_minutes_to_hhmm(minutes_val: int) -> str:
    m = int(minutes_val) % (24 * 60)
    return f"{m // 60:02d}:{m % 60:02d}"


def _store_node_to_frontend_id(store_row: Dict[str, Any]) -> str:
    store_id = store_row.get('id')
    if isinstance(store_id, str) and store_id.startswith('M'):
        return store_id
    try:
        return f"M{int(store_id):03d}"
    except Exception:
        return f"M{store_id}"


def _build_map_payload_from_schedules(schedules: Dict[str, ScheduleItem]) -> Dict[str, Any]:
    dc_location = (22.3700, 114.1130)
    store_locations = {
        store_id: {"name": info[0], "lat": info[1], "lng": info[2]}
        for store_id, info in MOCK_STORES.items()
    }

    routes = []
    for schedule in schedules.values():
        route_coords = [dc_location]
        for store_id in schedule.store_list:
            if store_id in MOCK_STORES:
                route_coords.append((MOCK_STORES[store_id][1], MOCK_STORES[store_id][2]))
        routes.append({
            "vehicle_id": schedule.vehicle_id,
            "driver": schedule.driver_name,
            "store_sequence": schedule.store_list,
            "coordinates": route_coords,
            "departure_time": schedule.departure_time,
            "status": schedule.status,
        })

    geojson = {"type": "FeatureCollection", "features": []}
    geojson["features"].append({
        "type": "Feature",
        "geometry": {"type": "Point", "coordinates": [dc_location[1], dc_location[0]]},
        "properties": {"type": "dc", "name": "配送中心"},
    })
    for store_id, info in MOCK_STORES.items():
        geojson["features"].append({
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": [info[2], info[1]]},
            "properties": {"type": "store", "id": store_id, "name": info[0]},
        })

    return {
        "dc_location": {"lat": dc_location[0], "lng": dc_location[1]},
        "store_locations": store_locations,
        "routes": routes,
        "geojson": geojson,
    }


@router.post("/routes/optimize")
async def optimize_routes(request: OptimizeRoutesRequest = Body(default=OptimizeRoutesRequest())):
    """
    执行真实路径优化，并返回前端稳定字段结构。
    - 不改现有 /schedules 与 /routes/map-data 的返回结构
    - 可选接入 DFI.zip 真实数据
    """
    global SCHEDULES, MOCK_STORES

    try:
        # Keep existing business logic untouched; only narrow-scoped config overrides.
        routing_config.USE_EUCLIDEAN_DISTANCE = not bool(request.use_haversine)

        if request.use_real_data:
            default_zip = Path(__file__).resolve().parents[5] / "DFI.zip"
            zip_path = Path(request.zip_path) if request.zip_path else default_zip
            if not zip_path.exists():
                raise HTTPException(status_code=404, detail=f"DFI zip not found: {zip_path}")
            df = load_dfi_zip_as_forecast_data(
                zip_path=str(zip_path),
                target_date=request.target_date,
                top_n_stores=max(1, request.top_n_stores),
            )
        else:
            df = _build_mock_routing_dataframe().head(max(1, request.top_n_stores))

        total_demand = float(df['demand'].sum())
        num_vehicles = request.num_vehicles or max(3, min(20, int(np.ceil(len(df) / 2))))
        vehicle_capacity = request.vehicle_capacity or int(np.ceil(total_demand / max(num_vehicles * 0.9, 1.0)))

        depot_location = (22.3700, 114.1130)
        vrp_input = prepare_vrp_input(
            df,
            depot_location=depot_location,
            vehicle_capacity=vehicle_capacity,
            num_vehicles=num_vehicles,
        )
        solution = solve_vrp(vrp_input, use_robust=request.use_robust, time_limit=max(1, request.time_limit))

        if solution.get('status') != 'Success':
            raise HTTPException(status_code=422, detail=f"Optimization failed: {solution.get('status')}")

        # Sync optimized routes into existing schedule shape.
        new_schedules: Dict[str, ScheduleItem] = {}
        stores_by_node = {idx + 1: s for idx, s in enumerate(vrp_input['stores'])}
        new_mock_stores = dict(MOCK_STORES)

        for route in solution.get('routes', []):
            vehicle_id = f"V{int(route.get('vehicle_id', 0)) + 1:03d}"
            vehicle_meta = MOCK_VEHICLES.get(vehicle_id, {"driver": "待分配", "phone": "0000****"})

            node_seq = [n for n in route.get('sequence', []) if n != 0]
            store_list = []
            store_names = []
            for node in node_seq:
                store_row = stores_by_node.get(node)
                if not store_row:
                    continue
                fe_store_id = _store_node_to_frontend_id(store_row)
                store_name = f"Mannings Store {store_row.get('id')}"
                lat = float(store_row.get('lat', 22.3193))
                lon = float(store_row.get('lon', 114.1694))
                new_mock_stores[fe_store_id] = (store_name, lat, lon)
                store_list.append(fe_store_id)
                store_names.append(store_name)

            times = route.get('times', [])
            departure_time = _format_minutes_to_hhmm(times[0]) if times else "08:00"
            return_time = _format_minutes_to_hhmm(times[-1]) if times else "18:00"
            departure_window = f"{departure_time}-{return_time}"

            schedule = ScheduleItem(
                vehicle_id=vehicle_id,
                driver_name=vehicle_meta.get('driver', '待分配'),
                driver_phone=vehicle_meta.get('phone', '0000****'),
                departure_time=departure_time,
                departure_window=departure_window,
                store_list=store_list,
                store_names=store_names,
                estimated_duration_min=float(route.get('times', [0])[-1] - route.get('times', [0])[0]) if len(route.get('times', [])) >= 2 else 0.0,
                estimated_cost=float(route.get('distance', 0)) / 100.0 * 1.5,
                status="pending",
                abnormal_reason=None,
            )
            new_schedules[schedule.vehicle_id] = schedule

        if request.update_schedules:
            SCHEDULES = new_schedules
            MOCK_STORES = new_mock_stores

        map_payload = _build_map_payload_from_schedules(SCHEDULES if request.update_schedules else new_schedules)

        return {
            "success": True,
            "message": "路线优化完成",
            "data": {
                "schedules": [s.dict() for s in (SCHEDULES if request.update_schedules else new_schedules).values()],
                "date": date.today().isoformat(),
                "optimization_summary": {
                    "status": solution.get('status'),
                    "optimization_type": solution.get('optimization_type', 'standard'),
                    "total_distance_km": round(solution.get('total_distance', 0) / 100.0, 2),
                    "vehicles_used": len(solution.get('routes', [])),
                    "sla_violations": len(solution.get('dropped_nodes', [])),
                    "computation_time_sec": round(float(solution.get('computation_time', 0.0)), 2),
                    "dataset": "DFI" if request.use_real_data else "mock",
                    "stores": len(df),
                },
                "optimization_result": export_solution_to_dict(solution),
                "map_data": map_payload,
            },
        }
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Route optimization error: {exc}")

@router.get("/schedules")
async def get_schedules(
    schedule_date: Optional[str] = Query(None, description="调度日期"),
    vehicle_type: Optional[str] = Query(None, description="车辆类型"),
    status: Optional[str] = Query(None, description="状态")
):
    """
    获取车队调度计划
    """
    schedules = list(SCHEDULES.values())
    
    if status:
        schedules = [s for s in schedules if s.status == status]
    
    return {
        "success": True,
        "data": {
            "schedules": [s.dict() for s in schedules],
            "date": schedule_date or date.today().isoformat()
        }
    }

@router.get("/routes/map-data")
async def get_route_map_data(
    route_ids: Optional[str] = Query(None, description="路线ID列表，逗号分隔")
):
    """
    获取路线地图数据（用于地图可视化）
    """
    # DC位置
    dc_location = (22.3700, 114.1130)  # 葵涌
    
    # 门店位置
    store_locations = {
        store_id: {"name": info[0], "lat": info[1], "lng": info[2]}
        for store_id, info in MOCK_STORES.items()
    }
    
    # 路线数据
    routes = []
    for schedule in SCHEDULES.values():
        route_coords = [dc_location]
        for store_id in schedule.store_list:
            if store_id in MOCK_STORES:
                route_coords.append((MOCK_STORES[store_id][1], MOCK_STORES[store_id][2]))
        
        routes.append({
            "vehicle_id": schedule.vehicle_id,
            "driver": schedule.driver_name,
            "store_sequence": schedule.store_list,
            "coordinates": route_coords,
            "departure_time": schedule.departure_time,
            "status": schedule.status
        })
    
    # GeoJSON格式
    geojson = {
        "type": "FeatureCollection",
        "features": []
    }
    
    # 添加DC点
    geojson["features"].append({
        "type": "Feature",
        "geometry": {"type": "Point", "coordinates": [dc_location[1], dc_location[0]]},
        "properties": {"type": "dc", "name": "配送中心"}
    })
    
    # 添加门店点
    for store_id, info in MOCK_STORES.items():
        geojson["features"].append({
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": [info[2], info[1]]},
            "properties": {"type": "store", "id": store_id, "name": info[0]}
        })
    
    return {
        "success": True,
        "data": {
            "dc_location": {"lat": dc_location[0], "lng": dc_location[1]},
            "store_locations": store_locations,
            "routes": routes,
            "geojson": geojson
        }
    }

@router.put("/schedules/{vehicle_id}/adjust")
async def adjust_schedule(
    vehicle_id: str,
    request: ScheduleAdjustmentRequest
):
    """
    调整调度方案
    """
    if vehicle_id not in SCHEDULES:
        raise HTTPException(status_code=404, detail="调度计划不存在")
    
    schedule = SCHEDULES[vehicle_id]
    original = schedule.dict()
    
    # 应用调整
    if request.store_list:
        schedule.store_list = request.store_list
        schedule.store_names = [MOCK_STORES[s][0] for s in request.store_list if s in MOCK_STORES]
        schedule.estimated_duration_min = 60 + len(request.store_list) * 20
        schedule.estimated_cost = 100 + len(request.store_list) * 25
    
    if request.departure_time:
        schedule.departure_time = request.departure_time
    
    return {
        "success": True,
        "message": "调度方案已调整",
        "data": {
            "original": original,
            "adjusted": schedule.dict()
        }
    }

@router.get("/vehicles/realtime")
async def get_realtime_vehicle_positions():
    """
    获取车辆实时位置（模拟数据）
    """
    positions = []
    
    for vehicle_id, schedule in SCHEDULES.items():
        if schedule.status in ["in_progress"]:
            # 模拟当前位置（在路线上随机位置）
            if schedule.store_list:
                current_store_idx = np.random.randint(0, len(schedule.store_list))
                current_store = schedule.store_list[current_store_idx]
                if current_store in MOCK_STORES:
                    lat, lng = MOCK_STORES[current_store][1], MOCK_STORES[current_store][2]
                    # 添加随机偏移模拟移动
                    lat += np.random.normal(0, 0.005)
                    lng += np.random.normal(0, 0.005)
                    
                    positions.append({
                        "vehicle_id": vehicle_id,
                        "driver": schedule.driver_name,
                        "lat": lat,
                        "lng": lng,
                        "heading_to": current_store,
                        "eta_min": np.random.randint(5, 20),
                        "last_update": datetime.now().isoformat()
                    })
    
    return {
        "success": True,
        "data": {"positions": positions}
    }
