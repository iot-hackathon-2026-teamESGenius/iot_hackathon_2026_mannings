"""
预测服务路由 - 适配前端需求预测和库存展望页面
"""
from fastapi import APIRouter, HTTPException, Query, Depends
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime, date, timedelta
import numpy as np
import pandas as pd

router = APIRouter()

# ==================== 请求/响应模型 ====================

class DemandForecastItem(BaseModel):
    """需求预测条目"""
    store_id: str
    store_name: str
    sku_id: str
    sku_name: str
    date: str
    time_slot: Optional[str] = None
    forecast_demand: float
    actual_demand: Optional[float] = None
    deviation_rate: Optional[float] = None
    lower_bound: float
    upper_bound: float

class InventoryOutlookItem(BaseModel):
    """库存展望条目"""
    ecdc_id: str
    ecdc_name: str
    sku_id: str
    sku_name: str
    forecast_date: str
    current_stock: float
    expected_arrival: float
    committed_demand: float
    projected_available: float
    stock_status: str  # normal / shortage / overstock

# ==================== 模拟数据生成 ====================

MOCK_STORES = {
    "M001": "Mannings Tsim Sha Tsui",
    "M002": "Mannings Causeway Bay",
    "M003": "Mannings Central",
    "M004": "Mannings Mongkok",
    "M005": "Mannings Sha Tin"
}

MOCK_SKUS = {
    "SKU001": "维他命C 1000mg",
    "SKU002": "感冒灵颗粒",
    "SKU003": "洗手液 500ml",
    "SKU004": "口罩 50片装",
    "SKU005": "消毒湿巾"
}

MOCK_ECDCS = {
    "ECDC01": "Kwai Chung DC",
    "ECDC02": "Tsuen Wan ECDC"
}

def generate_demand_forecasts(
    start_date: date,
    end_date: date,
    store_ids: List[str] = None,
    sku_ids: List[str] = None
) -> List[DemandForecastItem]:
    """生成模拟需求预测数据"""
    results = []
    stores = store_ids or list(MOCK_STORES.keys())
    skus = sku_ids or list(MOCK_SKUS.keys())
    
    current = start_date
    while current <= end_date:
        for store_id in stores:
            for sku_id in skus:
                # 基础需求 + 周末效应 + 随机波动
                base_demand = 50 + np.random.normal(0, 10)
                weekend_effect = 20 if current.weekday() >= 5 else 0
                forecast = max(0, base_demand + weekend_effect + np.random.normal(0, 5))
                
                # 模拟实际需求（仅历史日期）
                actual = None
                deviation = None
                if current < date.today():
                    actual = forecast + np.random.normal(0, forecast * 0.1)
                    deviation = (actual - forecast) / forecast * 100 if forecast > 0 else 0
                
                results.append(DemandForecastItem(
                    store_id=store_id,
                    store_name=MOCK_STORES.get(store_id, store_id),
                    sku_id=sku_id,
                    sku_name=MOCK_SKUS.get(sku_id, sku_id),
                    date=current.isoformat(),
                    forecast_demand=round(forecast, 1),
                    actual_demand=round(actual, 1) if actual else None,
                    deviation_rate=round(deviation, 2) if deviation else None,
                    lower_bound=round(forecast * 0.8, 1),
                    upper_bound=round(forecast * 1.2, 1)
                ))
        current += timedelta(days=1)
    
    return results

def generate_inventory_outlook(
    forecast_days: int = 7,
    ecdc_ids: List[str] = None
) -> List[InventoryOutlookItem]:
    """生成模拟库存展望数据"""
    results = []
    ecdcs = ecdc_ids or list(MOCK_ECDCS.keys())
    
    for ecdc_id in ecdcs:
        for sku_id, sku_name in MOCK_SKUS.items():
            for day_offset in range(forecast_days):
                forecast_date = date.today() + timedelta(days=day_offset)
                
                current_stock = np.random.randint(50, 200)
                expected_arrival = np.random.randint(0, 50) if day_offset > 0 else 0
                committed_demand = np.random.randint(30, 80)
                projected = current_stock + expected_arrival - committed_demand
                
                # 判断库存状态
                if projected < 20:
                    status = "shortage"
                elif projected > 150:
                    status = "overstock"
                else:
                    status = "normal"
                
                results.append(InventoryOutlookItem(
                    ecdc_id=ecdc_id,
                    ecdc_name=MOCK_ECDCS.get(ecdc_id, ecdc_id),
                    sku_id=sku_id,
                    sku_name=sku_name,
                    forecast_date=forecast_date.isoformat(),
                    current_stock=current_stock,
                    expected_arrival=expected_arrival,
                    committed_demand=committed_demand,
                    projected_available=max(0, projected),
                    stock_status=status
                ))
    
    return results

