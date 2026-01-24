"""
模块化架构的核心接口定义
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from datetime import datetime
import pandas as pd

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
