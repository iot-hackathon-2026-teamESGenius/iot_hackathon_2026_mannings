"""
数据Schema定义 - Mannings SLA Optimization System
统一数据接口规范，确保各模块数据一致性

Author: 王晔宸 (Team Lead)
Date: 2026-03-12
"""

from dataclasses import dataclass, field, asdict
from typing import List, Dict, Optional, Any, Tuple
from datetime import datetime, date, time
from enum import Enum
import pandas as pd


class GeocodeStatus(Enum):
    """地理编码状态枚举"""
    SUCCESS = "success"
    FAILED = "failed"
    PARTIAL = "partial"
    PENDING = "pending"


# ==================== 枚举类型定义 ====================

class District(Enum):
    """香港18区枚举"""
    CENTRAL_WESTERN = "Central and Western"
    EASTERN = "Eastern"
    SOUTHERN = "Southern"
    WAN_CHAI = "Wan Chai"
    KOWLOON_CITY = "Kowloon City"
    KWUN_TONG = "Kwun Tong"
    SHAM_SHUI_PO = "Sham Shui Po"
    WONG_TAI_SIN = "Wong Tai Sin"
    YAU_TSIM_MONG = "Yau Tsim Mong"
    ISLANDS = "Islands"
    KWAI_TSING = "Kwai Tsing"
    NORTH = "North"
    SAI_KUNG = "Sai Kung"
    SHA_TIN = "Sha Tin"
    TAI_PO = "Tai Po"
    TSUEN_WAN = "Tsuen Wan"
    TUEN_MUN = "Tuen Mun"
    YUEN_LONG = "Yuen Long"


class OrderStatus(Enum):
    """订单状态枚举"""
    CREATED = "created"              # 已创建
    READY = "ready"                  # 已确认
    ASSIGNED = "assigned"            # 已分配
    PICKING = "picking"              # 拣货中
    PICKED = "picked"                # 已拣货
    PACKED = "packed"                # 已打包
    SHIPPED = "shipped"              # 已发货
    IN_TRANSIT = "in_transit"        # 运输中
    READY_FOR_PICKUP = "ready_for_pickup"  # 待自提
    COMPLETED = "completed"          # 已完成
    CANCELLED = "cancelled"          # 已取消
    REFUNDED = "refunded"            # 已退款
    REJECTED = "rejected"            # 已拒绝
    EXPIRED = "expired"              # 已过期


class WeatherCondition(Enum):
    """天气状况枚举"""
    SUNNY = "sunny"
    CLOUDY = "cloudy"
    RAINY = "rainy"
    HEAVY_RAIN = "heavy_rain"
    TYPHOON = "typhoon"
    HOT = "hot"
    COLD = "cold"


class PromoType(Enum):
    """促销类型枚举"""
    PUBLIC_HOLIDAY = "public_holiday"
    ENJOYCARD_DAY = "enjoycard_day"
    YUU_DAY = "yuu_day"
    HAPPY_HOUR = "happy_hour"
    BABY_FAIR = "baby_fair"
    DAY_618 = "618_day"
    DOUBLE_11 = "double11_day"
    DAY_38 = "38_day"
    ANNIVERSARY = "anniversary_day"
    HH_WARE = "hh_ware_periods"


# ==================== 核心数据Schema ====================

