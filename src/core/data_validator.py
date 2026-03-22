"""
数据验证模块 - Mannings SLA Optimization System
实现数据完整性、地理边界、安全性验证

Author: 王晔宸 (Team Lead)
Date: 2026-02-12
"""

import re
import logging
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, date
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


# ==================== 香港地理边界 ====================

HK_BOUNDS = {
    'lat_min': 22.15,
    'lat_max': 22.56,
    'lng_min': 113.82,
    'lng_max': 114.45
}

HK_DISTRICTS = [
    "Central and Western", "Eastern", "Southern", "Wan Chai",
    "Kowloon City", "Kwun Tong", "Sham Shui Po", "Wong Tai Sin", "Yau Tsim Mong",
    "Islands", "Kwai Tsing", "North", "Sai Kung", "Sha Tin",
    "Tai Po", "Tsuen Wan", "Tuen Mun", "Yuen Long"
]


# ==================== 验证结果数据类 ====================

@dataclass
class ValidationResult:
    """验证结果"""
    is_valid: bool
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    sanitized_data: Any = None
    
    def add_error(self, msg: str):
        self.errors.append(msg)
        self.is_valid = False
    
    def add_warning(self, msg: str):
        self.warnings.append(msg)
    
    def merge(self, other: 'ValidationResult'):
        """合并另一个验证结果"""
        self.is_valid = self.is_valid and other.is_valid
        self.errors.extend(other.errors)
        self.warnings.extend(other.warnings)


# ==================== 地理验证 ====================

class GeographicValidator:
    """香港地理坐标验证器"""
    
    @staticmethod
    def validate_coordinates(lat: float, lng: float) -> ValidationResult:
        """验证坐标是否在香港范围内"""
        result = ValidationResult(is_valid=True)
        
        if lat is None or lng is None:
            result.add_warning("坐标为空")
            return result
        
        if not isinstance(lat, (int, float)) or not isinstance(lng, (int, float)):
            result.add_error(f"坐标类型错误: lat={type(lat)}, lng={type(lng)}")
            return result
        
        if not (HK_BOUNDS['lat_min'] <= lat <= HK_BOUNDS['lat_max']):
            result.add_error(f"纬度超出香港范围: {lat} (应在{HK_BOUNDS['lat_min']}-{HK_BOUNDS['lat_max']})")
        
        if not (HK_BOUNDS['lng_min'] <= lng <= HK_BOUNDS['lng_max']):
            result.add_error(f"经度超出香港范围: {lng} (应在{HK_BOUNDS['lng_min']}-{HK_BOUNDS['lng_max']})")
        
        return result
    
    @staticmethod
    def validate_district(district: str) -> ValidationResult:
        """验证区域名称"""
        result = ValidationResult(is_valid=True)
        
        if not district:
            result.add_warning("区域为空")
            return result
        
        # 模糊匹配
        district_lower = district.lower().strip()
        matched = False
        for valid_district in HK_DISTRICTS:
            if valid_district.lower() in district_lower or district_lower in valid_district.lower():
                matched = True
                break
        
        if not matched:
            result.add_warning(f"未识别的区域: {district}")
        
        return result
    
    @staticmethod
    def estimate_coordinates_from_district(district: str) -> Tuple[float, float]:
        """根据区域估算中心坐标"""
        district_centers = {
            "Central and Western": (22.2860, 114.1510),
            "Eastern": (22.2840, 114.2240),
            "Southern": (22.2470, 114.1580),
            "Wan Chai": (22.2780, 114.1710),
            "Kowloon City": (22.3280, 114.1910),
            "Kwun Tong": (22.3120, 114.2260),
            "Sham Shui Po": (22.3310, 114.1620),
            "Wong Tai Sin": (22.3420, 114.1930),
            "Yau Tsim Mong": (22.3210, 114.1700),
            "Islands": (22.2610, 113.9450),
            "Kwai Tsing": (22.3570, 114.1270),
            "North": (22.4940, 114.1380),
            "Sai Kung": (22.3830, 114.2710),
            "Sha Tin": (22.3870, 114.1950),
            "Tai Po": (22.4510, 114.1680),
            "Tsuen Wan": (22.3710, 114.1140),
            "Tuen Mun": (22.3910, 113.9770),
            "Yuen Long": (22.4450, 114.0220)
        }
        
        district_lower = district.lower().strip() if district else ""
        for name, coords in district_centers.items():
            if name.lower() in district_lower or district_lower in name.lower():
                return coords
        
        # 默认返回香港中心
        return (22.3193, 114.1694)


