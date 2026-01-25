"""
API路由模块
"""
from .auth import router as auth_router
from .forecast import router as forecast_router
from .planning import router as planning_router
from .sla import router as sla_router
from .dashboard import router as dashboard_router

__all__ = [
    'auth_router',
    'forecast_router', 
    'planning_router',
    'sla_router',
    'dashboard_router'
]
