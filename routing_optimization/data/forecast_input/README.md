# 路径优化输入接口说明 - Stage 2

本目录用于放置供路径优化模块消费的预测/需求输入文件。

## 最小输入字段

以下字段是路径优化最小可运行要求：

| 字段 | 类型 | 必需 | 说明 |
|------|------|------|------|
| `store_id` | int/string | 是 | 门店唯一标识 |
| `demand` | float | 是 | 基础需求 |
| `time_window_start` | int | 是 | 收货时间窗开始，分钟制 |
| `time_window_end` | int | 是 | 收货时间窗结束，分钟制 |
| `lat` | float | 推荐 | 纬度 |
| `lon` | float | 推荐 | 经度 |

## 预测增强字段

以下字段由预测模块提供时，鲁棒优化会自动使用：

| 字段 | 类型 | 必需 | 用途 |
|------|------|------|------|
| `predicted_demand` | float | 否 | 点预测需求 |
| `demand_p10` | float | 否 | 低需求场景 |
| `demand_p50` | float | 否 | 中位场景 |
| `demand_p90` | float | 否 | 高需求场景 |
| `feature_score` | float | 否 | 学习增强特征 |

## 推荐 CSV 示例

```csv
store_id,demand,predicted_demand,demand_p10,demand_p50,demand_p90,time_window_start,time_window_end,lat,lon,feature_score
101,25,27,22,27,31,480,1080,22.3193,114.1694,0.68
102,18,19,16,19,23,540,1080,22.3280,114.1800,0.55
```

## 对接来源说明

### 数据工程同学

如果提供门店聚合后的日级需求文件，只需满足最小输入字段即可。

### 预测同学

如果已经有 P10/P50/P90 输出，路径优化会直接用这些字段生成鲁棒场景，无需额外转换。

### DFI 真实数据

如果使用工作区根目录的 `DFI.zip`，可以不先生成 CSV，直接通过：

```python
from src.data_interface import load_dfi_zip_as_forecast_data

df = load_dfi_zip_as_forecast_data("../DFI.zip", top_n_stores=15)
```

## 输出去向

此目录下的数据最终会被转换为：

1. `prepare_vrp_input()` 输入
2. `solve_vrp()` 求解输入
3. Planning API 的 `schedules` / `map_data` 输出