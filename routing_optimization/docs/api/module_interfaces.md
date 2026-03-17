# 模块接口文档 - Stage 2

路径优化与其他成员模块的对接字段。

## 核心抽象接口

### IDataFetcher

- `fetch_weather_data(date_range, locations)`
- `fetch_geospatial_data(bounding_box)`
- `fetch_business_data(date_range, data_type)`
- `get_config()`
- `test_connection()`

### IDemandForecaster

- `train(historical_data, external_features)`
- `predict(future_dates, store_ids, sku_ids, external_features)`
- `evaluate(actual_data, forecast_data)`
- `get_model_info()`

### IRoutingOptimizer

- `optimize_routes(stores, demands, vehicles, distance_calculator, time_windows, capacity_constraints)`
- `evaluate_routes(route_plans, actual_performance)`
- `robust_optimization(stores, demand_scenarios, vehicles, distance_calculator, robustness_level)`

### ISLAPredictor

- `predict_pickup_time(order_info, route_plan, store_processing_time_model)`
- `calculate_sla_probability(promised_time, predicted_time, uncertainty)`

## Stage 2 路径优化输入接口

### 数据工程 -> 路径优化

最小输入表结构：

| 字段 | 类型 | 必需 |
|------|------|------|
| `store_id` | int/string | 是 |
| `demand` | float | 是 |
| `time_window_start` | int | 是 |
| `time_window_end` | int | 是 |
| `lat` | float | 推荐 |
| `lon` | float | 推荐 |

### 预测 -> 路径优化

增强字段：

| 字段 | 类型 | 必需 | 用途 |
|------|------|------|------|
| `predicted_demand` | float | 否 | 点预测 |
| `demand_p10` | float | 否 | 低需求场景 |
| `demand_p50` | float | 否 | 中位场景 |
| `demand_p90` | float | 否 | 高需求场景 |
| `feature_score` | float | 否 | 学习增强缩放 |

### DFI 真实数据 -> 路径优化

如果数据源是 `DFI.zip`，可以通过 `load_dfi_zip_as_forecast_data()` 适配为上述统一结构，无需其他模块额外转换。

## Stage 2 路径优化输出接口

### 算法标准输出

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

### Planning API 输出

`POST /api/planning/routes/optimize`

请求：

```json
{
	"use_real_data": true,
	"zip_path": null,
	"target_date": null,
	"top_n_stores": 15,
	"num_vehicles": null,
	"vehicle_capacity": null,
	"use_robust": true,
	"time_limit": 10,
	"use_haversine": true,
	"update_schedules": true
}
```

响应：

```json
{
	"success": true,
	"message": "路线优化完成",
	"data": {
		"schedules": [],
		"date": "YYYY-MM-DD",
		"optimization_summary": {},
		"optimization_result": {},
		"map_data": {}
	}
}
```

## 与前端的稳定字段约定

### schedules

前端调度页依赖以下字段：

| 字段 | 说明 |
|------|------|
| `vehicle_id` | 车辆编号 |
| `driver_name` | 司机名 |
| `driver_phone` | 司机电话 |
| `departure_time` | 发车时间 |
| `departure_window` | 发车区间 |
| `store_list` | 门店序列 |
| `store_names` | 门店名称 |
| `estimated_duration_min` | 预计时长 |
| `estimated_cost` | 预计成本 |
| `status` | 调度状态 |

### map_data

地图页依赖以下字段：

| 字段路径 | 说明 |
|----------|------|
| `map_data.dc_location` | 配送中心位置 |
| `map_data.store_locations` | 门店点位 |
| `map_data.routes` | 路线路径 |
| `map_data.geojson` | GeoJSON 绘制数据 |

## 与 SLA 模块的后续对接点

SLA 模块后续可从路径优化结果中直接取用：

1. 路径顺序
2. 到达时间序列
3. 未服务门店列表
4. 总时长与总距离
