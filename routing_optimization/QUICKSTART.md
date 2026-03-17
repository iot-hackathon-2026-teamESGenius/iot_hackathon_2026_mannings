# Routing Optimization - Quick Start Guide (Stage 2)

## 环境

### Conda

```bash
conda create -n routing_opt python=3.10
conda activate routing_opt
pip install -r requirements.txt
pip install fastapi
```

### pip / venv

```bash
python -m venv routing_env
routing_env\Scripts\activate
pip install -r requirements.txt
pip install fastapi
```

## 最快跑通方式

### 1. 最小样例验证

```bash
cd routing_optimization
python validate_experiment.py
```

### 2. DFI 真实数据验证

```bash
cd routing_optimization
python demo/run_dfi_demo.py
```

这个脚本会先跑最小样例，再跑 DFI.zip 的真实数据适配流程。

### 3. 三算法对比实验

```bash
cd routing_optimization
python run_experiment.py
```

## 输入数据接口

### 最小必需字段

```python
[
    {
        "store_id": 101,
        "demand": 25.0,
        "time_window_start": 480,
        "time_window_end": 1080,
        "lat": 22.3193,
        "lon": 114.1694,
    }
]
```

### 预测增强字段

```python
[
    {
        "predicted_demand": 27.0,
        "demand_p10": 22.0,
        "demand_p50": 27.0,
        "demand_p90": 31.0,
        "feature_score": 0.68,
    }
]
```

## 求解接口

### Python 调用

```python
from src.data_interface import load_forecast_data, prepare_vrp_input
from src.solver import solve_vrp, export_solution_to_dict

df = load_forecast_data("data/forecast_input/your_data.csv")
vrp_input = prepare_vrp_input(df, (22.3700, 114.1130), vehicle_capacity=100, num_vehicles=5)
solution = solve_vrp(vrp_input, use_robust=True, time_limit=10)
payload = export_solution_to_dict(solution)
```

### Planning API 调用

```bash
cd routing_optimization
uvicorn src.api.main:app --host 0.0.0.0 --port 8000 --reload
```

请求示例：

```json
POST /api/planning/routes/optimize
{
  "use_real_data": true,
  "top_n_stores": 15,
  "time_limit": 10,
  "use_robust": true,
  "update_schedules": true
}
```

响应中前端重点使用字段：

1. `data.schedules`
2. `data.optimization_summary`
3. `data.optimization_result`
4. `data.map_data`

## 关键配置

编辑 [routing_optimization/src/config.py](routing_optimization/src/config.py)：

1. `DEMAND_RATIOS`
2. `ROBUST_SELECTION_CRITERION`
3. `ROBUST_SELECTION_WEIGHTS`
4. `ROBUST_ENABLE_PARALLEL`
5. `ROBUST_PARALLEL_WORKERS`

当前支持的鲁棒选择策略：

1. `min_max_distance`
2. `min_avg_distance`
3. `min_sla_violation`
4. `weighted_sum`
5. `pareto`

## 与其他成员接口

### 预测模块

预测模块只要输出统一 DataFrame，即可直接接入当前路由优化。

### 数据工程

若原始数据是 DFI.zip，可直接通过 `load_dfi_zip_as_forecast_data()` 转换；若是其他 ETL 结果，只需对齐字段名。

### 前端 / 可视化

前端无需理解内部求解结构，直接消费 Planning API 返回的 `schedules` 和 `map_data` 即可。

## 常见问题

### 没有可行解

优先检查：

1. 总需求是否大于总车辆容量。
2. 时间窗是否过紧。
3. 门店数量是否远大于车辆数。

### 真实数据距离异常小或异常大

优先检查：

1. 是否使用了真实坐标。
2. 是否启用了 Haversine 距离。
3. 是否仍在使用适配器生成的伪坐标联调。

