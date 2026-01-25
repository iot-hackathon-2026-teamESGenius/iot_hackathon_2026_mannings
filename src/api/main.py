"""
FastAPI主应用 - 为前端提供REST API服务
适配技术栈: Vue3 + uniapp + uniCloud

启动命令: uvicorn src.api.main:app --host 0.0.0.0 --port 8000 --reload
"""
import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from fastapi import FastAPI, HTTPException, Depends, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from typing import Optional
import logging

from src.core.module_registry import ModuleRegistry
from src.api.routers import auth, forecast, planning, sla, dashboard

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 创建FastAPI应用
app = FastAPI(
    title="Mannings SLA Optimization API",
    description="门店自提SLA优化系统REST API - 适配Vue3+uniapp前端",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc"
)

# 配置CORS - 允许前端跨域请求
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:*",
        "http://127.0.0.1:*",
        "https://*.unicloud.dcloud.net.cn",  # uniCloud域名
        "*"  # 开发环境允许所有来源，生产环境应限制
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 全局模块注册表
registry: ModuleRegistry = None

def get_registry() -> ModuleRegistry:
    """获取模块注册表"""
    global registry
    if registry is None:
        registry = ModuleRegistry("config/modules.yaml")
    return registry

# 注册路由
app.include_router(auth.router, prefix="/api/auth", tags=["认证服务"])
app.include_router(forecast.router, prefix="/api/forecast", tags=["预测服务"])
app.include_router(planning.router, prefix="/api/planning", tags=["决策规划"])
app.include_router(sla.router, prefix="/api/sla", tags=["SLA服务"])
app.include_router(dashboard.router, prefix="/api/dashboard", tags=["数据看板"])

@app.on_event("startup")
async def startup_event():
    """应用启动事件"""
    global registry
    logger.info("Starting Mannings SLA Optimization API...")
    registry = ModuleRegistry("config/modules.yaml")
    logger.info("Module registry initialized")

@app.on_event("shutdown")
async def shutdown_event():
    """应用关闭事件"""
    logger.info("Shutting down Mannings SLA Optimization API...")

@app.get("/")
async def root():
    """API根路径"""
    return {
        "service": "Mannings SLA Optimization API",
        "version": "1.0.0",
        "docs": "/api/docs",
        "health": "/api/health"
    }

@app.get("/api/health")
async def health_check():
    """健康检查端点"""
    return {
        "status": "healthy",
        "service": "mannings-sla-api",
        "modules": {
            "registry": registry is not None
        }
    }

@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """全局异常处理"""
    logger.error(f"Global exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "error": str(exc),
            "message": "服务器内部错误，请稍后重试"
        }
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
