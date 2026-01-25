"""
SLA服务路由 - 适配前端自提订单和风险预警页面
"""
from fastapi import APIRouter, HTTPException, Query, Depends
from pydantic import BaseModel
from typing import Optional, List, Dict
from datetime import datetime, date, timedelta
import numpy as np
import uuid

router = APIRouter()

# ==================== 请求/响应模型 ====================

class OrderSLAItem(BaseModel):
    """订单SLA条目"""
    order_id: str
    order_time: str
    store_id: str
    store_name: str
    sku_list: List[str]
    promised_ready_time: str
    estimated_ready_time: str
    actual_ready_time: Optional[str] = None
    status: str  # pending / ready / completed / cancelled
    sla_achieved: Optional[bool] = None
    delay_reason: Optional[str] = None
    customer_name: str  # 脱敏
    customer_phone: str  # 脱敏

class SLAAlertItem(BaseModel):
    """SLA预警条目"""
    alert_id: str
    alert_time: str
    risk_level: str  # low / medium / high / critical
    affected_entity: str
    entity_type: str  # store / ecdc / vehicle
    alert_description: str
    bottleneck_type: str  # ecdc / fleet / store
    status: str  # pending / processing / resolved
    handler: Optional[str] = None
    resolution: Optional[str] = None
    resolved_time: Optional[str] = None

class AlertUpdateRequest(BaseModel):
    """预警更新请求"""
    status: str
    handler: str
    resolution: Optional[str] = None

# ==================== 模拟数据 ====================

MOCK_STORES = {
    "M001": "Mannings Tsim Sha Tsui",
    "M002": "Mannings Causeway Bay",
    "M003": "Mannings Central",
    "M004": "Mannings Mongkok",
    "M005": "Mannings Sha Tin"
}

DELAY_REASONS = [
    "门店处理缓慢",
    "配送延误",
    "ECDC出货延迟",
    "需求激增",
    "人手不足",
    "交通拥堵"
]

# 模拟数据存储
ORDERS: Dict[str, OrderSLAItem] = {}
ALERTS: Dict[str, SLAAlertItem] = {}

def init_mock_orders():
    """初始化模拟订单数据"""
    global ORDERS
    
    for i in range(50):
        order_id = f"ORD{date.today().strftime('%Y%m%d')}{i:04d}"
        store_id = np.random.choice(list(MOCK_STORES.keys()))
        
        order_time = datetime.now() - timedelta(hours=np.random.randint(1, 48))
        promised_time = order_time + timedelta(hours=4)
        estimated_time = promised_time + timedelta(minutes=np.random.randint(-30, 60))
        
        # 部分订单已完成
        if np.random.random() < 0.4:
            status = "completed"
            actual_time = estimated_time + timedelta(minutes=np.random.randint(-15, 30))
            sla_achieved = actual_time <= promised_time
            delay_reason = np.random.choice(DELAY_REASONS) if not sla_achieved else None
        elif np.random.random() < 0.6:
            status = "ready"
            actual_time = estimated_time
            sla_achieved = actual_time <= promised_time
            delay_reason = None
        else:
            status = "pending"
            actual_time = None
            sla_achieved = None
            delay_reason = None
        
        ORDERS[order_id] = OrderSLAItem(
            order_id=order_id,
            order_time=order_time.isoformat(),
            store_id=store_id,
            store_name=MOCK_STORES[store_id],
            sku_list=[f"SKU{j:03d}" for j in np.random.choice(range(1, 20), size=np.random.randint(1, 5), replace=False)],
            promised_ready_time=promised_time.isoformat(),
            estimated_ready_time=estimated_time.isoformat(),
            actual_ready_time=actual_time.isoformat() if actual_time else None,
            status=status,
            sla_achieved=sla_achieved,
            delay_reason=delay_reason,
            customer_name=f"顾客{i+1:03d}",
            customer_phone=f"91XX-XX{i%100:02d}"
        )