@dataclass
class StoreSchema:
    """
    门店数据Schema
    对应: dim_store.csv
    """
    store_code: int                      # 门店代码
    district: str                        # 所属区域 (18 Districts)
    address: str                         # 详细地址
    latitude: Optional[float] = None     # 纬度 (需要地理编码补充)
    longitude: Optional[float] = None    # 经度 (需要地理编码补充)
    
    # 营业时间
    business_hours_1: Optional[Tuple[str, str]] = None  # (days, hours) e.g. ("Mon-Sun", "09:00-20:00")
    business_hours_2: Optional[Tuple[str, str]] = None
    business_hours_3: Optional[Tuple[str, str]] = None
    
    # 运营属性 (待补充)
    capacity: Optional[int] = None       # 日处理能力 (订单数)
    avg_processing_time_min: Optional[float] = None  # 平均处理时间(分钟)
    
    def to_dict(self) -> Dict:
        return asdict(self)
    
    @classmethod
    def from_csv_row(cls, row: pd.Series) -> 'StoreSchema':
        """从CSV行创建实例"""
        bh1 = None
        if pd.notna(row.get('Business Hrs 1')) and row.get('Business Hrs 1') != '---':
            bh1 = (row.get('Business Hrs 1', ''), row.get('Business Hrs 1.1', ''))
        
        return cls(
            store_code=int(row['store \ncode']) if pd.notna(row['store \ncode']) else 0,
            district=row.get('18 Districts', ''),
            address=row.get('ADDRESS', ''),
            business_hours_1=bh1
        )


@dataclass
class DateFeatureSchema:
    """
    日期特征Schema
    对应: dim_date.csv
    """
    calendar_date: date
    calendar_year: int
    calendar_month: int
    calendar_day: int
    calendar_weekday: str               # Mon, Tue, Wed...
    
    # 工作日/周末标记
    is_weekday: bool
    is_weekend: bool
    
    # 促销/节假日标记
    is_public_holiday: bool
    is_enjoycard_day: bool
    is_yuu_day: bool
    is_happy_hour: bool
    is_baby_fair: bool
    is_618_day: bool
    is_double11_day: bool
    is_38_day: bool
    is_anniversary_day: bool
    is_hh_ware_periods: bool
    
    def to_dict(self) -> Dict:
        return asdict(self)
    
    def get_active_promos(self) -> List[PromoType]:
        """获取当日活跃的促销类型"""
        promos = []
        if self.is_public_holiday: promos.append(PromoType.PUBLIC_HOLIDAY)
        if self.is_enjoycard_day: promos.append(PromoType.ENJOYCARD_DAY)
        if self.is_yuu_day: promos.append(PromoType.YUU_DAY)
        if self.is_happy_hour: promos.append(PromoType.HAPPY_HOUR)
        if self.is_baby_fair: promos.append(PromoType.BABY_FAIR)
        if self.is_618_day: promos.append(PromoType.DAY_618)
        if self.is_double11_day: promos.append(PromoType.DOUBLE_11)
        if self.is_38_day: promos.append(PromoType.DAY_38)
        if self.is_anniversary_day: promos.append(PromoType.ANNIVERSARY)
        if self.is_hh_ware_periods: promos.append(PromoType.HH_WARE)
        return promos
    
    @classmethod
    def from_csv_row(cls, row: pd.Series) -> 'DateFeatureSchema':
        """从CSV行创建实例"""
        date_str = row['calendar_date']
        parsed_date = datetime.strptime(date_str, '%Y/%m/%d').date()
        
        return cls(
            calendar_date=parsed_date,
            calendar_year=int(row['calendar_year']),
            calendar_month=int(row['calendar_month']),
            calendar_day=int(row['calendar_day']),
            calendar_weekday=row['calendar_weekday'],
            is_weekday=bool(row['if_weekday']),
            is_weekend=bool(row['if_weekend']),
            is_public_holiday=bool(row['if_public_holiday']),
            is_enjoycard_day=bool(row['if_enjoycard_day']),
            is_yuu_day=bool(row['if_yuu_day']),
            is_happy_hour=bool(row['if_happy_hour']),
            is_baby_fair=bool(row['if_baby_fair']),
            is_618_day=bool(row['if_618_day']),
            is_double11_day=bool(row['if_double11_day']),
            is_38_day=bool(row['if_38_day']),
            is_anniversary_day=bool(row['if_anniversary_day']),
            is_hh_ware_periods=bool(row['if_HH_ware_periods'])
        )


