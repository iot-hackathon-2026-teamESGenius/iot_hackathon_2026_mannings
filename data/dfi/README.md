# DFI 企业数据目录

> ⚠️ **保密数据** - 已签署NDA，**严禁提交到Git**

## 目录结构

```
data/dfi/
├── raw/                    # 原始数据（直接从DFI获取）
│   ├── case_study_order_detail-000000000000.csv  # 订单明细 (~11MB)
│   ├── fufillment_detail-000000000000.csv        # 履约明细 (~18MB)
│   ├── dim_store.csv                              # 门店维度表
│   └── dim_date.csv                               # 日期维度表
│
├── processed/              # 处理后的数据（ETL产出）
│
└── metadata/               # 元数据（可提交）
```

## 数据文件说明

### 原始数据 (raw/)

| 文件 | 大小 | 描述 |
|------|------|------|
| `case_study_order_detail-000000000000.csv` | ~11MB | 订单明细数据 |
| `fufillment_detail-000000000000.csv` | ~18MB | 履约/配送明细数据 |
| `dim_store.csv` | ~29KB | 门店维度表 |
| `dim_date.csv` | ~37KB | 日期维度表 |

### 数据用途映射

| 业务模块 | 主要数据源 |
|----------|------------|
| 需求预测 | order_detail + dim_date |
| 路径优化 | fufillment_detail + dim_store |
| SLA分析 | fufillment_detail |
| 库存优化 | order_detail |

## 使用方式

```python
import pandas as pd

# 加载原始数据
orders = pd.read_csv('data/dfi/raw/case_study_order_detail-000000000000.csv')
stores = pd.read_csv('data/dfi/raw/dim_store.csv')
fulfillment = pd.read_csv('data/dfi/raw/fufillment_detail-000000000000.csv')
dates = pd.read_csv('data/dfi/raw/dim_date.csv')
```

## 安全提醒

- ✅ 本目录已在 `.gitignore` 中配置
- ✅ 所有 `.csv` 文件都不会被提交
- ❌ 不要通过截图、复制等方式将数据带出项目环境
