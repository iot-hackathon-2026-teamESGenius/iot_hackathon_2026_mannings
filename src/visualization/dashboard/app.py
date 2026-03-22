"""
Streamlit主应用 - Mannings SLA Optimization Dashboard
集成Pipeline数据，提供KPI、预测、路径优化、SLA分析可视化

Author: 王晔宸 (Team Lead)
Date: 2026-02-12
"""
import sys
from pathlib import Path
from datetime import date, datetime, timedelta
import json

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

import streamlit as st
import pandas as pd
import numpy as np

# 尝试导入可视化库
try:
    import plotly.express as px
    import plotly.graph_objects as go
    PLOTLY_AVAILABLE = True
except ImportError:
    PLOTLY_AVAILABLE = False

try:
    import folium
    from streamlit_folium import st_folium
    FOLIUM_AVAILABLE = True
except ImportError:
    FOLIUM_AVAILABLE = False

# 导入Pipeline
try:
    from src.core.pipeline_orchestrator import PipelineOrchestrator, PipelineConfig, ModuleFactory
    PIPELINE_AVAILABLE = True
except ImportError:
    PIPELINE_AVAILABLE = False


def init_session_state():
    """初始化Session State"""
    if 'pipeline_result' not in st.session_state:
        st.session_state.pipeline_result = None
    if 'last_run_time' not in st.session_state:
        st.session_state.last_run_time = None


def run_pipeline(target_date: date):
    """运行优化Pipeline"""
    if not PIPELINE_AVAILABLE:
        st.error("Pipeline模块不可用")
        return None
    
    with st.spinner("正在运行优化Pipeline..."):
        try:
            # 创建模块
            data_mod = ModuleFactory.create_data_module()
            forecast_mod = ModuleFactory.create_forecast_module()
            routing_mod = ModuleFactory.create_routing_module()
            sla_mod = ModuleFactory.create_sla_module()
            
            # 配置Pipeline
            config = PipelineConfig(
                num_vehicles=10,
                vehicle_capacity=100,
                sla_target_hours=4.0
            )
            
            # 创建Orchestrator
            orchestrator = PipelineOrchestrator(config)
            orchestrator.set_data_module(data_mod)
            orchestrator.set_forecast_module(forecast_mod)
            orchestrator.set_routing_module(routing_mod)
            orchestrator.set_sla_module(sla_mod)
            
            # 运行Pipeline
            result = orchestrator.run_pipeline(target_date)
            summary = orchestrator.get_pipeline_summary(result)
            
            st.session_state.pipeline_result = result
            st.session_state.pipeline_summary = summary
            st.session_state.last_run_time = datetime.now()
            
            return result
            
        except Exception as e:
            st.error(f"Pipeline运行失败: {e}")
            return None


def show_kpi_dashboard():
    """显示KPI仪表板"""
    st.header("📊 KPI Dashboard")
    
    result = st.session_state.get('pipeline_result')
    summary = st.session_state.get('pipeline_summary', {})
    
    if not result or not result.success:
        # 显示示例数据
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("SLA达成率", "95.2%", "+2.1%")
        with col2:
            st.metric("平均履约时间", "3.5h", "-0.3h")
        with col3:
            st.metric("路径效率", "87%", "+5%")
        with col4:
            st.metric("预测准确率", "92%", "+1.2%")
        
        st.info("💡 运行Pipeline获取实时数据")
        return
    
    # 显示实时KPI
    stats = summary.get('stats', {})
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        sla_prob = stats.get('avg_sla_probability', 0) * 100
        st.metric("SLA达成概率", f"{sla_prob:.1f}%", 
                  f"{sla_prob - 95:.1f}%" if sla_prob > 0 else None)
    
    with col2:
        total_orders = stats.get('total_predicted_orders', 0)
        st.metric("预测订单数", f"{total_orders:.0f}")
    
    with col3:
        total_distance = stats.get('total_distance_km', 0)
        st.metric("总配送距离", f"{total_distance:.1f} km")
    
    with col4:
        exec_time = summary.get('execution_time_sec', 0)
        st.metric("Pipeline耗时", f"{exec_time:.2f}s")
    
    # 显示更多详情
    st.markdown("---")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📦 预测统计")
        st.write(f"- 门店数量: {stats.get('num_forecasts', 0)}")
        st.write(f"- 场景数量: {stats.get('num_scenarios', 0)}")
        st.write(f"- 路线数量: {stats.get('num_routes', 0)}")
    
    with col2:
        st.subheader("⏱️ 执行信息")
        st.write(f"- 目标日期: {summary.get('target_date', 'N/A')}")
        st.write(f"- 执行状态: {'✅ 成功' if summary.get('success') else '❌ 失败'}")
        last_run = st.session_state.get('last_run_time')
        if last_run:
            st.write(f"- 上次运行: {last_run.strftime('%H:%M:%S')}")


