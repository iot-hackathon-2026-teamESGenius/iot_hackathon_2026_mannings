# 外部数据接入脚本使用指南

本目录包含用于接入外部数据源的脚本,按照 `docs/EXTERNAL_DATA_GUIDE.md` 中的优先级实现。

## 📋 脚本清单

| 优先级 | 脚本名称 | 数据源 | 说明 |
|--------|----------|--------|------|
| **P0** | `geocode_stores.py` | Google Maps API | 获取门店精确坐标 (推荐) |
| **P0** | `geocode_stores_district_centers.py` | 本地数据 | 使用区域中心点 (快速原型) |
| **P1** | - | HKO API | 已实现在 `src/modules/data/implementations/hko_weather_api.py` |
| **P2** | `fetch_traffic_data.py` | data.gov.hk | 获取实时交通数据 |
| **P3** | `download_public_holidays.py` | data.gov.hk | 下载公众假期数据 |
| - | `test_data_integration.py` | - | 测试所有数据源连通性 |

---

## 🚀 快速开始

### 1. 测试所有数据源

首先运行测试脚本,查看哪些数据源已经可用:

```bash
python scripts/test_data_integration.py
```

### 2. 按优先级接入数据

#### P0: 门店坐标 (必需)

**方案A: Google Maps API (推荐 - 精确)**

1. 获取 Google Maps API Key:
   - 访问 https://console.cloud.google.com/
   - 创建项目并启用 Geocoding API
   - 创建 API Key

2. 设置环境变量:
   ```powershell
   # Windows PowerShell
   $env:GOOGLE_MAPS_API_KEY = "your-api-key-here"
   ```

3. 运行脚本:
   ```bash
   python scripts/geocode_stores.py
   ```

4. 结果保存在: `data/dfi/processed/store_coordinates.csv`

**方案B: 区域中心点 (快速原型)**

如果暂时没有 API Key,可以使用区域中心点:

```bash
python scripts/geocode_stores_district_centers.py
```

⚠️ 注意: 此方案精度较低(~2-5km误差),仅适合快速验证算法。

#### P1: 天气数据 (已实现)

HKO Weather API 已经实现,无需额外配置。测试:

```python
from src.modules.data.implementations.hko_weather_api import HKOWeatherAPI

api = HKOWeatherAPI()
current = api.get_current_weather()
forecasts = api.get_9day_forecast()
```

#### P2: 交通数据 (已实现)

获取实时交通数据和路径规划:

```bash
python scripts/fetch_traffic_data.py
```

**支持的数据源:**
1. **TDAS API** - 实时路径规划
   - 端点: `https://tdas-api.hkemobility.gov.hk/tdas/api/route`
   - 功能: 路径规划、行程时间预测、多路线选择
   - 用途: 配送路线优化

2. **Traffic Data of Strategic/Major Roads** - 实时交通数据
   - 包含: 交通流量、速度、道路占用率
   - 更新频率: 每1-2分钟
   - 用途: 交通状况分析

3. **Traffic Speed Map** - 交通速度地图
   - 包含: 主要道路平均速度
   - 更新频率: 每5分钟
   - 用途: 配送时间估算

结果保存在: `data/official/traffic/`

#### P3: 公众假期 (验证用)

下载官方公众假期数据并验证 dim_date:

```bash
python scripts/download_public_holidays.py
```

结果保存在: `data/official/public_holidays_2025.json`

---

## 📁 输出文件结构

```
data/
├── dfi/
│   ├── raw/
│   │   └── dim_store.csv              # 原始门店数据
│   └── processed/
│       ├── store_coordinates.csv      # 门店坐标 (Google Maps)
│       └── store_coordinates_district_centers.csv  # 门店坐标 (区域中心点)
│
└── official/
    ├── public_holidays_2025.json      # 公众假期数据
    └── traffic/
        ├── traffic_speed_map_*.json   # 交通速度数据
        ├── traffic_speed_map_*.xml    # 交通速度原始数据
        ├── traffic_news_*.json        # 交通消息
        └── traffic_news_*.xml         # 交通消息原始数据
```

---

## 🔐 API Key 管理

### 方式1: 环境变量 (推荐)

```powershell
# Windows PowerShell
$env:GOOGLE_MAPS_API_KEY = "your-api-key"

# Linux/Mac
export GOOGLE_MAPS_API_KEY="your-api-key"
```

### 方式2: .env 文件

在项目根目录创建 `.env` 文件:

```env
GOOGLE_MAPS_API_KEY=your-api-key-here
```

⚠️ 注意: `.env` 文件已在 `.gitignore` 中,不会被提交到 Git。

---

## 📊 数据质量检查

### 门店坐标

```python
import pandas as pd

df = pd.read_csv('data/dfi/processed/store_coordinates.csv')

# 检查成功率
success_count = len(df[df['geocode_status'] == 'SUCCESS'])
print(f"成功率: {success_count}/{len(df)} ({success_count/len(df)*100:.1f}%)")

# 检查失败的门店
failed = df[df['geocode_status'] != 'SUCCESS']
print(f"失败的门店: {len(failed)}")
print(failed[['store_code', 'address', 'geocode_status']])
```

### 公众假期验证

```python
import pandas as pd
import json

# 加载 DFI 日期数据
dim_date = pd.read_csv('data/dfi/raw/dim_date.csv')
dfi_holidays = dim_date[dim_date['if_public_holiday'] == 1]['calendar_date'].tolist()

# 加载官方假期
with open('data/official/public_holidays_2025.json') as f:
    official = json.load(f)

# 对比差异
print(f"DFI 假期数: {len(dfi_holidays)}")
print(f"官方假期数: {len(official['vcalendar'][0]['vevent'])}")
```

---

## 🐛 常见问题

### Q1: Google Maps API 配额不足

**A:** 新账号有 $200 免费额度,足够处理 306 家门店。如果超出配额:
- 检查是否有重复调用
- 使用 `time.sleep(0.1)` 控制请求频率
- 考虑使用方案B (区域中心点)

### Q2: HKO API 请求超时

**A:** HKO API 有时会响应较慢,可以:
- 增加 timeout 参数: `HKOWeatherAPI(timeout=30)`
- 重试机制
- 使用缓存

### Q3: 交通数据 XML 解析失败

**A:** data.gov.hk 的 XML 格式可能变化:
- 检查原始 XML 文件
- 更新解析逻辑
- 联系 data.gov.hk 支持

### Q4: 门店地址无法找到

**A:** 部分门店地址可能不完整或格式不标准:
- 手动检查地址
- 尝试添加更多上下文 (如区域名称)
- 使用 CSDI API 作为备选

---

## 📞 支持与文档

- **Google Maps API**: https://developers.google.com/maps/documentation/geocoding
- **HKO Open Data**: https://www.hko.gov.hk/en/abouthko/opendata_intro.htm
- **data.gov.hk**: https://data.gov.hk/en/
- **项目文档**: `docs/EXTERNAL_DATA_GUIDE.md`

---

## ✅ 检查清单

完成数据接入后,请确认:

- [ ] 门店坐标数据已获取 (成功率 > 95%)
- [ ] HKO Weather API 测试通过
- [ ] 公众假期数据已下载并验证
- [ ] (可选) 交通数据已获取
- [ ] 运行 `test_data_integration.py` 全部通过
- [ ] 数据文件已保存到正确位置
- [ ] API Key 已妥善保管 (不提交到 Git)

---

最后更新: 2026-03-17