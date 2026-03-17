# 路径优化实验文档索引 - Stage 2

本目录用于存放路径优化实验文档治理。

## 职责边界

1. 本目录 [routing_optimization/docs/experiments/README.md](routing_optimization/docs/experiments/README.md)：记录实验文档规范、命名、归档要求。
2. 执行入口 [routing_optimization/experiments/README.md](routing_optimization/experiments/README.md)：记录如何运行实验、输入输出与当前结果。

## 文档产出规范

每次新增实验后，建议至少补充以下产物：

1. 实验背景：要验证的问题和假设。
2. 实验配置：数据范围、关键参数、随机种子。
3. 结果摘要：核心指标与结论。
4. 对比分析：与基线或上一版本差异。
5. 风险与下一步：未覆盖场景和后续动作。

## 命名与归档建议

1. 报告命名：`YYYYMMDD_topic.md`。
2. 原始结果命名：`YYYYMMDD_topic.json` 或 `YYYYMMDD_topic.csv`。
3. 图表文件放在对应报告同级目录，名称与报告主题一致。

## 当前状态

1. Stage 2 的可执行实验说明已统一放到 [routing_optimization/experiments/README.md](routing_optimization/experiments/README.md)。
2. 本目录后续仅保留“文档规范和归档规则”，避免与执行文档重复。

Last Updated: 2026-03-11
