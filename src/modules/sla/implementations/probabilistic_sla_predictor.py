"""
概率SLA预测器
"""
from datetime import datetime, timedelta
from typing import Dict, Any
import numpy as np
from ...interfaces import ISLAPredictor
from src.core.interfaces import RoutePlan

class ProbabilisticSLAPredictor(ISLAPredictor):
    """概率SLA预测器"""
    
    def __init__(self, confidence_level: float = 0.95, include_weather_impact: bool = True):
        self.confidence_level = confidence_level
        self.include_weather_impact = include_weather_impact
    
    def predict_pickup_time(self, order_info: Dict[str, Any], 
                           route_plan: RoutePlan,
                           store_processing_time_model: Any = None) -> Dict[str, Any]:
        """预测取货时间"""
        # 从路线中提取相关门店的到达时间
        store_id = order_info.get('store_id')
        
        if store_id in route_plan.store_sequence:
            idx = route_plan.store_sequence.index(store_id)
            arrival_time = route_plan.arrival_times[idx]
            
            # 估算处理时间（如果有模型则使用模型）
            if store_processing_time_model:
                processing_minutes = store_processing_time_model.predict(store_id)
            else:
                # 默认处理时间：10-30分钟
                processing_minutes = 20 + np.random.normal(0, 5)
            
            # 计算预计完成时间
            arrival_dt = datetime.strptime(arrival_time, "%H:%M")
            ready_dt = arrival_dt + timedelta(minutes=max(5, processing_minutes))
            
            # 考虑不确定性
            uncertainty = 0.1  # 10%不确定性
            ready_time_uncertain = ready_dt + timedelta(
                minutes=np.random.normal(0, processing_minutes * uncertainty)
            )
            
            return {
                'store_id': store_id,
                'route_id': route_plan.route_id,
                'estimated_arrival': arrival_time,
                'estimated_ready': ready_dt.strftime("%H:%M"),
                'estimated_ready_with_uncertainty': ready_time_uncertain.strftime("%H:%M"),
                'processing_minutes': processing_minutes,
                'confidence': self.confidence_level
            }
        
        return {
            'store_id': store_id,
            'error': 'Store not in route plan',
            'estimated_ready': None
        }
    
    def calculate_sla_probability(self, promised_time: datetime, 
                                 predicted_time: datetime, 
                                 uncertainty: float = 0.1) -> float:
        """计算SLA达成概率"""
        from scipy.stats import norm
        
        # 计算时间差（分钟）
        time_diff = (predicted_time - promised_time).total_seconds() / 60
        
        # 如果预测时间早于承诺时间，概率高
        if time_diff <= 0:
            base_prob = 0.95
        else:
            # 使用正态分布计算概率
            # 假设标准差为预测时间的uncertainty比例
            std_dev = abs(time_diff) * uncertainty
            z_score = -time_diff / std_dev if std_dev > 0 else 0
            base_prob = norm.cdf(z_score)
        
        # 应用置信水平
        adjusted_prob = base_prob * self.confidence_level
        
        return min(max(adjusted_prob, 0), 1)  # 确保在0-1范围内
