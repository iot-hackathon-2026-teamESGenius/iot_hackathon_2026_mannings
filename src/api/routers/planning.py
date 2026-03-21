"""
决策规划路由 - 适配前端补货计划和车队调度页面
整合真实DFI门店数据
"""
from fastapi import APIRouter, HTTPException, Query, Depends, Body
from pydantic import BaseModel
from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime, date, timedelta
import numpy as np
import uuid
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

# ==================== 香港18区中心点坐标 (用于无坐标门店的fallback) ====================
HK_DISTRICT_CENTERS: Dict[str, Tuple[float, float]] = {
    "Central and Western": (22.2860, 114.1510),
    "Central & Western": (22.2860, 114.1510),
    "Wan Chai": (22.2780, 114.1710),
    "Eastern": (22.2840, 114.2240),
    "Southern": (22.2470, 114.1580),
    "Yau Tsim Mong": (22.3120, 114.1720),
    "Sham Shui Po": (22.3310, 114.1620),
    "Kowloon City": (22.3280, 114.1910),
    "Wong Tai Sin": (22.3420, 114.1950),
    "Kwun Tong": (22.3130, 114.2260),
    "Tsuen Wan": (22.3710, 114.1140),
    "Tuen Mun": (22.3910, 113.9770),
    "Yuen Long": (22.4450, 114.0220),
    "North": (22.4940, 114.1380),
    "Tai Po": (22.4510, 114.1640),
    "Sha Tin": (22.3870, 114.1950),
    "Sai Kung": (22.3830, 114.2700),
    "Kwai Tsing": (22.3560, 114.1300),
    "Islands": (22.2610, 113.9460),
}

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

# ==================== 数据配置 ====================

# 配送中心和ECDC (暂无真实数据，保留配置)
MOCK_DCS = {"DC01": "主配送中心"}
MOCK_ECDCS = {"ECDC01": "葵涌电商中心", "ECDC02": "荃湾电商中心"}

# SKU数据 (暂无真实数据，保留配置)
MOCK_SKUS = {
    "SKU001": "维他命C 1000mg",
    "SKU002": "感冒灵颗粒",
    "SKU003": "洗手液 500ml",
    "SKU004": "口罩 50片装",
    "SKU005": "消毒湿巾"
}

# 车辆数据 (暂无真实数据，保留配置)
MOCK_VEHICLES = {
    "V001": {"driver": "陈大文", "phone": "9123****"},
    "V002": {"driver": "李小明", "phone": "9456****"},
    "V003": {"driver": "王志强", "phone": "9789****"}
}

# 门店数据缓存
_stores_cache: Dict[str, Dict] = {}
_stores_cache_time: datetime = None

def get_store_coordinates(district: str) -> Tuple[float, float]:
    """获取区域中心点坐标作为门店坐标"""
    # 尝试精确匹配
    if district in HK_DISTRICT_CENTERS:
        return HK_DISTRICT_CENTERS[district]
    
    # 尝试模糊匹配
    district_lower = district.lower()
    for key, coords in HK_DISTRICT_CENTERS.items():
        if key.lower() in district_lower or district_lower in key.lower():
            return coords
    
    # 默认返回香港中心
    return (22.3193, 114.1694)

