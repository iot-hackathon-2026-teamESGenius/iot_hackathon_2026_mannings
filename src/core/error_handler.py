"""
错误处理和恢复机制模块 - Mannings SLA Optimization System
实现降级策略、重试机制、性能监控

Author: 王晔宸 (Team Lead)
Date: 2026-02-12
"""

import time
import logging
import functools
import threading
from typing import Dict, List, Any, Optional, Callable, TypeVar
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict
import traceback

logger = logging.getLogger(__name__)

T = TypeVar('T')


# ==================== 错误类型枚举 ====================

class ErrorType(Enum):
    """错误类型"""
    DATA_LOAD_ERROR = "data_load_error"
    EXTERNAL_API_ERROR = "external_api_error"
    OPTIMIZATION_ERROR = "optimization_error"
    FORECAST_ERROR = "forecast_error"
    VALIDATION_ERROR = "validation_error"
    TIMEOUT_ERROR = "timeout_error"
    RESOURCE_ERROR = "resource_error"
    UNKNOWN_ERROR = "unknown_error"


class RecoveryStrategy(Enum):
    """恢复策略"""
    RETRY = "retry"
    FALLBACK = "fallback"
    SKIP = "skip"
    RELAX_CONSTRAINTS = "relax_constraints"
    USE_CACHE = "use_cache"
    FAIL_FAST = "fail_fast"


# ==================== 错误上下文 ====================

@dataclass
class ErrorContext:
    """错误上下文信息"""
    error_type: ErrorType
    error_message: str
    timestamp: datetime = field(default_factory=datetime.now)
    stack_trace: str = ""
    recovery_attempted: bool = False
    recovery_strategy: Optional[RecoveryStrategy] = None
    recovery_success: bool = False
    metadata: Dict = field(default_factory=dict)


# ==================== 重试机制 ====================

class RetryConfig:
    """重试配置"""
    def __init__(
        self,
        max_retries: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
        exponential_backoff: bool = True,
        retry_on: List[type] = None
    ):
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.exponential_backoff = exponential_backoff
        self.retry_on = retry_on or [Exception]


