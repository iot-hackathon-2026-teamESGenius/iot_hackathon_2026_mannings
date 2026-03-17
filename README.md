# IOT Hackathon 2026 - Mannings Store Pickup SLA Optimization

<p align="center">
  <strong>门店自提SLA优化系统</strong><br>
  DFI Retail Group - Mannings (万宁)
</p>

---

## 🎯 项目概述

为DFI Retail Group - Mannings开发端到端的**门店取货SLA优化系统**，通过AI/ML预测和数学优化算法提升顾客取货体验并控制总成本。

### 核心挑战

| 挑战 | 描述 | 解决方案 |
|-----|------|---------|
| A. 需求预测波动 | 促销/长尾SKU/门店差异/周末高峰/季节性 | Prophet + 外部因素融合 |
| B. 库存不确定性 | 账面库存 ≠ 实际可履约库存 | 动态安全库存优化 |
| C. 补货计划 | 交期不确定性，需韧性方案 | 鲁棒优化算法 |
| D. 车队调度 | 直接影响Pickup SLA | CVRPTW + 多情景优化 |
| E. 门店处理时间 | 缺乏可信Pickup Promise | 概率SLA预测 |

---

## 🏗️ 系统架构

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         前端层 (Vue3 + uniapp)                           │
│  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────────────┐   │
│  │ 登录    │ │ 首页    │ │ 预测    │ │ 决策    │ │ SLA预警        │   │
│  └────┬────┘ └────┬────┘ └────┬────┘ └────┬────┘ └───────┬─────────┘   │
└───────┼──────────┼──────────┼──────────┼───────────────┼───────────────┘
        │          │          │          │               │
        ▼          ▼          ▼          ▼               ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                      REST API 层 (FastAPI)                               │
│  /api/auth  /api/dashboard  /api/forecast  /api/planning  /api/sla      │
└─────────────────────────────────┬───────────────────────────────────────┘
                                  │
┌─────────────────────────────────┼───────────────────────────────────────┐
│                        核心模块层                                        │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌─────────────┐  │
│  │IDataFetcher  │  │IDemand       │  │IRouting      │  │ISLA         │  │
│  │数据获取      │  │Forecaster    │  │Optimizer     │  │Predictor    │  │
│  │              │  │需求预测      │  │路径优化      │  │SLA预测      │  │
│  └──────────────┘  └──────────────┘  └──────────────┘  └─────────────┘  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────────────┐   │
│  │IDistance     │  │IInventory    │  │RobustRoutingOptimizer       │   │
│  │Calculator    │  │Optimizer     │  │鲁棒路径优化 (创新点)         │   │
│  │距离计算      │  │库存优化      │  │                              │   │
│  └──────────────┘  └──────────────┘  └──────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼ (Stage 2)
┌─────────────────────────────────────────────────────────────────────────┐
│                      智能体层 (预留接口)                                  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌─────────────┐  │
│  │IDemand       │  │IInventory    │  │IRouting      │  │ISLAAlert    │  │
│  │ForecastAgent │  │OptAgent      │  │DispatchAgent │  │Agent        │  │
│  └──────────────┘  └──────────────┘  └──────────────┘  └─────────────┘  │
│                          ▲                                              │
│                          │                                              │
│                 IMultiAgentCoordinator                                  │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 🧠 核心算法

### 路径优化 - 鲁棒优化器

基于 **Learning Enhanced Robust Routing** 方案，实现Scenario-based Robust Optimization：

```python
from src.modules.routing.implementations.robust_optimizer import RobustRoutingOptimizer
from src.modules.routing.implementations.scenario_generator import ScenarioGenerator

# 创建优化器
optimizer = RobustRoutingOptimizer(
    scenario_generator=ScenarioGenerator(num_scenarios=5),
    selection_criterion="min_max_distance"
)

# 从预测结果进行鲁棒优化
result = optimizer.robust_optimization_from_forecasts(
    stores=store_list,
    forecasts=demand_forecasts,
    vehicles=vehicle_fleet,
    distance_calculator=calculator,
    use_confidence_bounds=True
)
```

### 创新点

1. **多情景需求建模**: 从预测置信区间生成离散需求情景
2. **Min-Max鲁棒策略**: 优化最坏情景下的表现
3. **预测→决策闭环**: 预测不确定性直接驱动调度决策
4. **学习增强策略**: 基于 feature_score 的需求缩放

### 输出格式标准化

```python
from src.modules.routing.optimization_result import OptimizationResult

# 标准化输出格式
result = OptimizationResult(
    routes=[[1,2,3], [4,5]],       # 每辆车的路径序列
    total_distance=12.5,           # 总行驶距离 (km)
    total_time=180,                # 总配送时间 (min)
    vehicles_used=2,               # 使用车辆数
    sla_risk_score=0.05,           # SLA风险评分 (0-1)
    scenario_id="ratio_1.0"        # 情景标识
)
```

---

## 📊 项目进度

### Stage 1 (当前)

- [x] 核心模块框架搭建
- [x] 需求预测模块 (Prophet)
- [x] 路径优化模块 (OR-Tools + 鲁棒优化)
- [x] SLA预测模块
- [x] REST API服务层
- [x] Streamlit可视化看板
- [x] 优化结果标准化输出 (OptimizationResult)
- [x] 鲁棒优化学习增强策略
- [x] 多情景生成器 (分位数/比例/蒙特卡洛)

### Stage 2 (计划)

- [ ] 智能体系统实现
- [ ] 强化学习集成
- [ ] 实时数据对接
- [ ] 生产环境部署

---

## 📄 License

Copyright © 2026 DFI Retail Group. All rights reserved.