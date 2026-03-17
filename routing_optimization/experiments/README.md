# 路径优化实验 | Routing Optimization Experiments

本文件是实验执行的唯一入口说明（Single Source of Truth）。
文档规范与归档规则请查看 [routing_optimization/docs/experiments/README.md](routing_optimization/docs/experiments/README.md)。

## 当前实验范围

实验文档已更新为 Stage 2 ，覆盖：

1. 贪心基线
2. 标准 OR-Tools 优化
3. 鲁棒多情景优化
4. DFI 真实数据快速验证

## 快速运行

### 三算法对比

```bash
cd routing_optimization
python run_experiment.py
```

或运行实验脚本：

```bash
cd routing_optimization
python experiments/routing/baseline_comparison.py
```

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

## 入口脚本说明与区别

1. [routing_optimization/run_experiment.py](routing_optimization/run_experiment.py)
	主实验入口，直接承载三算法对比实验逻辑，建议优先使用。
2. [routing_optimization/experiments/routing/baseline_comparison.py](routing_optimization/experiments/routing/baseline_comparison.py)
	轻量包装入口，内部调用 `run_experiment.py` 的 `run_comparison_experiment()`，用于在 experiments 子目录下保持统一入口形态。

结论：两者当前执行的是同一套对比实验，区别只在入口位置与调用方式，不在算法结果。

## Stage 2 重点实验项

### 鲁棒策略实验

当前算法支持的选择策略：

1. `min_max_distance`
2. `min_avg_distance`
3. `min_sla_violation`
4. `weighted_sum`
5. `pareto`

### 真实数据实验

DFI.zip 已接入实验链路，当前支持：

1. 按日期聚合门店需求
2. Top N 门店抽取
3. 自动构造 VRP 输入
4. 鲁棒求解结果输出

## 实验输入接口

实验输入与其他成员接口保持一致，推荐字段：

| 字段 | 说明 |
|------|------|
| `store_id` | 门店 ID |
| `demand` | 基础需求 |
| `predicted_demand` | 点预测 |
| `demand_p10/p50/p90` | 分位数预测 |
| `feature_score` | 学习增强特征 |
| `time_window_start/end` | 时间窗 |
| `lat/lon` | 坐标 |

## 当前验证结论

截至 2026-03-11，已完成：

1. 最小样例链路跑通。
2. DFI 真实数据链路跑通。
3. Planning API 已能消费真实求解输出。

## 下一步实验工作

1. 完整 DFI 数据规模下的性能基准。
2. 不同鲁棒选择策略对比。
3. 与 SLA 预测模块联调后的端到端实验。

Last Updated: 2026-03-11
