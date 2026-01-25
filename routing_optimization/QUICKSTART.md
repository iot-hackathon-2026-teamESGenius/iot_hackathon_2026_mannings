# Routing Optimization - Quick Start Guide

## 环境搭建 | Environment Setup

### 使用 Conda (推荐)
```bash
conda create -n routing_opt python=3.10
conda activate routing_opt
pip install ortools pandas numpy
```

### 使用 pip
```bash
python -m venv routing_env
# Windows
routing_env\Scripts\activate
# Linux/Mac
source routing_env/bin/activate

pip install -r requirements.txt
```

## 运行示例 | Running Examples

### 1. 简单演示 (3个门店)
```bash
cd routing_optimization/demo
python run_demo.py
# 选择: 1
```

### 2. 完整演示 (7个门店 + 鲁棒优化)
```bash
cd routing_optimization/demo
python run_demo.py
# 选择: 2
```

## 自定义数据 | Custom Data

### 方法1: 使用CSV文件
```python
from src.data_interface import load_forecast_data, prepare_vrp_input

# 加载数据
df = load_forecast_data("data/forecast_input/your_data.csv")

# 准备VRP输入
depot = (40.7128, -74.0060)
vrp_input = prepare_vrp_input(df, depot, vehicle_capacity=100, num_vehicles=5)
```

### 方法2: 直接构建字典
```python
vrp_input = {
    'depot': {'lat': 40.7128, 'lon': -74.0060},
    'stores': [
        {
            'id': 1,
            'demand': 20,
            'time_window': (480, 1080),  # 8:00 AM - 6:00 PM
            'lat': 40.75,
            'lon': -74.00
        }
    ],
    'num_vehicles': 3,
    'vehicle_capacity': 100
}
```

## 求解VRP | Solving VRP

### 标准优化
```python
from src.solver import solve_vrp, format_solution_output

solution = solve_vrp(vrp_input, use_robust=False, time_limit=30)
print(format_solution_output(solution))
```

### 鲁棒优化 (创新点)
```python
solution = solve_vrp(vrp_input, use_robust=True, time_limit=30)
print(format_solution_output(solution))
```

## 输出格式 | Output Format

### 控制台输出
- 总距离、车辆数、计算时间
- 每条路线的详细序列
- SLA违反情况
- 场景对比 (鲁棒优化)

### 导出数据
```python
from src.solver import export_solution_to_dict
export_data = export_solution_to_dict(solution)
# export_data 可直接传递给可视化
```

## 配置参数 | Configuration

编辑 `src/config.py` 修改:
- 车辆容量和数量
- 时间窗口设置
- OR-Tools搜索策略
- 鲁棒优化参数
- SLA惩罚权重

## 故障排除 | Troubleshooting

### ImportError: No module named 'ortools'
```bash
pip install ortools
```

### 无可行解
- 检查总需求是否超过总容量
- 放宽时间窗口约束
- 增加车辆数量

### 求解时间过长
- 减少 `time_limit` 参数
- 使用更快的搜索策略
- 减少场景数量 (鲁棒优化)