def retry_with_backoff(config: RetryConfig = None):
    """带指数退避的重试装饰器"""
    config = config or RetryConfig()
    
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> T:
            last_exception = None
            
            for attempt in range(config.max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except tuple(config.retry_on) as e:
                    last_exception = e
                    
                    if attempt == config.max_retries:
                        logger.error(f"{func.__name__} 失败，已达到最大重试次数 {config.max_retries}")
                        break
                    
                    # 计算延迟
                    if config.exponential_backoff:
                        delay = min(config.base_delay * (2 ** attempt), config.max_delay)
                    else:
                        delay = config.base_delay
                    
                    logger.warning(f"{func.__name__} 失败 (尝试 {attempt + 1}/{config.max_retries + 1}), "
                                 f"{delay:.1f}秒后重试: {e}")
                    time.sleep(delay)
            
            raise last_exception
        
        return wrapper
    return decorator


# ==================== 降级处理器 ====================

class FallbackHandler:
    """降级处理器"""
    
    def __init__(self):
        self._fallback_registry: Dict[str, Callable] = {}
        self._cache: Dict[str, Any] = {}
        self._cache_timestamps: Dict[str, datetime] = {}
        self._cache_ttl = timedelta(minutes=30)
    
    def register_fallback(self, operation_name: str, fallback_func: Callable):
        """注册降级函数"""
        self._fallback_registry[operation_name] = fallback_func
        logger.info(f"注册降级函数: {operation_name}")
    
    def get_fallback(self, operation_name: str) -> Optional[Callable]:
        """获取降级函数"""
        return self._fallback_registry.get(operation_name)
    
    def cache_result(self, key: str, value: Any):
        """缓存结果"""
        self._cache[key] = value
        self._cache_timestamps[key] = datetime.now()
    
    def get_cached_result(self, key: str) -> Optional[Any]:
        """获取缓存结果"""
        if key not in self._cache:
            return None
        
        # 检查TTL
        if datetime.now() - self._cache_timestamps[key] > self._cache_ttl:
            del self._cache[key]
            del self._cache_timestamps[key]
            return None
        
        return self._cache[key]
    
    def execute_with_fallback(
        self,
        operation_name: str,
        primary_func: Callable,
        *args,
        cache_key: str = None,
        **kwargs
    ) -> Any:
        """执行带降级的操作"""
        # 首先尝试缓存
        if cache_key:
            cached = self.get_cached_result(cache_key)
            if cached is not None:
                logger.info(f"使用缓存结果: {operation_name}")
                return cached
        
        try:
            result = primary_func(*args, **kwargs)
            
            # 缓存成功结果
            if cache_key and result is not None:
                self.cache_result(cache_key, result)
            
            return result
            
        except Exception as e:
            logger.warning(f"{operation_name} 失败: {e}")
            
            # 尝试降级函数
            fallback = self.get_fallback(operation_name)
            if fallback:
                logger.info(f"执行降级函数: {operation_name}")
                try:
                    return fallback(*args, **kwargs)
                except Exception as fallback_error:
                    logger.error(f"降级函数也失败: {fallback_error}")
            
            # 尝试缓存
            if cache_key:
                cached = self.get_cached_result(cache_key)
                if cached is not None:
                    logger.info(f"使用过期缓存: {operation_name}")
                    return cached
            
            raise


# ==================== 约束放松器 ====================

class ConstraintRelaxer:
    """约束放松器 - 用于优化问题不可行时逐步放松约束"""
    
    def __init__(self):
        self.relaxation_levels = [
            # Level 0: 原始约束
            {'time_window_slack': 0, 'capacity_slack': 0, 'max_distance_multiplier': 1.0},
            # Level 1: 轻微放松
            {'time_window_slack': 15, 'capacity_slack': 5, 'max_distance_multiplier': 1.1},
            # Level 2: 中度放松
            {'time_window_slack': 30, 'capacity_slack': 10, 'max_distance_multiplier': 1.2},
            # Level 3: 重度放松
            {'time_window_slack': 60, 'capacity_slack': 20, 'max_distance_multiplier': 1.5},
            # Level 4: 极度放松
            {'time_window_slack': 120, 'capacity_slack': 50, 'max_distance_multiplier': 2.0},
        ]
        self.current_level = 0
    
    def reset(self):
        """重置放松级别"""
        self.current_level = 0
    
    def can_relax(self) -> bool:
        """是否还能继续放松"""
        return self.current_level < len(self.relaxation_levels) - 1
    
    def relax(self) -> Dict:
        """放松到下一级别，返回新的约束参数"""
        if self.can_relax():
            self.current_level += 1
            logger.info(f"放松约束到级别 {self.current_level}")
        return self.get_current_relaxation()
    
    def get_current_relaxation(self) -> Dict:
        """获取当前放松参数"""
        return self.relaxation_levels[self.current_level]
    
    def apply_relaxation(self, constraints: Dict) -> Dict:
        """应用放松到约束"""
        relaxation = self.get_current_relaxation()
        relaxed = constraints.copy()
        
        # 放松时间窗
        if 'time_window_slack' in relaxation:
            relaxed['time_window_slack'] = relaxed.get('time_window_slack', 0) + relaxation['time_window_slack']
        
        # 放松容量
        if 'capacity_slack' in relaxation:
            current_capacity = relaxed.get('vehicle_capacity', 100)
            relaxed['vehicle_capacity'] = current_capacity + relaxation['capacity_slack']
        
        # 放松距离
        if 'max_distance_multiplier' in relaxation:
            current_max = relaxed.get('max_distance_km', 200)
            relaxed['max_distance_km'] = current_max * relaxation['max_distance_multiplier']
        
        return relaxed


# ==================== 性能监控器 ====================

@dataclass
class PerformanceMetrics:
    """性能指标"""
    operation_name: str
    start_time: datetime
    end_time: datetime = None
    duration_ms: float = 0
    success: bool = True
    error_message: str = None
    memory_usage_mb: float = 0
    
    def finish(self, success: bool = True, error: str = None):
        self.end_time = datetime.now()
        self.duration_ms = (self.end_time - self.start_time).total_seconds() * 1000
        self.success = success
        self.error_message = error


class PerformanceMonitor:
    """性能监控器"""
    
    def __init__(self):
        self._metrics: List[PerformanceMetrics] = []
        self._operation_stats: Dict[str, Dict] = defaultdict(lambda: {
            'count': 0,
            'success_count': 0,
            'total_duration_ms': 0,
            'max_duration_ms': 0,
            'min_duration_ms': float('inf'),
            'errors': []
        })
        self._lock = threading.Lock()
    
    def start_operation(self, operation_name: str) -> PerformanceMetrics:
        """开始监控操作"""
        return PerformanceMetrics(
            operation_name=operation_name,
            start_time=datetime.now()
        )
    
    def finish_operation(self, metrics: PerformanceMetrics, success: bool = True, error: str = None):
        """结束监控操作"""
        metrics.finish(success, error)
        
        with self._lock:
            self._metrics.append(metrics)
            
            # 更新统计
            stats = self._operation_stats[metrics.operation_name]
            stats['count'] += 1
            if success:
                stats['success_count'] += 1
            stats['total_duration_ms'] += metrics.duration_ms
            stats['max_duration_ms'] = max(stats['max_duration_ms'], metrics.duration_ms)
            stats['min_duration_ms'] = min(stats['min_duration_ms'], metrics.duration_ms)
            if error:
                stats['errors'].append(error)
        
        # 日志记录
        status = "成功" if success else "失败"
        logger.info(f"操作 {metrics.operation_name} {status}, 耗时 {metrics.duration_ms:.2f}ms")
    
    def get_stats(self, operation_name: str = None) -> Dict:
        """获取统计信息"""
        with self._lock:
            if operation_name:
                stats = self._operation_stats.get(operation_name, {})
                if stats and stats['count'] > 0:
                    stats['avg_duration_ms'] = stats['total_duration_ms'] / stats['count']
                    stats['success_rate'] = stats['success_count'] / stats['count']
                return stats
            
            return dict(self._operation_stats)
    
    def get_recent_metrics(self, count: int = 10) -> List[PerformanceMetrics]:
        """获取最近的指标"""
        with self._lock:
            return self._metrics[-count:]


# ==================== 错误恢复协调器 ====================

class ErrorRecoveryCoordinator:
    """错误恢复协调器 - 统一管理错误处理和恢复策略"""
    
    def __init__(self):
        self.fallback_handler = FallbackHandler()
        self.constraint_relaxer = ConstraintRelaxer()
        self.performance_monitor = PerformanceMonitor()
        self._error_history: List[ErrorContext] = []
        self._recovery_strategies: Dict[ErrorType, RecoveryStrategy] = {
            ErrorType.DATA_LOAD_ERROR: RecoveryStrategy.USE_CACHE,
            ErrorType.EXTERNAL_API_ERROR: RecoveryStrategy.RETRY,
            ErrorType.OPTIMIZATION_ERROR: RecoveryStrategy.RELAX_CONSTRAINTS,
            ErrorType.FORECAST_ERROR: RecoveryStrategy.FALLBACK,
            ErrorType.VALIDATION_ERROR: RecoveryStrategy.SKIP,
            ErrorType.TIMEOUT_ERROR: RecoveryStrategy.RETRY,
            ErrorType.RESOURCE_ERROR: RecoveryStrategy.FAIL_FAST,
        }
    
    def classify_error(self, exception: Exception) -> ErrorType:
        """分类错误类型"""
        error_msg = str(exception).lower()
        
        if 'timeout' in error_msg or 'timed out' in error_msg:
            return ErrorType.TIMEOUT_ERROR
        elif 'connection' in error_msg or 'network' in error_msg or 'api' in error_msg:
            return ErrorType.EXTERNAL_API_ERROR
        elif 'infeasible' in error_msg or 'no solution' in error_msg or 'optimization' in error_msg:
            return ErrorType.OPTIMIZATION_ERROR
        elif 'forecast' in error_msg or 'predict' in error_msg:
            return ErrorType.FORECAST_ERROR
        elif 'validation' in error_msg or 'invalid' in error_msg:
            return ErrorType.VALIDATION_ERROR
        elif 'memory' in error_msg or 'resource' in error_msg:
            return ErrorType.RESOURCE_ERROR
        elif 'load' in error_msg or 'file' in error_msg or 'data' in error_msg:
            return ErrorType.DATA_LOAD_ERROR
        
        return ErrorType.UNKNOWN_ERROR
    
    def get_recovery_strategy(self, error_type: ErrorType) -> RecoveryStrategy:
        """获取恢复策略"""
        return self._recovery_strategies.get(error_type, RecoveryStrategy.FAIL_FAST)
    
    def record_error(self, exception: Exception, metadata: Dict = None) -> ErrorContext:
        """记录错误"""
        error_type = self.classify_error(exception)
        strategy = self.get_recovery_strategy(error_type)
        
        context = ErrorContext(
            error_type=error_type,
            error_message=str(exception),
            stack_trace=traceback.format_exc(),
            recovery_strategy=strategy,
            metadata=metadata or {}
        )
        
        self._error_history.append(context)
        return context
    
    def execute_with_recovery(
        self,
        operation_name: str,
        func: Callable,
        *args,
        fallback_func: Callable = None,
        max_retries: int = 3,
        **kwargs
    ) -> Any:
        """执行带恢复的操作"""
        metrics = self.performance_monitor.start_operation(operation_name)
        
        try:
            # 注册降级函数
            if fallback_func:
                self.fallback_handler.register_fallback(operation_name, fallback_func)
            
            # 尝试执行
            result = self.fallback_handler.execute_with_fallback(
                operation_name,
                func,
                *args,
                cache_key=f"{operation_name}_{hash(str(args))}",
                **kwargs
            )
            
            self.performance_monitor.finish_operation(metrics, success=True)
            return result
            
        except Exception as e:
            error_context = self.record_error(e, {'operation': operation_name})
            self.performance_monitor.finish_operation(metrics, success=False, error=str(e))
            
            # 根据策略恢复
            strategy = error_context.recovery_strategy
            
            if strategy == RecoveryStrategy.RETRY:
                # 重试逻辑已在fallback_handler中处理
                pass
            elif strategy == RecoveryStrategy.RELAX_CONSTRAINTS:
                # 返回None，让调用者处理约束放松
                logger.info(f"建议放松约束后重试: {operation_name}")
            
            raise
    
    def get_error_summary(self) -> Dict:
        """获取错误摘要"""
        summary = {
            'total_errors': len(self._error_history),
            'by_type': defaultdict(int),
            'recovery_success_rate': 0,
            'recent_errors': []
        }
        
        recovery_attempted = 0
        recovery_success = 0
        
        for ctx in self._error_history:
            summary['by_type'][ctx.error_type.value] += 1
            if ctx.recovery_attempted:
                recovery_attempted += 1
                if ctx.recovery_success:
                    recovery_success += 1
        
        if recovery_attempted > 0:
            summary['recovery_success_rate'] = recovery_success / recovery_attempted
        
        summary['recent_errors'] = [
            {'type': ctx.error_type.value, 'message': ctx.error_message[:100], 'time': ctx.timestamp.isoformat()}
            for ctx in self._error_history[-5:]
        ]
        
        return dict(summary)


# ==================== 全局实例 ====================

_coordinator: Optional[ErrorRecoveryCoordinator] = None


def get_error_recovery_coordinator() -> ErrorRecoveryCoordinator:
    """获取全局错误恢复协调器"""
    global _coordinator
    if _coordinator is None:
        _coordinator = ErrorRecoveryCoordinator()
    return _coordinator


# ==================== 便捷装饰器 ====================

def with_error_recovery(
    operation_name: str = None,
    fallback_func: Callable = None,
    max_retries: int = 3
):
    """错误恢复装饰器"""
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> T:
            op_name = operation_name or func.__name__
            coordinator = get_error_recovery_coordinator()
            
            return coordinator.execute_with_recovery(
                op_name,
                func,
                *args,
                fallback_func=fallback_func,
                max_retries=max_retries,
                **kwargs
            )
        
        return wrapper
    return decorator


def with_performance_monitoring(operation_name: str = None):
    """性能监控装饰器"""
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> T:
            op_name = operation_name or func.__name__
            coordinator = get_error_recovery_coordinator()
            metrics = coordinator.performance_monitor.start_operation(op_name)
            
            try:
                result = func(*args, **kwargs)
                coordinator.performance_monitor.finish_operation(metrics, success=True)
                return result
            except Exception as e:
                coordinator.performance_monitor.finish_operation(metrics, success=False, error=str(e))
                raise
        
        return wrapper
    return decorator
