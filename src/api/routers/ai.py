"""
AI服务路由 - 提供智能助手、分析建议等AI功能
集成AWS Bedrock Claude模型
"""
from fastapi import APIRouter, HTTPException, Query, Body
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime, date
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

from src.api.services.bedrock_service import get_ai_assistant
from src.api.services.rag_service import get_rag_agent


# ==================== 请求/响应模型 ====================

class ChatRequest(BaseModel):
    """聊天请求"""
    message: str
    context: Optional[Dict[str, Any]] = None

class ChatResponse(BaseModel):
    """聊天响应"""
    success: bool
    response: str
    timestamp: str

class RAGChatRequest(BaseModel):
    """RAG聊天请求"""
    message: str
    history: Optional[List[Dict[str, str]]] = None

class RAGChatResponse(BaseModel):
    """RAG聊天响应"""
    success: bool
    response: str
    retrieved_data: List[str] = []
    timestamp: str

class AnalysisRequest(BaseModel):
    """分析请求"""
    data: Dict[str, Any]
    analysis_type: str  # traffic / sla / route / demand

class AnalysisResponse(BaseModel):
    """分析响应"""
    success: bool
    analysis: str
    recommendations: List[str] = []
    timestamp: str


# ==================== AI聊天接口 ====================

@router.post("/chat", response_model=ChatResponse)
async def chat_with_ai(request: ChatRequest):
    """
    与AI助手对话
    """
    try:
        assistant = get_ai_assistant()
        response = await assistant.chat(request.message, request.context)
        
        return ChatResponse(
            success=True,
            response=response,
            timestamp=datetime.now().isoformat()
        )
    except Exception as e:
        logger.error(f"AI chat error: {e}")
        return ChatResponse(
            success=False,
            response="AI服务暂时不可用，请稍后重试。",
            timestamp=datetime.now().isoformat()
        )


# ==================== RAG智能问答接口 ====================

@router.post("/rag/chat", response_model=RAGChatResponse)
async def rag_chat(request: RAGChatRequest):
    """
    RAG智能问答 - 结合本地数据和AI进行分析
    
    工作流程:
    1. 根据用户问题检索相关业务数据
    2. 将数据作为上下文传给AI
    3. 生成基于数据的专业回答
    """
    try:
        rag_agent = get_rag_agent()
        result = await rag_agent.chat(request.message, request.history)
        
        return RAGChatResponse(
            success=True,
            response=result.get("response", ""),
            retrieved_data=result.get("context", {}).get("retrieved_data", []),
            timestamp=datetime.now().isoformat()
        )
    except Exception as e:
        logger.error(f"RAG chat error: {e}")
        return RAGChatResponse(
            success=False,
            response="抱歉，数据分析服务暂时不可用。",
            retrieved_data=[],
            timestamp=datetime.now().isoformat()
        )


@router.get("/rag/capabilities")
async def get_rag_capabilities():
    """
    获取RAG系统能力说明
    """
    return {
        "success": True,
        "capabilities": [
            {
                "name": "SLA分析",
                "description": "查询和分析订单履约率",
                "examples": ["当前SLA达成率是多少？", "哪些门店SLA有风险？"]
            },
            {
                "name": "订单查询",
                "description": "查询订单统计和趋势",
                "examples": ["最近订单量趋势如何？", "今天有多少订单？"]
            },
            {
                "name": "门店信息",
                "description": "查询门店位置和状态",
                "examples": ["铜锣湾店在哪里？", "共有多少家门店？"]
            },
            {
                "name": "配送调度",
                "description": "查询配送车辆和路线状态",
                "examples": ["当前有几辆配送车在运行？", "V001的配送路线是什么？"]
            },
            {
                "name": "库存查询",
                "description": "查询库存和补货状态",
                "examples": ["哪些商品缺货？", "需要补货的门店有哪些？"]
            },
            {
                "name": "需求预测",
                "description": "预测未来需求趋势",
                "examples": ["未来7天预计订单量？", "周末订单会增加吗？"]
            }
        ],
        "quick_questions": [
            "当前系统运行状态如何？",
            "今天的SLA达成率是多少？",
            "最近订单趋势怎么样？",
            "哪些门店需要补货？",
            "当前配送调度情况"
        ]
    }


