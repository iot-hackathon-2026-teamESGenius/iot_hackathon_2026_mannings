# IOT Hackathon 2026 - Mannings Store Pickup SLA Optimization

## 🎯 项目概述
为DFI Retail Group - Mannings开发端到端的门店取货SLA优化系统，通过AI/ML和优化算法提升顾客取货体验并控制总成本。

## 🚀 快速开始

### 环境设置
```bash
# 1. 克隆仓库
git clone https://github.com/[组织名]/iot-hackathon-2026-mannings.git
cd iot-hackathon-2026-mannings

# 2. 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 3. 安装依赖
pip install -r requirements.txt

# 4. 运行Demo
streamlit run src/visualization/dashboard/app.py

## 🌿 Conda环境管理

本项目使用Conda进行环境管理，确保依赖一致性和隔离性。

### 环境设置

1. **安装Miniconda**（如未安装）：
   ```bash
   # 下载地址：https://docs.conda.io/en/latest/miniconda.html
   # 方法1：使用脚本（推荐）
bash scripts/setup_conda_environment.sh

# 方法2：手动创建
conda env create -f environment.yml
conda activate mannings-sla

# 5. 验证环境
python scripts/verify_environment.py
