# Routing Optimization - Stage 1 Technical Solution

## 项目概述 | Overview

**角色定位**: Algorithm Development – Optimization (Routing & Dispatch Planning)  
**应用场景**: DFI Retail / A5 Watson (DC→ECDC→Store / B2B2C配送场景)  
**目标**: 基于预测模块，生成路径优化，低成本 + 低SLA风险的送货路径与调度方案

## 核心创新 | Innovation

本项目采用 **"学习增强的鲁棒路径规划 (Learning-Enhanced Robust Routing)"** 方案:

1. **以经典VRP/CVRPTW为动作行框架** (Google OR-Tools)
2. **引入需求不确定性的创新增强**:
   - 做适不确定性的 **Scenario-based Robust Optimization**
   - 启发式叠加的 **Hybrid Optimization**
   - 实现从 **预测 → 决策** 的闭环，而非仅依赖点估计

## 问题定义 | Problem Definition

**问题类型**: Capacitated Vehicle Routing Problem with Time Windows (CVRPTW)

**输入 (由其他组提供)**:
- 门店需求清单 (store, day, demand)
- 门店收货时间窗 (time window)
- 车辆容量与数量
- 距离/行驶时间矩阵 (初期可用欧氏距离)

**输出 (本模块交付)**:
- 每辆车的配送路径 (Route Sequence)
- 发车时间与到达时间
- 总运输成本
- SLA风险指标 (是否存在迟到)

## 技术栈 | Tech Stack

- **Python 3.10+**
- **VS Code** (本地开发)
- **可选**: Kaggle Notebook (云端算力支持)
- **核心算法与优化库**:
  - **Google OR-Tools** (路径与调度优化核心)
  - **NumPy / Pandas** (数据结构与接口)

## 项目结构 | Project Structure

```
routing_optimization/
├── data/
│   ├── mock/                    # 模拟数据
│   │   └── generate_mock.py     # Mock数据生成器
│   └── forecast_input/          # 预测模块输出接口
├── src/
│   ├── config.py                # 全局参数
│   ├── data_interface.py        # 输入数据接口
│   ├── distance_matrix.py       # 距离/时间计算
│   ├── vrp_model.py             # OR-Tools 建模
│   ├── robust_optimizer.py      # 多情景鲁棒优化 (创新点)
│   └── solver.py                # 求解与结果解析
├── demo/
│   └── run_demo.py              # 最小可运行示例
└── requirements.txt
```

## 快速开始 | Quick Start

### Step 1: 环境搭建

```bash
# 创建虚拟环境
conda create -n routing_opt python=3.10
conda activate routing_opt

# 安装依赖
pip install ortools pandas numpy
```

### Step 2: 运行Demo

```bash
cd routing_optimization/demo
python run_demo.py
```

### Step 3: 自定义数据

修改 `data_interface.py` 中的数据加载函数，对接预测模块输出。

## 核心模块说明 | Core Modules

### 1. VRP Model (vrp_model.py)
使用 Google OR-Tools 构建 CVRPTW 模型：
- 容量约束 (Capacity Constraint)
- 时间窗口约束 (Time Window Constraint)
- SLA违反惩罚 (SLA Violation Penalty)

### 2. Robust Optimizer (robust_optimizer.py) - 创新点
**Scenario-based Robust Optimization**:
- 生成多个需求场景 (e.g., 90%, 100%, 110% demand)
- 对每个场景分别求解 VRP
- 选择最鲁棒的方案 (最小最大距离准则)

### 3. Solver (solver.py)
主求解器，集成标准优化与鲁棒优化，输出标准化结果供其他组使用。

## 评估指标 | Evaluation Metrics

- **总距离 (Total Distance)**: 所有路径的总行驶距离
- **车辆使用数 (Vehicles Used)**: 实际使用的车辆数量
- **SLA违反 (SLA Violations)**: 未能在时间窗口内送达的门店数
- **计算时间 (Computation Time)**: 算法运行时间

## Stage 1 交付清单 | Stage 1 Deliverables

- ✅ 路径优化算法设计说明
- ✅ 可运行的 Routing Demo (Mock数据)
- ✅ 鲁棒优化创新点描述
- ✅ 清晰的数据接口 (可对接预测模块)

## Stage 2 扩展 | Future Enhancements

- GIS 实际路网接入
- 动态 rerouting (实时订单)
- 多仓/多车型扩展

## 团队协作接口 | Team Integration

### 输入接口 (From Data Engineering)
```python
{
    "store_id": int,
    "demand": float,
    "time_window_start": int,  # minutes from depot open
    "time_window_end": int,
    "lat": float,
    "lon": float
}
```

### 输出接口 (To Visualization)
```python
{
    "routes": [
        {
            "vehicle_id": int,
            "store_sequence": [int],
            "distance_km": float,
            "departure_time_min": int,
            "return_time_min": int
        }
    ],
    "metrics": {
        "total_distance_km": float,
        "num_vehicles_used": int,
        "computation_time_sec": float
    },
    "sla_violations": [int]  # List of store IDs
}
```

## 参考资料 | References

- [Google OR-Tools Documentation](https://developers.google.com/optimization)
- [CVRPTW Problem Description](https://developers.google.com/optimization/routing/vrptw)
- Stage 1 技术方案文档

---

**Contact**: Algorithm Development - Optimization Team  
**Last Updated**: January 2026