"""
Forecasting service layer.
Bridges forecasting modules with API routers using cached training data.
"""

from __future__ import annotations

import logging
from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

from src.api.services.data_service import get_data_service
from src.modules.forecasting.prophet_forecaster import ProphetForecaster
from src.modules.forecasting.sla_predictor import MLSLAPredictor

logger = logging.getLogger(__name__)


SKU_PROFILES: Dict[str, Dict[str, Any]] = {
    "SKU001": {"name": "维他命C 1000mg", "weight": 0.26, "base_stock": 180, "daily_arrival": 18},
    "SKU002": {"name": "感冒灵颗粒", "weight": 0.22, "base_stock": 160, "daily_arrival": 16},
    "SKU003": {"name": "洗手液 500ml", "weight": 0.18, "base_stock": 140, "daily_arrival": 12},
    "SKU004": {"name": "口罩 50片装", "weight": 0.20, "base_stock": 170, "daily_arrival": 20},
    "SKU005": {"name": "消毒湿巾", "weight": 0.14, "base_stock": 130, "daily_arrival": 10},
}

ECDC_PROFILES: Dict[str, Dict[str, Any]] = {
    "ECDC01": {"name": "Kwai Chung DC", "share": 0.58},
    "ECDC02": {"name": "Tsuen Wan ECDC", "share": 0.42},
}


