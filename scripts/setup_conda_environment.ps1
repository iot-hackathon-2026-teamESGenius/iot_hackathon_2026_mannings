# Conda环境设置脚本 - Windows PowerShell

Write-Host "🚀 设置Mannings SLA优化项目环境 (Conda版)..." -ForegroundColor Green

# 检查conda是否安装
try {
    $condaInfo = conda --version
    Write-Host "✅ Conda已安装: $condaInfo" -ForegroundColor Green
} catch {
    Write-Host "❌ Conda未安装！请先安装Miniconda或Anaconda" -ForegroundColor Red
    Write-Host "下载地址：https://docs.conda.io/en/latest/miniconda.html" -ForegroundColor Yellow
    exit 1
}

# 检查是否在conda环境中
if ($env:CONDA_DEFAULT_ENV) {
    Write-Host "⚠️  检测到当前已在conda环境: $env:CONDA_DEFAULT_ENV" -ForegroundColor Yellow
    $response = Read-Host "是否继续创建新环境？(y/N)"
    if ($response -notmatch "^[Yy]$") {
        Write-Host "操作取消" -ForegroundColor Yellow
        exit 0
    }
}

# 复制项目级.condarc
if (Test-Path ".condarc") {
    Write-Host "📋 使用项目级.condarc配置..." -ForegroundColor Cyan
    Copy-Item ".condarc" -Destination "$HOME/.condarc" -Force
}

# 创建Conda环境
Write-Host "🔄 创建Conda环境 'mannings-sla'..." -ForegroundColor Cyan
conda env create -f environment.yml

Write-Host "✅ 环境创建成功！" -ForegroundColor Green
Write-Host ""
Write-Host "📝 使用以下命令激活环境：" -ForegroundColor White
Write-Host "    conda activate mannings-sla" -ForegroundColor Cyan
Write-Host ""
Write-Host "🚀 运行项目：" -ForegroundColor White
Write-Host "    streamlit run src/visualization/dashboard/app.py" -ForegroundColor Cyan