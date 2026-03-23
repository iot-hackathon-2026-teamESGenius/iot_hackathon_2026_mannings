#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
万宁SLA优化系统 - SLA预测模块
基于机器学习的SLA表现预测

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
    from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
    from sklearn.model_selection import train_test_split, cross_val_score
    from sklearn.preprocessing import StandardScaler, LabelEncoder
    from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False
    logging.warning("Scikit-learn not available. Install with: pip install scikit-learn")

    class StandardScaler:
        def fit_transform(self, X):
            return np.asarray(X, dtype=float)

        def transform(self, X):
            return np.asarray(X, dtype=float)

    class LabelEncoder:
        def fit_transform(self, values):
            self.classes_ = np.array(sorted({str(v) for v in values}))
            mapping = {value: index for index, value in enumerate(self.classes_)}
            return np.array([mapping[str(v)] for v in values], dtype=int)

        def transform(self, values):
            mapping = {value: index for index, value in enumerate(self.classes_)}
            return np.array([mapping[str(v)] for v in values], dtype=int)

    class _FallbackRegressor:
        def __init__(self, **_: Any):
            self.mean_ = 0.95
            self.feature_importances_ = np.array([])

        def fit(self, X, y):
            X = np.asarray(X, dtype=float)
            y = np.asarray(y, dtype=float)
            self.mean_ = float(np.mean(y)) if len(y) else 0.95
            self.feature_importances_ = np.full(X.shape[1], 1.0 / max(1, X.shape[1])) if X.ndim == 2 else np.array([])
            self.estimators_ = []
            return self

        def predict(self, X):
            X = np.asarray(X, dtype=float)
            return np.full(len(X), self.mean_, dtype=float)

        def score(self, X, y):
            y = np.asarray(y, dtype=float)
            if len(y) == 0:
                return 0.0
            pred = self.predict(X)
            ss_res = float(np.sum((y - pred) ** 2))
            ss_tot = float(np.sum((y - np.mean(y)) ** 2))
            return 0.0 if ss_tot == 0 else 1.0 - ss_res / ss_tot

    RandomForestRegressor = _FallbackRegressor
    GradientBoostingRegressor = _FallbackRegressor

    def train_test_split(X, y, test_size=0.2, random_state=None):
        X = np.asarray(X)
        y = np.asarray(y)
        split_idx = max(1, int(len(X) * (1 - test_size)))
        split_idx = min(split_idx, len(X) - 1) if len(X) > 1 else len(X)
        return X[:split_idx], X[split_idx:], y[:split_idx], y[split_idx:]

    def mean_absolute_error(y_true, y_pred):
        y_true = np.asarray(y_true, dtype=float)
        y_pred = np.asarray(y_pred, dtype=float)
        return float(np.mean(np.abs(y_true - y_pred)))

    def mean_squared_error(y_true, y_pred):
        y_true = np.asarray(y_true, dtype=float)
        y_pred = np.asarray(y_pred, dtype=float)
        return float(np.mean((y_true - y_pred) ** 2))

    def r2_score(y_true, y_pred):
        y_true = np.asarray(y_true, dtype=float)
        y_pred = np.asarray(y_pred, dtype=float)
        ss_res = float(np.sum((y_true - y_pred) ** 2))
        ss_tot = float(np.sum((y_true - np.mean(y_true)) ** 2))
        return 0.0 if ss_tot == 0 else 1.0 - ss_res / ss_tot

import sys
project_root = Path(__file__).parent.parent.parent
sys.path.append(str(project_root))

try:
    from core.interfaces import SLAPredictor
    from core.data_schema import SLAForecast, WeatherData, TrafficCondition
except ImportError:
    sys.path.append(str(project_root / "src"))
    from core.interfaces import SLAPredictor
    from core.data_schema import SLAForecast, WeatherData, TrafficCondition

logger = logging.getLogger(__name__)

