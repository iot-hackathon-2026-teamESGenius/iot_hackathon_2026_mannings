"""
智能体核心接口定义 - Stage 2 预留架构
=======================================

本模块定义供应链智能体(Agent)系统的核心接口，用于第二阶段的AI Agent开发。
智能体系统将增强现有模块的自主决策能力，实现：
- 实时感知环境变化
- 自主学习与策略优化
- 多智能体协同决策
- 动态阈值与自适应调整

设计原则：
1. 与现有IDataFetcher/IDemandForecaster/IRoutingOptimizer等接口兼容
2. 支持渐进式升级，可逐步替换传统模块
3. 预留强化学习、深度学习模型集成接口
4. 支持分布式多Agent协同

参考文献：
- Learning Enhanced Robust Routing
- Multi-Agent Supply Chain Coordination
- Reinforcement Learning for Inventory Optimization
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, Tuple, Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import pandas as pd

# ==================== 智能体枚举定义 ====================

class AgentType(Enum):
    """智能体类型"""
    DEMAND_FORECAST = "demand_forecast"      # 需求预测Agent
    INVENTORY_OPTIMIZATION = "inventory_opt" # 库存优化Agent
    ROUTING_DISPATCH = "routing_dispatch"    # 路径调度Agent
    SLA_ALERT = "sla_alert"                  # SLA预警Agent
    COORDINATOR = "coordinator"              # 协调器Agent

class AgentStatus(Enum):
    """智能体状态"""
    IDLE = "idle"                # 空闲
    PERCEIVING = "perceiving"    # 感知中
    REASONING = "reasoning"      # 推理中
    DECIDING = "deciding"        # 决策中
    EXECUTING = "executing"      # 执行中
    LEARNING = "learning"        # 学习中
    ERROR = "error"              # 错误

class MessageType(Enum):
    """Agent间消息类型"""
    REQUEST = "request"          # 请求
    RESPONSE = "response"        # 响应
    BROADCAST = "broadcast"      # 广播
    ALERT = "alert"              # 告警
    SYNC = "sync"                # 同步
    NEGOTIATE = "negotiate"      # 协商

class LearningMode(Enum):
    """学习模式"""
    SUPERVISED = "supervised"          # 监督学习
    REINFORCEMENT = "reinforcement"    # 强化学习
    ONLINE = "online"                  # 在线学习
    TRANSFER = "transfer"              # 迁移学习
    FEDERATED = "federated"            # 联邦学习

# ==================== 智能体数据结构 ====================

@dataclass
class AgentMessage:
    """智能体间通信消息"""
    message_id: str
    sender_id: str
    receiver_id: str  # "*" 表示广播
    message_type: MessageType
    topic: str
    payload: Dict[str, Any]
    timestamp: datetime
    priority: int = 0
    ttl_seconds: int = 300  # 消息有效期
    
    def to_dict(self) -> Dict:
        return {
            'message_id': self.message_id,
            'sender_id': self.sender_id,
            'receiver_id': self.receiver_id,
            'message_type': self.message_type.value,
            'topic': self.topic,
            'payload': self.payload,
            'timestamp': self.timestamp.isoformat(),
            'priority': self.priority,
            'ttl_seconds': self.ttl_seconds
        }

@dataclass
class AgentState:
    """智能体状态快照"""
    agent_id: str
    agent_type: AgentType
    status: AgentStatus
    last_perception: Dict[str, Any]
    last_decision: Dict[str, Any]
    performance_metrics: Dict[str, float]
    timestamp: datetime
    
    def to_dict(self) -> Dict:
        return {
            'agent_id': self.agent_id,
            'agent_type': self.agent_type.value,
            'status': self.status.value,
            'last_perception': self.last_perception,
            'last_decision': self.last_decision,
            'performance_metrics': self.performance_metrics,
            'timestamp': self.timestamp.isoformat()
        }

@dataclass
class PerceptionResult:
    """感知结果"""
    perception_id: str
    data_source: str
    raw_data: Dict[str, Any]
    features: Dict[str, float]
    anomalies: List[Dict[str, Any]]
    confidence: float
    timestamp: datetime

@dataclass
class DecisionResult:
    """决策结果"""
    decision_id: str
    action_type: str
    action_params: Dict[str, Any]
    expected_outcome: Dict[str, float]
    confidence: float
    reasoning_trace: List[str]  # 决策推理轨迹
    timestamp: datetime

@dataclass
class LearningFeedback:
    """学习反馈"""
    feedback_id: str
    decision_id: str
    actual_outcome: Dict[str, float]
    reward: float
    is_positive: bool
    timestamp: datetime

@dataclass
class AlertEvent:
    """预警事件"""
    alert_id: str
    alert_type: str
    severity: str  # low / medium / high / critical
    source_agent_id: str
    affected_entities: List[str]
    description: str
    suggested_actions: List[str]
    auto_trigger_enabled: bool
    timestamp: datetime

# ==================== 智能体核心接口 ====================

class IAgent(ABC):
    """
    智能体基础接口
    
    所有供应链智能体的抽象基类，定义核心能力：
    - 感知 (Perceive): 从环境获取数据
    - 推理 (Reason): 分析数据，识别模式
    - 决策 (Decide): 基于分析做出决策
    - 执行 (Execute): 执行决策动作
    - 学习 (Learn): 从反馈中优化策略
    - 通信 (Communicate): 与其他Agent交互
    """
    
    @property
    @abstractmethod
    def agent_id(self) -> str:
        """智能体唯一标识"""
        pass
    
    @property
    @abstractmethod
    def agent_type(self) -> AgentType:
        """智能体类型"""
        pass
    
    @abstractmethod
    def get_state(self) -> AgentState:
        """获取当前状态快照"""
        pass
    
    # ===== 感知能力 =====
    
    @abstractmethod
    def perceive(self, data_sources: Dict[str, Any]) -> PerceptionResult:
        """
        感知环境
        
        Args:
            data_sources: 数据源字典，如 {
                'historical_data': DataFrame,
                'realtime_data': Dict,
                'external_factors': Dict
            }
        
        Returns:
            PerceptionResult: 感知结果，包含特征提取和异常检测
        """
        pass
    
    @abstractmethod
    def extract_features(self, raw_data: Dict[str, Any]) -> Dict[str, float]:
        """
        特征提取
        
        从原始数据中提取用于决策的特征向量
        """
        pass
    
    @abstractmethod
    def detect_anomalies(self, features: Dict[str, float]) -> List[Dict[str, Any]]:
        """
        异常检测
        
        基于特征识别异常模式
        """
        pass
    
    # ===== 推理能力 =====
    
    @abstractmethod
    def reason(self, perception: PerceptionResult) -> Dict[str, Any]:
        """
        推理分析
        
        Args:
            perception: 感知结果
            
        Returns:
            推理结论，包含模式识别、趋势分析等
        """
        pass
    
    # ===== 决策能力 =====
    
    @abstractmethod
    def decide(self, reasoning_result: Dict[str, Any]) -> DecisionResult:
        """
        做出决策
        
        Args:
            reasoning_result: 推理结果
            
        Returns:
            DecisionResult: 决策结果，包含动作和预期效果
        """
        pass
    
    @abstractmethod
    def evaluate_options(self, options: List[Dict[str, Any]]) -> List[Tuple[Dict, float]]:
        """
        评估决策选项
        
        Returns:
            选项及其评分列表 [(option, score), ...]
        """
        pass
    
    # ===== 执行能力 =====
    
    @abstractmethod
    def execute(self, decision: DecisionResult) -> Dict[str, Any]:
        """
        执行决策
        
        Returns:
            执行结果，包含成功/失败状态和实际影响
        """
        pass
    
    # ===== 学习能力 =====
    
    @abstractmethod
    def learn(self, feedback: LearningFeedback) -> bool:
        """
        从反馈中学习
        
        Args:
            feedback: 学习反馈，包含实际结果和奖励
            
        Returns:
            是否成功更新模型
        """
        pass
    
    @abstractmethod
    def get_learning_mode(self) -> LearningMode:
        """获取当前学习模式"""
        pass
    
    @abstractmethod
    def set_learning_mode(self, mode: LearningMode) -> None:
        """设置学习模式"""
        pass
    
    # ===== 通信能力 =====
    
    @abstractmethod
    def send_message(self, message: AgentMessage) -> bool:
        """发送消息给其他Agent"""
        pass
    
    @abstractmethod
    def receive_message(self, message: AgentMessage) -> Dict[str, Any]:
        """接收并处理来自其他Agent的消息"""
        pass
    
    @abstractmethod
    def broadcast(self, topic: str, payload: Dict[str, Any]) -> bool:
        """广播消息给所有Agent"""
        pass


class IDemandForecastAgent(IAgent):
    """
    需求预测智能体接口
    
    增强现有 IDemandForecaster 的能力：
    - 实时感知市场变化（促销、天气、节假日等）
    - 自主选择最优预测模型
    - 动态调整预测策略
    - 与库存Agent协同优化
    """
    
    @abstractmethod
    def predict_with_scenarios(
        self, 
        store_ids: List[str],
        horizon_days: int,
        scenario_ratios: List[float] = None
    ) -> Dict[str, Any]:
        """
        多情景需求预测
        
        Returns:
            {
                'base_forecast': [...],
                'scenarios': [
                    {'ratio': 0.9, 'forecast': [...]},
                    {'ratio': 1.0, 'forecast': [...]},
                    {'ratio': 1.1, 'forecast': [...]}
                ],
                'confidence_intervals': {...}
            }
        """
        pass
    
    @abstractmethod
    def select_best_model(
        self, 
        historical_data: pd.DataFrame,
        candidate_models: List[str] = None
    ) -> Tuple[str, Dict[str, float]]:
        """
        自动选择最优预测模型
        
        Returns:
            (model_name, performance_metrics)
        """
        pass
    
    @abstractmethod
    def incorporate_external_factors(
        self,
        weather_data: pd.DataFrame = None,
        promotion_data: pd.DataFrame = None,
        holiday_data: pd.DataFrame = None
    ) -> Dict[str, float]:
        """
        融合外部因素
        
        Returns:
            各因素的影响权重
        """
        pass
    
    @abstractmethod
    def get_forecast_explanation(self, forecast_id: str) -> Dict[str, Any]:
        """
        获取预测解释（可解释AI）
        
        Returns:
            特征重要性、决策路径等解释信息
        """
        pass


class IInventoryOptimizationAgent(IAgent):
    """
    库存优化智能体接口
    
    增强现有 IInventoryOptimizer 的能力：
    - 动态安全库存调整
    - 多产品协调优化
    - 自适应补货策略
    - 库存异常实时预警
    """
    
    @abstractmethod
    def calculate_dynamic_safety_stock(
        self,
        store_id: str,
        sku_id: str,
        demand_forecast: Dict[str, Any],
        service_level: float = 0.95
    ) -> Dict[str, Any]:
        """
        动态计算安全库存
        
        Returns:
            {
                'safety_stock': float,
                'reorder_point': float,
                'adjustment_factors': {...},
                'confidence': float
            }
        """
        pass
    
    @abstractmethod
    def optimize_multi_product(
        self,
        product_demands: Dict[str, float],
        budget_constraint: float,
        storage_constraint: float
    ) -> Dict[str, Any]:
        """
        多产品协调优化
        
        考虑预算约束、仓储容量限制和产品间关联性
        """
        pass
    
    @abstractmethod
    def generate_adaptive_replenishment(
        self,
        current_inventory: Dict[str, float],
        demand_scenarios: List[Dict[str, float]]
    ) -> Dict[str, Any]:
        """
        生成自适应补货计划
        
        Returns:
            考虑需求不确定性的鲁棒补货方案
        """
        pass
    
    @abstractmethod
    def detect_inventory_anomaly(
        self,
        inventory_snapshots: List[Dict[str, Any]]
    ) -> List[AlertEvent]:
        """
        检测库存异常
        
        包括：负库存、突增、盘点不一致等
        """
        pass


class IRoutingDispatchAgent(IAgent):
    """
    路径调度智能体接口
    
    增强现有 IRoutingOptimizer 的能力：
    - 实时交通感知与路径重规划
    - 动态车辆调度
    - 多目标优化（成本、时效、碳排放）
    - 与需求预测Agent协同
    """
    
    @abstractmethod
    def optimize_with_realtime_traffic(
        self,
        planned_routes: List[Dict[str, Any]],
        traffic_data: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        基于实时交通的路径重优化
        """
        pass
    
    @abstractmethod
    def dynamic_vehicle_assignment(
        self,
        pending_orders: List[Dict[str, Any]],
        available_vehicles: List[Dict[str, Any]],
        urgency_weights: Dict[str, float] = None
    ) -> Dict[str, Any]:
        """
        动态车辆分配
        
        考虑订单紧急程度、车辆状态、司机工时等
        """
        pass
    
    @abstractmethod
    def multi_objective_optimize(
        self,
        objectives: Dict[str, float],  # {'cost': 0.5, 'time': 0.3, 'emission': 0.2}
        constraints: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        多目标优化
        
        Returns:
            帕累托最优解集
        """
        pass
    
    @abstractmethod
    def predict_delivery_risk(
        self,
        route_plan: Dict[str, Any],
        external_factors: Dict[str, Any]
    ) -> Dict[str, float]:
        """
        预测配送风险
        
        Returns:
            各门店的SLA违约概率
        """
        pass


class ISLAAlertAgent(IAgent):
    """
    SLA预警智能体接口
    
    增强现有 ISLAPredictor 的能力：
    - 实时SLA风险监控
    - 动态阈值自适应
    - 根因分析与瓶颈定位
    - 自动触发缓解策略
    """
    
    @abstractmethod
    def monitor_sla_realtime(
        self,
        order_status: List[Dict[str, Any]],
        route_progress: List[Dict[str, Any]]
    ) -> List[AlertEvent]:
        """
        实时SLA监控
        
        Returns:
            触发的预警事件列表
        """
        pass
    
    @abstractmethod
    def calculate_dynamic_threshold(
        self,
        historical_performance: pd.DataFrame,
        current_context: Dict[str, Any]
    ) -> Dict[str, float]:
        """
        动态计算预警阈值
        
        考虑历史表现、当前负载、外部因素等
        """
        pass
    
    @abstractmethod
    def analyze_root_cause(
        self,
        alert_event: AlertEvent
    ) -> Dict[str, Any]:
        """
        根因分析
        
        Returns:
            {
                'primary_cause': str,
                'contributing_factors': [...],
                'affected_scope': {...},
                'confidence': float
            }
        """
        pass
    
    @abstractmethod
    def recommend_mitigation(
        self,
        alert_event: AlertEvent,
        available_resources: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        推荐缓解措施
        
        Returns:
            按优先级排序的缓解方案列表
        """
        pass
    
    @abstractmethod
    def auto_execute_mitigation(
        self,
        alert_event: AlertEvent,
        mitigation_plan: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        自动执行缓解措施（需授权）
        """
        pass


class IMultiAgentCoordinator(ABC):
    """
    多智能体协调器接口
    
    负责多个Agent之间的协同决策：
    - Agent注册与生命周期管理
    - 消息路由与广播
    - 协同决策与冲突解决
    - 全局状态管理
    """
    
    @abstractmethod
    def register_agent(self, agent: IAgent) -> bool:
        """注册Agent"""
        pass
    
    @abstractmethod
    def unregister_agent(self, agent_id: str) -> bool:
        """注销Agent"""
        pass
    
    @abstractmethod
    def get_registered_agents(self) -> List[AgentState]:
        """获取所有已注册Agent的状态"""
        pass
    
    @abstractmethod
    def route_message(self, message: AgentMessage) -> bool:
        """路由消息"""
        pass
    
    @abstractmethod
    def broadcast_message(self, message: AgentMessage) -> int:
        """广播消息，返回成功接收的Agent数量"""
        pass
    
    @abstractmethod
    def coordinate_decision(
        self,
        participating_agents: List[str],
        decision_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        协调多Agent决策
        
        当多个Agent的决策存在依赖或冲突时，进行协调
        """
        pass
    
    @abstractmethod
    def resolve_conflict(
        self,
        conflicting_decisions: List[DecisionResult]
    ) -> DecisionResult:
        """
        解决决策冲突
        
        采用投票、优先级或协商机制
        """
        pass
    
    @abstractmethod
    def get_global_state(self) -> Dict[str, Any]:
        """获取全局状态"""
        pass
    
    @abstractmethod
    def sync_agents(self) -> bool:
        """同步所有Agent状态"""
        pass


class IAgentModelRegistry(ABC):
    """
    智能体模型注册表接口
    
    管理Agent使用的ML/DL模型：
    - 模型注册与版本管理
    - 模型热更新
    - A/B测试支持
    - 模型性能监控
    """
    
    @abstractmethod
    def register_model(
        self,
        model_name: str,
        model_type: str,
        model_artifact: Any,
        metadata: Dict[str, Any]
    ) -> str:
        """
        注册模型
        
        Returns:
            model_version_id
        """
        pass
    
    @abstractmethod
    def get_model(
        self,
        model_name: str,
        version: str = "latest"
    ) -> Tuple[Any, Dict[str, Any]]:
        """
        获取模型
        
        Returns:
            (model_artifact, metadata)
        """
        pass
    
    @abstractmethod
    def hot_swap_model(
        self,
        model_name: str,
        new_version: str
    ) -> bool:
        """热切换模型版本"""
        pass
    
    @abstractmethod
    def get_model_metrics(
        self,
        model_name: str,
        time_range: Tuple[datetime, datetime] = None
    ) -> Dict[str, Any]:
        """获取模型性能指标"""
        pass
    
    @abstractmethod
    def compare_models(
        self,
        model_a: str,
        model_b: str,
        test_data: pd.DataFrame
    ) -> Dict[str, Any]:
        """A/B对比测试"""
        pass


class IReinforcementLearningEngine(ABC):
    """
    强化学习引擎接口
    
    为Agent提供强化学习能力：
    - 环境建模
    - 策略训练
    - 奖励设计
    - 在线学习
    """
    
    @abstractmethod
    def define_state_space(self, state_config: Dict[str, Any]) -> None:
        """定义状态空间"""
        pass
    
    @abstractmethod
    def define_action_space(self, action_config: Dict[str, Any]) -> None:
        """定义动作空间"""
        pass
    
    @abstractmethod
    def set_reward_function(self, reward_fn: Callable) -> None:
        """设置奖励函数"""
        pass
    
    @abstractmethod
    def train_policy(
        self,
        episodes: int,
        environment: Any,
        algorithm: str = "PPO"
    ) -> Dict[str, Any]:
        """训练策略"""
        pass
    
    @abstractmethod
    def get_action(self, state: Dict[str, float]) -> Tuple[str, float]:
        """
        获取动作
        
        Returns:
            (action, confidence)
        """
        pass
    
    @abstractmethod
    def update_policy_online(
        self,
        state: Dict[str, float],
        action: str,
        reward: float,
        next_state: Dict[str, float]
    ) -> bool:
        """在线策略更新"""
        pass
