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

> **⚠️ 重要提示**：经过实战验证，**推荐使用方法一（手动pip安装）**，避免conda依赖求解过慢和Python版本降级问题。

### 方法一：手动pip安装（推荐✅）

这是最快速且稳定的安装方式，避免了conda的已知问题。

```bash
# 1. 克隆仓库
git clone https://github.com/iot-hackathon-2026-teamESGenius/iot_hackathon_2026_mannings.git
cd iot_hackathon_2026_mannings

# 2. 配置清华conda镜像源（加速）
cp .condarc ~/.condarc
conda clean --all -y

# 3. 创建纯净Python 3.9环境
conda create -n mannings-sla python=3.9 pip -y

# 4. 激活环境
conda activate mannings-sla

# 5. 使用pip安装核心包（第一批）
pip install -i https://pypi.tuna.tsinghua.edu.cn/simple \
  pandas numpy scipy scikit-learn xgboost \
  streamlit plotly pyyaml python-dotenv

# 6. 安装专业包（第二批 - 使用官方源）
pip install prophet ortools geopandas \
  fastapi uvicorn python-multipart \
  folium streamlit-folium

# 7. 验证环境
python scripts/verify_environment.py
```

**安装时间**：约5-10分钟（清华源约3-5分钟）

---

### 方法二：environment.yml安装（不推荐⚠️）

**已知问题**：
- ❌ **依赖求解慢**：conda需要5-30分钟求解依赖关系
- ❌ **Python版本降级风险**：可能从CPython 3.9.23降级到PyPy 3.9.18，导致streamlit等包无法安装
- ❌ **卡死风险**：在`Solving environment`或`Collecting package metadata`阶段长时间无响应
- ❌ **包冲突**：多通道(conda-forge/defaults)可能产生不兼容包组合

如果仍需使用此方法：

```bash
# 1. 配置镜像源
cp .condarc ~/.condarc

# 2. 创建环境（可能需要30分钟）
conda env create -f environment.yml

# 3. 激活环境
conda activate mannings-sla

# 4. 验证
python scripts/verify_environment.py
```

⚠️ **如遇到卡住**：按`Ctrl+C`终止，改用方法一

---

### 方法三：自动脚本安装（实验性）

```bash
# 运行安装脚本（内部调用conda）
bash scripts/setup_conda_environment.sh

# 如遇问题，改用方法一
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
pip list
# 或
conda list

# 安装新包（优先使用pip）
pip install package_name

# 使用清华源加速
pip install -i https://pypi.tuna.tsinghua.edu.cn/simple package_name

# 如需conda安装（仅针对需C库的包）
conda install -c conda-forge package_name

# 导出当前环境
pip freeze > requirements-export.txt
```

**⚠️ 推荐使用pip原因**：
- ✅ 安装速度快conda 10倍以上
- ✅ 无Python版本降级风险
- ✅ 包版本更新更及时
- ✅ 与conda环境完全兼容

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

### Q1: 为什么不推荐使用environment.yml？

**实战遇到的问题**：

1. **依赖求解过慢** (5-30分钟)
   - conda需要遍历多个通道的所有包的所有版本
   - 计算SAT可满足问题（NP完全问题）
   - 卡在`Collecting package metadata`或`Solving environment`阶段

2. **Python版本被自动降级**
   ```
   # 期望：Python 3.9.23 (CPython)
   # 实际：Python 3.9.18 (PyPy)  ← conda自动降级
   ```
   - PyPy与大量科学计算包不兼容
   - 导致streamlit、prophet等包安装失败

3. **包冲突问题**
   - conda-forge和defaults通道的包可能不兼容
   - 不同通道的同名包版本不一致

4. **内存占用大**
   - conda求解过程需要2-4GB内存
   - 可能导致虚拟机卡顿

**pip安装的优势**：
- ✅ 安装时间：3-5分钟 vs 30分钟
- ✅ 锁定CPython 3.9.23，不会降级
- ✅ 无依赖求解，直接下载安装
- ✅ 包版本更新，支持清华源加速

---

### Q2: 环境创建失败或卡住

```bash
# 方案一：终止并清理
conda clean --all -y

# 方案二：删除环境重建（使用pip方法）
conda env remove -n mannings-sla -y
conda create -n mannings-sla python=3.9 pip -y
conda activate mannings-sla
pip install -i https://pypi.tuna.tsinghua.edu.cn/simple pandas numpy scipy scikit-learn xgboost streamlit plotly pyyaml python-dotenv
pip install prophet ortools geopandas fastapi uvicorn python-multipart folium streamlit-folium
```

---

### Q3: Prophet安装失败

使用pip安装通常无问题，如遇问题：

```bash
# pip直接安装（推荐）
pip install prophet

# 或使用conda（不推荐）
conda install -c conda-forge cmdstanpy
conda install -c conda-forge prophet
```

---

### Q4: 环境已存在

```bash
# 查看环境
conda env list

# 删除旧环境
conda env remove -n mannings-sla -y

# 重新创建（使用pip方法）
conda create -n mannings-sla python=3.9 pip -y
```

---

### Q5: streamlit安装卡住或闪退

**原因**：conda尝试安装streamlit时触发Python版本降级至PyPy

**解决方案**：
```bash
# 确认Python版本
python --version  # 应为 3.9.23

# 如果是PyPy，重建环境
conda deactivate
conda env remove -n mannings-sla -y
conda create -n mannings-sla python=3.9 pip -y
conda activate mannings-sla

# 使用pip安装
pip install streamlit
```

---

### Q6: 如何切换不同环境

```bash
# 退出当前环境
conda deactivate

# 切换到其他环境
conda activate other_env
```

---

## 团队协作

### 新增依赖后

**推荐流程**（使用pip）：

1. 更新 `requirements.txt`：
```bash
# 安装新包
pip install new_package

# 导出依赖列表
pip freeze > requirements-current.txt

# 手动更新requirements.txt（只添加新包）
echo "new_package>=1.0.0" >> requirements.txt
```

2. 通知团队运行：
```bash
pip install new_package
# 或
pip install -r requirements.txt
```

**传统流程**（使用conda，不推荐）：

1. 更新 `environment.yml`
2. 更新 `requirements.txt`
3. 通知团队运行：
```bash
conda env update -f environment.yml --prune  # 可能很慢
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
