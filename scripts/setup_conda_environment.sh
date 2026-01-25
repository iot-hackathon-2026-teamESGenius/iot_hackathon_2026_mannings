#!/bin/bash
# ==============================================================================
# Conda环境设置脚本 - Mannings SLA优化项目
# 支持: Linux / macOS
# 更新: 2026-01-25
# ==============================================================================

set -e  # 遇到错误退出

ENV_NAME="mannings-sla"

echo ""
echo "========================================"
echo "🚀 Mannings SLA优化项目 - 环境设置"
echo "========================================"
echo ""

# ==============================================================================
# 1. 检查Conda是否安装
# ==============================================================================
if ! command -v conda &> /dev/null; then
    echo "❌ Conda未安装！请先安装Miniconda"
    echo ""
    echo "📌 下载地址: https://docs.conda.io/en/latest/miniconda.html"
    echo ""
    echo "快速安装 (Linux):"
    echo "  wget https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh"
    echo "  bash Miniconda3-latest-Linux-x86_64.sh -b"
    echo "  ~/miniconda3/bin/conda init bash"
    echo "  source ~/.bashrc"
    exit 1
fi

echo "✅ Conda已安装: $(conda --version)"

# ==============================================================================
# 2. 检查环境是否已存在
# ==============================================================================
if conda env list | grep -q "^${ENV_NAME} "; then
    echo ""
    echo "⚠️  检测到环境 '${ENV_NAME}' 已存在"
    echo ""
    echo "请选择操作:"
    echo "  [1] 更新环境 (推荐 - 保留现有包，添加新依赖)"
    echo "  [2] 重建环境 (删除并重新创建)"
    echo "  [3] 取消操作"
    echo ""
    read -p "请输入选项 [1/2/3]: " choice
    
    case $choice in
        1)
            echo ""
            echo "🔄 更新环境 '${ENV_NAME}'..."
            conda env update -f environment.yml --prune
            ;;
        2)
            echo ""
            echo "🗑️  删除旧环境..."
            conda env remove -n ${ENV_NAME} -y
            echo "🔄 创建新环境..."
            conda env create -f environment.yml
            ;;
        *)
            echo "操作取消"
            exit 0
            ;;
    esac
else
    # ==============================================================================
    # 3. 复制项目级.condarc配置
    # ==============================================================================
    if [ -f ".condarc" ]; then
        echo "📋 使用项目级.condarc配置..."
        cp .condarc ~/.condarc
    fi

    # ==============================================================================
    # 4. 创建Conda环境
    # ==============================================================================
    echo ""
    echo "🔄 创建Conda环境 '${ENV_NAME}'..."
    echo "这可能需要几分钟，请耐心等待..."
    echo ""
    conda env create -f environment.yml
fi

# ==============================================================================
# 5. 完成提示
# ==============================================================================
echo ""
echo "========================================"
echo "✅ 环境设置完成！"
echo "========================================"
echo ""
echo "📋 下一步操作:"
echo ""
echo "1️⃣  激活环境:"
echo "    conda activate ${ENV_NAME}"
echo ""
echo "2️⃣  验证环境:"
echo "    python scripts/verify_environment.py"
echo ""
echo "========================================"
echo "🚀 启动服务"
echo "========================================"
echo ""
echo "📊 REST API服务 (前端调用):"
echo "    uvicorn src.api.main:app --host 0.0.0.0 --port 8000 --reload"
echo ""
echo "💻 Streamlit看板 (内部调试):"
echo "    streamlit run src/visualization/dashboard/app.py"
echo ""
echo "🚧 路径优化Demo:"
echo "    python -m src.modules.routing.implementations.demo"
echo ""
echo "========================================"
echo "📖 API文档: http://localhost:8000/docs"
echo "========================================"