# ==================== 订单数据验证 ====================

class OrderValidator:
    """订单数据验证器"""
    
    @staticmethod
    def validate_order_id(order_id: str) -> ValidationResult:
        """验证订单ID"""
        result = ValidationResult(is_valid=True)
        
        if not order_id:
            result.add_error("订单ID为空")
            return result
        
        if len(order_id) < 3:
            result.add_error(f"订单ID过短: {order_id}")
        
        return result
    
    @staticmethod
    def validate_quantity(quantity: float) -> ValidationResult:
        """验证数量"""
        result = ValidationResult(is_valid=True)
        
        if quantity is None:
            result.add_error("数量为空")
            return result
        
        if quantity <= 0:
            result.add_error(f"数量必须为正数: {quantity}")
        elif quantity > 10000:
            result.add_warning(f"数量异常大: {quantity}")
        
        return result
    
    @staticmethod
    def validate_store_code(store_code: int) -> ValidationResult:
        """验证门店代码"""
        result = ValidationResult(is_valid=True)
        
        if store_code is None:
            result.add_error("门店代码为空")
            return result
        
        if not isinstance(store_code, int):
            try:
                store_code = int(store_code)
            except:
                result.add_error(f"门店代码格式错误: {store_code}")
                return result
        
        if store_code <= 0:
            result.add_error(f"门店代码必须为正数: {store_code}")
        
        return result
    
    @staticmethod
    def validate_order(order_data: Dict) -> ValidationResult:
        """验证完整订单"""
        result = ValidationResult(is_valid=True)
        
        # 验证订单ID
        result.merge(OrderValidator.validate_order_id(order_data.get('order_id')))
        
        # 验证门店代码
        result.merge(OrderValidator.validate_store_code(order_data.get('store_code') or order_data.get('fulfillment_store_code')))
        
        # 验证数量
        quantity = order_data.get('total_quantity') or order_data.get('quantity', 1)
        result.merge(OrderValidator.validate_quantity(quantity))
        
        return result


# ==================== 预测结果验证 ====================

class ForecastValidator:
    """预测结果验证器"""
    
    @staticmethod
    def validate_forecast(forecast_data: Dict) -> ValidationResult:
        """验证预测结果"""
        result = ValidationResult(is_valid=True)
        
        # 验证预测值非负
        predicted = forecast_data.get('predicted_orders', 0)
        if predicted < 0:
            result.add_error(f"预测值不能为负: {predicted}")
        
        # 验证置信区间顺序
        p10 = forecast_data.get('p10', 0)
        p50 = forecast_data.get('p50', 0)
        p90 = forecast_data.get('p90', 0)
        
        if not (p10 <= p50 <= p90):
            result.add_error(f"置信区间顺序错误: P10={p10}, P50={p50}, P90={p90}")
        
        # 验证极端值
        if p90 > p50 * 5:
            result.add_warning(f"P90预测值过高: {p90}")
        
        return result
    
    @staticmethod
    def validate_forecast_list(forecasts: List[Dict]) -> ValidationResult:
        """验证预测列表"""
        result = ValidationResult(is_valid=True)
        
        if not forecasts:
            result.add_warning("预测列表为空")
            return result
        
        for i, f in enumerate(forecasts):
            f_result = ForecastValidator.validate_forecast(f)
            if not f_result.is_valid:
                for err in f_result.errors:
                    result.add_error(f"预测[{i}]: {err}")
            for warn in f_result.warnings:
                result.add_warning(f"预测[{i}]: {warn}")
        
        return result


