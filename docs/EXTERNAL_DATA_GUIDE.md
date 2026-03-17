# 外部数据获取指导手册
> **保密文件** - 请勿提交至公开仓库
> 
> 最后更新: 2026-03-12

---

## 一、数据需求总览

| 优先级 | 数据类型 | 数据来源 | 用途 | 负责人 |
|--------|----------|----------|------|--------|
| **P0** | 门店经纬度坐标 | Google Maps / CSDI | 路径优化、距离矩阵 | 谭聪 |
| **P1** | 实时天气数据 | HKO Open API | 需求预测特征 | 谭聪 |
| **P2** | 交通状况数据 | data.gov.hk | 配送时间估算 | 李泰一 |
| **P3** | 公众假期官方表 | data.gov.hk | 验证dim_date | 李泰一 |

---

## 二、P0 - 门店经纬度坐标获取

### 2.1 问题说明

DFI提供的 `dim_store.csv` 包含306家门店，但**缺少经纬度坐标**，这是路径优化的必需数据。

**需要补充的数据格式:**
```csv
store_code,latitude,longitude
10001,22.3193,114.1694
10002,22.2855,114.1577
...
```

### 2.2 方案A: Google Maps Geocoding API (推荐)

**优点**: 精准度高、支持中英文地址、稳定可靠
**缺点**: 需要API Key、有调用配额

#### 步骤1: 获取API Key

