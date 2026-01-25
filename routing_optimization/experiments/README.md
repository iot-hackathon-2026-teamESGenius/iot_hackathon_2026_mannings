# 路径优化实验 | Routing Optimization Experiments

## 概述 | Overview

本目录包含路径优化算法的对比实验框架，用于验证三种优化方案的性能：
- **贪心基线 (Greedy Baseline)**: 简单快速的最近邻算法，用作性能基准
- **标准OR-Tools优化**: Google OR-Tools CVRPTW求解器，平衡质量与速度
- **鲁棒多情景优化**: 引入需求预测分布和学习特征，处理不确定性

## 快速开始 | Quick Start

### 运行对比实验

```bash
# 进入项目目录
cd routing_optimization

# 运行三路算法对比
python run_experiment.py
```

**预期输出**：
- 三种算法的求解过程和结果指标（距离、路线数、SLA违反、耗时）
- 场景对比统计（仅鲁棒优化）
- 性能改进幅度分析

### 运行简单Demo

```bash
# 运行带预测特征的最小可运行示例
python demo/run_demo.py

# 选择演示模式：
# 1: 简单3门店演示
# 2: 含预测特征的7门店演示
```

## 预测特征说明 | Prediction Features

### 1. 基础需求列 | Base Demand

| 列名 | 含义 | 来源 | 用途 |
|------|------|------|------|
| `demand` | 订单基础需求 | 历史数据或系统 | 标准优化的基准输入 |

### 2. 预测需求列 | Forecast Demand

| 列名 | 含义 | 范围 | 说明 |
|------|------|------|------|
| `predicted_demand` | 点预测（均值） | [0, ∞) | 预测模块提供的均值预测；若不提供则使用 `demand` |
| `demand_p10` | 低分位数预测 | [0, ∞) | 第10百分位（乐观情景，需求较低） |
| `demand_p50` | 中分位数预测 | [0, ∞) | 第50百分位（中位数，等同点预测） |
| `demand_p90` | 高分位数预测 | [0, ∞) | 第90百分位（悲观情景，需求较高） |

**分位数场景生成**：
- 若数据包含 `demand_p10`, `demand_p50`, `demand_p90`，鲁棒优化会生成三个分位数场景
- 同时保留 ±10% 需求波动场景以保持向后兼容性
- 场景标签："low" (p10), "mid" (p50), "high" (p90), "ratio_0.90", "ratio_1.00", "ratio_1.10"

### 3. 学习增强特征 | Learning Feature

| 列名 | 含义 | 范围 | 用途 |
|------|------|------|------|
| `feature_score` | 学习增强信号 | [0, 1] | 线性缩放需求的乘以因子；0.5为中性点 |

**特征缩放公式**：
```
adjusted_demand = base_demand × (1 + feature_weight × (feature_score - 0.5))
```
- `feature_score = 0.5` → 无调整（乘以1）
- `feature_score = 0` → 调整为 `1 - feature_weight` 倍
- `feature_score = 1` → 调整为 `1 + feature_weight` 倍

**示例**（feature_weight = 0.15）：
- Store A: `feature_score = 0.7` → demand 增加 `0.15 × (0.7 - 0.5) = 3%`
- Store B: `feature_score = 0.3` → demand 减少 `0.15 × (0.3 - 0.5) = -3%`

## 数据接口 | Data Interface

### 输入格式

```python
{
    'store_id': int,                      # 门店编号
    'demand': float,                      # 基础需求（若无predicted_demand则使用）
    'predicted_demand': float,            # [可选] 预测均值需求
    'demand_p10': float,                  # [可选] 低分位预测
    'demand_p50': float,                  # [可选] 中分位预测
    'demand_p90': float,                  # [可选] 高分位预测
    'feature_score': float,               # [可选] 学习增强特征(0-1)
    'time_window_start': int,             # 收货窗口起始(分钟)
    'time_window_end': int,               # 收货窗口结束(分钟)
    'lat': float,                         # 门店纬度
    'lon': float                          # 门店经度
}
```

### 输出格式

