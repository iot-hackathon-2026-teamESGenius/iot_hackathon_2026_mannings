"""RAG (Retrieval-Augmented Generation) 服务 - 安全版本
结合本地业务数据和 AI 进行智能分析

【安全架构】
AI 只能通过 DataSanitizer 获取脱敏后的安全报告
无法直接访问企业原始数据
"""
import logging
import json
import numpy as np
from typing import Dict, List, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class NumpyEncoder(json.JSONEncoder):
    """自定义 JSON 编码器，处理 numpy 类型"""
    def default(self, obj):
        if isinstance(obj, np.integer):
            return int(obj)
        if isinstance(obj, np.floating):
            return float(obj)
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        return super().default(obj)


class SecureDataRetriever:
    """安全数据检索器 - 只通过 DataSanitizer 获取脱敏数据
    
    安全保证:
    1. 不直接访问 data_service
    2. 不直接访问 stores 原始数据
    3. 所有数据都经过脱敏处理
    4. 所有访问都有审计日志
    """
    
    def __init__(self):
        self._sanitizer = None
    
    def _get_sanitizer(self):
        """获取数据净化服务"""
        if self._sanitizer is None:
            from src.api.services.data_sanitizer import get_data_sanitizer
            self._sanitizer = get_data_sanitizer()
        return self._sanitizer
    
    def retrieve(self, query: str) -> Dict[str, Any]:
        """
        根据查询检索安全报告数据
        
        【重要】此方法只返回脱敏后的安全报告
        不会暴露任何原始企业数据
        """
        query_lower = query.lower()
        sanitizer = self._get_sanitizer()
        
        context = {
            "retrieved_at": datetime.now().isoformat(),
            "query": query,
            "data": {},
            "security": {
                "data_sanitized": True,
                "raw_data_exposed": False,
                "access_logged": True
            }
        }
        
        try:
            # 根据关键词检索对应的安全报告
            
            # 1. SLA 相关
            if any(kw in query_lower for kw in ['sla', '达成率', '履约', '完成率', '订单完成']):
                context["data"]["sla_report"] = sanitizer.get_safe_sla_report()
            
            # 2. 订单相关
            if any(kw in query_lower for kw in ['订单', '单量', '销量', '销售', '订单量', '今天', '昨天', '最近']):
                context["data"]["order_report"] = sanitizer.get_safe_order_report()
            
            # 3. 门店相关
            if any(kw in query_lower for kw in ['门店', '店铺', '分店', '区域', '覆盖']):
                context["data"]["store_report"] = sanitizer.get_safe_store_report(query)
            
            # 4. 库存相关
            if any(kw in query_lower for kw in ['库存', '缺货', '补货', '存货', '商品', '产品']):
                context["data"]["inventory_report"] = sanitizer.get_safe_inventory_report()
            
            # 5. 配送/物流相关
            if any(kw in query_lower for kw in ['配送', '调度', '路线', '车辆', '司机', '派送', '物流', '运输']):
                context["data"]["logistics_report"] = sanitizer.get_safe_logistics_report()
            
            # 6. 预测相关
            if any(kw in query_lower for kw in ['预测', '趋势', '未来', '预期', '预估']):
                context["data"]["forecast_report"] = sanitizer.get_safe_forecast_report()
            
            # 7. 安全审计
            if any(kw in query_lower for kw in ['安全', '审计', '访问记录', '数据保护']):
                context["data"]["audit_report"] = sanitizer.get_audit_summary()
            
            # 如果没有匹配到特定数据，返回系统概览
            if not context["data"]:
                context["data"]["system_overview"] = sanitizer.get_safe_system_overview()
            
            # 添加安全声明
            context["data"]["_security_notice"] = {
                "message": "所有数据均已脱敏处理",
                "raw_data_blocked": True,
                "compliance": "符合数据安全规范"
            }
            
        except Exception as e:
            logger.error(f"Secure data retrieval error: {e}")
            context["error"] = str(e)
        
        return context