def show_demand_forecast():
    """显示需求预测页面"""
    st.header("📈 需求预测")
    
    result = st.session_state.get('pipeline_result')
    
    if not result or not result.forecasts:
        st.info("暂无预测数据，请先运行Pipeline")
        
        # 显示示例图表
        if PLOTLY_AVAILABLE:
            dates = pd.date_range(start=date.today(), periods=7)
            example_data = pd.DataFrame({
                'date': dates,
                'p50': [100 + i*5 + np.random.normal(0, 10) for i in range(7)],
                'p10': [80 + i*4 for i in range(7)],
                'p90': [120 + i*6 for i in range(7)]
            })
            
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=example_data['date'], y=example_data['p90'],
                                    fill=None, mode='lines', name='P90'))
            fig.add_trace(go.Scatter(x=example_data['date'], y=example_data['p10'],
                                    fill='tonexty', mode='lines', name='P10-P90区间'))
            fig.add_trace(go.Scatter(x=example_data['date'], y=example_data['p50'],
                                    mode='lines+markers', name='P50 (中位数)', line=dict(width=3)))
            fig.update_layout(title="示例：需求预测与置信区间",
                            xaxis_title="日期", yaxis_title="预测需求")
            st.plotly_chart(fig, use_container_width=True)
        return
    
    # 显示实际预测数据
    forecasts = result.forecasts
    
    # 转换为DataFrame
    forecast_data = []
    for f in forecasts[:50]:  # 只显示前50个
        forecast_data.append({
            'store_code': f.store_code,
            'date': f.forecast_date,
            'predicted_orders': f.predicted_orders,
            'p10': f.p10,
            'p50': f.p50,
            'p90': f.p90
        })
    
    df = pd.DataFrame(forecast_data)
    
    # 门店选择器
    selected_stores = st.multiselect(
        "选择门店",
        options=df['store_code'].unique()[:20],
        default=df['store_code'].unique()[:5]
    )
    
    if selected_stores:
        filtered_df = df[df['store_code'].isin(selected_stores)]
        
        if PLOTLY_AVAILABLE:
            fig = px.bar(filtered_df, x='store_code', y='predicted_orders',
                        title="门店预测订单量",
                        labels={'store_code': '门店代码', 'predicted_orders': '预测订单数'})
            st.plotly_chart(fig, use_container_width=True)
    
    # 显示预测表格
    st.subheader("预测详情")
    st.dataframe(df.head(20), use_container_width=True)


def show_route_optimization():
    """显示路径优化页面"""
    st.header("🗺️ 路径优化")
    
    result = st.session_state.get('pipeline_result')
    
    if result and result.robust_plan:
        plan = result.robust_plan
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("总距离", f"{plan.total_distance_km:.1f} km")
        with col2:
            st.metric("总时长", f"{plan.total_duration_min:.0f} min")
        with col3:
            st.metric("停靠点数", f"{plan.num_stops}")
        
        # 显示路线详情
        st.subheader("路线停靠点")
        stops_data = []
        for stop in plan.stops:
            stops_data.append({
                '序号': stop.sequence,
                '门店代码': stop.store_code,
                '纬度': stop.latitude,
                '经度': stop.longitude,
                '到达时间': stop.arrival_time.strftime('%H:%M') if stop.arrival_time else 'N/A',
                '需求量': stop.demand or 0
            })
        
        st.dataframe(pd.DataFrame(stops_data), use_container_width=True)
        
        # 显示地图
        if FOLIUM_AVAILABLE and plan.stops:
            st.subheader("路线地图")
            
            # 计算中心点
            lats = [s.latitude for s in plan.stops if s.latitude]
            lngs = [s.longitude for s in plan.stops if s.longitude]
            
            if lats and lngs:
                center_lat = sum(lats) / len(lats)
                center_lng = sum(lngs) / len(lngs)
                
                m = folium.Map(location=[center_lat, center_lng], zoom_start=12)
                
                # 添加标记和路线
                coords = []
                for stop in plan.stops:
                    if stop.latitude and stop.longitude:
                        coords.append([stop.latitude, stop.longitude])
                        
                        # 配送中心用特殊标记
                        if stop.sequence == 0:
                            folium.Marker(
                                [stop.latitude, stop.longitude],
                                popup="配送中心",
                                icon=folium.Icon(color='red', icon='home')
                            ).add_to(m)
                        else:
                            folium.Marker(
                                [stop.latitude, stop.longitude],
                                popup=f"门店 {stop.store_code}",
                                icon=folium.Icon(color='blue', icon='store', prefix='fa')
                            ).add_to(m)
                
                # 绘制路线
                if len(coords) >= 2:
                    folium.PolyLine(coords, color='blue', weight=3, opacity=0.8).add_to(m)
                
                st_folium(m, width=700, height=450)
    else:
        st.info("暂无路径数据，请先运行Pipeline")
        
        # 显示示例地图
        if FOLIUM_AVAILABLE:
            m = folium.Map(location=[22.3, 114.17], zoom_start=11)
            st_folium(m, width=700, height=400)