class MLSLAPredictor(SLAPredictor):
    """基于机器学习的SLA预测器"""
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or self._get_default_config()
        self.model = None
        self.scaler = StandardScaler()
        self.label_encoders = {}
        self.feature_columns = []
        self.is_trained = False
        self.feature_importance = {}
        self.reference_date = date.today()
        self.store_baseline_map: Dict[str, float] = {}
        
        if not SKLEARN_AVAILABLE:
            logger.warning("Scikit-learn不可用，将使用简化的预测方法")
    
    def _get_default_config(self) -> Dict[str, Any]:
        """获取默认配置"""
        return {
            'model_type': 'random_forest',  # 'random_forest', 'gradient_boosting'
            'target_sla_rate': 0.95,  # 目标SLA率
            'sla_time_window_hours': 24,  # SLA时间窗口
            'feature_selection_threshold': 0.01,  # 特征选择阈值
            'cross_validation_folds': 5,  # 交叉验证折数
            'test_size': 0.2,  # 测试集比例
            'random_state': 42,  # 随机种子
            'model_params': {
                'random_forest': {
                    'n_estimators': 100,
                    'max_depth': 10,
                    'min_samples_split': 5,
                    'min_samples_leaf': 2,
                    'random_state': 42
                },
                'gradient_boosting': {
                    'n_estimators': 100,
                    'learning_rate': 0.1,
                    'max_depth': 6,
                    'random_state': 42
                }
            }
        }
    
    def train(self, training_data: pd.DataFrame, **kwargs) -> None:
        """训练SLA预测模型"""
        logger.info("开始训练SLA预测模型...")
        
        try:
            # 数据预处理
            processed_data = self._preprocess_training_data(training_data)
            
            if processed_data.empty:
                raise ValueError("预处理后的训练数据为空")

            self.reference_date = pd.to_datetime(processed_data['order_date']).max().date()
            self.store_baseline_map = (
                processed_data.assign(
                    fulfillment_store_code=processed_data['fulfillment_store_code'].astype(str)
                ).groupby('fulfillment_store_code')['sla_rate']
                .mean()
                .astype(float)
                .to_dict()
            )
            
            # 特征工程
            features_df = self._engineer_features(processed_data)
            
            # 准备训练数据
            X, y = self._prepare_training_data(features_df)
            
            if len(X) == 0:
                raise ValueError("没有有效的训练样本")
            
            # 分割训练和测试数据
            X_train, X_test, y_train, y_test = train_test_split(
                X, y, 
                test_size=self.config['test_size'],
                random_state=self.config['random_state']
            )
            
            # 特征缩放
            X_train_scaled = self.scaler.fit_transform(X_train)
            X_test_scaled = self.scaler.transform(X_test)
            
            # 创建和训练模型
            self.model = self._create_model()
            self.model.fit(X_train_scaled, y_train)
            
            # 评估模型
            train_score = self.model.score(X_train_scaled, y_train)
            test_score = self.model.score(X_test_scaled, y_test)
            
            # 计算特征重要性
            if hasattr(self.model, 'feature_importances_'):
                self.feature_importance = dict(zip(
                    self.feature_columns, 
                    self.model.feature_importances_
                ))
            
            self.is_trained = True
            
            logger.info(f"✅ SLA预测模型训练完成")
            logger.info(f"   训练集R²: {train_score:.3f}")
            logger.info(f"   测试集R²: {test_score:.3f}")
            logger.info(f"   特征数量: {len(self.feature_columns)}")
            
        except Exception as e:
            logger.error(f"SLA预测模型训练失败: {str(e)}")
            raise
    
    def predict(self, forecast_horizon: int, **kwargs) -> List[SLAForecast]:
        """执行SLA预测"""
        if not self.is_trained and SKLEARN_AVAILABLE:
            raise ValueError("模型尚未训练，请先调用train()方法")
        
        logger.info(f"开始预测未来 {forecast_horizon} 天的SLA表现...")
        
        forecasts = []
        
        try:
            # 获取门店列表
            store_codes = kwargs.get('store_codes', ['417', '331', '213'])  # 默认门店
            
            for store_code in store_codes:
                for days_ahead in range(1, forecast_horizon + 1):
                    forecast_date = self.reference_date + timedelta(days=days_ahead)
                    
                    # 预测单店SLA
                    sla_forecast = self.predict_sla_performance(store_code, forecast_date)
                    forecasts.append(sla_forecast)
            
            logger.info(f"✅ SLA预测完成，生成 {len(forecasts)} 个预测结果")
            return forecasts
            
        except Exception as e:
            logger.error(f"SLA预测失败: {str(e)}")
            raise
    
    def predict_sla_performance(self, store_code: str, forecast_date: date) -> SLAForecast:
        """预测SLA表现"""
        try:
            # 创建预测特征
            features = self._create_prediction_features(store_code, forecast_date)
            
            if self.is_trained and SKLEARN_AVAILABLE:
                # 使用训练好的模型预测
                features_scaled = self.scaler.transform([features])
                predicted_sla = self.model.predict(features_scaled)[0]
                
                # 计算置信区间
                confidence_interval = self._calculate_confidence_interval(predicted_sla, features_scaled)
                
            else:
                # 使用增强的预测方法
                predicted_sla, confidence_interval = self._enhanced_sla_prediction(store_code, forecast_date)
            
            # 识别风险因子
            risk_factors = self.identify_risk_factors(store_code, forecast_date)
            
            # 生成改进建议
            recommendations = self._generate_recommendations(predicted_sla, risk_factors)
            
            return SLAForecast(
                store_code=store_code,
                forecast_date=forecast_date,
                predicted_sla_rate=max(0.0, min(1.0, predicted_sla)),
                confidence_interval=confidence_interval,
                risk_factors=risk_factors,
                improvement_recommendations=recommendations
            )
            
        except Exception as e:
            logger.error(f"SLA预测失败 {store_code}-{forecast_date}: {str(e)}")
            # 返回默认预测
            return self._create_default_forecast(store_code, forecast_date)
    
    def identify_risk_factors(self, store_code: str, forecast_date: date) -> Dict[str, float]:
        """识别风险因子"""
        risk_factors = {}
        
        try:
            # 1. 需求风险评估
            demand_risk = self._assess_demand_risk(store_code, forecast_date)
            if demand_risk > 0.1:
                risk_factors['high_demand_risk'] = demand_risk
            
            # 2. 天气风险评估
            weather_risk = self._assess_weather_risk(forecast_date)
            if weather_risk > 0.05:
                risk_factors['weather_risk'] = weather_risk
            
            # 3. 交通风险评估
            traffic_risk = self._assess_traffic_risk(store_code, forecast_date)
            if traffic_risk > 0.05:
                risk_factors['traffic_risk'] = traffic_risk
            
            # 4. 容量约束风险
            capacity_risk = self._assess_capacity_risk(store_code, forecast_date)
            if capacity_risk > 0.1:
                risk_factors['capacity_constraint_risk'] = capacity_risk
            
            # 5. 时间相关风险
            temporal_risk = self._assess_temporal_risk(forecast_date)
            if temporal_risk > 0.05:
                risk_factors['temporal_risk'] = temporal_risk
            
            # 6. 历史表现风险
            historical_risk = self._assess_historical_performance_risk(store_code)
            if historical_risk > 0.1:
                risk_factors['historical_performance_risk'] = historical_risk
            
            # 7. 供应链风险
            supply_chain_risk = self._assess_supply_chain_risk(store_code, forecast_date)
            if supply_chain_risk > 0.05:
                risk_factors['supply_chain_risk'] = supply_chain_risk
            
        except Exception as e:
            logger.warning(f"风险因子识别失败: {str(e)}")
            risk_factors['assessment_error_risk'] = 0.15
        
        return risk_factors
    
    def evaluate(self, test_data: pd.DataFrame) -> Dict[str, float]:
        """评估模型性能"""
        if not self.is_trained:
            return {'error': 'Model not trained'}
        
        try:
            # 预处理测试数据
            processed_data = self._preprocess_training_data(test_data)
            features_df = self._engineer_features(processed_data)
            X_test, y_test = self._prepare_training_data(features_df)
            
            if len(X_test) == 0:
                return {'error': 'No valid test samples'}
            
            # 预测
            X_test_scaled = self.scaler.transform(X_test)
            y_pred = self.model.predict(X_test_scaled)
            
            # 计算评估指标
            mae = mean_absolute_error(y_test, y_pred)
            mse = mean_squared_error(y_test, y_pred)
            rmse = np.sqrt(mse)
            r2 = r2_score(y_test, y_pred)
            
            # 计算MAPE
            mape = np.mean(np.abs((y_test - y_pred) / y_test)) * 100
            
            return {
                'mae': mae,
                'mse': mse,
                'rmse': rmse,
                'r2': r2,
                'mape': mape,
                'feature_importance': self.feature_importance
            }
            
        except Exception as e:
            logger.error(f"模型评估失败: {str(e)}")
            return {'error': str(e)}

    def get_model_info(self) -> Dict[str, Any]:
        """获取模型元信息"""
        return {
            'backend': 'sklearn' if SKLEARN_AVAILABLE else 'fallback',
            'is_trained': self.is_trained,
            'feature_columns': list(self.feature_columns),
            'reference_date': self.reference_date.isoformat() if isinstance(self.reference_date, date) else None,
            'feature_importance': self.feature_importance,
        }

    def predict_pickup_time(self, order_info: Dict[str, Any], route_plan: Any, store_processing_time_model: Any = None) -> Dict[str, Any]:
        """根据订单和路径信息估算取货时间。"""
        order_time = order_info.get('order_time', datetime.now())
        if isinstance(order_time, str):
            order_time = datetime.fromisoformat(order_time)

        route_minutes = float(order_info.get('route_minutes', 30))
        processing_minutes = float(order_info.get('processing_minutes', 45))
        if store_processing_time_model is not None and hasattr(store_processing_time_model, 'predict'):
            try:
                processing_minutes = float(store_processing_time_model.predict([order_info])[0])
            except Exception:
                pass

        predicted_time = order_time + timedelta(minutes=route_minutes + processing_minutes)
        return {
            'predicted_pickup_time': predicted_time,
            'processing_minutes': processing_minutes,
            'route_minutes': route_minutes,
        }

    def calculate_sla_probability(self, promised_time: datetime, predicted_time: datetime, uncertainty: float = 0.1) -> float:
        """根据承诺时间、预测时间和不确定性估算SLA达成概率。"""
        delta_hours = (promised_time - predicted_time).total_seconds() / 3600.0
        scaled = delta_hours / max(0.25, uncertainty * 24)
        probability = 1.0 / (1.0 + np.exp(-scaled))
        return float(max(0.0, min(1.0, probability)))
    
    def save_model(self, filepath: str) -> None:
        """保存模型"""
        import pickle

        model = self.model
        model_serialized = True
        try:
            pickle.dumps(model)
        except Exception:
            model = None
            model_serialized = False

        model_data = {
            'model': model,
            'scaler': self.scaler,
            'label_encoders': self.label_encoders,
            'feature_columns': self.feature_columns,
            'config': self.config,
            'is_trained': self.is_trained,
            'feature_importance': self.feature_importance,
            'model_serialized': model_serialized,
        }
        
        with open(filepath, 'wb') as f:
            pickle.dump(model_data, f)
        
        logger.info(f"✅ SLA预测模型已保存到 {filepath}")
    
    def load_model(self, filepath: str) -> None:
        """加载模型"""
        import pickle
        
        with open(filepath, 'rb') as f:
            model_data = pickle.load(f)
        
        self.model = model_data['model']
        self.scaler = model_data['scaler']
        self.label_encoders = model_data['label_encoders']
        self.feature_columns = model_data['feature_columns']
        self.config = model_data['config']
        self.is_trained = model_data['is_trained']
        self.feature_importance = model_data.get('feature_importance', {})
        
        logger.info(f"✅ SLA预测模型已从 {filepath} 加载")
    
    # ==================== 私有方法 ====================
    
    def _preprocess_training_data(self, data: pd.DataFrame) -> pd.DataFrame:
        """预处理训练数据"""
        processed = data.copy()
        
        # 确保必要的列存在
        required_columns = ['fulfillment_store_code', 'order_date']
        for col in required_columns:
            if col not in processed.columns:
                logger.warning(f"缺少必要列: {col}")
                return pd.DataFrame()
        
        # 计算SLA指标（简化）
        if 'sla_rate' not in processed.columns:
            # 模拟SLA计算
            processed['sla_rate'] = 0.95 + np.random.normal(0, 0.05, len(processed))
        processed['sla_rate'] = processed['sla_rate'].clip(0, 1)
        
        return processed
    
    def _engineer_features(self, data: pd.DataFrame) -> pd.DataFrame:
        """特征工程"""
        features_df = data.copy()
        
        # 时间特征
        features_df['order_date'] = pd.to_datetime(features_df['order_date'])
        features_df['weekday'] = features_df['order_date'].dt.dayofweek
        features_df['month'] = features_df['order_date'].dt.month
        features_df['day_of_month'] = features_df['order_date'].dt.day
        features_df['is_weekend'] = features_df['weekday'].isin([5, 6]).astype(int)
        
        # 订单特征
        if 'total_quantity' in features_df.columns:
            features_df['order_size'] = features_df['total_quantity']
        else:
            features_df['order_size'] = 5  # 默认值
        
        if 'unique_sku_count' in features_df.columns:
            features_df['sku_diversity'] = features_df['unique_sku_count']
        else:
            features_df['sku_diversity'] = 2  # 默认值
        
        # 门店特征（编码）
        if 'fulfillment_store_code' not in self.label_encoders:
            self.label_encoders['fulfillment_store_code'] = LabelEncoder()
            features_df['store_encoded'] = self.label_encoders['fulfillment_store_code'].fit_transform(
                features_df['fulfillment_store_code'].astype(str)
            )
        else:
            # 处理新的门店代码
            known_stores = set(self.label_encoders['fulfillment_store_code'].classes_)
            features_df['store_encoded'] = features_df['fulfillment_store_code'].apply(
                lambda x: self.label_encoders['fulfillment_store_code'].transform([str(x)])[0] 
                if str(x) in known_stores else -1
            )
        
        # 外部特征
        weather_features = ['weather_temperature_high', 'weather_humidity', 'weather_rainfall']
        for feature in weather_features:
            if feature not in features_df.columns:
                features_df[feature] = np.random.normal(25, 5) if 'temperature' in feature else np.random.normal(70, 10)
        
        # 假期特征
        if 'is_holiday' not in features_df.columns:
            features_df['is_holiday'] = 0
        
        return features_df
    
    def _prepare_training_data(self, features_df: pd.DataFrame) -> Tuple[np.ndarray, np.ndarray]:
        """准备训练数据"""
        # 选择特征列
        feature_candidates = [
            'weekday', 'month', 'day_of_month', 'is_weekend', 'is_holiday',
            'order_size', 'sku_diversity', 'store_encoded',
            'weather_temperature_high', 'weather_humidity', 'weather_rainfall'
        ]
        
        self.feature_columns = [col for col in feature_candidates if col in features_df.columns]
        
        # 准备特征矩阵
        X = features_df[self.feature_columns].fillna(0).values
        
        # 准备目标变量
        if 'sla_rate' in features_df.columns:
            y = features_df['sla_rate'].clip(0, 1).values
        else:
            # 如果没有真实SLA数据，生成模拟数据
            y = 0.95 + np.random.normal(0, 0.05, len(X))
            y = np.clip(y, 0, 1)
        
        return X, y
    
    def _create_model(self):
        """创建机器学习模型"""
        model_type = self.config['model_type']
        params = self.config['model_params'][model_type]
        
        if model_type == 'random_forest':
            return RandomForestRegressor(**params)
        elif model_type == 'gradient_boosting':
            return GradientBoostingRegressor(**params)
        else:
            logger.warning(f"未知模型类型 {model_type}，使用随机森林")
            return RandomForestRegressor(**self.config['model_params']['random_forest'])
    
    def _create_prediction_features(self, store_code: str, forecast_date: date) -> List[float]:
        """创建预测特征"""
        features = []
        
        # 时间特征
        features.append(forecast_date.weekday())  # weekday
        features.append(forecast_date.month)      # month
        features.append(forecast_date.day)        # day_of_month
        features.append(1 if forecast_date.weekday() in [5, 6] else 0)  # is_weekend
        features.append(1 if self._is_holiday(forecast_date) else 0)    # is_holiday
        
        # 订单特征（预测值）
        features.append(5.0)   # order_size (预测平均值)
        features.append(2.5)   # sku_diversity (预测平均值)
        
        # 门店特征
        if 'fulfillment_store_code' in self.label_encoders:
            try:
                store_encoded = self.label_encoders['fulfillment_store_code'].transform([store_code])[0]
            except:
                store_encoded = -1  # 未知门店
        else:
            store_encoded = 0
        features.append(store_encoded)
        
        # 天气特征（预测值或历史平均值）
        features.append(25.0)  # weather_temperature_high
        features.append(70.0)  # weather_humidity
        features.append(2.0)   # weather_rainfall
        
        return features
    
    def _enhanced_sla_prediction(self, store_code: str, forecast_date: date) -> Tuple[float, Tuple[float, float]]:
        """增强的SLA预测方法"""
        # 基础SLA率（基于历史表现）
        base_sla = self._get_historical_baseline_sla(store_code)
        
        # 时间因子调整
        time_adjustment = self._calculate_time_adjustment(forecast_date)
        
        # 需求因子调整
        demand_adjustment = self._calculate_demand_adjustment(store_code, forecast_date)
        
        # 外部因子调整
        external_adjustment = self._calculate_external_factors_adjustment(forecast_date)
        
        # 综合预测
        predicted_sla = base_sla + time_adjustment + demand_adjustment + external_adjustment
        predicted_sla = max(0.7, min(0.99, predicted_sla))
        
        # 计算不确定性
        uncertainty = self._calculate_prediction_uncertainty(store_code, forecast_date)
        
        # 置信区间
        confidence_interval = (
            max(0.0, predicted_sla - uncertainty),
            min(1.0, predicted_sla + uncertainty)
        )
        
        return predicted_sla, confidence_interval
    
    def _get_historical_baseline_sla(self, store_code: str) -> float:
        """获取历史基准SLA率"""
        if store_code in self.store_baseline_map:
            baseline = float(self.store_baseline_map[store_code])
            return max(0.0, min(1.0, baseline))

        # 模拟基于门店的历史表现
        store_baselines = {
            '417': 0.94,
            '331': 0.92,
            '213': 0.96,
            '418': 0.93,
            '419': 0.91
        }
        return store_baselines.get(store_code, 0.93)
    
    def _calculate_time_adjustment(self, forecast_date: date) -> float:
        """计算时间相关调整"""
        adjustment = 0.0
        
        # 周末效应
        if forecast_date.weekday() in [5, 6]:
            adjustment -= 0.02
        
        # 月末效应
        if forecast_date.day >= 28:
            adjustment -= 0.01
        
        # 假期效应
        if self._is_holiday(forecast_date):
            adjustment -= 0.03
        
        return adjustment
    
    def _calculate_demand_adjustment(self, store_code: str, forecast_date: date) -> float:
        """计算需求相关调整"""
        # 预测需求水平
        expected_demand = self._estimate_demand_level(store_code, forecast_date)
        
        # 需求过高时SLA下降
        if expected_demand > 1.2:  # 比平均高20%
            return -0.03 * (expected_demand - 1.0)
        elif expected_demand < 0.8:  # 比平均低20%
            return 0.01 * (1.0 - expected_demand)
        
        return 0.0
    
    def _calculate_external_factors_adjustment(self, forecast_date: date) -> float:
        """计算外部因子调整"""
        adjustment = 0.0
        
        # 天气影响（模拟）
        weather_severity = np.random.uniform(0, 1)
        if weather_severity > 0.7:  # 恶劣天气
            adjustment -= 0.02 * weather_severity
        
        # 交通影响
        traffic_congestion = np.random.uniform(0.5, 1.5)
        if traffic_congestion > 1.2:
            adjustment -= 0.015 * (traffic_congestion - 1.0)
        
        return adjustment
    
    def _calculate_prediction_uncertainty(self, store_code: str, forecast_date: date) -> float:
        """计算预测不确定性"""
        base_uncertainty = 0.03
        
        # 门店历史波动性
        volatility = self._calculate_demand_volatility(store_code)
        uncertainty_adjustment = volatility * 0.02
        
        # 预测时间距离
        days_ahead = (forecast_date - date.today()).days
        time_uncertainty = min(0.02, days_ahead * 0.002)
        
        return base_uncertainty + uncertainty_adjustment + time_uncertainty
    
    def _assess_demand_risk(self, store_code: str, forecast_date: date) -> float:
        """评估需求风险"""
        try:
            # 预测需求水平
            expected_demand = self._estimate_demand_level(store_code, forecast_date)
            
            # 需求波动性
            demand_volatility = self._calculate_demand_volatility(store_code)
            
            # 高需求风险
            if expected_demand > 1.3:  # 比平均高30%
                return min(0.4, 0.1 + (expected_demand - 1.0) * 0.2)
            
            # 需求不确定性风险
            if demand_volatility > 0.4:
                return min(0.3, demand_volatility * 0.5)
            
            return 0.0
        except Exception:
            return 0.1
    
    def _assess_weather_risk(self, forecast_date: date) -> float:
        """评估天气风险"""
        try:
            # 模拟天气风险评估
            # 实际应用中应该调用天气API
            
            # 季节性风险
            month = forecast_date.month
            seasonal_risk = 0.0
            
            # 台风季节 (6-11月)
            if month in [6, 7, 8, 9, 10, 11]:
                seasonal_risk = 0.1
            
            # 雨季风险 (5-9月)
            if month in [5, 6, 7, 8, 9]:
                seasonal_risk += 0.05
            
            # 随机天气事件
            random_weather_risk = np.random.exponential(0.05)
            
            return min(0.3, seasonal_risk + random_weather_risk)
        except Exception:
            return 0.05
    
    def _assess_traffic_risk(self, store_code: str, forecast_date: date) -> float:
        """评估交通风险"""
        try:
            base_risk = 0.0
            
            # 工作日交通风险更高
            if forecast_date.weekday() < 5:
                base_risk = 0.08
            
            # 月末交通风险
            if forecast_date.day >= 28:
                base_risk += 0.03
            
            # 门店位置风险（模拟）
            location_risk_map = {
                '417': 0.12,  # 旺角区域，交通拥堵
                '331': 0.08,  # 中等拥堵区域
                '213': 0.05,  # 较少拥堵区域
                '418': 0.10,
                '419': 0.15   # 高拥堵区域
            }
            
            location_risk = location_risk_map.get(store_code, 0.08)
            
            return min(0.25, base_risk + location_risk)
        except Exception:
            return 0.08
    
    def _assess_capacity_risk(self, store_code: str, forecast_date: date) -> float:
        """评估容量约束风险"""
        try:
            # 预测容量利用率
            capacity_utilization = self._estimate_capacity_utilization(store_code, forecast_date)
            
            # 高利用率风险
            if capacity_utilization > 0.85:
                return min(0.4, (capacity_utilization - 0.85) * 2.0)
            elif capacity_utilization > 0.75:
                return (capacity_utilization - 0.75) * 0.5
            
            return 0.0
        except Exception:
            return 0.1
    
    def _assess_temporal_risk(self, forecast_date: date) -> float:
        """评估时间相关风险"""
        try:
            risk = 0.0
            
            # 周末风险
            if forecast_date.weekday() in [5, 6]:
                risk += 0.1
            
            # 月末风险
            if forecast_date.day >= 28:
                risk += 0.08
            
            # 假期风险
            if self._is_holiday(forecast_date):
                risk += 0.15
            
            # 特殊日期风险（如情人节、母亲节等）
            special_dates = self._get_special_shopping_dates()
            if forecast_date in special_dates:
                risk += 0.12
            
            return min(0.3, risk)
        except Exception:
            return 0.05
    
    def _assess_historical_performance_risk(self, store_code: str) -> float:
        """评估历史表现风险"""
        try:
            # 获取历史SLA表现
            historical_sla = self._get_historical_baseline_sla(store_code)
            
            # 历史表现差的门店风险更高
            if historical_sla < 0.90:
                return min(0.3, (0.95 - historical_sla) * 2.0)
            elif historical_sla < 0.93:
                return (0.95 - historical_sla) * 1.0
            
            return 0.0
        except Exception:
            return 0.1
    
    def _assess_supply_chain_risk(self, store_code: str, forecast_date: date) -> float:
        """评估供应链风险"""
        try:
            risk = 0.0
            
            # 库存风险（模拟）
            inventory_risk = np.random.uniform(0, 0.15)
            if inventory_risk > 0.1:
                risk += inventory_risk
            
            # 供应商风险
            supplier_risk = np.random.uniform(0, 0.1)
            risk += supplier_risk
            
            # 物流风险
            logistics_risk = np.random.uniform(0, 0.08)
            risk += logistics_risk
            
            return min(0.25, risk)
        except Exception:
            return 0.05
    
    def _get_special_shopping_dates(self) -> set:
        """获取特殊购物日期"""
        # 返回一些特殊购物日期
        special_dates = set()
        
        # 2026年的一些特殊日期
        try:
            special_dates.add(date(2026, 2, 14))  # 情人节
            special_dates.add(date(2026, 5, 10))  # 母亲节（假设）
            special_dates.add(date(2026, 6, 21))  # 父亲节（假设）
            special_dates.add(date(2026, 11, 11))  # 双十一
            special_dates.add(date(2026, 12, 12))  # 双十二
        except Exception:
            pass
        
        return special_dates
    
    def _calculate_confidence_interval(self, predicted_sla: float, features_scaled: np.ndarray = None) -> Tuple[float, float]:
        """计算置信区间"""
        if self.is_trained and SKLEARN_AVAILABLE and hasattr(self.model, 'estimators_'):
            # 使用随机森林的预测方差
            try:
                predictions = [tree.predict(features_scaled)[0] for tree in self.model.estimators_]
                std_error = np.std(predictions)
            except Exception:
                std_error = 0.03
        else:
            # 基于预测值的自适应标准误差
            std_error = max(0.02, min(0.05, predicted_sla * (1 - predicted_sla) * 0.3))
        
        # 95%置信区间
        margin = 1.96 * std_error
        
        lower = max(0.0, predicted_sla - margin)
        upper = min(1.0, predicted_sla + margin)
        
        return (lower, upper)
    
    def monitor_real_time_sla_performance(self, active_orders: List[Any]) -> Dict[str, float]:
        """监控实时SLA表现"""
        try:
            performance_metrics = {}
            
            if not active_orders:
                return {'no_active_orders': 1.0}
            
            # 按门店分组统计
            store_performance = {}
            
            for order in active_orders:
                store_code = getattr(order, 'fulfillment_store_code', 'unknown')
                
                if store_code not in store_performance:
                    store_performance[store_code] = {
                        'total_orders': 0,
                        'on_time_orders': 0,
                        'delayed_orders': 0,
                        'avg_processing_time': 0,
                        'sla_compliance_rate': 0
                    }
                
                # 计算处理时间和SLA状态
                processing_time, is_on_time = self._calculate_order_sla_status(order)
                
                store_performance[store_code]['total_orders'] += 1
                store_performance[store_code]['avg_processing_time'] += processing_time
                
                if is_on_time:
                    store_performance[store_code]['on_time_orders'] += 1
                else:
                    store_performance[store_code]['delayed_orders'] += 1
            
            # 计算各门店的SLA指标
            for store_code, metrics in store_performance.items():
                if metrics['total_orders'] > 0:
                    metrics['sla_compliance_rate'] = metrics['on_time_orders'] / metrics['total_orders']
                    metrics['avg_processing_time'] /= metrics['total_orders']
                    
                    performance_metrics[f'{store_code}_sla_rate'] = metrics['sla_compliance_rate']
                    performance_metrics[f'{store_code}_avg_time'] = metrics['avg_processing_time']
            
            # 计算整体指标
            total_orders = sum(m['total_orders'] for m in store_performance.values())
            total_on_time = sum(m['on_time_orders'] for m in store_performance.values())
            
            if total_orders > 0:
                performance_metrics['overall_sla_rate'] = total_on_time / total_orders
                performance_metrics['total_active_orders'] = total_orders
            
            return performance_metrics
            
        except Exception as e:
            logger.error(f"实时SLA监控失败: {str(e)}")
            return {'monitoring_error': 1.0}
    
    def _calculate_order_sla_status(self, order: Any) -> Tuple[float, bool]:
        """计算订单SLA状态"""
        try:
            # 获取订单时间信息
            order_time = getattr(order, 'order_create_time', datetime.now())
            current_time = datetime.now()
            
            # 计算处理时间（小时）
            processing_time = (current_time - order_time).total_seconds() / 3600
            
            # SLA目标时间（24小时）
            sla_target_hours = self.config.get('sla_time_window_hours', 24)
            
            # 判断是否按时
            is_on_time = processing_time <= sla_target_hours
            
            return processing_time, is_on_time
            
        except Exception as e:
            logger.warning(f"计算订单SLA状态失败: {str(e)}")
            return 12.0, True  # 默认值
    
    def generate_sla_alerts(self, sla_forecasts: List[SLAForecast], threshold: float = 0.90) -> List[Dict[str, Any]]:
        """生成SLA预警"""
        alerts = []
        
        try:
            for forecast in sla_forecasts:
                # 检查SLA预测是否低于阈值
                if forecast.predicted_sla_rate < threshold:
                    alert = {
                        'alert_type': 'sla_risk',
                        'store_code': forecast.store_code,
                        'forecast_date': forecast.forecast_date,
                        'predicted_sla': forecast.predicted_sla_rate,
                        'threshold': threshold,
                        'severity': self._calculate_alert_severity(forecast.predicted_sla_rate, threshold),
                        'risk_factors': forecast.risk_factors,
                        'recommendations': forecast.improvement_recommendations,
                        'alert_timestamp': datetime.now()
                    }
                    alerts.append(alert)
                
                # 检查高风险因子
                high_risk_factors = {k: v for k, v in forecast.risk_factors.items() if v > 0.2}
                if high_risk_factors:
                    alert = {
                        'alert_type': 'high_risk_factors',
                        'store_code': forecast.store_code,
                        'forecast_date': forecast.forecast_date,
                        'high_risk_factors': high_risk_factors,
                        'severity': 'medium',
                        'alert_timestamp': datetime.now()
                    }
                    alerts.append(alert)
            
            return alerts
            
        except Exception as e:
            logger.error(f"生成SLA预警失败: {str(e)}")
            return []
    
    def _calculate_alert_severity(self, predicted_sla: float, threshold: float) -> str:
        """计算预警严重程度"""
        gap = threshold - predicted_sla
        
        if gap > 0.1:  # 差距超过10%
            return 'critical'
        elif gap > 0.05:  # 差距超过5%
            return 'high'
        elif gap > 0.02:  # 差距超过2%
            return 'medium'
        else:
            return 'low'
    
    def _calculate_demand_volatility(self, store_code: str) -> float:
        """计算需求波动性"""
        # 简化的需求波动性计算
        return np.random.uniform(0.1, 0.5)
    
    def _estimate_capacity_utilization(self, store_code: str, forecast_date: date) -> float:
        """估算容量利用率"""
        # 简化的容量利用率估算
        base_utilization = 0.7
        
        # 周末和假期利用率更高
        if forecast_date.weekday() in [5, 6]:
            base_utilization += 0.1
        
        if self._is_holiday(forecast_date):
            base_utilization += 0.15
        
        return min(1.0, base_utilization + np.random.uniform(-0.1, 0.1))
    
    def _generate_recommendations(self, predicted_sla: float, risk_factors: Dict[str, float]) -> List[str]:
        """生成改进建议"""
        recommendations = []
        
        # 基于预测SLA水平的建议
        if predicted_sla < 0.85:
            recommendations.append("🚨 SLA表现预计严重不足，建议立即采取紧急措施：增加人员配置、优化流程")
        elif predicted_sla < 0.90:
            recommendations.append("⚠️ SLA表现预计较低，建议增加人员配置并优化关键流程")
        elif predicted_sla < 0.95:
            recommendations.append("📈 SLA表现有改进空间，建议优化部分流程环节")
        
        # 基于具体风险因子的建议
        for risk_factor, impact in risk_factors.items():
            if impact > 0.15:  # 高影响风险因子
                if 'demand' in risk_factor:
                    recommendations.append("📊 高需求风险：建议提前备货、增加拣货人员、优化库存布局")
                elif 'weather' in risk_factor:
                    recommendations.append("🌧️ 天气风险：建议准备应急配送方案、调整配送时间窗口")
                elif 'traffic' in risk_factor:
                    recommendations.append("🚗 交通风险：建议优化配送路径、错峰配送、使用实时交通数据")
                elif 'capacity' in risk_factor:
                    recommendations.append("🏪 容量约束：建议增加临时人员、延长营业时间、优化空间布局")
                elif 'temporal' in risk_factor:
                    recommendations.append("⏰ 时间风险：建议提前准备、增加节假日人员安排")
                elif 'historical' in risk_factor:
                    recommendations.append("📋 历史表现风险：建议分析根本原因、制定改进计划、加强培训")
                elif 'supply_chain' in risk_factor:
                    recommendations.append("🔗 供应链风险：建议加强供应商管理、增加安全库存、多元化供应渠道")
        
        # 基于风险因子数量的建议
        if len(risk_factors) > 3:
            recommendations.append("🎯 多重风险并存，建议制定综合应对策略，优先处理高影响风险")
        
        # 预防性建议
        if predicted_sla > 0.95:
            recommendations.append("✅ SLA表现预计良好，建议保持当前运营水平，持续监控关键指标")
        
        # 如果没有特定建议，提供通用建议
        if not recommendations:
            recommendations.append("📊 建议持续监控SLA表现，收集更多数据以提高预测准确性")
        
        return recommendations
    
    def _is_holiday(self, check_date: date) -> bool:
        """检查是否为假期"""
        try:
            # 香港主要公共假期
            holidays_2026 = {
                date(2026, 1, 1),   # 新年
                date(2026, 2, 17),  # 农历新年（假设）
                date(2026, 2, 18),  # 农历新年
                date(2026, 2, 19),  # 农历新年
                date(2026, 4, 3),   # 清明节（假设）
                date(2026, 4, 6),   # 复活节（假设）
                date(2026, 5, 1),   # 劳动节
                date(2026, 5, 14),  # 佛诞（假设）
                date(2026, 6, 22),  # 端午节（假设）
                date(2026, 7, 1),   # 香港特别行政区成立纪念日
                date(2026, 9, 28),  # 中秋节翌日（假设）
                date(2026, 10, 1),  # 国庆节
                date(2026, 10, 21), # 重阳节（假设）
                date(2026, 12, 25), # 圣诞节
                date(2026, 12, 26), # 节礼日
            }
            
            return check_date in holidays_2026
        except Exception:
            return False
    
    def _estimate_demand_level(self, store_code: str, forecast_date: date) -> float:
        """估算需求水平"""
        try:
            # 基础需求水平
            base_demand = 1.0
            
            # 门店特性调整
            store_demand_factors = {
                '417': 1.2,  # 高需求门店
                '331': 0.9,  # 中等需求门店
                '213': 1.1,  # 较高需求门店
                '418': 0.8,  # 较低需求门店
                '419': 1.3   # 最高需求门店
            }
            
            store_factor = store_demand_factors.get(store_code, 1.0)
            
            # 时间因子
            time_factor = 1.0
            if forecast_date.weekday() in [5, 6]:  # 周末
                time_factor = 1.15
            
            if self._is_holiday(forecast_date):  # 假期
                time_factor = 1.25
            
            # 季节性因子
            month = forecast_date.month
            seasonal_factors = {
                1: 1.1, 2: 1.2, 3: 1.0, 4: 0.9, 5: 0.95, 6: 1.05,
                7: 1.1, 8: 1.05, 9: 0.9, 10: 1.0, 11: 1.15, 12: 1.3
            }
            seasonal_factor = seasonal_factors.get(month, 1.0)
            
            # 随机波动
            random_factor = np.random.uniform(0.9, 1.1)
            
            return base_demand * store_factor * time_factor * seasonal_factor * random_factor
            
        except Exception:
            return 1.0
    
    def _create_default_forecast(self, store_code: str, forecast_date: date) -> SLAForecast:
        """创建默认预测"""
        return SLAForecast(
            store_code=store_code,
            forecast_date=forecast_date,
            predicted_sla_rate=0.95,
            confidence_interval=(0.90, 0.98),
            risk_factors={'default_risk': 0.05},
            improvement_recommendations=["使用默认预测，建议收集更多历史数据以提高预测准确性"]
        )

