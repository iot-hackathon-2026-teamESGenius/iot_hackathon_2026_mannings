"""
认证服务路由 - 适配前端登录与权限控制
"""
from fastapi import APIRouter, HTTPException, Header, Depends
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime, timedelta
import hashlib
import secrets
import logging

# 配置日志
logger = logging.getLogger(__name__)

router = APIRouter()

# ==================== 请求/响应模型 ====================

class LoginRequest(BaseModel):
    """登录请求"""
    username: str
    password: str

class LoginResponse(BaseModel):
    """登录响应"""
    success: bool
    token: Optional[str] = None
    user: Optional[dict] = None
    permissions: Optional[List[str]] = None
    error: Optional[str] = None

class TokenValidationResponse(BaseModel):
    """Token验证响应"""
    valid: bool
    user: Optional[dict] = None
    error: Optional[str] = None

# ==================== 模拟用户数据（生产环境应使用数据库） ====================

MOCK_USERS = {
    "store_manager": {
        "user_id": "U001",
        "username": "store_manager",
        "password_hash": hashlib.sha256("store123".encode()).hexdigest(),
        "role": "store_inventory",
        "permissions": [
            "view_orders", "view_inventory", "submit_replenishment",
            "view_alerts", "view_forecast"
        ],
        "store_ids": ["M001", "M002", "M003"]
    },
    "logistics_admin": {
        "user_id": "U002",
        "username": "logistics_admin",
        "password_hash": hashlib.sha256("logistics123".encode()).hexdigest(),
        "role": "logistics",
        "permissions": [
            "view_schedules", "edit_schedules", "view_routes",
            "adjust_routes", "view_alerts", "handle_alerts",
            "view_vehicle_tracking", "export_reports"
        ],
        "store_ids": None
    },
    "admin": {
        "user_id": "U003",
        "username": "admin",
        "password_hash": hashlib.sha256("admin123".encode()).hexdigest(),
        "role": "admin",
        "permissions": ["*"],  # 全部权限
        "store_ids": None
    }
}

# Token存储（生产环境应使用Redis）
TOKEN_STORE = {}

# ==================== 辅助函数 ====================

def generate_token() -> str:
    """生成随机Token"""
    return secrets.token_urlsafe(32)

def verify_password(plain_password: str, password_hash: str) -> bool:
    """验证密码"""
    return hashlib.sha256(plain_password.encode()).hexdigest() == password_hash

async def get_current_user(authorization: str = Header(None)):
    """依赖注入：获取当前用户"""
    if not authorization:
        raise HTTPException(status_code=401, detail="未提供认证Token")
    
    token = authorization.replace("Bearer ", "")
    if token not in TOKEN_STORE:
        raise HTTPException(status_code=401, detail="Token无效或已过期")
    
    token_data = TOKEN_STORE[token]
    if datetime.now() > token_data["expires"]:
        del TOKEN_STORE[token]
        raise HTTPException(status_code=401, detail="Token已过期")
    
    return token_data["user"]

def check_permission(user: dict, required_permission: str) -> bool:
    """检查用户权限"""
    if "*" in user.get("permissions", []):
        return True
    return required_permission in user.get("permissions", [])

# ==================== API端点 ====================

@router.post("/login", response_model=LoginResponse)
async def login(request: LoginRequest):
    """
    用户登录
    
    - **username**: 用户名（store_manager / logistics_admin / admin）
    - **password**: 密码（store123 / logistics123 / admin123）
    """
    user_data = MOCK_USERS.get(request.username)
    
    if not user_data:
        return LoginResponse(
            success=False,
            error="用户名或密码错误"
        )
    
    if not verify_password(request.password, user_data["password_hash"]):
        return LoginResponse(
            success=False,
            error="用户名或密码错误"
        )
    
    # 生成Token
    token = generate_token()
    expires = datetime.now() + timedelta(hours=24)
    
    # 存储Token
    TOKEN_STORE[token] = {
        "user": {
            "user_id": user_data["user_id"],
            "username": user_data["username"],
            "role": user_data["role"],
            "permissions": user_data["permissions"],
            "store_ids": user_data["store_ids"]
        },
        "expires": expires
    }
    
    return LoginResponse(
        success=True,
        token=token,
        user={
            "user_id": user_data["user_id"],
            "username": user_data["username"],
            "role": user_data["role"],
            "store_ids": user_data["store_ids"]
        },
        permissions=user_data["permissions"]
    )

@router.post("/logout")
async def logout(authorization: str = Header(None)):
    """用户登出"""
    if authorization:
        token = authorization.replace("Bearer ", "")
        if token in TOKEN_STORE:
            del TOKEN_STORE[token]
    
    return {"success": True, "message": "登出成功"}

@router.get("/validate", response_model=TokenValidationResponse)
async def validate_token(authorization: str = Header(None)):
    """验证Token有效性"""
    if not authorization:
        return TokenValidationResponse(valid=False, error="未提供Token")
    
    token = authorization.replace("Bearer ", "")
    
    if token not in TOKEN_STORE:
        return TokenValidationResponse(valid=False, error="Token无效")
    
    token_data = TOKEN_STORE[token]
    if datetime.now() > token_data["expires"]:
        del TOKEN_STORE[token]
        return TokenValidationResponse(valid=False, error="Token已过期")
    
    return TokenValidationResponse(
        valid=True,
        user=token_data["user"]
    )