def load_real_stores() -> Dict[str, Dict]:
    """
    加载真实门店数据
    返回格式: {store_id: {"name": ..., "lat": ..., "lng": ..., "district": ...}}
    """
    global _stores_cache, _stores_cache_time
    
    # 5分钟缓存
    if _stores_cache and _stores_cache_time:
        if (datetime.now() - _stores_cache_time).seconds < 300:
            return _stores_cache
    
    try:
        from src.api.services.data_service import get_data_service
        service = get_data_service()
        stores = service.get_active_stores()  # 只获取有订单的活跃门店
        
        store_dict = {}
        for store in stores:
            store_id = str(store["store_code"])
            lat = store.get("latitude")
            lng = store.get("longitude")
            
            # 如果没有坐标，使用区域中心点
            if lat is None or lng is None:
                district = store.get("district", "")
                lat, lng = get_store_coordinates(district)
            
            store_dict[store_id] = {
                "name": store.get("store_name", f"Mannings {store_id}"),
                "lat": lat,
                "lng": lng,
                "district": store.get("district", "Unknown"),
                "address": store.get("address", "")
            }
        
        _stores_cache = store_dict
        _stores_cache_time = datetime.now()
        logger.info(f"Loaded {len(store_dict)} real stores for routing")
        return store_dict
        
    except Exception as e:
        logger.warning(f"Failed to load real stores, using fallback: {e}")
        # Fallback到硬编码数据
        return {
            "10001": {"name": "Mannings Tsim Sha Tsui", "lat": 22.2988, "lng": 114.1722, "district": "Yau Tsim Mong"},
            "10002": {"name": "Mannings Causeway Bay", "lat": 22.2800, "lng": 114.1830, "district": "Wan Chai"},
            "10003": {"name": "Mannings Central", "lat": 22.2820, "lng": 114.1580, "district": "Central and Western"},
            "10004": {"name": "Mannings Mongkok", "lat": 22.3193, "lng": 114.1694, "district": "Yau Tsim Mong"},
            "10005": {"name": "Mannings Sha Tin", "lat": 22.3817, "lng": 114.1877, "district": "Sha Tin"},
        }

def get_stores_for_routing() -> Dict[str, Tuple[str, float, float]]:
    """
    获取用于路径规划的门店数据
    返回格式兼容原有MOCK_STORES: {store_id: (name, lat, lng)}
    """
    stores = load_real_stores()
    return {
        store_id: (info["name"], info["lat"], info["lng"])
        for store_id, info in stores.items()
    }

# 模拟数据存储
REPLENISHMENT_PLANS: Dict[str, ReplenishmentPlanItem] = {}
SCHEDULES: Dict[str, ScheduleItem] = {}