1. 访问 [Google Cloud Console](https://console.cloud.google.com/)
2. 创建项目或选择已有项目
3. 启用 **Geocoding API**
4. 创建 API Key (建议设置IP限制)
5. 新账号有$200免费额度，足够使用

#### 步骤2: 安装依赖

```bash
pip install googlemaps
```

#### 步骤3: 批量地理编码脚本

将以下代码保存为 `scripts/geocode_stores.py`:

```python
"""
门店地址地理编码脚本
使用 Google Maps Geocoding API 获取门店经纬度
"""
import pandas as pd
import googlemaps
import time
import os
from pathlib import Path

# ========== 配置 ==========
# 方式1: 环境变量 (推荐)
API_KEY = os.getenv('GOOGLE_MAPS_API_KEY')

# 方式2: 直接填写 (仅本地测试用，勿提交!)
# API_KEY = 'your-api-key-here'

# 文件路径
PROJECT_ROOT = Path(__file__).parent.parent
INPUT_FILE = PROJECT_ROOT / 'data/dfi/raw/dim_store.csv'
OUTPUT_FILE = PROJECT_ROOT / 'data/dfi/processed/store_coordinates.csv'

def geocode_stores():
    """批量获取门店坐标"""
    if not API_KEY:
        raise ValueError("请设置 GOOGLE_MAPS_API_KEY 环境变量")
    
    gmaps = googlemaps.Client(key=API_KEY)
    
    # 读取门店数据
    df = pd.read_csv(INPUT_FILE)
    print(f"共 {len(df)} 家门店待处理")
    
    results = []
    for idx, row in df.iterrows():
        store_code = row['store code']
        address = row['ADDRESS']
        district = row['18 Districts']
        
        # 构建完整地址 (添加Hong Kong后缀提高准确率)
        full_address = f"{address}, {district}, Hong Kong"
        
        try:
            # 调用API
            result = gmaps.geocode(full_address)
            
            if result:
                location = result[0]['geometry']['location']
                lat = location['lat']
                lng = location['lng']
                status = 'SUCCESS'
            else:
                lat, lng = None, None
                status = 'NOT_FOUND'
                
        except Exception as e:
            lat, lng = None, None
            status = f'ERROR: {str(e)}'
        
        results.append({
            'store_code': store_code,
            'district': district,
            'address': address,
            'latitude': lat,
            'longitude': lng,
            'geocode_status': status
        })
        
        # 进度显示
        if (idx + 1) % 10 == 0:
            print(f"已处理: {idx + 1}/{len(df)}")
        
        # 避免超过API配额 (50 requests/second for Geocoding)
        time.sleep(0.1)
    
    # 保存结果
    result_df = pd.DataFrame(results)
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    result_df.to_csv(OUTPUT_FILE, index=False, encoding='utf-8-sig')
    
    # 统计
    success_count = sum(1 for r in results if r['geocode_status'] == 'SUCCESS')
    print(f"\n完成! 成功: {success_count}/{len(df)}")
    print(f"结果保存至: {OUTPUT_FILE}")
    
    return result_df

if __name__ == '__main__':
    geocode_stores()
```

#### 步骤4: 执行

```powershell
# Windows PowerShell
$env:GOOGLE_MAPS_API_KEY = "your-api-key"
python scripts/geocode_stores.py
```

### 2.3 方案B: CSDI 香港空间数据平台 (免费)

**优点**: 免费、官方数据、无需API Key
**缺点**: 需手动操作、批量处理较慢

#### 操作步骤 (GUI优先)

1. 访问 [CSDI Portal](https://portal.csdi.gov.hk/csdi-webpage/)
2. 点击 **地址搜寻** 功能
3. 输入门店地址，获取坐标
4. 手动记录或使用其API

#### CSDI API 方式

```python
import requests

def csdi_geocode(address: str) -> dict:
    """使用CSDI地址查询API"""
    url = "https://geodata.gov.hk/gs/api/v1.0.0/locationSearch"
    params = {'q': address}
    
    response = requests.get(url, params=params, timeout=10)
    data = response.json()
    
    if data:
        return {
            'latitude': data[0]['y'],
            'longitude': data[0]['x']
        }
    return None
```

### 2.4 方案C: 香港18区中心点 (备选/快速原型)

如果时间紧迫，可使用区域中心点作为近似值:

```python
HK_DISTRICT_CENTERS = {
    'Central & Western': (22.2860, 114.1510),
    'Wan Chai': (22.2780, 114.1710),
    'Eastern': (22.2840, 114.2240),
    'Southern': (22.2470, 114.1580),
    'Yau Tsim Mong': (22.3120, 114.1720),
    'Sham Shui Po': (22.3310, 114.1620),
    'Kowloon City': (22.3280, 114.1910),
    'Wong Tai Sin': (22.3420, 114.1950),
    'Kwun Tong': (22.3130, 114.2260),
    'Tsuen Wan': (22.3710, 114.1140),
    'Tuen Mun': (22.3910, 113.9770),
    'Yuen Long': (22.4450, 114.0220),
    'North': (22.4940, 114.1380),
    'Tai Po': (22.4510, 114.1640),
    'Sha Tin': (22.3870, 114.1950),
    'Sai Kung': (22.3830, 114.2700),
    'Kwai Tsing': (22.3560, 114.1300),
    'Islands': (22.2610, 113.9460),
}
```

**注意**: 此方案精度较低(~2-5km误差)，仅适合快速验证算法。

---

## 三、P1 - HKO 天气数据

### 3.1 API 概览

香港天文台提供免费开放数据API，**无需注册**。

| API | 端点 | 数据内容 |
|-----|------|----------|
| 9天预报 | /weather/v1/fnd | 9天天气预报 |
| 当前天气 | /weather/v1/rhrread | 实时温度、湿度 |
| 天气警告 | /weather/v1/warninginfo | 台风、暴雨警告 |
| 分区天气 | /weather/v1/rtd | 各区温度 |

### 3.2 API 调用示例

```python
import requests

HKO_BASE_URL = "https://data.weather.gov.hk/weatherAPI/opendata"

def get_9day_forecast():
    """获取9天天气预报"""
    url = f"{HKO_BASE_URL}/weather.php"
    params = {
        'dataType': 'fnd',
        'lang': 'en'
    }
    response = requests.get(url, params=params, timeout=10)
    return response.json()

def get_current_weather():
    """获取当前天气"""
    url = f"{HKO_BASE_URL}/weather.php"
    params = {
        'dataType': 'rhrread',
        'lang': 'en'
    }
    response = requests.get(url, params=params, timeout=10)
    return response.json()

def get_weather_warnings():
    """获取天气警告"""
    url = f"{HKO_BASE_URL}/weather.php"
    params = {
        'dataType': 'warninginfo',
        'lang': 'en'
    }
    response = requests.get(url, params=params, timeout=10)
    return response.json()
```

### 3.3 项目中已实现

已创建完整接口: `src/modules/data/implementations/hko_weather_api.py`

```python
from src.modules.data.implementations.hko_weather_api import HKOWeatherAPI

api = HKOWeatherAPI()
forecast = api.get_9day_forecast()      # 9天预报
current = api.get_current_weather()      # 当前天气
warnings = api.get_weather_warnings()    # 警告信息
```

### 3.4 历史天气数据

HKO开放数据不提供历史API，需从官网下载:

1. 访问 [HKO Climate Data](https://www.hko.gov.hk/en/cis/dailyExtract.htm)
2. 选择日期范围 (2025-06 至 2025-12)
3. 下载CSV格式
4. 保存至 `data/official/hko_historical_weather.csv`

---

## 四、P2 - 交通数据

### 4.1 data.gov.hk 交通数据

访问: https://data.gov.hk/en-data/dataset/hk-td-tis_7-traffic-data

**可用数据:**
- 交通流量 (Traffic Flow)
- 行车时间 (Journey Time)
- 特別交通消息 (Special Traffic News)

### 4.2 API 示例

```python
def get_traffic_speed_map():
    """获取交通速度地图数据"""
    url = "https://resource.data.one.gov.hk/td/speedmap.xml"
    response = requests.get(url, timeout=10)
    return response.text  # XML格式
```

---

## 五、P3 - 公众假期数据

### 5.1 官方数据源

访问: https://data.gov.hk/en-data/dataset/hk-effo-statistic-public-holidays-en

### 5.2 直接下载

```bash
# 2025年公众假期
curl -o data/official/public_holidays_2025.json \
  "https://www.1823.gov.hk/common/ical/en.json"
```

### 5.3 与 dim_date 对比验证

```python
import pandas as pd
import json

# 加载DFI日期特征
dim_date = pd.read_csv('data/dfi/raw/dim_date.csv')
dfi_holidays = dim_date[dim_date['if_public_holiday'] == 1]['calendar_date'].tolist()

# 加载官方假期
with open('data/official/public_holidays_2025.json') as f:
    official = json.load(f)
official_holidays = [h['date'] for h in official['events']]

# 对比
print(f"DFI假期数: {len(dfi_holidays)}")
print(f"官方假期数: {len(official_holidays)}")
```

---

## 六、API Key 安全管理

### 6.1 环境变量方式 (推荐)

创建 `.env` 文件 (已在.gitignore中):

```env
# API Keys - 勿提交!
GOOGLE_MAPS_API_KEY=your-google-api-key
```

Python 中使用:
```python
from dotenv import load_dotenv
import os

load_dotenv()
api_key = os.getenv('GOOGLE_MAPS_API_KEY')
```

### 6.2 已忽略的敏感文件

确保以下文件在 `.gitignore` 中:
- `.env` / `.env.*`
- `config/credentials.yaml`
- `data/dfi/**` (企业数据)
- 本文件 (`docs/EXTERNAL_DATA_GUIDE.md`)

---

## 七、快速开始清单

### 谭聪 (数据工程)

- [ ] 获取Google Maps API Key
- [ ] 运行 `scripts/geocode_stores.py` 获取门店坐标
- [ ] 验证坐标正确性 (抽查5-10家门店)
- [ ] 测试HKO API连通性
- [ ] 下载历史天气数据

### 李泰一 (数据分析)

- [ ] 下载公众假期官方数据
- [ ] 验证 dim_date 假期标记
- [ ] 准备需求预测训练数据集
- [ ] 评估交通数据是否需要集成

---

## 八、联系与支持

- **Google Maps API**: https://developers.google.com/maps/documentation/geocoding
- **HKO Open Data**: https://www.hko.gov.hk/en/abouthko/opendata_intro.htm
- **data.gov.hk**: https://data.gov.hk/en/
- **CSDI Portal**: https://portal.csdi.gov.hk/