@dataclass
class OrderDetailSchema:
    """
    订单明细Schema
    对应: case_study_order_detail-000000000000.csv
    """
    dt: date                            # 订单日期
    order_id: str                       # 订单ID (hash)
    user_id: str                        # 用户ID (hash)
    fulfillment_store_code: int         # 履约门店代码
    unique_sku_cnt: int                 # 不同SKU数量
    total_quantity_cnt: float           # 总商品数量
    
    def to_dict(self) -> Dict:
        return asdict(self)
    
    @classmethod
    def from_csv_row(cls, row: pd.Series) -> 'OrderDetailSchema':
        """从CSV行创建实例"""
        return cls(
            dt=datetime.strptime(row['dt'], '%Y-%m-%d').date(),
            order_id=row['order_id'],
            user_id=row['user_id'],
            fulfillment_store_code=int(row['fulfillment_store_code']),
            unique_sku_cnt=int(row['unique_sku_cnt']),
            total_quantity_cnt=float(row['total_quantity_cnt'])
        )


@dataclass
class FulfillmentDetailSchema:
    """
    履约明细Schema - 订单全生命周期时间戳
    对应: fufillment_detail-000000000000.csv
    """
    order_id: str
    
    # 正常流程时间戳
    order_create_time: Optional[datetime] = None
    ready_time: Optional[datetime] = None
    assigned_time: Optional[datetime] = None
    picking_time: Optional[datetime] = None
    picked_time: Optional[datetime] = None
    packed_time: Optional[datetime] = None
    shipped_time: Optional[datetime] = None
    in_transit_time: Optional[datetime] = None
    ready_for_pickup_time: Optional[datetime] = None
    completed_time: Optional[datetime] = None
    
    # 异常状态时间戳
    cancel_time: Optional[datetime] = None
    refund_time: Optional[datetime] = None
    rejected_time: Optional[datetime] = None
    rejected_returned_time: Optional[datetime] = None
    expired_time: Optional[datetime] = None
    expired_returned_time: Optional[datetime] = None
    retry_time: Optional[datetime] = None
    retry_returned_time: Optional[datetime] = None
    
    def get_status(self) -> OrderStatus:
        """根据时间戳推断当前状态"""
        if self.completed_time:
            return OrderStatus.COMPLETED
        if self.cancel_time:
            return OrderStatus.CANCELLED
        if self.refund_time:
            return OrderStatus.REFUNDED
        if self.rejected_time:
            return OrderStatus.REJECTED
        if self.expired_time:
            return OrderStatus.EXPIRED
        if self.ready_for_pickup_time:
            return OrderStatus.READY_FOR_PICKUP
        if self.in_transit_time:
            return OrderStatus.IN_TRANSIT
        if self.shipped_time:
            return OrderStatus.SHIPPED
        if self.packed_time:
            return OrderStatus.PACKED
        if self.picked_time:
            return OrderStatus.PICKED
        if self.picking_time:
            return OrderStatus.PICKING
        if self.assigned_time:
            return OrderStatus.ASSIGNED
        if self.ready_time:
            return OrderStatus.READY
        return OrderStatus.CREATED
    
    def calculate_sla_metrics(self) -> Dict[str, Optional[float]]:
        """计算SLA相关指标 (分钟)"""
        metrics = {}
        
        # 订单到可提货时间
        if self.order_create_time and self.ready_for_pickup_time:
            delta = self.ready_for_pickup_time - self.order_create_time
            metrics['order_to_pickup_ready_min'] = delta.total_seconds() / 60
        
        # 拣货时间
        if self.picking_time and self.picked_time:
            delta = self.picked_time - self.picking_time
            metrics['picking_duration_min'] = delta.total_seconds() / 60
        
        # 打包时间
        if self.picked_time and self.packed_time:
            delta = self.packed_time - self.picked_time
            metrics['packing_duration_min'] = delta.total_seconds() / 60
        
        # 配送时间
        if self.shipped_time and self.ready_for_pickup_time:
            delta = self.ready_for_pickup_time - self.shipped_time
            metrics['delivery_duration_min'] = delta.total_seconds() / 60
        
        # 客户提货时间
        if self.ready_for_pickup_time and self.completed_time:
            delta = self.completed_time - self.ready_for_pickup_time
            metrics['customer_pickup_duration_min'] = delta.total_seconds() / 60
        
        return metrics
    
    def to_dict(self) -> Dict:
        return asdict(self)
    
    @classmethod
    def from_csv_row(cls, row: pd.Series) -> 'FulfillmentDetailSchema':
        """从CSV行创建实例"""
        def parse_datetime(val):
            if pd.isna(val) or val == '':
                return None
            try:
                return datetime.strptime(str(val), '%Y-%m-%d %H:%M:%S')
            except:
                return None
        
        return cls(
            order_id=row['order_id'],
            order_create_time=parse_datetime(row.get('order_create_time')),
            ready_time=parse_datetime(row.get('ready_time')),
            assigned_time=parse_datetime(row.get('assigned_time')),
            picking_time=parse_datetime(row.get('picking_time')),
            picked_time=parse_datetime(row.get('picked_time')),
            packed_time=parse_datetime(row.get('packed_time')),
            shipped_time=parse_datetime(row.get('shipped_time')),
            in_transit_time=parse_datetime(row.get('in_transit_time')),
            ready_for_pickup_time=parse_datetime(row.get('ready_for_pickup_time')),
            completed_time=parse_datetime(row.get('completed_time')),
            cancel_time=parse_datetime(row.get('cancel_time')),
            refund_time=parse_datetime(row.get('refund_time')),
            rejected_time=parse_datetime(row.get('rejected_time')),
            rejected_returned_time=parse_datetime(row.get('rejected_returned_time')),
            expired_time=parse_datetime(row.get('expired_time')),
            expired_returned_time=parse_datetime(row.get('expired_returned_time')),
            retry_time=parse_datetime(row.get('retry_time')),
            retry_returned_time=parse_datetime(row.get('retry_returned_time'))
        )


