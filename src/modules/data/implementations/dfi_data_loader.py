"""
DFI企业数据加载器
加载和处理Mannings DFI提供的企业数据

Author: 王晔宸 (Team Lead)
Date: 2026-03-12
"""

import pandas as pd
from pathlib import Path
from typing import List, Dict, Optional, Any, Tuple
from datetime import date, datetime
import logging

from src.core.data_schema import (
    StoreSchema, DateFeatureSchema, OrderDetailSchema, 
    FulfillmentDetailSchema, DataLoaderInterface,
    validate_store_data, validate_fulfillment_data
)

logger = logging.getLogger(__name__)


class DFIDataLoader(DataLoaderInterface):
    """
    DFI企业数据加载器
    负责加载和解析Mannings提供的4张CSV数据表
    """
    
    def __init__(self, data_path: str = "data/dfi/raw/"):
        self.data_path = Path(data_path)
        self._cache = {}
        
        # 文件名映射
        self.file_mapping = {
            'stores': 'dim_store.csv',
            'dates': 'dim_date.csv',
            'orders': 'case_study_order_detail-000000000000.csv',
            'fulfillment': 'fufillment_detail-000000000000.csv'
        }
    
    def _get_file_path(self, key: str) -> Path:
        """获取数据文件路径"""
        filename = self.file_mapping.get(key)
        if not filename:
            raise ValueError(f"Unknown data key: {key}")
        return self.data_path / filename
    
    def _load_csv(self, key: str, use_cache: bool = True) -> pd.DataFrame:
        """加载CSV文件"""
        if use_cache and key in self._cache:
            return self._cache[key]
        
        file_path = self._get_file_path(key)
        if not file_path.exists():
            raise FileNotFoundError(f"Data file not found: {file_path}")
        
        logger.info(f"Loading {key} from {file_path}")
        df = pd.read_csv(file_path)
        
        if use_cache:
            self._cache[key] = df
        
        return df
    
    # ==================== 门店数据 ====================
    
    def load_stores_raw(self) -> pd.DataFrame:
        """加载原始门店数据"""
        return self._load_csv('stores')
    
    def load_stores(self) -> List[StoreSchema]:
        """加载并解析门店数据"""
        df = self.load_stores_raw()
        stores = []
        
        for _, row in df.iterrows():
            try:
                store = StoreSchema.from_csv_row(row)
                stores.append(store)
            except Exception as e:
                logger.warning(f"Failed to parse store row: {e}")
                continue
        
        logger.info(f"Loaded {len(stores)} stores")
        return stores
    
    def get_store_by_code(self, store_code: int) -> Optional[StoreSchema]:
        """根据门店代码获取门店信息"""
        stores = self.load_stores()
        for store in stores:
            if store.store_code == store_code:
                return store
        return None
    
    def get_stores_by_district(self, district: str) -> List[StoreSchema]:
        """根据区域获取门店列表"""
        stores = self.load_stores()
        return [s for s in stores if s.district == district]
    
    def get_active_store_codes(self) -> List[int]:
        """
        获取有订单数据的活跃门店代码列表
        """
        orders_df = self._load_csv('orders')
        return orders_df['fulfillment_store_code'].unique().tolist()
    
    # ==================== 日期特征 ====================
    
    def load_dates_raw(self) -> pd.DataFrame:
        """加载原始日期特征数据"""
        return self._load_csv('dates')
    
    def load_date_features(self, start_date: date = None, end_date: date = None) -> List[DateFeatureSchema]:
        """加载日期特征数据"""
        df = self.load_dates_raw()
        features = []
        
        for _, row in df.iterrows():
            try:
                feature = DateFeatureSchema.from_csv_row(row)
                
                # 日期范围过滤
                if start_date and feature.calendar_date < start_date:
                    continue
                if end_date and feature.calendar_date > end_date:
                    continue
                
                features.append(feature)
            except Exception as e:
                logger.warning(f"Failed to parse date row: {e}")
                continue
        
        logger.info(f"Loaded {len(features)} date features")
        return features
    
    def get_date_feature(self, target_date: date) -> Optional[DateFeatureSchema]:
        """获取特定日期的特征"""
        features = self.load_date_features(target_date, target_date)
        return features[0] if features else None
    
    def get_promo_dates(self, promo_type: str) -> List[date]:
        """获取特定促销类型的日期列表"""
        df = self.load_dates_raw()
        
        promo_column_mapping = {
            'public_holiday': 'if_public_holiday',
            'enjoycard_day': 'if_enjoycard_day',
            'yuu_day': 'if_yuu_day',
            'happy_hour': 'if_happy_hour',
            'baby_fair': 'if_baby_fair',
            '618': 'if_618_day',
            'double11': 'if_double11_day',
            '38': 'if_38_day',
            'anniversary': 'if_anniversary_day'
        }
        
        column = promo_column_mapping.get(promo_type)
        if not column:
            return []
        
        promo_df = df[df[column] == 1]
        return [datetime.strptime(d, '%Y/%m/%d').date() for d in promo_df['calendar_date'].tolist()]
    
    # ==================== 订单数据 ====================
    
    def load_orders_raw(self) -> pd.DataFrame:
        """加载原始订单数据"""
        return self._load_csv('orders')
    
    def load_orders(self, start_date: date = None, end_date: date = None,
                    store_codes: Optional[List[int]] = None) -> List[OrderDetailSchema]:
        """加载订单数据"""
        df = self.load_orders_raw()
        
        # 日期过滤
        if start_date:
            df = df[df['dt'] >= start_date.strftime('%Y-%m-%d')]
        if end_date:
            df = df[df['dt'] <= end_date.strftime('%Y-%m-%d')]
        
        # 门店过滤
        if store_codes:
            df = df[df['fulfillment_store_code'].isin(store_codes)]
        
        orders = []
        for _, row in df.iterrows():
            try:
                order = OrderDetailSchema.from_csv_row(row)
                orders.append(order)
            except Exception as e:
                logger.warning(f"Failed to parse order row: {e}")
                continue
        
        logger.info(f"Loaded {len(orders)} orders")
        return orders
    
    def get_daily_order_summary(self, store_code: Optional[int] = None) -> pd.DataFrame:
        """
        获取每日订单汇总
        返回: DataFrame with columns [dt, store_code, order_count, total_quantity]
        """
        df = self.load_orders_raw()
        
        if store_code:
            df = df[df['fulfillment_store_code'] == store_code]
        
        summary = df.groupby(['dt', 'fulfillment_store_code']).agg({
            'order_id': 'count',
            'total_quantity_cnt': 'sum',
            'unique_sku_cnt': 'mean'
        }).reset_index()
        
        summary.columns = ['dt', 'store_code', 'order_count', 'total_quantity', 'avg_sku_per_order']
        return summary
    
    def get_store_order_stats(self) -> pd.DataFrame:
        """获取各门店订单统计"""
        df = self.load_orders_raw()
        
        stats = df.groupby('fulfillment_store_code').agg({
            'order_id': 'count',
            'total_quantity_cnt': ['sum', 'mean'],
            'unique_sku_cnt': 'mean',
            'dt': ['min', 'max']
        }).reset_index()
        
        stats.columns = [
            'store_code', 'total_orders', 'total_quantity', 
            'avg_quantity_per_order', 'avg_sku_per_order',
            'first_order_date', 'last_order_date'
        ]
        return stats
    
    # ==================== 履约数据 ====================
    
    def load_fulfillment_raw(self) -> pd.DataFrame:
        """加载原始履约数据"""
        return self._load_csv('fulfillment')
    
    def load_fulfillment(self, order_ids: Optional[List[str]] = None) -> List[FulfillmentDetailSchema]:
        """加载履约数据"""
        df = self.load_fulfillment_raw()
        
        if order_ids:
            df = df[df['order_id'].isin(order_ids)]
        
        fulfillments = []
        for _, row in df.iterrows():
            try:
                f = FulfillmentDetailSchema.from_csv_row(row)
                fulfillments.append(f)
            except Exception as e:
                logger.warning(f"Failed to parse fulfillment row: {e}")
                continue
        
        logger.info(f"Loaded {len(fulfillments)} fulfillment records")
        return fulfillments
    
    def get_sla_analysis(self) -> Dict[str, Any]:
        """
        获取SLA分析结果
        计算各时间段的平均耗时
        """
        df = self.load_fulfillment_raw()
        
        # 转换时间戳
        time_columns = [
            'order_create_time', 'ready_time', 'assigned_time', 
            'picking_time', 'picked_time', 'packed_time', 
            'shipped_time', 'ready_for_pickup_time', 'completed_time'
        ]
        
        for col in time_columns:
            if col in df.columns:
                df[col] = pd.to_datetime(df[col], errors='coerce')
        
        analysis = {
            'total_orders': len(df),
            'completed_orders': df['completed_time'].notna().sum(),
            'cancelled_orders': df['cancel_time'].notna().sum() if 'cancel_time' in df.columns else 0
        }
        
        # 计算各阶段耗时 (分钟)
        stages = [
            ('order_to_ready', 'order_create_time', 'ready_time'),
            ('ready_to_picking', 'ready_time', 'picking_time'),
            ('picking_duration', 'picking_time', 'picked_time'),
            ('packing_duration', 'picked_time', 'packed_time'),
            ('shipping_duration', 'packed_time', 'shipped_time'),
            ('delivery_duration', 'shipped_time', 'ready_for_pickup_time'),
            ('customer_pickup', 'ready_for_pickup_time', 'completed_time'),
            ('total_fulfillment', 'order_create_time', 'ready_for_pickup_time')
        ]
        
        analysis['stage_durations'] = {}
        for stage_name, start_col, end_col in stages:
            if start_col in df.columns and end_col in df.columns:
                valid = df[df[start_col].notna() & df[end_col].notna()]
                if len(valid) > 0:
                    durations = (valid[end_col] - valid[start_col]).dt.total_seconds() / 60
                    # 过滤异常值 (负数或超过7天)
                    durations = durations[(durations >= 0) & (durations < 10080)]
                    
                    if len(durations) > 0:
                        analysis['stage_durations'][stage_name] = {
                            'mean_min': float(durations.mean()),
                            'median_min': float(durations.median()),
                            'std_min': float(durations.std()),
                            'p90_min': float(durations.quantile(0.9)),
                            'sample_size': len(durations)
                        }
        
        return analysis
    
    # ==================== 数据质量报告 ====================
    
    def generate_data_quality_report(self) -> Dict[str, Any]:
        """生成数据质量报告"""
        report = {
            'generated_at': datetime.now().isoformat(),
            'data_path': str(self.data_path)
        }
        
        # 门店数据
        try:
            stores = self.load_stores()
            report['stores'] = validate_store_data(stores)
        except Exception as e:
            report['stores'] = {'error': str(e)}
        
        # 日期数据
        try:
            dates_df = self.load_dates_raw()
            report['dates'] = {
                'total_days': len(dates_df),
                'date_range': f"{dates_df['calendar_date'].min()} to {dates_df['calendar_date'].max()}",
                'promo_days': {
                    'public_holiday': int(dates_df['if_public_holiday'].sum()),
                    'enjoycard_day': int(dates_df['if_enjoycard_day'].sum()),
                    '618_day': int(dates_df['if_618_day'].sum()),
                    'double11_day': int(dates_df['if_double11_day'].sum())
                }
            }
        except Exception as e:
            report['dates'] = {'error': str(e)}
        
        # 订单数据
        try:
            orders_df = self.load_orders_raw()
            report['orders'] = {
                'total_orders': len(orders_df),
                'unique_users': orders_df['user_id'].nunique(),
                'unique_stores': orders_df['fulfillment_store_code'].nunique(),
                'date_range': f"{orders_df['dt'].min()} to {orders_df['dt'].max()}",
                'avg_quantity_per_order': float(orders_df['total_quantity_cnt'].mean()),
                'avg_sku_per_order': float(orders_df['unique_sku_cnt'].mean())
            }
        except Exception as e:
            report['orders'] = {'error': str(e)}
        
        # 履约数据
        try:
            sla = self.get_sla_analysis()
            report['fulfillment'] = sla
        except Exception as e:
            report['fulfillment'] = {'error': str(e)}
        
        return report
    
    # ==================== 预测数据准备 ====================
    
    def prepare_forecast_training_data(self) -> pd.DataFrame:
        """
        准备需求预测训练数据
        合并订单数据、日期特征
        """
        # 加载基础数据
        orders = self.get_daily_order_summary()
        dates_df = self.load_dates_raw()
        
        # 转换日期格式
        dates_df['dt'] = dates_df['calendar_date'].apply(
            lambda x: datetime.strptime(x, '%Y/%m/%d').strftime('%Y-%m-%d')
        )
        
        # 合并
        merged = orders.merge(dates_df, on='dt', how='left')
        
        logger.info(f"Prepared forecast training data: {len(merged)} records")
        return merged
    
    def prepare_routing_input(self, target_date: date) -> Dict[str, Any]:
        """
        准备路径优化输入数据
        """
        # 获取门店信息
        stores = self.load_stores()
        active_codes = self.get_active_store_codes()
        
        # 获取日期特征
        date_feature = self.get_date_feature(target_date)
        
        # 获取历史平均需求作为预测基准
        orders_df = self.load_orders_raw()
        store_avg = orders_df.groupby('fulfillment_store_code').agg({
            'total_quantity_cnt': 'mean'
        }).to_dict()['total_quantity_cnt']
        
        # 构建输入
        routing_input = {
            'date': target_date.isoformat(),
            'stores': [],
            'is_promo_day': date_feature.is_public_holiday if date_feature else False,
            'is_weekend': date_feature.is_weekend if date_feature else False
        }
        
        for store in stores:
            if store.store_code in active_codes:
                avg_demand = store_avg.get(store.store_code, 50)
                routing_input['stores'].append({
                    'store_code': store.store_code,
                    'district': store.district,
                    'address': store.address,
                    'demand': avg_demand,
                    'latitude': store.latitude,
                    'longitude': store.longitude
                })
        
        return routing_input