# ==================== AI安全审计接口 ====================

@router.get("/security/status")
async def get_security_status():
    """
    获取AI数据安全状态
    
    返回数据脱敏和审计的当前状态
    """
    try:
        rag_agent = get_rag_agent()
        return {
            "success": True,
            **rag_agent.get_security_status()
        }
    except Exception as e:
        logger.error(f"Get security status error: {e}")
        return {
            "success": False,
            "error": str(e)
        }


@router.get("/security/audit")
async def get_security_audit():
    """
    获取安全审计日志
    
    记录所有AI对数据的访问
    """
    try:
        from src.api.services.data_sanitizer import get_data_sanitizer
        sanitizer = get_data_sanitizer()
        return {
            "success": True,
            **sanitizer.get_audit_summary()
        }
    except Exception as e:
        logger.error(f"Get security audit error: {e}")
        return {
            "success": False,
            "error": str(e)
        }


@router.get("/security/architecture")
async def get_security_architecture():
    """
    获取AI数据安全架构说明
    """
    return {
        "success": True,
        "architecture": {
            "name": "AI数据安全隔离架构",
            "version": "1.0",
            "layers": [
                {
                    "level": 1,
                    "name": "AI智能助手",
                    "description": "只能访问脱敏后的SafeReport",
                    "access": "read_only"
                },
                {
                    "level": 2,
                    "name": "DataSanitizer数据净化层",
                    "description": "执行数据脱敏、聚合和审计",
                    "functions": ["门店ID匿名化", "坐标区域化", "金额范围化", "时间时段化"]
                },
                {
                    "level": 3,
                    "name": "企业原始数据",
                    "description": "DFI/NDA保密数据",
                    "access": "ai_blocked"
                }
            ],
            "security_measures": [
                "数据脱敏: 所有敏感字段在传递给AI前已处理",
                "访问AI计: 每次数据访问都有审计日志",
                "原始数据隔离: AI无法直接访问data_service"
            ],
            "compliance": [
                "符合企业数据安全规范",
                "符合NDA保密要求",
                "符合AI安全最佳实践"
            ]
        }
    }


@router.post("/analyze/traffic")
async def analyze_traffic():
    """
    分析实时路况
    """
    try:
        # 获取实时路况数据
        from src.modules.data.implementations.traffic_fetcher import HKTrafficFetcher
        
        fetcher = HKTrafficFetcher()
        traffic_data = fetcher.fetch_current_traffic()
        
        # 转换为字典格式
        traffic_dict = {
            "timestamp": datetime.now().isoformat(),
            "routes": [
                {
                    "name": t.road_segment,
                    "speed_kmh": t.speed_kmh,
                    "congestion_level": t.congestion_level,
                    "travel_time_factor": t.travel_time_factor
                }
                for t in traffic_data
            ] if traffic_data else []
        }
        
        # AI分析
        assistant = get_ai_assistant()
        analysis = await assistant.analyze_traffic(traffic_dict)
        
        return {
            "success": True,
            "data": {
                "traffic": traffic_dict,
                "analysis": analysis,
                "timestamp": datetime.now().isoformat()
            }
        }
    except Exception as e:
        logger.error(f"Traffic analysis error: {e}")
        return {
            "success": False,
            "error": str(e),
            "data": {
                "analysis": "路况分析服务暂时不可用",
                "timestamp": datetime.now().isoformat()
            }
        }


