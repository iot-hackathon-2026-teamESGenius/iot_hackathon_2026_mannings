"""
统一数据服务层
整合DFI企业数据，为所有API提供真实数据访问

使用方式:
    from src.api.services.data_service import DataService
    
    service = DataService()
    stores = service.get_stores()
    kpi = service.get_dashboard_kpi()
"""

import logging
from datetime import date, datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from functools import lru_cache
import pandas as pd

logger = logging.getLogger(__name__)


class DataService:
    """
    统一数据服务 - 封装DFI数据加载器
    提供缓存和便捷的数据访问接口
    """
    
    _instance = None
    _initialized = False
    
    def __new__(cls):
        """单例模式"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if DataService._initialized:
            return
        
        self._data_loader = None
        self._cache = {}
        self._cache_expiry = {}
        self._cache_ttl = 300  # 5分钟缓存
        
        DataService._initialized = True
        logger.info("DataService initialized")
    
    @property
    def data_loader(self):
        """懒加载数据加载器"""
        if self._data_loader is None:
            try:
                from src.modules.data.implementations.dfi_data_loader import DFIDataLoader
                self._data_loader = DFIDataLoader()
                logger.info("DFIDataLoader initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize DFIDataLoader: {e}")
                raise
        return self._data_loader
    
    def _get_cached(self, key: str) -> Optional[Any]:
        """获取缓存数据"""
        if key in self._cache:
            if datetime.now().timestamp() < self._cache_expiry.get(key, 0):
                return self._cache[key]
        return None
    
    def _set_cached(self, key: str, value: Any, ttl: int = None):
        """设置缓存"""
        self._cache[key] = value
        self._cache_expiry[key] = datetime.now().timestamp() + (ttl or self._cache_ttl)
    
    def clear_cache(self):
        """清除所有缓存"""
        self._cache.clear()
        self._cache_expiry.clear()
        logger.info("DataService cache cleared")
    
    # ==================== 门店数据 ====================
    
    def get_stores(self, use_cache: bool = True) -> List[Dict]:
        """
        获取所有门店列表
        返回格式适配前端需要
        """
        cache_key = "stores_list"
        if use_cache:
            cached = self._get_cached(cache_key)
            if cached:
                return cached
        
        try:
            stores = self.data_loader.load_stores()
            store_list = []
            
            for store in stores:
                store_data = {
                    "store_id": str(store.store_code),
                    "store_code": store.store_code,
                    "store_name": f"Mannings {store.district}" if store.district else f"Store {store.store_code}",
                    "district": store.district or "Unknown",
                    "address": store.address or "",
                    "latitude": store.latitude,
                    "longitude": store.longitude,
                    "has_coordinates": store.latitude is not None and store.longitude is not None
                }
                store_list.append(store_data)
            
            self._set_cached(cache_key, store_list)
            logger.info(f"Loaded {len(store_list)} stores from DFI data")
            return store_list
            
        except Exception as e:
            logger.error(f"Failed to load stores: {e}")
            raise
    
    def get_store_by_code(self, store_code: int) -> Optional[Dict]:
        """根据门店代码获取门店信息"""
        stores = self.get_stores()
        for store in stores:
            if store["store_code"] == store_code:
                return store
        return None
    
    def get_stores_by_district(self, district: str) -> List[Dict]:
        """根据区域获取门店列表"""
        stores = self.get_stores()
        return [s for s in stores if s["district"] == district]
    
    def get_active_stores(self) -> List[Dict]:
        """获取有订单数据的活跃门店"""
        cache_key = "active_stores"
        cached = self._get_cached(cache_key)
        if cached:
            return cached
        
        try:
            active_codes = self.data_loader.get_active_store_codes()
            stores = self.get_stores()
            active_stores = [s for s in stores if s["store_code"] in active_codes]
            
            self._set_cached(cache_key, active_stores)
            logger.info(f"Found {len(active_stores)} active stores")
            return active_stores
            
        except Exception as e:
            logger.error(f"Failed to get active stores: {e}")
            return self.get_stores()  # Fallback to all stores
    
    def get_stores_with_coordinates(self) -> List[Dict]:
        """获取有坐标的门店（用于路径规划）"""
        stores = self.get_stores()
        return [s for s in stores if s["has_coordinates"]]
    
    # ==================== 订单数据 ====================
    
    def get_orders(self, start_date: date = None, end_date: date = None,
                   store_codes: List[int] = None) -> List[Dict]:
        """获取订单列表"""
        try:
            orders = self.data_loader.load_orders(start_date, end_date, store_codes)
            return [
                {
                    "order_id": o.order_id,
                    "date": o.dt.isoformat(),
                    "store_code": o.fulfillment_store_code,
                    "user_id": o.user_id,
                    "sku_count": o.unique_sku_cnt,
                    "total_quantity": o.total_quantity_cnt
                }
                for o in orders
            ]
        except Exception as e:
            logger.error(f"Failed to load orders: {e}")
            return []
    
    def get_order_stats(self) -> Dict[str, Any]:
        """获取订单统计信息"""
        cache_key = "order_stats"
        cached = self._get_cached(cache_key)
        if cached:
            return cached
        
        try:
            stats_df = self.data_loader.get_store_order_stats()
            
            result = {
                "total_orders": int(stats_df["total_orders"].sum()),
                "total_stores": len(stats_df),
                "avg_orders_per_store": float(stats_df["total_orders"].mean()),
                "total_quantity": float(stats_df["total_quantity"].sum()),
                "avg_quantity_per_order": float(stats_df["avg_quantity_per_order"].mean()),
                "date_range": {
                    "start": str(stats_df["first_order_date"].min()),
                    "end": str(stats_df["last_order_date"].max())
                },
                "store_stats": stats_df.to_dict(orient="records")
            }
            
            self._set_cached(cache_key, result)
            return result
            
        except Exception as e:
            logger.error(f"Failed to get order stats: {e}")
            return {}
    
    def get_daily_orders(self, store_code: int = None) -> List[Dict]:
        """获取每日订单汇总"""
        try:
            df = self.data_loader.get_daily_order_summary(store_code)
            return df.to_dict(orient="records")
        except Exception as e:
            logger.error(f"Failed to get daily orders: {e}")
            return []
    
    # ==================== 履约/SLA数据 ====================
    
    def get_fulfillment_data(self, order_ids: List[str] = None) -> List[Dict]:
        """获取履约数据"""
        try:
            fulfillments = self.data_loader.load_fulfillment(order_ids)
            return [
                {
                    "order_id": f.order_id,
                    "status": f.get_status().value,
                    "order_create_time": f.order_create_time.isoformat() if f.order_create_time else None,
                    "ready_for_pickup_time": f.ready_for_pickup_time.isoformat() if f.ready_for_pickup_time else None,
                    "completed_time": f.completed_time.isoformat() if f.completed_time else None,
                    "is_completed": f.completed_time is not None,
                    "is_cancelled": f.cancel_time is not None,
                    "sla_metrics": f.calculate_sla_metrics()
                }
                for f in fulfillments
            ]
        except Exception as e:
            logger.error(f"Failed to load fulfillment data: {e}")
            return []
    
    def get_sla_analysis(self) -> Dict[str, Any]:
        """获取SLA分析结果"""
        cache_key = "sla_analysis"
        cached = self._get_cached(cache_key)
        if cached:
            return cached
        
        try:
            analysis = self.data_loader.get_sla_analysis()
            self._set_cached(cache_key, analysis)
            return analysis
        except Exception as e:
            logger.error(f"Failed to get SLA analysis: {e}")
            return {}
    
    # ==================== Dashboard KPI ====================
    
    def get_dashboard_kpi(self) -> Dict[str, Any]:
        """
        获取Dashboard KPI数据
        基于真实数据计算
        """
        cache_key = "dashboard_kpi"
        cached = self._get_cached(cache_key)
        if cached:
            return cached
        
        try:
            # 获取SLA分析
            sla = self.get_sla_analysis()
            order_stats = self.get_order_stats()
            
            total_orders = sla.get("total_orders", 0)
            completed_orders = sla.get("completed_orders", 0)
            cancelled_orders = sla.get("cancelled_orders", 0)
            
            # 计算SLA达成率 (基于完成订单)
            sla_rate = (completed_orders / total_orders * 100) if total_orders > 0 else 0
            
            # 计算平均履约时间
            stage_durations = sla.get("stage_durations", {})
            total_fulfillment = stage_durations.get("total_fulfillment", {})
            avg_fulfillment_hours = total_fulfillment.get("mean_min", 0) / 60
            
            # 取消率
            cancel_rate = (cancelled_orders / total_orders * 100) if total_orders > 0 else 0
            
            kpi = {
                "sla_achievement_rate": {
                    "value": round(sla_rate, 1),
                    "unit": "%",
                    "description": "订单完成率"
                },
                "total_orders": {
                    "value": total_orders,
                    "unit": "单",
                    "description": "总订单数"
                },
                "completed_orders": {
                    "value": completed_orders,
                    "unit": "单",
                    "description": "完成订单"
                },
                "cancelled_orders": {
                    "value": cancelled_orders,
                    "unit": "单",
                    "description": "取消订单"
                },
                "cancel_rate": {
                    "value": round(cancel_rate, 2),
                    "unit": "%",
                    "description": "取消率"
                },
                "avg_fulfillment_time": {
                    "value": round(avg_fulfillment_hours, 1),
                    "unit": "小时",
                    "description": "平均履约时间"
                },
                "active_stores": {
                    "value": len(self.get_active_stores()),
                    "unit": "家",
                    "description": "活跃门店数"
                },
                "stage_durations": stage_durations
            }
            
            self._set_cached(cache_key, kpi)
            return kpi
            
        except Exception as e:
            logger.error(f"Failed to calculate KPI: {e}")
            return {}
    
    # ==================== 日期特征 ====================
    
    def get_date_features(self, start_date: date = None, end_date: date = None) -> List[Dict]:
        """获取日期特征"""
        try:
            features = self.data_loader.load_date_features(start_date, end_date)
            return [
                {
                    "date": f.calendar_date.isoformat(),
                    "weekday": f.calendar_weekday,
                    "is_weekend": f.is_weekend,
                    "is_public_holiday": f.is_public_holiday,
                    "active_promos": [p.value for p in f.get_active_promos()]
                }
                for f in features
            ]
        except Exception as e:
            logger.error(f"Failed to load date features: {e}")
            return []
    
    # ==================== 路径规划数据准备 ====================
    
    def prepare_routing_input(self, target_date: date = None) -> Dict[str, Any]:
        """准备路径优化输入数据"""
        try:
            if target_date is None:
                target_date = date.today()
            return self.data_loader.prepare_routing_input(target_date)
        except Exception as e:
            logger.error(f"Failed to prepare routing input: {e}")
            return {}
    
    # ==================== 数据质量报告 ====================
    
    def get_data_quality_report(self) -> Dict[str, Any]:
        """获取数据质量报告"""
        try:
            return self.data_loader.generate_data_quality_report()
        except Exception as e:
            logger.error(f"Failed to generate data quality report: {e}")
            return {"error": str(e)}


# 全局单例实例
_data_service: Optional[DataService] = None


def get_data_service() -> DataService:
    """获取DataService单例"""
    global _data_service
    if _data_service is None:
        _data_service = DataService()
    return _data_service
