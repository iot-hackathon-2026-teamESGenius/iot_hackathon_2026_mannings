#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
企业数据与外部数据适配性分析脚本
分析万宁企业数据与已接入的外部数据源的兼容性和集成可能性

创建时间: 2026-03-17
作者: AI Assistant
"""

import pandas as pd
import numpy as np
import json
from datetime import datetime, timedelta
import os
from pathlib import Path

class DataCompatibilityAnalyzer:
    """数据适配性分析器"""
    
    def __init__(self):
        self.base_path = Path(".")
        self.raw_data_path = self.base_path / "data" / "dfi" / "raw"
        self.processed_data_path = self.base_path / "data" / "dfi" / "processed"
        self.external_data_path = self.base_path / "data" / "official"
        
        # 存储分析结果
        self.analysis_results = {}
        
    def load_enterprise_data(self):
        """加载企业原始数据"""
        print("📊 加载企业原始数据...")
        
        # 加载门店维度表
        store_file = self.raw_data_path / "dim_store.csv"
        if store_file.exists():
            self.dim_store = pd.read_csv(store_file)
            print(f"✅ 门店维度表: {len(self.dim_store)} 条记录")
        
        # 加载订单详情表
        order_file = self.raw_data_path / "case_study_order_detail-000000000000.csv"
        if order_file.exists():
            self.order_detail = pd.read_csv(order_file)
            print(f"✅ 订单详情表: {len(self.order_detail)} 条记录")
        
        # 加载履约详情表
        fulfillment_file = self.raw_data_path / "fufillment_detail-000000000000.csv"
        if fulfillment_file.exists():
            self.fulfillment_detail = pd.read_csv(fulfillment_file)
            print(f"✅ 履约详情表: {len(self.fulfillment_detail)} 条记录")
        
        # 加载日期维度表
        date_file = self.raw_data_path / "dim_date.csv"
        if date_file.exists():
            self.dim_date = pd.read_csv(date_file)
            print(f"✅ 日期维度表: {len(self.dim_date)} 条记录")
    
    def load_external_data(self):
        """加载外部数据"""
        print("\n🌐 加载外部数据...")
        
        # 加载增强的门店坐标数据
        enhanced_coords_file = self.processed_data_path / "store_coordinates_enhanced_v2.csv"
        if enhanced_coords_file.exists():
            self.enhanced_coordinates = pd.read_csv(enhanced_coords_file)
            print(f"✅ 增强门店坐标: {len(self.enhanced_coordinates)} 条记录")
        
        # 加载公共假期数据
        holidays_file = self.external_data_path / "public_holidays_2025.json"
        if holidays_file.exists():
            with open(holidays_file, 'r', encoding='utf-8') as f:
                self.public_holidays = json.load(f)
            print(f"✅ 公共假期数据: {len(self.public_holidays)} 个假期")
        
        # 检查交通数据
        traffic_path = self.external_data_path / "traffic"
        if traffic_path.exists():
            traffic_files = list(traffic_path.glob("*.json")) + list(traffic_path.glob("*.csv"))
            print(f"✅ 交通数据文件: {len(traffic_files)} 个文件")
            self.traffic_files = traffic_files
    
    def analyze_store_data_compatibility(self):
        """分析门店数据适配性"""
        print("\n🏪 分析门店数据适配性...")
        
        # 分析门店代码匹配情况
        enterprise_stores = set(self.dim_store['store \ncode'].astype(str))
        enhanced_stores = set(self.enhanced_coordinates['store_code'].astype(str))
        
        # 计算匹配统计
        matched_stores = enterprise_stores.intersection(enhanced_stores)
        missing_in_enhanced = enterprise_stores - enhanced_stores
        extra_in_enhanced = enhanced_stores - enterprise_stores
        
        store_compatibility = {
            "total_enterprise_stores": len(enterprise_stores),
            "total_enhanced_stores": len(enhanced_stores),
            "matched_stores": len(matched_stores),
            "match_rate": len(matched_stores) / len(enterprise_stores) * 100,
            "missing_in_enhanced": list(missing_in_enhanced),
            "extra_in_enhanced": list(extra_in_enhanced)
        }
        
        self.analysis_results["store_compatibility"] = store_compatibility
        
        print(f"📈 门店匹配率: {store_compatibility['match_rate']:.1f}%")
        print(f"📊 企业门店总数: {store_compatibility['total_enterprise_stores']}")
        print(f"📊 增强坐标门店数: {store_compatibility['total_enhanced_stores']}")
        print(f"✅ 匹配门店数: {store_compatibility['matched_stores']}")
        
        if missing_in_enhanced:
            print(f"⚠️  缺失坐标的门店: {len(missing_in_enhanced)} 个")
            print(f"   门店代码: {missing_in_enhanced[:5]}{'...' if len(missing_in_enhanced) > 5 else ''}")
    
    def analyze_temporal_data_compatibility(self):
        """分析时间数据适配性"""
        print("\n📅 分析时间数据适配性...")
        
        # 分析订单时间范围
        self.order_detail['dt'] = pd.to_datetime(self.order_detail['dt'])
        order_date_range = {
            "start_date": self.order_detail['dt'].min().strftime('%Y-%m-%d'),
            "end_date": self.order_detail['dt'].max().strftime('%Y-%m-%d'),
            "total_days": (self.order_detail['dt'].max() - self.order_detail['dt'].min()).days,
            "unique_dates": self.order_detail['dt'].nunique()
        }
        
        # 分析履约时间数据
        time_columns = ['order_create_time', 'ready_time', 'shipped_time', 'completed_time']
        fulfillment_time_analysis = {}
        
        for col in time_columns:
            if col in self.fulfillment_detail.columns:
                non_null_count = self.fulfillment_detail[col].notna().sum()
                fulfillment_time_analysis[col] = {
                    "non_null_count": int(non_null_count),
                    "completion_rate": non_null_count / len(self.fulfillment_detail) * 100
                }
        
        # 分析与公共假期的适配性
        # 解析公共假期数据结构
        holiday_events = self.public_holidays['vcalendar'][0]['vevent']
        holiday_dates = []
        for event in holiday_events:
            date_str = event['dtstart'][0]  # 格式如 "20250101"
            formatted_date = f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}"
            holiday_dates.append(formatted_date)
        
        holiday_compatibility = {
            "total_holidays": len(holiday_dates),
            "holiday_date_range": f"{min(holiday_dates)} to {max(holiday_dates)}",
            "overlaps_with_order_period": any(
                order_date_range["start_date"] <= date <= order_date_range["end_date"] 
                for date in holiday_dates
            )
        }
        
        temporal_compatibility = {
            "order_date_range": order_date_range,
            "fulfillment_time_analysis": fulfillment_time_analysis,
            "holiday_compatibility": holiday_compatibility
        }
        
        self.analysis_results["temporal_compatibility"] = temporal_compatibility
        
        print(f"📊 订单时间范围: {order_date_range['start_date']} 至 {order_date_range['end_date']}")
        print(f"📊 订单覆盖天数: {order_date_range['total_days']} 天")
        print(f"📊 有效订单日期: {order_date_range['unique_dates']} 天")
        print(f"🎉 公共假期数据: {len(holiday_dates)} 个假期")
        print(f"✅ 时间范围重叠: {'是' if holiday_compatibility['overlaps_with_order_period'] else '否'}")
    
    def analyze_business_metrics_compatibility(self):
        """分析业务指标适配性"""
        print("\n📈 分析业务指标适配性...")
        
        # 分析订单分布
        order_metrics = {
            "total_orders": len(self.order_detail),
            "unique_users": self.order_detail['user_id'].nunique(),
            "unique_stores": self.order_detail['fulfillment_store_code'].nunique(),
            "avg_sku_per_order": self.order_detail['unique_sku_cnt'].mean(),
            "avg_quantity_per_order": self.order_detail['total_quantity_cnt'].mean()
        }
        
        # 分析履约指标
        fulfillment_metrics = self._calculate_fulfillment_metrics()
        
        # 分析门店营业时间与订单时间的适配性
        business_hours_analysis = self._analyze_business_hours()
        
        business_compatibility = {
            "order_metrics": order_metrics,
            "fulfillment_metrics": fulfillment_metrics,
            "business_hours_analysis": business_hours_analysis
        }
        
        self.analysis_results["business_compatibility"] = business_compatibility
        
        print(f"📊 总订单数: {order_metrics['total_orders']:,}")
        print(f"📊 独立用户数: {order_metrics['unique_users']:,}")
        print(f"📊 活跃门店数: {order_metrics['unique_stores']}")
        print(f"📊 平均SKU数/订单: {order_metrics['avg_sku_per_order']:.1f}")
        print(f"📊 平均商品数/订单: {order_metrics['avg_quantity_per_order']:.1f}")
    
    def _calculate_fulfillment_metrics(self):
        """计算履约指标"""
        # 转换时间列
        time_cols = ['order_create_time', 'ready_time', 'shipped_time', 'completed_time']
        for col in time_cols:
            if col in self.fulfillment_detail.columns:
                self.fulfillment_detail[col] = pd.to_datetime(self.fulfillment_detail[col], errors='coerce')
        
        # 计算履约时间
        metrics = {}
        
        # 准备时间 (order_create_time -> ready_time)
        if 'order_create_time' in self.fulfillment_detail.columns and 'ready_time' in self.fulfillment_detail.columns:
            ready_time_diff = (self.fulfillment_detail['ready_time'] - self.fulfillment_detail['order_create_time']).dt.total_seconds() / 60
            metrics['avg_ready_time_minutes'] = ready_time_diff.mean()
        
        # 配送时间 (shipped_time -> completed_time)
        if 'shipped_time' in self.fulfillment_detail.columns and 'completed_time' in self.fulfillment_detail.columns:
            delivery_time_diff = (self.fulfillment_detail['completed_time'] - self.fulfillment_detail['shipped_time']).dt.total_seconds() / 3600
            metrics['avg_delivery_time_hours'] = delivery_time_diff.mean()
        
        # 完成率
        if 'completed_time' in self.fulfillment_detail.columns:
            completion_rate = self.fulfillment_detail['completed_time'].notna().sum() / len(self.fulfillment_detail) * 100
            metrics['completion_rate'] = completion_rate
        
        return metrics
    
    def _analyze_business_hours(self):
        """分析营业时间"""
        # 简化的营业时间分析
        business_hours_data = []
        
        for _, store in self.dim_store.iterrows():
            store_code = store['store \ncode']
            hours1 = f"{store['Business Hrs 1']} {store['Business Hrs 1.1']}"
            
            business_hours_data.append({
                'store_code': store_code,
                'business_hours': hours1,
                'has_extended_hours': store['Business Hrs 2'] != '---'
            })
        
        extended_hours_count = sum(1 for item in business_hours_data if item['has_extended_hours'])
        
        return {
            'total_stores_with_hours': len(business_hours_data),
            'stores_with_extended_hours': extended_hours_count,
            'extended_hours_rate': extended_hours_count / len(business_hours_data) * 100
        }
    
    def analyze_integration_opportunities(self):
        """分析数据集成机会"""
        print("\n🔗 分析数据集成机会...")
        
        integration_opportunities = []
        
        # 1. 门店坐标与订单数据集成
        if hasattr(self, 'enhanced_coordinates') and hasattr(self, 'order_detail'):
            integration_opportunities.append({
                "type": "地理位置增强",
                "description": "将精确的门店坐标集成到订单分析中，支持地理位置相关的业务分析",
                "data_sources": ["enhanced_coordinates", "order_detail"],
                "potential_benefits": [
                    "精确的配送距离计算",
                    "基于地理位置的需求分析",
                    "区域性配送优化",
                    "门店辐射范围分析"
                ],
                "implementation_complexity": "低",
                "business_value": "高"
            })
        
        # 2. 公共假期与订单模式分析
        if hasattr(self, 'public_holidays') and hasattr(self, 'order_detail'):
            integration_opportunities.append({
                "type": "节假日影响分析",
                "description": "结合公共假期数据分析订单模式和履约表现",
                "data_sources": ["public_holidays", "order_detail", "fulfillment_detail"],
                "potential_benefits": [
                    "节假日订单量预测",
                    "节假日配送时间调整",
                    "节假日人员配置优化",
                    "促销活动时机优化"
                ],
                "implementation_complexity": "中",
                "business_value": "高"
            })
        
        # 3. 交通数据与配送优化
        if hasattr(self, 'traffic_files') and hasattr(self, 'fulfillment_detail'):
            integration_opportunities.append({
                "type": "智能配送路径优化",
                "description": "利用实时交通数据优化配送路径和时间预测",
                "data_sources": ["traffic_data", "fulfillment_detail", "enhanced_coordinates"],
                "potential_benefits": [
                    "动态配送路径规划",
                    "准确的配送时间预测",
                    "交通拥堵避免",
                    "配送成本降低"
                ],
                "implementation_complexity": "高",
                "business_value": "极高"
            })
        
        # 4. 营业时间与订单时间匹配
        integration_opportunities.append({
            "type": "营业时间智能匹配",
            "description": "基于门店营业时间优化订单分配和履约时间",
            "data_sources": ["dim_store", "order_detail", "fulfillment_detail"],
            "potential_benefits": [
                "避免非营业时间配送",
                "优化门店工作负载",
                "提高客户满意度",
                "减少配送失败率"
            ],
            "implementation_complexity": "中",
            "business_value": "中"
        })
        
        self.analysis_results["integration_opportunities"] = integration_opportunities
        
        print(f"🎯 发现 {len(integration_opportunities)} 个数据集成机会:")
        for i, opportunity in enumerate(integration_opportunities, 1):
            print(f"   {i}. {opportunity['type']} (价值: {opportunity['business_value']}, 复杂度: {opportunity['implementation_complexity']})")
    
    def generate_compatibility_report(self):
        """生成适配性报告"""
        print("\n📋 生成数据适配性报告...")
        
        report = {
            "report_metadata": {
                "generated_at": datetime.now().isoformat(),
                "analyzer_version": "1.0",
                "data_sources_analyzed": [
                    "dim_store.csv",
                    "case_study_order_detail.csv", 
                    "fulfillment_detail.csv",
                    "dim_date.csv",
                    "store_coordinates_enhanced_v2.csv",
                    "public_holidays_2025.json",
                    "traffic_data"
                ]
            },
            "compatibility_analysis": self.analysis_results,
            "recommendations": self._generate_recommendations()
        }
        
        # 保存报告
        report_path = self.base_path / "docs" / "reports" / "DATA_COMPATIBILITY_ANALYSIS.md"
        self._save_markdown_report(report, report_path)
        
        # 保存JSON格式的详细数据
        json_report_path = self.base_path / "docs" / "reports" / "data_compatibility_analysis.json"
        with open(json_report_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2, default=str)
        
        print(f"✅ 报告已保存:")
        print(f"   📄 Markdown报告: {report_path}")
        print(f"   📊 JSON数据: {json_report_path}")
        
        return report
    
    def _generate_recommendations(self):
        """生成改进建议"""
        recommendations = []
        
        # 基于门店匹配率的建议
        if "store_compatibility" in self.analysis_results:
            match_rate = self.analysis_results["store_compatibility"]["match_rate"]
            if match_rate < 100:
                recommendations.append({
                    "category": "数据完整性",
                    "priority": "高",
                    "issue": f"门店坐标匹配率为 {match_rate:.1f}%，存在缺失数据",
                    "recommendation": "补充缺失门店的精确坐标数据，确保所有活跃门店都有准确的地理位置信息",
                    "expected_impact": "提高配送路径规划准确性，减少配送时间和成本"
                })
        
        # 基于数据集成机会的建议
        if "integration_opportunities" in self.analysis_results:
            high_value_opportunities = [
                opp for opp in self.analysis_results["integration_opportunities"] 
                if opp["business_value"] in ["高", "极高"]
            ]
            
            for opp in high_value_opportunities[:3]:  # 取前3个高价值机会
                recommendations.append({
                    "category": "数据集成",
                    "priority": "高" if opp["business_value"] == "极高" else "中",
                    "issue": f"未充分利用{opp['type']}的潜力",
                    "recommendation": opp["description"],
                    "expected_impact": "、".join(opp["potential_benefits"][:2])
                })
        
        return recommendations
    
    def _save_markdown_report(self, report, file_path):
        """保存Markdown格式的报告"""
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write("# 万宁企业数据与外部数据适配性分析报告\n\n")
            f.write(f"> 生成时间: {report['report_metadata']['generated_at']}\n")
            f.write(f"> 分析版本: {report['report_metadata']['analyzer_version']}\n\n")
            
            f.write("## 📊 数据源概览\n\n")
            for source in report['report_metadata']['data_sources_analyzed']:
                f.write(f"- {source}\n")
            
            # 门店数据适配性
            if "store_compatibility" in report['compatibility_analysis']:
                store_compat = report['compatibility_analysis']['store_compatibility']
                f.write(f"\n## 🏪 门店数据适配性\n\n")
                f.write(f"- **匹配率**: {store_compat['match_rate']:.1f}%\n")
                f.write(f"- **企业门店总数**: {store_compat['total_enterprise_stores']}\n")
                f.write(f"- **增强坐标门店数**: {store_compat['total_enhanced_stores']}\n")
                f.write(f"- **成功匹配**: {store_compat['matched_stores']} 个门店\n")
                
                if store_compat['missing_in_enhanced']:
                    f.write(f"- **缺失坐标门店**: {len(store_compat['missing_in_enhanced'])} 个\n")
            
            # 集成机会
            if "integration_opportunities" in report['compatibility_analysis']:
                f.write(f"\n## 🔗 数据集成机会\n\n")
                for i, opp in enumerate(report['compatibility_analysis']['integration_opportunities'], 1):
                    f.write(f"### {i}. {opp['type']}\n\n")
                    f.write(f"**描述**: {opp['description']}\n\n")
                    f.write(f"**业务价值**: {opp['business_value']} | **实施复杂度**: {opp['implementation_complexity']}\n\n")
                    f.write("**潜在收益**:\n")
                    for benefit in opp['potential_benefits']:
                        f.write(f"- {benefit}\n")
                    f.write("\n")
            
            # 改进建议
            if report['recommendations']:
                f.write(f"## 💡 改进建议\n\n")
                for i, rec in enumerate(report['recommendations'], 1):
                    f.write(f"### {i}. {rec['category']} (优先级: {rec['priority']})\n\n")
                    f.write(f"**问题**: {rec['issue']}\n\n")
                    f.write(f"**建议**: {rec['recommendation']}\n\n")
                    f.write(f"**预期影响**: {rec['expected_impact']}\n\n")

def main():
    """主函数"""
    print("🚀 开始企业数据与外部数据适配性分析...")
    
    analyzer = DataCompatibilityAnalyzer()
    
    try:
        # 加载数据
        analyzer.load_enterprise_data()
        analyzer.load_external_data()
        
        # 执行分析
        analyzer.analyze_store_data_compatibility()
        analyzer.analyze_temporal_data_compatibility()
        analyzer.analyze_business_metrics_compatibility()
        analyzer.analyze_integration_opportunities()
        
        # 生成报告
        report = analyzer.generate_compatibility_report()
        
        print("\n🎉 数据适配性分析完成!")
        print("📋 主要发现:")
        
        if "store_compatibility" in analyzer.analysis_results:
            match_rate = analyzer.analysis_results["store_compatibility"]["match_rate"]
            print(f"   🏪 门店数据匹配率: {match_rate:.1f}%")
        
        if "integration_opportunities" in analyzer.analysis_results:
            opp_count = len(analyzer.analysis_results["integration_opportunities"])
            print(f"   🔗 发现集成机会: {opp_count} 个")
        
        if report["recommendations"]:
            rec_count = len(report["recommendations"])
            print(f"   💡 改进建议: {rec_count} 条")
        
    except Exception as e:
        print(f"❌ 分析过程中出现错误: {str(e)}")
        raise

if __name__ == "__main__":
    main()