# ==================== 路径解决方案验证 ====================

class RouteValidator:
    """路径解决方案验证器"""
    
    @staticmethod
    def validate_route_feasibility(route_data: Dict, constraints: Dict = None) -> ValidationResult:
        """验证路径可行性"""
        result = ValidationResult(is_valid=True)
        constraints = constraints or {}
        
        # 获取路径信息
        stops = route_data.get('stops', [])
        total_distance = route_data.get('total_distance_km', 0)
        total_duration = route_data.get('total_duration_min', 0)
        total_demand = route_data.get('total_demand', 0)
        
        # 验证停靠点数量
        if len(stops) < 2:
            result.add_warning("路径停靠点过少")
        
        # 验证距离
        max_distance = constraints.get('max_distance_km', 300)
        if total_distance > max_distance:
            result.add_error(f"总距离超限: {total_distance}km > {max_distance}km")
        
        # 验证时长
        max_duration = constraints.get('max_duration_min', 480)  # 8小时
        if total_duration > max_duration:
            result.add_error(f"总时长超限: {total_duration}min > {max_duration}min")
        
        # 验证容量
        vehicle_capacity = constraints.get('vehicle_capacity', 100)
        if total_demand > vehicle_capacity:
            result.add_error(f"超出车辆容量: {total_demand} > {vehicle_capacity}")
        
        return result
    
    @staticmethod
    def validate_time_windows(stops: List[Dict]) -> ValidationResult:
        """验证时间窗约束"""
        result = ValidationResult(is_valid=True)
        
        for i, stop in enumerate(stops):
            arrival = stop.get('arrival_time')
            window_start = stop.get('time_window_start')
            window_end = stop.get('time_window_end')
            
            if arrival and window_end:
                # 检查是否在时间窗内
                if isinstance(arrival, str):
                    try:
                        arrival = datetime.strptime(arrival, "%H:%M")
                    except:
                        continue
                
                if isinstance(window_end, str):
                    try:
                        window_end = datetime.strptime(window_end, "%H:%M")
                    except:
                        continue
                
                if hasattr(arrival, 'hour') and hasattr(window_end, 'hour'):
                    if arrival > window_end:
                        result.add_warning(f"停靠点{i}到达时间超出时间窗")
        
        return result


# ==================== 输入安全验证 ====================

class SecurityValidator:
    """安全验证器 - 输入净化和注入防护"""
    
    # 危险字符模式
    DANGEROUS_PATTERNS = [
        r'<script[^>]*>.*?</script>',  # XSS
        r'javascript:',
        r'on\w+\s*=',  # 事件处理器
        r'[\x00-\x1f\x7f]',  # 控制字符
        r'(\.\./)+',  # 路径遍历
        r';\s*(?:rm|del|drop|truncate|delete)\s',  # 危险命令
    ]
    
    @staticmethod
    def sanitize_string(value: str) -> str:
        """净化字符串输入"""
        if not isinstance(value, str):
            return str(value) if value is not None else ""
        
        # 移除危险字符
        sanitized = value
        for pattern in SecurityValidator.DANGEROUS_PATTERNS:
            sanitized = re.sub(pattern, '', sanitized, flags=re.IGNORECASE)
        
        # 限制长度
        max_length = 1000
        if len(sanitized) > max_length:
            sanitized = sanitized[:max_length]
        
        return sanitized.strip()
    
    @staticmethod
    def validate_api_key(api_key: str) -> ValidationResult:
        """验证API密钥格式"""
        result = ValidationResult(is_valid=True)
        
        if not api_key:
            result.add_error("API密钥为空")
            return result
        
        # 检查格式
        if len(api_key) < 16:
            result.add_error("API密钥长度不足")
        
        if not re.match(r'^[a-zA-Z0-9_-]+$', api_key):
            result.add_error("API密钥包含非法字符")
        
        return result
    
    @staticmethod
    def anonymize_customer_data(data: Dict) -> Dict:
        """匿名化客户数据"""
        anonymized = data.copy()
        
        sensitive_fields = ['customer_name', 'customer_phone', 'email', 'address', 'user_id']
        
        for field in sensitive_fields:
            if field in anonymized:
                value = anonymized[field]
                if value and isinstance(value, str):
                    if field == 'customer_phone':
                        # 保留后4位
                        anonymized[field] = '****' + value[-4:] if len(value) >= 4 else '****'
                    elif field == 'email':
                        # 保留域名
                        parts = value.split('@')
                        anonymized[field] = '***@' + parts[1] if len(parts) == 2 else '***'
                    else:
                        # 哈希处理
                        import hashlib
                        anonymized[field] = hashlib.md5(value.encode()).hexdigest()[:8]
        
        return anonymized


