# 模块接口文档

## 核心接口

### IDataFetcher (数据获取接口)
- `fetch_weather_data(date_range, locations)`: 获取天气数据
- `fetch_geospatial_data(bounding_box)`: 获取地理数据
- `fetch_business_data(date_range, data_type)`: 获取业务数据
- `get_config()`: 获取配置信息
- `test_connection()`: 测试连接

### IDistanceCalculator (距离计算接口)
- `calculate_distance_matrix(origins, destinations, mode)`: 计算距离矩阵
- `get_provider_name()`: 获取提供商名称
- `get_cost_per_request()`: 获取请求成本

### IDemandForecaster (需求预测接口)
- `train(historical_data, external_features)`: 训练模型
- `predict(future_dates, store_ids, sku_ids, external_features)`: 进行预测
- `evaluate(actual_data, forecast_data)`: 评估模型
- `get_model_info()`: 获取模型信息

### IInventoryOptimizer (库存优化接口)
- `calculate_safety_stock(demand_forecasts, service_level, lead_time_days)`: 计算安全库存
- `optimize_inventory_allocation(current_inventory, demand_forecasts, warehouse_capacity, costs)`: 优化库存分配
- `generate_replenishment_plan(safety_stocks, current_inventory, min_order_qty, batch_sizes)`: 生成补货计划

### IRoutingOptimizer (路径优化接口)
- `optimize_routes(stores, demands, vehicles, distance_calculator, time_windows, capacity_constraints)`: 优化路径
- `evaluate_routes(route_plans, actual_performance)`: 评估路线
- `robust_optimization(stores, demand_scenarios, vehicles, distance_calculator, robustness_level)`: 鲁棒优化

### ISLAPredictor (SLA预测接口)
- `predict_pickup_time(order_info, route_plan, store_processing_time_model)`: 预测取货时间
- `calculate_sla_probability(promised_time, predicted_time, uncertainty)`: 计算SLA概率

### IVisualization (可视化接口)
- `create_dashboard(data_sources, layout_config)`: 创建仪表板
- `plot_routes(route_plans, store_locations, map_provider)`: 绘制路线图
