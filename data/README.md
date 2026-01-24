# 数据目录

## 子目录说明
- `official/`: 官方数据集（从API获取）
- `synthetic/`: 模拟生成的数据
- `processed/`: 处理后的中间数据
- `external/`: 外部数据源

## Git 规则
- 大文件被 .gitignore 忽略
- 目录结构和小型配置文件被跟踪
- 使用 `data/synthetic/data_config.json` 记录数据生成配置