```python
{
    'status': 'Success',
    'routes': [
        {
            'vehicle_id': int,            # 车辆编号
            'store_sequence': [int],      # 门店访问顺序
            'distance_km': float,         # 路线距离(km)
            'load_units': float,          # 车辆载重(单位)
            'departure_time_min': int,    # 发车时间(分钟)
            'return_time_min': int        # 返回时间(分钟)
        }
    ],
    'metrics': {
        'total_distance_km': float,       # 总距离
        'num_vehicles_used': int,         # 使用车辆数
        'computation_time_sec': float,    # 求解耗时
        'optimization_type': str          # "greedy_baseline" / "standard" / "robust"
    },
    'sla_violations': [int]               # 未按时送达的门店ID列表
}
```

## 配置说明 | Configuration

关键配置文件：`src/config.py`

### 预测特征配置

```python
# 预测特征配置
PREDICTED_DEMAND_COL = 'predicted_demand'  # 预测均值列名
DEMAND_QUANTILE_COLS = {                    # 分位数列名映射
    'low': 'demand_p10',
    'mid': 'demand_p50',
    'high': 'demand_p90'
}
LEARNING_FEATURE_COL = 'feature_score'      # 学习特征列名
LEARNING_FEATURE_WEIGHT = 0.15              # 特征权重（>0时启用）
ENABLE_PREDICTIVE_SCENARIOS = True          # 若存在分位数/特征则自动启用
```

### 鲁棒优化配置

```python
# 鲁棒优化参数
DEMAND_RATIOS = [0.9, 1.0, 1.1]              # 需求波动比例
SCENARIO_WEIGHTS = None                      # 可选，与 DEMAND_RATIOS 一一对应的权重
MONTE_CARLO_SAMPLES = 0                      # 额外蒙特卡洛场景数（0=关闭）
MONTE_CARLO_MAX_SAMPLES = 20                 # 安全上限，防止场景爆炸
MONTE_CARLO_STD = 0.05                       # 正态扰动标准差（围绕1.0，剪裁到[0.8,1.2]）
ROBUST_SELECTION_CRITERION = 'min_max_distance'  # 鲁棒方案选择标准
```

**说明**：
- 若提供 `SCENARIO_WEIGHTS`，比例场景将携带权重并参与比较；未提供则等权。
- `MONTE_CARLO_SAMPLES`>0 时，会在比例/分位数场景之外再采样若干随机扰动场景；数量被 `MONTE_CARLO_MAX_SAMPLES` 限制。
- 学习特征缩放已做剪裁（0.8–1.2），避免需求被极端放大/缩小。

### 调整方法

1. **禁用预测特征**：
   ```python
   ENABLE_PREDICTIVE_SCENARIOS = False
   ```
   此时只使用 `demand` 和 `DEMAND_RATIOS` 生成场景（向后兼容）

2. **调整特征权重**：
   ```python
   LEARNING_FEATURE_WEIGHT = 0.25  # 增加特征影响
   ```

3. **调整需求波动范围**：
   ```python
   DEMAND_RATIOS = [0.8, 0.9, 1.0, 1.1, 1.2]  # 更宽的波动范围
   ```

4. **启用加权/蒙特卡洛场景**：
    ```python
    SCENARIO_WEIGHTS = [0.2, 0.5, 0.3]  # 与 DEMAND_RATIOS 对应
    MONTE_CARLO_SAMPLES = 5             # 生成5个扰动场景（受 MAX_SAMPLES 限制）
    ```

## 算法说明 | Algorithms

### 贪心基线 (Greedy Baseline)

**策略**：逐车辆贪心扩展，每步选择距离最近的可行门店

**特点**：
- 快速（线性复杂度，无需求解器）
- 简单（无需复杂参数调优）
- 质量较低（作为性能下界参考）

**适用场景**：
- 实时应答需求
- 快速可行解初始化

**输出指标**：
- 总距离、路线数、未送达门店数
- 每条路线的距离与载重

### 标准OR-Tools优化 (Standard Optimization)

**策略**：启发式搜索（PATH_CHEAPEST_ARC + GUIDED_LOCAL_SEARCH）

**特点**：
- 质量好（平衡成本与可行性）
- 时间预可控（30秒内收敛）
- 生产就绪（Google OR-Tools稳定库）

**场景**：
- 日常配送计划
- 需要SLA保障的订单

### 鲁棒多情景优化 (Robust Optimization)