class SecureRAGAgent:
    """安全 RAG Agent - 只能访问脱敏数据
    
    安全架构:
    ┌─────────────────────────────────────┐
    │         SecureRAGAgent              │
    │  (只能读取 SafeReport)               │
    └──────────────┬──────────────────────┘
                   │ 安全接口
                   ▼
    ┌─────────────────────────────────────┐
    │        DataSanitizer                │
    │  (数据脱敏 + 审计日志)               │
    └──────────────┬──────────────────────┘
                   │ 内部访问
                   ▼
    ┌─────────────────────────────────────┐
    │      企业原始数据 (不可直接访问)     │
    └─────────────────────────────────────┘
    """
    
    def __init__(self):
        self.retriever = SecureDataRetriever()
        self._ai_assistant = None
    
    def _get_ai_assistant(self):
        """获取 AI 助手"""
        if self._ai_assistant is None:
            from src.api.services.bedrock_service import get_ai_assistant
            self._ai_assistant = get_ai_assistant()
        return self._ai_assistant
    
    async def chat(self, message: str, history: List[Dict] = None) -> Dict[str, Any]:
        """
        安全 RAG 对话
        
        流程:
        1. 通过 SecureDataRetriever 获取脱敏报告
        2. 将安全报告作为上下文传给 AI
        3. AI 基于脱敏数据生成回答
        4. 记录访问审计日志
        """
        # 获取脱敏的安全报告
        context = self.retriever.retrieve(message)
        
        # 构建安全的 prompt
        prompt = self._build_secure_prompt(message, context, history)
        
        # 调用 AI
        ai = self._get_ai_assistant()
        response = await ai.chat(prompt, context.get("data"))
        
        return {
            "success": True,
            "response": response,
            "context": {
                "retrieved_data": list(context["data"].keys()) if context.get("data") else [],
                "timestamp": context.get("retrieved_at"),
                "security": context.get("security", {})
            }
        }
    
    def _build_secure_prompt(self, query: str, context: Dict, history: List[Dict] = None) -> str:
        """构建安全的 RAG prompt"""
        data = context.get("data", {})
        
        prompt_parts = [
            "你是万宁(Mannings)门店物流SLA优化系统的AI助手。",
            "",
            "【数据安全声明】",
            "以下数据均已经过脱敏处理，不包含任何敏感的企业原始数据。",
            "门店位置已转换为区域描述，订单金额已范围化，时间已时段化。",
            "",
            "=== 安全报告数据 ===",
        ]
        
        for key, value in data.items():
            if key.startswith("_"):  # 跳过内部字段
                continue
            prompt_parts.append(f"\n【{key.upper().replace('_', ' ')}】")
            if isinstance(value, dict):
                prompt_parts.append(json.dumps(value, ensure_ascii=False, indent=2, cls=NumpyEncoder))
            else:
                prompt_parts.append(str(value))
        
        prompt_parts.append("\n=== 用户问题 ===")
        prompt_parts.append(query)
        prompt_parts.append("\n请基于上述安全报告数据给出专业、准确的分析和建议。")
        prompt_parts.append("注意：你只能看到脱敏后的统计报告，无法访问具体的门店名称、客户信息或订单明细。")
        
        return "\n".join(prompt_parts)
    
    def get_security_status(self) -> Dict:
        """获取安全状态报告"""
        sanitizer = self.retriever._get_sanitizer()
        return {
            "security_enabled": True,
            "data_sanitization": "active",
            "raw_data_access": "blocked",
            "audit_logging": "enabled",
            "audit_summary": sanitizer.get_audit_summary()
        }


# ==================== 兼容性别名 ====================

# 保持向后兼容
DataRetriever = SecureDataRetriever
RAGAgent = SecureRAGAgent


# ==================== 单例 ====================

_rag_agent: Optional[SecureRAGAgent] = None

def get_rag_agent() -> SecureRAGAgent:
    """获取安全 RAG Agent 单例"""
    global _rag_agent
    if _rag_agent is None:
        _rag_agent = SecureRAGAgent()
    return _rag_agent
