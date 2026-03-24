"""
道路路径服务 - 获取真实道路路线
支持高德地图API和Google Maps Directions API
"""
import os
import httpx
import logging
from typing import Optional, List, Dict, Tuple, Any
from datetime import datetime
import asyncio

logger = logging.getLogger(__name__)

# 高德地图API配置（优先使用）
AMAP_API_KEY = os.getenv("AMAP_API_KEY", "")
AMAP_DIRECTIONS_URL = "https://restapi.amap.com/v3/direction/driving"

# Google Maps API配置（备用）
GOOGLE_MAPS_API_KEY = os.getenv("GOOGLE_MAPS_API_KEY", "")
GOOGLE_DIRECTIONS_URL = "https://maps.googleapis.com/maps/api/directions/json"

# 缓存路径结果（减少API调用）
_route_cache: Dict[str, Dict] = {}
_cache_ttl = 3600  # 1小时缓存


class DirectionsService:
    """道路路径服务 - 支持高德和Google"""
    
    def __init__(self, amap_key: str = None, google_key: str = None):
        self.amap_key = amap_key or AMAP_API_KEY
        self.google_key = google_key or GOOGLE_MAPS_API_KEY
        
        # 优先使用高德
        self.provider = None
        if self.amap_key:
            self.provider = "amap"
            logger.info("Using Amap (高德) Directions API")
        elif self.google_key:
            self.provider = "google"
            logger.info("Using Google Maps Directions API")
        else:
            logger.warning("No API Key configured. Using straight-line fallback.")
    
    def _cache_key(self, origin: Tuple[float, float], destination: Tuple[float, float], waypoints: List[Tuple[float, float]] = None) -> str:
        """生成缓存键 - 包含起点、终点和所有途经点"""
        key_parts = [f"{origin[0]:.6f},{origin[1]:.6f}"]
        if waypoints:
            for wp in waypoints:
                key_parts.append(f"{wp[0]:.6f},{wp[1]:.6f}")
        key_parts.append(f"{destination[0]:.6f},{destination[1]:.6f}")
        return "_".join(key_parts)
    
    async def get_route(
        self, 
        origin: Tuple[float, float],  # (lat, lng)
        destination: Tuple[float, float],  # (lat, lng)
        waypoints: List[Tuple[float, float]] = None  # [(lat, lng), ...]
    ) -> Dict[str, Any]:
        """
        获取两点或多点之间的真实道路路径
        
        Args:
            origin: 起点坐标 (lat, lng)
            destination: 终点坐标 (lat, lng)
            waypoints: 途经点列表 [(lat, lng), ...]
            
        Returns:
            {
                "success": bool,
                "polyline": [(lat, lng), ...],  # 道路路径点
                "distance_meters": int,
                "duration_seconds": int,
                "source": "amap" | "google" | "fallback"
            }
        """
        # 优先尝试高德
        if self.provider == "amap":
            result = await self._get_amap_route(origin, destination, waypoints)
            if result.get("success"):
                return result
            logger.warning("Amap API failed, trying fallback...")
        
        # 其次尝试Google
        if self.provider == "google":
            result = await self._get_google_route(origin, destination, waypoints)
            if result.get("success"):
                return result
            logger.warning("Google API failed, trying fallback...")
        
        # 使用fallback
        return self._fallback_route(origin, destination, waypoints)
    
    async def _get_amap_route(
        self,
        origin: Tuple[float, float],
        destination: Tuple[float, float],
        waypoints: List[Tuple[float, float]] = None
    ) -> Dict[str, Any]:
        """调用高德地图API获取路径"""
        # 检查缓存
        cache_key = self._cache_key(origin, destination, waypoints)
        if cache_key in _route_cache:
            cached = _route_cache[cache_key]
            if (datetime.now().timestamp() - cached.get("cached_at", 0)) < _cache_ttl:
                return cached["data"]
        
        try:
            # 高德API参数（注意：高德是lng,lat格式）
            params = {
                "key": self.amap_key,
                "origin": f"{origin[1]},{origin[0]}",  # lng,lat
                "destination": f"{destination[1]},{destination[0]}",  # lng,lat
                "extensions": "all",
                "output": "json"
            }
            
            # 添加途经点
            if waypoints:
                wp_str = ";".join([f"{wp[1]},{wp[0]}" for wp in waypoints])  # 高德用分号分隔
                params["waypoints"] = wp_str
            
            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.get(AMAP_DIRECTIONS_URL, params=params)
                
                if response.status_code == 200:
                    data = response.json()
                    
                    if data.get("status") == "1" and data.get("route"):
                        route = data["route"]
                        path = route.get("paths", [{}])[0]
                        
                        # 解析路径点
                        polyline_points = []
                        total_distance = int(path.get("distance", 0))
                        total_duration = int(path.get("duration", 0))
                        
                        # 从steps中提取路径点
                        for step in path.get("steps", []):
                            polyline = step.get("polyline", "")
                            if polyline:
                                # 高德返回的是"lng,lat;lng,lat;..."格式
                                coords = polyline.split(";")
                                for coord in coords:
                                    parts = coord.split(",")
                                    if len(parts) >= 2:
                                        lng, lat = float(parts[0]), float(parts[1])
                                        polyline_points.append((lat, lng))
                        
                        # 去重
                        if polyline_points:
                            unique_points = [polyline_points[0]]
                            for p in polyline_points[1:]:
                                if p != unique_points[-1]:
                                    unique_points.append(p)
                            polyline_points = unique_points
                        
                        result = {
                            "success": True,
                            "polyline": polyline_points,
                            "distance_meters": total_distance,
                            "duration_seconds": total_duration,
                            "source": "amap"
                        }
                        
                        # 缓存
                        _route_cache[cache_key] = {
                            "data": result,
                            "cached_at": datetime.now().timestamp()
                        }
                        
                        return result
                    else:
                        info = data.get("info", "Unknown error")
                        logger.warning(f"Amap API error: {info}")
                        
        except Exception as e:
            logger.error(f"Error calling Amap API: {e}")
        
        return {"success": False, "error": "Amap API failed"}
    
    async def _get_google_route(
        self, 
        origin: Tuple[float, float],
        destination: Tuple[float, float],
        waypoints: List[Tuple[float, float]] = None
    ) -> Dict[str, Any]:
        """调用Google Maps API获取路径"""
        # 检查缓存
        cache_key = self._cache_key(origin, destination, waypoints)
        if cache_key in _route_cache:
            cached = _route_cache[cache_key]
            if (datetime.now().timestamp() - cached.get("cached_at", 0)) < _cache_ttl:
                return cached["data"]
        
        try:
            params = {
                "origin": f"{origin[0]},{origin[1]}",
                "destination": f"{destination[0]},{destination[1]}",
                "key": self.google_key,
                "mode": "driving",
                "alternatives": False,
                "units": "metric"
            }
            
            # 添加途经点
            if waypoints:
                wp_str = "|".join([f"{wp[0]},{wp[1]}" for wp in waypoints])
                params["waypoints"] = f"optimize:true|{wp_str}"
            
            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.get(GOOGLE_DIRECTIONS_URL, params=params)
                
                if response.status_code == 200:
                    data = response.json()
                    
                    if data.get("status") == "OK" and data.get("routes"):
                        route = data["routes"][0]
                        
                        # 解码polyline
                        polyline_points = []
                        total_distance = 0
                        total_duration = 0
                        
                        for leg in route.get("legs", []):
                            total_distance += leg.get("distance", {}).get("value", 0)
                            total_duration += leg.get("duration", {}).get("value", 0)
                            
                            for step in leg.get("steps", []):
                                encoded = step.get("polyline", {}).get("points", "")
                                if encoded:
                                    decoded = self._decode_polyline(encoded)
                                    polyline_points.extend(decoded)
                        
                        # 去重
                        if polyline_points:
                            unique_points = [polyline_points[0]]
                            for p in polyline_points[1:]:
                                if p != unique_points[-1]:
                                    unique_points.append(p)
                            polyline_points = unique_points
                        
                        result = {
                            "success": True,
                            "polyline": polyline_points,
                            "distance_meters": total_distance,
                            "duration_seconds": total_duration,
                            "source": "google"
                        }
                        
                        # 缓存
                        _route_cache[cache_key] = {
                            "data": result,
                            "cached_at": datetime.now().timestamp()
                        }
                        
                        return result
                    else:
                        error_msg = data.get("error_message", data.get("status", "Unknown error"))
                        logger.warning(f"Google Directions API error: {error_msg}")
                        
        except Exception as e:
            logger.error(f"Error calling Google Directions API: {e}")
        
        return {"success": False, "error": "Google API failed"}
    
    def _decode_polyline(self, encoded: str) -> List[Tuple[float, float]]:
        """
        解码Google的encoded polyline格式
        返回 [(lat, lng), ...]
        """
        points = []
        index = 0
        lat = 0
        lng = 0
        
        while index < len(encoded):
            # 解码纬度
            shift = 0
            result = 0
            while True:
                b = ord(encoded[index]) - 63
                index += 1
                result |= (b & 0x1f) << shift
                shift += 5
                if b < 0x20:
                    break
            
            dlat = ~(result >> 1) if result & 1 else result >> 1
            lat += dlat
            
            # 解码经度
            shift = 0
            result = 0
            while True:
                b = ord(encoded[index]) - 63
                index += 1
                result |= (b & 0x1f) << shift
                shift += 5
                if b < 0x20:
                    break
            
            dlng = ~(result >> 1) if result & 1 else result >> 1
            lng += dlng
            
            points.append((lat / 1e5, lng / 1e5))
        
        return points
    
    def _fallback_route(
        self,
        origin: Tuple[float, float],
        destination: Tuple[float, float],
        waypoints: List[Tuple[float, float]] = None
    ) -> Dict[str, Any]:
        """
        当API不可用时的回退方案
        使用插值生成平滑曲线（不是直线）
        """
        points = [origin]
        
        if waypoints:
            points.extend(waypoints)
        
        points.append(destination)
        
        # 在点之间插值，生成更平滑的路径
        interpolated = []
        for i in range(len(points) - 1):
            p1 = points[i]
            p2 = points[i + 1]
            
            # 计算两点之间的距离（简化）
            dist = ((p2[0] - p1[0])**2 + (p2[1] - p1[1])**2) ** 0.5
            
            # 根据距离决定插值点数
            num_points = max(2, int(dist * 500))  # 约每0.002度一个点
            
            for j in range(num_points):
                t = j / num_points
                lat = p1[0] + t * (p2[0] - p1[0])
                lng = p1[1] + t * (p2[1] - p1[1])
                interpolated.append((lat, lng))
        
        interpolated.append(destination)
        
        # 估算距离和时间
        total_distance = sum(
            self._haversine(interpolated[i], interpolated[i+1])
            for i in range(len(interpolated) - 1)
        )
        
        return {
            "success": True,
            "polyline": interpolated,
            "distance_meters": int(total_distance),
            "duration_seconds": int(total_distance / 500 * 60),  # 假设30km/h
            "source": "fallback"
        }
    
    def _haversine(self, p1: Tuple[float, float], p2: Tuple[float, float]) -> float:
        """计算两点之间的Haversine距离（米）"""
        import math
        R = 6371000  # 地球半径（米）
        
        lat1, lon1 = math.radians(p1[0]), math.radians(p1[1])
        lat2, lon2 = math.radians(p2[0]), math.radians(p2[1])
        
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        
        a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
        c = 2 * math.asin(math.sqrt(a))
        
        return R * c
    
    async def get_multi_stop_route(
        self,
        stops: List[Tuple[float, float]]  # [(lat, lng), ...]
    ) -> Dict[str, Any]:
        """
        获取多站点路线（配送场景）
        
        Args:
            stops: 所有站点坐标列表，第一个为起点，最后一个为终点
            
        Returns:
            与get_route相同的格式，但包含完整路线
        """
        if len(stops) < 2:
            return {"success": False, "error": "At least 2 stops required"}
        
        origin = stops[0]
        destination = stops[-1]
        waypoints = stops[1:-1] if len(stops) > 2 else None
        
        return await self.get_route(origin, destination, waypoints)


# 单例
_directions_service: Optional[DirectionsService] = None

def get_directions_service() -> DirectionsService:
    """获取道路路径服务单例"""
    global _directions_service
    if _directions_service is None:
        _directions_service = DirectionsService()
    return _directions_service


async def get_delivery_route(
    dc_location: Tuple[float, float],
    store_locations: List[Tuple[float, float]],
    return_to_dc: bool = True
) -> Dict[str, Any]:
    """
    便捷函数：获取配送路线
    
    Args:
        dc_location: 配送中心坐标
        store_locations: 门店坐标列表（按配送顺序）
        return_to_dc: 是否返回配送中心
        
    Returns:
        包含完整路线的字典
    """
    service = get_directions_service()
    
    stops = [dc_location] + list(store_locations)
    if return_to_dc:
        stops.append(dc_location)
    
    return await service.get_multi_stop_route(stops)