# ==================== 工厂函数 ====================

def create_sla_predictor(config: Dict[str, Any] = None) -> MLSLAPredictor:
    """创建SLA预测器实例"""
    return MLSLAPredictor(config)

# ==================== 测试和演示 ====================

if __name__ == "__main__":
    print("⏱️ 测试SLA预测模块...")
    
    # 创建SLA预测器
    predictor = MLSLAPredictor()
    print("✅ SLA预测器创建成功")
    
    # 创建示例训练数据
    dates = pd.date_range(start='2025-01-01', end='2025-12-31', freq='D')
    sample_data = pd.DataFrame({
        'order_date': dates,
        'fulfillment_store_code': np.random.choice(['417', '331', '213'], len(dates)),
        'total_quantity': np.random.poisson(5, len(dates)),
        'unique_sku_count': np.random.poisson(2, len(dates)),
        'sla_rate': 0.95 + np.random.normal(0, 0.05, len(dates))
    })
    sample_data['sla_rate'] = sample_data['sla_rate'].clip(0.8, 0.99)
    
    print(f"📊 创建示例数据: {len(sample_data)} 条记录")
    
    try:
        # 训练模型
        print("🚀 开始训练模型...")
        predictor.train(sample_data)
        
        # 执行预测
        print("🔮 执行SLA预测...")
        forecasts = predictor.predict(forecast_horizon=7, store_codes=['417', '331'])
        
        print(f"✅ 预测完成，生成 {len(forecasts)} 个预测结果")
        
        # 显示预测结果
        print("\n📋 预测结果:")
        for forecast in forecasts[:5]:  # 显示前5个结果
            print(f"   📅 {forecast.forecast_date} - 门店 {forecast.store_code}:")
            print(f"      预测SLA: {forecast.predicted_sla_rate:.3f}")
            print(f"      置信区间: ({forecast.confidence_interval[0]:.3f}, {forecast.confidence_interval[1]:.3f})")
            print(f"      风险因子: {len(forecast.risk_factors)} 个")
            print(f"      建议: {len(forecast.improvement_recommendations)} 条")
        
        # 模型评估
        if SKLEARN_AVAILABLE:
            print("\n📊 模型评估...")
            metrics = predictor.evaluate(sample_data.tail(100))  # 使用最后100条数据评估
            if 'error' not in metrics:
                print(f"   R²分数: {metrics['r2']:.3f}")
                print(f"   平均绝对误差: {metrics['mae']:.3f}")
                print(f"   MAPE: {metrics['mape']:.1f}%")
        
        print("\n🎉 SLA预测模块测试完成！")
        
    except Exception as e:
        print(f"❌ 测试失败: {str(e)}")
        import traceback
        traceback.print_exc()
