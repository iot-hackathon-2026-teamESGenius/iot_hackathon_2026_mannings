#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
万宁SLA优化系统 - Prophet需求预测模块
基于Facebook Prophet的时间序列预测

创建时间: 2026-03-17
作者: 冼思敏 (Team ESGenius)
"""

import pandas as pd
import numpy as np
from datetime import datetime, date, timedelta
from typing import List, Dict, Optional, Tuple, Any
import logging
from pathlib import Path

try:
    from prophet import Prophet
    from prophet.diagnostics import cross_validation, performance_metrics
    PROPHET_AVAILABLE = True
except ImportError:
    PROPHET_AVAILABLE = False
    logging.warning("Prophet not available. Install with: pip install prophet")

import sys
project_root = Path(__file__).parent.parent.parent
sys.path.append(str(project_root))

try:
    from core.interfaces import DemandForecaster
    from core.data_schema import DemandForecast, WeatherData, PublicHoliday
except ImportError:
    sys.path.append(str(project_root / "src"))
    from core.interfaces import DemandForecaster
    from core.data_schema import DemandForecast, WeatherData, PublicHoliday

logger = logging.getLogger(__name__)


class _FallbackProphetModel:
    """Minimal Prophet-compatible fallback for offline environments."""

    def __init__(self, interval_width: float = 0.8, **_: Any):
        self.interval_width = interval_width
        self.history = pd.DataFrame()
        self.last_date = None
        self.base_level = 0.0
        self.trend_slope = 0.0
        self.weekday_effects = {day: 0.0 for day in range(7)}
        self.residual_std = 1.0
        self.regressor_weights: Dict[str, float] = {}
        self.holidays = pd.DataFrame()

    def add_seasonality(self, **_: Any) -> None:
        return None

    def add_regressor(self, name: str, prior_scale: float = 0.1) -> None:
        self.regressor_weights[name] = min(0.05, max(0.005, prior_scale * 0.02))

    def fit(self, prophet_data: pd.DataFrame) -> None:
        history = prophet_data.sort_values("ds").reset_index(drop=True).copy()
        if history.empty:
            raise ValueError("训练数据不能为空")

        history["t"] = np.arange(len(history), dtype=float)
        self.history = history
        self.last_date = history["ds"].max()
        self.base_level = float(history["y"].mean())

        if len(history) > 1:
            coeffs = np.polyfit(history["t"], history["y"], deg=1)
            self.trend_slope = float(coeffs[0])

        history["weekday"] = history["ds"].dt.dayofweek
        weekday_mean = history.groupby("weekday")["y"].mean()
        self.weekday_effects = {
            day: float(weekday_mean.get(day, self.base_level) - self.base_level)
            for day in range(7)
        }

        fitted = self._predict_core(history)
        residuals = history["y"].to_numpy(dtype=float) - fitted
        residual_std = float(np.std(residuals)) if len(residuals) > 1 else 0.0
        self.residual_std = max(1.0, residual_std, self.base_level * 0.05)

    def make_future_dataframe(self, periods: int) -> pd.DataFrame:
        if self.last_date is None:
            raise ValueError("模型尚未训练")
        dates = pd.date_range(end=self.last_date + pd.Timedelta(days=periods), periods=len(self.history) + periods, freq="D")
        return pd.DataFrame({"ds": dates})

    def predict(self, future_df: pd.DataFrame) -> pd.DataFrame:
        if self.last_date is None:
            raise ValueError("模型尚未训练")

        future = future_df.copy()
        yhat = np.maximum(1.0, self._predict_core(future))
        margin = np.minimum(1.28 * self.residual_std, yhat * 0.8)
        future["yhat"] = yhat
        future["yhat_lower"] = np.maximum(0.0, yhat - margin)
        future["yhat_upper"] = np.maximum(future["yhat"], yhat + margin)
        return future

    def _predict_core(self, df: pd.DataFrame) -> np.ndarray:
        ds = pd.to_datetime(df["ds"])
        if self.history.empty:
            offsets = np.arange(len(df), dtype=float)
        else:
            min_date = self.history["ds"].min()
            offsets = (ds - min_date).dt.days.to_numpy(dtype=float)

        values = np.full(len(df), self.base_level, dtype=float)
        values += offsets * self.trend_slope
        values += np.array([self.weekday_effects.get(int(day), 0.0) for day in ds.dt.dayofweek], dtype=float)

        for regressor, weight in self.regressor_weights.items():
            if regressor in df.columns:
                series = pd.to_numeric(df[regressor], errors="coerce").fillna(0.0).to_numpy(dtype=float)
                values += (series - float(np.mean(series) if len(series) else 0.0)) * weight

        return np.maximum(0.0, values)

class ProphetForecaster(DemandForecaster):
    """基于Prophet的需求预测器"""
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or self._get_default_config()
        self.models = {}  # store_code -> model
        self.is_trained = False
        self.feature_columns = []
        self.backend = "prophet" if PROPHET_AVAILABLE else "fallback"

        if not PROPHET_AVAILABLE:
            logger.warning("Prophet未安装，使用内置统计回退模型")
    
    def _get_default_config(self) -> Dict[str, Any]:
        """获取默认配置"""
        return {
            'seasonality_mode': 'multiplicative',
            'yearly_seasonality': True,
            'weekly_seasonality': True,
            'daily_seasonality': False,
            'holidays_prior_scale': 10.0,
            'seasonality_prior_scale': 10.0,
            'changepoint_prior_scale': 0.05,
            'interval_width': 0.8,
            'uncertainty_samples': 1000,
            'mcmc_samples': 0
        }
    
    def train(self, training_data: pd.DataFrame, **kwargs) -> None:
        """训练预测模型"""
        logger.info("开始训练Prophet预测模型...")
        
        try:
            # 数据预处理
            processed_data = self._preprocess_training_data(training_data)
            
            # 按门店分组训练
            store_codes = processed_data['store_code'].unique()
            
            # 限制训练的门店数量，避免太慢
            max_stores = 10
            if len(store_codes) > max_stores:
                logger.info(f"门店数量({len(store_codes)})超过限制，只训练前{max_stores}个门店")
                store_codes = store_codes[:max_stores]
            
            for store_code in store_codes:
                store_data = processed_data[processed_data['store_code'] == store_code].copy()
                
                # 准备Prophet数据格式
                prophet_data = self._prepare_prophet_data(store_data)
                
                if len(prophet_data) < 30:  # 需要至少30天数据
                    logger.warning(f"门店 {store_code} 数据点不足({len(prophet_data)}天)，跳过训练")
                    continue
                
                # 创建和配置Prophet模型
                model_cls = Prophet if PROPHET_AVAILABLE else _FallbackProphetModel
                model = model_cls(
                    seasonality_mode=self.config['seasonality_mode'],
                    yearly_seasonality=self.config['yearly_seasonality'],
                    weekly_seasonality=self.config['weekly_seasonality'],
                    daily_seasonality=self.config['daily_seasonality'],
                    holidays_prior_scale=self.config['holidays_prior_scale'],
                    seasonality_prior_scale=self.config['seasonality_prior_scale'],
                    changepoint_prior_scale=self.config['changepoint_prior_scale'],
                    interval_width=self.config['interval_width'],
                    uncertainty_samples=self.config['uncertainty_samples'],
                    mcmc_samples=self.config['mcmc_samples']
                )
                
                # 添加自定义季节性
                model.add_seasonality(name='monthly', period=30.5, fourier_order=5)
                
                # 添加假期
                holidays = self._create_holidays_dataframe()
                if not holidays.empty:
                    model.holidays = holidays
                
                # 添加外部回归变量（简化日志输出）
                for col in self.feature_columns:
                    if col in prophet_data.columns:
                        if 'weather' in col:
                            prior_scale = 0.5
                        elif 'holiday' in col or 'weekend' in col:
                            prior_scale = 1.0
                        elif 'traffic' in col:
                            prior_scale = 0.3
                        else:
                            prior_scale = 0.1
                        model.add_regressor(col, prior_scale=prior_scale)
                
                # 训练模型
                model.fit(prophet_data)
                self.models[store_code] = model
            
            self.is_trained = True
            logger.info(f"✅ 所有模型训练完成，共训练 {len(self.models)} 个门店模型")
            
        except Exception as e:
            logger.error(f"模型训练失败: {str(e)}")
            raise
    
    def predict(self, forecast_horizon: int, **kwargs) -> List[DemandForecast]:
        """执行预测"""
        if not self.is_trained:
            raise ValueError("模型尚未训练，请先调用train()方法")
        
        logger.info(f"开始预测未来 {forecast_horizon} 天的需求...")
        
        forecasts = []
        
        try:
            for store_code, model in self.models.items():
                logger.info(f"预测门店 {store_code} 的需求...")
                
                # 创建未来日期
                future = model.make_future_dataframe(periods=forecast_horizon)
                
                # 添加外部特征（如果有）
                future = self._add_future_features(future, store_code)
                
                # 执行预测
                forecast = model.predict(future)
                
                # 提取预测结果
                future_forecast = forecast.tail(forecast_horizon)
                
                for _, row in future_forecast.iterrows():
                    demand_forecast = DemandForecast(
                        store_code=store_code,
                        sku_id="aggregate",  # 聚合预测
                        forecast_date=row['ds'].date(),
                        predicted_demand=max(0, row['yhat']),  # 确保非负
                        confidence_intervals={
                            'P10': max(0, row['yhat_lower']),
                            'P50': max(0, row['yhat']),
                            'P90': max(0, row['yhat_upper'])
                        },
                        external_factors=self._extract_external_factors(row),
                        model_version="prophet_v1.0",
                        forecast_timestamp=datetime.now()
                    )
                    forecasts.append(demand_forecast)
            
            logger.info(f"✅ 预测完成，生成 {len(forecasts)} 个预测结果")
            return forecasts
            
        except Exception as e:
            logger.error(f"预测失败: {str(e)}")
            raise
    
    def predict_store_demand(self, store_code: str, sku_id: str, forecast_date: date) -> DemandForecast:
        """预测单店单SKU需求"""
        if store_code not in self.models:
            raise ValueError(f"门店 {store_code} 的模型不存在")
        
        model = self.models[store_code]
        
        # 创建预测数据
        future_df = pd.DataFrame({'ds': [pd.to_datetime(forecast_date)]})
        future_df = self._add_future_features(future_df, store_code)
        
        # 执行预测
        forecast = model.predict(future_df)
        row = forecast.iloc[0]
        
        return DemandForecast(
            store_code=store_code,
            sku_id=sku_id,
            forecast_date=forecast_date,
            predicted_demand=max(0, row['yhat']),
            confidence_intervals={
                'P10': max(0, row['yhat_lower']),
                'P50': max(0, row['yhat']),
                'P90': max(0, row['yhat_upper'])
            },
            external_factors=self._extract_external_factors(row),
            model_version="prophet_v1.0",
            forecast_timestamp=datetime.now()
        )
    
    def predict_batch_demand(self, store_codes: List[str], sku_ids: List[str], 
                           forecast_dates: List[date]) -> List[DemandForecast]:
        """批量预测需求"""
        forecasts = []
        
        for store_code in store_codes:
            for sku_id in sku_ids:
                for forecast_date in forecast_dates:
                    try:
                        forecast = self.predict_store_demand(store_code, sku_id, forecast_date)
                        forecasts.append(forecast)
                    except Exception as e:
                        logger.warning(f"预测失败 {store_code}-{sku_id}-{forecast_date}: {str(e)}")
        
        return forecasts
    
    def get_confidence_intervals(self, prediction: float, confidence_levels: List[float]) -> Dict[str, float]:
        """获取预测置信区间"""
        intervals = {}
        
        # 基于预测值的相对标准差
        relative_std = 0.15  # 15%的相对标准差
        std = prediction * relative_std
        
        for level in confidence_levels:
            if level == 0.1:
                # P10: 10th percentile
                intervals['P10'] = max(0, prediction - 1.28 * std)
            elif level == 0.5:
                # P50: median (50th percentile)
                intervals['P50'] = prediction
            elif level == 0.9:
                # P90: 90th percentile
                intervals['P90'] = prediction + 1.28 * std
            else:
                # 使用正态分布近似计算其他百分位数
                try:
                    from scipy.stats import norm
                    z_score = norm.ppf(level)
                    intervals[f'P{int(level*100)}'] = max(0, prediction + z_score * std)
                except ImportError:
                    # 如果scipy不可用，使用线性近似
                    if level < 0.5:
                        z_approx = -2.0 + 4.0 * level  # 简单线性映射
                    else:
                        z_approx = 4.0 * level - 2.0
                    intervals[f'P{int(level*100)}'] = max(0, prediction + z_approx * std)
        
        return intervals
    
    def evaluate(self, test_data: pd.DataFrame) -> Dict[str, float]:
        """评估模型性能"""
        if not self.is_trained:
            raise ValueError("模型尚未训练")
        
        logger.info("开始评估模型性能...")
        
        metrics = {}
        
        try:
            for store_code, model in self.models.items():
                logger.info(f"评估门店 {store_code} 的模型...")

                if PROPHET_AVAILABLE:
                    df_cv = cross_validation(
                        model,
                        initial='30 days',
                        period='7 days',
                        horizon='7 days'
                    )

                    df_p = performance_metrics(df_cv)

                    metrics[store_code] = {
                        'mape': df_p['mape'].mean(),
                        'mae': df_p['mae'].mean(),
                        'rmse': df_p['rmse'].mean(),
                        'coverage': df_p['coverage'].mean()
                    }
                else:
                    processed = self._preprocess_training_data(test_data)
                    store_test = processed[processed['store_code'] == store_code].copy()
                    if store_test.empty:
                        continue

                    prediction_input = self._prepare_prophet_data(store_test)
                    prediction = model.predict(prediction_input)
                    actual = store_test['y'].to_numpy(dtype=float)
                    pred = prediction['yhat'].to_numpy(dtype=float)
                    denom = np.maximum(np.abs(actual), 1.0)

                    metrics[store_code] = {
                        'mape': float(np.mean(np.abs(actual - pred) / denom)),
                        'mae': float(np.mean(np.abs(actual - pred))),
                        'rmse': float(np.sqrt(np.mean((actual - pred) ** 2))),
                        'coverage': float(np.mean((actual >= prediction['yhat_lower']) & (actual <= prediction['yhat_upper'])))
                    }
            
            # 计算总体指标
            overall_metrics = {
                'overall_mape': np.mean([m['mape'] for m in metrics.values()]),
                'overall_mae': np.mean([m['mae'] for m in metrics.values()]),
                'overall_rmse': np.mean([m['rmse'] for m in metrics.values()]),
                'overall_coverage': np.mean([m['coverage'] for m in metrics.values()]),
                'store_metrics': metrics
            }
            
            logger.info(f"✅ 模型评估完成，总体MAPE: {overall_metrics['overall_mape']:.3f}")
            return overall_metrics
            
        except Exception as e:
            logger.error(f"模型评估失败: {str(e)}")
            return {'error': str(e)}

    def get_model_info(self) -> Dict[str, Any]:
        """获取模型元信息"""
        return {
            'backend': self.backend,
            'is_trained': self.is_trained,
            'store_count': len(self.models),
            'feature_columns': list(self.feature_columns),
            'config': self.config
        }
    
    def save_model(self, filepath: str) -> None:
        """保存模型"""
        import pickle
        
        model_data = {
            'models': self.models,
            'config': self.config,
            'is_trained': self.is_trained,
            'feature_columns': self.feature_columns
        }
        
        with open(filepath, 'wb') as f:
            pickle.dump(model_data, f)
        
        logger.info(f"✅ 模型已保存到 {filepath}")
    
    def load_model(self, filepath: str) -> None:
        """加载模型"""
        import pickle
        
        with open(filepath, 'rb') as f:
            model_data = pickle.load(f)
        
        self.models = model_data['models']
        self.config = model_data['config']
        self.is_trained = model_data['is_trained']
        self.feature_columns = model_data.get('feature_columns', [])
        
        logger.info(f"✅ 模型已从 {filepath} 加载")
    
    # ==================== 辅助方法 ====================
    
    def _preprocess_training_data(self, data: pd.DataFrame) -> pd.DataFrame:
        """预处理训练数据"""
        processed = data.copy()
        
        # 确保日期列存在
        if 'order_date' in processed.columns:
            processed['ds'] = pd.to_datetime(processed['order_date'])
        elif 'ds' not in processed.columns:
            raise ValueError("数据必须包含 'order_date' 或 'ds' 列")
        
        # 按门店和日期聚合
        if 'store_code' not in processed.columns:
            if 'fulfillment_store_code' in processed.columns:
                processed['store_code'] = processed['fulfillment_store_code']
            else:
                raise ValueError("数据必须包含门店代码列")
        
        # 聚合每日需求
        agg_data = processed.groupby(['store_code', 'ds']).agg({
            'total_quantity': 'sum',
            'unique_sku_count': 'sum'
        }).reset_index()
        
        # 重命名为Prophet格式
        agg_data['y'] = agg_data['total_quantity']  # 目标变量
        
        # 添加外部特征
        feature_cols = [
            'weather_temperature_high', 'weather_temperature_low', 'weather_humidity', 
            'weather_rainfall', 'weather_wind_speed',
            'is_holiday', 'is_weekend', 'is_month_end', 'is_month_start',
            'traffic_congestion_level', 'traffic_speed_avg'
        ]
        self.feature_columns = []
        
        for col in feature_cols:
            if col in processed.columns:
                # 按日期聚合特征
                if col.startswith('weather_') or col.startswith('traffic_'):
                    # 数值特征取平均值
                    feature_data = processed.groupby(['store_code', 'ds'])[col].mean().reset_index()
                else:
                    # 布尔特征取最大值
                    feature_data = processed.groupby(['store_code', 'ds'])[col].max().reset_index()
                
                agg_data = agg_data.merge(feature_data, on=['store_code', 'ds'], how='left')
                self.feature_columns.append(col)
        
        # 添加时间特征
        agg_data['is_weekend'] = agg_data['ds'].dt.dayofweek.isin([5, 6]).astype(int)
        agg_data['is_month_end'] = (agg_data['ds'].dt.day >= 28).astype(int)
        agg_data['is_month_start'] = (agg_data['ds'].dt.day <= 3).astype(int)
        agg_data['day_of_week'] = agg_data['ds'].dt.dayofweek
        agg_data['month'] = agg_data['ds'].dt.month
        
        # 确保时间特征在feature_columns中
        time_features = ['is_weekend', 'is_month_end', 'is_month_start']
        for feature in time_features:
            if feature not in self.feature_columns:
                self.feature_columns.append(feature)
        
        return agg_data
    
    def _prepare_prophet_data(self, store_data: pd.DataFrame) -> pd.DataFrame:
        """准备Prophet数据格式"""
        prophet_data = store_data[['ds', 'y']].copy()
        
        # 添加外部回归变量
        for col in self.feature_columns:
            if col in store_data.columns:
                prophet_data[col] = store_data[col].fillna(0)
        
        # 确保数据按日期排序
        prophet_data = prophet_data.sort_values('ds').reset_index(drop=True)
        
        return prophet_data
    
    def _create_holidays_dataframe(self) -> pd.DataFrame:
        """创建假期数据框"""
        holidays = []
        
        # 香港主要公共假期
        years = [2025, 2026, 2027]
        
        for year in years:
            # 固定日期假期
            holidays.extend([
                {'holiday': 'New Year', 'ds': f'{year}-01-01', 'lower_window': 0, 'upper_window': 1},
                {'holiday': 'Labour Day', 'ds': f'{year}-05-01', 'lower_window': 0, 'upper_window': 0},
                {'holiday': 'National Day', 'ds': f'{year}-10-01', 'lower_window': 0, 'upper_window': 2},
                {'holiday': 'Christmas', 'ds': f'{year}-12-25', 'lower_window': -1, 'upper_window': 1},
                {'holiday': 'Boxing Day', 'ds': f'{year}-12-26', 'lower_window': 0, 'upper_window': 0},
            ])
            
            # 农历新年（近似日期）
            if year == 2025:
                holidays.append({'holiday': 'Chinese New Year', 'ds': '2025-01-29', 'lower_window': -1, 'upper_window': 3})
            elif year == 2026:
                holidays.append({'holiday': 'Chinese New Year', 'ds': '2026-02-17', 'lower_window': -1, 'upper_window': 3})
            elif year == 2027:
                holidays.append({'holiday': 'Chinese New Year', 'ds': '2027-02-06', 'lower_window': -1, 'upper_window': 3})
        
        if holidays:
            holidays_df = pd.DataFrame(holidays)
            holidays_df['ds'] = pd.to_datetime(holidays_df['ds'])
            return holidays_df
        else:
            return pd.DataFrame(columns=['holiday', 'ds', 'lower_window', 'upper_window'])
    
    def _add_future_features(self, future_df: pd.DataFrame, store_code: str) -> pd.DataFrame:
        """为未来数据添加特征"""
        # 添加基础时间特征
        future_df['is_weekend'] = future_df['ds'].dt.dayofweek.isin([5, 6]).astype(int)
        future_df['is_month_end'] = (future_df['ds'].dt.day >= 28).astype(int)
        future_df['is_month_start'] = (future_df['ds'].dt.day <= 3).astype(int)
        future_df['day_of_week'] = future_df['ds'].dt.dayofweek
        future_df['month'] = future_df['ds'].dt.month
        
        # 添加假期特征
        future_df['is_holiday'] = 0
        holidays_df = self._create_holidays_dataframe()
        if not holidays_df.empty:
            holiday_dates = set(holidays_df['ds'].dt.date)
            future_df['is_holiday'] = future_df['ds'].dt.date.isin(holiday_dates).astype(int)
        
        # 添加天气特征（使用季节性模式或天气预报）
        if 'weather_temperature_high' in self.feature_columns:
            # 基于月份的季节性温度模式
            month_temp_map = {1: 18, 2: 19, 3: 22, 4: 26, 5: 29, 6: 31, 
                            7: 32, 8: 32, 9: 30, 10: 27, 11: 23, 12: 19}
            future_df['weather_temperature_high'] = future_df['month'].map(month_temp_map)
            # 添加随机波动
            future_df['weather_temperature_high'] += np.random.normal(0, 2, len(future_df))
        
        if 'weather_temperature_low' in self.feature_columns:
            future_df['weather_temperature_low'] = future_df.get('weather_temperature_high', 25) - 8
        
        if 'weather_humidity' in self.feature_columns:
            # 香港湿度通常较高
            future_df['weather_humidity'] = 75 + np.random.normal(0, 10, len(future_df))
            future_df['weather_humidity'] = future_df['weather_humidity'].clip(50, 95)
        
        if 'weather_rainfall' in self.feature_columns:
            # 雨季(5-9月)降雨较多
            is_rainy_season = future_df['month'].isin([5, 6, 7, 8, 9])
            future_df['weather_rainfall'] = np.where(is_rainy_season, 
                                                   np.random.exponential(5, len(future_df)),
                                                   np.random.exponential(1, len(future_df)))
        
        if 'weather_wind_speed' in self.feature_columns:
            future_df['weather_wind_speed'] = 10 + np.random.normal(0, 5, len(future_df))
            future_df['weather_wind_speed'] = future_df['weather_wind_speed'].clip(0, 30)
        
        # 添加交通特征（基于时间模式）
        if 'traffic_congestion_level' in self.feature_columns:
            # 工作日交通更拥堵
            base_congestion = np.where(future_df['is_weekend'] == 0, 3, 2)
            future_df['traffic_congestion_level'] = base_congestion + np.random.normal(0, 0.5, len(future_df))
            future_df['traffic_congestion_level'] = future_df['traffic_congestion_level'].clip(1, 5)
        
        if 'traffic_speed_avg' in self.feature_columns:
            # 拥堵程度越高，平均速度越低
            congestion = future_df.get('traffic_congestion_level', 3)
            future_df['traffic_speed_avg'] = 60 - (congestion - 1) * 10 + np.random.normal(0, 5, len(future_df))
            future_df['traffic_speed_avg'] = future_df['traffic_speed_avg'].clip(20, 80)
        
        return future_df
    
    def _extract_external_factors(self, forecast_row) -> Dict[str, float]:
        """提取外部因子影响"""
        factors = {}
        
        # 从预测结果中提取各种影响因子
        if 'is_holiday' in forecast_row:
            factors['holiday_impact'] = float(forecast_row.get('is_holiday', 0))
        
        if 'is_weekend' in forecast_row:
            factors['weekend_impact'] = float(forecast_row.get('is_weekend', 0))
        
        if 'weather_temperature_high' in forecast_row:
            # 计算温度对需求的影响（简化）
            temp = float(forecast_row.get('weather_temperature_high', 25))
            factors['weather_impact'] = (temp - 25) / 25  # 相对于25度的影响
        
        return factors

# ==================== 工厂函数 ====================

def create_prophet_forecaster(config: Dict[str, Any] = None) -> ProphetForecaster:
    """创建Prophet预测器实例"""
    return ProphetForecaster(config)

# ==================== 测试和演示 ====================

if __name__ == "__main__":
    print("🔮 测试Prophet预测模块...")
    
    if not PROPHET_AVAILABLE:
        print("❌ Prophet未安装，请运行: pip install prophet")
        exit(1)
    
    # 创建预测器
    forecaster = ProphetForecaster()
    print("✅ Prophet预测器创建成功")
    
    # 创建示例训练数据
    dates = pd.date_range(start='2025-01-01', end='2025-12-31', freq='D')
    sample_data = pd.DataFrame({
        'order_date': dates,
        'store_code': '417',
        'total_quantity': 50 + 10 * np.sin(2 * np.pi * np.arange(len(dates)) / 365) + np.random.normal(0, 5, len(dates)),
        'unique_sku_count': 20 + 5 * np.sin(2 * np.pi * np.arange(len(dates)) / 365) + np.random.normal(0, 2, len(dates)),
        'is_weekend': dates.dayofweek.isin([5, 6]).astype(int),
        'is_holiday': 0,
        'weather_temperature_high': 25 + 5 * np.sin(2 * np.pi * np.arange(len(dates)) / 365) + np.random.normal(0, 2, len(dates)),
        'weather_humidity': 70 + 10 * np.sin(2 * np.pi * np.arange(len(dates)) / 365) + np.random.normal(0, 5, len(dates))
    })
    
    print(f"📊 创建示例数据: {len(sample_data)} 条记录")
    
    try:
        # 训练模型
        print("🚀 开始训练模型...")
        forecaster.train(sample_data)
        
        # 执行预测
        print("🔮 执行7天预测...")
        forecasts = forecaster.predict(forecast_horizon=7)
        
        print(f"✅ 预测完成，生成 {len(forecasts)} 个预测结果")
        
        # 显示预测结果
        for forecast in forecasts[:3]:  # 显示前3个结果
            print(f"   📅 {forecast.forecast_date}: {forecast.predicted_demand:.1f} (P10: {forecast.confidence_intervals['P10']:.1f}, P90: {forecast.confidence_intervals['P90']:.1f})")
        
        print("\n🎉 Prophet预测模块测试完成！")
        
    except Exception as e:
        print(f"❌ 测试失败: {str(e)}")
