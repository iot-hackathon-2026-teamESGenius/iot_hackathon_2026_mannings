# Routing Optimization - Stage 2 Status

## 概述
本仓库为 Routing Optimization 阶段 2 项目的主要代码库，包含以下内容：

- CVRPTW 求解器完善
- 多场景并行求解
- Min-Max / weighted_sum / pareto 鲁棒选择策略
- DFI.zip 真实数据接入到路径优化链路
- Planning API 对接真实求解输出

不属于当前模块负责范围但需要协同的部分：包括数据接入、预测、SLA、前端页面和 Dashboard

## 当前实现

Stage 2 已落地的核心能力：

1. 标准 CVRPTW 求解，基于 OR-Tools。
2. 鲁棒多情景优化，支持分位数场景、比例场景和可选 Monte Carlo 场景。
3. 并行场景求解，减少多场景求解延迟。
4. 新增鲁棒选择策略 `weighted_sum` 和 `pareto`。
5. DFI.zip 真实数据适配函数，可直接转成现有 VRP 输入格式。
6. Planning API 新增真实优化接口 `/api/planning/routes/optimize`。

## 目录

```
routing_optimization/                              # 路径优化主目录
├── demo/                                          # 演示与联调脚本
│   ├── run_demo.py                                # Mock 数据快速演示
│   └── run_dfi_demo.py                            # DFI 真实数据演示
├── experiments/                                   # 对比实验与实验说明
├── data/                                          # 输入数据目录
│   ├── forecast_input/                            # 预测/需求标准输入
│   └── mock/                                      # 模拟数据生成与样例
├── src/                                           # 核心算法源码
│   ├── config.py                                  # 全局配置与调参项
│   ├── data_interface.py                          # 数据加载与字段适配
│   ├── distance_matrix.py                         # 距离/时间矩阵计算
│   ├── solver.py                                  # 求解主入口
│   ├── optimization_result.py                     # 结果标准化输出
│   ├── api/main.py                                # FastAPI 入口（外层）
│   └── api/routers/planning.py                    # Planning 路由对接入口
│   └── modules/routing/implementations/           # 路径优化实现集合
│       ├── ortools_optimizer.py                   # 标准 CVRPTW 求解器
│       ├── robust_optimizer.py                    # 鲁棒优化与策略选择
│       └── scenario_generator.py                  # 多场景生成器
```

## 快速使用

### 最小样例验证

```bash
cd routing_optimization
python validate_experiment.py
```

### 真实数据验证

```bash
cd routing_optimization
python demo/run_dfi_demo.py
```

### 启动 Planning API

```bash
cd routing_optimization
uvicorn src.api.main:app --host 0.0.0.0 --port 8000 --reload
```

### 调用真实路径优化接口

```json
POST /api/planning/routes/optimize
{
  "use_real_data": true,
  "top_n_stores": 15,
  "time_limit": 10,
  "use_robust": true,
  "update_schedules": true
}
```

## Stage 2 接口对齐

### 来自数据工程同学的输入接口

最小必需字段：

```python
{
    "store_id": int,
    "demand": float,
    "time_window_start": int,
    "time_window_end": int,
    "lat": float,
    "lon": float,
}
```

### 来自预测同学的增强字段

如果预测模块提供以下字段，鲁棒优化会自动接入：

```python
{
    "predicted_demand": float,
    "demand_p10": float,
    "demand_p50": float,
    "demand_p90": float,
    "feature_score": float,
}
```

字段含义：

1. `predicted_demand`: 点预测，用于替代基础 demand。
2. `demand_p10/p50/p90`: 用于生成低/中/高需求场景。
3. `feature_score`: 学习增强特征，用于对需求做轻量缩放。

### 输出给 Planning API / 前端的稳定接口

算法内部标准输出：

```python
{
    "status": "Success",
    "routes": [...],
    "metrics": {
        "total_distance_km": float,
        "num_vehicles_used": int,
        "computation_time_sec": float,
        "optimization_type": str,
    },
    "sla_violations": [int],
}
```

Planning API 额外映射为前端稳定结构：

```python
{
    "success": True,
    "data": {
        "schedules": [...],
        "date": "YYYY-MM-DD",
        "optimization_summary": {...},
        "optimization_result": {...},
        "map_data": {...},
    }
}
```

## 当前协作边界

### 我方负责

1. 路径优化建模与求解。
2. 鲁棒策略与场景生成对接。
3. 算法输出标准化。
4. 真实数据适配到优化输入。
5. Planning API 的优化结果映射。

### 其他成员通过接口对接

1. 数据工程：提供门店需求、时间窗、门店基础信息。
2. 预测模块：提供点预测和分位数预测。
3. 前端 / 可视化：消费 `schedules` 与 `map_data`。
4. SLA 模块：消费路线和时间结果做 SLA 概率推断。

## 相关文档

1. [GITHUB_CHECKLIST.md](GITHUB_CHECKLIST.md)
2. [routing_optimization/QUICKSTART.md](routing_optimization/QUICKSTART.md)
3. [routing_optimization/data/forecast_input/README.md](routing_optimization/data/forecast_input/README.md)
4. [routing_optimization/docs/api/module_interfaces.md](routing_optimization/docs/api/module_interfaces.md)

## 更新时间

Last Updated: 2026-03-11