# ==================== 测试函数 ====================

def test_dfi_loader():
    """测试DFI数据加载器"""
    loader = DFIDataLoader()
    
    print("=" * 60)
    print("DFI Data Loader Test")
    print("=" * 60)
    
    # 测试门店加载
    print("\n1. Testing store loading...")
    stores = loader.load_stores()
    print(f"   Loaded {len(stores)} stores")
    if stores:
        print(f"   Sample: {stores[0].store_code} - {stores[0].district}")
    
    # 测试日期加载
    print("\n2. Testing date features...")
    dates = loader.load_date_features()
    print(f"   Loaded {len(dates)} date features")
    promo_days = loader.get_promo_dates('public_holiday')
    print(f"   Public holidays: {len(promo_days)} days")
    
    # 测试订单加载
    print("\n3. Testing order loading...")
    orders = loader.load_orders()
    print(f"   Loaded {len(orders)} orders")
    
    # 测试履约分析
    print("\n4. Testing SLA analysis...")
    sla = loader.get_sla_analysis()
    print(f"   Total orders: {sla['total_orders']}")
    print(f"   Completed: {sla['completed_orders']}")
    if 'total_fulfillment' in sla.get('stage_durations', {}):
        tf = sla['stage_durations']['total_fulfillment']
        print(f"   Avg fulfillment time: {tf['mean_min']:.1f} min (median: {tf['median_min']:.1f} min)")
    
    # 生成质量报告
    print("\n5. Generating quality report...")
    report = loader.generate_data_quality_report()
    print(f"   Report generated at: {report['generated_at']}")
    
    print("\n" + "=" * 60)
    print("All tests passed!")
    print("=" * 60)
    
    return report


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    test_dfi_loader()
