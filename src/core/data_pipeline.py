#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
万宁SLA优化系统 - 自动化数据管道
整合所有数据源，提供统一的数据处理和更新机制

创建时间: 2026-03-17
作者: 谭聪 + 李泰一 (Team ESGenius)
"""

import pandas as pd
import numpy as np
import json
import logging
import requests
from datetime import datetime, date, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
import schedule
import time
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

try:
    from .data_schema import (
        StoreLocation, OrderDetail, WeatherData, PublicHoliday, TrafficCondition,
        GeocodeStatus, WeatherCondition, dataframe_to_store_locations, dataframe_to_order_details
    )
    from .interfaces import DataFetcher, DataProcessor, Logger
except ImportError:
    # For direct execution
    from data_schema import (
        StoreLocation, OrderDetail, WeatherData, PublicHoliday, TrafficCondition,
        GeocodeStatus, WeatherCondition, dataframe_to_store_locations, dataframe_to_order_details
    )
    from interfaces import DataFetcher, DataProcessor, Logger

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('data_pipeline.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class DataPipeline:
    """统一数据管道类"""
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or self._get_default_config()
        self.base_path = Path(".")
        self.raw_data_path = self.base_path / "data" / "dfi" / "raw"
        self.processed_data_path = self.base_path / "data" / "dfi" / "processed"
        self.external_data_path = self.base_path / "data" / "official"
        
        # 数据缓存
        self._store_locations_cache = None
        self._orders_cache = None
        self._weather_cache = None
        self._holidays_cache = None
        self._traffic_cache = None
        
        # 缓存时间戳
        self._cache_timestamps = {}
        
        # 数据质量统计
        self.quality_stats = {
            'last_update': None,
            'total_stores': 0,
            'total_orders': 0,
            'data_completeness': {},
            'error_count': 0
        }
        
        logger.info("数据管道初始化完成")
    
    def _get_default_config(self) -> Dict[str, Any]:
        """获取默认配置"""
        return {
            'cache_ttl_minutes': 60,  # 缓存有效期
            'weather_update_interval': 360,  # 天气数据更新间隔(分钟)
            'traffic_update_interval': 15,   # 交通数据更新间隔(分钟)
            'batch_size': 1000,  # 批处理大小
            'max_workers': 4,    # 最大并发数
            'retry_attempts': 3,  # 重试次数
            'timeout_seconds': 30  # 超时时间
        }
    
    # ==================== 数据加载方法 ====================
    
    def load_store_locations(self, force_refresh: bool = False) -> List[StoreLocation]:
        """加载门店位置数据"""
        cache_key = 'store_locations'
        
        if not force_refresh and self._is_cache_valid(cache_key):
            logger.info("使用缓存的门店位置数据")
            return self._store_locations_cache
        
        try:
            logger.info("加载门店位置数据...")
            
            # 加载增强的门店坐标数据
            enhanced_coords_file = self.processed_data_path / "store_coordinates_enhanced_v2.csv"
            if enhanced_coords_file.exists():
                df = pd.read_csv(enhanced_coords_file)
                locations = dataframe_to_store_locations(df)
                
                self._store_locations_cache = locations
                self._cache_timestamps[cache_key] = datetime.now()
                self.quality_stats['total_stores'] = len(locations)
                
                logger.info(f"✅ 成功加载 {len(locations)} 个门店位置")
                return locations
            else:
                logger.error(f"门店坐标文件不存在: {enhanced_coords_file}")
                return []
                
        except Exception as e:
            logger.error(f"加载门店位置数据失败: {str(e)}")
            self.quality_stats['error_count'] += 1
            return []
    
    def load_order_data(self, start_date: Optional[date] = None, 
                       end_date: Optional[date] = None, 
                       force_refresh: bool = False) -> List[OrderDetail]:
        """加载订单数据"""
        cache_key = f'orders_{start_date}_{end_date}'
        
        if not force_refresh and self._is_cache_valid(cache_key):
            logger.info("使用缓存的订单数据")
            return self._orders_cache
        
        try:
            logger.info("加载订单数据...")
            
            # 加载订单详情
            order_file = self.raw_data_path / "case_study_order_detail-000000000000.csv"
            if order_file.exists():
                df = pd.read_csv(order_file)
                
                # 日期过滤
                if start_date or end_date:
                    df['dt'] = pd.to_datetime(df['dt'])
                    if start_date:
                        df = df[df['dt'] >= pd.to_datetime(start_date)]
                    if end_date:
                        df = df[df['dt'] <= pd.to_datetime(end_date)]
                
                orders = dataframe_to_order_details(df)
                
                self._orders_cache = orders
                self._cache_timestamps[cache_key] = datetime.now()
                self.quality_stats['total_orders'] = len(orders)
                
                logger.info(f"✅ 成功加载 {len(orders)} 个订单")
                return orders
            else:
                logger.error(f"订单文件不存在: {order_file}")
                return []
                
        except Exception as e:
            logger.error(f"加载订单数据失败: {str(e)}")
            self.quality_stats['error_count'] += 1
            return []
    
    def load_weather_data(self, force_refresh: bool = False) -> List[WeatherData]:
        """加载天气数据 - 集成HKO API"""
        cache_key = 'weather_data'
        
        if not force_refresh and self._is_cache_valid(cache_key):
            logger.info("使用缓存的天气数据")
            return self._weather_cache
        
        try:
            logger.info("从HKO API加载天气数据...")
            
            # 使用HKO API获取真实天气数据
            weather_data = self._fetch_hko_weather_data()
            
            # 如果API失败，使用缓存或模拟数据
            if not weather_data:
                logger.warning("HKO API失败，使用备用数据")
                if self._weather_cache:
                    logger.info("使用缓存的天气数据作为备用")
                    return self._weather_cache
                else:
                    logger.info("生成模拟天气数据作为备用")
                    weather_data = self._generate_sample_weather_data()
            
            self._weather_cache = weather_data
            self._cache_timestamps[cache_key] = datetime.now()
            
            logger.info(f"✅ 成功加载 {len(weather_data)} 条天气数据")
            return weather_data
            
        except Exception as e:
            logger.error(f"加载天气数据失败: {str(e)}")
            self.quality_stats['error_count'] += 1
            
            # 返回缓存数据或空列表
            return self._weather_cache if self._weather_cache else []
    
    def load_holiday_data(self, year: int = None, force_refresh: bool = False) -> List[PublicHoliday]:
        """加载公共假期数据 - 支持在线更新"""
        if year is None:
            year = datetime.now().year
            
        cache_key = f'holidays_{year}'
        
        if not force_refresh and self._is_cache_valid(cache_key):
            logger.info("使用缓存的假期数据")
            return self._holidays_cache
        
        try:
            logger.info(f"加载 {year} 年公共假期数据...")
            
            # 使用增强的假期数据加载
            holidays = self._enhance_holiday_data_loading(year)
            
            self._holidays_cache = holidays
            self._cache_timestamps[cache_key] = datetime.now()
            
            logger.info(f"✅ 成功加载 {len(holidays)} 个公共假期")
            return holidays
                
        except Exception as e:
            logger.error(f"加载假期数据失败: {str(e)}")
            self.quality_stats['error_count'] += 1
            
            # 返回缓存数据或空列表
            return self._holidays_cache if self._holidays_cache else []
    
    def load_traffic_data(self, force_refresh: bool = False) -> List[TrafficCondition]:
        """加载交通数据 - 集成实时交通API"""
        cache_key = 'traffic_data'
        
        if not force_refresh and self._is_cache_valid(cache_key):
            logger.info("使用缓存的交通数据")
            return self._traffic_cache
        
        try:
            logger.info("从交通API加载实时交通数据...")
            
            # 使用实时交通API获取数据
            traffic_data = self._fetch_real_traffic_data()
            
            # 如果API失败，使用缓存或模拟数据
            if not traffic_data:
                logger.warning("交通API失败，使用备用数据")
                if self._traffic_cache:
                    logger.info("使用缓存的交通数据作为备用")
                    return self._traffic_cache
                else:
                    logger.info("生成模拟交通数据作为备用")
                    traffic_data = self._generate_sample_traffic_data()
            
            self._traffic_cache = traffic_data
            self._cache_timestamps[cache_key] = datetime.now()
            
            logger.info(f"✅ 成功加载 {len(traffic_data)} 条交通数据")
            return traffic_data
            
        except Exception as e:
            logger.error(f"加载交通数据失败: {str(e)}")
            self.quality_stats['error_count'] += 1
            
            # 返回缓存数据或空列表
            return self._traffic_cache if self._traffic_cache else []
    
    # ==================== 数据集成方法 ====================
    
    def create_integrated_dataset(self, target_date: date = None) -> pd.DataFrame:
        """创建集成数据集"""
        if target_date is None:
            target_date = date.today()
        
        logger.info(f"创建 {target_date} 的集成数据集...")
        
        try:
            # 加载所有数据
            stores = self.load_store_locations()
            orders = self.load_order_data()
            weather = self.load_weather_data()
            holidays = self.load_holiday_data()
            traffic = self.load_traffic_data()
            
            # 转换为DataFrame
            stores_df = pd.DataFrame([{
                'store_code': s.store_code,
                'latitude': s.latitude,
                'longitude': s.longitude,
                'district': s.district,
                'address': s.address,
                'geocode_status': s.geocode_status.value
            } for s in stores])
            
            orders_df = pd.DataFrame([{
                'order_id': o.order_id,
                'user_id': o.user_id,
                'fulfillment_store_code': o.fulfillment_store_code,
                'order_date': o.order_date,
                'total_quantity': o.total_quantity,
                'unique_sku_count': o.unique_sku_count
            } for o in orders])
            
            # 集成订单和门店数据
            integrated_df = orders_df.merge(
                stores_df,
                left_on='fulfillment_store_code',
                right_on='store_code',
                how='left'
            )
            
            # 添加时间特征
            integrated_df['order_date'] = pd.to_datetime(integrated_df['order_date'])
            integrated_df['weekday'] = integrated_df['order_date'].dt.dayofweek
            integrated_df['is_weekend'] = integrated_df['weekday'].isin([5, 6])
            
            # 添加假期标记
            holiday_dates = {h.date for h in holidays}
            integrated_df['is_holiday'] = integrated_df['order_date'].dt.date.isin(holiday_dates)
            
            # 添加天气特征（简化处理）
            if weather:
                weather_dict = {w.date: {
                    'temperature_high': w.temperature_high,
                    'temperature_low': w.temperature_low,
                    'humidity': w.humidity,
                    'condition': w.condition.value,
                    'rainfall': w.rainfall
                } for w in weather}
                
                for col in ['temperature_high', 'temperature_low', 'humidity', 'rainfall']:
                    integrated_df[f'weather_{col}'] = integrated_df['order_date'].dt.date.map(
                        lambda x: weather_dict.get(x, {}).get(col, np.nan)
                    )
                
                integrated_df['weather_condition'] = integrated_df['order_date'].dt.date.map(
                    lambda x: weather_dict.get(x, {}).get('condition', 'unknown')
                )
            
            logger.info(f"✅ 成功创建集成数据集，包含 {len(integrated_df)} 条记录")
            return integrated_df
            
        except Exception as e:
            logger.error(f"创建集成数据集失败: {str(e)}")
            self.quality_stats['error_count'] += 1
            return pd.DataFrame()
    
    # ==================== 增强的数据质量检查 ====================
    
    def check_data_quality(self) -> Dict[str, Any]:
        """增强的数据质量检查"""
        logger.info("执行增强的数据质量检查...")
        
        quality_report = {
            'timestamp': datetime.now(),
            'stores': {},
            'orders': {},
            'external_data': {},
            'data_integrity': {},
            'overall_score': 0.0,
            'recommendations': []
        }
        
        try:
            # 检查门店数据
            stores = self.load_store_locations()
            if stores:
                store_validation = self._validate_store_data_quality(stores)
                quality_report['stores'] = store_validation
            
            # 检查订单数据
            orders = self.load_order_data()
            if orders:
                order_validation = self._validate_order_data_quality(orders)
                quality_report['orders'] = order_validation
            
            # 检查外部数据
            external_validation = self._validate_external_data_quality()
            quality_report['external_data'] = external_validation
            
            # 检查数据完整性
            integrity_validation = self._validate_data_integrity()
            quality_report['data_integrity'] = integrity_validation
            
            # 计算总体质量分数
            quality_report['overall_score'] = self._calculate_overall_quality_score(quality_report)
            
            # 生成改进建议
            quality_report['recommendations'] = self._generate_quality_recommendations(quality_report)
            
            logger.info(f"✅ 数据质量检查完成，总体分数: {quality_report['overall_score']:.1f}")
            return quality_report
            
        except Exception as e:
            logger.error(f"数据质量检查失败: {str(e)}")
            quality_report['error'] = str(e)
            return quality_report
    
    def _validate_store_data_quality(self, stores: List[StoreLocation]) -> Dict[str, Any]:
        """验证门店数据质量"""
        validation = {
            'total_count': len(stores),
            'valid_coordinates': 0,
            'coordinate_accuracy': 0.0,
            'geocode_success_rate': 0.0,
            'district_coverage': {},
            'issues': []
        }
        
        valid_coords = 0
        geocode_success = 0
        district_counts = {}
        
        for store in stores:
            # 验证坐标
            if self._validate_coordinates(store.latitude, store.longitude):
                valid_coords += 1
            else:
                validation['issues'].append(f"门店 {store.store_code} 坐标超出香港范围")
            
            # 验证地理编码状态
            if store.geocode_status != GeocodeStatus.FAILED:
                geocode_success += 1
            
            # 统计区域分布
            district_counts[store.district] = district_counts.get(store.district, 0) + 1
        
        validation['valid_coordinates'] = valid_coords
        validation['coordinate_accuracy'] = (valid_coords / len(stores)) * 100 if stores else 0
        validation['geocode_success_rate'] = (geocode_success / len(stores)) * 100 if stores else 0
        validation['district_coverage'] = district_counts
        
        return validation
    
    def _validate_order_data_quality(self, orders: List[OrderDetail]) -> Dict[str, Any]:
        """验证订单数据质量"""
        validation = {
            'total_count': len(orders),
            'valid_orders': 0,
            'data_completeness': 0.0,
            'date_range': {},
            'store_coverage': {},
            'anomalies': [],
            'issues': []
        }
        
        if not orders:
            return validation
        
        valid_orders = 0
        store_counts = {}
        quantities = []
        sku_counts = []
        
        for order in orders:
            # 验证订单完整性
            is_valid = True
            
            if not order.order_id or not order.user_id:
                validation['issues'].append(f"订单 {order.order_id} 缺少必要标识符")
                is_valid = False
            
            if order.total_quantity <= 0 or order.unique_sku_count <= 0:
                validation['issues'].append(f"订单 {order.order_id} 数量异常")
                is_valid = False
            
            if len(order.items) != order.unique_sku_count:
                validation['issues'].append(f"订单 {order.order_id} SKU数量不匹配")
                is_valid = False
            
            if is_valid:
                valid_orders += 1
                quantities.append(order.total_quantity)
                sku_counts.append(order.unique_sku_count)
            
            # 统计门店分布
            store_counts[order.fulfillment_store_code] = store_counts.get(order.fulfillment_store_code, 0) + 1
        
        validation['valid_orders'] = valid_orders
        validation['data_completeness'] = (valid_orders / len(orders)) * 100
        validation['date_range'] = {
            'start': min(o.order_date for o in orders).isoformat(),
            'end': max(o.order_date for o in orders).isoformat()
        }
        validation['store_coverage'] = len(store_counts)
        
        # 检测异常值
        if quantities:
            q_mean = np.mean(quantities)
            q_std = np.std(quantities)
            outliers = [q for q in quantities if abs(q - q_mean) > 3 * q_std]
            if outliers:
                validation['anomalies'].append(f"发现 {len(outliers)} 个数量异常订单")
        
        return validation
    
    def _validate_external_data_quality(self) -> Dict[str, Any]:
        """验证外部数据质量"""
        validation = {
            'weather_status': 'unknown',
            'holidays_status': 'unknown',
            'traffic_status': 'unknown',
            'weather_freshness': None,
            'traffic_freshness': None,
            'api_health': {}
        }
        
        # 检查天气数据
        try:
            weather = self.load_weather_data()
            if weather:
                validation['weather_status'] = 'available'
                # 检查数据新鲜度
                latest_date = max(w.date for w in weather)
                days_ahead = (latest_date - date.today()).days
                validation['weather_freshness'] = f"{days_ahead} days ahead"
                
                # 验证数据合理性
                for w in weather:
                    if w.temperature_high < w.temperature_low:
                        validation['api_health']['weather_temp_inconsistent'] = True
                    if w.humidity < 0 or w.humidity > 100:
                        validation['api_health']['weather_humidity_invalid'] = True
            else:
                validation['weather_status'] = 'unavailable'
        except Exception as e:
            validation['weather_status'] = 'error'
            validation['api_health']['weather_error'] = str(e)
        
        # 检查假期数据
        try:
            holidays = self.load_holiday_data()
            if holidays:
                validation['holidays_status'] = 'available'
                current_year_holidays = [h for h in holidays if h.date.year == datetime.now().year]
                validation['current_year_holidays'] = len(current_year_holidays)
            else:
                validation['holidays_status'] = 'unavailable'
        except Exception as e:
            validation['holidays_status'] = 'error'
            validation['api_health']['holidays_error'] = str(e)
        
        # 检查交通数据
        try:
            traffic = self.load_traffic_data()
            if traffic:
                validation['traffic_status'] = 'available'
                # 检查数据时效性
                latest_time = max(t.timestamp for t in traffic)
                minutes_old = (datetime.now() - latest_time).total_seconds() / 60
                validation['traffic_freshness'] = f"{minutes_old:.1f} minutes old"
                
                # 验证数据合理性
                for t in traffic:
                    if t.speed_kmh < 0 or t.speed_kmh > 120:
                        validation['api_health']['traffic_speed_invalid'] = True
                    if t.congestion_level < 1 or t.congestion_level > 5:
                        validation['api_health']['traffic_congestion_invalid'] = True
            else:
                validation['traffic_status'] = 'unavailable'
        except Exception as e:
            validation['traffic_status'] = 'error'
            validation['api_health']['traffic_error'] = str(e)
        
        return validation
    
    def _validate_data_integrity(self) -> Dict[str, Any]:
        """验证数据完整性"""
        integrity = {
            'store_order_consistency': True,
            'date_continuity': True,
            'cross_reference_issues': [],
            'missing_data_periods': []
        }
        
        try:
            # 检查门店-订单一致性
            stores = self.load_store_locations()
            orders = self.load_order_data()
            
            if stores and orders:
                store_codes = {s.store_code for s in stores}
                order_store_codes = {o.fulfillment_store_code for o in orders}
                
                missing_stores = order_store_codes - store_codes
                if missing_stores:
                    integrity['store_order_consistency'] = False
                    integrity['cross_reference_issues'].append(
                        f"订单中引用了 {len(missing_stores)} 个不存在的门店代码"
                    )
            
            # 检查日期连续性
            if orders:
                order_dates = sorted(set(o.order_date for o in orders))
                if len(order_dates) > 1:
                    date_gaps = []
                    for i in range(1, len(order_dates)):
                        gap_days = (order_dates[i] - order_dates[i-1]).days
                        if gap_days > 7:  # 超过7天的间隔
                            date_gaps.append((order_dates[i-1], order_dates[i], gap_days))
                    
                    if date_gaps:
                        integrity['date_continuity'] = False
                        integrity['missing_data_periods'] = [
                            f"{start} to {end} ({days} days)" 
                            for start, end, days in date_gaps
                        ]
        
        except Exception as e:
            integrity['validation_error'] = str(e)
        
        return integrity
    
    def _calculate_overall_quality_score(self, quality_report: Dict[str, Any]) -> float:
        """计算总体质量分数"""
        scores = []
        
        # 门店数据分数
        if 'stores' in quality_report and 'coordinate_accuracy' in quality_report['stores']:
            scores.append(quality_report['stores']['coordinate_accuracy'])
        
        # 订单数据分数
        if 'orders' in quality_report and 'data_completeness' in quality_report['orders']:
            scores.append(quality_report['orders']['data_completeness'])
        
        # 外部数据分数
        external = quality_report.get('external_data', {})
        external_score = 0
        if external.get('weather_status') == 'available':
            external_score += 33.33
        if external.get('holidays_status') == 'available':
            external_score += 33.33
        if external.get('traffic_status') == 'available':
            external_score += 33.34
        scores.append(external_score)
        
        # 数据完整性分数
        integrity = quality_report.get('data_integrity', {})
        integrity_score = 100
        if not integrity.get('store_order_consistency', True):
            integrity_score -= 30
        if not integrity.get('date_continuity', True):
            integrity_score -= 20
        scores.append(max(0, integrity_score))
        
        return np.mean(scores) if scores else 0.0
    
    def _generate_quality_recommendations(self, quality_report: Dict[str, Any]) -> List[str]:
        """生成质量改进建议"""
        recommendations = []
        
        # 门店数据建议
        stores = quality_report.get('stores', {})
        if stores.get('coordinate_accuracy', 0) < 95:
            recommendations.append("建议重新验证门店坐标，提高地理编码准确性")
        
        # 订单数据建议
        orders = quality_report.get('orders', {})
        if orders.get('data_completeness', 0) < 90:
            recommendations.append("建议检查订单数据完整性，修复缺失字段")
        
        # 外部数据建议
        external = quality_report.get('external_data', {})
        if external.get('weather_status') != 'available':
            recommendations.append("建议检查HKO天气API连接，确保天气数据可用")
        if external.get('traffic_status') != 'available':
            recommendations.append("建议检查交通API连接，确保实时交通数据可用")
        
        # 数据完整性建议
        integrity = quality_report.get('data_integrity', {})
        if not integrity.get('store_order_consistency', True):
            recommendations.append("建议同步门店主数据，确保订单引用的门店存在")
        if not integrity.get('date_continuity', True):
            recommendations.append("建议补充缺失日期的订单数据，保持数据连续性")
        
        return recommendations
    
    # ==================== 自动化更新 ====================
    
    def setup_automatic_updates(self):
        """设置自动化数据更新"""
        logger.info("设置自动化数据更新...")
        
        # 每小时更新天气数据
        schedule.every().hour.do(lambda: self.load_weather_data(force_refresh=True))
        
        # 每15分钟更新交通数据
        schedule.every(15).minutes.do(lambda: self.load_traffic_data(force_refresh=True))
        
        # 每天凌晨2点更新所有数据
        schedule.every().day.at("02:00").do(self.full_data_refresh)
        
        # 每天上午8点执行数据质量检查
        schedule.every().day.at("08:00").do(self.check_data_quality)
        
        logger.info("✅ 自动化更新任务已设置")
    
    def start_scheduler(self):
        """启动调度器"""
        def run_scheduler():
            while True:
                schedule.run_pending()
                time.sleep(60)  # 每分钟检查一次
        
        scheduler_thread = threading.Thread(target=run_scheduler, daemon=True)
        scheduler_thread.start()
        logger.info("✅ 数据更新调度器已启动")
    
    def full_data_refresh(self):
        """全量数据刷新"""
        logger.info("执行全量数据刷新...")
        
        try:
            # 并行刷新所有数据
            with ThreadPoolExecutor(max_workers=self.config['max_workers']) as executor:
                futures = {
                    executor.submit(self.load_store_locations, True): 'stores',
                    executor.submit(self.load_order_data, None, None, True): 'orders',
                    executor.submit(self.load_weather_data, True): 'weather',
                    executor.submit(self.load_holiday_data, None, True): 'holidays',
                    executor.submit(self.load_traffic_data, True): 'traffic'
                }
                
                results = {}
                for future in as_completed(futures):
                    data_type = futures[future]
                    try:
                        result = future.result(timeout=self.config['timeout_seconds'])
                        results[data_type] = len(result) if result else 0
                        logger.info(f"✅ {data_type} 数据刷新完成: {results[data_type]} 条记录")
                    except Exception as e:
                        logger.error(f"❌ {data_type} 数据刷新失败: {str(e)}")
                        results[data_type] = 0
            
            # 更新质量统计
            self.quality_stats['last_update'] = datetime.now()
            self.quality_stats['data_completeness'] = results
            
            logger.info("✅ 全量数据刷新完成")
            
        except Exception as e:
            logger.error(f"全量数据刷新失败: {str(e)}")
            self.quality_stats['error_count'] += 1
    
    # ==================== 辅助方法 ====================
    
    def _is_cache_valid(self, cache_key: str) -> bool:
        """检查缓存是否有效"""
        if cache_key not in self._cache_timestamps:
            return False
        
        cache_time = self._cache_timestamps[cache_key]
        ttl_minutes = self.config['cache_ttl_minutes']
        
        return (datetime.now() - cache_time).total_seconds() < ttl_minutes * 60
    
    def _validate_coordinates(self, lat: float, lng: float) -> bool:
        """验证坐标是否在香港范围内"""
        return 22.1 <= lat <= 22.6 and 113.8 <= lng <= 114.5
    
    def _generate_sample_weather_data(self) -> List[WeatherData]:
        """生成示例天气数据"""
        weather_data = []
        for i in range(7):  # 未来7天
            target_date = date.today() + timedelta(days=i)
            weather = WeatherData(
                date=target_date,
                temperature_high=25.0 + np.random.normal(0, 3),
                temperature_low=20.0 + np.random.normal(0, 2),
                humidity=70.0 + np.random.normal(0, 10),
                condition=np.random.choice(list(WeatherCondition)),
                rainfall=max(0, np.random.normal(0, 5))
            )
            weather_data.append(weather)
        return weather_data
    
    def _generate_sample_traffic_data(self) -> List[TrafficCondition]:
        """生成示例交通数据"""
        traffic_data = []
        road_segments = ["Central-Causeway Bay", "Tsim Sha Tsui-Mong Kok", "Sha Tin-Tai Po"]
        
        for segment in road_segments:
            traffic = TrafficCondition(
                timestamp=datetime.now(),
                road_segment=segment,
                speed_kmh=40.0 + np.random.normal(0, 10),
                congestion_level=np.random.randint(1, 6),
                travel_time_minutes=15.0 + np.random.normal(0, 5),
                incident_reported=np.random.random() < 0.1
            )
            traffic_data.append(traffic)
        
        return traffic_data
    
    # ==================== 外部API集成方法 ====================
    
    def _fetch_hko_weather_data(self) -> List[WeatherData]:
        """从HKO API获取天气数据"""
        try:
            # 使用新的HKO Fetcher
            import sys
            from pathlib import Path
            
            # 添加项目根目录到路径
            project_root = Path(__file__).parent.parent.parent
            sys.path.insert(0, str(project_root))
            
            from src.modules.data.implementations.hko_fetcher import HKOWeatherFetcher
            
            hko_fetcher = HKOWeatherFetcher(timeout=self.config['timeout_seconds'])
            
            # 获取9天天气预报
            weather_data = hko_fetcher.fetch_weather_forecast(days=9)
            
            # 获取当前天气并更新今天的数据
            try:
                current = hko_fetcher.fetch_current_weather()
                today = date.today()
                
                # 如果今天的预报存在，更新实际数据
                for weather in weather_data:
                    if weather.date == today:
                        weather.temperature_high = max(weather.temperature_high, current.temperature_high)
                        weather.temperature_low = min(weather.temperature_low, current.temperature_low)
                        weather.humidity = current.humidity
                        if current.rainfall:
                            weather.rainfall = current.rainfall
                        break
                else:
                    # 如果今天不在预报中，添加当前天气
                    weather_data.insert(0, current)
                    
            except Exception as e:
                logger.warning(f"获取当前天气失败: {e}")
            
            return weather_data
            
        except ImportError as e:
            logger.error(f"HKO Fetcher模块导入失败: {e}")
            return []
        except Exception as e:
            logger.error(f"HKO API调用失败: {e}")
            return []

    
    def _fetch_real_traffic_data(self) -> List[TrafficCondition]:
        """从交通API获取实时交通数据"""
        try:
            # 使用新的Traffic Fetcher
            import sys
            from pathlib import Path
            
            # 添加项目根目录到路径
            project_root = Path(__file__).parent.parent.parent
            sys.path.insert(0, str(project_root))
            
            from src.modules.data.implementations.traffic_fetcher import HKTrafficFetcher
            
            traffic_fetcher = HKTrafficFetcher(timeout=self.config['timeout_seconds'])
            
            # 获取当前交通状况
            traffic_data = traffic_fetcher.fetch_current_traffic()
            
            return traffic_data
            
        except ImportError as e:
            logger.error(f"Traffic Fetcher模块导入失败: {e}")
            return []
        except Exception as e:
            logger.error(f"交通API调用失败: {e}")
            return []
    
    def _enhance_holiday_data_loading(self, year: int = None) -> List[PublicHoliday]:
        """增强的假期数据加载 - 支持在线更新"""
        if year is None:
            year = datetime.now().year
            
        try:
            # 使用新的Holiday Fetcher
            import sys
            from pathlib import Path
            
            # 添加项目根目录到路径
            project_root = Path(__file__).parent.parent.parent
            sys.path.insert(0, str(project_root))
            
            from src.modules.data.implementations.holiday_fetcher import HKHolidayFetcher
            
            holiday_fetcher = HKHolidayFetcher(
                timeout=self.config['timeout_seconds'],
                cache_dir=str(self.external_data_path)
            )
            
            # 获取指定年份的假期数据
            holidays = holiday_fetcher.fetch_holidays(year)
            
            logger.info(f"从Holiday Fetcher获取到 {len(holidays)} 个假期")
            return holidays
            
        except ImportError as e:
            logger.error(f"Holiday Fetcher模块导入失败: {e}")
            return self._fallback_holiday_loading(year)
        except Exception as e:
            logger.error(f"Holiday Fetcher调用失败: {e}")
            return self._fallback_holiday_loading(year)
    
    def _fallback_holiday_loading(self, year: int) -> List[PublicHoliday]:
        """备用假期数据加载方法"""
        try:
            # 回退到本地文件
            holidays_file = self.external_data_path / "public_holidays_2025.json"
            if holidays_file.exists():
                with open(holidays_file, 'r', encoding='utf-8') as f:
                    holidays_data = json.load(f)
                
                # 解析假期数据
                holiday_events = holidays_data['vcalendar'][0]['vevent']
                holidays = []
                
                for event in holiday_events:
                    date_str = event['dtstart'][0]
                    event_date = datetime.strptime(date_str, '%Y%m%d').date()
                    
                    if event_date.year == year:
                        holiday = PublicHoliday(
                            date=event_date,
                            name=event['summary'],
                            type="public"
                        )
                        holidays.append(holiday)
                
                logger.info(f"从备用方法获取到 {len(holidays)} 个假期")
                return holidays
            else:
                logger.error(f"假期文件不存在: {holidays_file}")
                return []
                
        except Exception as e:
            logger.error(f"备用假期数据加载失败: {e}")
            return []

    
    def get_pipeline_status(self) -> Dict[str, Any]:
        """获取管道状态"""
        return {
            'pipeline_status': 'running',
            'last_update': self.quality_stats['last_update'],
            'cache_status': {
                key: self._is_cache_valid(key) 
                for key in self._cache_timestamps.keys()
            },
            'quality_stats': self.quality_stats,
            'config': self.config
        }

# ==================== 全局管道实例 ====================

# 创建全局数据管道实例
global_pipeline = DataPipeline()

def get_pipeline() -> DataPipeline:
    """获取全局数据管道实例"""
    return global_pipeline

# ==================== 测试和演示 ====================

if __name__ == "__main__":
    print("🚀 启动数据管道测试...")
    
    # 创建数据管道
    pipeline = DataPipeline()
    
    # 测试数据加载
    print("\n📊 测试数据加载...")
    stores = pipeline.load_store_locations()
    print(f"✅ 门店数据: {len(stores)} 个门店")
    
    orders = pipeline.load_order_data()
    print(f"✅ 订单数据: {len(orders)} 个订单")
    
    weather = pipeline.load_weather_data()
    print(f"✅ 天气数据: {len(weather)} 条记录")
    
    holidays = pipeline.load_holiday_data()
    print(f"✅ 假期数据: {len(holidays)} 个假期")
    
    # 测试数据集成
    print("\n🔗 测试数据集成...")
    integrated_df = pipeline.create_integrated_dataset()
    print(f"✅ 集成数据集: {len(integrated_df)} 条记录")
    print(f"   包含列: {list(integrated_df.columns)}")
    
    # 测试数据质量检查
    print("\n🔍 测试数据质量检查...")
    quality_report = pipeline.check_data_quality()
    print(f"✅ 数据质量分数: {quality_report['overall_score']:.1f}")
    
    # 显示管道状态
    print("\n📋 管道状态:")
    status = pipeline.get_pipeline_status()
    print(f"   状态: {status['pipeline_status']}")
    print(f"   最后更新: {status['last_update']}")
    print(f"   错误计数: {status['quality_stats']['error_count']}")
    
    print("\n🎉 数据管道测试完成！")
    print("💡 提示: 可调用 pipeline.setup_automatic_updates() 启用自动更新")