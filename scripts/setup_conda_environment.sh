#!/bin/bash
# Conda环境设置脚本 - Linux/Mac

set -e  # 遇到错误退出

echo "🚀 设置Mannings SLA优化项目环境 (Conda版)..."

# 检查conda是否安装
if ! command -v conda &> /dev/null; then
    echo "❌ Conda未安装！请先安装Miniconda或Anaconda"
    echo "下载地址：https://docs.conda.io/en/latest/miniconda.html"
    exit 1
fi

echo "✅ Conda已安装: $(conda --version)"

# 检查是否在conda环境中，如果是则退出
if [[ -n "$CONDA_DEFAULT_ENV" ]]; then
    echo "⚠️  检测到当前已在conda环境: $CONDA_DEFAULT_ENV"
    read -p "是否继续创建新环境？(y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "操作取消"
        exit 0
    fi
fi

# 复制项目级.condarc
if [ -f ".condarc" ]; then
    echo "📋 使用项目级.condarc配置..."
    cp .condarc ~/.condarc
fi

# 创建Conda环境
echo "🔄 创建Conda环境 'mannings-sla'..."
conda env create -f environment.yml

# 激活环境
echo "✅ 环境创建成功！"
echo ""
echo "📝 使用以下命令激活环境："
echo "    conda activate mannings-sla"
echo ""
echo "🚀 运行项目："
echo "    streamlit run src/visualization/dashboard/app.py"
echo ""
echo "📊 验证环境："
echo "    python scripts/verify_environment.py"