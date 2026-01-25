# 路径优化模块 - 预测数据接口说明

## 数据接口定义

本目录用于存放预测模块输出的需求预测数据，供路径优化模块使用。

## 输入数据格式

### 1. 需求预测数据 (forecast_demand.csv)

```csv
store_id,sku_id,date,forecast_demand,lower_bound,upper_bound,confidence
M001,SKU001,2026-01-25,45.0,38.2,51.8,0.90
M001,SKU002,2026-01-25,32.0,27.2,36.8,0.85
M002,SKU001,2026-01-25,58.0,49.3,66.7,0.92
...
```

### 字段说明

| 字段 | 类型 | 说明 |
|-----|------|------|
| store_id | string | 门店ID，如 "M001" |
| sku_id | string | SKU编号，路径优化时聚合为 "ALL" |
| date | string | 预测日期 (YYYY-MM-DD) |
| forecast_demand | float | 预测需求量（件/单位） |
| lower_bound | float | 置信区间下界 |
| upper_bound | float | 置信区间上界 |
| confidence | float | 预测置信度 (0-1) |

## 与核心接口的对应关系

预测数据将被转换为 `DemandForecast` 数据类：

```python
from src.core.interfaces import DemandForecast

forecast = DemandForecast(
    store_id="M001",
    sku_id="SKU001",
    date="2026-01-25",
    forecast_demand=45.0,
    lower_bound=38.2,
    upper_bound=51.8,
    confidence=0.90
)
```

## 数据加载示例

```python
import pandas as pd
from src.core.interfaces import DemandForecast

def load_forecast_data(file_path: str) -> list:
    """
    加载预测数据并转换为 DemandForecast 列表
    """
    df = pd.read_csv(file_path)
    
    forecasts = []
    for _, row in df.iterrows():
        forecasts.append(DemandForecast(
            store_id=row['store_id'],
            sku_id=row['sku_id'],
            date=row['date'],
            forecast_demand=row['forecast_demand'],
            lower_bound=row['lower_bound'],
            upper_bound=row['upper_bound'],
            confidence=row['confidence']
        ))
    
    return forecasts
```

## 与路径优化模块的对接

```python
from src.modules.routing.implementations.robust_optimizer import RobustRoutingOptimizer

# 加载预测数据
forecasts = load_forecast_data("data/routing/forecast_input/forecast_demand.csv")

# 创建鲁棒优化器
optimizer = RobustRoutingOptimizer(
    time_limit_seconds=60,
    demand_ratios=[0.9, 1.0, 1.1]
)

# 执行优化（直接使用预测结果）
result = optimizer.robust_optimization_from_forecasts(
    stores=stores,
    forecasts=forecasts,
    vehicles=vehicles,
    distance_calculator=distance_calc,
    use_confidence_bounds=True  # 使用预测的置信区间生成情景
)
```

## 注意事项

1. **数据时效性**: 确保预测数据与优化运行日期对应
2. **门店ID一致性**: store_id 必须与门店基础数据中的 ID 一致
3. **需求聚合**: 路径优化时会按 store_id 聚合所有 SKU 的需求
4. **置信区间**: 如果 `use_confidence_bounds=True`，将使用 lower_bound/upper_bound 生成情景
