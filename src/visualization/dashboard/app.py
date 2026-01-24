"""
Streamlit主应用 - 适配新架构
"""
import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

import streamlit as st
from src.core.module_registry import ModuleRegistry
from src.modules.visualization.implementations.streamlit_dashboard import StreamlitDashboard

def main():
    """主函数"""
    # 初始化模块注册表
    registry = ModuleRegistry("config/modules.yaml")
    
    # 获取可视化模块
    try:
        viz_module = registry.get_module("visualization")
    except Exception as e:
        st.error(f"Failed to load visualization module: {e}")
        
        # 创建默认仪表板
        viz_module = StreamlitDashboard()
    
    # 创建数据源（示例）
    data_sources = {
        'weather_data': {
            'status': 'loaded',
            'sample_count': 100
        },
        'demand_forecasts': {
            'status': 'generated',
            'forecast_count': 15
        },
        'route_plans': {
            'status': 'optimized',
            'route_count': 3
        }
    }
    
    # 创建仪表板
    viz_module.create_dashboard(data_sources)

if __name__ == "__main__":
    main()