# ==================== 综合验证器 ====================

class DataValidator:
    """综合数据验证器"""
    
    def __init__(self):
        self.geo_validator = GeographicValidator()
        self.order_validator = OrderValidator()
        self.forecast_validator = ForecastValidator()
        self.route_validator = RouteValidator()
        self.security_validator = SecurityValidator()
    
    def validate_store(self, store_data: Dict) -> ValidationResult:
        """验证门店数据"""
        result = ValidationResult(is_valid=True)
        
        # 验证门店代码
        result.merge(self.order_validator.validate_store_code(store_data.get('store_code')))
        
        # 验证坐标
        lat = store_data.get('latitude')
        lng = store_data.get('longitude')
        if lat is not None and lng is not None:
            result.merge(self.geo_validator.validate_coordinates(lat, lng))
        
        # 验证区域
        district = store_data.get('district')
        if district:
            result.merge(self.geo_validator.validate_district(district))
        
        return result
    
    def validate_pipeline_input(self, stores: List, orders: List = None) -> ValidationResult:
        """验证Pipeline输入数据"""
        result = ValidationResult(is_valid=True)
        
        # 验证门店
        if not stores:
            result.add_error("门店列表为空")
        else:
            for i, store in enumerate(stores[:10]):  # 只检查前10个
                store_dict = store if isinstance(store, dict) else store.__dict__
                s_result = self.validate_store(store_dict)
                if not s_result.is_valid:
                    for err in s_result.errors:
                        result.add_error(f"门店[{i}]: {err}")
        
        # 验证订单
        if orders:
            for i, order in enumerate(orders[:10]):
                order_dict = order if isinstance(order, dict) else order.__dict__
                o_result = self.order_validator.validate_order(order_dict)
                if not o_result.is_valid:
                    for err in o_result.errors:
                        result.add_error(f"订单[{i}]: {err}")
        
        return result
    
    def validate_pipeline_output(self, forecasts: List, routes: List = None) -> ValidationResult:
        """验证Pipeline输出数据"""
        result = ValidationResult(is_valid=True)
        
        # 验证预测
        if forecasts:
            forecast_dicts = [f if isinstance(f, dict) else f.__dict__ for f in forecasts[:10]]
            result.merge(self.forecast_validator.validate_forecast_list(forecast_dicts))
        
        # 验证路径
        if routes:
            for i, route in enumerate(routes):
                route_dict = route if isinstance(route, dict) else route.__dict__
                r_result = self.route_validator.validate_route_feasibility(route_dict)
                if not r_result.is_valid:
                    for err in r_result.errors:
                        result.add_error(f"路径[{i}]: {err}")
        
        return result


# ==================== 工厂函数 ====================

def create_data_validator() -> DataValidator:
    """创建数据验证器实例"""
    return DataValidator()


def validate_hk_coordinates(lat: float, lng: float) -> bool:
    """快速验证香港坐标"""
    return (HK_BOUNDS['lat_min'] <= lat <= HK_BOUNDS['lat_max'] and
            HK_BOUNDS['lng_min'] <= lng <= HK_BOUNDS['lng_max'])


def sanitize_input(value: Any) -> Any:
    """快速净化输入"""
    if isinstance(value, str):
        return SecurityValidator.sanitize_string(value)
    return value
