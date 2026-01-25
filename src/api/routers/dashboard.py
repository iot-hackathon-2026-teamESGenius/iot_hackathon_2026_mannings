"""
数据看板路由 - 适配前端首页数据概览
"""
from fastapi import APIRouter, Query
from typing import Optional
from datetime import datetime, date, timedelta
import numpy as np

router = APIRouter()

# ==================== API端点 ====================

@router.get("/kpi")
async def get_dashboard_kpi():
    """
    获取首页KPI指标卡片数据
    """
    return {
        "success": True,
        "data": {
            "sla_achievement_rate": {
                "value": 94.5,
                "unit": "%",
                "change": 2.3,
                "change_type": "increase",
                "trend": "up"
            },
            "today_orders": {
                "value": 1256,
                "unit": "单",
                "change": 128,
                "change_type": "increase",
                "trend": "up"
            },
            "stockout_rate": {
                "value": 2.8,
                "unit": "%",
                "change": -0.5,
                "change_type": "decrease",
                "trend": "down"  # 下降是好事
            },
            "delivery_delay_count": {
                "value": 15,
                "unit": "次",
                "change": -3,
                "change_type": "decrease",
                "trend": "down"
            },
            "pending_alerts": {
                "value": 8,
                "unit": "条",
                "change": 2,
                "change_type": "increase",
                "trend": "up",
                "alert_level": "warning"
            },
            "avg_pickup_time": {
                "value": 3.2,
                "unit": "小时",
                "change": -0.3,
                "change_type": "decrease",
                "trend": "down"
            }
        },
        "updated_at": datetime.now().isoformat()
    }

@router.get("/trend")
async def get_dashboard_trend(
    metric: str = Query("sla_rate", description="指标名称"),
    days: int = Query(7, ge=1, le=30, description="天数")
):
    """
    获取首页趋势图数据
    """
    trends = []
    
    for i in range(days):
        trend_date = date.today() - timedelta(days=days-1-i)
        
        if metric == "sla_rate":
            value = 92 + np.random.normal(2, 1)
        elif metric == "order_count":
            value = 1200 + np.random.normal(0, 100) + (50 if trend_date.weekday() >= 5 else 0)
        elif metric == "stockout_rate":
            value = 3 + np.random.normal(0, 0.5)
        else:
            value = np.random.random() * 100
        
        trends.append({
            "date": trend_date.isoformat(),
            "value": round(value, 2)
        })
    
    return {
        "success": True,
        "data": {
            "metric": metric,
            "trends": trends
        }
    }

@router.get("/alerts-summary")
async def get_alerts_summary():
    """
    获取首页预警摘要（实时预警区）
    """
    # 模拟未处理预警
    alerts = [
        {
            "alert_id": "ALT001",
            "risk_level": "critical",
            "title": "尖沙咀门店SLA即将违约",
            "description": "预计延迟45分钟，建议立即增派人手",
            "time": (datetime.now() - timedelta(minutes=15)).isoformat(),
            "action_url": "/sla/alerts?id=ALT001"
        },
        {
            "alert_id": "ALT002",
            "risk_level": "high",
            "title": "V001车辆配送延误",
            "description": "交通拥堵，影响3个门店配送",
            "time": (datetime.now() - timedelta(minutes=30)).isoformat(),
            "action_url": "/planning/routing?vehicle=V001"
        },
        {
            "alert_id": "ALT003",
            "risk_level": "medium",
            "title": "ECDC01库存预警",
            "description": "SKU003预计明日缺货",
            "time": (datetime.now() - timedelta(hours=1)).isoformat(),
            "action_url": "/forecast/inventory?ecdc=ECDC01"
        }
    ]
    
    return {
        "success": True,
        "data": {
            "alerts": alerts,
            "total_pending": 8,
            "critical_count": 1,
            "high_count": 2
        }
    }

@router.get("/announcements")
async def get_announcements():
    """
    获取系统公告
    """
    return {
        "success": True,
        "data": {
            "announcements": [
                {
                    "id": "ANN001",
                    "type": "info",
                    "title": "系统升级通知",
                    "content": "系统将于今晚23:00-24:00进行维护升级",
                    "time": "2026-01-25T10:00:00",
                    "is_read": False
                },
                {
                    "id": "ANN002",
                    "type": "success",
                    "title": "新功能上线",
                    "content": "车辆实时追踪功能已上线，请在调度页面查看",
                    "time": "2026-01-24T14:00:00",
                    "is_read": True
                }
            ]
        }
    }

@router.get("/quick-stats")
async def get_quick_stats():
    """
    获取快速统计数据（用于快捷入口显示）
    """
    return {
        "success": True,
        "data": {
            "replenishment": {
                "pending_count": 25,
                "urgent_count": 5,
                "label": "待审核补货"
            },
            "scheduling": {
                "today_routes": 12,
                "in_progress": 8,
                "label": "今日调度"
            },
            "alerts": {
                "pending_count": 8,
                "critical_count": 1,
                "label": "待处理预警"
            },
            "inventory": {
                "shortage_count": 15,
                "overstock_count": 8,
                "label": "库存异常"
            }
        }
    }

@router.get("/store-performance")
async def get_store_performance(
    top_n: int = Query(5, ge=1, le=20, description="显示门店数量")
):
    """
    获取门店绩效排名
    """
    stores = [
        {"store_id": "M003", "store_name": "Mannings Central", "sla_rate": 98.5, "order_count": 156},
        {"store_id": "M001", "store_name": "Mannings Tsim Sha Tsui", "sla_rate": 96.2, "order_count": 203},
        {"store_id": "M002", "store_name": "Mannings Causeway Bay", "sla_rate": 95.8, "order_count": 189},
        {"store_id": "M005", "store_name": "Mannings Sha Tin", "sla_rate": 93.1, "order_count": 134},
        {"store_id": "M004", "store_name": "Mannings Mongkok", "sla_rate": 91.5, "order_count": 167}
    ]
    
    return {
        "success": True,
        "data": {
            "rankings": stores[:top_n],
            "avg_sla_rate": 95.0
        }
    }
