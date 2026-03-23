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

        results: List[Dict[str, Any]] = []
        current = start_date
        while current <= end_date:
            for store_id in stores:
                store_name = self._get_store_name(store_id)
                aggregate = forecast_map.get((store_id, current))
                actual_total = actual_map.get((store_id, current))

                if aggregate is None and actual_total is not None:
                    aggregate = {
                        "predicted": float(actual_total),
                        "lower": max(0.0, actual_total * 0.9),
                        "upper": actual_total * 1.1,
                    }

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
                        }
                    )
            current += timedelta(days=1)

        return results

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
        for forecast in forecasts:
            if forecast.store_code not in stores:
                continue
            lookup[(forecast.store_code, forecast.forecast_date)] = {
                "predicted": float(forecast.predicted_demand),
                "lower": float(forecast.confidence_intervals.get("P10", forecast.predicted_demand)),
                "upper": float(forecast.confidence_intervals.get("P90", forecast.predicted_demand)),
            }
        return lookup

    @staticmethod
    def _build_actual_lookup(training: pd.DataFrame) -> Dict[tuple[str, date], float]:
        actuals: Dict[tuple[str, date], float] = {}
        for row in training.itertuples(index=False):
            actuals[(str(row.fulfillment_store_code), pd.to_datetime(row.order_date).date())] = float(row.total_quantity)
        return actuals

    def _get_store_name(self, store_id: str) -> str:
        try:
            stores = self.data_service.get_stores()
            for store in stores:
                if str(store["store_code"]) == str(store_id):
                    return store["store_name"]
        except Exception:
            pass
        return f"Store {store_id}"

    @staticmethod
    def _describe_alert(alert: Dict[str, Any]) -> str:
        if alert["alert_type"] == "sla_risk":
            return f"门店 {alert['store_code']} 预测SLA降至 {alert['predicted_sla']:.1%}"
        high_risk = ", ".join(alert.get("high_risk_factors", {}).keys()) or "多项风险因子"
        return f"门店 {alert['store_code']} 出现高风险因子: {high_risk}"


def get_forecasting_service() -> ForecastingService:
    return ForecastingService()
