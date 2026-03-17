#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
万宁数据集成演示脚本
展示企业数据与外部数据的集成应用示例

创建时间: 2026-03-17
作者: AI Assistant
"""

import pandas as pd
import numpy as np
import json
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
import warnings
warnings.filterwarnings('ignore')

# 设置中文字体
plt.rcParams['font.sans-serif'] = ['SimHei', 'Arial Unicode MS']
plt.rcParams['axes.unicode_minus'] = False

class DataIntegrationDemo:
    """数据集成演示类"""
    
    def __init__(self):
        self.base_path = Path(".")
        self.raw_data_path = self.base_path / "data" / "dfi" / "raw"
        self.processed_data_path = self.base_path / "data" / "dfi" / "processed"
        self.external_data_path = self.base_path / "data" / "official"
        
    def load_all_data(self):
        """加载所有数据"""
        print("📊 加载企业数据和外部数据...")
        
        # 加载企业数据
        self.dim_store = pd.read_csv(self.raw_data_path / "dim_store.csv")
        self.order_detail = pd.read_csv(self.raw_data_path / "case_study_order_detail-000000000000.csv")
        self.fulfillment_detail = pd.read_csv(self.raw_data_path / "fufillment_detail-000000000000.csv")
        
        # 加载外部数据
        self.enhanced_coordinates = pd.read_csv(self.processed_data_path / "store_coordinates_enhanced_v2.csv")
        
        # 加载公共假期数据
        with open(self.external_data_path / "public_holidays_2025.json", 'r', encoding='utf-8') as f:
            holidays_data = json.load(f)
        
        # 解析公共假期
        holiday_events = holidays_data['vcalendar'][0]['vevent']
        self.holidays = []
        for event in holiday_events:
            date_str = event['dtstart'][0]
            formatted_date = f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}"
            self.holidays.append({
                'date': formatted_date,
                'name': event['summary']
            })
        self.holidays_df = pd.DataFrame(self.holidays)
        
        print(f"✅ 数据加载完成:")
        print(f"   门店数据: {len(self.dim_store)} 条")
        print(f"   订单数据: {len(self.order_detail)} 条")
        print(f"   履约数据: {len(self.fulfillment_detail)} 条")
        print(f"   增强坐标: {len(self.enhanced_coordinates)} 条")
        print(f"   公共假期: {len(self.holidays)} 个")
    
    def demo_geographic_integration(self):
        """演示地理位置数据集成"""
        print("\n🗺️ 演示1: 地理位置数据集成")
        
        # 将订单数据与门店地理位置集成
        orders_with_location = self.order_detail.merge(
            self.enhanced_coordinates[['store_code', 'district', 'latitude', 'longitude', 'geocode_status']],
            left_on='fulfillment_store_code',
            right_on='store_code',
            how='left'
        )
        
        # 分析各区域的订单分布
        district_analysis = orders_with_location.groupby('district').agg({
            'order_id': 'count',
            'total_quantity_cnt': 'sum',
            'unique_sku_cnt': 'mean'
        }).round(2)
        district_analysis.columns = ['订单数量', '总商品数', '平均SKU数']
        district_analysis = district_analysis.sort_values('订单数量', ascending=False)
        
        print("📊 各区域订单分布 (Top 10):")
        print(district_analysis.head(10))
        
        # 计算门店坐标精度分布
        precision_analysis = orders_with_location['geocode_status'].value_counts()
        print(f"\n📍 门店坐标精度分布:")
        for status, count in precision_analysis.items():
            percentage = count / len(orders_with_location) * 100
            print(f"   {status}: {count} 订单 ({percentage:.1f}%)")
        
        return orders_with_location
    
    def demo_temporal_integration(self):
        """演示时间数据集成"""
        print("\n📅 演示2: 时间数据集成 - 节假日影响分析")
        
        # 转换日期格式
        self.order_detail['dt'] = pd.to_datetime(self.order_detail['dt'])
        self.holidays_df['date'] = pd.to_datetime(self.holidays_df['date'])
        
        # 标记节假日订单
        holiday_dates = set(self.holidays_df['date'].dt.date)
        self.order_detail['is_holiday'] = self.order_detail['dt'].dt.date.isin(holiday_dates)
        
        # 分析节假日vs平日的订单模式
        holiday_analysis = self.order_detail.groupby('is_holiday').agg({
            'order_id': 'count',
            'total_quantity_cnt': 'mean',
            'unique_sku_cnt': 'mean',
            'fulfillment_store_code': 'nunique'
        }).round(2)
        
        holiday_analysis.index = ['平日', '节假日']
        holiday_analysis.columns = ['订单总数', '平均商品数/单', '平均SKU数/单', '活跃门店数']
        
        print("📊 节假日 vs 平日订单对比:")
        print(holiday_analysis)
        
        # 计算节假日影响
        holiday_impact = {
            '订单量变化': f"{(holiday_analysis.loc['节假日', '订单总数'] / holiday_analysis.loc['平日', '订单总数'] - 1) * 100:.1f}%",
            '平均商品数变化': f"{(holiday_analysis.loc['节假日', '平均商品数/单'] / holiday_analysis.loc['平日', '平均商品数/单'] - 1) * 100:.1f}%",
            '活跃门店变化': f"{(holiday_analysis.loc['节假日', '活跃门店数'] / holiday_analysis.loc['平日', '活跃门店数'] - 1) * 100:.1f}%"
        }
        
        print(f"\n🎯 节假日影响分析:")
        for metric, change in holiday_impact.items():
            print(f"   {metric}: {change}")
        
        return holiday_analysis
    
    def demo_fulfillment_analysis(self):
        """演示履约数据分析"""
        print("\n⏱️ 演示3: 履约时间分析")
        
        # 转换时间列
        time_columns = ['order_create_time', 'ready_time', 'shipped_time', 'completed_time']
        for col in time_columns:
            if col in self.fulfillment_detail.columns:
                self.fulfillment_detail[col] = pd.to_datetime(self.fulfillment_detail[col], errors='coerce')
        
        # 计算履约时间指标
        fulfillment_metrics = {}
        
        # 准备时间 (下单到准备完成)
        if 'order_create_time' in self.fulfillment_detail.columns and 'ready_time' in self.fulfillment_detail.columns:
            ready_time_diff = (self.fulfillment_detail['ready_time'] - self.fulfillment_detail['order_create_time']).dt.total_seconds() / 60
            fulfillment_metrics['平均准备时间(分钟)'] = ready_time_diff.mean()
            fulfillment_metrics['准备时间中位数(分钟)'] = ready_time_diff.median()
        
        # 配送时间 (发货到完成)
        if 'shipped_time' in self.fulfillment_detail.columns and 'completed_time' in self.fulfillment_detail.columns:
            delivery_time_diff = (self.fulfillment_detail['completed_time'] - self.fulfillment_detail['shipped_time']).dt.total_seconds() / 3600
            fulfillment_metrics['平均配送时间(小时)'] = delivery_time_diff.mean()
            fulfillment_metrics['配送时间中位数(小时)'] = delivery_time_diff.median()
        
        # 总履约时间 (下单到完成)
        if 'order_create_time' in self.fulfillment_detail.columns and 'completed_time' in self.fulfillment_detail.columns:
            total_time_diff = (self.fulfillment_detail['completed_time'] - self.fulfillment_detail['order_create_time']).dt.total_seconds() / 3600
            fulfillment_metrics['平均总履约时间(小时)'] = total_time_diff.mean()
            fulfillment_metrics['总履约时间中位数(小时)'] = total_time_diff.median()
        
        # 完成率
        completion_rate = self.fulfillment_detail['completed_time'].notna().sum() / len(self.fulfillment_detail) * 100
        fulfillment_metrics['订单完成率(%)'] = completion_rate
        
        print("📊 履约时间分析:")
        for metric, value in fulfillment_metrics.items():
            if isinstance(value, float):
                print(f"   {metric}: {value:.2f}")
            else:
                print(f"   {metric}: {value}")
        
        return fulfillment_metrics
    
    def demo_business_insights(self):
        """演示业务洞察分析"""
        print("\n💡 演示4: 综合业务洞察")
        
        # 集成所有数据进行综合分析
        comprehensive_data = self.order_detail.merge(
            self.enhanced_coordinates[['store_code', 'district', 'latitude', 'longitude']],
            left_on='fulfillment_store_code',
            right_on='store_code',
            how='left'
        )
        
        # 添加节假日标记
        holiday_dates = set(self.holidays_df['date'].dt.date)
        comprehensive_data['is_holiday'] = comprehensive_data['dt'].dt.date.isin(holiday_dates)
        
        # 分析各区域在节假日和平日的表现差异
        district_holiday_analysis = comprehensive_data.groupby(['district', 'is_holiday']).agg({
            'order_id': 'count',
            'total_quantity_cnt': 'mean'
        }).round(2)
        
        # 计算节假日影响最大的区域
        district_impact = []
        for district in comprehensive_data['district'].unique():
            if pd.isna(district):
                continue
            
            district_data = district_holiday_analysis.loc[district]
            if len(district_data) == 2:  # 有节假日和平日数据
                holiday_orders = district_data.loc[True, 'order_id'] if True in district_data.index else 0
                weekday_orders = district_data.loc[False, 'order_id'] if False in district_data.index else 0
                
                if weekday_orders > 0:
                    impact = (holiday_orders / weekday_orders - 1) * 100
                    district_impact.append({
                        'district': district,
                        'holiday_impact': impact,
                        'weekday_orders': weekday_orders,
                        'holiday_orders': holiday_orders
                    })
        
        district_impact_df = pd.DataFrame(district_impact)
        district_impact_df = district_impact_df.sort_values('holiday_impact', ascending=False)
        
        print("🎯 节假日影响最大的区域 (Top 5):")
        for _, row in district_impact_df.head(5).iterrows():
            print(f"   {row['district']}: {row['holiday_impact']:+.1f}% (平日:{row['weekday_orders']:.0f}单, 节假日:{row['holiday_orders']:.0f}单)")
        
        # 门店效率分析
        store_efficiency = comprehensive_data.groupby('fulfillment_store_code').agg({
            'order_id': 'count',
            'total_quantity_cnt': 'sum',
            'unique_sku_cnt': 'mean'
        }).round(2)
        store_efficiency.columns = ['订单数', '总商品数', '平均SKU数']
        store_efficiency['效率指数'] = (store_efficiency['订单数'] * store_efficiency['平均SKU数']).round(2)
        store_efficiency = store_efficiency.sort_values('效率指数', ascending=False)
        
        print(f"\n🏆 高效门店 (Top 5):")
        for store_code, row in store_efficiency.head(5).iterrows():
            print(f"   门店{store_code}: 效率指数{row['效率指数']:.1f} (订单:{row['订单数']}, SKU:{row['平均SKU数']:.1f})")
        
        return district_impact_df, store_efficiency
    
    def generate_integration_summary(self):
        """生成集成总结报告"""
        print("\n📋 数据集成演示总结")
        print("=" * 50)
        
        # 数据覆盖率统计
        total_orders = len(self.order_detail)
        orders_with_coords = self.order_detail.merge(
            self.enhanced_coordinates[['store_code']], 
            left_on='fulfillment_store_code', 
            right_on='store_code', 
            how='inner'
        )
        coord_coverage = len(orders_with_coords) / total_orders * 100
        
        holiday_orders = self.order_detail[self.order_detail['is_holiday']].shape[0]
        holiday_coverage = holiday_orders / total_orders * 100
        
        completed_orders = self.fulfillment_detail['completed_time'].notna().sum()
        completion_coverage = completed_orders / len(self.fulfillment_detail) * 100
        
        print(f"📊 数据集成覆盖率:")
        print(f"   地理坐标覆盖: {coord_coverage:.1f}% ({len(orders_with_coords)}/{total_orders} 订单)")
        print(f"   节假日数据覆盖: {holiday_coverage:.1f}% ({holiday_orders}/{total_orders} 订单)")
        print(f"   履约完成覆盖: {completion_coverage:.1f}% ({completed_orders}/{len(self.fulfillment_detail)} 订单)")
        
        print(f"\n🎯 集成价值:")
        print(f"   ✅ 实现了企业数据与外部数据的无缝集成")
        print(f"   ✅ 提供了地理位置、时间、履约三个维度的综合分析")
        print(f"   ✅ 发现了节假日对不同区域的差异化影响")
        print(f"   ✅ 识别了高效门店和优化机会")
        
        print(f"\n🚀 下一步建议:")
        print(f"   1. 建立实时数据集成管道")
        print(f"   2. 开发基于地理位置的智能配送算法")
        print(f"   3. 构建节假日需求预测模型")
        print(f"   4. 实施门店效率优化方案")

def main():
    """主函数"""
    print("🚀 万宁数据集成演示开始...")
    print("=" * 60)
    
    demo = DataIntegrationDemo()
    
    try:
        # 加载数据
        demo.load_all_data()
        
        # 执行各种集成演示
        orders_with_location = demo.demo_geographic_integration()
        holiday_analysis = demo.demo_temporal_integration()
        fulfillment_metrics = demo.demo_fulfillment_analysis()
        district_impact, store_efficiency = demo.demo_business_insights()
        
        # 生成总结
        demo.generate_integration_summary()
        
        print("\n🎉 数据集成演示完成!")
        print("📋 演示展示了以下集成能力:")
        print("   🗺️ 地理位置数据集成 - 区域订单分布分析")
        print("   📅 时间数据集成 - 节假日影响分析")
        print("   ⏱️ 履约数据分析 - 配送时间优化")
        print("   💡 综合业务洞察 - 跨维度分析")
        
    except Exception as e:
        print(f"❌ 演示过程中出现错误: {str(e)}")
        raise

if __name__ == "__main__":
    main()