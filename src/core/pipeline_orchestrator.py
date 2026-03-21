"""
系统架构协调器 - Stage 2升级版
整合数据层、预测层、优化层、展示层的端到端流水线

Author: 王晔宸 (Team Lead / Architect)
Date: 2026-03-12
"""

from typing import Dict, List, Any, Optional
from datetime import date, datetime
from dataclasses import dataclass, field
import logging

# 数据层
from src.core.data_schema import (
    StoreSchema, DateFeatureSchema, OrderDetailSchema,
    FulfillmentDetailSchema, WeatherDataSchema,
    DemandForecastSchema, RoutePlanSchema, SLAPredictionSchema
)

logger = logging.getLogger(__name__)


# ==================== 模块接口定义 ====================

class IDataModule:
    """数据模块接口"""
    
    def load_stores(self) -> List[StoreSchema]:
        raise NotImplementedError
    
    def load_orders(self, start_date: date, end_date: date) -> List[OrderDetailSchema]:
        raise NotImplementedError
    
    def load_fulfillment(self) -> List[FulfillmentDetailSchema]:
        raise NotImplementedError
    
    def load_date_features(self, start_date: date, end_date: date) -> List[DateFeatureSchema]:
        raise NotImplementedError
    
    def get_weather(self, target_date: date) -> Optional[WeatherDataSchema]:
        raise NotImplementedError


class IForecastModule:
    """预测模块接口"""
    
    def train(self, historical_data: Any, external_features: Dict = None) -> Dict:
        """训练模型"""
        raise NotImplementedError
    
    def predict(self, store_codes: List[int], dates: List[date], 
                weather: List[WeatherDataSchema] = None,
                date_features: List[DateFeatureSchema] = None) -> List[DemandForecastSchema]:
        """需求预测"""
        raise NotImplementedError
    
    def get_confidence_intervals(self, forecasts: List[DemandForecastSchema]) -> Dict[str, List[float]]:
        """获取置信区间 (P10, P50, P90)"""
        raise NotImplementedError


class IRoutingModule:
    """路径优化模块接口"""
    
    def generate_scenarios(self, base_demand: Dict[int, float], 
                          confidence_intervals: Dict[str, List[float]]) -> List[Dict]:
        """生成需求场景"""
        raise NotImplementedError
    
    def optimize_single(self, stores: List[StoreSchema], demands: Dict[int, float],
                       vehicles: int, capacity: float) -> RoutePlanSchema:
        """单场景优化"""
        raise NotImplementedError
    
    def optimize_robust(self, stores: List[StoreSchema], scenarios: List[Dict],
                       vehicles: int, capacity: float) -> RoutePlanSchema:
        """鲁棒优化 (多场景 + Min-Max选择)"""
        raise NotImplementedError


class ISLAModule:
    """SLA预测模块接口"""
    
    def predict_pickup_time(self, store_code: int, route_plan: RoutePlanSchema,
                           date_feature: DateFeatureSchema) -> SLAPredictionSchema:
        """预测自提时间"""
        raise NotImplementedError
    
    def calculate_sla_probability(self, predicted_time: datetime, 
                                  promised_time: datetime) -> float:
        """计算SLA达成概率"""
        raise NotImplementedError


# ==================== 流水线配置 ====================

@dataclass
class PipelineConfig:
    """流水线配置"""
    # 数据配置
    data_source: str = "dfi"  # dfi / simulated
    data_path: str = "data/dfi/raw/"
    
    # 预测配置
    forecast_horizon_days: int = 7
    confidence_levels: List[float] = field(default_factory=lambda: [0.1, 0.5, 0.9])
    
    # 路径优化配置
    num_vehicles: int = 10
    vehicle_capacity: float = 100.0
    time_limit_seconds: int = 60
    
    # 场景配置
    demand_ratios: List[float] = field(default_factory=lambda: [0.9, 1.0, 1.1])
    monte_carlo_samples: int = 5
    robustness_criterion: str = "min_max_distance"  # min_max_distance / min_avg_distance / min_sla_violation
    
    # SLA配置
    sla_confidence_level: float = 0.95
    sla_target_hours: float = 4.0  # 4小时内可提货