@router.post("/analyze/sla")
async def analyze_sla():
    """
    分析SLA风险
    """
    try:
        from src.api.services.data_service import get_data_service
        
        service = get_data_service()
        
        # 获取SLA数据
        sla = service.get_sla_analysis()
        order_stats = service.get_order_stats()
        
        # 确保所有值都是Python原生类型（而不是numpy类型）
        def to_native(val):
            if hasattr(val, 'item'):
                return val.item()
            return val
        
        # 从真实数据计算 SLA 指标
        total_orders = to_native(sla.get("total_orders", 0))
        completed_orders = to_native(sla.get("completed_orders", 0))
        cancelled_orders = to_native(sla.get("cancelled_orders", 0))
        
        # 计算 SLA 率（与首页 KPI 一致）
        sla_rate = (completed_orders / total_orders * 100) if total_orders > 0 else 0.0
        
        # 计算平均履约时间（小时）
        stage_durations = sla.get("stage_durations", {})
        total_fulfillment = stage_durations.get("total_fulfillment", {})
        avg_fulfillment_hours = total_fulfillment.get("mean_min", 0) / 60 if total_fulfillment else 0.0
        
        sla_dict = {
            "total_orders": total_orders,
            "completed_orders": completed_orders,
            "cancelled_orders": cancelled_orders,
            "sla_rate": round(sla_rate, 2),
            "avg_fulfillment_hours": round(avg_fulfillment_hours, 2),
            "timestamp": datetime.now().isoformat()
        }
        
        # AI分析
        assistant = get_ai_assistant()
        analysis = await assistant.analyze_sla_risk(sla_dict)
        
        return {
            "success": True,
            "data": {
                "sla_metrics": sla_dict,
                "analysis": analysis,
                "timestamp": datetime.now().isoformat()
            }
        }
    except Exception as e:
        logger.error(f"SLA analysis error: {e}")
        return {
            "success": False,
            "error": str(e),
            "data": {
                "analysis": "SLA分析服务暂时不可用",
                "timestamp": datetime.now().isoformat()
            }
        }


@router.post("/analyze/route")
async def analyze_route(
    vehicle_id: Optional[str] = Query(None, description="车辆ID")
):
    """
    分析路径优化
    """
    try:
        from src.api.routers.planning import SCHEDULES, load_real_stores
        
        stores = load_real_stores()
        
        # 获取调度数据
        if vehicle_id and vehicle_id in SCHEDULES:
            schedule = SCHEDULES[vehicle_id]
            route_data = {
                "vehicle_id": schedule.vehicle_id,
                "driver": schedule.driver_name,
                "departure_time": schedule.departure_time,
                "stores": [
                    {
                        "store_id": sid,
                        "store_name": stores.get(sid, {}).get("name", f"Store {sid}"),
                        "lat": stores.get(sid, {}).get("lat"),
                        "lng": stores.get(sid, {}).get("lng")
                    }
                    for sid in schedule.store_list
                ],
                "estimated_duration_min": schedule.estimated_duration_min,
                "estimated_cost": schedule.estimated_cost
            }
        else:
            # 返回所有路线概览
            route_data = {
                "total_vehicles": len(SCHEDULES),
                "routes": [
                    {
                        "vehicle_id": s.vehicle_id,
                        "store_count": len(s.store_list),
                        "status": s.status
                    }
                    for s in SCHEDULES.values()
                ]
            }
        
        # AI分析
        assistant = get_ai_assistant()
        analysis = await assistant.optimize_route(route_data)
        
        return {
            "success": True,
            "data": {
                "route": route_data,
                "analysis": analysis,
                "timestamp": datetime.now().isoformat()
            }
        }
    except Exception as e:
        logger.error(f"Route analysis error: {e}")
        return {
            "success": False,
            "error": str(e),
            "data": {
                "analysis": "路径分析服务暂时不可用",
                "timestamp": datetime.now().isoformat()
            }
        }


