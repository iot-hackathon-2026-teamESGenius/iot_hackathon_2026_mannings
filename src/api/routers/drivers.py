"""
派送员管理路由 - 司机信息录入和管理
"""
from fastapi import APIRouter, HTTPException, Query, Body
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime
import uuid
import logging

logger = logging.getLogger(__name__)
router = APIRouter()


# ==================== 数据模型 ====================

class DriverInfo(BaseModel):
    """派送员信息"""
    driver_id: str
    name: str
    phone: str
    license_number: Optional[str] = None
    vehicle_id: Optional[str] = None
    status: str = "available"  # available / on_duty / off_duty
    current_location: Optional[Dict[str, float]] = None  # {lat, lng}
    created_at: str
    updated_at: str

class DriverCreateRequest(BaseModel):
    """创建派送员请求"""
    name: str
    phone: str
    license_number: Optional[str] = None
    vehicle_id: Optional[str] = None

class DriverUpdateRequest(BaseModel):
    """更新派送员请求"""
    name: Optional[str] = None
    phone: Optional[str] = None
    license_number: Optional[str] = None
    vehicle_id: Optional[str] = None
    status: Optional[str] = None
    current_location: Optional[Dict[str, float]] = None


# ==================== 数据存储 ====================

DRIVERS: Dict[str, DriverInfo] = {}

def init_drivers():
    """初始化默认派送员数据"""
    global DRIVERS
    
    default_drivers = [
        {"name": "陈大文", "phone": "9123****", "license_number": "HK-D-001", "vehicle_id": "V001"},
        {"name": "李小明", "phone": "9456****", "license_number": "HK-D-002", "vehicle_id": "V002"},
        {"name": "王志强", "phone": "9789****", "license_number": "HK-D-003", "vehicle_id": "V003"},
        {"name": "张伟业", "phone": "9012****", "license_number": "HK-D-004", "vehicle_id": None},
        {"name": "刘建国", "phone": "9345****", "license_number": "HK-D-005", "vehicle_id": None},
    ]
    
    for d in default_drivers:
        driver_id = f"DRV-{str(uuid.uuid4())[:8].upper()}"
        now = datetime.now().isoformat()
        DRIVERS[driver_id] = DriverInfo(
            driver_id=driver_id,
            name=d["name"],
            phone=d["phone"],
            license_number=d.get("license_number"),
            vehicle_id=d.get("vehicle_id"),
            status="available",
            current_location=None,
            created_at=now,
            updated_at=now
        )
    
    logger.info(f"Initialized {len(DRIVERS)} drivers")

# 初始化
init_drivers()


# ==================== API接口 ====================

@router.get("/list")
async def list_drivers(
    status: Optional[str] = Query(None, description="状态筛选"),
    vehicle_id: Optional[str] = Query(None, description="车辆ID筛选")
):
    """
    获取派送员列表
    """
    drivers = list(DRIVERS.values())
    
    if status:
        drivers = [d for d in drivers if d.status == status]
    if vehicle_id:
        drivers = [d for d in drivers if d.vehicle_id == vehicle_id]
    
    return {
        "success": True,
        "data": {
            "drivers": [d.dict() for d in drivers],
            "total": len(drivers),
            "statistics": {
                "available": len([d for d in DRIVERS.values() if d.status == "available"]),
                "on_duty": len([d for d in DRIVERS.values() if d.status == "on_duty"]),
                "off_duty": len([d for d in DRIVERS.values() if d.status == "off_duty"])
            }
        }
    }


@router.get("/{driver_id}")
async def get_driver(driver_id: str):
    """
    获取单个派送员信息
    """
    if driver_id not in DRIVERS:
        raise HTTPException(status_code=404, detail="派送员不存在")
    
    return {
        "success": True,
        "data": DRIVERS[driver_id].dict()
    }


@router.post("/create")
async def create_driver(request: DriverCreateRequest):
    """
    创建新派送员
    """
    driver_id = f"DRV-{str(uuid.uuid4())[:8].upper()}"
    now = datetime.now().isoformat()
    
    driver = DriverInfo(
        driver_id=driver_id,
        name=request.name,
        phone=request.phone,
        license_number=request.license_number,
        vehicle_id=request.vehicle_id,
        status="available",
        current_location=None,
        created_at=now,
        updated_at=now
    )
    
    DRIVERS[driver_id] = driver
    
    return {
        "success": True,
        "message": "派送员创建成功",
        "data": driver.dict()
    }