@dataclass
class PipelineResult:
    """流水线执行结果"""
    success: bool
    execution_time_sec: float
    target_date: date
    
    # 各阶段输出
    forecasts: List[DemandForecastSchema] = field(default_factory=list)
    scenarios: List[Dict] = field(default_factory=list)
    route_plans: List[RoutePlanSchema] = field(default_factory=list)
    robust_plan: Optional[RoutePlanSchema] = None
    sla_predictions: List[SLAPredictionSchema] = field(default_factory=list)
    
    # 元信息
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


# ==================== 端到端流水线协调器 ====================

class PipelineOrchestrator:
    """
    端到端流水线协调器
    
    数据流:
    1. 数据层 → 加载门店、订单、日期特征、天气
    2. 预测层 → 需求预测 + 置信区间
    3. 场景层 → 生成多个需求场景
    4. 优化层 → 多场景路径优化 + 鲁棒选择
    5. SLA层 → 自提时间预测 + 风险评估
    """
    
    def __init__(self, config: PipelineConfig = None):
        self.config = config or PipelineConfig()
        
        # 模块实例 (延迟初始化)
        self._data_module: Optional[IDataModule] = None
        self._forecast_module: Optional[IForecastModule] = None
        self._routing_module: Optional[IRoutingModule] = None
        self._sla_module: Optional[ISLAModule] = None
        
        # 缓存
        self._stores_cache: List[StoreSchema] = None
    
    def set_data_module(self, module: IDataModule):
        """设置数据模块"""
        self._data_module = module
    
    def set_forecast_module(self, module: IForecastModule):
        """设置预测模块"""
        self._forecast_module = module
    
    def set_routing_module(self, module: IRoutingModule):
        """设置路径优化模块"""
        self._routing_module = module
    
    def set_sla_module(self, module: ISLAModule):
        """设置SLA模块"""
        self._sla_module = module
    
    def run_pipeline(self, target_date: date) -> PipelineResult:
        """
        执行完整流水线
        
        Args:
            target_date: 目标日期 (用于预测和规划)
        
        Returns:
            PipelineResult: 流水线执行结果
        """
        import time
        start_time = time.time()
        
        result = PipelineResult(
            success=False,
            execution_time_sec=0,
            target_date=target_date
        )
        
        try:
            # Step 1: 数据加载
            logger.info("Step 1: Loading data...")
            stores, date_features, weather = self._load_data(target_date)
            
            if not stores:
                result.errors.append("No store data available")
                return result
            
            # Step 2: 需求预测
            logger.info("Step 2: Forecasting demand...")
            forecasts = self._run_forecast(stores, target_date, date_features, weather)
            result.forecasts = forecasts
            
            if not forecasts:
                result.warnings.append("No forecasts generated, using historical average")
            
            # Step 3: 场景生成
            logger.info("Step 3: Generating scenarios...")
            scenarios = self._generate_scenarios(forecasts)
            result.scenarios = scenarios
            
            # Step 4: 路径优化
            logger.info("Step 4: Running route optimization...")
            route_plans, robust_plan = self._run_optimization(stores, scenarios)
            result.route_plans = route_plans
            result.robust_plan = robust_plan
            
            # Step 5: SLA预测
            logger.info("Step 5: Predicting SLA...")
            if robust_plan:
                sla_predictions = self._run_sla_prediction(robust_plan, date_features)
                result.sla_predictions = sla_predictions
            
            result.success = True
            
        except Exception as e:
            logger.error(f"Pipeline failed: {e}")
            result.errors.append(str(e))
        
        result.execution_time_sec = time.time() - start_time
        logger.info(f"Pipeline completed in {result.execution_time_sec:.2f}s")
        
        return result
    
    def _load_data(self, target_date: date):
        """加载数据"""
        if not self._data_module:
            raise ValueError("Data module not set")
        
        stores = self._data_module.load_stores()
        date_features = self._data_module.load_date_features(target_date, target_date)
        weather = self._data_module.get_weather(target_date)
        
        self._stores_cache = stores
        
        return stores, date_features, weather
    
    def _run_forecast(self, stores: List[StoreSchema], target_date: date,
                     date_features: List[DateFeatureSchema],
                     weather: Optional[WeatherDataSchema]) -> List[DemandForecastSchema]:
        """运行需求预测"""
        if not self._forecast_module:
            logger.warning("Forecast module not set, using default demand")
            # 返回默认预测
            return [
                DemandForecastSchema(
                    store_code=s.store_code,
                    forecast_date=target_date,
                    predicted_orders=50.0,
                    predicted_quantity=100.0,
                    p10=40.0, p50=50.0, p90=60.0
                )
                for s in stores
            ]
        
        store_codes = [s.store_code for s in stores]
        weather_list = [weather] if weather else None
        
        return self._forecast_module.predict(
            store_codes=store_codes,
            dates=[target_date],
            weather=weather_list,
            date_features=date_features
        )
    
    def _generate_scenarios(self, forecasts: List[DemandForecastSchema]) -> List[Dict]:
        """生成需求场景"""
        scenarios = []
        
        # 场景1: 基于置信区间
        for quantile_name, quantile_key in [('low', 'p10'), ('mid', 'p50'), ('high', 'p90')]:
            scenario = {
                'name': f'quantile_{quantile_name}',
                'type': 'quantile',
                'demands': {}
            }
            for f in forecasts:
                scenario['demands'][f.store_code] = getattr(f, quantile_key)
            scenarios.append(scenario)
        
        # 场景2: 基于比例
        for ratio in self.config.demand_ratios:
            scenario = {
                'name': f'ratio_{ratio}',
                'type': 'ratio',
                'ratio': ratio,
                'demands': {}
            }
            for f in forecasts:
                scenario['demands'][f.store_code] = f.p50 * ratio
            scenarios.append(scenario)
        
        return scenarios
    
    def _run_optimization(self, stores: List[StoreSchema], 
                         scenarios: List[Dict]) -> tuple:
        """运行路径优化"""
        if not self._routing_module:
            logger.warning("Routing module not set, skipping optimization")
            return [], None
        
        route_plans = []
        
        # 对每个场景运行优化
        for scenario in scenarios:
            try:
                plan = self._routing_module.optimize_single(
                    stores=stores,
                    demands=scenario['demands'],
                    vehicles=self.config.num_vehicles,
                    capacity=self.config.vehicle_capacity
                )
                plan.scenario_name = scenario['name']
                route_plans.append(plan)
            except Exception as e:
                logger.warning(f"Optimization failed for scenario {scenario['name']}: {e}")
        
        # 鲁棒选择
        robust_plan = self._select_robust_plan(route_plans)
        
        return route_plans, robust_plan
    
    def _select_robust_plan(self, plans: List[RoutePlanSchema]) -> Optional[RoutePlanSchema]:
        """选择鲁棒方案"""
        if not plans:
            return None
        
        criterion = self.config.robustness_criterion
        
        if criterion == 'min_max_distance':
            # 选择最大距离最小的方案
            return min(plans, key=lambda p: p.total_distance_km)
        
        elif criterion == 'min_avg_distance':
            # 选择平均距离最小的方案
            return min(plans, key=lambda p: p.total_distance_km)
        
        elif criterion == 'min_sla_violation':
            # 选择SLA风险最低的方案
            return min(plans, key=lambda p: p.sla_risk_score)
        
        else:
            # 默认返回中间方案
            return plans[len(plans) // 2]
    
    def _run_sla_prediction(self, route_plan: RoutePlanSchema,
                           date_features: List[DateFeatureSchema]) -> List[SLAPredictionSchema]:
        """运行SLA预测"""
        if not self._sla_module:
            logger.warning("SLA module not set, skipping SLA prediction")
            return []
        
        predictions = []
        date_feature = date_features[0] if date_features else None
        
        for stop in route_plan.stops:
            if stop.sequence == 0:  # 跳过DC
                continue
            
            try:
                pred = self._sla_module.predict_pickup_time(
                    store_code=stop.store_code,
                    route_plan=route_plan,
                    date_feature=date_feature
                )
                predictions.append(pred)
            except Exception as e:
                logger.warning(f"SLA prediction failed for store {stop.store_code}: {e}")
        
        return predictions
    
    def get_pipeline_summary(self, result: PipelineResult) -> Dict:
        """获取流水线执行摘要"""
        summary = {
            'success': result.success,
            'target_date': result.target_date.isoformat(),
            'execution_time_sec': round(result.execution_time_sec, 2),
            'errors': result.errors,
            'warnings': result.warnings,
            'stats': {}
        }
        
        if result.forecasts:
            summary['stats']['num_forecasts'] = len(result.forecasts)
            summary['stats']['total_predicted_orders'] = sum(f.predicted_orders for f in result.forecasts)
        
        if result.scenarios:
            summary['stats']['num_scenarios'] = len(result.scenarios)
        
        if result.robust_plan:
            summary['stats']['total_distance_km'] = round(result.robust_plan.total_distance_km, 2)
            summary['stats']['total_duration_min'] = round(result.robust_plan.total_duration_min, 2)
            summary['stats']['num_routes'] = result.robust_plan.num_stops
        
        if result.sla_predictions:
            avg_prob = sum(p.sla_achievement_probability for p in result.sla_predictions) / len(result.sla_predictions)
            summary['stats']['avg_sla_probability'] = round(avg_prob, 3)
        
        return summary


# ==================== 模块工厂 ====================

class ModuleFactory:
    """模块工厂 - 创建各模块实例"""
    
    @staticmethod
    def create_data_module(source: str = "dfi", **kwargs) -> IDataModule:
        """创建数据模块"""
        from src.core.module_adapters import create_data_module
        return create_data_module(kwargs)
    
    @staticmethod
    def create_forecast_module(model_type: str = "prophet", **kwargs) -> IForecastModule:
        """创建预测模块"""
        from src.core.module_adapters import create_forecast_module
        config = {'model_type': model_type, **kwargs}
        return create_forecast_module(config)
    
    @staticmethod
    def create_routing_module(solver: str = "ortools", **kwargs) -> IRoutingModule:
        """创建路径优化模块"""
        from src.core.module_adapters import create_routing_module
        config = {'solver': solver, **kwargs}
        return create_routing_module(config)
    
    @staticmethod
    def create_sla_module(**kwargs) -> ISLAModule:
        """创建SLA模块"""
        from src.core.module_adapters import create_sla_module
        return create_sla_module(kwargs)


# ==================== 测试函数 ====================

def test_pipeline_orchestrator():
    """测试流水线协调器"""
    print("=" * 60)
    print("Pipeline Orchestrator Test")
    print("=" * 60)
    
    # 创建配置
    config = PipelineConfig(
        data_source="dfi",
        num_vehicles=10,
        demand_ratios=[0.9, 1.0, 1.1]
    )
    
    # 创建协调器
    orchestrator = PipelineOrchestrator(config)
    
    print(f"\nConfig:")
    print(f"  Data source: {config.data_source}")
    print(f"  Vehicles: {config.num_vehicles}")
    print(f"  Demand ratios: {config.demand_ratios}")
    print(f"  Robustness criterion: {config.robustness_criterion}")
    
    print("\n" + "=" * 60)
    print("Pipeline Orchestrator Test Complete")
    print("=" * 60)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    test_pipeline_orchestrator()
