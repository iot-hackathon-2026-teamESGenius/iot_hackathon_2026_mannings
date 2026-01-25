#!/usr/bin/env python
"""
环境验证脚本 - Mannings SLA优化项目
检查所有必需的包是否正确安装
更新: 2026-01-25
"""

import sys
import subprocess
from importlib import import_module, metadata

# 必须的包和最小版本
REQUIRED_PACKAGES = {
    # 数据处理
    'pandas': '1.5',
    'numpy': '1.23',
    # 预测模型
    'prophet': '1.1',
    'sklearn': '1.2',  # scikit-learn的导入名是sklearn
    'xgboost': '1.7',
    # 优化求解
    'ortools': '9.6',
    # 地理处理
    'geopandas': '0.13',
    # 可视化
    'streamlit': '1.22',
    'plotly': '5.14',
    # REST API (Stage 1新增)
    'fastapi': '0.100',
    'uvicorn': '0.22',
}

# 可选的包 (Stage 2 智能体系统)
OPTIONAL_PACKAGES = {
    'tensorflow': '2.12',      # 深度学习Agent
    'torch': '2.0',            # 深度学习备选
    'stable_baselines3': '2.0', # 强化学习
    'redis': '4.5',            # 多Agent通信
    'mlflow': '2.3',           # 模型管理
}

def check_package(package, min_version=None):
    """检查包是否安装并满足版本要求"""
    try:
        # 尝试导入包
        mod = import_module(package)
        
        # 获取版本
        try:
            version = metadata.version(package)
        except:
            # 备选方法
            if hasattr(mod, '__version__'):
                version = mod.__version__
            else:
                version = "未知版本"
        
        # 检查版本
        if min_version:
            from packaging import version as packaging_version
            if packaging_version.parse(version) < packaging_version.parse(min_version):
                return False, f"{package} ({version}) < 要求版本 {min_version}"
        
        return True, f"{package} ({version})"
    
    except ImportError:
        return False, f"{package} 未安装"
    except Exception as e:
        return False, f"{package} 检查错误: {str(e)}"

def check_python_version():
    """检查Python版本"""
    version = sys.version_info
    return f"{version.major}.{version.minor}.{version.micro}"

def check_conda_env():
    """检查是否在Conda环境中"""
    try:
        result = subprocess.run(
            ['conda', 'info', '--json'],
            capture_output=True,
            text=True,
            check=False
        )
        if result.returncode == 0:
            import json
            info = json.loads(result.stdout)
            return info.get('active_prefix_name', '未知环境')
    except:
        pass
    
    # 备选方法
    import os
    return os.environ.get('CONDA_DEFAULT_ENV', '非Conda环境')

def main():
    """主验证函数"""
    print("🔍 验证项目环境...")
    print("=" * 50)
    
    # 检查Python版本
    python_version = check_python_version()
    print(f"🐍 Python版本: {python_version}")
    
    # 检查Conda环境
    env_name = check_conda_env()
    print(f"🌿 Conda环境: {env_name}")
    
    print("\n📦 检查必需包:")
    print("-" * 30)
    
    all_ok = True
    for package, min_version in REQUIRED_PACKAGES.items():
        ok, message = check_package(package, min_version)
        status = "✅" if ok else "❌"
        print(f"  {status} {message}")
        if not ok:
            all_ok = False
    
    print("\n📦 检查可选包:")
    print("-" * 30)
    
    for package, min_version in OPTIONAL_PACKAGES.items():
        ok, message = check_package(package, min_version)
        status = "✅" if ok else "⚠️ "
        print(f"  {status} {message}")
    
    print("\n" + "=" * 50)
    if all_ok:
        print("🎉 环境验证通过！所有必需包已正确安装。")
        return 0
    else:
        print("❌ 环境验证失败！请安装缺失的包。")
        print(f"\n运行以下命令修复：")
        print(f"  conda env update -f environment.yml")
        return 1

if __name__ == "__main__":
    sys.exit(main())