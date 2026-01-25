"""
决策规划路由 - 适配前端补货计划和车队调度页面
"""
from fastapi import APIRouter, HTTPException, Query, Depends, Body
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime, date, timedelta
import numpy as np
import uuid

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