**策略**：
1. 生成多个需求场景（分位数或波动比例）
2. 对每个场景分别求解VRP
3. 选择最鲁棒的方案（最小化最坏情况距离或SLA违反）

**特点**：
- 处理需求不确定性
- 结合预测分布和学习特征
- 计算成本增加（多场景求解）

**选择准则**：
- `min_max_distance`: 最小化最坏情况距离（保守）
- `min_avg_distance`: 最小化平均距离（激进）
- `min_sla_violation`: 最小化SLA违反数（可靠性优先）

## 输出解读 | Output Interpretation

### 标准输出示例

```
🔬 路径优化对比实验 - ROUTING OPTIMIZATION COMPARISON
============================================================

⏳ Running experiments...

### 标准优化 (Standard Optimization) ###
Total Distance: 25.45 km
Routes: 3
SLA Violations: 0
Computation Time: 2.34 s

### 贪心基线 (Greedy Baseline) ###
Total Distance: 28.32 km        ← 比标准多11.3%
Routes: 3
SLA Violations: 0
Elapsed Time (simulated): 120.5 min

### 鲁棒优化 (Robust Optimization) - 含预测特征 & 需求波动 ###
Scenario Distances: [24.23, 25.45, 26.78] km
Worst-case Distance: 26.78 km
SLA Violations: 0
Computation Time: 7.89 s
选择标准: min_max_distance (最小化最坏情况距离)

💡 对比分析 (Comparison Analysis)
⚠️  鲁棒优化最坏距离比标准优化增加了 5.2%
    但鲁棒方案可应对需求波动，降低SLA风险
➡️  贪心基线相比标准优化距离差异: 11.3%

📈 场景稳定性（鲁棒优化）: 标准差 = 1.15 km
🚗 车辆使用对比: 贪心 3 辆, 标准 3 辆, 鲁棒 3 辆

✅ 实验完成!
```

### 关键指标解读

| 指标 | 含义 | 优化方向 |
|------|------|--------|
| Total Distance | 总行驶距离(km) | 越低越好 |
| Routes | 使用车辆数 | 越少越好 |
| SLA Violations | 未按时送达的门店数 | 越少越好（0最佳） |
| Worst-case Distance | 最坏情景距离 | 仅鲁棒优化有；越低越稳定 |
| Std Distance | 场景距离标准差 | 越低越稳定（仅鲁棒） |

## 常见问题 | FAQ

### Q: 为什么鲁棒优化比标准优化距离更长？
**A**: 鲁棒优化优先保证在需求波动条件下的稳定性。为应对高需求情景，可能在低需求时浪费容量。这是可靠性与成本的权衡。调整 `ROBUST_SELECTION_CRITERION` 为 `min_avg_distance` 可降低距离但增加风险。

### Q: 特征权重多少合适？
**A**: 推荐 0.1~0.3。权重越大，特征信号对需求的影响越大。建议先用小权重(0.1)验证，再根据预测准确性调整。

### Q: 贪心基线出现较多SLA违反，是否存在bug？
**A**: 不一定是bug。贪心算法优先选择距离最近的店点，不充分考虑时间窗约束的长期影响。可以通过调整 `src/baselines.py` 中的候选排序，优先选择时间窗更紧张的店点。

### Q: 如何集成真实预测数据？
**A**: 
1. 准备CSV文件，包含 `predicted_demand`, `demand_p10`, `demand_p50`, `demand_p90`, `feature_score` 列
2. 在 `demo/run_demo.py` 或业务脚本中调用：
   ```python
   import pandas as pd
   from src.data_interface import prepare_vrp_input, load_forecast_data
   
   df = pd.read_csv('path/to/forecast.csv')
   vrp_input = prepare_vrp_input(df, depot_location, capacity, num_vehicles)
   ```
3. 运行求解器

## 后续改进 | Future Enhancements

- [ ] 支持多仓库和多车型
- [ ] 动态 rerouting（实时订单插入）
- [ ] 与真实GIS/路网的接入
- [ ] 学习特征的在线更新与反馈循环
- [ ] 可视化dashboard展示路线和指标
- [ ] A/B测试框架（对比不同配置）

## 联系与反馈 | Contact

问题或建议：请联系路由优化团队

---

**Last Updated**: January 2026  
**Version**: 1.0
