"""
预测服务路由 - 适配前端需求预测和库存展望页面
整合真实DFI门店数据
"""
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import Optional, List, Dict
from datetime import datetime, date, timedelta
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

from src.api.services.forecasting_service import get_forecasting_service

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
    factors: Optional[List[str]] = []  # 影响因素
    multiplier: Optional[float] = 1.0  # 调整系数

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

# ==================== 数据配置 ====================

# SKU数据 (暂无真实数据)
MOCK_SKUS = {
    "SKU001": "维他命C 1000mg",
    "SKU002": "感冒灵颗粒",
    "SKU003": "洗手液 500ml",
    "SKU004": "口罩 50片装",
    "SKU005": "消毒湿巾"
}

# ECDC数据 (暂无真实数据)
MOCK_ECDCS = {
    "ECDC01": "Kwai Chung DC",
    "ECDC02": "Tsuen Wan ECDC"
}

# 门店缓存
_stores_cache: Dict[str, str] = {}
_stores_cache_loaded: bool = False

def load_store_names() -> Dict[str, str]:
    """加载真实门店名称（带缓存）"""
    global _stores_cache, _stores_cache_loaded
    if _stores_cache_loaded:
        return _stores_cache
    
    try:
        from src.api.services.data_service import get_data_service
        service = get_data_service()
        stores = service.get_active_stores()  # 只获取活跃门店
        _stores_cache = {str(s["store_code"]): s["store_name"] for s in stores}
        _stores_cache_loaded = True
        logger.info(f"Loaded {len(_stores_cache)} stores for forecast")
        return _stores_cache
    except Exception as e:
        logger.warning(f"Failed to load stores, using fallback: {e}")
        _stores_cache_loaded = True  # 即使失败也标记已加载，避免重复尝试
        _stores_cache = {
            "10001": "Mannings Yau Tsim Mong",
            "10002": "Mannings Wan Chai",
            "10003": "Mannings Central and Western",
            "10004": "Mannings Kwun Tong",
            "10005": "Mannings Sha Tin"
        }
        return _stores_cache

def generate_demand_forecasts(
    start_date: date,
    end_date: date,
    store_ids: List[str] = None,
    sku_ids: List[str] = None
) -> List[DemandForecastItem]:
    """生成需求预测数据。"""
    service = get_forecasting_service()
    return [
        DemandForecastItem(**row)
        for row in service.get_demand_forecasts(start_date, end_date, store_ids, sku_ids)
    ]

def generate_inventory_outlook(
    forecast_days: int = 7,
    ecdc_ids: List[str] = None,
    sku_ids: List[str] = None,
) -> List[InventoryOutlookItem]:
    """生成ATP库存展望数据。"""
    service = get_forecasting_service()
    return [
        InventoryOutlookItem(**row)
        for row in service.get_inventory_outlook(forecast_days, ecdc_ids, sku_ids)
    ]

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
    
    # 获取真实门店名称
    store_names = load_store_names()
    
    return {
        "success": True,
        "data": {
            "store_id": store_id,
            "store_name": store_names.get(store_id, f"Store {store_id}"),
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
    sku_ids = [sku_id] if sku_id else None
    outlook = generate_inventory_outlook(forecast_days, ecdc_ids, sku_ids)
    
    # 筛选
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
    model_info = get_forecasting_service().get_model_info()
    return {
        "success": True,
        "data": {
            "model_name": "ProphetForecaster + MLSLAPredictor",
            "last_reference_date": model_info["demand_model"].get("config", {}).get("last_trained"),
            "training_samples": model_info.get("training_samples", 0),
            "features": model_info["demand_model"].get("feature_columns", []),
            "metrics": {
                "backend": model_info["demand_model"].get("backend"),
                "stores": model_info["demand_model"].get("store_count", 0),
            },
            "sla_model": model_info["sla_model"],
        }
    }
