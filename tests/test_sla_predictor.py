#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unit tests for SLA Predictor
"""

import pytest
import pandas as pd
import numpy as np
from datetime import date, datetime, timedelta
from unittest.mock import Mock, patch
import sys
from pathlib import Path

# Add src to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

from modules.forecasting.sla_predictor import MLSLAPredictor
from core.data_schema import SLAForecast

class TestMLSLAPredictor:
    
    @pytest.fixture
    def sample_training_data(self):
        """Create sample training data"""
        dates = pd.date_range(start='2025-01-01', end='2025-12-31', freq='D')
        return pd.DataFrame({
            'order_date': dates,
            'fulfillment_store_code': np.random.choice(['417', '331', '213'], len(dates)),
            'total_quantity': np.random.poisson(5, len(dates)),
            'unique_sku_count': np.random.poisson(2, len(dates)),
            'sla_rate': 0.95 + np.random.normal(0, 0.05, len(dates))
        })
    
    @pytest.fixture
    def predictor(self):
        """Create SLA predictor instance"""
        return MLSLAPredictor()
    
    def test_predictor_initialization(self, predictor):
        """Test predictor initialization"""
        assert predictor is not None
        assert not predictor.is_trained
        assert predictor.model is None
        assert isinstance(predictor.config, dict)
    
    def test_config_validation(self, predictor):
        """Test configuration validation"""
        config = predictor.config
        
        # Check required config keys
        required_keys = [
            'model_type', 'target_sla_rate', 'sla_time_window_hours',
            'cross_validation_folds', 'test_size', 'random_state'
        ]
        
        for key in required_keys:
            assert key in config
        
        # Check value ranges
        assert 0 < config['target_sla_rate'] <= 1
        assert config['sla_time_window_hours'] > 0
        assert 0 < config['test_size'] < 1
    
    def test_data_preprocessing(self, predictor, sample_training_data):
        """Test data preprocessing"""
        processed_data = predictor._preprocess_training_data(sample_training_data)
        
        # Check required columns exist
        assert 'fulfillment_store_code' in processed_data.columns
        assert 'order_date' in processed_data.columns
        
        # Check SLA rate is generated if not present
        if 'sla_rate' not in sample_training_data.columns:
            assert 'sla_rate' in processed_data.columns
        
        # Check SLA rate is within valid range
        assert (processed_data['sla_rate'] >= 0).all()
        assert (processed_data['sla_rate'] <= 1).all()
    
    def test_feature_engineering(self, predictor, sample_training_data):
        """Test feature engineering"""
        features_df = predictor._engineer_features(sample_training_data)
        
        # Check time features are created
        time_features = ['weekday', 'month', 'day_of_month', 'is_weekend']
        for feature in time_features:
            assert feature in features_df.columns
        
        # Check value ranges
        assert features_df['weekday'].between(0, 6).all()
        assert features_df['month'].between(1, 12).all()
        assert features_df['is_weekend'].isin([0, 1]).all()
        
        # Check store encoding
        assert 'store_encoded' in features_df.columns
    
    def test_training_data_preparation(self, predictor, sample_training_data):
        """Test training data preparation"""
        features_df = predictor._engineer_features(sample_training_data)
        X, y = predictor._prepare_training_data(features_df)
        
        # Check shapes match
        assert len(X) == len(y)
        assert len(X) > 0
        
        # Check feature columns are set
        assert len(predictor.feature_columns) > 0
        
        # Check X has correct number of features
        assert X.shape[1] == len(predictor.feature_columns)
        
        # Check y values are valid SLA rates
        assert (y >= 0).all()
        assert (y <= 1).all()
    
    def test_risk_factor_identification(self, predictor):
        """Test risk factor identification"""
        store_code = '417'
        forecast_date = date.today() + timedelta(days=1)
        
        risk_factors = predictor.identify_risk_factors(store_code, forecast_date)
        
        # Check return type
        assert isinstance(risk_factors, dict)
        
        # Check risk values are valid
        for factor, value in risk_factors.items():
            assert isinstance(value, (int, float))
            assert 0 <= value <= 1  # Risk factors should be probabilities
    
    def test_demand_risk_assessment(self, predictor):
        """Test demand risk assessment"""
        store_code = '417'
        forecast_date = date.today()
        
        risk = predictor._assess_demand_risk(store_code, forecast_date)
        
        # Check return type and range
        assert isinstance(risk, float)
        assert 0 <= risk <= 1
    
    def test_weather_risk_assessment(self, predictor):
        """Test weather risk assessment"""
        forecast_date = date.today()
        
        risk = predictor._assess_weather_risk(forecast_date)
        
        # Check return type and range
        assert isinstance(risk, float)
        assert 0 <= risk <= 1
    
    def test_traffic_risk_assessment(self, predictor):
        """Test traffic risk assessment"""
        store_code = '417'
        forecast_date = date.today()
        
        risk = predictor._assess_traffic_risk(store_code, forecast_date)
        
        # Check return type and range
        assert isinstance(risk, float)
        assert 0 <= risk <= 1
    
    def test_capacity_risk_assessment(self, predictor):
        """Test capacity risk assessment"""
        store_code = '417'
        forecast_date = date.today()
        
        risk = predictor._assess_capacity_risk(store_code, forecast_date)
        
        # Check return type and range
        assert isinstance(risk, float)
        assert 0 <= risk <= 1
    
    def test_temporal_risk_assessment(self, predictor):
        """Test temporal risk assessment"""
        # Test weekend
        weekend_date = date.today() + timedelta(days=(5 - date.today().weekday()) % 7)
        weekend_risk = predictor._assess_temporal_risk(weekend_date)
        
        # Test weekday
        weekday_date = date.today() + timedelta(days=(0 - date.today().weekday()) % 7)
        weekday_risk = predictor._assess_temporal_risk(weekday_date)
        
        # Weekend should have higher risk
        assert weekend_risk >= weekday_risk
        
        # Check ranges
        assert 0 <= weekend_risk <= 1
        assert 0 <= weekday_risk <= 1
    
    def test_sla_performance_prediction(self, predictor):
        """Test SLA performance prediction"""
        store_code = '417'
        forecast_date = date.today() + timedelta(days=1)
        
        forecast = predictor.predict_sla_performance(store_code, forecast_date)
        
        # Check return type
        assert isinstance(forecast, SLAForecast)
        
        # Check required fields
        assert forecast.store_code == store_code
        assert forecast.forecast_date == forecast_date
        assert 0 <= forecast.predicted_sla_rate <= 1
        
        # Check confidence interval
        lower, upper = forecast.confidence_interval
        assert 0 <= lower <= upper <= 1
        assert lower <= forecast.predicted_sla_rate <= upper
        
        # Check risk factors and recommendations
        assert isinstance(forecast.risk_factors, dict)
        assert isinstance(forecast.improvement_recommendations, list)
    
    def test_enhanced_sla_prediction(self, predictor):
        """Test enhanced SLA prediction method"""
        store_code = '417'
        forecast_date = date.today() + timedelta(days=1)
        
        predicted_sla, confidence_interval = predictor._enhanced_sla_prediction(store_code, forecast_date)
        
        # Check predicted SLA
        assert isinstance(predicted_sla, float)
        assert 0 <= predicted_sla <= 1
        
        # Check confidence interval
        lower, upper = confidence_interval
        assert 0 <= lower <= upper <= 1
        assert lower <= predicted_sla <= upper
    
    def test_historical_baseline_sla(self, predictor):
        """Test historical baseline SLA retrieval"""
        # Test known store
        baseline_417 = predictor._get_historical_baseline_sla('417')
        assert isinstance(baseline_417, float)
        assert 0 <= baseline_417 <= 1
        
        # Test unknown store (should return default)
        baseline_unknown = predictor._get_historical_baseline_sla('999')
        assert isinstance(baseline_unknown, float)
        assert 0 <= baseline_unknown <= 1
    
    def test_time_adjustment_calculation(self, predictor):
        """Test time adjustment calculation"""
        # Test weekend
        weekend_date = date.today() + timedelta(days=(5 - date.today().weekday()) % 7)
        weekend_adj = predictor._calculate_time_adjustment(weekend_date)
        
        # Test weekday
        weekday_date = date.today() + timedelta(days=(0 - date.today().weekday()) % 7)
        weekday_adj = predictor._calculate_time_adjustment(weekday_date)
        
        # Weekend should have negative adjustment (lower SLA)
        assert weekend_adj <= weekday_adj
        
        # Check reasonable ranges
        assert -0.1 <= weekend_adj <= 0.1
        assert -0.1 <= weekday_adj <= 0.1
    
    def test_demand_level_estimation(self, predictor):
        """Test demand level estimation"""
        store_code = '417'
        forecast_date = date.today()
        
        demand_level = predictor._estimate_demand_level(store_code, forecast_date)
        
        # Check return type and reasonable range
        assert isinstance(demand_level, float)
        assert 0.5 <= demand_level <= 2.0  # Reasonable multiplier range
    
    def test_confidence_interval_calculation(self, predictor):
        """Test confidence interval calculation"""
        predicted_sla = 0.95
        
        # Test without features (fallback method)
        lower, upper = predictor._calculate_confidence_interval(predicted_sla)
        
        assert 0 <= lower <= upper <= 1
        assert lower <= predicted_sla <= upper
        
        # Test with mock features
        mock_features = np.array([[0.5, 0.3, 0.8]])
        lower_feat, upper_feat = predictor._calculate_confidence_interval(predicted_sla, mock_features)
        
        assert 0 <= lower_feat <= upper_feat <= 1
    
    def test_real_time_monitoring(self, predictor):
        """Test real-time SLA monitoring"""
        # Create mock orders
        mock_orders = []
        for i in range(5):
            mock_order = Mock()
            mock_order.fulfillment_store_code = '417'
            mock_order.order_create_time = datetime.now() - timedelta(hours=i*2)
            mock_orders.append(mock_order)
        
        # Test monitoring
        metrics = predictor.monitor_real_time_sla_performance(mock_orders)
        
        # Check return type
        assert isinstance(metrics, dict)
        
        # Check for expected metrics
        if mock_orders:
            assert 'overall_sla_rate' in metrics or '417_sla_rate' in metrics
            assert 'total_active_orders' in metrics or 'no_active_orders' in metrics
    
    def test_sla_alerts_generation(self, predictor):
        """Test SLA alerts generation"""
        # Create mock forecasts
        forecasts = []
        
        # Low SLA forecast (should trigger alert)
        low_sla_forecast = SLAForecast(
            store_code='417',
            forecast_date=date.today(),
            predicted_sla_rate=0.85,  # Below threshold
            confidence_interval=(0.80, 0.90),
            risk_factors={'high_demand_risk': 0.25},
            improvement_recommendations=['Increase staffing']
        )
        forecasts.append(low_sla_forecast)
        
        # Good SLA forecast (should not trigger alert)
        good_sla_forecast = SLAForecast(
            store_code='331',
            forecast_date=date.today(),
            predicted_sla_rate=0.96,
            confidence_interval=(0.94, 0.98),
            risk_factors={'weather_risk': 0.05},
            improvement_recommendations=['Maintain current level']
        )
        forecasts.append(good_sla_forecast)
        
        # Generate alerts
        alerts = predictor.generate_sla_alerts(forecasts, threshold=0.90)
        
        # Check alerts are generated
        assert isinstance(alerts, list)
        assert len(alerts) >= 1  # At least one alert for low SLA
        
        # Check alert structure
        for alert in alerts:
            assert 'alert_type' in alert
            assert 'store_code' in alert
            assert 'severity' in alert
            assert 'alert_timestamp' in alert
    
    def test_alert_severity_calculation(self, predictor):
        """Test alert severity calculation"""
        threshold = 0.90
        
        # Test different severity levels
        critical_sla = 0.75  # 15% below threshold
        high_sla = 0.84      # 6% below threshold
        medium_sla = 0.87    # 3% below threshold
        low_sla = 0.89       # 1% below threshold
        
        assert predictor._calculate_alert_severity(critical_sla, threshold) == 'critical'
        assert predictor._calculate_alert_severity(high_sla, threshold) == 'high'
        assert predictor._calculate_alert_severity(medium_sla, threshold) == 'medium'
        assert predictor._calculate_alert_severity(low_sla, threshold) == 'low'
    
    def test_holiday_detection(self, predictor):
        """Test holiday detection"""
        # Test known holiday (New Year)
        new_year = date(2026, 1, 1)
        assert predictor._is_holiday(new_year) == True
        
        # Test regular day
        regular_day = date(2026, 3, 15)
        assert predictor._is_holiday(regular_day) == False
    
    def test_recommendation_generation(self, predictor):
        """Test recommendation generation"""
        # Test low SLA with high risk factors
        low_sla = 0.80
        high_risks = {
            'high_demand_risk': 0.25,
            'weather_risk': 0.20,
            'traffic_risk': 0.18
        }
        
        recommendations = predictor._generate_recommendations(low_sla, high_risks)
        
        # Check recommendations are generated
        assert isinstance(recommendations, list)
        assert len(recommendations) > 0
        
        # Check recommendations are strings
        for rec in recommendations:
            assert isinstance(rec, str)
            assert len(rec) > 0
        
        # Test good SLA with low risks
        good_sla = 0.97
        low_risks = {'weather_risk': 0.05}
        
        good_recommendations = predictor._generate_recommendations(good_sla, low_risks)
        assert isinstance(good_recommendations, list)
        assert len(good_recommendations) > 0
    
    def test_model_persistence(self, predictor, tmp_path):
        """Test model saving and loading"""
        # Setup mock model state
        predictor.is_trained = True
        predictor.model = Mock()
        predictor.feature_columns = ['weekday', 'is_weekend']
        
        # Test saving
        model_path = tmp_path / "test_sla_model.pkl"
        predictor.save_model(str(model_path))
        
        assert model_path.exists()
        
        # Test loading
        new_predictor = MLSLAPredictor()
        new_predictor.load_model(str(model_path))
        
        assert new_predictor.is_trained
        assert new_predictor.feature_columns == ['weekday', 'is_weekend']
    
    def test_prediction_without_training(self, predictor):
        """Test prediction methods work without trained model"""
        store_code = '417'
        forecast_date = date.today() + timedelta(days=1)
        
        # Should not raise error, should use fallback method
        forecast = predictor.predict_sla_performance(store_code, forecast_date)
        
        assert isinstance(forecast, SLAForecast)
        assert 0 <= forecast.predicted_sla_rate <= 1

if __name__ == "__main__":
    pytest.main([__file__])