# ==================== API端点 ====================

@router.get("/demand")
async def get_demand_forecast(
    start_date: str = Query(..., description="开始日期 (YYYY-MM-DD)"),
    end_date: str = Query(..., description="结束日期 (YYYY-MM-DD)"),
    store_ids: Optional[str] = Query(None, description="门店ID列表，逗号分隔"),
    sku_ids: Optional[str] = Query(None, description="SKU ID列表，逗号分隔"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(50, ge=1, le=200, description="每页数量")
):
    """
    获取需求预测数据
    
    - **start_date**: 开始日期
    - **end_date**: 结束日期
    - **store_ids**: 门店ID筛选（可选，逗号分隔）
    - **sku_ids**: SKU ID筛选（可选，逗号分隔）
    """
    try:
        start = datetime.strptime(start_date, "%Y-%m-%d").date()
        end = datetime.strptime(end_date, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(status_code=400, detail="日期格式错误，请使用 YYYY-MM-DD")
    
    stores = store_ids.split(",") if store_ids else None
    skus = sku_ids.split(",") if sku_ids else None
    
    forecasts = generate_demand_forecasts(start, end, stores, skus)
    
    # 分页
    total = len(forecasts)
    start_idx = (page - 1) * page_size
    end_idx = start_idx + page_size
    page_data = forecasts[start_idx:end_idx]
    
    return {
        "success": True,
        "data": {
            "forecasts": [f.dict() for f in page_data],
            "pagination": {
                "total": total,
                "page": page,
                "page_size": page_size,
                "total_pages": (total + page_size - 1) // page_size
            }
        }
    }

@router.get("/demand/trend")
async def get_demand_trend(
    store_id: str = Query(..., description="门店ID"),
    days: int = Query(7, ge=1, le=30, description="天数")
):
    """
    获取需求趋势数据（用于图表展示）
    """
    start = date.today() - timedelta(days=days)
    end = date.today() + timedelta(days=7)  # 包含未来7天预测
    
    forecasts = generate_demand_forecasts(start, end, [store_id])
    
    # 按日期聚合
    trend_data = {}
    for f in forecasts:
        if f.date not in trend_data:
            trend_data[f.date] = {"date": f.date, "forecast": 0, "actual": 0}
        trend_data[f.date]["forecast"] += f.forecast_demand
        if f.actual_demand:
            trend_data[f.date]["actual"] += f.actual_demand
    
    return {
        "success": True,
        "data": {
            "store_id": store_id,
            "store_name": MOCK_STORES.get(store_id, store_id),
            "trend": list(trend_data.values())
        }
    }

@router.get("/inventory")
async def get_inventory_outlook(
    ecdc_id: Optional[str] = Query(None, description="ECDC ID"),
    sku_id: Optional[str] = Query(None, description="SKU ID"),
    status: Optional[str] = Query(None, description="库存状态 (normal/shortage/overstock)"),
    forecast_days: int = Query(7, ge=1, le=14, description="预测天数")
):
    """
    获取可售库存展望数据
    """
    ecdc_ids = [ecdc_id] if ecdc_id else None
    outlook = generate_inventory_outlook(forecast_days, ecdc_ids)
    
    # 筛选
    if sku_id:
        outlook = [o for o in outlook if o.sku_id == sku_id]
    if status:
        outlook = [o for o in outlook if o.stock_status == status]
    
    # 统计
    stats = {
        "total_items": len(outlook),
        "shortage_count": len([o for o in outlook if o.stock_status == "shortage"]),
        "overstock_count": len([o for o in outlook if o.stock_status == "overstock"]),
        "normal_count": len([o for o in outlook if o.stock_status == "normal"])
    }
    
    return {
        "success": True,
        "data": {
            "outlook": [o.dict() for o in outlook],
            "statistics": stats
        }
    }

@router.get("/model-info")
async def get_forecast_model_info():
    """
    获取预测模型信息
    """
    return {
        "success": True,
        "data": {
            "model_name": "Prophet + LightGBM Ensemble",
            "last_trained": "2026-01-24T10:00:00",
            "training_samples": 50000,
            "features": [
                "historical_sales", "day_of_week", "is_weekend",
                "is_holiday", "weather_condition", "promotion_flag",
                "store_type", "sku_category"
            ],
            "metrics": {
                "mape": 8.5,
                "rmse": 12.3,
                "r2": 0.92
            }
        }
    }
