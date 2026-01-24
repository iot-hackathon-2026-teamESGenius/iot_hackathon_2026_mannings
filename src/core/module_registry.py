"""
模块注册表 - 实现动态模块加载
"""
import importlib
from typing import Dict, Any
import yaml
from dataclasses import dataclass

@dataclass
class ModuleConfig:
    """模块配置"""
    module_class: str
    config: Dict[str, Any]
    enabled: bool = True
    singleton: bool = True

class ModuleRegistry:
    """模块注册表"""
    
    def __init__(self, config_path: str = "config/modules.yaml"):
        self.config_path = config_path
        self.modules: Dict[str, ModuleConfig] = {}
        self.instances: Dict[str, Any] = {}
        self.load_config()
    
    def load_config(self):
        """加载模块配置"""
        try:
            with open(self.config_path, 'r') as f:
                config_data = yaml.safe_load(f)
                
            for module_name, module_info in config_data.get('modules', {}).items():
                self.modules[module_name] = ModuleConfig(
                    module_class=module_info['class'],
                    config=module_info.get('config', {}),
                    enabled=module_info.get('enabled', True),
                    singleton=module_info.get('singleton', True)
                )
        except FileNotFoundError:
            print(f"Warning: Config file {self.config_path} not found. Using empty registry.")
    
    def get_module(self, module_name: str) -> Any:
        """获取模块实例"""
        if module_name not in self.modules:
            raise KeyError(f"Module {module_name} not found in registry")
        
        config = self.modules[module_name]
        
        if not config.enabled:
            raise ValueError(f"Module {module_name} is disabled")
        
        if config.singleton and module_name in self.instances:
            return self.instances[module_name]
        
        # 动态导入
        module_path, class_name = config.module_class.rsplit('.', 1)
        module = importlib.import_module(module_path)
        module_class = getattr(module, class_name)
        
        instance = module_class(**config.config)
        
        if config.singleton:
            self.instances[module_name] = instance
        
        return instance
    
    def register_module(self, module_name: str, module_class: str, config: Dict[str, Any] = None, enabled: bool = True, singleton: bool = True):
        """注册模块"""
        self.modules[module_name] = ModuleConfig(
            module_class=module_class,
            config=config or {},
            enabled=enabled,
            singleton=singleton
        )
