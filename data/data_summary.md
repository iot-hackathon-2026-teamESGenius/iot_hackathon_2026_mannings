# 数据接入状态总结

> **更新时间**: 2026-03-18  
> **状态**: 部分真实数据已接入，部分API仍使用模拟数据

## 📊 数据接入概览

| 数据类型 | 状态 | 数据源 | API端点 | 备注 |
|---------|------|--------|---------|------|
| **门店信息** | ✅ **真实数据** | DFI企业数据 | `/auth/stores`, `/auth/stores/public` | 306个真实门店 |
| **需求预测** | ❌ 模拟数据 | 算法生成 | `/forecast/demand`, `/forecast/trend` | 基于随机算法 |
| **库存展望** | ❌ 模拟数据 | 算法生成 | `/forecast/inventory` | 基于随机算法 |
| **补货计划** | ❌ 模拟数据 | 算法生成 | `/planning/replenishment` | 基于随机算法 |
| **车队调度** | ❌ 模拟数据 | 算法生成 | `/planning/schedules` | 基于随机算法 |
| **SLA订单** | ❌ 模拟数据 | 算法生成 | `/sla/orders` | 基于随机算法 |
| **SLA预警** | ❌ 模拟数据 | 算法生成 | `/sla/alerts` | 基于随机算法 |
| **首页看板** | ❌ 模拟数据 | 算法生成 | `/dashboard/kpi`, `/dashboard/trend` | 基于随机算法 |
| **官方数据** | ✅ **真实数据** | 政府开放数据 | 文件形式 | 交通、天气、节假日 |

## 🎯 已成功接入的真实数据

### 1. 门店信息 (DFI企业数据)
- **数据源**: `data/dfi/raw/dim_store.csv`
- **API端点**: 
  - `GET /auth/stores` (需认证)
  - `GET /auth/stores/public` (公开访问)
- **数据量**: 306个真实门店
- **字段**: `store_id`, `store_name`, `district`, `address`
- **前端使用**: 
  - ✅ 首页门店选择器
  - ✅ 需求预测页面门店筛选
  - ✅ 补货计划页面门店筛选
- **实现文件**: `src/api/routers/auth.py`

### 2. 官方开放数据
- **交通数据**: `data/official/traffic/` - 实时路况、战略道路信息
- **天气数据**: 通过HKO API获取 - 实时天气、预报
- **节假日数据**: `data/official/public_holidays_*.json` - 2025-2026年公众假期
- **实现模块**: 
  - `src/modules/data/implementations/traffic_fetcher.py`
  - `src/modules/data/implementations/hko_fetcher.py`
  - `src/modules/data/implementations/holiday_fetcher.py`

## ❌ 仍使用模拟数据的API

### 1. 需求预测模块 (`src/api/routers/forecast.py`)
**API端点**:
- `GET /forecast/demand` - 需求预测数据
- `GET /forecast/trend` - 需求趋势图表
- `GET /forecast/inventory` - 库存展望
- `GET /forecast/model-info` - 预测模型信息

**模拟数据特征**:
- 使用固定的5个模拟门店 (M001-M005)
- 使用固定的5个模拟SKU (SKU001-SKU005)
- 基于随机算法生成预测值
- 包含周末效应和随机波动

**可移除的模拟数据**:
```python
# 可以移除这些常量定义
MOCK_STORES = {
    "M001": "Mannings Tsim Sha Tsui",
    "M002": "Mannings Causeway Bay", 
    # ...
}
MOCK_SKUS = {
    "SKU001": "维他命C 1000mg",
    "SKU002": "感冒灵颗粒",
    # ...
}
```

### 2. 补货计划模块 (`src/api/routers/planning.py`)
**API端点**:
- `GET /planning/replenishment` - 补货计划列表
- `PUT /planning/replenishment/{plan_id}/adjust` - 调整补货量
- `PUT /planning/replenishment/{plan_id}/approve` - 审批补货计划
- `GET /planning/schedules` - 车队调度计划
- `GET /planning/routes/map-data` - 路线地图数据

