
# Mannings SLA 优化系统 - 完整开发指南

## 项目概述

### 项目简介
**Mannings SLA 优化系统**是为 DFI Retail Group - Mannings 开发的端到端门店取货服务等级协议（Service Level Agreement）优化解决方案。系统通过集成 AI/ML 预测模型和运筹优化算法，提升顾客取货体验并控制运营总成本。

### 核心目标
- 📈 **提升 SLA 达成率**：从预测的 85% 提升至 95%
- ⏱️ **缩短取货时间**：平均取货时间减少 15%
- 💰 **优化运营成本**：运输成本降低 20%
- 🔍 **增强决策透明度**：提供实时可视化和预测分析

### 技术架构特点
- 🔌 **可插拔模块化设计**：每个功能模块可独立开发和替换
- 📦 **接口驱动开发**：标准化接口确保模块兼容性
- ⚙️ **配置驱动部署**：通过配置文件切换不同实现
- 🔄 **事件驱动架构**：支持实时数据处理和响应
- 🧪 **全面测试覆盖**：单元测试、集成测试和端到端测试

---

## 目录
1. [开发环境设置](#开发环境设置)
2. [项目结构说明](#项目结构说明)
3. [模块化架构详解](#模块化架构详解)
4. [核心接口规范](#核心接口规范)
5. [模块开发指南](#模块开发指南)
6. [数据管理策略](#数据管理策略)
7. [测试策略](#测试策略)
8. [代码质量与规范](#代码质量与规范)
9. [协作开发流程](#协作开发流程)
10. [部署与运维](#部署与运维)
11. [故障排查](#故障排查)
12. [附录](#附录)

---

## 开发环境设置

### 系统要求
- **操作系统**：Ubuntu 20.04+/macOS 10.15+/Windows 10+（推荐 Ubuntu）
- **Python 版本**：3.9.x（推荐 3.9.16）
- **内存**：最低 8GB，推荐 16GB
- **存储**：最低 10GB 可用空间
- **网络**：稳定的互联网连接（用于 API 调用）

### 快速设置（5分钟完成）

#### 方法一：使用自动设置脚本（推荐）
```bash
# 1. 克隆仓库
git clone https://github.com/iot-hackathon-2026-teamESGenius/iot_hackathon_2026_mannings.git
cd iot_hackathon_2026_mannings

# 2. 运行自动设置脚本
bash scripts/setup_conda_environment.sh

# 3. 激活环境
conda activate mannings-sla

# 4. 验证环境
python scripts/verify_environment.py
```

#### 方法二：手动设置
```bash
# 1. 克隆仓库
git clone https://github.com/iot-hackathon-2026-teamESGenius/iot_hackathon_2026_mannings.git
cd iot_hackathon_2026_mannings

# 2. 安装 Miniconda（如未安装）
wget https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh
bash Miniconda3-latest-Linux-x86_64.sh -b -p $HOME/miniconda
export PATH="$HOME/miniconda/bin:$PATH"

# 3. 创建 Conda 环境
conda env create -f environment.yml
conda activate mannings-sla

# 4. 验证环境
python scripts/verify_environment.py
```

### 启动服务

环境配置完成后，可以启动以下服务：

#### REST API服务（前端调用）
```bash
uvicorn src.api.main:app --host 0.0.0.0 --port 8000 --reload
```
- **API文档**：http://localhost:8000/docs
- **健康检查**：http://localhost:8000/health

#### Streamlit可视化看板（内部调试）
```bash
streamlit run src/visualization/dashboard/app.py
```
- **访问地址**：http://localhost:8501

#### 路径优化Demo
```bash
python -m src.modules.routing.implementations.demo
```

### 环境变量配置
```bash
# 复制环境变量模板
cp .env.example .env

# 编辑 .env 文件，填入以下内容：
GOOGLE_MAPS_API_KEY=your_google_maps_api_key_here
HKO_API_KEY=your_hong_kong_observatory_api_key_here
LOG_LEVEL=INFO
DEBUG=False
```

### IDE 配置
#### VS Code 推荐配置
1. 安装以下扩展：
   - Python (Microsoft)
   - Pylance
   - Black Formatter
   - Python Test Explorer
   - GitLens

2. 工作区设置（`.vscode/settings.json`）：
```json
{
    "python.defaultInterpreterPath": "${workspaceFolder}/envs/mannings-sla/bin/python",
    "python.linting.enabled": true,
    "python.linting.flake8Enabled": true,
    "python.formatting.provider": "black",
    "python.formatting.blackArgs": ["--line-length", "88"],
    "python.testing.pytestEnabled": true,
    "python.testing.unittestEnabled": false,
    "editor.formatOnSave": true,
    "editor.codeActionsOnSave": {
        "source.organizeImports": true
    },
    "files.exclude": {
        "**/__pycache__": true,
        "**/*.pyc": true,
        "**/.pytest_cache": true
    }
}
```

#### PyCharm 配置
1. 项目解释器：选择 Conda 环境 `mannings-sla`
2. 启用 Black 代码格式化
3. 配置 pytest 为测试运行器
4. 启用类型提示检查

---

## 项目结构说明

```
iot_hackathon_2026_mannings/
├── config/                    # 配置文件
│   ├── modules.yaml          # 模块注册配置
│   ├── agents.yaml           # 智能体配置 (Stage 2)
│   ├── environment.yaml      # 环境配置
│   └── pipelines/            # 流水线配置
│       └── daily_optimization.yaml
├── src/                      # 源代码
│   ├── core/                 # 核心框架
│   │   ├── interfaces.py     # 所有模块接口定义
│   │   ├── module_registry.py  # 模块注册表
│   │   ├── orchestrator.py   # 流水线协调器
│   │   └── __init__.py
│   ├── api/                  # REST API服务层 (新增)
│   │   ├── main.py           # FastAPI入口
│   │   └── routers/          # API路由
│   │       ├── auth.py       # 认证服务
│   │       ├── dashboard.py  # 数据看板
│   │       ├── forecast.py   # 预测服务
│   │       ├── planning.py   # 决策规划
│   │       └── sla.py        # SLA服务
│   ├── agents/               # 智能体接口 (Stage 2预留)
│   │   ├── interfaces.py     # Agent接口定义
│   │   └── __init__.py
│   ├── modules/              # 可插拔模块
│   │   ├── data/            # 数据获取模块
│   │   │   ├── interfaces.py
│   │   │   └── implementations/
│   │   │       └── simulated_data_fetcher.py
│   │   ├── distance/        # 距离计算模块
│   │   │   ├── interfaces.py
│   │   │   └── implementations/
│   │   │       ├── euclidean_calculator.py
│   │   │       └── google_distance_matrix.py
│   │   ├── forecasting/     # 预测模块
│   │   ├── inventory/       # 库存优化模块
│   │   ├── routing/         # 路径优化模块 ⭐
│   │   │   ├── interfaces.py
│   │   │   └── implementations/
│   │   │       ├── ortools_optimizer.py      # Baseline CVRPTW
│   │   │       ├── robust_optimizer.py       # 鲁棒优化器 (创新点)
│   │   │       ├── scenario_generator.py     # 情景生成器
│   │   │       └── demo.py                   # Demo脚本
│   │   ├── sla/             # SLA预测模块
│   │   └── visualization/   # 可视化模块
│   ├── main.py              # 主应用入口
│   └── visualization/dashboard/  # Streamlit仪表板
│       └── app.py
├── tests/                    # 测试代码
│   ├── core/                # 核心框架测试
│   ├── modules/             # 模块测试
│   └── integration/         # 集成测试
├── data/                    # 数据目录
│   ├── official/           # 官方数据
│   ├── synthetic/          # 模拟数据
│   ├── processed/          # 处理后的数据
│   ├── external/           # 外部数据
│   └── routing/            # 路径优化数据 (新增)
│       └── forecast_input/  # 预测输入接口
├── outputs/                 # 输出目录
│   ├── models/             # 模型输出
│   ├── reports/            # 报告输出
│   └── visualizations/     # 可视化输出
├── docs/                    # 文档
├── notebooks/              # Jupyter Notebooks
├── scripts/                # 工具脚本
├── logs/                   # 日志文件
├── environment.yml         # Conda环境配置
├── requirements.txt        # Python依赖
├── requirements-dev.txt    # 开发依赖
├── Dockerfile             # Docker配置
├── docker-compose.yml     # Docker Compose配置
└── README.md              # 项目说明
```

### 关键目录说明

#### 1. `src/core/` - 核心框架
- `interfaces.py`：定义所有模块必须实现的接口
- `module_registry.py`：动态模块加载和注册系统
- `orchestrator.py`：协调各个模块执行工作流

#### 2. `src/api/` - REST API服务层 (新增)
为前端(Vue3+uniapp)提供HTTP接口：
- `main.py`：FastAPI应用入口
- `routers/auth.py`：认证服务（登录/Token验证）
- `routers/dashboard.py`：KPI数据看板
- `routers/forecast.py`：需求预测服务
- `routers/planning.py`：补货计划/车队调度
- `routers/sla.py`：SLA预警服务

#### 3. `src/agents/` - 智能体接口 (Stage 2预留)
第二阶段AI Agent开发接口：
- `IDemandForecastAgent`：需求预测智能体
- `IInventoryOptimizationAgent`：库存优化智能体
- `IRoutingDispatchAgent`：路径调度智能体
- `ISLAAlertAgent`：SLA预警智能体
- `IMultiAgentCoordinator`：多Agent协调器

#### 4. `src/modules/` - 可插拔模块
每个模块包含：
- `interfaces.py`：模块特定的接口定义（继承核心接口）
- `implementations/`：具体实现类
- `__init__.py`：模块导出

#### 5. `src/modules/routing/` - 路径优化模块 ⭐
包含鲁棒优化算法（项目创新点）：
- `ortools_optimizer.py`：Baseline CVRPTW实现
- `robust_optimizer.py`：基于多情景的鲁棒优化
- `scenario_generator.py`：从预测结果生成需求情景

#### 6. `config/` - 配置管理
- `modules.yaml`：定义可用模块及其配置
- `agents.yaml`：智能体系统配置 (Stage 2)
- `environment.yaml`：系统级配置参数
- `pipelines/`：预定义的工作流配置

#### 7. `tests/` - 测试代码
- 遵循与 `src/` 相同的目录结构
- 每个模块都有对应的测试目录
- 包含单元测试、集成测试和端到端测试

---

## 模块化架构详解

### 架构设计原则

#### 1. 单一职责原则
每个模块只负责一个特定的功能域：
- **数据获取模块**：从各种数据源获取数据
- **距离计算模块**：计算位置之间的距离和时间
- **预测模块**：进行需求和时间预测
- **优化模块**：解决各种优化问题
- **可视化模块**：展示数据和结果

#### 2. 接口隔离原则
模块间通过标准化的接口通信，不直接依赖具体实现：
```python
# 示例：距离计算器接口
class IDistanceCalculator(ABC):
    @abstractmethod
    def calculate_distance_matrix(self, origins, destinations, mode="driving"):
        pass
    
    @abstractmethod
    def get_provider_name(self):
        pass
```

#### 3. 依赖反转原则
高层模块不依赖低层模块，都依赖抽象接口：
```python
class RoutingOptimizer:
    def __init__(self, distance_calculator: IDistanceCalculator):
        # 依赖抽象接口，而不是具体实现
        self.distance_calculator = distance_calculator
```

#### 4. 可替换性原则
任何模块的实现可以轻松替换，只需：
1. 实现相同的接口
2. 更新配置文件

### 模块注册系统

#### 工作原理
1. **配置加载**：系统启动时加载 `config/modules.yaml`
2. **动态导入**：根据需要动态导入模块类
3. **依赖注入**：自动解析和注入模块依赖
4. **生命周期管理**：支持单例和非单例模式

#### 配置文件示例
```yaml
modules:
  data_fetcher:
    class: "src.modules.data.implementations.simulated_data_fetcher.SimulatedDataFetcher"
    config:
      data_path: "data/synthetic/"
      cache_enabled: true
    enabled: true
    singleton: true
  
  distance_calculator:
    class: "src.modules.distance.implementations.google_distance_matrix.GoogleDistanceMatrixCalculator"
    config:
      api_key: "${GOOGLE_MAPS_API_KEY}"
    enabled: false  # 默认禁用，需要时启用
    singleton: true
```

#### 模块获取示例
```python
from src.core.module_registry import ModuleRegistry

# 创建注册表
registry = ModuleRegistry("config/modules.yaml")

# 获取模块实例
data_fetcher = registry.get_module("data_fetcher")
distance_calculator = registry.get_module("distance_calculator")
```

### 工作流协调器

#### 流水线执行
```python
from src.core.orchestrator import PipelineOrchestrator

# 创建协调器
orchestrator = PipelineOrchestrator(registry)

# 执行流水线
result = orchestrator.execute_pipeline({
    'name': 'daily_optimization',
    'modules': ['data_fetcher', 'demand_forecaster', 'routing_optimizer'],
    'parameters': {
        'date_range': ['2024-01-25', '2024-01-31'],
        'store_ids': ['M001', 'M002', 'M003']
    }
})
```

#### 流水线配置示例
```yaml
# config/pipelines/daily_optimization.yaml
name: "daily_store_pickup_optimization"
schedule: "0 2 * * *"  # 每天2:00 AM
modules:
  - data_fetcher
  - demand_forecaster
  - routing_optimizer
  - sla_predictor

parameters:
  date_range: ["2024-01-25", "2024-01-31"]
  store_ids: ["M001", "M002", "M003", "M004", "M005"]
  forecast_horizon_days: 7

output:
  formats: ["json", "csv"]
  path: "outputs/daily_optimization/"
```

---

## 核心接口规范

### 基础数据类型

#### StoreInfo - 门店信息
```python
@dataclass
class StoreInfo:
    store_id: str
    name: str
    address: str
    latitude: float
    longitude: float
    time_window_start: str  # "09:00"
    time_window_end: str    # "18:00"
    capacity: float
```

#### DemandForecast - 需求预测
```python
@dataclass
class DemandForecast:
    store_id: str
    sku_id: str
    date: str
    forecast_demand: float
    lower_bound: float
    upper_bound: float
    confidence: float
```

#### RoutePlan - 路线规划
```python
@dataclass
class RoutePlan:
    route_id: str
    vehicle_id: str
    store_sequence: List[str]
    arrival_times: List[str]
    departure_times: List[str]
    distances_km: List[float]
    total_distance_km: float
    total_duration_min: float
    total_cost: float
    sla_risk_score: float
```

### 核心接口定义

#### IDataFetcher - 数据获取接口
```python
class IDataFetcher(ABC):
    @abstractmethod
    def fetch_weather_data(self, date_range: tuple, locations: List[tuple]) -> pd.DataFrame:
        """获取天气数据"""
        pass
    
    @abstractmethod
    def fetch_geospatial_data(self, bounding_box: tuple) -> Dict:
        """获取地理空间数据"""
        pass
    
    @abstractmethod
    def fetch_business_data(self, date_range: tuple, data_type: str) -> pd.DataFrame:
        """获取业务数据"""
        pass
    
    @abstractmethod
    def get_config(self) -> Dict[str, Any]:
        """获取数据源配置"""
        pass
    
    @abstractmethod
    def test_connection(self) -> bool:
        """测试数据源连接"""
        pass
```

#### IDistanceCalculator - 距离计算接口
```python
class IDistanceCalculator(ABC):
    @abstractmethod
    def calculate_distance_matrix(self, 
                                origins: List[tuple], 
                                destinations: List[tuple],
                                mode: str = "driving") -> pd.DataFrame:
        """计算距离矩阵"""
        pass
    
    @abstractmethod
    def get_provider_name(self) -> str:
        """获取提供商名称"""
        pass
    
    @abstractmethod
    def get_cost_per_request(self) -> float:
        """获取每次请求的成本"""
        pass
```

#### IDemandForecaster - 需求预测接口
```python
class IDemandForecaster(ABC):
    @abstractmethod
    def train(self, 
             historical_data: pd.DataFrame,
             external_features: Dict[str, pd.DataFrame] = None) -> Dict[str, Any]:
        """训练预测模型"""
        pass
    
    @abstractmethod
    def predict(self,
               future_dates: List[str],
               store_ids: List[str],
               sku_ids: List[str],
               external_features: Dict[str, pd.DataFrame] = None) -> List[DemandForecast]:
        """进行需求预测"""
        pass
    
    @abstractmethod
    def evaluate(self, 
                actual_data: pd.DataFrame,
                forecast_data: pd.DataFrame) -> Dict[str, float]:
        """评估预测性能"""
        pass
```

#### IInventoryOptimizer - 库存优化接口
```python
class IInventoryOptimizer(ABC):
    @abstractmethod
    def calculate_safety_stock(self,
                              demand_forecasts: List[DemandForecast],
                              service_level: float = 0.95,
                              lead_time_days: int = 2) -> Dict[str, float]:
        """计算安全库存"""
        pass
    
    @abstractmethod
    def optimize_inventory_allocation(self,
                                    current_inventory: Dict[str, float],
                                    demand_forecasts: List[DemandForecast],
                                    warehouse_capacity: Dict[str, float],
                                    costs: Dict[str, float]) -> Dict[str, Any]:
        """优化库存分配"""
        pass
```

#### IRoutingOptimizer - 路径优化接口
```python
class IRoutingOptimizer(ABC):
    @abstractmethod
    def optimize_routes(self,
                       stores: List[StoreInfo],
                       demands: Dict[str, float],
                       vehicles: List[Any],
                       distance_calculator: IDistanceCalculator,
                       time_windows: bool = True,
                       capacity_constraints: bool = True) -> List[RoutePlan]:
        """优化配送路径"""
        pass
    
    @abstractmethod
    def robust_optimization(self,
                          stores: List[StoreInfo],
                          demand_scenarios: List[Dict[str, float]],
                          vehicles: List[Any],
                          distance_calculator: IDistanceCalculator,
                          robustness_level: float = 0.9) -> List[RoutePlan]:
        """鲁棒优化"""
        pass
```

#### ISLAPredictor - SLA预测接口
```python
class ISLAPredictor(ABC):
    @abstractmethod
    def predict_pickup_time(self,
                           order_info: Dict[str, Any],
                           route_plan: RoutePlan,
                           store_processing_time_model: Any = None) -> Dict[str, Any]:
        """预测取货时间"""
        pass
    
    @abstractmethod
    def calculate_sla_probability(self,
                                 promised_time: datetime,
                                 predicted_time: datetime,
                                 uncertainty: float = 0.1) -> float:
        """计算SLA达成概率"""
        pass
```

#### IVisualization - 可视化接口
```python
class IVisualization(ABC):
    @abstractmethod
    def create_dashboard(self,
                        data_sources: Dict[str, Any],
                        layout_config: Dict[str, Any] = None) -> Any:
        """创建仪表板"""
        pass
    
    @abstractmethod
    def plot_routes(self,
                   route_plans: List[RoutePlan],
                   store_locations: Dict[str, tuple],
                   map_provider: str = "openstreetmap") -> Any:
        """绘制路线图"""
        pass
```

---

## 模块开发指南

### 创建新模块的步骤

#### 步骤 1：确定模块类型
首先确定新模块属于哪个功能域：
- `data/` - 数据获取
- `distance/` - 距离计算
- `forecasting/` - 预测
- `inventory/` - 库存优化
- `routing/` - 路径优化
- `sla/` - SLA预测
- `visualization/` - 可视化

#### 步骤 2：实现接口
在对应目录创建实现文件：

```python
# src/modules/distance/implementations/my_new_calculator.py
from typing import List, Tuple, Dict, Any
import pandas as pd
from ...interfaces import IDistanceCalculator

class MyNewDistanceCalculator(IDistanceCalculator):
    """新的距离计算器实现"""
    
    def __init__(self, custom_param: str = "default"):
        self.custom_param = custom_param
        
    def calculate_distance_matrix(self, 
                                 origins: List[Tuple[float, float]], 
                                 destinations: List[Tuple[float, float]], 
                                 mode: str = "driving") -> pd.DataFrame:
        # 实现距离矩阵计算逻辑
        distances = []
        for orig in origins:
            row = []
            for dest in destinations:
                # 计算距离
                distance = self._calculate_distance(orig, dest)
                row.append(distance)
            distances.append(row)
        
        return pd.DataFrame(distances)
    
    def get_provider_name(self) -> str:
        return "My New Distance Calculator"
    
    def get_cost_per_request(self) -> float:
        return 0.0  # 本地计算无成本
    
    def _calculate_distance(self, point1: Tuple[float, float], 
                           point2: Tuple[float, float]) -> float:
        """私有方法：计算两点间距离"""
        # 实现具体距离计算逻辑
        import math
        lat1, lon1 = point1
        lat2, lon2 = point2
        # 使用 Haversine 公式
        R = 6371.0  # 地球半径（公里）
        # ... 计算代码 ...
        return distance
```

#### 步骤 3：注册模块
在 `config/modules.yaml` 中添加新模块配置：

```yaml
modules:
  my_new_calculator:
    class: "src.modules.distance.implementations.my_new_calculator.MyNewDistanceCalculator"
    config:
      custom_param: "my_value"
    enabled: true
    singleton: true
```

#### 步骤 4：编写单元测试
创建对应的测试文件：

```python
# tests/modules/distance/test_my_new_calculator.py
import pytest
import pandas as pd
from src.modules.distance.implementations.my_new_calculator import MyNewDistanceCalculator

class TestMyNewDistanceCalculator:
    """测试新的距离计算器"""
    
    def test_initialization(self):
        """测试初始化"""
        calculator = MyNewDistanceCalculator(custom_param="test")
        assert calculator.custom_param == "test"
        assert calculator.get_provider_name() == "My New Distance Calculator"
    
    def test_calculate_distance_matrix(self):
        """测试距离矩阵计算"""
        calculator = MyNewDistanceCalculator()
        origins = [(22.3193, 114.1694)]
        destinations = [(22.3287, 114.1883)]
        
        result = calculator.calculate_distance_matrix(origins, destinations)
        
        assert isinstance(result, pd.DataFrame)
        assert result.shape == (1, 1)
        assert result.iloc[0, 0] > 0  # 距离应为正数
    
    def test_cost_per_request(self):
        """测试请求成本"""
        calculator = MyNewDistanceCalculator()
        assert calculator.get_cost_per_request() == 0.0
```

#### 步骤 5：更新文档
在 `docs/modules/` 中添加模块文档：

```markdown
# MyNewDistanceCalculator 模块文档

## 功能说明
提供基于自定义算法的距离计算功能。

## 配置参数
- `custom_param`：自定义参数，默认值为 "default"

## 使用方法
```python
from src.core.module_registry import ModuleRegistry

registry = ModuleRegistry()
calculator = registry.get_module("my_new_calculator")

# 计算距离矩阵
origins = [(22.3193, 114.1694), (22.3287, 114.1883)]
destinations = [(22.3372, 114.1521)]
result = calculator.calculate_distance_matrix(origins, destinations)
```

## 性能特点
- 计算精度：±100米
- 计算速度：1000点/秒
- 支持模式：driving, walking
```

### 模块开发最佳实践

#### 1. 保持接口兼容性
- 实现所有抽象方法
- 遵循类型提示
- 不修改接口签名

#### 2. 错误处理
```python
def calculate_distance_matrix(self, origins, destinations, mode="driving"):
    try:
        # 参数验证
        if not origins or not destinations:
            raise ValueError("Origins and destinations cannot be empty")
        
        if mode not in ["driving", "walking", "bicycling"]:
            raise ValueError(f"Unsupported mode: {mode}")
        
        # 业务逻辑
        return self._calculate_matrix(origins, destinations)
    
    except Exception as e:
        # 记录错误日志
        logging.error(f"Failed to calculate distance matrix: {e}")
        # 返回空DataFrame或抛出异常
        raise
```

#### 3. 配置管理
```python
class MyModule:
    def __init__(self, **config):
        # 设置默认配置
        default_config = {
            'param1': 'default1',
            'param2': 100,
            'param3': True
        }
        
        # 合并配置
        self.config = {**default_config, **config}
        
        # 验证配置
        self._validate_config()
    
    def _validate_config(self):
        if self.config['param2'] < 0:
            raise ValueError("param2 must be positive")
```

#### 4. 缓存实现
```python
class CachedDistanceCalculator(IDistanceCalculator):
    def __init__(self, cache_enabled=True, cache_size=1000):
        self.cache_enabled = cache_enabled
        self.cache = {}
        self.cache_size = cache_size
    
    def calculate_distance_matrix(self, origins, destinations, mode="driving"):
        cache_key = self._create_cache_key(origins, destinations, mode)
        
        if self.cache_enabled and cache_key in self.cache:
            return self.cache[cache_key]
        
        # 计算距离
        result = self._calculate_uncached(origins, destinations, mode)
        
        if self.cache_enabled:
            # 管理缓存大小
            if len(self.cache) >= self.cache_size:
                self._evict_oldest()
            self.cache[cache_key] = result
        
        return result
    
    def _create_cache_key(self, origins, destinations, mode):
        return f"{hash(str(origins))}_{hash(str(destinations))}_{mode}"
```

### 模块间通信

#### 1. 通过接口通信
```python
# 路由优化器使用距离计算器
class RoutingOptimizer(IRoutingOptimizer):
    def __init__(self, distance_calculator: IDistanceCalculator):
        self.distance_calculator = distance_calculator
    
    def optimize_routes(self, stores, demands, vehicles, **kwargs):
        # 计算距离矩阵
        locations = [(s.latitude, s.longitude) for s in stores]
        distance_matrix = self.distance_calculator.calculate_distance_matrix(
            origins=locations,
            destinations=locations
        )
        
        # 使用距离矩阵进行优化
        # ...
```

#### 2. 数据格式标准化
```python
# 使用标准化的数据类
from src.core.interfaces import StoreInfo, DemandForecast

# 创建门店信息
store = StoreInfo(
    store_id="M001",
    name="Mannings Central",
    address="Central, Hong Kong",
    latitude=22.3193,
    longitude=114.1694,
    time_window_start="09:00",
    time_window_end="18:00",
    capacity=1000
)

# 创建需求预测
forecast = DemandForecast(
    store_id="M001",
    sku_id="SKU001",
    date="2024-01-25",
    forecast_demand=150.5,
    lower_bound=120.4,
    upper_bound=180.6,
    confidence=0.95
)
```

#### 3. 错误传播
```python
def process_data(data_fetcher, demand_forecaster):
    try:
        # 获取数据
        weather_data = data_fetcher.fetch_weather_data(...)
        
        # 进行预测
        forecasts = demand_forecaster.predict(
            future_dates=...,
            store_ids=...,
            external_features={'weather': weather_data}
        )
        
        return forecasts
    
    except DataFetchError as e:
        # 数据获取错误
        logging.error(f"Data fetch failed: {e}")
        raise ProcessingError(f"Failed to process data: {e}")
    
    except PredictionError as e:
        # 预测错误
        logging.error(f"Prediction failed: {e}")
        raise ProcessingError(f"Failed to generate forecasts: {e}")
```

---

## 数据管理策略

### 数据目录结构
```
data/
├── official/          # 官方数据（从API获取）
│   ├── weather/
│   │   ├── 2024-01-25.csv
│   │   └── 2024-01-26.csv
│   └── geospatial/
│       └── hk_3d_map.geojson
├── synthetic/         # 模拟数据
│   ├── stores.csv
│   ├── skus.csv
│   ├── sales.csv
│   └── inventory.csv
├── processed/         # 处理后的数据
│   ├── features/
│   │   └── demand_features_2024-01.csv
│   └── models/
│       └── prophet_model.pkl
└── external/          # 外部数据源
    └── hk_population.csv
```

### 数据生成

#### 生成模拟数据
```bash
# 生成完整的模拟数据集
python scripts/generate_synthetic_data.py

# 生成特定类型的数据
python scripts/generate_synthetic_data.py --type stores --count 100
python scripts/generate_synthetic_data.py --type sales --days 30
```

#### 模拟数据脚本配置
```python
# 在脚本中配置数据生成参数
python scripts/generate_synthetic_data.py \
    --stores 320 \
    --skus 1000 \
    --start-date 2023-07-01 \
    --end-date 2024-01-24 \
    --output-dir data/synthetic/
```

### 数据验证

#### 数据质量检查
```python
# scripts/validate_data.py
import pandas as pd
from typing import List, Dict

class DataValidator:
    """数据验证器"""
    
    @staticmethod
    def validate_store_data(df: pd.DataFrame) -> List[str]:
        """验证门店数据"""
        issues = []
        
        # 检查必需列
        required_columns = ['store_id', 'latitude', 'longitude', 'time_window_start']
        missing = [col for col in required_columns if col not in df.columns]
        if missing:
            issues.append(f"Missing columns: {missing}")
        
        # 检查数据范围
        if 'latitude' in df.columns:
            if (df['latitude'] < 22.15).any() or (df['latitude'] > 22.55).any():
                issues.append("Latitude out of Hong Kong range")
        
        # 检查唯一性
        if df['store_id'].duplicated().any():
            issues.append("Duplicate store_ids found")
        
        return issues
    
    @staticmethod
    def validate_sales_data(df: pd.DataFrame) -> List[str]:
        """验证销售数据"""
        issues = []
        
        # 检查负值
        if 'demand' in df.columns and (df['demand'] < 0).any():
            issues.append("Negative demand values found")
        
        # 检查日期格式
        if 'date' in df.columns:
            try:
                pd.to_datetime(df['date'])
            except:
                issues.append("Invalid date format")
        
        return issues
```

#### 运行数据验证
```bash
# 验证所有数据文件
python scripts/validate_data.py --all

# 验证特定数据文件
python scripts/validate_data.py --file data/synthetic/stores.csv
```

### 数据处理流水线

#### 特征工程示例
```python
# src/modules/data/implementations/feature_engineer.py
import pandas as pd
import numpy as np
from datetime import datetime

class FeatureEngineer:
    """特征工程处理器"""
    
    def create_time_features(self, df: pd.DataFrame, date_column: str) -> pd.DataFrame:
        """创建时间特征"""
        df = df.copy()
        
        # 转换为datetime
        df['date'] = pd.to_datetime(df[date_column])
        
        # 提取时间特征
        df['year'] = df['date'].dt.year
        df['month'] = df['date'].dt.month
        df['day'] = df['date'].dt.day
        df['dayofweek'] = df['date'].dt.dayofweek
        df['weekofyear'] = df['date'].dt.isocalendar().week
        df['quarter'] = df['date'].dt.quarter
        df['is_weekend'] = df['dayofweek'].isin([5, 6]).astype(int)
        df['is_month_start'] = df['date'].dt.is_month_start.astype(int)
        df['is_month_end'] = df['date'].dt.is_month_end.astype(int)
        
        # 季节性特征
        df['sin_month'] = np.sin(2 * np.pi * df['month'] / 12)
        df['cos_month'] = np.cos(2 * np.pi * df['month'] / 12)
        
        return df
    
    def create_lag_features(self, df: pd.DataFrame, value_column: str, 
                           group_columns: List[str], lags: List[int]) -> pd.DataFrame:
        """创建滞后特征"""
        df = df.sort_values(['date'] + group_columns).copy()
        
        for lag in lags:
            df[f'{value_column}_lag_{lag}'] = df.groupby(group_columns)[value_column].shift(lag)
        
        return df
    
    def create_rolling_features(self, df: pd.DataFrame, value_column: str,
                               group_columns: List[str], windows: List[int]) -> pd.DataFrame:
        """创建滚动特征"""
        df = df.sort_values(['date'] + group_columns).copy()
        
        for window in windows:
            df[f'{value_column}_rolling_mean_{window}'] = (
                df.groupby(group_columns)[value_column]
                .rolling(window=window, min_periods=1)
                .mean()
                .reset_index(level=group_columns, drop=True)
            )
            
            df[f'{value_column}_rolling_std_{window}'] = (
                df.groupby(group_columns)[value_column]
                .rolling(window=window, min_periods=1)
                .std()
                .reset_index(level=group_columns, drop=True)
            )
        
        return df
```

---

## 测试策略

### 测试金字塔

```
        端到端测试 (10%)
            ↑
      集成测试 (20%)
            ↑
    单元测试 (70%)
```

### 单元测试

#### 测试目录结构
```
tests/
├── core/
│   └── test_module_registry.py
├── modules/
│   ├── data/
│   │   └── test_data_fetcher.py
│   ├── distance/
│   │   └── test_distance_calculators.py
│   └── ...
└── integration/
    └── test_pipeline_integration.py
```

#### 单元测试示例
```python
# tests/modules/distance/test_euclidean_calculator.py
import pytest
import pandas as pd
import numpy as np
from src.modules.distance.implementations.euclidean_calculator import EuclideanDistanceCalculator

class TestEuclideanDistanceCalculator:
    """测试欧几里得距离计算器"""
    
    @pytest.fixture
    def calculator(self):
        """测试夹具：创建计算器实例"""
        return EuclideanDistanceCalculator(cache_enabled=False)
    
    @pytest.fixture
    def sample_locations(self):
        """测试夹具：样本位置"""
        return [
            (22.3193, 114.1694),  # Central
            (22.3287, 114.1883),  # Wan Chai
            (22.3372, 114.1521)   # Kowloon Tong
        ]
    
    def test_initialization(self, calculator):
        """测试初始化"""
        assert calculator.cache_enabled == False
        assert calculator.get_provider_name() == "Euclidean Distance Calculator"
        assert calculator.get_cost_per_request() == 0.0
    
    def test_calculate_distance_matrix_shape(self, calculator, sample_locations):
        """测试距离矩阵形状"""
        origins = sample_locations[:2]
        destinations = sample_locations[1:]
        
        result = calculator.calculate_distance_matrix(origins, destinations)
        
        # 验证形状
        assert isinstance(result, pd.DataFrame)
        assert 'distance_km' in result.columns
        assert 'duration_min' in result.columns
        assert len(result) == len(origins) * len(destinations)
    
    def test_distance_values(self, calculator):
        """测试距离值合理性"""
        # 测试近距离点
        origin = [(22.3193, 114.1694)]
        destination = [(22.3194, 114.1695)]  # 约100米
        
        result = calculator.calculate_distance_matrix(origin, destination)
        distance = result['distance_km'].iloc[0]
        
        # 距离应该在合理范围内
        assert 0.09 < distance < 0.11  # 约100米
    
    def test_same_location_distance(self, calculator):
        """测试相同位置的距离为0"""
        location = [(22.3193, 114.1694)]
        
        result = calculator.calculate_distance_matrix(location, location)
        distance = result['distance_km'].iloc[0]
        
        # 相同位置距离应为0
        assert distance == 0.0
    
    def test_cache_functionality(self):
        """测试缓存功能"""
        calculator = EuclideanDistanceCalculator(cache_enabled=True)
        origins = [(22.3193, 114.1694)]
        destinations = [(22.3287, 114.1883)]
        
        # 第一次计算
        result1 = calculator.calculate_distance_matrix(origins, destinations)
        
        # 第二次计算应该使用缓存
        result2 = calculator.calculate_distance_matrix(origins, destinations)
        
        # 验证结果相同
        pd.testing.assert_frame_equal(result1, result2)
    
    @pytest.mark.parametrize("mode", ["driving", "walking", "bicycling"])
    def test_different_modes(self, calculator, sample_locations, mode):
        """测试不同交通模式"""
        origins = sample_locations[:1]
        destinations = sample_locations[1:2]
        
        result = calculator.calculate_distance_matrix(origins, destinations, mode=mode)
        
        # 距离应该相同（欧几里得距离不考虑模式）
        assert result['distance_km'].iloc[0] > 0
```

#### 参数化测试
```python
@pytest.mark.parametrize("input_data,expected", [
    ([(0, 0), (0, 1)], 111.32),  # 1度纬度 ≈ 111km
    ([(0, 0), (1, 0)], 111.32),  # 1度经度 ≈ 111km（在赤道）
    ([(22.3, 114.1), (22.3, 114.2)], 10.4),  # 香港范围内
])
def test_specific_distances(calculator, input_data, expected):
    """测试特定距离计算"""
    origins = [input_data[0]]
    destinations = [input_data[1]]
    
    result = calculator.calculate_distance_matrix(origins, destinations)
    distance = result['distance_km'].iloc[0]
    
    # 允许5%的误差
    assert abs(distance - expected) / expected < 0.05
```

### 集成测试

#### 模块间集成测试
```python
# tests/integration/test_data_pipeline.py
import pytest
from src.core.module_registry import ModuleRegistry
from src.core.orchestrator import PipelineOrchestrator

class TestDataPipelineIntegration:
    """数据流水线集成测试"""
    
    @pytest.fixture
    def registry(self):
        """创建模块注册表"""
        registry = ModuleRegistry("config/modules.yaml")
        return registry
    
    @pytest.fixture
    def orchestrator(self, registry):
        """创建协调器"""
        return PipelineOrchestrator(registry)
    
    def test_data_fetch_and_forecast(self, orchestrator):
        """测试数据获取和预测集成"""
        pipeline_config = {
            'name': 'test_pipeline',
            'modules': ['data_fetcher', 'demand_forecaster'],
            'date_range': ('2024-01-01', '2024-01-07'),
            'forecast_dates': ['2024-01-08', '2024-01-09'],
            'store_ids': ['M001', 'M002'],
            'sku_ids': ['SKU001'],
            'locations': [(22.3193, 114.1694)]
        }
        
        # 执行流水线
        result = orchestrator.execute_pipeline(pipeline_config)
        
        # 验证结果
        assert result['pipeline_name'] == 'test_pipeline'
        assert 'execution_time' in result
        assert 'results' in result
        assert 'demand_forecasts' in result['results']
        
        forecasts = result['results']['demand_forecasts']
        assert len(forecasts) > 0
        
        # 验证预测数据结构
        forecast = forecasts[0]
        assert hasattr(forecast, 'store_id')
        assert hasattr(forecast, 'sku_id')
        assert hasattr(forecast, 'date')
        assert hasattr(forecast, 'forecast_demand')
    
    def test_module_dependency_injection(self, registry):
        """测试模块依赖注入"""
        # 获取距离计算器
        distance_calculator = registry.get_module('distance_calculator')
        
        # 获取路由优化器（依赖距离计算器）
        routing_optimizer = registry.get_module('routing_optimizer')
        
        # 验证路由优化器可以使用距离计算器
        assert hasattr(routing_optimizer, 'distance_calculator')
        assert routing_optimizer.distance_calculator is not None
    
    def test_config_switching(self):
        """测试配置切换"""
        # 测试切换距离计算器
        registry = ModuleRegistry()
        
        # 注册两种距离计算器
        registry.register_module(
            module_name='calc_euclidean',
            module_class='src.modules.distance.implementations.euclidean_calculator.EuclideanDistanceCalculator',
            config={'cache_enabled': True}
        )
        
        registry.register_module(
            module_name='calc_google',
            module_class='src.modules.distance.implementations.google_distance_matrix.GoogleDistanceMatrixCalculator',
            config={'api_key': 'test_key'},
            enabled=False  # 默认禁用
        )
        
        # 使用欧几里得计算器
        euclidean = registry.get_module('calc_euclidean')
        assert euclidean.get_provider_name() == "Euclidean Distance Calculator"
        
        # 切换到Google计算器
        registry.modules['calc_euclidean'].enabled = False
        registry.modules['calc_google'].enabled = True
        
        google = registry.get_module('calc_google')
        assert "Google" in google.get_provider_name()
```

### 端到端测试

#### 完整工作流测试
```python
# tests/integration/test_end_to_end.py
import pytest
import json
from pathlib import Path
from datetime import datetime

class TestEndToEndWorkflow:
    """端到端工作流测试"""
    
    def test_complete_pipeline(self, tmp_path):
        """测试完整流水线"""
        from src.core.module_registry import ModuleRegistry
        from src.core.orchestrator import PipelineOrchestrator
        
        # 创建临时输出目录
        output_dir = tmp_path / "outputs"
        output_dir.mkdir()
        
        # 使用测试配置
        registry = ModuleRegistry("config/test_modules.yaml")
        orchestrator = PipelineOrchestrator(registry)
        
        # 完整流水线配置
        pipeline_config = {
            'name': 'end_to_end_test',
            'modules': [
                'data_fetcher',
                'demand_forecaster',
                'inventory_optimizer',
                'routing_optimizer',
                'sla_predictor'
            ],
            'date_range': ('2024-01-01', '2024-01-07'),
            'forecast_dates': ['2024-01-08', '2024-01-09', '2024-01-10'],
            'store_ids': ['M001', 'M002', 'M003'],
            'sku_ids': ['SKU001', 'SKU002'],
            'locations': [
                (22.3193, 114.1694),
                (22.3287, 114.1883),
                (22.3372, 114.1521)
            ],
            'output_path': str(output_dir)
        }
        
        # 执行完整流水线
        result = orchestrator.execute_pipeline(pipeline_config)
        
        # 验证结果完整性
        assert result['execution_time'] > 0
        assert 'results' in result
        
        results = result['results']
        
        # 验证每个模块的输出
        assert 'weather_data' in results or 'error' in results
        assert 'demand_forecasts' in results
        assert len(results['demand_forecasts']) > 0
        
        # 验证输出文件
        output_files = list(output_dir.glob("*"))
        assert len(output_files) > 0
        
        # 检查至少有一个JSON或CSV文件
        json_files = list(output_dir.glob("*.json"))
        csv_files = list(output_dir.glob("*.csv"))
        assert len(json_files) > 0 or len(csv_files) > 0
    
    def test_error_handling(self):
        """测试错误处理"""
        from src.core.module_registry import ModuleRegistry
        
        registry = ModuleRegistry()
        
        # 注册一个有错误的模块
        registry.register_module(
            module_name='faulty_module',
            module_class='tests.faulty_module.FaultyImplementation',
            config={}
        )
        
        # 应该抛出异常
        with pytest.raises(Exception):
            registry.get_module('faulty_module')
```

### 性能测试

#### 性能基准测试
```python
# tests/performance/test_performance.py
import pytest
import time
import pandas as pd
from src.modules.distance.implementations.euclidean_calculator import EuclideanDistanceCalculator

class TestPerformance:
    """性能测试"""
    
    @pytest.mark.benchmark
    def test_distance_matrix_performance(self):
        """测试距离矩阵计算性能"""
        calculator = EuclideanDistanceCalculator(cache_enabled=False)
        
        # 生成测试数据
        n_points = 100
        locations = [
            (22.3 + i * 0.001, 114.1 + i * 0.001)
            for i in range(n_points)
        ]
        
        # 性能测试
        start_time = time.time()
        
        result = calculator.calculate_distance_matrix(locations, locations)
        
        end_time = time.time()
        execution_time = end_time - start_time
        
        # 验证性能
        assert execution_time < 1.0  # 应在1秒内完成
        
        # 记录性能指标
        print(f"\nPerformance metrics:")
        print(f"  Points: {n_points}")
        print(f"  Matrix size: {n_points} × {n_points}")
        print(f"  Execution time: {execution_time:.3f} seconds")
        print(f"  Time per point pair: {(execution_time * 1e6) / (n_points * n_points):.2f} μs")
    
    @pytest.mark.benchmark
    @pytest.mark.parametrize("cache_enabled", [True, False])
    def test_cache_performance_impact(self, cache_enabled, benchmark):
        """测试缓存对性能的影响"""
        calculator = EuclideanDistanceCalculator(cache_enabled=cache_enabled)
        locations = [(22.3193, 114.1694), (22.3287, 114.1883)]
        
        # 第一次计算
        result1 = calculator.calculate_distance_matrix(locations, locations)
        
        # 第二次计算（应受益于缓存）
        result2 = calculator.calculate_distance_matrix(locations, locations)
        
        # 验证结果一致性
        pd.testing.assert_frame_equal(result1, result2)
        
        print(f"\nCache impact (enabled={cache_enabled}):")
        print(f"  Cache hit expected: {cache_enabled}")
```

### 测试运行与报告

#### 运行测试套件
```bash
# 运行所有测试
pytest

# 运行特定模块的测试
pytest tests/modules/distance/

# 运行单个测试文件
pytest tests/modules/distance/test_euclidean_calculator.py

# 运行特定测试函数
pytest tests/modules/distance/test_euclidean_calculator.py::TestEuclideanDistanceCalculator::test_distance_values

# 运行标记的测试
pytest -m benchmark
pytest -m "not slow"
```

#### 测试覆盖率
```bash
# 生成覆盖率报告
pytest --cov=src --cov-report=html

# 查看覆盖率摘要
pytest --cov=src --cov-report=term-missing

# 生成XML格式的覆盖率报告（用于CI/CD）
pytest --cov=src --cov-report=xml:coverage.xml
```

#### 测试配置
```ini
# pytest.ini
[pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts = 
    --strict-markers
    --strict-config
    --tb=short
    --color=yes
    -v
markers =
    slow: marks tests as slow (deselect with '-m "not slow"')
    benchmark: performance benchmark tests
    integration: integration tests
    e2e: end-to-end tests
```

---

## 代码质量与规范

### 代码格式化

#### Black 代码格式化
```bash
# 格式化所有代码
black src/ tests/

# 检查哪些文件需要格式化
black --check src/ tests/

# 格式化指定文件
black src/modules/distance/implementations/euclidean_calculator.py
```

#### isort 导入排序
```bash
# 排序所有导入
isort src/ tests/

# 检查导入排序
isort --check-only src/ tests/
```

### 代码风格检查

#### Flake8 检查
```bash
# 运行flake8检查
flake8 src/ tests/

# 忽略特定错误
flake8 --extend-ignore=E203,E501 src/

# 显示统计信息
flake8 --statistics src/
```

#### Flake8 配置
```ini
# .flake8
[flake8]
max-line-length = 88
extend-ignore = 
    E203,  # Whitespace before ':'
    W503,  # Line break before binary operator
    C901   # Function is too complex
exclude = 
    .git,
    __pycache__,
    build,
    dist,
    envs,
    venv
per-file-ignores = 
    __init__.py:F401
```

### 类型检查

#### MyPy 类型检查
```bash
# 运行类型检查
mypy src/

# 显示详细错误信息
mypy --pretty src/

# 生成HTML报告
mypy --html-report mypy_report src/
```

#### MyPy 配置
```ini
# mypy.ini
[mypy]
python_version = 3.9
warn_return_any = True
warn_unused_configs = True
disallow_untyped_defs = True
disallow_incomplete_defs = True
check_untyped_defs = True
disallow_untyped_decorators = True
no_implicit_optional = True
warn_redundant_casts = True
warn_unused_ignores = True
warn_no_return = True
warn_unreachable = True

[mypy-pandas.*]
ignore_missing_imports = True

[mypy-googlemaps.*]
ignore_missing_imports = True
```

### 预提交钩子

#### 预提交配置
```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.4.0
    hooks:
      - id: trailing-whitespace
      - id: end-of-file-fixer
      - id: check-yaml
      - id: check-added-large-files
      - id: check-merge-conflict
      - id: check-case-conflict
  
  - repo: https://github.com/psf/black
    rev: 23.9.1
    hooks:
      - id: black
        language_version: python3
  
  - repo: https://github.com/PyCQA/isort
    rev: 5.12.0
    hooks:
      - id: isort
        args: ["--profile", "black"]
  
  - repo: https://github.com/PyCQA/flake8
    rev: 6.1.0
    hooks:
      - id: flake8
        args: ["--max-line-length=88", "--extend-ignore=E203,W503"]
  
  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.6.0
    hooks:
      - id: mypy
        additional_dependencies: 
          - types-requests
          - types-PyYAML
          - pandas-stubs
```

#### 安装预提交钩子
```bash
# 安装预提交钩子
pre-commit install

# 在所有文件上运行预提交钩子
pre-commit run --all-files

# 运行特定钩子
pre-commit run black --all-files
```

### 文档字符串规范

#### Google 风格文档字符串
```python
def calculate_distance_matrix(self, origins, destinations, mode="driving"):
    """计算两点间的距离矩阵。
    
    Args:
        origins: 起点坐标列表，格式为 [(lat1, lng1), (lat2, lng2), ...]
        destinations: 终点坐标列表，格式与origins相同
        mode: 交通模式，可选值为 "driving", "walking", "bicycling"
            Default: "driving"
    
    Returns:
        pandas.DataFrame: 包含距离和时间的DataFrame，包含以下列：
            - distance_km: 距离（公里）
            - duration_min: 时间（分钟）
    
    Raises:
        ValueError: 当输入参数无效时
        ConnectionError: 当API连接失败时
    
    Example:
        >>> calculator = EuclideanDistanceCalculator()
        >>> origins = [(22.3193, 114.1694)]
        >>> destinations = [(22.3287, 114.1883)]
        >>> result = calculator.calculate_distance_matrix(origins, destinations)
        >>> print(result['distance_km'].iloc[0])
        1.234
    """
    # 实现代码...
```

#### 类型提示最佳实践
```python
from typing import List, Tuple, Dict, Any, Optional, Union
import pandas as pd

def process_data(
    data: pd.DataFrame,
    config: Dict[str, Any],
    threshold: Optional[float] = None,
    verbose: bool = False
) -> Tuple[pd.DataFrame, Dict[str, float]]:
    """处理数据并返回结果和统计信息。
    
    Args:
        data: 输入数据
        config: 处理配置
        threshold: 可选阈值参数
        verbose: 是否显示详细信息
    
    Returns:
        处理后的数据和统计信息
    """
    # 实现代码...
    return processed_data, stats
```

---

## 协作开发流程

### Git 工作流

#### 分支策略
```
main (保护分支)
    ↑
develop (保护分支)
    ↑
feature/xxx (功能分支)
bugfix/xxx (Bug修复分支)
hotfix/xxx (紧急修复分支)
```

#### 创建功能分支
```bash
# 从develop分支创建功能分支
git checkout develop
git pull origin develop
git checkout -b feature/distance-google-api

# 或使用快捷脚本
python scripts/create_feature_branch.py --name distance-google-api
```

#### 提交规范
使用 Conventional Commits 格式：
```
<type>[optional scope]: <description>

[optional body]

[optional footer(s)]
```

提交类型：
- `feat`: 新功能
- `fix`: Bug修复
- `docs`: 文档更新
- `style`: 代码格式（不影响功能）
- `refactor`: 代码重构
- `test`: 测试相关
- `chore`: 构建过程或辅助工具

示例：
```bash
# 新功能
git commit -m "feat(distance): add Google Distance Matrix API integration"

# Bug修复
git commit -m "fix(routing): fix time window constraint in VRP model"

# 文档更新
git commit -m "docs: update API documentation for new modules"
```

### 代码审查

#### Pull Request 模板
```markdown
## PR 类型
- [ ] 新功能 (feat)
- [ ] Bug修复 (fix)
- [ ] 文档更新 (docs)
- [ ] 代码样式 (style)
- [ ] 代码重构 (refactor)
- [ ] 测试 (test)
- [ ] 配置变更 (chore)
- [ ] 性能优化 (perf)

## 描述
请详细描述本次PR的内容：

### 背景
[为什么需要这个变更？解决了什么问题？]

### 变更内容
[具体做了哪些修改？]

### 影响范围
[哪些模块受到影响？是否有破坏性变更？]

## 测试情况

### 单元测试
- [ ] 已添加新测试
- [ ] 所有现有测试通过
- [ ] 测试覆盖率：[百分比]

### 集成测试
- [ ] 已测试与其他模块的集成
- [ ] 端到端流程测试通过

### 手动测试
- [ ] 在本地环境验证
- [ ] 测试数据：[描述测试数据]

## 检查清单
- [ ] 代码遵循PEP8规范
- [ ] 添加了必要的类型提示
- [ ] 更新了相关文档
- [ ] 更新了CHANGELOG（如适用）
- [ ] 没有引入新的警告或错误
- [ ] 代码已经过自我审查

## 截图/演示
[如有界面变更，请提供截图]
[或提供演示链接]

## 相关Issue
Close #123, Fix #456
```

#### 审查清单
1. **代码质量**
   - [ ] 代码是否清晰易读？
   - [ ] 是否有适当的注释？
   - [ ] 类型提示是否正确？
   - [ ] 错误处理是否充分？

2. **功能正确性**
   - [ ] 是否实现了需求？
   - [ ] 是否有边缘情况处理？
   - [ ] 性能是否可接受？

3. **测试覆盖**
   - [ ] 是否有充分的测试？
   - [ ] 测试是否通过？
   - [ ] 覆盖率是否足够？

4. **文档更新**
   - [ ] 是否更新了相关文档？
   - [ ] API文档是否准确？
   - [ ] 配置说明是否清晰？

### 团队协作工具

#### 每日站会
- **时间**：每天 9:00 PM（15分钟）
- **格式**：
  1. 昨天完成了什么？
  2. 今天计划做什么？
  3. 遇到什么阻碍？

#### 项目管理
```bash
# 使用GitHub Projects管理任务
# 列：Backlog → To Do → In Progress → Review → Done

# 创建任务Issue
gh issue create --title "[数据] 集成香港天文台API" \
                --body "需要获取实时天气数据用于需求预测" \
                --label "enhancement" \
                --assignee "@数据工程师"
```

#### 沟通规范
- **技术讨论**：GitHub Issues
- **代码审查**：GitHub Pull Requests
- **即时沟通**：微信群（紧急问题）
- **会议记录**：保存到 `docs/meeting_notes/`

---

## 部署与运维

### 本地部署

#### 运行主应用
```bash
# 激活环境
conda activate mannings-sla

# 运行主应用
python src/main.py

# 查看日志
tail -f logs/app.log
```

#### 运行仪表板
```bash
# 启动Streamlit仪表板
streamlit run src/visualization/dashboard/app.py

# 指定端口
streamlit run src/visualization/dashboard/app.py --server.port 8501

# 无浏览器模式
streamlit run src/visualization/dashboard/app.py --server.headless true
```

### Docker 部署

#### 构建镜像
```bash
# 构建Docker镜像
docker build -t mannings-sla:latest .

# 添加标签
docker tag mannings-sla:latest mannings-sla:1.0.0
```

#### 运行容器
```bash
# 运行容器
docker run -d \
  --name mannings-sla \
  -p 8501:8501 \
  -v $(pwd)/data:/app/data \
  -v $(pwd)/logs:/app/logs \
  -v $(pwd)/outputs:/app/outputs \
  -e GOOGLE_MAPS_API_KEY=your_key \
  -e HKO_API_KEY=your_key \
  mannings-sla:latest

# 查看容器状态
docker ps
docker logs mannings-sla
```

#### Docker Compose
```bash
# 启动所有服务
docker-compose up -d

# 查看服务状态
docker-compose ps

# 查看日志
docker-compose logs -f app

# 停止服务
docker-compose down
```

### 生产环境部署

#### 环境要求
```bash
# 服务器规格
- CPU: 4核以上
- 内存: 16GB以上
- 存储: 100GB SSD
- 网络: 公网IP，防火墙开放8501端口

# 依赖软件
- Docker 20.10+
- Docker Compose 2.0+
- Nginx (反向代理)
- Certbot (SSL证书)
```

#### 部署脚本
```bash
#!/bin/bash
# scripts/deploy_production.sh

set -e

echo "🚀 Starting production deployment..."

# 1. 拉取最新代码
git pull origin main

# 2. 构建Docker镜像
docker-compose build

# 3. 停止现有服务
docker-compose down

# 4. 启动新服务
docker-compose up -d

# 5. 运行数据库迁移（如果有）
# docker-compose exec app python manage.py migrate

# 6. 收集静态文件（如果有）
# docker-compose exec app python manage.py collectstatic --noinput

echo "✅ Deployment completed!"
echo "📊 Check status: docker-compose ps"
echo "📋 Check logs: docker-compose logs -f"
```

#### Nginx 配置
```nginx
# /etc/nginx/sites-available/mannings-sla
server {
    listen 80;
    server_name mannings.example.com;
    
    location / {
        proxy_pass http://localhost:8501;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # WebSocket支持
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
```

#### SSL 配置
```bash
# 使用Let's Encrypt获取SSL证书
sudo apt-get install certbot python3-certbot-nginx
sudo certbot --nginx -d mannings.example.com

# 自动续期
sudo certbot renew --dry-run
```

### 监控与日志

#### 日志配置
```python
# src/core/logging_config.py
import logging
import logging.handlers
from pathlib import Path

def setup_logging(log_level=logging.INFO, log_file="logs/app.log"):
    """配置日志系统"""
    
    # 创建日志目录
    log_path = Path(log_file)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    
    # 配置日志格式
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(module)s:%(lineno)d - %(message)s'
    )
    
    # 控制台处理器
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    console_handler.setLevel(log_level)
    
    # 文件处理器（按大小轮转）
    file_handler = logging.handlers.RotatingFileHandler(
        log_file,
        maxBytes=10*1024*1024,  # 10MB
        backupCount=5
    )
    file_handler.setFormatter(formatter)
    file_handler.setLevel(logging.DEBUG)
    
    # 配置根日志记录器
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)
    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)
    
    # 设置第三方库的日志级别
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('googleapiclient').setLevel(logging.WARNING)
    
    return root_logger
```

#### 健康检查端点
```python
# src/api/health.py
from fastapi import APIRouter, HTTPException
import psutil
import datetime

router = APIRouter()

@router.get("/health")
async def health_check():
    """健康检查端点"""
    try:
        # 检查系统资源
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        # 检查关键服务
        services_status = {
            'database': check_database_connection(),
            'redis': check_redis_connection(),
            'api_services': check_external_apis()
        }
        
        health_status = {
            'status': 'healthy',
            'timestamp': datetime.datetime.now().isoformat(),
            'system': {
                'cpu_percent': cpu_percent,
                'memory_percent': memory.percent,
                'disk_percent': disk.percent
            },
            'services': services_status
        }
        
        # 如果有服务不可用，返回部分健康
        if any(status == 'unhealthy' for status in services_status.values()):
            health_status['status'] = 'degraded'
        
        return health_status
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
```

#### 性能监控
```python
# src/core/monitoring.py
import time
from functools import wraps
from typing import Callable, Any
import logging

logger = logging.getLogger(__name__)

def monitor_performance(metric_name: str):
    """性能监控装饰器"""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            start_time = time.time()
            
            try:
                result = func(*args, **kwargs)
                execution_time = time.time() - start_time
                
                # 记录性能指标
                logger.info(
                    f"Performance metric: {metric_name} - "
                    f"execution_time={execution_time:.3f}s"
                )
                
                # 可以发送到监控系统
                # send_to_metrics_system(metric_name, execution_time)
                
                return result
                
            except Exception as e:
                execution_time = time.time() - start_time
                logger.error(
                    f"Performance metric (error): {metric_name} - "
                    f"execution_time={execution_time:.3f}s, error={e}"
                )
                raise
        
        return wrapper
    return decorator

# 使用示例
@monitor_performance("distance_matrix_calculation")
def calculate_distance_matrix(origins, destinations):
    # 计算逻辑
    pass
```

### 备份与恢复

#### 数据备份脚本
```bash
#!/bin/bash
# scripts/backup.sh

set -e

BACKUP_DIR="/backups/mannings-sla"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_FILE="$BACKUP_DIR/backup_$TIMESTAMP.tar.gz"

echo "📦 Starting backup..."

# 创建备份目录
mkdir -p $BACKUP_DIR

# 备份数据
tar -czf $BACKUP_FILE \
  data/ \
  outputs/ \
  logs/ \
  config/

# 保留最近7天的备份
find $BACKUP_DIR -name "backup_*.tar.gz" -mtime +7 -delete

echo "✅ Backup completed: $BACKUP_FILE"
```

#### 数据库备份（如果使用数据库）
```bash
#!/bin/bash
# scripts/backup_database.sh

# PostgreSQL备份
pg_dump -U $DB_USER -h $DB_HOST $DB_NAME > backup_$(date +%Y%m%d).sql

# SQLite备份
sqlite3 data/mannings.db ".backup backup_$(date +%Y%m%d).db"
```

#### 恢复脚本
```bash
#!/bin/bash
# scripts/restore.sh

set -e

BACKUP_FILE=$1

if [ -z "$BACKUP_FILE" ]; then
    echo "Usage: $0 <backup_file.tar.gz>"
    exit 1
fi

echo "🔄 Restoring from backup: $BACKUP_FILE"

# 停止服务
docker-compose down

# 解压备份
tar -xzf $BACKUP_FILE -C /

# 启动服务
docker-compose up -d

echo "✅ Restore completed!"
```

---

## 故障排查

### 常见问题与解决方案

#### 1. 模块加载失败
**问题**：`ModuleNotFoundError: No module named 'src'`
```bash
# 解决方案1：添加项目根目录到Python路径
export PYTHONPATH="${PYTHONPATH}:$(pwd)"

# 解决方案2：使用绝对导入
# 在文件开头添加：
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# 解决方案3：检查__init__.py文件
# 确保所有目录都有__init__.py文件
```

**问题**：`KeyError: Module 'xxx' not found in registry`
```bash
# 解决方案1：检查配置文件
cat config/modules.yaml | grep -A5 "xxx:"

# 解决方案2：验证模块路径
python -c "import src.modules.data.implementations.simulated_data_fetcher"

# 解决方案3：重新注册模块
python scripts/manage_modules.py list
```

#### 2. 依赖安装失败
**问题**：`CondaHTTPError: HTTP 000 CONNECTION FAILED`
```bash
# 解决方案：使用国内镜像源
conda config --add channels https://mirrors.tuna.tsinghua.edu.cn/anaconda/pkgs/main/
conda config --add channels https://mirrors.tuna.tsinghua.edu.cn/anaconda/pkgs/free/
conda config --set show_channel_urls yes

# 或者使用代理
export https_proxy=http://your-proxy:port
export http_proxy=http://your-proxy:port
```

**问题**：`Prophet安装失败`
```bash
# 解决方案：先安装依赖
conda install -c conda-forge prophet

# 或者使用pip
pip install prophet --no-deps
pip install pystan==2.19.1.1
```

#### 3. API调用失败
**问题**：`Google Maps API quota exceeded`
```bash
# 解决方案1：检查API配额
# 访问Google Cloud Console查看配额使用情况

# 解决方案2：启用缓存减少调用
# 在配置中设置cache_enabled: true

# 解决方案3：使用备选距离计算器
# 切换到欧几里得或曼哈顿距离计算器
```

**问题**：`HK Observatory API timeout`
```bash
# 解决方案1：增加超时时间
config:
  timeout: 30

# 解决方案2：使用模拟数据
# 切换到SimulatedDataFetcher
```

#### 4. 内存不足
**问题**：`MemoryError` 或进程被杀死
```bash
# 解决方案1：增加系统内存
# 如果使用Docker，增加内存限制：
docker run -m 8g ...

# 解决方案2：优化数据处理
# 使用分块处理大数据
def process_large_data(file_path, chunk_size=10000):
    for chunk in pd.read_csv(file_path, chunksize=chunk_size):
        process_chunk(chunk)

# 解决方案3：使用更高效的数据类型
df['column'] = df['column'].astype('float32')  # 而不是float64
```

#### 5. 性能问题
**问题**：距离计算太慢
```bash
# 解决方案1：启用缓存
distance_calculator:
  config:
    cache_enabled: true
    cache_size: 10000

# 解决方案2：并行计算
from concurrent.futures import ThreadPoolExecutor

def calculate_distances_parallel(origins, destinations):
    with ThreadPoolExecutor(max_workers=4) as executor:
        results = list(executor.map(calculate_distance, origins, destinations))
    return results

# 解决方案3：使用更快的算法
# 考虑使用近似算法或预计算距离矩阵
```

### 调试技巧

#### 1. 日志级别调整
```python
# 临时调整日志级别
import logging
logging.getLogger().setLevel(logging.DEBUG)

# 查看特定模块的日志
logging.getLogger('src.modules.distance').setLevel(logging.DEBUG)
```

#### 2. 调试器使用
```python
# 在代码中插入断点
import pdb; pdb.set_trace()

# 或使用breakpoint()（Python 3.7+）
breakpoint()

# VS Code调试配置
# .vscode/launch.json
{
    "version": "0.2.0",
    "configurations": [
        {
            "name": "Python: Main",
            "type": "python",
            "request": "launch",
            "program": "${workspaceFolder}/src/main.py",
            "console": "integratedTerminal",
            "env": {
                "PYTHONPATH": "${workspaceFolder}"
            }
        }
    ]
}
```

#### 3. 性能分析
```python
# 使用cProfile进行性能分析
import cProfile
import pstats

profiler = cProfile.Profile()
profiler.enable()

# 运行需要分析的代码
main()

profiler.disable()

# 保存分析结果
stats = pstats.Stats(profiler)
stats.sort_stats('cumulative')
stats.print_stats(20)  # 打印前20个最耗时的函数

# 保存到文件
stats.dump_stats('profile_results.prof')

# 使用snakeviz可视化
# pip install snakeviz
# snakeviz profile_results.prof
```

### 系统诊断

#### 系统状态检查
```bash
# 运行系统状态检查脚本
python scripts/system_status.py

# 检查关键服务
python -c "from src.core.module_registry import ModuleRegistry; \
           r = ModuleRegistry(); \
           print('Modules:', list(r.modules.keys()))"

# 检查数据文件
python -c "import pandas as pd; \
           df = pd.read_csv('data/synthetic/stores.csv'); \
           print(f'Stores: {len(df)}')"
```

#### 环境验证
```bash
# 验证Python环境
python scripts/verify_environment.py

# 检查依赖版本
conda list | grep -E "(pandas|numpy|prophet|streamlit)"

# 检查磁盘空间
df -h .

# 检查内存使用
free -h

# 检查进程
ps aux | grep -E "(python|streamlit)"
```

---

## 附录

### A. 快捷键参考

#### VS Code 快捷键
- `Ctrl+Shift+P`：命令面板
- `Ctrl+P`：快速打开文件
- `Ctrl+Shift+`：打开终端
- `F5`：开始调试
- `F9`：切换断点
- `Ctrl+Shift+I`：格式化文档
- `Ctrl+Shift+L`：选择所有匹配项

#### 终端快捷键
- `Ctrl+C`：中断当前命令
- `Ctrl+D`：退出终端
- `Ctrl+L`：清屏
- `Ctrl+R`：搜索历史命令
- `Ctrl+A`：移动到行首
- `Ctrl+E`：移动到行尾
- `Ctrl+U`：删除到行首
- `Ctrl+K`：删除到行尾

### B. 有用的命令

#### Git 命令
```bash
# 查看提交历史
git log --oneline --graph --all

# 撤销最后一次提交
git reset --soft HEAD~1

# 清理本地分支
git branch --merged | grep -v "\*" | xargs -n 1 git branch -d

# 查找包含特定内容的提交
git log --all --grep="关键字"

# 查看文件修改历史
git log -p -- path/to/file
```

#### Docker 命令
```bash
# 清理无用镜像
docker system prune -a

# 查看容器资源使用
docker stats

# 进入运行中的容器
docker exec -it container_name bash

# 查看容器日志
docker logs -f container_name

# 导出/导入镜像
docker save -o image.tar image:tag
docker load -i image.tar
```

#### Conda 命令
```bash
# 创建环境副本
conda create --name new_env --clone old_env

# 导出环境配置
conda env export > environment.yml

# 从YAML文件创建环境
conda env create -f environment.yml

# 更新环境
conda env update -f environment.yml --prune

# 清理包缓存
conda clean --all
```

### C. 性能优化技巧

#### 1. 向量化操作
```python
# 不好：使用循环
result = []
for x in data:
    result.append(x * 2)

# 好：使用向量化
result = data * 2

# 更好：使用NumPy
import numpy as np
result = np.array(data) * 2
```

#### 2. 避免重复计算
```python
# 不好：重复计算
for i in range(len(data)):
    result1 = expensive_function(data[i])
    result2 = expensive_function(data[i])  # 重复计算！

# 好：缓存结果
cache = {}
for i in range(len(data)):
    if i not in cache:
        cache[i] = expensive_function(data[i])
    result = cache[i]
```

#### 3. 使用生成器处理大数据
```python
# 不好：一次性加载所有数据
with open('large_file.csv') as f:
    data = f.readlines()  # 可能内存不足
    process(data)

# 好：使用生成器逐行处理
def read_large_file(file_path):
    with open(file_path) as f:
        for line in f:
            yield line

for line in read_large_file('large_file.csv'):
    process_line(line)
```

### D. 学习资源

#### Python 相关
- [Python官方文档](https://docs.python.org/3/)
- [Real Python教程](https://realpython.com/)
- [Python Design Patterns](https://refactoring.guru/design-patterns/python)

#### 数据科学
- [Pandas文档](https://pandas.pydata.org/docs/)
- [NumPy文档](https://numpy.org/doc/)
- [Scikit-learn教程](https://scikit-learn.org/stable/tutorial/index.html)

#### 机器学习
- [Prophet文档](https://facebook.github.io/prophet/docs/quick_start.html)
- [XGBoost文档](https://xgboost.readthedocs.io/)
- [TensorFlow教程](https://www.tensorflow.org/tutorials)

#### 优化算法
- [OR-Tools文档](https://developers.google.com/optimization)
- [PuLP文档](https://coin-or.github.io/pulp/)
- [车辆路径问题教程](https://developers.google.com/optimization/routing/vrp)

#### 可视化
- [Streamlit文档](https://docs.streamlit.io/)
- [Plotly文档](https://plotly.com/python/)
- [Folium文档](https://python-visualization.github.io/folium/)

#### 最佳实践
- [Google Python风格指南](https://google.github.io/styleguide/pyguide.html)
- [Python代码质量工具](https://realpython.com/python-code-quality/)
- [Python测试指南](https://realpython.com/python-testing/)

---

## 更新日志

### v0.1.0 (2024-01-25)
- ✅ 初始模块化架构实现
- ✅ 核心框架（接口、注册表、协调器）
- ✅ 基础模块实现（数据、距离、预测、路由、SLA、可视化）
- ✅ 完整的开发环境和工具链
- ✅ 详细的文档和开发指南

### 计划功能
- [ ] 实时数据流处理
- [ ] 高级机器学习模型集成
- [ ] 多目标优化算法
- [ ] 移动端应用
- [ ] 预测模型自动调优
- [ ] A/B测试框架

---

## 联系我们

### 项目团队
- **项目经理**：负责整体协调和进度管理
- **系统架构师**：负责系统设计和技术决策
- **数据工程师**：负责数据获取和处理
- **算法工程师**：负责预测和优化算法
- **前端工程师**：负责可视化界面
- **测试工程师**：负责质量保证

### 支持渠道
- **GitHub Issues**：技术问题和功能请求
- **团队微信群**：日常沟通和协调
- **每周会议**：进度同步和问题解决
- **文档**：详细的技术文档和指南

### 紧急联系方式
- 技术问题：@技术负责人
- 部署问题：@运维负责人
- 数据问题：@数据负责人

---

**最后更新**：2024年1月25日  
**版本**：v1.0.0  
**状态**：开发中  

> 注意：本开发指南会根据项目进展持续更新。请定期查看最新版本。