@router.get("/permissions")
async def get_permissions(current_user: dict = Depends(get_current_user)):
    """获取当前用户权限列表"""
    return {
        "success": True,
        "user_id": current_user["user_id"],
        "role": current_user["role"],
        "permissions": current_user["permissions"]
    }

@router.get("/check-permission/{permission}")
async def check_user_permission(
    permission: str,
    current_user: dict = Depends(get_current_user)
):
    """检查当前用户是否具有特定权限"""
    has_permission = check_permission(current_user, permission)
    return {
        "success": True,
        "permission": permission,
        "has_permission": has_permission
    }

@router.get("/stores")
async def get_user_stores(current_user: dict = Depends(get_current_user)):
    """
    获取当前用户可访问的门店列表
    
    根据用户角色返回相应的门店数据：
    - store_inventory: 返回用户分配的门店
    - logistics/admin: 返回所有门店
    """
    logger.info(f"Authenticated stores API called by user: {current_user.get('username', 'unknown')}")
    try:
        # 导入数据加载器
        from src.modules.data.implementations.dfi_data_loader import DFIDataLoader
        
        # 加载真实门店数据
        data_loader = DFIDataLoader()
        stores = data_loader.load_stores()
        
        # 转换为前端需要的格式
        store_list = []
        for store in stores:  # 返回所有门店，不限制数量
            store_data = {
                "store_id": str(store.store_code),
                "store_name": f"Mannings {store.district}",
                "district": str(store.district) if store.district else "Unknown",
                "address": str(store.address) if store.address else ""
            }
            store_list.append(store_data)
        
        # 根据用户权限过滤门店
        if current_user["role"] == "store_inventory":
            # 门店管理员只能看到分配给他的门店
            user_store_ids = current_user.get("store_ids", [])
            if user_store_ids:
                store_list = [s for s in store_list if s["store_id"] in user_store_ids]
        
        logger.info(f"Returning {len(store_list)} authenticated stores for user {current_user.get('username')}")
        return {
            "success": True,
            "data": store_list,
            "total": len(store_list)
        }
        
    except Exception as e:
        logger.error(f"Failed to load stores: {e}")
        # 如果加载真实数据失败，返回模拟数据
        mock_stores = [
            {"store_id": "M001", "store_name": "Mannings Tsim Sha Tsui", "district": "Tsim Sha Tsui"},
            {"store_id": "M002", "store_name": "Mannings Causeway Bay", "district": "Causeway Bay"},
            {"store_id": "M003", "store_name": "Mannings Central", "district": "Central"},
            {"store_id": "M004", "store_name": "Mannings Mongkok", "district": "Mongkok"},
            {"store_id": "M005", "store_name": "Mannings Sha Tin", "district": "Sha Tin"}
        ]
        
        # 根据用户权限过滤
        if current_user["role"] == "store_inventory":
            user_store_ids = current_user.get("store_ids", [])
            if user_store_ids:
                mock_stores = [s for s in mock_stores if s["store_id"] in user_store_ids]
        
        logger.info(f"Returning {len(mock_stores)} mock stores due to error")
        return {
            "success": True,
            "data": mock_stores,
            "total": len(mock_stores)
        }

@router.get("/stores/public")
async def get_public_stores():
    """
    获取公开的门店列表（无需认证）
    """
    logger.info("Public stores API called")
    try:
        # 导入数据加载器
        from src.modules.data.implementations.dfi_data_loader import DFIDataLoader
        
        # 加载真实门店数据
        data_loader = DFIDataLoader()
        stores = data_loader.load_stores()
        
        # 转换为前端需要的格式
        store_list = []
        for store in stores:  # 返回所有门店，不限制数量
            store_data = {
                "store_id": str(store.store_code),
                "store_name": f"Mannings {store.district}",
                "district": str(store.district) if store.district else "Unknown",
                "address": str(store.address) if store.address else ""
            }
            store_list.append(store_data)
        
        logger.info(f"Returning {len(store_list)} public stores")
        return {
            "success": True,
            "data": store_list,
            "total": len(store_list)
        }
        
    except Exception as e:
        logger.error(f"Failed to load public stores: {e}")
        # 如果加载真实数据失败，返回模拟数据
        mock_stores = [
            {"store_id": "M001", "store_name": "Mannings Tsim Sha Tsui", "district": "Tsim Sha Tsui"},
            {"store_id": "M002", "store_name": "Mannings Causeway Bay", "district": "Causeway Bay"},
            {"store_id": "M003", "store_name": "Mannings Central", "district": "Central"},
            {"store_id": "M004", "store_name": "Mannings Mongkok", "district": "Mongkok"},
            {"store_id": "M005", "store_name": "Mannings Sha Tin", "district": "Sha Tin"}
        ]
        
        logger.info(f"Returning {len(mock_stores)} mock stores due to error")
        return {
            "success": True,
            "data": mock_stores,
            "total": len(mock_stores)
        }