# ==================== 外部数据Schema ====================

@dataclass
class WeatherDataSchema:
    """
    天气数据Schema
    来源: Hong Kong Observatory API
    """
    date: date
    location: Optional[str] = None      # 观测站位置
    
    # 基础天气数据
    temperature_max: Optional[float] = None   # 最高温度 (°C)
    temperature_min: Optional[float] = None   # 最低温度 (°C)
    temperature_avg: Optional[float] = None   # 平均温度 (°C)
    humidity: Optional[float] = None          # 相对湿度 (%)
    rainfall: Optional[float] = None          # 降雨量 (mm)
    
    # 天气状况
    weather_condition: Optional[WeatherCondition] = None
    weather_icon: Optional[int] = None        # HKO天气图标代码
    
    # 预警信号
    has_typhoon_signal: bool = False
    has_rainstorm_warning: bool = False
    has_hot_weather_warning: bool = False
    has_cold_weather_warning: bool = False
    
    def get_demand_impact_factor(self) -> float:
        """
        根据天气计算需求影响因子
        返回: 1.0为基准, >1.0表示需求增加, <1.0表示需求减少
        """
        factor = 1.0
        
        # 台风/暴雨显著降低需求
        if self.has_typhoon_signal:
            factor *= 0.3
        elif self.has_rainstorm_warning:
            factor *= 0.6
        elif self.weather_condition == WeatherCondition.HEAVY_RAIN:
            factor *= 0.7
        elif self.weather_condition == WeatherCondition.RAINY:
            factor *= 0.85
        
        # 极端温度影响
        if self.temperature_max and self.temperature_max > 33:
            factor *= 0.9  # 高温略降需求
        elif self.temperature_min and self.temperature_min < 10:
            factor *= 0.95  # 低温略降需求
        
        return factor
    
    def to_dict(self) -> Dict:
        result = asdict(self)
        if self.weather_condition:
            result['weather_condition'] = self.weather_condition.value
        return result


