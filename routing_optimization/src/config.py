"""
Global configuration for routing optimization
全局参数配置 - 集中管理所有可调参数
"""

# Vehicle Configuration (车辆配置)
VEHICLE_CAPACITY = 100  # 单辆车的最大容量（单位）
NUM_VEHICLES = 5        # 可用车辆总数
VEHICLE_SPEED = 40      # 平均行驶速度 (km/h)

# Time Window Configuration (时间窗口配置)
DEPOT_OPEN_TIME = 8 * 60    # 仓库开放时间：8:00 AM (分钟)
DEPOT_CLOSE_TIME = 18 * 60  # 仓库关闭时间：6:00 PM (分钟)
SERVICE_TIME = 15           # 单个客户的服务时间 (分钟)

# Optimization Parameters (优化算法参数)
MAX_SEARCH_TIME = 30        # 最大求解时间 (秒) - 更长的时间通常能找到更好的解
FIRST_SOLUTION_STRATEGY = 'PATH_CHEAPEST_ARC'  # OR-Tools初始化策略：贪心路径构建
LOCAL_SEARCH_METAHEURISTIC = 'GUIDED_LOCAL_SEARCH'  # OR-Tools局部搜索策略：引导型局部搜索

# SLA Configuration (服务水平协议配置)
SLA_VIOLATION_PENALTY = 1000  # 未按时送达的惩罚成本
LATE_DELIVERY_WEIGHT = 2.0    # 迟到权重因子

# Robust Optimization Configuration (鲁棒优化配置 - 核心创新点)
DEMAND_RATIOS = [0.9, 1.0, 1.1]  # 需求场景：-10%, 标准, +10% (模拟需求波动)
ROBUST_SELECTION_CRITERION = 'min_max_distance'  # 鲁棒方案选择标准：
                                                   # - min_max_distance: 最小化最坏情况距离
                                                   # - min_avg_distance: 最小化平均距离
                                                   # - min_sla_violation: 最小化SLA违反

# Distance Calculation (距离计算配置)
USE_EUCLIDEAN_DISTANCE = True   # True: 欧几里得距离（快速，用于小范围）
                                 # False: Haversine距离（精确，用于真实地理）
DISTANCE_UNIT = 'km'            # 距离单位：'km' 或 'miles'

# Output Configuration (输出配置)
PRINT_SOLUTION = True           # 是否打印求解结果
SAVE_SOLUTION_TO_FILE = False   # 是否保存结果到文件
OUTPUT_FORMAT = 'json'          # 输出格式：'json' 或 'csv'
