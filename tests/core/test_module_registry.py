"""
模块注册表测试
"""
import pytest
import yaml
import tempfile
from src.core.module_registry import ModuleRegistry, ModuleConfig

def test_module_registry_initialization():
    """测试模块注册表初始化"""
    # 创建临时配置文件
    config_data = {
        'modules': {
            'test_module': {
                'class': 'src.modules.data.implementations.simulated_data_fetcher.SimulatedDataFetcher',
                'config': {'data_path': '/tmp'},
                'enabled': True,
                'singleton': True
            }
        }
    }
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        yaml.dump(config_data, f)
        config_path = f.name
    
    try:
        registry = ModuleRegistry(config_path)
        assert 'test_module' in registry.modules
        assert isinstance(registry.modules['test_module'], ModuleConfig)
        assert registry.modules['test_module'].enabled == True
    finally:
        import os
        os.unlink(config_path)

def test_module_registry_missing_config():
    """测试缺少配置文件"""
    registry = ModuleRegistry("non_existent.yaml")
    assert registry.modules == {}  # 应该为空而不是报错

def test_get_module():
    """测试获取模块"""
    registry = ModuleRegistry()
    
    # 注册测试模块
    registry.register_module(
        module_name='test_fetcher',
        module_class='src.modules.data.implementations.simulated_data_fetcher.SimulatedDataFetcher',
        config={'data_path': '/tmp'}
    )
    
    # 获取模块
    module = registry.get_module('test_fetcher')
    assert module is not None
    assert hasattr(module, 'fetch_weather_data')

def test_singleton_pattern():
    """测试单例模式"""
    registry = ModuleRegistry()
    
    registry.register_module(
        module_name='singleton_test',
        module_class='src.modules.data.implementations.simulated_data_fetcher.SimulatedDataFetcher',
        config={'data_path': '/tmp'},
        singleton=True
    )
    
    # 两次获取应该是同一个实例
    instance1 = registry.get_module('singleton_test')
    instance2 = registry.get_module('singleton_test')
    
    assert instance1 is instance2

def test_disabled_module():
    """测试禁用模块"""
    registry = ModuleRegistry()
    
    registry.register_module(
        module_name='disabled_module',
        module_class='src.modules.data.implementations.simulated_data_fetcher.SimulatedDataFetcher',
        config={'data_path': '/tmp'},
        enabled=False
    )
    
    # 应该抛出异常
    with pytest.raises(ValueError, match="is disabled"):
        registry.get_module('disabled_module')

if __name__ == "__main__":
    pytest.main([__file__, '-v'])