@router.put("/{driver_id}")
async def update_driver(driver_id: str, request: DriverUpdateRequest):
    """
    更新派送员信息
    """
    if driver_id not in DRIVERS:
        raise HTTPException(status_code=404, detail="派送员不存在")
    
    driver = DRIVERS[driver_id]
    
    if request.name is not None:
        driver.name = request.name
    if request.phone is not None:
        driver.phone = request.phone
    if request.license_number is not None:
        driver.license_number = request.license_number
    if request.vehicle_id is not None:
        driver.vehicle_id = request.vehicle_id
    if request.status is not None:
        driver.status = request.status
    if request.current_location is not None:
        driver.current_location = request.current_location
    
    driver.updated_at = datetime.now().isoformat()
    DRIVERS[driver_id] = driver
    
    return {
        "success": True,
        "message": "派送员信息已更新",
        "data": driver.dict()
    }


@router.delete("/{driver_id}")
async def delete_driver(driver_id: str):
    """
    删除派送员
    """
    if driver_id not in DRIVERS:
        raise HTTPException(status_code=404, detail="派送员不存在")
    
    del DRIVERS[driver_id]
    
    return {
        "success": True,
        "message": "派送员已删除"
    }


@router.put("/{driver_id}/status")
async def update_driver_status(
    driver_id: str,
    status: str = Body(..., embed=True)
):
    """
    更新派送员状态
    """
    if driver_id not in DRIVERS:
        raise HTTPException(status_code=404, detail="派送员不存在")
    
    if status not in ["available", "on_duty", "off_duty"]:
        raise HTTPException(status_code=400, detail="无效的状态值")
    
    driver = DRIVERS[driver_id]
    driver.status = status
    driver.updated_at = datetime.now().isoformat()
    DRIVERS[driver_id] = driver
    
    return {
        "success": True,
        "message": f"派送员状态已更新为: {status}",
        "data": driver.dict()
    }


@router.put("/{driver_id}/location")
async def update_driver_location(
    driver_id: str,
    lat: float = Body(...),
    lng: float = Body(...)
):
    """
    更新派送员位置
    """
    if driver_id not in DRIVERS:
        raise HTTPException(status_code=404, detail="派送员不存在")
    
    driver = DRIVERS[driver_id]
    driver.current_location = {"lat": lat, "lng": lng}
    driver.updated_at = datetime.now().isoformat()
    DRIVERS[driver_id] = driver
    
    return {
        "success": True,
        "message": "位置已更新",
        "data": driver.dict()
    }


@router.post("/{driver_id}/assign-vehicle")
async def assign_vehicle(
    driver_id: str,
    vehicle_id: str = Body(..., embed=True)
):
    """
    分配车辆给派送员
    """
    if driver_id not in DRIVERS:
        raise HTTPException(status_code=404, detail="派送员不存在")
    
    # 检查车辆是否已被分配
    for d in DRIVERS.values():
        if d.vehicle_id == vehicle_id and d.driver_id != driver_id:
            raise HTTPException(status_code=400, detail=f"车辆 {vehicle_id} 已分配给 {d.name}")
    
    driver = DRIVERS[driver_id]
    driver.vehicle_id = vehicle_id
    driver.updated_at = datetime.now().isoformat()
    DRIVERS[driver_id] = driver
    
    return {
        "success": True,
        "message": f"车辆 {vehicle_id} 已分配给 {driver.name}",
        "data": driver.dict()
    }


@router.get("/available/list")
async def get_available_drivers():
    """
    获取可用派送员列表（用于调度分配）
    """
    available = [d for d in DRIVERS.values() if d.status == "available"]
    
    return {
        "success": True,
        "data": {
            "drivers": [
                {
                    "driver_id": d.driver_id,
                    "name": d.name,
                    "vehicle_id": d.vehicle_id,
                    "has_vehicle": d.vehicle_id is not None
                }
                for d in available
            ],
            "count": len(available)
        }
    }