def init_mock_alerts():
    """初始化模拟预警数据"""
    global ALERTS
    
    bottleneck_types = ["ecdc", "fleet", "store"]
    risk_levels = ["low", "medium", "high", "critical"]
    entity_types = ["store", "ecdc", "vehicle"]
    
    for i in range(30):
        alert_id = f"ALT{uuid.uuid4().hex[:8].upper()}"
        risk_level = np.random.choice(risk_levels, p=[0.3, 0.35, 0.25, 0.1])
        bottleneck = np.random.choice(bottleneck_types)
        entity_type = np.random.choice(entity_types)
        
        if entity_type == "store":
            affected = np.random.choice(list(MOCK_STORES.keys()))
        elif entity_type == "ecdc":
            affected = np.random.choice(["ECDC01", "ECDC02"])
        else:
            affected = f"V00{np.random.randint(1, 4)}"
        
        # 预警描述
        descriptions = {
            "ecdc": f"{affected} 出货能力不足，预计延迟2小时",
            "fleet": f"车辆 {affected} 配送延误，影响5个门店",
            "store": f"门店 {MOCK_STORES.get(affected, affected)} 处理积压，预计延迟1小时"
        }
        
        status = np.random.choice(["pending", "processing", "resolved"], p=[0.4, 0.3, 0.3])
        alert_time = datetime.now() - timedelta(hours=np.random.randint(0, 24))
        
        ALERTS[alert_id] = SLAAlertItem(
            alert_id=alert_id,
            alert_time=alert_time.isoformat(),
            risk_level=risk_level,
            affected_entity=affected,
            entity_type=entity_type,
            alert_description=descriptions[bottleneck],
            bottleneck_type=bottleneck,
            status=status,
            handler="物流主管" if status != "pending" else None,
            resolution="已增派人手" if status == "resolved" else None,
            resolved_time=(datetime.now() - timedelta(hours=np.random.randint(0, 12))).isoformat() if status == "resolved" else None
        )

# 初始化
init_mock_orders()
init_mock_alerts()

# ==================== 订单API ====================

@router.get("/orders")
async def get_orders(
    order_id: Optional[str] = Query(None, description="订单号精准搜索"),
    store_id: Optional[str] = Query(None, description="门店ID"),
    date_from: Optional[str] = Query(None, description="下单开始日期"),
    date_to: Optional[str] = Query(None, description="下单结束日期"),
    status: Optional[str] = Query(None, description="订单状态"),
    sla_achieved: Optional[bool] = Query(None, description="SLA是否达标"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100)
):
    """
    获取自提订单列表
    """
    orders = list(ORDERS.values())
    
    # 筛选
    if order_id:
        orders = [o for o in orders if order_id in o.order_id]
    if store_id:
        orders = [o for o in orders if o.store_id == store_id]
    if status:
        orders = [o for o in orders if o.status == status]
    if sla_achieved is not None:
        orders = [o for o in orders if o.sla_achieved == sla_achieved]
    
    # 分页
    total = len(orders)
    start_idx = (page - 1) * page_size
    page_data = orders[start_idx:start_idx + page_size]
    
    # 统计
    stats = {
        "total_orders": total,
        "pending": len([o for o in orders if o.status == "pending"]),
        "ready": len([o for o in orders if o.status == "ready"]),
        "completed": len([o for o in orders if o.status == "completed"]),
        "sla_achieved": len([o for o in orders if o.sla_achieved == True]),
        "sla_breached": len([o for o in orders if o.sla_achieved == False])
    }
    
    return {
        "success": True,
        "data": {
            "orders": [o.dict() for o in page_data],
            "statistics": stats,
            "pagination": {
                "total": total,
                "page": page,
                "page_size": page_size
            }
        }
    }

@router.get("/orders/{order_id}")
async def get_order_detail(order_id: str):
    """
    获取订单详情
    """
    if order_id not in ORDERS:
        raise HTTPException(status_code=404, detail="订单不存在")
    
    order = ORDERS[order_id]
    
    # 添加SLA分析
    analysis = None
    if order.sla_achieved == False:
        analysis = {
            "delay_minutes": 30,  # 模拟
            "primary_cause": order.delay_reason,
            "contributing_factors": ["高峰时段", "人手不足"]
        }
    
    return {
        "success": True,
        "data": {
            "order": order.dict(),
            "sla_analysis": analysis
        }
    }

@router.get("/pickup-promise")
async def get_pickup_promise(
    store_id: str = Query(..., description="门店ID"),
    sku_ids: str = Query(..., description="SKU列表，逗号分隔")
):
    """
    获取自提承诺时间窗口
    """
    store_name = MOCK_STORES.get(store_id, store_id)
    now = datetime.now()
    
    # 模拟承诺时间计算
    base_hours = 4
    # 周末加时
    if now.weekday() >= 5:
        base_hours += 1
    # 高峰时段加时
    if 12 <= now.hour <= 14 or 17 <= now.hour <= 19:
        base_hours += 0.5
    
    promised_time = now + timedelta(hours=base_hours)
    
    return {
        "success": True,
        "data": {
            "store_id": store_id,
            "store_name": store_name,
            "order_time": now.isoformat(),
            "promised_ready_time": promised_time.isoformat(),
            "confidence": 0.92,
            "risk_factors": [
                {"factor": "周末高峰", "impact_hours": 1.0} if now.weekday() >= 5 else None,
                {"factor": "用餐高峰", "impact_hours": 0.5} if 12 <= now.hour <= 14 else None
            ],
            "window_description": f"预计 {promised_time.strftime('%H:%M')} 前可取"
        }
    }

# ==================== 预警API ====================

