"""
供应链智能体系统 - Stage 2 预留架构
====================================

本模块为第二阶段AI Agent开发预留接口定义。

智能体类型：
- IDemandForecastAgent: 需求预测智能体
- IInventoryOptimizationAgent: 库存优化智能体  
- IRoutingDispatchAgent: 路径调度智能体
- ISLAAlertAgent: SLA预警智能体
- IMultiAgentCoordinator: 多Agent协调器

使用示例（Stage 2实现后）：
    from src.agents import IDemandForecastAgent, IMultiAgentCoordinator
    
    # 创建预测Agent
    forecast_agent = DemandForecastAgentImpl(config)
    
    # 注册到协调器
    coordinator.register_agent(forecast_agent)
    
    # 执行感知-推理-决策循环
    perception = forecast_agent.perceive(data_sources)
    reasoning = forecast_agent.reason(perception)
    decision = forecast_agent.decide(reasoning)
    result = forecast_agent.execute(decision)
    
    # 学习反馈
    feedback = LearningFeedback(...)
    forecast_agent.learn(feedback)
"""

from .interfaces import (
    # 枚举类型
    AgentType,
    AgentStatus,
    MessageType,
    LearningMode,
    
    # 数据结构
    AgentMessage,
    AgentState,
    PerceptionResult,
    DecisionResult,
    LearningFeedback,
    AlertEvent,
    
    # 核心接口
    IAgent,
    IDemandForecastAgent,
    IInventoryOptimizationAgent,
    IRoutingDispatchAgent,
    ISLAAlertAgent,
    IMultiAgentCoordinator,
    IAgentModelRegistry,
    IReinforcementLearningEngine,
)

__all__ = [
    # 枚举
    'AgentType',
    'AgentStatus', 
    'MessageType',
    'LearningMode',
    
    # 数据结构
    'AgentMessage',
    'AgentState',
    'PerceptionResult',
    'DecisionResult',
    'LearningFeedback',
    'AlertEvent',
    
    # 接口
    'IAgent',
    'IDemandForecastAgent',
    'IInventoryOptimizationAgent',
    'IRoutingDispatchAgent',
    'ISLAAlertAgent',
    'IMultiAgentCoordinator',
    'IAgentModelRegistry',
    'IReinforcementLearningEngine',
]