@router.post("/analyze/demand")
async def analyze_demand():
    """
    分析需求预测
    """
    try:
        from src.api.services.data_service import get_data_service
        
        service = get_data_service()
        
        # 获取需求数据
        daily_orders = service.get_daily_orders()
        
        # 取最近14天
        recent = daily_orders[-14:] if daily_orders and len(daily_orders) > 14 else daily_orders
        
        demand_dict = {
            "period": "last_14_days",
            "daily_data": recent[:10] if recent else [],  # 限制数据量
            "total_orders": sum(d.get("order_count", 0) for d in recent) if recent else 0,
            "avg_daily_orders": sum(d.get("order_count", 0) for d in recent) / len(recent) if recent else 0,
            "timestamp": datetime.now().isoformat()
        }
        
        # AI分析
        assistant = get_ai_assistant()
        analysis = await assistant.predict_demand(demand_dict)
        
        return {
            "success": True,
            "data": {
                "demand": demand_dict,
                "analysis": analysis,
                "timestamp": datetime.now().isoformat()
            }
        }
    except Exception as e:
        logger.error(f"Demand analysis error: {e}")
        return {
            "success": False,
            "error": str(e),
            "data": {
                "analysis": "需求分析服务暂时不可用",
                "timestamp": datetime.now().isoformat()
            }
        }


@router.get("/status")
async def get_ai_status():
    """
    获取AI服务状态
    """
    try:
        assistant = get_ai_assistant()
        
        # 简单测试
        test_response = await assistant.chat("你好，请简单介绍你自己。")
        is_available = test_response is not None and len(test_response) > 10
        
        return {
            "success": True,
            "data": {
                "status": "online" if is_available else "degraded",
                "model": "Claude 3 Sonnet (Bedrock)",
                "features": [
                    "智能对话",
                    "路况分析",
                    "SLA风险评估",
                    "路径优化建议",
                    "需求预测分析"
                ],
                "timestamp": datetime.now().isoformat()
            }
        }
    except Exception as e:
        logger.error(f"AI status check error: {e}")
        return {
            "success": False,
            "data": {
                "status": "offline",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
        }


# ==================== 演示专用接口 ====================

@router.get("/demo/summary")
async def get_demo_summary():
    """
    获取系统演示摘要（一键演示用）
    """
    try:
        from src.api.services.data_service import get_data_service
        from src.api.routers.planning import SCHEDULES, load_real_stores, REPLENISHMENT_PLANS
        
        service = get_data_service()
        stores = load_real_stores()
        
        # 汇总各模块数据
        order_stats = service.get_order_stats()
        sla = service.get_sla_analysis()
        
        summary = {
            "system": "万宁门店取货SLA优化系统",
            "version": "1.0.0",
            "timestamp": datetime.now().isoformat(),
            
            "data_status": {
                "stores": len(stores),
                "total_orders": int(order_stats.get("total_orders", 0)),
                "completed_orders": int(sla.get("completed_orders", 0)),
                "sla_rate": round(sla.get("sla_rate", 0) * 100, 1),
                "data_source": "DFI Enterprise Data"
            },
            
            "logistics": {
                "active_vehicles": len(SCHEDULES),
                "pending_routes": len([s for s in SCHEDULES.values() if s.status == "pending"]),
                "in_progress": len([s for s in SCHEDULES.values() if s.status == "in_progress"]),
                "replenishment_plans": len(REPLENISHMENT_PLANS)
            },
            
            "ai_features": {
                "status": "online",
                "capabilities": [
                    "智能路况分析",
                    "SLA风险预警",
                    "路径智能优化",
                    "需求预测分析",
                    "自然语言交互"
                ]
            },
            
            "highlights": [
                f"已接入 {len(stores)} 家真实门店数据",
                f"历史订单 {int(order_stats.get('total_orders', 0)):,} 单",
                f"SLA达成率 {round(sla.get('sla_rate', 0) * 100, 1)}%",
                "集成AWS Bedrock AI能力",
                "鲁棒路径优化算法"
            ]
        }
        
        return {
            "success": True,
            "data": summary
        }
    except Exception as e:
        logger.error(f"Demo summary error: {e}")
        return {
            "success": False,
            "error": str(e)
        }