def show_sla_analysis():
    """显示SLA分析页面"""
    st.header("⏰ SLA分析")
    
    result = st.session_state.get('pipeline_result')
    
    if result and result.sla_predictions:
        predictions = result.sla_predictions
        
        # SLA统计
        probs = [p.sla_achievement_probability for p in predictions]
        avg_prob = sum(probs) / len(probs) if probs else 0
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("平均SLA概率", f"{avg_prob*100:.1f}%")
        with col2:
            high_risk = sum(1 for p in probs if p < 0.8)
            st.metric("高风险门店", f"{high_risk}")
        with col3:
            low_risk = sum(1 for p in probs if p >= 0.95)
            st.metric("低风险门店", f"{low_risk}")
        
        # SLA分布图
        if PLOTLY_AVAILABLE and probs:
            fig = go.Figure(data=[go.Histogram(x=[p*100 for p in probs], nbinsx=20)])
            fig.update_layout(title="SLA达成概率分布",
                            xaxis_title="SLA概率 (%)",
                            yaxis_title="门店数量")
            st.plotly_chart(fig, use_container_width=True)
        
        # 风险门店列表
        st.subheader("⚠️ 风险门店")
        risk_data = []
        for pred in predictions:
            if pred.sla_achievement_probability < 0.9:
                risk_data.append({
                    '门店代码': pred.store_code,
                    'SLA概率': f"{pred.sla_achievement_probability*100:.1f}%",
                    '风险因素': ', '.join(pred.risk_factors) if pred.risk_factors else 'N/A',
                    '预计就绪': pred.predicted_ready_time.strftime('%H:%M') if pred.predicted_ready_time else 'N/A'
                })
        
        if risk_data:
            st.dataframe(pd.DataFrame(risk_data), use_container_width=True)
        else:
            st.success("所有门店SLA风险较低！")
    else:
        st.info("暂无SLA数据，请先运行Pipeline")
        
        # 示例数据
        if PLOTLY_AVAILABLE:
            example_probs = [np.random.beta(8, 2) * 100 for _ in range(50)]
            fig = go.Figure(data=[go.Histogram(x=example_probs, nbinsx=20)])
            fig.update_layout(title="示例：SLA达成概率分布",
                            xaxis_title="SLA概率 (%)",
                            yaxis_title="门店数量")
            st.plotly_chart(fig, use_container_width=True)


def show_system_status():
    """显示系统状态页面"""
    st.header("🔧 系统状态")
    
    # 模块状态
    st.subheader("模块状态")
    
    modules = [
        ("Pipeline核心", PIPELINE_AVAILABLE, "src.core.pipeline_orchestrator"),
        ("Plotly可视化", PLOTLY_AVAILABLE, "plotly"),
        ("Folium地图", FOLIUM_AVAILABLE, "folium, streamlit_folium"),
    ]
    
    for name, available, package in modules:
        status = "✅ 可用" if available else "❌ 不可用"
        st.write(f"- **{name}**: {status} (`{package}`)")
    
    # Session状态
    st.subheader("会话状态")
    last_run = st.session_state.get('last_run_time')
    if last_run:
        st.write(f"- 上次运行: {last_run.strftime('%Y-%m-%d %H:%M:%S')}")
    
    result = st.session_state.get('pipeline_result')
    if result:
        st.write(f"- Pipeline结果: {'成功' if result.success else '失败'}")
        st.write(f"- 预测数量: {len(result.forecasts)}")
        st.write(f"- 场景数量: {len(result.scenarios)}")
    
    # 清除缓存
    if st.button("清除缓存"):
        st.session_state.clear()
        st.rerun()


def main():
    """主函数"""
    # 页面配置
    st.set_page_config(
        page_title="Mannings SLA Optimization",
        page_icon="🏪",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    # 初始化Session State
    init_session_state()
    
    # 侧边栏
    with st.sidebar:
        st.title("🏪 Mannings SLA")
        st.markdown("### 门店自提SLA优化系统")
        st.markdown("---")
        
        # 导航
        page = st.radio(
            "导航",
            ["📊 KPI Dashboard", "📈 需求预测", "🗺️ 路径优化", "⏰ SLA分析", "🔧 系统状态"]
        )
        
        st.markdown("---")
        
        # 运行控制
        st.subheader("🚀 运行Pipeline")
        target_date = st.date_input("目标日期", value=date.today())
        
        if st.button("运行优化", type="primary"):
            run_pipeline(target_date)
            st.success("Pipeline运行完成！")
        
        # 显示上次运行时间
        last_run = st.session_state.get('last_run_time')
        if last_run:
            st.caption(f"上次运行: {last_run.strftime('%H:%M:%S')}")
    
    # 主内容
    if "KPI" in page:
        show_kpi_dashboard()
    elif "需求预测" in page:
        show_demand_forecast()
    elif "路径优化" in page:
        show_route_optimization()
    elif "SLA分析" in page:
        show_sla_analysis()
    elif "系统状态" in page:
        show_system_status()


if __name__ == "__main__":
    main()
