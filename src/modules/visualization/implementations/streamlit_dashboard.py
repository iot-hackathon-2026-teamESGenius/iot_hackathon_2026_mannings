"""
Streamlit仪表板实现
"""
import streamlit as st
import pandas as pd
import plotly.express as px
from typing import Dict, Any, List
from ...interfaces import IVisualization
from src.core.interfaces import RoutePlan

class StreamlitDashboard(IVisualization):
    """Streamlit仪表板"""
    
    def __init__(self, theme: str = "light", page_title: str = "Mannings SLA Optimization"):
        self.theme = theme
        self.page_title = page_title
    
    def create_dashboard(self, data_sources: Dict[str, Any], layout_config: Dict[str, Any] = None) -> Any:
        """创建仪表板"""
        # 设置页面配置
        st.set_page_config(
            page_title=self.page_title,
            page_icon="🏪",
            layout="wide",
            initial_sidebar_state="expanded"
        )
        
        # 设置主题
        if self.theme == "dark":
            st.markdown("""
            <style>
            .stApp {
                background-color: #0E1117;
                color: #FAFAFA;
            }
            </style>
            """, unsafe_allow_html=True)
        
        # 创建侧边栏
        with st.sidebar:
            st.title("🏪 Mannings SLA Optimizer")
            st.markdown("---")
            
            # 导航
            page = st.radio(
                "Navigation",
                ["Overview", "Demand Forecast", "Inventory", "Route Optimization", "SLA Analysis"]
            )
        
        # 主内容区
        st.title(self.page_title)
        
        # 根据选择的页面显示内容
        if page == "Overview":
            self._show_overview(data_sources)
        elif page == "Demand Forecast":
            self._show_forecast(data_sources)
        elif page == "Route Optimization":
            self._show_routes(data_sources)
        
        return st
    
    def plot_routes(self, route_plans: List[RoutePlan], store_locations: Dict[str, tuple], 
                   map_provider: str = "openstreetmap") -> Any:
        """绘制路线图"""
        import folium
        from streamlit_folium import st_folium
        
        # 创建地图
        center_lat = sum(loc[0] for loc in store_locations.values()) / len(store_locations)
        center_lng = sum(loc[1] for loc in store_locations.values()) / len(store_locations)
        
        m = folium.Map(location=[center_lat, center_lng], zoom_start=12)
        
        # 添加门店标记
        for store_id, (lat, lng) in store_locations.items():
            folium.Marker(
                [lat, lng],
                popup=f"Store: {store_id}",
                tooltip=f"Click for details",
                icon=folium.Icon(color="blue", icon="store", prefix="fa")
            ).add_to(m)
        
        # 添加路线
        colors = ['red', 'green', 'purple', 'orange', 'darkblue']
        for i, route in enumerate(route_plans):
            if len(route.store_sequence) >= 2:
                route_coords = []
                for store_id in route.store_sequence:
                    if store_id in store_locations:
                        route_coords.append(store_locations[store_id])
                
                if len(route_coords) >= 2:
                    folium.PolyLine(
                        route_coords,
                        color=colors[i % len(colors)],
                        weight=3,
                        opacity=0.8,
                        popup=f"Route {route.route_id}"
                    ).add_to(m)
        
        return m
    
    def _show_overview(self, data_sources: Dict[str, Any]):
        """显示概览页面"""
        st.header("📊 System Overview")
        
        # KPI指标
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("SLA Achievement", "95%", "+2.3%")
        with col2:
            st.metric("Avg Delivery Time", "45 min", "-5 min")
        with col3:
            st.metric("Cost Efficiency", "88%", "+3.1%")
        with col4:
            st.metric("Forecast Accuracy", "92%", "+1.8%")
        
        st.markdown("---")
        
        # 系统架构图
        st.subheader("System Architecture")
        st.image("https://via.placeholder.com/800x400?text=System+Architecture+Diagram", 
                caption="Modular Architecture Design")
    
    def _show_forecast(self, data_sources: Dict[str, Any]):
        """显示预测页面"""
        st.header("📈 Demand Forecasting")
        
        # 创建示例数据
        dates = pd.date_range(start="2024-01-01", end="2024-01-31", freq='D')
        forecast_data = pd.DataFrame({
            'date': dates,
            'forecast': [100 + i*2 + (i%7)*10 for i in range(len(dates))],
            'actual': [95 + i*2 + (i%7)*8 + (i%3)*5 for i in range(len(dates))]
        })
        
        # 绘制图表
        fig = px.line(forecast_data, x='date', y=['forecast', 'actual'],
                     title="Demand Forecast vs Actual",
                     labels={'value': 'Demand', 'variable': 'Type'})
        
        st.plotly_chart(fig, use_container_width=True)
    
    def _show_routes(self, data_sources: Dict[str, Any]):
        """显示路线优化页面"""
        st.header("🗺️ Route Optimization")
        
        # 示例路线数据
        route_plans = [
            RoutePlan(
                route_id="R001",
                vehicle_id="V001",
                store_sequence=["M001", "M003", "M005"],
                arrival_times=["09:30", "10:15", "11:00"],
                departure_times=["09:45", "10:30", "11:15"],
                distances_km=[5.2, 3.8, 4.5],
                total_distance_km=13.5,
                total_duration_min=120,
                total_cost=45.0,
                sla_risk_score=0.1
            ),
            RoutePlan(
                route_id="R002",
                vehicle_id="V002",
                store_sequence=["M002", "M004"],
                arrival_times=["09:45", "10:30"],
                departure_times=["10:00", "10:45"],
                distances_km=[7.1, 3.2],
                total_distance_km=10.3,
                total_duration_min=90,
                total_cost=32.5,
                sla_risk_score=0.05
            )
        ]
        
        # 门店位置（示例）
        store_locations = {
            "M001": (22.3193, 114.1694),
            "M002": (22.3287, 114.1883),
            "M003": (22.3372, 114.1521),
            "M004": (22.3105, 114.1829),
            "M005": (22.3038, 114.1587)
        }
        
        # 显示路线详情
        for route in route_plans:
            with st.expander(f"Route {route.route_id} (Vehicle: {route.vehicle_id})"):
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Total Distance", f"{route.total_distance_km} km")
                with col2:
                    st.metric("Total Duration", f"{route.total_duration_min} min")
                with col3:
                    st.metric("SLA Risk", f"{route.sla_risk_score*100:.1f}%")
                
                # 路线表格
                route_df = pd.DataFrame({
                    'Store': route.store_sequence,
                    'Arrival': route.arrival_times,
                    'Departure': route.departure_times,
                    'Distance (km)': route.distances_km
                })
                st.dataframe(route_df, use_container_width=True)
        
        # 显示地图
        st.subheader("Route Map")
        map_obj = self.plot_routes(route_plans, store_locations)
        st_folium(map_obj, width=800, height=500)
