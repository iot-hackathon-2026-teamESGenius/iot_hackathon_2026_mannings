"""
流水线协调器
"""
import logging
from datetime import datetime
from typing import Dict, Any
from .module_registry import ModuleRegistry

logger = logging.getLogger(__name__)

class PipelineOrchestrator:
    """流水线协调器"""
    
    def __init__(self, registry: ModuleRegistry):
        self.registry = registry
        self.pipeline_history = []
    
    def execute_pipeline(self, pipeline_config: Dict[str, Any]) -> Dict[str, Any]:
        """执行流水线"""
        logger.info(f"Starting pipeline: {pipeline_config.get('name', 'unnamed')}")
        
        start_time = datetime.now()
        
        try:
            # 获取模块实例
            modules = {}
            for module_name in pipeline_config.get('modules', []):
                modules[module_name] = self.registry.get_module(module_name)
            
            # 执行流水线步骤
            results = {}
            
            # 数据获取
            if 'data_fetcher' in modules:
                logger.info("Fetching data...")
                data_fetcher = modules['data_fetcher']
                results['weather_data'] = data_fetcher.fetch_weather_data(
                    pipeline_config.get('date_range', ('2024-01-01', '2024-01-31')),
                    pipeline_config.get('locations', [])
                )
            
            # 需求预测
            if 'demand_forecaster' in modules and 'data_fetcher' in modules:
                logger.info("Forecasting demand...")
                demand_forecaster = modules['demand_forecaster']
                results['demand_forecasts'] = demand_forecaster.predict(
                    future_dates=pipeline_config.get('forecast_dates', []),
                    store_ids=pipeline_config.get('store_ids', []),
                    sku_ids=pipeline_config.get('sku_ids', []),
                    external_features={'weather': results.get('weather_data')}
                )
            
            # 路径优化
            if 'routing_optimizer' in modules and 'distance_calculator' in modules:
                logger.info("Optimizing routes...")
                routing_optimizer = modules['routing_optimizer']
                distance_calculator = modules['distance_calculator']
                
                # 这里需要更多参数，简化示例
                # results['route_plans'] = routing_optimizer.optimize_routes(...)
            
            execution_time = (datetime.now() - start_time).total_seconds()
            
            result = {
                'pipeline_name': pipeline_config.get('name'),
                'execution_time': execution_time,
                'timestamp': datetime.now().isoformat(),
                'results': results
            }
            
            self.pipeline_history.append(result)
            logger.info(f"Pipeline completed in {execution_time:.2f}s")
            
            return result
            
        except Exception as e:
            logger.error(f"Pipeline execution failed: {str(e)}")
            raise
    
    def get_status(self) -> Dict[str, Any]:
        """获取状态"""
        return {
            'total_executions': len(self.pipeline_history),
            'last_execution': self.pipeline_history[-1] if self.pipeline_history else None
        }
