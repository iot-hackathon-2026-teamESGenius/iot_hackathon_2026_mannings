# IOT Hackathon 2026 - Mannings Store Pickup SLA Optimization
# 第一阶段提案 (Initial Proposal)

<p align="center">
  <strong>门店自提SLA优化系统</strong><br>
  DFI Retail Group - Mannings (万宁)
</p>

**Team Name:** ESGenius  
**Submission Date:** February 15, 2026  
**Challenge:** DFI Retail Group - Mannings Store Pickup SLA Optimization

---

## 目录 (Table of Contents)

1. [Objectives (目标)](#1-objectives-目标)
2. [Pain Points / Problems to Address (痛点/问题)](#2-pain-points--problems-to-address-痛点问题)
3. [Proposed Solution (提案解决方案)](#3-proposed-solution-提案解决方案)
4. [Data Sources (数据来源)](#4-data-sources-数据来源)
5. [Benefits & Impacts (效益与影响)](#5-benefits--impacts-效益与影响)
6. [Team Profile (团队介绍)](#6-team-profile-团队介绍)
7. [Appendices (附录)](#7-appendices-附录)

---

## 1. Objectives (目标)

### 1.1 项目愿景

为万宁（Mannings）打造**端到端的门店自提SLA优化系统**，通过AI/ML预测与数学优化算法的深度融合，实现：

> **"让每一位顾客都能在承诺时间内取到货品，同时最大化运营效率、最小化物流成本"**

### 1.2 核心目标（量化指标）

| 目标维度 | KPI指标 | 当前基线 | 目标值 | 改善幅度 |
|----------|---------|----------|--------|----------|
| **SLA达成率** | 订单按时履约率 | ~85% | ≥95% | +10%↑ |
| **需求预测精度** | MAPE (Mean Absolute Percentage Error) | 未知 | <15% | 行业领先 |
| **路径优化效率** | 总配送距离/成本 | 人工规划 | 降低20% | -20%↓ |
| **库存缺货率** | 门店级缺货订单比例 | 波动大 | <5% | 显著改善 |
| **自提承诺准确度** | 可提货时间预测误差 | 无预测 | ±15分钟 | 全新能力 |

### 1.3 战略目标

1. **顾客体验升级**：提供可信赖的"可提货时间"承诺，减少顾客等待焦虑
2. **运营智能化**：从人工经验决策转向数据驱动的自动化决策
3. **成本精细控制**：在保障SLA的前提下，最小化车队调度与库存持有成本
4. **系统可扩展**：模块化架构支持未来智能体（AI Agent）能力扩展

---

## 2. Pain Points / Problems to Address (痛点/问题)

基于 Mannings Challenge Briefing 中明确的 **A-E 五大核心问题**，我们逐一分析并提出针对性解决思路：

### 2.1 Problem A: 需求预测波动 (Demand Fluctuation)

| 波动因素 | 业务影响 | 我们的解决思路 |
|----------|----------|----------------|
| **促销活动** | 需求激增30-50%，易缺货 | Prophet模型 + 促销日历特征 |
| **长尾SKU** | 历史数据稀疏，预测难 | 层级预测 + SKU聚类 |
| **门店异质性** | 不同门店需求模式差异大 | 门店级参数自适应调优 |
| **周末/节假日高峰** | 处理能力瓶颈 | 外部日历特征 + 周期性建模 |
| **季节性趋势** | Q4节日购物高峰 | Prophet自动季节分解 |

**技术方案**：采用 **Facebook Prophet** 作为主预测模型，融合以下外部因素：
- 促销日历（Promotion Calendar）
- 香港公众假期（HK Public Holidays from data.gov.hk）
- 天气数据（HKO Weather API）
- 历史同期数据

### 2.2 Problem B: 库存不确定性 (Inventory Uncertainty)

| 不确定性来源 | 具体表现 | 我们的解决思路 |
|--------------|----------|----------------|
| **账面 ≠ 实际** | 损坏、错放、实时消耗 | 概率性可销售库存模型 |
| **多渠道共享库存** | 线上线下竞争同一库存 | 动态安全库存缓冲 |
| **盘点滞后** | 库存信息更新延迟 | 基于订单流的实时修正 |

**技术方案**：构建 **可销售库存预测模型**，核心公式：

```
可销售库存 = 账面库存 × 可用率系数 - 在途订单 - 安全库存
```

其中「可用率系数」通过历史订单履约数据学习得到。

### 2.3 Problem C: 补货计划延迟 (Replenishment Delays)

| 延迟因素 | 业务影响 | 我们的解决思路 |
|----------|----------|----------------|
| **DC→ECDC交期不确定** | 补货到达时间波动 | 鲁棒优化 + 多情景规划 |
| **ECDC收货能力限制** | 峰值期处理积压 | 收货窗口平滑调度 |
| **运输延误** | 交通、天气影响 | 交通数据融合 + 缓冲时间 |

**技术方案**：采用 **Scenario-based Robust Optimization**，在补货计划中考虑：
- 乐观情景（准时到达）
- 基准情景（平均延迟）
- 悲观情景（严重延迟）

选择在最坏情景下仍能保障SLA的鲁棒方案。

### 2.4 Problem D: 车队调度与路线规划 (Fleet Scheduling & Routing)

| 调度挑战 | 业务影响 | 我们的解决思路 |
|----------|----------|----------------|
| **时间窗约束** | 门店有限营业时间 | CVRPTW（带时间窗的车辆路径问题） |
| **车辆容量限制** | 单车装载上限 | 容量约束建模 |
| **多门店配送** | 路径组合爆炸 | OR-Tools + 元启发式算法 |
| **SLA与成本权衡** | 更快 vs 更省 | 多目标优化 + Pareto前沿 |

**技术方案**：基于 **Google OR-Tools** 实现 CVRPTW 求解，并创新性地引入：
- **鲁棒路径优化器（RobustRoutingOptimizer）**：核心创新点
- **多情景需求建模**：从预测置信区间生成多个需求场景
- **Min-Max策略**：选择在最坏需求情景下表现最优的路径方案

### 2.5 Problem E: 门店处理时间预测 (Store Processing Time)

| 处理环节 | 不确定性来源 | 我们的解决思路 |
|----------|--------------|----------------|
| **拣货时间** | SKU位置、数量、员工熟练度 | 历史拣货时间回归模型 |
| **打包时间** | 订单复杂度、包装要求 | 订单特征→时间预测 |
| **等待时间** | 顾客到达分布 | 队列论建模 |

**技术方案**：构建 **概率性SLA预测模型**，输出：
- 预计可提货时间（Point Estimate）
- 置信区间（如 [10:00, 10:30] with 90% confidence）

---

## 3. Proposed Solution (提案解决方案)

### 3.1 端到端系统架构

我们采用 **五层模块化架构**，确保清晰解耦与未来扩展性：

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         Layer 1: 前端展示层                                   │
│                         Vue 3 + uniapp + uni-ui                              │
│  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────────────┐    │
│  │ 登录    │  │ 首页    │  │ 预测    │  │ 调度    │  │ SLA预警监控    │    │
│  │ 模块    │  │ 看板    │  │ 展示    │  │ 规划    │  │ 实时告警       │    │
│  └─────────┘  └─────────┘  └─────────┘  └─────────┘  └─────────────────┘    │
└────────────────────────────────┬────────────────────────────────────────────┘
                                 │ RESTful API
┌────────────────────────────────┼────────────────────────────────────────────┐
│                         Layer 2: API服务层                                   │
│                         FastAPI + Uvicorn                                    │
│  /api/auth   /api/dashboard   /api/forecast   /api/planning   /api/sla      │
│  用户认证     KPI看板          需求预测        补货&调度       SLA预警        │
└────────────────────────────────┬────────────────────────────────────────────┘
                                 │
┌────────────────────────────────┼────────────────────────────────────────────┐
│                         Layer 3: 核心算法模块层                               │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐ │
│  │ 需求预测模块  │  │ 库存优化模块  │  │ 补货计划模块  │  │ SLA预测模块     │ │
│  │ IDemand      │  │ IInventory   │  │ IReplenish   │  │ ISLA           │ │
│  │ Forecaster   │  │ Optimizer    │  │ Planner      │  │ Predictor      │ │
│  │ (Prophet)    │  │ (SafetyStock)│  │ (Robust Opt) │  │ (Probabilistic)│ │
│  └──────────────┘  └──────────────┘  └──────────────┘  └──────────────────┘ │
│  ┌──────────────┐  ┌──────────────┐  ┌────────────────────────────────────┐ │
│  │ 距离计算模块  │  │ 情景生成模块  │  │ 鲁棒路径优化模块 ⭐ (核心创新)     │ │
│  │ IDistance    │  │ IScenario    │  │ RobustRoutingOptimizer            │ │
│  │ Calculator   │  │ Generator    │  │ CVRPTW + Multi-Scenario + Min-Max │ │
│  └──────────────┘  └──────────────┘  └────────────────────────────────────┘ │
└────────────────────────────────┬────────────────────────────────────────────┘
                                 │
┌────────────────────────────────┼────────────────────────────────────────────┐
│                         Layer 4: 智能体层 (Stage 2 预留)                      │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐ │
│  │ 需求预测     │  │ 库存优化     │  │ 路径调度     │  │ SLA预警         │ │
│  │ Agent       │  │ Agent       │  │ Agent       │  │ Agent           │ │
│  └──────────────┘  └──────────────┘  └──────────────┘  └──────────────────┘ │
│                          ▲                                                  │
│                 IMultiAgentCoordinator (多智能体协调器)                       │
└─────────────────────────────────────────────────────────────────────────────┘
                                 │
┌────────────────────────────────┼────────────────────────────────────────────┐
│                         Layer 5: 数据层                                      │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐ │
│  │ 门店数据     │  │ 订单历史     │  │ 库存记录     │  │ 外部数据源      │ │
│  │ Store Info   │  │ Order History│  │ Inventory    │  │ HKO/data.gov.hk │ │
│  └──────────────┘  └──────────────┘  └──────────────┘  └──────────────────┘ │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 3.2 核心模块详解

#### 3.2.1 需求预测模块 (Demand Forecaster)

**算法选型**：Facebook Prophet

**选择理由**：
- 自动处理多重季节性（周、月、年）
- 原生支持节假日效应建模
- 对缺失数据和异常值鲁棒
- 可解释性强，便于业务理解

**输入特征**：
| 特征类别 | 具体特征 | 数据来源 |
|----------|----------|----------|
| 历史销售 | 门店×SKU×日期 | 挑战方数据 |
| 促销日历 | 促销类型、折扣力度 | 挑战方数据 |
| 时间特征 | 周几、月份、节假日 | 自动生成 |
| 天气数据 | 温度、降雨概率 | HKO API |
| 门店属性 | 位置、面积、客流量 | 挑战方数据 |

**输出格式**：
```json
{
  "store_id": "MAN001",
  "date": "2026-02-20",
  "predicted_demand": 85,
  "demand_lower": 72,   // 10th percentile
  "demand_upper": 98    // 90th percentile
}
```

#### 3.2.2 可销售库存预测模块 (Inventory Optimizer)

**核心功能**：预测实际可履约的库存量，避免超卖

**关键创新**：动态安全库存计算

```python
safety_stock = z_score × σ_demand × √(lead_time + review_period)
```

其中：
- `z_score`：服务水平对应的z值（如95% SLA → z=1.65）
- `σ_demand`：需求预测标准差
- `lead_time`：补货提前期
- `review_period`：库存检查周期

#### 3.2.3 补货计划模块 (Replenishment Planner)

**流程设计**：

```
DC库存 → ECDC需求汇总 → 补货量计算 → 运输批次规划 → 到货时间预测
```

**考虑因素**：
- DC可用库存
- ECDC收货时间窗
- 运输车辆容量
- 历史运输延迟分布

#### 3.2.4 鲁棒路径优化模块 (Robust Routing Optimizer) ⭐

**核心创新：Scenario-based Robust CVRPTW**

这是我们方案的**核心技术创新点**，解决传统路径优化忽视需求不确定性的问题。

**算法流程**：

```
Step 1: 情景生成 (Scenario Generation)
   ├── 方式A: 分位数情景 (从预测置信区间)
   │   └── low (P10), mid (P50), high (P90)
   ├── 方式B: 比例情景 (需求缩放)
   │   └── ratios = [0.9, 1.0, 1.1]
   └── 方式C: 蒙特卡洛采样
       └── N个随机需求场景

Step 2: 多情景求解 (Multi-Scenario Solving)
   └── 对每个情景独立求解CVRPTW，得到最优路径

Step 3: 鲁棒方案选择 (Robust Selection)
   ├── min_max_distance: 最小化最坏情景距离
   ├── min_avg_distance: 最小化平均距离
   └── min_sla_violation: 最小化SLA违约风险
```

**代码实现示例**：

```python
from src.modules.routing.implementations.robust_optimizer import RobustOptimizer
from src.modules.routing.implementations.scenario_generator import ScenarioGenerator

# 1. 配置情景生成器
scenario_gen = ScenarioGenerator(
    quantile_keys={"low": "demand_p10", "mid": "demand_p50", "high": "demand_p90"},
    feature_key="feature_score",
    feature_weight=0.15,
    monte_carlo_samples=5
)

# 2. 创建鲁棒优化器
optimizer = RobustOptimizer(
    base_vrp_input=vrp_data,
    scenario_generator=scenario_gen
)

# 3. 生成多需求情景
scenarios = optimizer.generate_scenarios()

# 4. 求解所有情景
solutions = optimizer.solve_all_scenarios(time_limit=30)

# 5. 选择鲁棒方案
robust_solution = optimizer.select_robust_solution(
    criterion="min_max_distance"
)
```

**输出格式标准化**：

```python
@dataclass
class OptimizationResult:
    routes: List[List[int]]      # 路径序列 [[1,2,3], [4,5]]
    total_distance: float        # 总距离 (km)
    total_time: float            # 总时间 (min)
    vehicles_used: int           # 车辆数
    sla_risk_score: float        # SLA风险 (0-1)
    scenario_id: str             # 情景标识
```

#### 3.2.5 自提承诺时间预测模块 (SLA Predictor)

**预测目标**：给定订单，预测"最早可提货时间"

**输入**：
- 当前时间
- 路径优化结果（预计到达门店时间）
- 门店处理能力（历史拣货/打包时间）
- 当前排队订单数

**输出**：
```json
{
  "order_id": "ORD123456",
  "pickup_time_estimate": "2026-02-20T14:30:00",
  "confidence_interval": ["14:15", "14:45"],
  "confidence_level": 0.90,
  "risk_level": "LOW"
}
```

### 3.3 模块集成流程

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   需求预测   │ ──→ │  情景生成    │ ──→ │  鲁棒优化    │ ──→ │  SLA预测    │
│   Prophet   │     │ Quantile/MC │     │ CVRPTW+RO  │     │ Probabilistic│
└─────────────┘     └─────────────┘     └─────────────┘     └─────────────┘
      │                   │                   │                   │
      ▼                   ▼                   ▼                   ▼
  预测均值+CI         多需求场景          鲁棒路径方案        可提货时间
```

---

## 4. Data Sources (数据来源)

### 4.1 香港官方公开数据 (Required)

| 数据源 | 网址 | 使用数据 | 应用场景 |
|--------|------|----------|----------|
| **data.gov.hk** | https://data.gov.hk | 交通流量、公众假期 | 行程时间估计、需求调整 |
| **HKO 香港天文台** | https://www.hko.gov.hk/en/abouthko/opendata_intro.htm | 天气预报API | 需求预测调整因子 |
| **CSDI 空间数据** | https://portal.csdi.gov.hk | 地理位置、道路网络 | 距离矩阵计算 |
| **运输署** | https://www.td.gov.hk/en/transport_in_hong_kong/ | 道路网络、交通状况 | 路径规划 |

### 4.2 挑战方提供数据 (Stage 2)

| 数据类型 | 数据描述 | 使用模块 |
|----------|----------|----------|
| 门店信息 | 位置、营业时间、处理能力 | 路径优化、SLA预测 |
| 历史订单 | 订单时间、SKU、数量、履约状态 | 需求预测、SLA预测 |
| 库存记录 | 门店/DC库存水平、补货历史 | 库存优化、补货计划 |
| 车队信息 | 车辆数量、容量、可用时段 | 路径优化 |

### 4.3 模拟数据 (Stage 1 开发)

为Stage 1开发验证，我们实现了 `SimulatedDataFetcher` 模块，生成符合真实分布特征的模拟数据：

```python
from src.modules.data.implementations.simulated_data_fetcher import SimulatedDataFetcher

fetcher = SimulatedDataFetcher()
stores = fetcher.get_stores(region="Hong Kong Island", count=20)
orders = fetcher.get_historical_orders(days=90)
```

---

## 5. Benefits & Impacts (效益与影响)

### 5.1 量化效益预测

| 效益类别 | KPI | 预期改善 | 年化价值估算 |
|----------|-----|----------|--------------|
| **SLA达成率提升** | 按时履约订单占比 | +10% (85%→95%) | 减少客诉、提升复购 |
| **配送距离优化** | 总行驶公里数 | -15% | 燃油成本节省 HK$XXX/年 |
| **车辆利用率** | 单车日均配送单数 | +20% | 减少所需车辆数 |
| **缺货率降低** | 因缺货取消订单比 | -40% | 减少销售损失 |
| **规划效率** | 调度规划耗时 | -80% | 从数小时→数分钟 |

### 5.2 顾客体验影响

| 改善维度 | 当前痛点 | 优化后体验 |
|----------|----------|------------|
| **承诺可信度** | 承诺时间不准，常需等待 | 准确的可提货时间窗 |
| **等待焦虑** | 不知道何时能取货 | 实时进度追踪 |
| **沟通主动性** | 被动等待通知 | 主动推送预警 |
| **取货便利** | 到店后仍需等待 | 到店即取 |

### 5.3 运营效率影响

| 影响领域 | 改善描述 |
|----------|----------|
| **自动化决策** | 从人工经验规划转向AI推荐+人工确认 |
| **实时可见性** | 统一看板展示全链路状态 |
| **异常预警** | 提前识别SLA风险，预留缓解时间 |
| **资源优化** | 基于预测动态调配人员和车辆 |

### 5.4 成本控制影响

| 成本项 | 当前状态 | 优化后 | 节省估算 |
|--------|----------|--------|----------|
| 路径规划人力 | 人工规划(数小时/天) | 自动生成(秒级) | 人力成本大幅降低 |
| 加急配送 | 频繁临时调度 | 主动规划减少突发 | 加急成本减少 |
| 库存持有成本 | 高安全库存 | 精准预测降低缓冲 | 库存成本优化 |
| 客诉处理 | 因延迟产生的客服成本 | SLA提升减少客诉 | 客服成本下降 |

---

## 6. Team Profile (团队介绍)

### 6.1 团队概览

**Team Name:** ESGenius  
**Team Size:** 4人（符合最多6人限制）  
**团队特点:** 跨学科组合 - 运筹优化 + 数据科学 + 软件工程 + 商业分析

### 6.2 成员介绍

| 姓名 | 背景 | 角色 | 主要贡献 |
|------|------|------|----------|
| **成员1** | 运筹学/优化算法 | 组长 & 算法负责人 | 鲁棒路径优化器设计与实现 |
| **成员2** | 数据科学/机器学习 | 数据工程师 | Prophet预测模型、数据管道 |
| **成员3** | 软件工程/后端开发 | 全栈开发 | FastAPI服务、系统集成 |
| **成员4** | 商业分析/UX设计 | 前端负责人 | Vue3界面、用户体验设计 |

### 6.3 团队优势

1. **跨学科融合**
   - 运筹优化 (Operations Research) + 机器学习 (Machine Learning)
   - 技术实现能力 + 业务理解能力

2. **技术栈完整覆盖**
   - 后端：Python, FastAPI, OR-Tools
   - 前端：Vue3, uniapp
   - 数据：Pandas, Prophet, scikit-learn

3. **项目经验**
   - 团队成员有物流优化、供应链分析相关项目经验
   - 熟悉香港零售市场特点

4. **敏捷协作**
   - 采用Git分支协作
   - 模块化开发，并行推进

### 6.4 开发计划

| 阶段 | 时间 | 里程碑 |
|------|------|--------|
| **Stage 1** | 2月1日-15日 | 提案提交、架构设计、核心模块原型 |
| **Stage 2** | 2月16日-3月中 | 数据对接、模块完善、系统集成 |
| **Final** | 3月下旬 | 测试优化、演示准备、最终提交 |

---

## 7. Appendices (附录)

### Appendix A: 技术栈清单

| 类别 | 技术/框架 | 版本 | 用途 |
|------|-----------|------|------|
| **语言** | Python | 3.9 | 后端开发 |
| **API框架** | FastAPI | 0.100+ | REST API服务 |
| **预测模型** | Prophet | 1.1+ | 需求预测 |
| **优化求解** | OR-Tools | 9.6+ | CVRPTW路径优化 |
| **数据处理** | Pandas, NumPy | Latest | 数据ETL |
| **地理计算** | GeoPandas, Shapely | 0.13+/2.0+ | 空间数据处理 |
| **可视化** | Streamlit, Plotly | Latest | 内部看板 |
| **前端框架** | Vue 3 + uniapp | Latest | 用户界面 |
| **部署** | Docker, uniCloud | Latest | 容器化部署 |

### Appendix B: 项目仓库结构

```
iot_hackathon_2026_mannings/
├── src/
│   ├── api/                    # REST API服务
│   │   ├── main.py             # FastAPI入口
│   │   └── routers/            # 路由模块
│   │       ├── auth.py         # 认证
│   │       ├── dashboard.py    # 看板
│   │       ├── forecast.py     # 预测
│   │       ├── planning.py     # 规划
│   │       └── sla.py          # SLA
│   ├── modules/                # 核心算法模块
│   │   ├── routing/            # 路径优化 ⭐
│   │   │   ├── config.py
│   │   │   ├── optimization_result.py
│   │   │   └── implementations/
│   │   │       ├── ortools_optimizer.py
│   │   │       ├── robust_optimizer.py
│   │   │       └── scenario_generator.py
│   │   ├── forecasting/        # 需求预测
│   │   ├── inventory/          # 库存优化
│   │   └── sla/                # SLA预测
│   └── agents/                 # Stage 2 智能体
├── config/                     # 配置文件
├── docs/                       # 文档
├── tests/                      # 测试
└── requirements.txt            # 依赖
```

### Appendix C: API接口清单

| 模块 | 端点 | 方法 | 功能描述 |
|------|------|------|----------|
| Auth | `/api/auth/login` | POST | 用户登录 |
| Auth | `/api/auth/validate` | GET | Token验证 |
| Dashboard | `/api/dashboard/kpi` | GET | KPI指标 |
| Dashboard | `/api/dashboard/trend` | GET | 趋势数据 |
| Forecast | `/api/forecast/demand` | GET | 需求预测 |
| Forecast | `/api/forecast/inventory` | GET | 库存展望 |
| Planning | `/api/planning/replenishment` | GET | 补货计划 |
| Planning | `/api/planning/routes/optimize` | POST | 路径优化 |
| SLA | `/api/sla/orders` | GET | 订单列表 |
| SLA | `/api/sla/alerts` | GET | 预警列表 |

---

## 声明 (Declaration)

- 本提案为团队原创作品
- 已使用至少一个官方公开数据源（HKO, data.gov.hk）
- 团队成员均仅参与本队，符合比赛规则

---

**GitHub Repository:** https://github.com/iot-hackathon-2026-teamESGenius/iot_hackathon_2026_mannings

**Contact:** [Team ESGenius]

---

*本提案展示了我们针对 Mannings 门店自提SLA优化挑战的端到端解决方案，通过AI/ML预测与鲁棒数学优化的深度融合，实现从需求预测到可提货时间承诺的全链路智能化。*