**模拟数据特征**:
- 使用内存字典存储 (`REPLENISHMENT_PLANS`, `SCHEDULES`)
- 模拟DC、ECDC、车辆信息
- 基于随机算法生成计划状态

### 3. SLA服务模块 (`src/api/routers/sla.py`)
**API端点**:
- `GET /sla/orders` - 自提订单列表
- `GET /sla/alerts` - SLA预警列表
- `GET /sla/bottleneck` - 瓶颈分析
- `GET /sla/statistics` - SLA统计数据

**模拟数据特征**:
- 使用内存字典存储 (`ORDERS`, `ALERTS`)
- 模拟订单状态和SLA达成情况
- 基于随机算法生成预警信息

### 4. 首页看板模块 (`src/api/routers/dashboard.py`)
**API端点**:
- `GET /dashboard/kpi` - KPI指标卡片
- `GET /dashboard/trend` - 趋势图数据
- `GET /dashboard/alerts-summary` - 预警摘要
- `GET /dashboard/store-performance` - 门店绩效排名

**模拟数据特征**:
- 基于随机算法生成KPI指标
- 模拟趋势数据和预警信息
- 使用固定的模拟门店进行排名

## 🗂️ 可用的真实数据集

### DFI企业数据 (`data/dfi/raw/`)
| 文件 | 大小 | 描述 | 可用于 |
|------|------|------|--------|
| `dim_store.csv` | ~29KB | 门店维度表 | ✅ 已接入门店API |
| `case_study_order_detail-*.csv` | ~11MB | 订单明细数据 | 需求预测、库存优化 |
| `fufillment_detail-*.csv` | ~18MB | 履约配送明细 | 路径优化、SLA分析 |
| `dim_date.csv` | ~37KB | 日期维度表 | 时间序列分析 |

### 官方开放数据 (`data/official/`)
- **交通数据**: 实时路况API、战略道路信息
- **天气数据**: HKO天气API
- **节假日数据**: 2025-2026年公众假期

## 🔧 接入建议

### 优先级P0 - 立即可接入
1. **订单数据接入** - 使用 `case_study_order_detail-*.csv`
   - 替换需求预测API的模拟数据
   - 提供真实的历史订单趋势

2. **履约数据接入** - 使用 `fufillment_detail-*.csv`
   - 替换SLA订单API的模拟数据
   - 提供真实的配送时效数据

### 优先级P1 - 需要数据处理
1. **库存数据推导** - 基于订单数据计算
   - 从订单明细推导库存变化
   - 替换库存展望API的模拟数据

2. **补货计划优化** - 基于历史数据训练
   - 使用真实订单数据训练预测模型
   - 替换补货计划API的模拟数据

### 优先级P2 - 需要算法开发
1. **车队调度优化** - 基于地理和交通数据
   - 结合门店位置和交通数据
   - 开发真实的路径优化算法

2. **SLA预警系统** - 基于历史履约数据
   - 分析历史延误模式
   - 开发预测性预警算法

## 📝 前端模拟数据清理建议

### 可以立即移除的模拟数据
由于门店API已接入真实数据，以下前端模拟数据可以移除：

1. **需求预测页面** (`frontend/pages/index/forcast.vue`)
   - 已使用真实门店API，无需清理

2. **补货计划页面** (`frontend/pages/index/replenishment.vue`)
   - 已使用真实门店API，无需清理

3. **首页** (`frontend/pages/index/index.vue`)
   - 已使用真实门店API，无需清理

### 保留的模拟数据
以下模拟数据需要保留，直到对应的后端API接入真实数据：
- 需求预测的SKU和预测值数据
- 补货计划的计划状态数据
- SLA订单和预警数据
- 首页KPI和趋势数据

## 🚀 下一步行动计划

1. **立即行动**: 分析DFI订单和履约数据结构
2. **第一阶段**: 接入订单历史数据到需求预测API
3. **第二阶段**: 接入履约数据到SLA相关API
4. **第三阶段**: 开发基于真实数据的预测和优化算法
5. **最终目标**: 所有API使用真实数据，移除所有模拟数据

---

**注意**: DFI企业数据受NDA保护，严禁提交到Git仓库。所有数据处理应在本地环境进行。