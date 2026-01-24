#!/usr/bin/env python3
"""
模块管理工具
"""
import argparse
import yaml
from pathlib import Path

def list_modules(config_path: str = "config/modules.yaml"):
    """列出所有模块"""
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)
    
    modules = config.get('modules', {})
    
    print("📦 Available Modules:")
    print("-" * 60)
    print(f"{'Module Name':<20} {'Status':<10} {'Class':<30}")
    print("-" * 60)
    
    for name, info in modules.items():
        status = "✅ Enabled" if info.get('enabled', True) else "❌ Disabled"
        class_name = info.get('class', 'N/A')
        print(f"{name:<20} {status:<10} {class_name:<30}")
    
    return modules

def enable_module(module_name: str, config_path: str = "config/modules.yaml"):
    """启用模块"""
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)
    
    if module_name not in config.get('modules', {}):
        print(f"❌ Module '{module_name}' not found")
        return False
    
    config['modules'][module_name]['enabled'] = True
    
    with open(config_path, 'w') as f:
        yaml.dump(config, f, default_flow_style=False)
    
    print(f"✅ Module '{module_name}' enabled")
    return True

def disable_module(module_name: str, config_path: str = "config/modules.yaml"):
    """禁用模块"""
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)
    
    if module_name not in config.get('modules', {}):
        print(f"❌ Module '{module_name}' not found")
        return False
    
    config['modules'][module_name]['enabled'] = False
    
    with open(config_path, 'w') as f:
        yaml.dump(config, f, default_flow_style=False)
    
    print(f"✅ Module '{module_name}' disabled")
    return True

def main():
    parser = argparse.ArgumentParser(description="Module Management Tool")
    subparsers = parser.add_subparsers(dest='command', help='Commands')
    
    # List command
    subparsers.add_parser('list', help='List all modules')
    
    # Enable command
    enable_parser = subparsers.add_parser('enable', help='Enable a module')
    enable_parser.add_argument('module_name', help='Name of the module to enable')
    
    # Disable command
    disable_parser = subparsers.add_parser('disable', help='Disable a module')
    disable_parser.add_argument('module_name', help='Name of the module to disable')
    
    args = parser.parse_args()
    
    if args.command == 'list':
        list_modules()
    elif args.command == 'enable':
        enable_module(args.module_name)
    elif args.command == 'disable':
        disable_module(args.module_name)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