class ForecastingService:
    """Cached access layer for demand, ATP and SLA forecasts."""

    _instance: Optional["ForecastingService"] = None

    def __new__(cls) -> "ForecastingService":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self) -> None:
        if getattr(self, "_initialized", False):
            return

        self.data_service = get_data_service()
        self.forecaster = ProphetForecaster()
        self.sla_predictor = MLSLAPredictor()
        self._training_frame: Optional[pd.DataFrame] = None
        self._forecast_reference_date: Optional[date] = None
        self._store_name_cache: Dict[str, str] = {}  # 缓存门店名称
        self._initialized = True

    def get_demand_forecasts(
        self,
        start_date: date,
        end_date: date,
        store_ids: Optional[List[str]] = None,
        sku_ids: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        self._ensure_models()

        training = self._get_training_frame()
        stores = store_ids or sorted(training["fulfillment_store_code"].astype(str).unique().tolist())
        skus = sku_ids or list(SKU_PROFILES.keys())
        reference_date = self._forecast_reference_date or start_date

        forecast_map = self._build_forecast_lookup(stores, end_date)
        actual_map = self._build_actual_lookup(training)
        
        # 预加载门店名称缓存，避免循环中重复查询
        store_names = self._get_store_names_batch(stores)
        
        # 为没有专属模型的门店计算历史平均值作为回退预测
        store_historical_avg = self._compute_historical_averages(training, stores)

        results: List[Dict[str, Any]] = []
        current = start_date
        while current <= end_date:
            for store_id in stores:
                store_name = store_names.get(store_id, f"Store {store_id}")
                aggregate = forecast_map.get((store_id, current))
                actual_total = actual_map.get((store_id, current))

                # 如果没有模型预测，使用智能加权预测
                if aggregate is None:
                    hist_avg = store_historical_avg.get(store_id)
                    if hist_avg is not None:
                        # 使用智能预测而不是简单平均值
                        aggregate = self._compute_smart_forecast(
                            base_avg=hist_avg,
                            forecast_date=current,
                            training=training,
                            store_id=store_id
                        )
                    elif actual_total is not None:
                        aggregate = {
                            "predicted": float(actual_total),
                            "lower": max(0.0, actual_total * 0.9),
                            "upper": actual_total * 1.1,
                            "factors": [],
                            "multiplier": 1.0,
                        }
                else:
                    # 即使有模型预测，也应用智能调整因子
                    hist_avg = aggregate.get("predicted", 10.0)
                    smart = self._compute_smart_forecast(
                        base_avg=hist_avg,
                        forecast_date=current,
                        training=training,
                        store_id=store_id
                    )
                    # 保留模型预测值，但添加因素信息
                    aggregate["factors"] = smart.get("factors", [])
                    aggregate["multiplier"] = smart.get("multiplier", 1.0)
                    # 应用智能调整（较小幅度）
                    adj_factor = (smart["multiplier"] - 1.0) * 0.3 + 1.0  # 只应用30%的调整
                    aggregate["predicted"] = round(aggregate["predicted"] * adj_factor, 1)
                    aggregate["lower"] = round(aggregate.get("lower", aggregate["predicted"] * 0.8) * adj_factor, 1)
                    aggregate["upper"] = round(aggregate.get("upper", aggregate["predicted"] * 1.2) * adj_factor, 1)

                if aggregate is None:
                    current += timedelta(days=0)
                    continue

                for sku_id in skus:
                    profile = SKU_PROFILES.get(sku_id, {"name": sku_id, "weight": 1.0 / max(1, len(skus))})
                    weight = float(profile["weight"])
                    forecast_value = aggregate["predicted"] * weight
                    lower = aggregate["lower"] * weight
                    upper = aggregate["upper"] * weight
                    actual_value = actual_total * weight if actual_total is not None else None
                    deviation = None
                    if actual_value is not None and forecast_value > 0:
                        deviation = (actual_value - forecast_value) / forecast_value * 100

                    results.append(
                        {
                            "store_id": store_id,
                            "store_name": store_name,
                            "sku_id": sku_id,
                            "sku_name": profile["name"],
                            "date": current.isoformat(),
                            "forecast_demand": round(forecast_value, 1),
                            "actual_demand": round(actual_value, 1) if actual_value is not None and current <= reference_date else None,
                            "deviation_rate": round(deviation, 2) if deviation is not None and current <= reference_date else None,
                            "lower_bound": round(lower, 1),
                            "upper_bound": round(upper, 1),
                            "factors": aggregate.get("factors", []),  # 影响因素
                            "multiplier": aggregate.get("multiplier", 1.0),  # 调整系数
                        }
                    )
            current += timedelta(days=1)

        return results
    
    def _compute_historical_averages(self, training: pd.DataFrame, store_ids: List[str]) -> Dict[str, float]:
        """计算门店的历史平均需求，用于没有模型的门店"""
        averages = {}
        # 计算全局平均值作为默认回退
        global_avg = training["total_quantity"].mean()
        if pd.isna(global_avg):
            global_avg = 10.0
        
        for store_id in store_ids:
            store_data = training[training["fulfillment_store_code"].astype(str) == str(store_id)]
            if not store_data.empty:
                avg = store_data["total_quantity"].mean()
                averages[store_id] = float(avg) if pd.notna(avg) else float(global_avg)
            else:
                # 门店没有历史数据，使用全局平均值
                averages[store_id] = float(global_avg)
        return averages
    
    def _compute_smart_forecast(self, base_avg: float, forecast_date: date, training: pd.DataFrame, store_id: str) -> Dict[str, float]:
        """
        智能加权预测：考虑多种因素对需求的影响
        
        因素包括：
        1. 星期几效应 - 周末/工作日
        2. 节假日效应 - 公众假期
        3. 季节性/月份效应
        4. 天气效应 - 温度、降雨
        5. 历史数据学习 - 同类型日期的历史模式
        """
        multiplier = 1.0
        uncertainty = 0.15  # 基础不确定性 15%
        factors = []
        
        # 获取日期类型分类
        date_type = self._classify_date(forecast_date)
        weekday = forecast_date.weekday()
        weekday_names = ['周一', '周二', '周三', '周四', '周五', '周六', '周日']
        
        # 预设因子
        weekday_factors = {
            0: 0.95, 1: 0.98, 2: 1.00, 3: 1.02, 4: 1.08, 5: 1.15, 6: 1.10
        }
        month_factors = {
            1: 1.05, 2: 1.08, 3: 1.00, 4: 0.98, 5: 1.02, 6: 1.05,
            7: 1.08, 8: 1.10, 9: 1.05, 10: 1.02, 11: 1.00, 12: 1.12
        }
        
        # ================== 从历史数据学习 ==================
        store_data = training[training["fulfillment_store_code"].astype(str) == str(store_id)].copy()
        learned_from_history = False
        history_factor = 1.0
        
        if not store_data.empty and "order_date" in store_data.columns:
            # 为历史数据添加日期分类
            store_data["date_parsed"] = pd.to_datetime(store_data["order_date"])
            store_data["date_type"] = store_data["date_parsed"].apply(lambda d: self._classify_date(d.date()))
            store_data["weekday"] = store_data["date_parsed"].dt.dayofweek
            store_data["month"] = store_data["date_parsed"].dt.month
            
            overall_avg = store_data["total_quantity"].mean()
            
            if overall_avg > 0:
                # 学习同类型日期的历史模式
                same_type_data = store_data[store_data["date_type"] == date_type]
                if len(same_type_data) >= 3:  # 至少有3个同类型数据点
                    type_avg = same_type_data["total_quantity"].mean()
                    history_factor = type_avg / overall_avg
                    learned_from_history = True
                    factors.append(f"历史{date_type}模式")
                
                # 学习星期模式
                weekday_avg = store_data.groupby("weekday")["total_quantity"].mean()
                if weekday in weekday_avg.index:
                    weekday_learned = weekday_avg[weekday] / overall_avg
                    weekday_factors[weekday] = 0.5 * weekday_factors[weekday] + 0.5 * weekday_learned
                
                # 学习月份模式
                month_avg = store_data.groupby("month")["total_quantity"].mean()
                month = forecast_date.month
                if month in month_avg.index:
                    month_learned = month_avg[month] / overall_avg
                    month_factors[month] = 0.5 * month_factors.get(month, 1.0) + 0.5 * month_learned
        
        # ================== 应用因子 ==================
        # 1. 星期因子
        weekday_mult = weekday_factors.get(weekday, 1.0)
        if weekday in [5, 6]:
            factors.append(f"{weekday_names[weekday]}+{int((weekday_mult-1)*100)}%")
        multiplier *= weekday_mult
        
        # 2. 节假日因子
        holiday_info = self._get_holiday_info(forecast_date)
        if holiday_info["factor"] > 1.0:
            multiplier *= holiday_info["factor"]
            uncertainty += 0.1
            factors.append(f"{holiday_info['name']}+{int((holiday_info['factor']-1)*100)}%")
        
        # 3. 月份因子
        month_mult = month_factors.get(forecast_date.month, 1.0)
        multiplier *= month_mult
        
        # 4. 天气因子
        weather_factor = self._get_weather_factor(forecast_date)
        if weather_factor > 1.0:
            multiplier *= weather_factor
            factors.append(f"季节性天气+{int((weather_factor-1)*100)}%")
        
        # 5. 应用历史学习因子
        if learned_from_history:
            # 混合预设因子和历史因子（60%历史 + 40%预设）
            multiplier = 0.4 * multiplier + 0.6 * history_factor * (multiplier / max(0.5, history_factor))
        
        # 计算最终预测值
        predicted = base_avg * multiplier
        
        # 添加随机波动（基于日期种子，确保可重复）
        seed = int(forecast_date.toordinal()) + hash(store_id) % 1000
        rng = np.random.default_rng(seed)
        noise = rng.normal(0, predicted * 0.05)
        predicted = max(0.1, predicted + noise)
        
        return {
            "predicted": round(predicted, 1),
            "lower": round(max(0.0, predicted * (1 - uncertainty)), 1),
            "upper": round(predicted * (1 + uncertainty), 1),
            "factors": factors,
            "multiplier": round(multiplier, 2),
        }
    
    def _classify_date(self, d: date) -> str:
        """
        将日期分类为不同类型，用于历史数据学习
        
        类型包括：
        - 节假日：公众假期、特殊节日
        - 节前：重要节日前1-7天
        - 周末：周六、周日
        - 工作日：普通工作日
        """
        # 检查是否是节假日
        holiday_info = self._get_holiday_info(d)
        if holiday_info["type"] == "holiday":
            return f"节假日-{holiday_info['category']}"
        elif holiday_info["type"] == "pre_holiday":
            return f"节前-{holiday_info['category']}"
        
        # 周末
        if d.weekday() >= 5:
            return "周末"
        
        return "工作日"
    
    def _get_holiday_info(self, forecast_date: date) -> Dict[str, Any]:
        """获取节假日详细信息"""
        year = forecast_date.year
        month = forecast_date.month
        day = forecast_date.day
        key = (month, day)
        
        # 香港公众假期分类
        holidays = {
            # (月, 日): (名称, 类别, 因子)
            (1, 1): ("元旦", "新年", 1.25),
            (5, 1): ("劳动节", "公众假期", 1.20),
            (7, 1): ("回归日", "公众假期", 1.15),
            (10, 1): ("国庆节", "国庆", 1.30),
            (10, 2): ("国庆节", "国庆", 1.25),
            (12, 24): ("平安夜", "圣诞", 1.30),
            (12, 25): ("圣诞节", "圣诞", 1.35),
            (12, 26): ("节礼日", "圣诞", 1.25),
            (12, 31): ("除夕", "新年", 1.20),
        }
        
        # 检查固定假期
        if key in holidays:
            name, category, factor = holidays[key]
            return {"type": "holiday", "name": name, "category": category, "factor": factor}
        
        # 农历新年（近似日期）
        lunar_new_year = {
            2025: [(1, 29), (1, 30), (1, 31), (2, 1)],
            2026: [(2, 17), (2, 18), (2, 19), (2, 20)],
            2027: [(2, 6), (2, 7), (2, 8), (2, 9)],
        }
        
        if year in lunar_new_year:
            lny_dates = lunar_new_year[year]
            for i, lny_date in enumerate(lny_dates):
                if key == lny_date:
                    factor = 1.40 if i == 0 else 1.35 - i * 0.05
                    return {"type": "holiday", "name": "农历新年", "category": "春节", "factor": factor}
            
            # 检查节前日期
            first_lny = date(year, lny_dates[0][0], lny_dates[0][1])
            days_before = (first_lny - forecast_date).days
            if 1 <= days_before <= 14:
                # 节前采购高峰
                factor = 1.10 + (14 - days_before) * 0.02
                return {"type": "pre_holiday", "name": "春节前", "category": "春节", "factor": factor}
        
        # 检查其他节前日期
        pre_holiday_periods = [
            (date(year, 12, 18), date(year, 12, 23), "圣诞前", "圣诞", 1.15),
            (date(year, 12, 26), date(year, 12, 30), "新年前", "新年", 1.10),
        ]
        
        for start, end, name, category, factor in pre_holiday_periods:
            if start <= forecast_date <= end:
                return {"type": "pre_holiday", "name": name, "category": category, "factor": factor}
        
        return {"type": "normal", "name": "", "category": "", "factor": 1.0}
    
    def _get_weather_factor(self, forecast_date: date) -> float:
        """获取天气因子（基于香港季节性模式）"""
        month = forecast_date.month
        day = forecast_date.day
        
        # 香港天气模式
        # 雨季 (5-9月): 可能增加室内活动，药品需求上升
        # 台风季 (7-9月): 大幅增加应急物资需求
        # 冬季 (12-2月): 感冒药需求上升
        
        if month in [7, 8, 9]:  # 台风季节
            # 模拟台风概率
            seed = int(forecast_date.toordinal())
            rng = np.random.default_rng(seed)
            if rng.random() < 0.15:  # 15% 概率台风天气
                return 1.25
            return 1.05
        elif month in [5, 6]:  # 雨季开始
            return 1.03
        elif month in [12, 1, 2]:  # 冬季
            return 1.08  # 感冒季节
        elif month in [3, 4]:  # 潮湿季节
            return 1.02
        
        return 1.0

    def get_inventory_outlook(
        self,
        forecast_days: int = 7,
        ecdc_ids: Optional[List[str]] = None,
        sku_ids: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        self._ensure_models()

        ecdcs = ecdc_ids or list(ECDC_PROFILES.keys())
        skus = sku_ids or list(SKU_PROFILES.keys())
        start = (self._forecast_reference_date or date.today()) + timedelta(days=1)
        end = start + timedelta(days=forecast_days - 1)

        demand_rows = self.get_demand_forecasts(start, end, sku_ids=skus)
        daily_demand: Dict[tuple[str, date], float] = {}
        for row in demand_rows:
            key = (row["sku_id"], datetime.strptime(row["date"], "%Y-%m-%d").date())
            daily_demand[key] = daily_demand.get(key, 0.0) + float(row["forecast_demand"])

        results: List[Dict[str, Any]] = []
        for ecdc_id in ecdcs:
            ecdc_profile = ECDC_PROFILES.get(ecdc_id, {"name": ecdc_id, "share": 0.5})
            for sku_id in skus:
                sku_profile = SKU_PROFILES[sku_id]
                seed = sum(ord(ch) for ch in f"{ecdc_id}:{sku_id}")
                rng = np.random.default_rng(seed)
                current_stock = float(sku_profile["base_stock"] + rng.integers(-20, 25))

                for day_offset in range(forecast_days):
                    forecast_date = start + timedelta(days=day_offset)
                    committed_demand = daily_demand.get((sku_id, forecast_date), 0.0) * float(ecdc_profile["share"])
                    expected_arrival = float(sku_profile["daily_arrival"] * (1.2 if day_offset % 3 == 0 else 0.8))
                    safety_buffer = committed_demand * 0.25
                    projected_available = max(0.0, current_stock + expected_arrival - committed_demand)

                    if projected_available < safety_buffer:
                        status = "shortage"
                    elif projected_available > committed_demand * 2.2 + 40:
                        status = "overstock"
                    else:
                        status = "normal"

                    results.append(
                        {
                            "ecdc_id": ecdc_id,
                            "ecdc_name": ecdc_profile["name"],
                            "sku_id": sku_id,
                            "sku_name": sku_profile["name"],
                            "forecast_date": forecast_date.isoformat(),
                            "current_stock": round(current_stock, 1),
                            "expected_arrival": round(expected_arrival, 1),
                            "committed_demand": round(committed_demand, 1),
                            "projected_available": round(projected_available, 1),
                            "stock_status": status,
                        }
                    )

                    current_stock = projected_available

        return results

    def get_pickup_promise(self, store_id: str, sku_ids: List[str], order_time: Optional[datetime] = None) -> Dict[str, Any]:
        self._ensure_models()

        order_time = order_time or datetime.now()
        forecast_date = (self._forecast_reference_date or order_time.date()) + timedelta(days=1)
        sla_forecast = self.sla_predictor.predict_sla_performance(store_id, forecast_date)

        route_minutes = 25 + 8 * len(sku_ids)
        risk_weight = sum(float(value) for value in sla_forecast.risk_factors.values())
        processing_minutes = 70 + 10 * len(sku_ids) + risk_weight * 80
        pickup = self.sla_predictor.predict_pickup_time(
            {
                "order_time": order_time,
                "route_minutes": route_minutes,
                "processing_minutes": processing_minutes,
            },
            route_plan=None,
        )

        predicted_pickup_time: datetime = pickup["predicted_pickup_time"]
        promised_ready_time = max(order_time + timedelta(hours=4), predicted_pickup_time)
        uncertainty = max(0.03, sla_forecast.confidence_interval[1] - sla_forecast.confidence_interval[0])
        confidence = self.sla_predictor.calculate_sla_probability(promised_ready_time, predicted_pickup_time, uncertainty)

        return {
            "store_id": store_id,
            "store_name": self._get_store_name(store_id),
            "order_time": order_time.isoformat(),
            "promised_ready_time": promised_ready_time.isoformat(),
            "estimated_ready_time": predicted_pickup_time.isoformat(),
            "confidence": round(confidence, 3),
            "risk_factors": [
                {"factor": key, "impact": round(float(value), 3)}
                for key, value in sorted(sla_forecast.risk_factors.items(), key=lambda item: item[1], reverse=True)
            ],
            "window_description": f"预计 {predicted_pickup_time.strftime('%H:%M')} 前可取",
        }

    def get_sla_alerts(self, store_ids: Optional[List[str]] = None, forecast_days: int = 3, threshold: float = 0.92) -> List[Dict[str, Any]]:
        self._ensure_models()

        training = self._get_training_frame()
        stores = store_ids or sorted(training["fulfillment_store_code"].astype(str).unique().tolist())[:10]
        forecasts = self.sla_predictor.predict(forecast_horizon=forecast_days, store_codes=stores)
        alerts = self.sla_predictor.generate_sla_alerts(forecasts, threshold=threshold)
        normalized: List[Dict[str, Any]] = []
        for item in alerts:
            normalized.append(
                {
                    "alert_id": f"ML-{hash((item['store_code'], item['forecast_date'], item['alert_type'])) & 0xFFFFFFFF:08X}",
                    "alert_time": datetime.now().isoformat(),
                    "risk_level": item.get("severity", "medium"),
                    "affected_entity": item["store_code"],
                    "entity_type": "store",
                    "alert_description": self._describe_alert(item),
                    "bottleneck_type": "store",
                    "status": "pending",
                }
            )
        return normalized

    def get_model_info(self) -> Dict[str, Any]:
        self._ensure_models()
        return {
            "demand_model": self.forecaster.get_model_info(),
            "sla_model": self.sla_predictor.get_model_info(),
            "training_samples": 0 if self._training_frame is None else len(self._training_frame),
        }

    def _ensure_models(self) -> None:
        training = self._get_training_frame()
        if not self.forecaster.is_trained:
            self.forecaster.train(training.copy())
        if not self.sla_predictor.is_trained:
            self.sla_predictor.train(training.copy())

    def _get_training_frame(self) -> pd.DataFrame:
        if self._training_frame is not None:
            return self._training_frame

        try:
            daily = pd.DataFrame(self.data_service.get_daily_orders())
        except Exception as exc:
            logger.warning("Failed to load daily orders from data service: %s", exc)
            daily = pd.DataFrame()

        if daily.empty:
            self._training_frame = self._build_fallback_training_frame()
            self._forecast_reference_date = pd.to_datetime(self._training_frame["order_date"]).max().date()
            return self._training_frame

        daily = daily.rename(columns={"dt": "order_date"})
        daily["order_date"] = pd.to_datetime(daily["order_date"])
        if "store_code" not in daily.columns:
            daily["store_code"] = "10001"
        daily["fulfillment_store_code"] = daily["store_code"].astype(str)
        if "total_quantity" not in daily.columns and "order_count" in daily.columns:
            daily["total_quantity"] = daily["order_count"].astype(float) * 2.0
        daily["unique_sku_count"] = daily.get("avg_sku_per_order", 2.0)
        daily = self._add_engineered_features(daily)
        self._training_frame = daily
        self._forecast_reference_date = daily["order_date"].max().date()
        return self._training_frame

    def _build_fallback_training_frame(self) -> pd.DataFrame:
        stores = ["10001", "10002", "10003"]
        dates = pd.date_range(end=pd.Timestamp.today().normalize(), periods=180, freq="D")
        rows: List[Dict[str, Any]] = []
        for store_idx, store_code in enumerate(stores):
            for day_idx, dt in enumerate(dates):
                seasonal = 55 + 12 * np.sin(2 * np.pi * day_idx / 30.0) + store_idx * 4
                weekly = 10 if dt.dayofweek >= 5 else 0
                quantity = max(10.0, seasonal + weekly)
                rows.append(
                    {
                        "order_date": dt,
                        "store_code": store_code,
                        "fulfillment_store_code": store_code,
                        "order_count": max(5, int(quantity / 3)),
                        "total_quantity": quantity,
                        "unique_sku_count": 3 + (day_idx % 4),
                    }
                )
        return self._add_engineered_features(pd.DataFrame(rows))

    def _add_engineered_features(self, frame: pd.DataFrame) -> pd.DataFrame:
        data = frame.copy()
        dates = pd.to_datetime(data["order_date"])
        day_of_year = dates.dt.dayofyear.to_numpy(dtype=float)
        weekday = dates.dt.dayofweek.to_numpy(dtype=float)

        data["weather_temperature_high"] = 25 + 6 * np.sin(2 * np.pi * day_of_year / 365.25)
        data["weather_temperature_low"] = data["weather_temperature_high"] - 7
        data["weather_humidity"] = 72 + 10 * np.cos(2 * np.pi * day_of_year / 365.25)
        data["weather_rainfall"] = np.where(dates.dt.month.isin([5, 6, 7, 8, 9]), 5.0, 1.5)
        data["weather_wind_speed"] = 11 + 2 * np.sin(2 * np.pi * day_of_year / 365.25 + 0.4)
        data["is_weekend"] = dates.dt.dayofweek.isin([5, 6]).astype(int)
        data["is_holiday"] = ((dates.dt.month == 1) & (dates.dt.day == 1)).astype(int)
        data["traffic_congestion_level"] = np.where(weekday < 5, 3.2, 2.1)
        data["traffic_speed_avg"] = np.where(weekday < 5, 38.0, 48.0)

        quantity = pd.to_numeric(data["total_quantity"], errors="coerce").fillna(0.0)
        baseline = max(quantity.mean(), 1.0)
        demand_ratio = quantity / baseline
        data["sla_rate"] = (
            0.965
            - 0.03 * np.clip(demand_ratio - 1.0, 0.0, None)
            - 0.02 * data["is_weekend"]
            - 0.01 * data["is_holiday"]
        ).clip(0.82, 0.99)

        return data

    def _build_forecast_lookup(self, stores: List[str], end_date: date) -> Dict[tuple[str, date], Dict[str, float]]:
        lookup: Dict[tuple[str, date], Dict[str, float]] = {}
        horizon = max(0, (end_date - (self._forecast_reference_date or end_date)).days)
        if horizon <= 0:
            return lookup

        forecasts = self.forecaster.predict(forecast_horizon=horizon)
        # 将门店ID统一转为字符串进行比较
        stores_set = set(str(s) for s in stores)
        for forecast in forecasts:
            store_code_str = str(forecast.store_code)
            if store_code_str not in stores_set:
                continue
            lookup[(store_code_str, forecast.forecast_date)] = {
                "predicted": float(forecast.predicted_demand),
                "lower": float(forecast.confidence_intervals.get("P10", forecast.predicted_demand)),
                "upper": float(forecast.confidence_intervals.get("P90", forecast.predicted_demand)),
            }
        return lookup

    @staticmethod
    def _build_actual_lookup(training: pd.DataFrame) -> Dict[tuple[str, date], float]:
        actuals: Dict[tuple[str, date], float] = {}
        for row in training.itertuples(index=False):
            # 统一转为字符串类型
            store_code = str(row.fulfillment_store_code)
            order_date = pd.to_datetime(row.order_date).date()
            actuals[(store_code, order_date)] = float(row.total_quantity)
        return actuals

    def _get_store_name(self, store_id: str) -> str:
        """Cached store name lookup"""
        if store_id in self._store_name_cache:
            return self._store_name_cache[store_id]
        
        # 批量加载并缓存
        self._load_store_names_cache()
        return self._store_name_cache.get(store_id, f"Store {store_id}")
    
    def _get_store_names_batch(self, store_ids: List[str]) -> Dict[str, str]:
        """批量获取门店名称，避免循环中重复查询"""
        if not self._store_name_cache:
            self._load_store_names_cache()
        
        return {sid: self._store_name_cache.get(sid, f"Store {sid}") for sid in store_ids}
    
    def _load_store_names_cache(self) -> None:
        """加载门店名称到缓存"""
        if self._store_name_cache:
            return
        
        try:
            stores = self.data_service.get_stores()
            for store in stores:
                self._store_name_cache[str(store["store_code"])] = store["store_name"]
            logger.info(f"Cached {len(self._store_name_cache)} store names")
        except Exception as e:
            logger.warning(f"Failed to load store names: {e}")

    @staticmethod
    def _describe_alert(alert: Dict[str, Any]) -> str:
        if alert["alert_type"] == "sla_risk":
            return f"门店 {alert['store_code']} 预测SLA降至 {alert['predicted_sla']:.1%}"
        high_risk = ", ".join(alert.get("high_risk_factors", {}).keys()) or "多项风险因子"
        return f"门店 {alert['store_code']} 出现高风险因子: {high_risk}"


def get_forecasting_service() -> ForecastingService:
    return ForecastingService()
