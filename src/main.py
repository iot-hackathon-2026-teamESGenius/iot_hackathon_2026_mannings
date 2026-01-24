"""
主应用入口
"""
import logging
import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.core.module_registry import ModuleRegistry
from src.core.orchestrator import PipelineOrchestrator

def setup_logging():
    """配置日志"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler('logs/app.log')
        ]
    )

def main():
    """主函数"""
    setup_logging()
    logger = logging.getLogger(__name__)
    
    logger.info("Starting Mannings SLA Optimization System")
    
    try:
        # 1. 初始化模块注册表
        registry = ModuleRegistry("config/modules.yaml")
        
        # 2. 创建协调器
        orchestrator = PipelineOrchestrator(registry)
        
        # 3. 测试模块
        logger.info("Testing modules...")
        test_modules = ['data_fetcher', 'distance_calculator', 'demand_forecaster']
        
        for module_name in test_modules:
            try:
                module = registry.get_module(module_name)
                logger.info(f"✓ {module_name} loaded successfully")
                if hasattr(module, 'get_provider_name'):
                    logger.info(f"  Provider: {module.get_provider_name()}")
            except Exception as e:
                logger.error(f"✗ Failed to load {module_name}: {e}")
        
        # 4. 执行示例流水线
        logger.info("Executing example pipeline...")
        
        pipeline_config = {
            'name': 'example_pipeline',
            'modules': ['data_fetcher', 'demand_forecaster'],
            'date_range': ('2024-01-25', '2024-01-31'),
            'forecast_dates': ['2024-02-01', '2024-02-02', '2024-02-03'],
            'store_ids': ['M001', 'M002', 'M003'],
            'sku_ids': ['SKU001', 'SKU002'],
            'locations': [(22.3193, 114.1694), (22.3287, 114.1883)]
        }
        
        result = orchestrator.execute_pipeline(pipeline_config)
        
        logger.info(f"Pipeline executed successfully in {result['execution_time']:.2f}s")
        logger.info(f"Generated {len(result['results'].get('demand_forecasts', []))} demand forecasts")
        
        # 5. 显示系统状态
        status = orchestrator.get_status()
        logger.info(f"Total pipeline executions: {status['total_executions']}")
        
        print("\n" + "="*50)
        print("System Started Successfully!")
        print("="*50)
        print("\nNext steps:")
        print("1. Run Streamlit dashboard: streamlit run src/visualization/dashboard/app.py")
        print("2. Check logs at: logs/app.log")
        print("3. Modify config/modules.yaml to switch implementations")
        print("\nAvailable modules:")
        for module_name, config in registry.modules.items():
            status = "✓ Enabled" if config.enabled else "✗ Disabled"
            print(f"  - {module_name}: {status}")
        
    except Exception as e:
        logger.error(f"Application failed to start: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
