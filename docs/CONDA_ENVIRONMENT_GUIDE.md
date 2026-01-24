# Conda环境使用指南

## 为什么使用Conda？

1. **依赖隔离**：每个项目独立环境，避免包冲突
2. **科学计算友好**：对numpy、pandas等有优化版本
3. **跨平台一致**：在Windows、Mac、Linux上行为一致
4. **非Python依赖**：可以管理非Python包（如C库）

## 常用命令

### 环境操作
```bash
# 列出所有环境
conda env list

# 激活环境
conda activate mannings-sla

# 退出环境
conda deactivate

# 删除环境
conda remove --name mannings-sla --all