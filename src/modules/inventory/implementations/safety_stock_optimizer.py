"""
安全库存优化器
"""
import numpy as np
from typing import Dict, Any, List
from ...interfaces import IInventoryOptimizer
from src.core.interfaces import DemandForecast

class SafetyStockOptimizer(IInventoryOptimizer):
    """安全库存优化器"""
    
    def __init__(self, default_service_level: float = 0.95):
        self.default_service_level = default_service_level
    
    def calculate_safety_stock(self, demand_forecasts: List[DemandForecast], 
                              service_level: float = 0.95, 
                              lead_time_days: int = 2) -> Dict[str, float]:
        """计算安全库存"""
        import scipy.stats as stats
        
        # 按SKU分组
        sku_demands = {}
        for forecast in demand_forecasts:
            key = forecast.sku_id
            if key not in sku_demands:
                sku_demands[key] = []
            sku_demands[key].append(forecast.forecast_demand)
        
        safety_stocks = {}
        z_score = stats.norm.ppf(service_level)
        
        for sku_id, demands in sku_demands.items():
            mean_demand = np.mean(demands)
            std_demand = np.std(demands)
            
            # 安全库存公式
            safety_stock = z_score * std_demand * np.sqrt(lead_time_days)
            safety_stocks[sku_id] = max(0, safety_stock)
        
        return safety_stocks
    
    def optimize_inventory_allocation(self, current_inventory: Dict[str, float], 
                                     demand_forecasts: List[DemandForecast], 
                                     warehouse_capacity: Dict[str, float], 
                                     costs: Dict[str, float]) -> Dict[str, Any]:
        """优化库存分配"""
        # 简化实现
        return {
            'status': 'optimized',
            'total_cost': sum(costs.values()),
            'inventory_allocation': current_inventory.copy()
        }
    
    def generate_replenishment_plan(self, safety_stocks: Dict[str, float], 
                                   current_inventory: Dict[str, float], 
                                   min_order_qty: Dict[str, float], 
                                   batch_sizes: Dict[str, float]) -> Dict[str, Any]:
        """生成补货计划"""
        plan = {}
        
        for sku_id, safety_stock in safety_stocks.items():
            current = current_inventory.get(sku_id, 0)
            min_qty = min_order_qty.get(sku_id, 10)
            batch = batch_sizes.get(sku_id, 25)
            
            if current < safety_stock:
                # 需要补货
                deficit = safety_stock - current
                order_qty = max(min_qty, np.ceil(deficit / batch) * batch)
                
                plan[sku_id] = {
                    'current': current,
                    'safety_stock': safety_stock,
                    'order_quantity': order_qty,
                    'status': 'needs_reorder'
                }
            else:
                plan[sku_id] = {
                    'current': current,
                    'safety_stock': safety_stock,
                    'order_quantity': 0,
                    'status': 'sufficient'
                }
        
        return {
            'replenishment_plan': plan,
            'total_skus': len(plan),
            'skus_needing_reorder': sum(1 for p in plan.values() if p['status'] == 'needs_reorder')
        }
