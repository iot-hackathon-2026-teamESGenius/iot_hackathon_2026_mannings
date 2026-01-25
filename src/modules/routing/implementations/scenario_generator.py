"""
多情景需求生成器 - 路径优化创新点
实现 Learning Enhanced Robust Routing 中的 Scenario Generation

用途：基于预测需求生成多个需求情景，支持鲁棒优化
"""
from typing import List, Dict, Any, Tuple
from dataclasses import dataclass
import numpy as np
from src.core.interfaces import DemandForecast

@dataclass
class DemandScenario:
    """需求情景"""
    scenario_id: str
    scenario_name: str
    demand_ratio: float  # 相对于基准预测的比例
    demands: Dict[str, float]  # store_id -> demand
    probability: float = None  # 情景发生概率（可选）

class ScenarioGenerator:
    """
    多情景需求生成器
    
    创新点：将预测不确定性转化为可优化的离散情景
    """
    
    def __init__(self, base_ratios: List[float] = None):
        """
        Args:
            base_ratios: 默认情景比例，如 [0.9, 1.0, 1.1] 表示 90%/100%/110% 需求
        """
        self.base_ratios = base_ratios or [0.9, 1.0, 1.1]
    
    def generate_from_forecasts(
        self, 
        forecasts: List[DemandForecast],
        ratios: List[float] = None,
        use_confidence_bounds: bool = False
    ) -> List[DemandScenario]:
        """
        从预测结果生成多情景需求
        
        Args:
            forecasts: 预测结果列表
            ratios: 自定义情景比例
            use_confidence_bounds: 是否使用预测置信区间生成情景
            
        Returns:
            DemandScenario 列表
        """
        ratios = ratios or self.base_ratios
        scenarios = []
        
        # 聚合门店需求
        base_demands = {}
        for f in forecasts:
            if f.store_id not in base_demands:
                base_demands[f.store_id] = 0
            base_demands[f.store_id] += f.forecast_demand
        
        if use_confidence_bounds and forecasts:
            # 使用预测的置信区间
            scenarios = self._generate_from_bounds(forecasts, base_demands)
        else:
            # 使用固定比例
            for i, ratio in enumerate(ratios):
                scenario_demands = {
                    store_id: demand * ratio 
                    for store_id, demand in base_demands.items()
                }
                
                scenarios.append(DemandScenario(
                    scenario_id=f"S{i+1:02d}",
                    scenario_name=f"{int(ratio*100)}% Demand",
                    demand_ratio=ratio,
                    demands=scenario_demands,
                    probability=1.0 / len(ratios)  # 均匀概率
                ))
        
        return scenarios
    
    def _generate_from_bounds(
        self, 
        forecasts: List[DemandForecast],
        base_demands: Dict[str, float]
    ) -> List[DemandScenario]:
        """使用预测置信区间生成情景"""
        scenarios = []
        
        # 计算平均置信度
        avg_confidence = np.mean([f.confidence for f in forecasts])
        
        # 低需求情景（下界）
        low_demands = {}
        for f in forecasts:
            if f.store_id not in low_demands:
                low_demands[f.store_id] = 0
            low_demands[f.store_id] += f.lower_bound
        
        low_ratio = sum(low_demands.values()) / sum(base_demands.values()) if base_demands else 0.9
        scenarios.append(DemandScenario(
            scenario_id="S_LOW",
            scenario_name="Low Demand (Lower Bound)",
            demand_ratio=low_ratio,
            demands=low_demands,
            probability=0.1
        ))
        
        # 基准情景
        scenarios.append(DemandScenario(
            scenario_id="S_BASE",
            scenario_name="Base Demand (Forecast)",
            demand_ratio=1.0,
            demands=base_demands.copy(),
            probability=0.8
        ))
        
        # 高需求情景（上界）
        high_demands = {}
        for f in forecasts:
            if f.store_id not in high_demands:
                high_demands[f.store_id] = 0
            high_demands[f.store_id] += f.upper_bound
        
        high_ratio = sum(high_demands.values()) / sum(base_demands.values()) if base_demands else 1.1
        scenarios.append(DemandScenario(
            scenario_id="S_HIGH",
            scenario_name="High Demand (Upper Bound)",
            demand_ratio=high_ratio,
            demands=high_demands,
            probability=0.1
        ))
        
        return scenarios
    
    def generate_monte_carlo(
        self, 
        base_demands: Dict[str, float],
        n_scenarios: int = 100,
        cv: float = 0.15  # 变异系数
    ) -> List[DemandScenario]:
        """
        蒙特卡洛采样生成情景
        
        Args:
            base_demands: 基准需求
            n_scenarios: 情景数量
            cv: 变异系数（标准差/均值）
        """
        scenarios = []
        
        for i in range(n_scenarios):
            scenario_demands = {}
            for store_id, demand in base_demands.items():
                # 对数正态分布采样（确保非负）
                std = demand * cv
                sampled = max(0, np.random.normal(demand, std))
                scenario_demands[store_id] = sampled
            
            ratio = sum(scenario_demands.values()) / sum(base_demands.values()) if base_demands else 1.0
            
            scenarios.append(DemandScenario(
                scenario_id=f"MC{i+1:04d}",
                scenario_name=f"Monte Carlo #{i+1}",
                demand_ratio=ratio,
                demands=scenario_demands,
                probability=1.0 / n_scenarios
            ))
        
        return scenarios
    
    def filter_representative_scenarios(
        self, 
        scenarios: List[DemandScenario],
        n_representative: int = 5,
        method: str = "percentile"
    ) -> List[DemandScenario]:
        """
        从大量情景中筛选代表性情景
        
        Args:
            scenarios: 原始情景列表
            n_representative: 代表性情景数量
            method: 筛选方法 ("percentile" / "kmeans")
        """
        if len(scenarios) <= n_representative:
            return scenarios
        
        if method == "percentile":
            # 按总需求排序，选取百分位数对应的情景
            sorted_scenarios = sorted(scenarios, key=lambda s: sum(s.demands.values()))
            indices = np.linspace(0, len(sorted_scenarios) - 1, n_representative, dtype=int)
            return [sorted_scenarios[i] for i in indices]
        
        return scenarios[:n_representative]