@dataclass
class PublicHolidaySchema:
    """
    公众假期Schema
    来源: data.gov.hk
    """
    date: date
    name_en: str                        # 英文名称
    name_tc: Optional[str] = None       # 繁体中文名称
    name_sc: Optional[str] = None       # 简体中文名称
    is_statutory: bool = True           # 是否为法定假期
    
    def to_dict(self) -> Dict:
        return asdict(self)


# ==================== 预测与规划输出Schema ====================

@dataclass
class DemandForecastSchema:
    """需求预测输出Schema"""
    store_code: int
    forecast_date: date
    
    # 预测值
    predicted_orders: float             # 预测订单数
    predicted_quantity: float           # 预测商品数量
    
    # 置信区间
    p10: float                          # 10%分位数 (下界)
    p50: float                          # 50%分位数 (中位数)
    p90: float                          # 90%分位数 (上界)
    
    # 元信息
    model_version: Optional[str] = None
    forecast_timestamp: Optional[datetime] = None
    
    # 特征贡献
    weather_impact: Optional[float] = None
    promo_impact: Optional[float] = None
    weekday_impact: Optional[float] = None
    
    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class RouteStopSchema:
    """路线停靠点Schema"""
    sequence: int                       # 停靠顺序 (0=起点/DC)
    store_code: int                     # 门店代码
    
    # 位置信息
    latitude: float
    longitude: float
    
    # 时间信息
    arrival_time: Optional[datetime] = None
    departure_time: Optional[datetime] = None
    service_time_min: Optional[float] = None
    
    # 需求信息
    demand: Optional[float] = None
    
    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class RoutePlanSchema:
    """路线规划输出Schema"""
    route_id: str
    vehicle_id: str
    
    # 路线详情
    stops: List[RouteStopSchema] = field(default_factory=list)
    
    # 汇总指标
    total_distance_km: float = 0.0
    total_duration_min: float = 0.0
    total_demand: float = 0.0
    num_stops: int = 0
    
    # SLA风险
    sla_risk_score: float = 0.0         # 0-1, 越高风险越大
    estimated_delay_min: float = 0.0
    
    # 场景信息 (鲁棒优化)
    scenario_name: Optional[str] = None
    scenario_ratio: Optional[float] = None
    
    def to_dict(self) -> Dict:
        result = asdict(self)
        result['stops'] = [s.to_dict() if hasattr(s, 'to_dict') else s for s in self.stops]
        return result


@dataclass
class SLAPredictionSchema:
    """SLA预测输出Schema"""
    order_id: str
    store_code: int
    
    # 预测时间
    predicted_ready_time: datetime
    predicted_pickup_time: datetime
    
    # 置信区间 (分钟)
    confidence_interval_min: float      # 下界
    confidence_interval_max: float      # 上界
    
    # SLA达成概率
    sla_achievement_probability: float
    
    # 可选参数 (必须在必填参数之后)
    confidence_level: float = 0.95      # 置信水平
    risk_factors: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict:
        return asdict(self)


# ==================== 数据加载器接口 ====================

class DataLoaderInterface:
    """数据加载器接口规范"""
    
    def load_stores(self) -> List[StoreSchema]:
        """加载门店数据"""
        raise NotImplementedError
    
    def load_date_features(self, start_date: date, end_date: date) -> List[DateFeatureSchema]:
        """加载日期特征"""
        raise NotImplementedError
    
    def load_orders(self, start_date: date, end_date: date, 
                    store_codes: Optional[List[int]] = None) -> List[OrderDetailSchema]:
        """加载订单数据"""
        raise NotImplementedError
    
    def load_fulfillment(self, order_ids: Optional[List[str]] = None) -> List[FulfillmentDetailSchema]:
        """加载履约数据"""
        raise NotImplementedError
    
    def load_weather(self, start_date: date, end_date: date) -> List[WeatherDataSchema]:
        """加载天气数据"""
        raise NotImplementedError
    
    def load_holidays(self, year: int) -> List[PublicHolidaySchema]:
        """加载公众假期"""
        raise NotImplementedError


