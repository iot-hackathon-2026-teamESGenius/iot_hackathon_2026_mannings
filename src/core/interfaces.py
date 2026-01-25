"""
模块化架构的核心接口定义
适配前端技术栈: Vue3 + uniapp + uniCloud
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime
from enum import Enum
import pandas as pd

# ==================== 枚举定义 ====================

class UserRole(Enum):
    """用户角色枚举"""
    STORE_INVENTORY = "store_inventory"  # 门店库存管理
    LOGISTICS = "logistics"  # 物流配送团队
    ADMIN = "admin"  # 系统管理员

class RiskLevel(Enum):
    """风险等级枚举"""
    LOW = "low"  # 蓝色
    MEDIUM = "medium"  # 黄色
    HIGH = "high"  # 橙色
    CRITICAL = "critical"  # 红色

class AlertStatus(Enum):
    """预警状态枚举"""
    PENDING = "pending"  # 未处理
    PROCESSING = "processing"  # 处理中
    RESOLVED = "resolved"  # 已解决

class BottleneckType(Enum):
    """瓶颈类型枚举"""
    ECDC = "ecdc"  # 电商配送中心
    FLEET = "fleet"  # 车队调度
    STORE = "store"  # 门店处理

# ==================== 数据类定义 ====================

@dataclass
class UserInfo:
    """用户信息"""
    user_id: str
    username: str
    role: UserRole
    permissions: List[str]
    store_ids: List[str] = None  # 可管理的门店列表
    
    def to_dict(self) -> Dict:
        return {
            'user_id': self.user_id,
            'username': self.username,
            'role': self.role.value,
            'permissions': self.permissions,
            'store_ids': self.store_ids or []
        }

@dataclass
class SLAAlert:
    """SLA预警信息"""
    alert_id: str
    alert_time: datetime
    risk_level: RiskLevel
    affected_entity: str  # store_id / ecdc_id / vehicle_id
    entity_type: str  # 'store' / 'ecdc' / 'vehicle'
    alert_description: str
    bottleneck_type: BottleneckType
    status: AlertStatus
    handler: str = None
    resolution: str = None
    resolved_time: datetime = None
    
    def to_dict(self) -> Dict:
        return {
            'alert_id': self.alert_id,
            'alert_time': self.alert_time.isoformat() if self.alert_time else None,
            'risk_level': self.risk_level.value,
            'affected_entity': self.affected_entity,
            'entity_type': self.entity_type,
            'alert_description': self.alert_description,
            'bottleneck_type': self.bottleneck_type.value,
            'status': self.status.value,
            'handler': self.handler,
            'resolution': self.resolution,
            'resolved_time': self.resolved_time.isoformat() if self.resolved_time else None
        }

@dataclass
class OrderSLAInfo:
    """订单SLA信息"""
    order_id: str
    order_time: datetime
    store_id: str
    store_name: str
    sku_list: List[str]
    promised_ready_time: datetime
    estimated_ready_time: datetime
    actual_ready_time: datetime = None
    status: str = "pending"  # pending / ready / completed / cancelled
    sla_achieved: bool = None
    delay_reason: str = None
    customer_name: str = None  # 脱敏
    customer_phone: str = None  # 脱敏
    
    def to_dict(self) -> Dict:
        return {
            'order_id': self.order_id,
            'order_time': self.order_time.isoformat() if self.order_time else None,
            'store_id': self.store_id,
            'store_name': self.store_name,
            'sku_list': self.sku_list,
            'promised_ready_time': self.promised_ready_time.isoformat() if self.promised_ready_time else None,
            'estimated_ready_time': self.estimated_ready_time.isoformat() if self.estimated_ready_time else None,
            'actual_ready_time': self.actual_ready_time.isoformat() if self.actual_ready_time else None,
            'status': self.status,
            'sla_achieved': self.sla_achieved,
            'delay_reason': self.delay_reason,
            'customer_name': self.customer_name,
            'customer_phone': self.customer_phone
        }

@dataclass
class ReplenishmentPlan:
    """补货计划"""
    plan_id: str
    dc_id: str
    dc_name: str
    ecdc_id: str
    ecdc_name: str
    sku_id: str
    sku_name: str
    recommended_qty: float
    actual_qty: float = None
    replenishment_date: str = None
    status: str = "pending"  # pending / approved / adjusted / rejected
    is_feasible: bool = True
    infeasible_reason: str = None
    reviewer: str = None
    review_time: datetime = None
    adjustment_reason: str = None
    
    def to_dict(self) -> Dict:
        return {
            'plan_id': self.plan_id,
            'dc_id': self.dc_id,
            'dc_name': self.dc_name,
            'ecdc_id': self.ecdc_id,
            'ecdc_name': self.ecdc_name,
            'sku_id': self.sku_id,
            'sku_name': self.sku_name,
            'recommended_qty': self.recommended_qty,
            'actual_qty': self.actual_qty,
            'replenishment_date': self.replenishment_date,
            'status': self.status,
            'is_feasible': self.is_feasible,
            'infeasible_reason': self.infeasible_reason,
            'reviewer': self.reviewer,
            'review_time': self.review_time.isoformat() if self.review_time else None,
            'adjustment_reason': self.adjustment_reason
        }

@dataclass
class StoreInfo:
    """门店信息"""
    store_id: str
    name: str
    address: str
    latitude: float
    longitude: float
    time_window_start: str
    time_window_end: str
    capacity: float

@dataclass
class DemandForecast:
    """需求预测结果"""
    store_id: str
    sku_id: str
    date: str
    forecast_demand: float
    lower_bound: float
    upper_bound: float
    confidence: float

@dataclass
class RoutePlan:
    """路线规划结果"""
    route_id: str
    vehicle_id: str
    store_sequence: List[str]
    arrival_times: List[str]
    departure_times: List[str]
    distances_km: List[float]
    total_distance_km: float
    total_duration_min: float
    total_cost: float
    sla_risk_score: float

class IDataFetcher(ABC):
    """数据获取接口"""
    @abstractmethod
    def fetch_weather_data(self, date_range: tuple, locations: List[tuple]) -> pd.DataFrame:
        pass
    
    @abstractmethod
    def fetch_geospatial_data(self, bounding_box: tuple) -> Dict:
        pass
    
    @abstractmethod
    def fetch_business_data(self, date_range: tuple, data_type: str) -> pd.DataFrame:
        pass
    
    @abstractmethod
    def get_config(self) -> Dict[str, Any]:
        pass
    
    @abstractmethod
    def test_connection(self) -> bool:
        pass

class IDistanceCalculator(ABC):
    """距离计算接口"""
    @abstractmethod
    def calculate_distance_matrix(self, origins: List[tuple], destinations: List[tuple], mode: str = "driving") -> pd.DataFrame:
        pass
    
    @abstractmethod
    def get_provider_name(self) -> str:
        pass
    
    @abstractmethod
    def get_cost_per_request(self) -> float:
        pass

class IDemandForecaster(ABC):
    """需求预测接口"""
    @abstractmethod
    def train(self, historical_data: pd.DataFrame, external_features: Dict[str, pd.DataFrame] = None) -> Dict[str, Any]:
        pass
    
    @abstractmethod
    def predict(self, future_dates: List[str], store_ids: List[str], sku_ids: List[str], external_features: Dict[str, pd.DataFrame] = None) -> List[DemandForecast]:
        pass
    
    @abstractmethod
    def evaluate(self, actual_data: pd.DataFrame, forecast_data: pd.DataFrame) -> Dict[str, float]:
        pass
    
    @abstractmethod
    def get_model_info(self) -> Dict[str, Any]:
        pass

class IInventoryOptimizer(ABC):
    """库存优化接口"""
    @abstractmethod
    def calculate_safety_stock(self, demand_forecasts: List[DemandForecast], service_level: float = 0.95, lead_time_days: int = 2) -> Dict[str, float]:
        pass
    
    @abstractmethod
    def optimize_inventory_allocation(self, current_inventory: Dict[str, float], demand_forecasts: List[DemandForecast], warehouse_capacity: Dict[str, float], costs: Dict[str, float]) -> Dict[str, Any]:
        pass
    
    @abstractmethod
    def generate_replenishment_plan(self, safety_stocks: Dict[str, float], current_inventory: Dict[str, float], min_order_qty: Dict[str, float], batch_sizes: Dict[str, float]) -> Dict[str, Any]:
        pass

class IRoutingOptimizer(ABC):
    """路径优化接口"""
    @abstractmethod
    def optimize_routes(self, stores: List[StoreInfo], demands: Dict[str, float], vehicles: List[Any], distance_calculator: IDistanceCalculator, time_windows: bool = True, capacity_constraints: bool = True) -> List[RoutePlan]:
        pass
    
    @abstractmethod
    def evaluate_routes(self, route_plans: List[RoutePlan], actual_performance: Dict[str, Any] = None) -> Dict[str, float]:
        pass
    
    @abstractmethod
    def robust_optimization(self, stores: List[StoreInfo], demand_scenarios: List[Dict[str, float]], vehicles: List[Any], distance_calculator: IDistanceCalculator, robustness_level: float = 0.9) -> List[RoutePlan]:
        pass

class ISLAPredictor(ABC):
    """SLA预测接口"""
    @abstractmethod
    def predict_pickup_time(self, order_info: Dict[str, Any], route_plan: RoutePlan, store_processing_time_model: Any = None) -> Dict[str, Any]:
        pass
    
    @abstractmethod
    def calculate_sla_probability(self, promised_time: datetime, predicted_time: datetime, uncertainty: float = 0.1) -> float:
        pass

class IVisualization(ABC):
    """可视化接口"""
    @abstractmethod
    def create_dashboard(self, data_sources: Dict[str, Any], layout_config: Dict[str, Any] = None) -> Any:
        pass
    
    @abstractmethod
    def plot_routes(self, route_plans: List[RoutePlan], store_locations: Dict[str, tuple], map_provider: str = "openstreetmap") -> Any:
        pass

class IOrchestrator(ABC):
    """协调器接口"""
    @abstractmethod
    def execute_pipeline(self, pipeline_config: Dict[str, Any], modules: Dict[str, Any]) -> Dict[str, Any]:
        pass
    
    @abstractmethod
    def validate_pipeline(self, modules: Dict[str, Any]) -> bool:
        pass

# ==================== 前端适配新增接口 ====================

class IAuthService(ABC):
    """认证服务接口 - 适配前端RBAC权限控制"""
    
    @abstractmethod
    def login(self, username: str, password: str) -> Dict[str, Any]:
        """
        用户登录
        
        Returns:
            {
                'success': bool,
                'token': str,
                'user': UserInfo.to_dict(),
                'error': str (if failed)
            }
        """
        pass
    
    @abstractmethod
    def logout(self, token: str) -> bool:
        """用户登出"""
        pass
    
    @abstractmethod
    def validate_token(self, token: str) -> Dict[str, Any]:
        """
        验证Token有效性
        
        Returns:
            {
                'valid': bool,
                'user': UserInfo.to_dict() (if valid),
                'error': str (if invalid)
            }
        """
        pass
    
    @abstractmethod
    def get_user_permissions(self, user_id: str) -> List[str]:
        """获取用户权限列表"""
        pass
    
    @abstractmethod
    def check_permission(self, token: str, required_permission: str) -> bool:
        """检查用户是否具有特定权限"""
        pass

class ISLAAnalyzer(ABC):
    """SLA分析器接口 - 适配前端预警与瓶颈分析页面"""
    
    @abstractmethod
    def generate_alerts(self, predictions: List[Dict[str, Any]], 
                        threshold: float = 0.8) -> List[SLAAlert]:
        """
        根据预测结果生成SLA风险预警
        
        Args:
            predictions: SLA预测结果列表
            threshold: 风险阈值，低于此概率则生成预警
        
        Returns:
            SLAAlert列表
        """
        pass
    
    @abstractmethod
    def analyze_bottleneck(self, time_range: Tuple[str, str], 
                           store_ids: List[str] = None) -> Dict[str, Any]:
        """
        分析SLA瓶颈环节分布
        
        Returns:
            {
                'distribution': {'ecdc': 0.3, 'fleet': 0.5, 'store': 0.2},
                'trends': [...],  # 按时间的趋势数据
                'top_issues': [...]  # 最常见问题列表
            }
        """
        pass
    
    @abstractmethod
    def get_alerts(self, filters: Dict[str, Any] = None) -> List[SLAAlert]:
        """
        获取预警列表（支持筛选）
        
        Args:
            filters: {
                'risk_level': RiskLevel,
                'status': AlertStatus,
                'time_range': (start, end),
                'store_ids': List[str]
            }
        """
        pass
    
    @abstractmethod
    def update_alert_status(self, alert_id: str, status: AlertStatus, 
                            handler: str = None, resolution: str = None) -> bool:
        """更新预警处理状态"""
        pass
    
    @abstractmethod
    def get_alert_statistics(self, time_range: Tuple[str, str]) -> Dict[str, Any]:
        """
        获取预警统计数据
        
        Returns:
            {
                'total_count': int,
                'by_risk_level': {'low': n, 'medium': n, 'high': n, 'critical': n},
                'by_status': {'pending': n, 'processing': n, 'resolved': n},
                'by_bottleneck': {'ecdc': n, 'fleet': n, 'store': n},
                'resolution_rate': float,
                'avg_resolution_time_min': float
            }
        """
        pass

class IOrderService(ABC):
    """订单服务接口 - 适配前端自提订单管理页面"""
    
    @abstractmethod
    def get_orders(self, filters: Dict[str, Any] = None) -> List[OrderSLAInfo]:
        """
        获取订单列表（支持筛选）
        
        Args:
            filters: {
                'order_id': str,
                'store_id': str,
                'date_range': (start, end),
                'status': str
            }
        """
        pass
    
    @abstractmethod
    def get_order_detail(self, order_id: str) -> OrderSLAInfo:
        """获取订单详情"""
        pass
    
    @abstractmethod
    def get_pickup_promise(self, store_id: str, sku_ids: List[str], 
                           order_time: datetime) -> Dict[str, Any]:
        """
        获取自提承诺时间窗口
        
        Returns:
            {
                'store_id': str,
                'promised_ready_time': datetime,
                'confidence': float,
                'risk_factors': [...]
            }
        """
        pass

class IReplenishmentService(ABC):
    """补货服务接口 - 适配前端补货计划管理页面"""
    
    @abstractmethod
    def get_replenishment_plans(self, filters: Dict[str, Any] = None) -> List[ReplenishmentPlan]:
        """
        获取补货计划列表
        
        Args:
            filters: {
                'date_range': (start, end),
                'dc_id': str,
                'ecdc_id': str,
                'status': str,
                'sku_id': str
            }
        """
        pass
    
    @abstractmethod
    def adjust_replenishment_qty(self, plan_id: str, new_qty: float, 
                                  reason: str, operator: str) -> bool:
        """调整补货数量"""
        pass
    
    @abstractmethod
    def approve_plan(self, plan_id: str, reviewer: str, approved: bool, 
                     reject_reason: str = None) -> bool:
        """审核补货计划"""
        pass

class IScheduleService(ABC):
    """调度服务接口 - 适配前端车队调度页面"""
    
    @abstractmethod
    def get_schedules(self, date: str, vehicle_type: str = None) -> List[Dict[str, Any]]:
        """
        获取调度计划列表
        
        Returns:
            [{
                'vehicle_id': str,
                'driver_name': str,
                'driver_phone': str,
                'departure_time': str,
                'departure_window': str,
                'store_list': List[str],
                'estimated_duration_min': float,
                'estimated_cost': float,
                'status': str  # pending / in_progress / completed / abnormal
            }]
        """
        pass
    
    @abstractmethod
    def get_route_map_data(self, route_ids: List[str]) -> Dict[str, Any]:
        """
        获取路线地图数据（GeoJSON格式）
        
        Returns:
            {
                'routes': [RoutePlan.to_dict()],
                'store_locations': {'store_id': (lat, lng)},
                'dc_location': (lat, lng),
                'geojson': {...}  # 用于地图渲染
            }
        """
        pass
    
    @abstractmethod
    def adjust_schedule(self, vehicle_id: str, changes: Dict[str, Any], 
                        operator: str) -> Dict[str, Any]:
        """
        调整调度方案
        
        Args:
            changes: {
                'store_list': List[str],  # 新的门店列表
                'departure_time': str,
                'driver_id': str
            }
        
        Returns:
            调整前后的方案对比
        """
        pass
    
    @abstractmethod
    def get_realtime_vehicle_positions(self) -> List[Dict[str, Any]]:
        """获取车辆实时位置（用于地图展示）"""
        pass
