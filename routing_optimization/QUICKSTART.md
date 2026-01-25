# Routing Optimization - Quick Start Guide

## 环境搭建 | Environment Setup

### 使用 Conda (推荐)
```bash
conda create -n routing_opt python=3.10
conda activate routing_opt
pip install ortools pandas numpy
```

### 使用 pip
```bash
python -m venv routing_env
# Windows
routing_env\Scripts\activate
# Linux/Mac
source routing_env/bin/activate

pip install -r requirements.txt
```

## 运行示例 | Running Examples

### 1. 简单演示 (3个门店)
```bash
cd routing_optimization/demo
python run_demo.py
# 选择: 1
```

### 2. 完整演示 (7个门店 + 鲁棒优化)
```bash
cd routing_optimization/demo
python run_demo.py
# 选择: 2
```

## 自定义数据 | Custom Data

### 方法1: 使用CSV文件
```python
from src.data_interface import load_forecast_data, prepare_vrp_input

# 加载数据
df = load_forecast_data("data/forecast_input/your_data.csv")

# 准备VRP输入
depot = (40.7128, -74.0060)
vrp_input = prepare_vrp_input(df, depot, vehicle_capacity=100, num_vehicles=5)
```

### 方法2: 直接构建字典
```python
vrp_input = {
    'depot': {'lat': 40.7128, 'lon': -74.0060},
    'stores': [
        {
            'id': 1,
            'demand': 20,
            'time_window': (480, 1080),  # 8:00 AM - 6:00 PM
            'lat': 40.75,
            'lon': -74.00
        }
    ],
    'num_vehicles': 3,
    'vehicle_capacity': 100
}
```

## 求解VRP | Solving VRP

### 标准优化
```python
from src.solver import solve_vrp, format_solution_output

solution = solve_vrp(vrp_input, use_robust=False, time_limit=30)
print(format_solution_output(solution))
```

### 鲁棒优化 (创新点)
```python
solution = solve_vrp(vrp_input, use_robust=True, time_limit=30)
print(format_solution_output(solution))
```

## 输出格式 | Output Format

### 控制台输出
- 总距离、车辆数、计算时间
- 每条路线的详细序列
- SLA违反情况
- 场景对比 (鲁棒优化)

### 导出数据
```python
from src.solver import export_solution_to_dict
export_data = export_solution_to_dict(solution)
# export_data 可直接传递给可视化
```

## 配置参数 | Configuration

编辑 `src/config.py` 修改:
- 车辆容量和数量
- 时间窗口设置
- OR-Tools搜索策略
- 鲁棒优化参数
- SLA惩罚权重

## 实验对比 | Experiment Comparison

### 运行三算法对比实验
```bash
cd routing_optimization
python run_experiment.py
```

此命令会在同一VRP实例上运行并对比三种方法:

1. **贪心基线 (Greedy Baseline)**
   - 最近邻启发式算法
   - 最快的计算速度
   - 质量: 通常是三者中最差

2. **标准优化 (Standard OR-Tools)**
   - Google OR-Tools CVRPTW求解器
   - Guided Local Search元启发式
   - 质量: 通常好于贪心
   - 速度: 中等

3. **鲁棒优化 (Robust with Predictions)**
   - 基于需求预测的多场景优化
   - 在多个需求场景下求解
   - 选择最坏情况表现最好的解
   - 质量: 通常最优
   - 速度: 最慢

### 预测特征说明 | Prediction Features

如果输入数据包含以下列，系统会自动使用预测特征:

| 列名 | 说明 | 示例 |
|------|------|------|
| `predicted_demand` | 预测需求 (使用此值而不是基础需求) | 25.5 |
| `demand_p10` | 10分位数 (悲观场景) | 20.0 |
| `demand_p50` | 50分位数 (中位数/标称) | 25.0 |
| `demand_p90` | 90分位数 (乐观场景) | 30.0 |
| `feature_score` | 学习特征得分 (0-1) | 0.7 |

**启用/禁用预测特征:**
```python
# 在 src/config.py 中修改
ENABLE_PREDICTIVE_SCENARIOS = True  # 使用预测特征 (默认)
ENABLE_PREDICTIVE_SCENARIOS = False # 使用基础需求
```

### 场景生成策略 | Scenario Generation Strategy

鲁棒优化生成6个需求场景:

**量化场景 (如果提供了分位数列):**
- 低需求场景: 使用 `demand_p10` (悲观)
- 中需求场景: 使用 `demand_p50` (标称)
- 高需求场景: 使用 `demand_p90` (乐观)

**比例场景 (备选方案):**
- 低需求: 基础需求 × 0.9
- 中需求: 基础需求 × 1.0
- 高需求: 基础需求 × 1.1

**学习特征增强 (如果提供了特征列):**
```
调整后需求 = 基础需求 × (1 + LEARNING_FEATURE_WEIGHT × (特征分数 - 0.5))
```

其中 `LEARNING_FEATURE_WEIGHT=0.15` (可在config.py中配置)

### 实验输出解读 | Interpreting Results

典型输出格式:
```
[INFO] Running routing optimization experiment...
[STAT] Problem size: 10 stores, 3 vehicles

============================================================
Greedy Baseline Results
============================================================
[STAT] Total distance: 42.3 km
[STAT] Number of routes: 3
[STAT] SLA violations: 0
[STAT] Computation time: 0.01 s

============================================================
Standard OR-Tools Optimization
============================================================
[STAT] Total distance: 38.7 km
[STAT] Number of routes: 3
[STAT] SLA violations: 0
[STAT] Computation time: 2.34 s

============================================================
Robust Optimization (6 scenarios)
============================================================
[STAT] Scenario 1 (low): 35.2 km, 3 routes
[STAT] Scenario 2 (mid): 38.7 km, 3 routes
[STAT] Scenario 3 (high): 42.1 km, 3 routes
[STAT] Worst-case distance: 42.1 km
[STAT] Computation time: 8.56 s

[INFO] Performance Analysis:
[STAT] Greedy gap vs Standard: +9.3%
[STAT] Robust robustness score: 0.95
[OK] Experiment completed successfully!
```

**关键指标:**
- **Total distance**: 路线总长度 (越小越好)
- **Number of routes**: 使用的车辆数
- **SLA violations**: 违反时间窗口的客户数
- **Worst-case distance**: 鲁棒方案在最坏场景下的距离
- **Robustness score**: 解的稳定性评分 (0-1, 越接近1越稳定)

## 故障排除 | Troubleshooting

### ImportError: No module named 'ortools'
```bash
pip install ortools
```

### 无可行解
- 检查总需求是否超过总容量
- 放宽时间窗口约束
- 增加车辆数量

### 求解时间过长
- 减少 `time_limit` 参数
- 使用更快的搜索策略
- 减少场景数量 (鲁棒优化)

### 预测特征未生效
确保:
1. CSV文件包含 `predicted_demand` 列
2. `src/config.py` 中 `ENABLE_PREDICTIVE_SCENARIOS = True`
3. 可选: 提供 `demand_p10, demand_p50, demand_p90` 列以启用量化场景