# ==================== 数据验证工具 ====================

def validate_store_data(stores: List[StoreSchema]) -> Dict[str, Any]:
    """验证门店数据质量"""
    report = {
        'total_count': len(stores),
        'missing_coordinates': 0,
        'missing_business_hours': 0,
        'districts': set()
    }
    
    for store in stores:
        if store.latitude is None or store.longitude is None:
            report['missing_coordinates'] += 1
        if store.business_hours_1 is None:
            report['missing_business_hours'] += 1
        report['districts'].add(store.district)
    
    report['districts'] = list(report['districts'])
    report['coordinate_coverage'] = (report['total_count'] - report['missing_coordinates']) / report['total_count'] * 100
    
    return report


def validate_fulfillment_data(fulfillments: List[FulfillmentDetailSchema]) -> Dict[str, Any]:
    """验证履约数据质量"""
    report = {
        'total_count': len(fulfillments),
        'status_distribution': {},
        'avg_order_to_pickup_min': None,
        'sla_metrics': []
    }
    
    order_to_pickup_times = []
    
    for f in fulfillments:
        status = f.get_status()
        report['status_distribution'][status.value] = report['status_distribution'].get(status.value, 0) + 1
        
        metrics = f.calculate_sla_metrics()
        if 'order_to_pickup_ready_min' in metrics:
            order_to_pickup_times.append(metrics['order_to_pickup_ready_min'])
    
    if order_to_pickup_times:
        import statistics
        report['avg_order_to_pickup_min'] = statistics.mean(order_to_pickup_times)
        report['median_order_to_pickup_min'] = statistics.median(order_to_pickup_times)
    
    return report

# ==================== Vehicle and Traffic Schemas ====================

@dataclass
class DeliveryVehicle:
    """配送车辆信息"""
    vehicle_id: str
    capacity: float                     # 载重量
    current_location: Tuple[float, float]  # (latitude, longitude)
    max_distance_km: Optional[float] = None
    max_duration_hours: Optional[float] = None
    cost_per_km: Optional[float] = None
    driver_id: Optional[str] = None
    vehicle_type: Optional[str] = None
    
    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class TrafficCondition:
    """交通状况信息"""
    timestamp: datetime
    road_segment: str
    speed_kmh: float
    congestion_level: int               # 1-5, 1=free flow, 5=severe congestion
    travel_time_factor: float           # 相对于自由流动的时间倍数
    incident_reported: bool = False
    incident_description: Optional[str] = None
    
    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class WeatherData:
    """天气数据 (简化版本，用于算法接口)"""
    date: date
    temperature_high: Optional[float] = None
    temperature_low: Optional[float] = None
    humidity: Optional[float] = None
    rainfall: Optional[float] = None
    weather_condition: Optional[WeatherCondition] = None
    impact_factor: float = 1.0          # 对需求的影响因子
    
    def to_dict(self) -> Dict:
        result = asdict(self)
        if self.weather_condition:
            result['weather_condition'] = self.weather_condition.value
        return result


@dataclass
class PublicHoliday:
    """公众假期 (简化版本，用于算法接口)"""
    date: date
    name: str
    impact_factor: float = 1.2          # 对需求的影响因子
    
    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class SLAForecast:
    """SLA预测结果"""
    store_code: str
    forecast_date: date
    predicted_sla_rate: float           # 预测SLA达成率 (0-1)
    confidence_interval: Tuple[float, float]  # (lower, upper)
    risk_factors: List[str] = field(default_factory=list)
    improvement_recommendations: List[str] = field(default_factory=list)
    forecast_timestamp: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict:
        return asdict(self)