def init_mock_data():
    """初始化补货计划 - 基于真实订单预测"""
    global REPLENISHMENT_PLANS, SCHEDULES
    
    # 获取真实门店数据
    stores = load_real_stores()
    store_ids = list(stores.keys())[:10]  # 取前10家门店用于演示
    
    # 尝试从真实订单数据生成补货计划
    try:
        from src.api.services.data_service import get_data_service
        service = get_data_service()
        
        # 获取历史订单数据
        daily_orders = service.get_daily_orders()
        
        if daily_orders and len(daily_orders) > 7:
            # 计算最近7天的平均需求
            recent = daily_orders[-7:]
            total_qty = sum(d.get("total_quantity", 0) for d in recent)
            avg_daily_qty = total_qty / len(recent)
            
            # 基于真实需求生成补货计划
            for ecdc_id, ecdc_name in MOCK_ECDCS.items():
                for sku_id, sku_name in MOCK_SKUS.items():
                    plan_id = f"REP-{ecdc_id}-{sku_id}-{date.today().isoformat()}"
                    
                    # 基于真实需求计算建议补货量
                    base_demand = avg_daily_qty / (len(MOCK_ECDCS) * len(MOCK_SKUS))
                    # 添加安全库存 (1.5倍 + 随机波动)
                    recommended = int(base_demand * 1.5 * (0.8 + np.random.random() * 0.4))
                    recommended = max(20, min(500, recommended))  # 限制在合理范围
                    
                    is_feasible = recommended < 300  # 超过300认为不可行
                    
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
            
            logger.info(f"补货计划已基于真实订单数据生成，历史日均需求: {avg_daily_qty:.0f}")
        else:
            # 回退到模拟数据
            raise Exception("历史订单数据不足")
            
    except Exception as e:
        logger.warning(f"无法使用真实订单数据生成补货计划: {e}，使用模拟数据")
        
        # 生成模拟补货计划
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
    
    # 生成调度计划 - 使用真实门店
    if len(store_ids) >= 5:
        routes = [
            (store_ids[0:3], "08:00", "08:00-10:00"),
            (store_ids[3:5], "09:00", "09:00-11:00"),
            (store_ids[0:2] + store_ids[4:5], "14:00", "14:00-16:00")
        ]
    else:
        routes = [(store_ids, "08:00", "08:00-10:00")]
    
    for i, (route_stores, dep_time, window) in enumerate(routes):
        vehicle_id = f"V00{i+1}"
        vehicle = MOCK_VEHICLES.get(vehicle_id, {"driver": f"司机{i+1}", "phone": "9XXX****"})
        
        SCHEDULES[vehicle_id] = ScheduleItem(
            vehicle_id=vehicle_id,
            driver_name=vehicle["driver"],
            driver_phone=vehicle["phone"],
            departure_time=dep_time,
            departure_window=window,
            store_list=route_stores,
            store_names=[stores[s]["name"] for s in route_stores if s in stores],
            estimated_duration_min=60 + len(route_stores) * 20,
            estimated_cost=100 + len(route_stores) * 25,
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
    使用真实门店数据
    """
    # DC位置 (葵涌配送中心)
    dc_location = (22.3700, 114.1130)
    
    # 加载真实门店数据
    stores = load_real_stores()
    
    # 门店位置
    store_locations = {
        store_id: {"name": info["name"], "lat": info["lat"], "lng": info["lng"], "district": info["district"]}
        for store_id, info in stores.items()
    }
    
    # 路线数据
    routes = []
    for schedule in SCHEDULES.values():
        route_coords = [dc_location]
        for store_id in schedule.store_list:
            if store_id in stores:
                route_coords.append((stores[store_id]["lat"], stores[store_id]["lng"]))
        
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
    for store_id, info in stores.items():
        geojson["features"].append({
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": [info["lng"], info["lat"]]},
            "properties": {"type": "store", "id": store_id, "name": info["name"], "district": info["district"]}
        })
    
    return {
        "success": True,
        "data": {
            "dc_location": {"lat": dc_location[0], "lng": dc_location[1]},
            "store_locations": store_locations,
            "routes": routes,
            "geojson": geojson,
            "total_stores": len(stores)
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
    
    # 获取真实门店数据
    stores = load_real_stores()
    
    # 应用调整
    if request.store_list:
        schedule.store_list = request.store_list
        schedule.store_names = [stores[s]["name"] for s in request.store_list if s in stores]
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
    获取车辆实时位置（基于真实门店位置模拟）
    """
    # 获取真实门店数据
    stores = load_real_stores()
    positions = []
    
    for vehicle_id, schedule in SCHEDULES.items():
        if schedule.status in ["in_progress"]:
            # 模拟当前位置（在路线上随机位置）
            if schedule.store_list:
                current_store_idx = np.random.randint(0, len(schedule.store_list))
                current_store = schedule.store_list[current_store_idx]
                if current_store in stores:
                    lat = stores[current_store]["lat"]
                    lng = stores[current_store]["lng"]
                    # 添加随机偏移模拟移动
                    lat += np.random.normal(0, 0.005)
                    lng += np.random.normal(0, 0.005)
                    
                    positions.append({
                        "vehicle_id": vehicle_id,
                        "driver": schedule.driver_name,
                        "lat": lat,
                        "lng": lng,
                        "heading_to": current_store,
                        "heading_to_name": stores[current_store]["name"],
                        "eta_min": np.random.randint(5, 20),
                        "last_update": datetime.now().isoformat()
                    })
    
    return {
        "success": True,
        "data": {"positions": positions}
    }


# ==================== 门店列表API (新增) ====================

@router.get("/stores")
async def get_available_stores():
    """
    获取可用于路径规划的门店列表
    """
    stores = load_real_stores()
    
    store_list = [
        {
            "store_id": store_id,
            "name": info["name"],
            "district": info["district"],
            "lat": info["lat"],
            "lng": info["lng"]
        }
        for store_id, info in stores.items()
    ]
    
    # 按区域分组
    by_district = {}
    for store in store_list:
        district = store["district"]
        if district not in by_district:
            by_district[district] = []
        by_district[district].append(store)
    
    return {
        "success": True,
        "data": {
            "stores": store_list,
            "total": len(store_list),
            "by_district": by_district
        }
    }
