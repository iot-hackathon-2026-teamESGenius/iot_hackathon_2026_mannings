# 数据目录

## 子目录说明

| 目录 | 描述 | Git跟踪 |
|------|------|--------|
| `dfi/` | DFI企业数据（保密） | ❌ 不提交 |
| `official/` | 官方开放数据（HKO/Gov.hk） | ✅ 可提交 |
| `synthetic/` | 模拟生成的数据 | ⚠️ 仅配置文件 |
| `processed/` | 处理后的中间数据 | ❌ 不提交 |
| `external/` | 外部数据源 | ❌ 不提交 |
| `routing/` | 路径规划相关数据 | ⚠️ 按需 |

## DFI企业数据 (已签署NDA)

```
data/dfi/
├── raw/          # 原始数据 → 直接存放DFI提供的数据文件
├── processed/    # 处理后数据 → ETL后的特征数据
└── metadata/     # 元数据 → 数据字典（可提交）
```

**⚠️ 重要**: DFI数据严禁提交到Git，已在 `.gitignore` 配置

## Git 规则
- 大文件被 .gitignore 忽略
- 目录结构和小型配置文件被跟踪
- 使用 `data/synthetic/data_config.json` 记录数据生成配置
- DFI企业数据绝不提交