# ==================== Routing and Optimization Schemas ====================

@dataclass
class OrderItem:
    """订单项目"""
    sku_id: str
    sku_name: str
    quantity: int
    unit_price: Optional[float] = None
    
    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class OrderDetail:
    """订单详情"""
    order_id: str
    user_id: str
    fulfillment_store_code: str
    order_date: date
    items: List[OrderItem]
    total_quantity: int
    unique_sku_count: int
    total_amount: Optional[float] = None
    priority: int = 1
    
    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class StoreLocation:
    """店铺位置信息"""
    store_code: str
    latitude: float
    longitude: float
    district: str
    address: str
    geocode_status: str
    accuracy_note: Optional[str] = None
    
    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class RouteOptimizationResult:
    """路径优化结果"""
    scenario_id: str
    vehicle_routes: Dict[str, List[str]]  # vehicle_id -> [store_codes]
    total_distance: float
    total_time: float
    total_cost: float
    sla_compliance_rate: float
    optimization_timestamp: datetime
    solver_status: str
    
    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class DeliveryScenario:
    """配送场景"""
    scenario_id: str
    orders: List[OrderDetail]
    demand_forecast: Dict[str, float]  # store_code -> demand_multiplier
    weather_impact: float
    traffic_impact: float
    probability: float
    generated_timestamp: datetime
    
    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class RobustOptimizationResult:
    """鲁棒优化结果"""
    scenarios: List[DeliveryScenario]
    route_results: List[RouteOptimizationResult]
    selected_route: RouteOptimizationResult
    selection_strategy: str
    robustness_score: float
    confidence_level: float
    optimization_timestamp: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class DemandForecast:
    """需求预测结果"""
    store_code: str
    sku_id: str
    forecast_date: date
    predicted_demand: float
    confidence_intervals: Dict[str, float]  # {"P10": 10, "P50": 15, "P90": 25}
    external_factors: Dict[str, float]  # {"weather_impact": 0.1, "holiday_impact": 0.3}
    model_version: str
    forecast_timestamp: datetime
    
    def to_dict(self) -> Dict:
        return asdict(self)


# ==================== Data Conversion Functions ====================

def dataframe_to_store_locations(df: pd.DataFrame) -> List[StoreLocation]:
    """Convert DataFrame to StoreLocation objects"""
    locations = []
    for _, row in df.iterrows():
        location = StoreLocation(
            store_code=str(row.get('store_code', '')),
            latitude=float(row.get('latitude', 0.0)),
            longitude=float(row.get('longitude', 0.0)),
            district=str(row.get('district', '')),
            address=str(row.get('address', '')),
            geocode_status=str(row.get('geocode_status', 'success')),
            accuracy_note=row.get('accuracy_note')
        )
        locations.append(location)
    return locations


def dataframe_to_order_details(df: pd.DataFrame) -> List[OrderDetail]:
    """Convert DataFrame to OrderDetail objects"""
    orders = []
    for _, row in df.iterrows():
        # Create order items (simplified)
        items = [OrderItem(
            sku_id=f"SKU_{i}",
            sku_name=f"Product {i}",
            quantity=1
        ) for i in range(int(row.get('unique_sku_cnt', 1)))]
        
        order = OrderDetail(
            order_id=str(row.get('order_id', '')),
            user_id=str(row.get('user_id', '')),
            fulfillment_store_code=str(row.get('fulfillment_store_code', '')),
            order_date=pd.to_datetime(row.get('dt')).date() if 'dt' in row else date.today(),
            items=items,
            total_quantity=int(row.get('total_quantity_cnt', 0)),
            unique_sku_count=int(row.get('unique_sku_cnt', 0))
        )
        orders.append(order)
    return orders