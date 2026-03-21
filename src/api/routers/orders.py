"""
订单数据路由 - 真实DFI订单数据展示
"""
from fastapi import APIRouter, Query, HTTPException
from typing import Optional, List, Dict, Any
from datetime import datetime, date, timedelta
import logging
import numpy as np

logger = logging.getLogger(__name__)
router = APIRouter()


def safe_int(val):
    """安全转换为Python int"""
    try:
        return int(val) if val is not None else 0
    except:
        return 0


def safe_float(val):
    """安全转换为Python float"""
    try:
        return float(val) if val is not None else 0.0
    except:
        return 0.0


@router.get("/list")
async def get_orders(
    store_id: Optional[str] = Query(None, description="门店ID"),
    start_date: Optional[str] = Query(None, description="开始日期"),
    end_date: Optional[str] = Query(None, description="结束日期"),
    status: Optional[str] = Query(None, description="订单状态"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量")
):
    """
    获取订单列表 - 真实DFI数据
    """
    try:
        from src.api.services.data_service import get_data_service
        service = get_data_service()
        
        # 获取每日订单数据
        daily_orders = service.get_daily_orders(store_code=int(store_id) if store_id else None)
        
        if not daily_orders:
            return {
                "success": True,
                "data": {
                    "orders": [],
                    "total": 0,
                    "page": page,
                    "page_size": page_size
                }
            }
        
        # 转换格式
        orders = []
        for i, order in enumerate(daily_orders):
            order_date = order.get("dt", "") or order.get("order_date", "")
            # 日期筛选
            if start_date and order_date < start_date:
                continue
            if end_date and order_date > end_date:
                continue
            
            store_code = order.get("store_code")
            orders.append({
                "order_id": f"ORD-{order_date}-{store_code}",
                "order_date": order_date,
                "store_code": store_code,
                "store_name": order.get("store_name", f"门店{store_code}"),
                "district": order.get("district", ""),
                "total_orders": safe_int(order.get("order_count") or order.get("total_orders", 0)),
                "total_quantity": safe_int(order.get("total_quantity", 0)),
                "avg_quantity": safe_float(order.get("avg_sku_per_order") or order.get("avg_quantity_per_order", 0)),
                "status": "completed"  # 历史订单默认完成
            })
        
        # 分页
        total = len(orders)
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        paged_orders = orders[start_idx:end_idx]
        
        return {
            "success": True,
            "data": {
                "orders": paged_orders,
                "total": total,
                "page": page,
                "page_size": page_size,
                "total_pages": (total + page_size - 1) // page_size
            }
        }
    except Exception as e:
        logger.error(f"Failed to get orders: {e}")
        return {
            "success": False,
            "error": str(e),
            "data": {"orders": [], "total": 0}
        }


@router.get("/stats")
async def get_order_statistics(
    store_id: Optional[str] = Query(None, description="门店ID")
):
    """
    获取订单统计 - 真实DFI数据
    """
    try:
        from src.api.services.data_service import get_data_service
        service = get_data_service()
        
        stats = service.get_order_stats()
        sla = service.get_sla_analysis()
        
        # 获取门店排名
        store_stats = stats.get("store_stats", [])
        top_stores = sorted(store_stats, key=lambda x: safe_int(x.get("total_orders", 0)), reverse=True)[:10]
        
        total_orders = safe_int(stats.get("total_orders", 0))
        completed_orders = safe_int(sla.get("completed_orders", 0))
        
        return {
            "success": True,
            "data": {
                "total_orders": total_orders,
                "total_stores": safe_int(stats.get("total_stores", 0)),
                "total_quantity": safe_int(stats.get("total_quantity", 0)),
                "avg_orders_per_store": safe_float(stats.get("avg_orders_per_store", 0)),
                "completed_orders": completed_orders,
                "cancelled_orders": safe_int(sla.get("cancelled_orders", 0)),
                "completion_rate": round(completed_orders / max(total_orders, 1) * 100, 1),
                "date_range": stats.get("date_range", {}),
                "top_stores": [
                    {
                        "store_code": safe_int(s.get("store_code")),
                        "store_name": s.get("store_name", ""),
                        "total_orders": safe_int(s.get("total_orders", 0)),
                        "total_quantity": safe_int(s.get("total_quantity", 0))
                    }
                    for s in top_stores
                ]
            }
        }
    except Exception as e:
        logger.error(f"Failed to get order statistics: {e}")
        return {"success": False, "error": str(e)}


@router.get("/daily")
async def get_daily_orders(
    store_id: Optional[str] = Query(None, description="门店ID"),
    days: int = Query(30, ge=1, le=365, description="天数")
):
    """
    获取每日订单趋势 - 真实DFI数据
    """
    try:
        from src.api.services.data_service import get_data_service
        service = get_data_service()
        
        daily = service.get_daily_orders(store_id=int(store_id) if store_id else None)
        
        # 取最近N天
        if daily:
            daily = daily[-days:] if len(daily) > days else daily
        
        return {
            "success": True,
            "data": {
                "daily_orders": daily,
                "total_days": len(daily)
            }
        }
    except Exception as e:
        logger.error(f"Failed to get daily orders: {e}")
        return {"success": False, "error": str(e)}


@router.get("/store/{store_code}")
async def get_store_orders(store_code: int):
    """
    获取指定门店的订单历史
    """
    try:
        from src.api.services.data_service import get_data_service
        service = get_data_service()
        
        daily = service.get_daily_orders(store_code=store_code)
        
        # 计算门店统计
        total_orders = sum(d.get("total_orders", 0) for d in daily)
        total_quantity = sum(d.get("total_quantity", 0) for d in daily)
        
        return {
            "success": True,
            "data": {
                "store_code": store_code,
                "total_orders": total_orders,
                "total_quantity": total_quantity,
                "order_history": daily,
                "avg_daily_orders": round(total_orders / max(len(daily), 1), 1)
            }
        }
    except Exception as e:
        logger.error(f"Failed to get store orders: {e}")
        return {"success": False, "error": str(e)}


@router.get("/predict-replenishment")
async def predict_replenishment(
    store_id: Optional[str] = Query(None, description="门店ID"),
    days_ahead: int = Query(7, ge=1, le=30, description="预测天数")
):
    """
    基于真实订单预测生成补货建议
    """
    try:
        from src.api.services.data_service import get_data_service
        import numpy as np
        
        service = get_data_service()
        
        # 获取历史订单数据
        daily = service.get_daily_orders(store_id=int(store_id) if store_id else None)
        
        if not daily:
            return {
                "success": True,
                "data": {
                    "predictions": [],
                    "message": "无历史订单数据"
                }
            }
        
        # 计算平均需求和标准差
        orders = [d.get("total_orders", 0) for d in daily[-30:]]  # 最近30天
        quantities = [d.get("total_quantity", 0) for d in daily[-30:]]
        
        avg_orders = np.mean(orders) if orders else 0
        std_orders = np.std(orders) if orders else 0
        avg_qty = np.mean(quantities) if quantities else 0
        std_qty = np.std(quantities) if quantities else 0
        
        # 生成预测
        predictions = []
        for i in range(days_ahead):
            pred_date = date.today() + timedelta(days=i+1)
            # 考虑周末效应
            weekend_factor = 1.2 if pred_date.weekday() >= 5 else 1.0
            
            pred_orders = int(avg_orders * weekend_factor)
            pred_qty = int(avg_qty * weekend_factor)
            
            # 安全库存 (P90)
            safety_qty = int(pred_qty + 1.28 * std_qty)
            
            predictions.append({
                "date": pred_date.isoformat(),
                "weekday": ["周一", "周二", "周三", "周四", "周五", "周六", "周日"][pred_date.weekday()],
                "predicted_orders": pred_orders,
                "predicted_quantity": pred_qty,
                "safety_stock": safety_qty,
                "recommended_replenishment": safety_qty  # 建议补货量
            })
        
        return {
            "success": True,
            "data": {
                "store_id": store_id,
                "historical_avg_orders": round(avg_orders, 1),
                "historical_avg_quantity": round(avg_qty, 1),
                "predictions": predictions,
                "total_recommended": sum(p["recommended_replenishment"] for p in predictions)
            }
        }
    except Exception as e:
        logger.error(f"Failed to predict replenishment: {e}")
        return {"success": False, "error": str(e)}
