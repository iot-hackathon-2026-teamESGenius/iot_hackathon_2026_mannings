# DFI 数据分析报告
> 生成时间: 2026-03-12

## 一、数据概览

### 1.1 数据文件清单

| 文件 | 大小 | 行数 | 列数 | 描述 |
|------|------|------|------|------|
| dim_store.csv | ~37KB | 306 | 9 | 门店维度表 |
| dim_date.csv | ~29KB | 365 | 22 | 日期特征表 |
| case_study_order_detail.csv | ~11MB | 77,807 | 6 | 订单明细 |
| fufillment_detail.csv | ~18MB | 77,807 | 19 | 履约明细 |

### 1.2 数据覆盖范围

- **时间范围**: 2025-06-01 至 2025-12-31 (7个月)
- **门店数量**: 306家 (265家有订单数据)
- **订单数量**: 77,807笔
- **用户数量**: 52,116位
- **完成订单**: 77,586笔 (99.7%)

---

## 二、各表详细分析

### 2.1 门店维度表 (dim_store.csv)

**列结构:**
```
- 18 Districts      : 所属区域 (香港18区)
- store code        : 门店代码
- Business Hrs 1-3  : 营业时间段
- ADDRESS           : 详细地址
```

**区域分布 (Top 10):**
| 区域 | 门店数 |
|------|--------|
| Sha Tin | 29 |
| Yau Tsim Mong | 26 |
| Kwun Tong | 23 |
| Tuen Mun | 22 |
| Sham Shui Po | 22 |
| Eastern | 21 |
| Yuen Long | 20 |
| North | 18 |
| Central & Western | 15 |
| Kwai Tsing | 15 |

**⚠️ 缺失数据:**
- 门店经纬度坐标 (路径优化必需)
- 门店处理能力/产能数据

### 2.2 日期特征表 (dim_date.csv)

**列结构:**
```
基础日期字段:
- calendar_date, calendar_year, calendar_month, calendar_day
- calendar_weekday, if_weekday, if_weekend

促销/节假日标记 (共10个):
- if_public_holiday    : 公众假期 (17天)
- if_enjoycard_day     : 享乐卡日
- if_yuu_day           : yuu会员日
- if_happy_hour        : 欢乐时光
- if_baby_fair         : 婴儿用品展
- if_618_day           : 618促销
- if_double11_day      : 双11促销
- if_38_day            : 三八节
- if_anniversary_day   : 周年庆
- if_HH_ware_periods   : 特定促销期
```

**促销日统计:**
| 促销类型 | 天数 |
|----------|------|
| 公众假期 | 17 |
| Enjoycard Day | 若干 |
| 618促销 | 若干 |
| 双11促销 | 若干 |

**✅ 此表数据完整，可直接用于需求预测特征**

### 2.3 订单明细表 (case_study_order_detail.csv)

**列结构:**
```
- dt                      : 订单日期
- order_id                : 订单ID (SHA256 hash)
- user_id                 : 用户ID (SHA256 hash)
- fulfillment_store_code  : 履约门店代码
- unique_sku_cnt          : 不同SKU数量
- total_quantity_cnt      : 总商品数量
```

**订单统计:**
- 平均每单SKU数: ~1.5
- 平均每单商品数: ~2.3
- 日均订单: ~363笔

### 2.4 履约明细表 (fufillment_detail.csv)

**列结构 - 正常流程时间戳:**
```
order_create_time      → 订单创建
ready_time             → 订单确认
assigned_time          → 分配给门店
picking_time           → 开始拣货
picked_time            → 拣货完成
packed_time            → 打包完成
shipped_time           → 发货
in_transit_time        → 运输中
ready_for_pickup_time  → 可提货
completed_time         → 完成
```

**异常状态时间戳:**
```
cancel_time, refund_time, rejected_time, expired_time, retry_time
```

**SLA分析结果:**
| 阶段 | 平均耗时 | 中位数 |
|------|----------|--------|
| 订单→可提货 | 5,109 min | 4,702 min |
| (约85小时) | (约78小时) |

---

## 三、数据质量评估

### 3.1 完整性

| 数据项 | 完整度 | 说明 |
|--------|--------|------|
| 门店基础信息 | ✅ 100% | |
| 门店坐标 | ❌ 0% | **需要补充** |
| 日期特征 | ✅ 100% | |
| 订单明细 | ✅ 100% | |
| 履约时间戳 | ✅ 99.7% | 少量取消/退款订单 |

### 3.2 一致性

- ✅ 订单ID在两表间一一对应
- ✅ 门店代码可关联
- ⚠️ 部分门店在dim_store中但无订单数据 (41家)

---

## 四、外部数据需求

### 4.1 必需数据

| 数据 | 来源 | 用途 | 优先级 |
|------|------|------|--------|
| 门店经纬度坐标 | 地理编码/CSDI | 距离矩阵计算、路径优化 | **P0** |
| 天气数据 | HKO API | 需求预测特征 | **P1** |

### 4.2 可选数据

| 数据 | 来源 | 用途 | 优先级 |
|------|------|------|--------|
| 交通状况 | data.gov.hk | 配送时间估算 | P2 |
| 人口密度 | Census Dept | 需求预测 | P3 |

---

## 五、数据获取指南

### 5.1 门店坐标获取方案

**方案A: Google Maps Geocoding API**
```python
# 使用门店地址进行地理编码
import googlemaps
gmaps = googlemaps.Client(key='YOUR_API_KEY')
result = gmaps.geocode("Shop No.213, Fung Tak Shopping Centre, Wong Tai Sin, Kln")
lat, lng = result[0]['geometry']['location'].values()
```

**方案B: CSDI地址查询**
- 网址: https://geodata.gov.hk/gs/
- 支持批量地址匹配

**方案C: 手动标注 (备选)**
- 使用香港18区中心点坐标作为近似值

### 5.2 HKO天气数据

已实现API接口: `src/modules/data/implementations/hko_weather_api.py`

```python
from src.modules.data.implementations.hko_weather_api import HKOWeatherAPI

api = HKOWeatherAPI()
current = api.get_current_weather()
forecast = api.get_9day_forecast()
```

---

## 六、下一步行动

1. **P0 - 门店坐标补充** (谭聪/李泰一)
   - 选择地理编码方案
   - 批量获取306家门店坐标
   - 更新dim_store数据

2. **P1 - 数据预处理** (李泰一)
   - 合并订单+日期特征
   - 生成需求预测训练集

3. **P2 - 天气数据集成** (谭聪)
   - 测试HKO API连通性
   - 获取历史天气数据 (如有)