@router.get("/alerts")
async def get_alerts(
    risk_level: Optional[str] = Query(None, description="风险等级"),
    status: Optional[str] = Query(None, description="处理状态"),
    bottleneck_type: Optional[str] = Query(None, description="瓶颈类型"),
    store_id: Optional[str] = Query(None, description="门店ID"),
    time_from: Optional[str] = Query(None, description="开始时间"),
    time_to: Optional[str] = Query(None, description="结束时间")
):
    """
    获取SLA预警列表
    """
    alerts = list(ALERTS.values())
    
    # 筛选
    if risk_level:
        alerts = [a for a in alerts if a.risk_level == risk_level]
    if status:
        alerts = [a for a in alerts if a.status == status]
    if bottleneck_type:
        alerts = [a for a in alerts if a.bottleneck_type == bottleneck_type]
    if store_id:
        alerts = [a for a in alerts if a.affected_entity == store_id]
    
    # 按时间和风险等级排序
    risk_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    alerts.sort(key=lambda x: (risk_order.get(x.risk_level, 4), x.alert_time), reverse=True)
    
    return {
        "success": True,
        "data": {
            "alerts": [a.dict() for a in alerts],
            "count": len(alerts)
        }
    }

@router.put("/alerts/{alert_id}")
async def update_alert(alert_id: str, request: AlertUpdateRequest):
    """
    更新预警处理状态
    """
    if alert_id not in ALERTS:
        raise HTTPException(status_code=404, detail="预警不存在")
    
    alert = ALERTS[alert_id]
    alert.status = request.status
    alert.handler = request.handler
    
    if request.resolution:
        alert.resolution = request.resolution
    
    if request.status == "resolved":
        alert.resolved_time = datetime.now().isoformat()
    
    return {
        "success": True,
        "message": "预警状态已更新",
        "data": alert.dict()
    }

@router.get("/bottleneck")
async def get_bottleneck_analysis(
    time_range: Optional[str] = Query("7d", description="时间范围: 1d/7d/30d")
):
    """
    获取瓶颈分析数据
    """
    alerts = list(ALERTS.values())
    
    # 瓶颈分布
    distribution = {
        "ecdc": len([a for a in alerts if a.bottleneck_type == "ecdc"]),
        "fleet": len([a for a in alerts if a.bottleneck_type == "fleet"]),
        "store": len([a for a in alerts if a.bottleneck_type == "store"])
    }
    total = sum(distribution.values()) or 1
    distribution_pct = {k: round(v/total*100, 1) for k, v in distribution.items()}
    
    # 风险等级分布
    risk_distribution = {
        "low": len([a for a in alerts if a.risk_level == "low"]),
        "medium": len([a for a in alerts if a.risk_level == "medium"]),
        "high": len([a for a in alerts if a.risk_level == "high"]),
        "critical": len([a for a in alerts if a.risk_level == "critical"])
    }
    
    # 趋势数据（模拟）
    trends = []
    for i in range(7):
        trend_date = date.today() - timedelta(days=6-i)
        trends.append({
            "date": trend_date.isoformat(),
            "ecdc": np.random.randint(2, 10),
            "fleet": np.random.randint(3, 12),
            "store": np.random.randint(1, 8)
        })
    
    return {
        "success": True,
        "data": {
            "distribution": distribution,
            "distribution_percentage": distribution_pct,
            "risk_distribution": risk_distribution,
            "trends": trends,
            "top_issues": [
                {"issue": "门店高峰处理延迟", "count": 15, "affected_stores": 8},
                {"issue": "配送车辆调度延误", "count": 12, "affected_routes": 5},
                {"issue": "ECDC出货能力不足", "count": 8, "affected_ecdcs": 2}
            ]
        }
    }

@router.get("/statistics")
async def get_sla_statistics(
    time_range: Optional[str] = Query("7d", description="时间范围")
):
    """
    获取SLA统计数据
    """
    orders = list(ORDERS.values())
    alerts = list(ALERTS.values())
    
    completed = [o for o in orders if o.status == "completed"]
    achieved = [o for o in completed if o.sla_achieved == True]
    
    resolved = [a for a in alerts if a.status == "resolved"]
    
    return {
        "success": True,
        "data": {
            "orders": {
                "total": len(orders),
                "completed": len(completed),
                "sla_achievement_rate": round(len(achieved)/len(completed)*100, 1) if completed else 0
            },
            "alerts": {
                "total": len(alerts),
                "pending": len([a for a in alerts if a.status == "pending"]),
                "processing": len([a for a in alerts if a.status == "processing"]),
                "resolved": len(resolved),
                "resolution_rate": round(len(resolved)/len(alerts)*100, 1) if alerts else 0,
                "avg_resolution_time_min": 45  # 模拟
            }
        }
    }
