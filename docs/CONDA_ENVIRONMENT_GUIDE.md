# Conda环境使用指南

本指南帮助团队成员快速搭建和管理项目开发环境。

---

## 为什么使用Conda？

1. **依赖隔离**：每个项目独立环境，避免包冲突
2. **科学计算友好**：对numpy、pandas等有优化版本
3. **跨平台一致**：在Windows、Mac、Linux上行为一致
4. **非Python依赖**：可以管理非Python包（如C库）

---

## 快速开始

### 方法一：一键安装（推荐）

```bash
# 克隆仓库
git clone https://github.com/iot-hackathon-2026-teamESGenius/iot_hackathon_2026_mannings.git
cd iot_hackathon_2026_mannings

# 运行安装脚本
bash scripts/setup_conda_environment.sh

# 激活环境
conda activate mannings-sla

# 验证环境
python scripts/verify_environment.py
```

### 方法二：手动安装

```bash
# 1. 安装Miniconda（如未安装）
wget https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh
bash Miniconda3-latest-Linux-x86_64.sh -b
~/miniconda3/bin/conda init bash
source ~/.bashrc

# 2. 创建环境
conda env create -f environment.yml

# 3. 激活环境
conda activate mannings-sla

# 4. 验证
python scripts/verify_environment.py
```

---

## 环境要求

| 要求 | 版本 |
|-----|------|
| **Python** | 3.9（严格要求） |
| **Conda** | Miniconda 或 Anaconda |
| **内存** | 最低8GB |

---

## 常用命令

### 环境管理

```bash
# 列出所有环境
conda env list

# 激活环境
conda activate mannings-sla

# 退出环境
conda deactivate

# 更新环境（新增依赖后）
conda env update -f environment.yml --prune

# 删除环境（谨慎使用）
conda remove --name mannings-sla --all
```

### 包管理

```bash
# 查看已安装的包
conda list

# 安装新包（优先使用conda）
conda install package_name

# 如果conda没有，使用pip
pip install package_name

# 导出当前环境
conda env export > environment_export.yml
```

---

## 启动服务

环境激活后，可以启动以下服务：

### REST API服务（前端调用）

```bash
uvicorn src.api.main:app --host 0.0.0.0 --port 8000 --reload
```

**访问地址**：
- API文档：http://localhost:8000/docs
- 健康检查：http://localhost:8000/health

### Streamlit可视化看板（内部调试）

```bash
streamlit run src/visualization/dashboard/app.py
```

**访问地址**：http://localhost:8501

### 路径优化Demo

```bash
python -m src.modules.routing.implementations.demo
```

---

## 验证清单

运行 `python scripts/verify_environment.py` 将检查以下包：

### Stage 1 必需包

| 包名 | 最低版本 | 用途 |
|-----|---------|------|
| pandas | 1.5 | 数据处理 |
| numpy | 1.23 | 数值计算 |
| prophet | 1.1 | 需求预测 |
| scikit-learn | 1.2 | 机器学习 |
| xgboost | 1.7 | 梯度提升 |
| ortools | 9.6 | 路径优化 |
| geopandas | 0.13 | 地理处理 |
| streamlit | 1.22 | 可视化 |
| plotly | 5.14 | 图表 |
| fastapi | 0.100 | REST API |
| uvicorn | 0.22 | ASGI服务器 |

### Stage 2 可选包（智能体系统）

| 包名 | 版本 | 用途 |
|-----|------|------|
| tensorflow | 2.12+ | 深度学习Agent |
| stable-baselines3 | 2.0+ | 强化学习 |
| redis | 4.5+ | 多Agent通信 |

---

## 常见问题

### Q1: 环境创建失败

```bash
# 清理conda缓存
conda clean --all

# 重新创建
conda env create -f environment.yml
```

### Q2: Prophet安装失败

Prophet依赖cmdstanpy，可能需要：

```bash
# 先安装cmdstanpy
conda install -c conda-forge cmdstanpy
conda install -c conda-forge prophet
```

### Q3: 环境已存在

脚本会提示选择：
- `[1]` 更新环境（推荐）
- `[2]` 重建环境
- `[3]` 取消

### Q4: 如何切换不同环境

```bash
# 退出当前环境
conda deactivate

# 切换到其他环境
conda activate other_env
```

---

## 团队协作

### 新增依赖后

1. 更新 `environment.yml`
2. 更新 `requirements.txt`
3. 通知团队运行：

```bash
conda env update -f environment.yml --prune
```

### 提交前检查

```bash
# 确保环境正常
python scripts/verify_environment.py

# 运行测试
pytest tests/ -v
```

---

## 参考链接

- [Miniconda下载](https://docs.conda.io/en/latest/miniconda.html)
- [Conda官方文档](https://docs.conda.io/en/latest/)
- [项目README](../README.md)
