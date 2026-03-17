#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Integration tests for Prophet Forecaster and SLA Predictor
"""

import pytest
import pandas as pd
import numpy as np
from datetime import date, datetime, timedelta
import sys
from pathlib import Path

# Add src to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

from modules.forecasting.prophet_forecaster import ProphetForecaster
from modules.forecasting.sla_predictor import MLSLAPredictor
from core.data_schema import DemandForecast, SLAForecast

class TestForecastingIntegration:
    
    @pytest.fixture
    def comprehensive_training_data(self):
        """Create comprehensive training data with all features"""
        dates = pd.date_range(start='2025-01-01', end='2025-12-31', freq='D')
        n_days = len(dates)
        
        # Create realistic seasonal patterns
        day_of_year = np.arange(n_days)
        seasonal_pattern = 50 + 20 * np.sin(2 * np.pi * day_of_year / 365.25)  # Yearly
        weekly_pattern = 5 * np.sin(2 * np.pi * day_of_year / 7)  # Weekly
        
        return pd.DataFrame({
            'order_date': dates,
            'fulfillment_store_code': np.random.choice(['417', '331', '213'], n_days),
            'total_quantity': (seasonal_pattern + weekly_pattern + np.random.normal(0, 5, n_days)).astype(int).clip(1),
            'unique_sku_count': np.random.poisson(20, n_days),
            
            # Weather features
            'weather_temperature_high': 25 + 8 * np.sin(2 * np.pi * day_of_year / 365.25) + np.random.normal(0, 3, n_days),
            'weather_temperature_low': 18 + 6 * np.sin(2 * np.pi * day_of_year / 365.25) + np.random.normal(0, 2, n_days),
            'weather_humidity': 70 + 15 * np.sin(2 * np.pi * day_of_year / 365.25 + np.pi) + np.random.normal(0, 8, n_days),
            'weather_rainfall': np.random.exponential(2, n_days),
            'weather_wind_speed': 10 + 5 * np.sin(2 * np.pi * day_of_year / 365.25) + np.random.normal(0, 3, n_days),
            
            # Time features
            'is_weekend': dates.dayofweek.isin([5, 6]).astype(int),
            'is_holiday': np.random.choice([0, 1], n_days, p=[0.97, 0.03]),
            
            # Traffic features
            'traffic_congestion_level': 2 + dates.dayofweek.map(lambda x: 1 if x < 5 else -0.5) + np.random.normal(0, 0.5, n_days),
            'traffic_speed_avg': 50 + np.random.normal(0, 10, n_days),
            
            # SLA performance (for SLA predictor)
            'sla_rate': 0.94 + 0.03 * np.sin(2 * np.pi * day_of_year / 365.25) + np.random.normal(0, 0.02, n_days)
        })
    
    def test_prophet_forecaster_complete_workflow(self, comprehensive_training_data):
        """Test complete Prophet forecaster workflow"""
        forecaster = ProphetForecaster()
        
        # Test training
        forecaster.train(comprehensive_training_data)
        assert forecaster.is_trained
        assert len(forecaster.models) > 0
        
        # Test feature extraction
        assert len(forecaster.feature_columns) > 0
        expected_features = ['weather_temperature_high', 'weather_humidity', 'is_weekend', 'is_holiday']
        for feature in expected_features:
            if feature in comprehensive_training_data.columns:
                assert feature in forecaster.feature_columns
        
        # Test prediction
        forecasts = forecaster.predict(forecast_horizon=7)
        assert len(forecasts) > 0
        
        # Validate forecast structure
        for forecast in forecasts:
            assert isinstance(forecast, DemandForecast)
            assert forecast.predicted_demand >= 0
            assert 'P10' in forecast.confidence_intervals
            assert 'P50' in forecast.confidence_intervals
            assert 'P90' in forecast.confidence_intervals
            
            # Check confidence interval ordering
            p10 = forecast.confidence_intervals['P10']
            p50 = forecast.confidence_intervals['P50']
            p90 = forecast.confidence_intervals['P90']
            assert p10 <= p50 <= p90
            
            # Check external factors
            assert isinstance(forecast.external_factors, dict)
        
        # Test single store prediction
        single_forecast = forecaster.predict_store_demand('417', 'SKU001', date.today() + timedelta(days=1))
        assert isinstance(single_forecast, DemandForecast)
        assert single_forecast.store_code == '417'
        assert single_forecast.sku_id == 'SKU001'
        
        # Test batch prediction
        batch_forecasts = forecaster.predict_batch_demand(
            store_codes=['417', '331'],
            sku_ids=['SKU001', 'SKU002'],
            forecast_dates=[date.today() + timedelta(days=i) for i in range(1, 4)]
        )
        assert len(batch_forecasts) == 2 * 2 * 3  # stores × SKUs × dates
    
    def test_sla_predictor_complete_workflow(self, comprehensive_training_data):
        """Test complete SLA predictor workflow"""
        predictor = MLSLAPredictor()
        
        # Test training
        predictor.train(comprehensive_training_data)
        assert predictor.is_trained
        
        # Test prediction
        forecasts = predictor.predict(forecast_horizon=7, store_codes=['417', '331'])
        assert len(forecasts) > 0
        
        # Validate forecast structure
        for forecast in forecasts:
            assert isinstance(forecast, SLAForecast)
            assert 0 <= forecast.predicted_sla_rate <= 1
            
            # Check confidence interval
            lower, upper = forecast.confidence_interval
            assert 0 <= lower <= upper <= 1
            assert lower <= forecast.predicted_sla_rate <= upper
            
            # Check risk factors
            assert isinstance(forecast.risk_factors, dict)
            for factor, value in forecast.risk_factors.items():
                assert 0 <= value <= 1
            
            # Check recommendations
            assert isinstance(forecast.improvement_recommendations, list)
            assert len(forecast.improvement_recommendations) > 0
        
        # Test single store SLA prediction
        single_sla = predictor.predict_sla_performance('417', date.today() + timedelta(days=1))
        assert isinstance(single_sla, SLAForecast)
        assert single_sla.store_code == '417'
        
        # Test risk factor identification
        risk_factors = predictor.identify_risk_factors('417', date.today() + timedelta(days=1))
        assert isinstance(risk_factors, dict)
        for factor, value in risk_factors.items():
            assert 0 <= value <= 1
    
    def test_forecaster_and_predictor_integration(self, comprehensive_training_data):
        """Test integration between Prophet forecaster and SLA predictor"""
        # Initialize both components
        forecaster = ProphetForecaster()
        predictor = MLSLAPredictor()
        
        # Train both models
        forecaster.train(comprehensive_training_data)
        predictor.train(comprehensive_training_data)
        
        # Generate demand forecasts
        demand_forecasts = forecaster.predict(forecast_horizon=3)
        
        # Generate SLA forecasts for the same period
        sla_forecasts = predictor.predict(forecast_horizon=3, store_codes=['417', '331'])
        
        # Verify both types of forecasts are generated
        assert len(demand_forecasts) > 0
        assert len(sla_forecasts) > 0
        
        # Check that forecasts cover similar time periods
        demand_dates = {f.forecast_date for f in demand_forecasts}
        sla_dates = {f.forecast_date for f in sla_forecasts}
        
        # Should have some overlap in forecast dates
        assert len(demand_dates.intersection(sla_dates)) > 0
        
        # Test correlation between high demand and SLA risk
        store_417_demand = [f for f in demand_forecasts if f.store_code == '417']
        store_417_sla = [f for f in sla_forecasts if f.store_code == '417']
        
        if store_417_demand and store_417_sla:
            # High demand should correlate with lower SLA or higher risk
            high_demand_forecast = max(store_417_demand, key=lambda x: x.predicted_demand)
            corresponding_sla = next((s for s in store_417_sla if s.forecast_date == high_demand_forecast.forecast_date), None)
            
            if corresponding_sla:
                # Either SLA should be lower or risk factors should be higher
                has_high_risk = any(risk > 0.15 for risk in corresponding_sla.risk_factors.values())
                assert corresponding_sla.predicted_sla_rate < 0.98 or has_high_risk
    
    def test_real_time_monitoring_integration(self, comprehensive_training_data):
        """Test real-time monitoring capabilities"""
        predictor = MLSLAPredictor()
        predictor.train(comprehensive_training_data)
        
        # Create mock active orders
        from unittest.mock import Mock
        
        active_orders = []
        for i in range(10):
            order = Mock()
            order.fulfillment_store_code = np.random.choice(['417', '331', '213'])
            order.order_create_time = datetime.now() - timedelta(hours=np.random.randint(1, 48))
            active_orders.append(order)
        
        # Test real-time monitoring
        metrics = predictor.monitor_real_time_sla_performance(active_orders)
        
        assert isinstance(metrics, dict)
        assert len(metrics) > 0
        
        # Should have overall metrics or store-specific metrics
        has_overall = 'overall_sla_rate' in metrics
        has_store_specific = any(key.endswith('_sla_rate') for key in metrics.keys())
        assert has_overall or has_store_specific
    
    def test_alert_generation_integration(self, comprehensive_training_data):
        """Test alert generation based on forecasts"""
        predictor = MLSLAPredictor()
        predictor.train(comprehensive_training_data)
        
        # Generate SLA forecasts
        sla_forecasts = predictor.predict(forecast_horizon=5, store_codes=['417', '331', '213'])
        
        # Generate alerts with different thresholds
        high_threshold_alerts = predictor.generate_sla_alerts(sla_forecasts, threshold=0.98)
        medium_threshold_alerts = predictor.generate_sla_alerts(sla_forecasts, threshold=0.90)
        
        # High threshold should generate more alerts than medium threshold
        assert len(high_threshold_alerts) >= len(medium_threshold_alerts)
        
        # Check alert structure
        for alert in high_threshold_alerts:
            assert 'alert_type' in alert
            assert 'store_code' in alert
            assert 'severity' in alert
            assert alert['severity'] in ['low', 'medium', 'high', 'critical']
    
    def test_model_performance_validation(self, comprehensive_training_data):
        """Test model performance validation"""
        # Split data for validation
        split_date = pd.to_datetime('2025-10-01')
        train_data = comprehensive_training_data[comprehensive_training_data['order_date'] < split_date]
        test_data = comprehensive_training_data[comprehensive_training_data['order_date'] >= split_date]
        
        # Train Prophet forecaster
        forecaster = ProphetForecaster()
        forecaster.train(train_data)
        
        # Evaluate forecaster (simplified - would need actual evaluation in real scenario)
        assert forecaster.is_trained
        assert len(forecaster.models) > 0
        
        # Train SLA predictor
        predictor = MLSLAPredictor()
        predictor.train(train_data)
        
        # Evaluate SLA predictor
        if len(test_data) > 0:
            evaluation_metrics = predictor.evaluate(test_data)
            
            if 'error' not in evaluation_metrics:
                # Check that evaluation metrics are reasonable
                assert 'mae' in evaluation_metrics
                assert 'r2' in evaluation_metrics
                assert evaluation_metrics['mae'] >= 0
                assert -1 <= evaluation_metrics['r2'] <= 1
    
    def test_external_factor_impact_analysis(self, comprehensive_training_data):
        """Test external factor impact analysis"""
        forecaster = ProphetForecaster()
        forecaster.train(comprehensive_training_data)
        
        # Generate forecasts
        forecasts = forecaster.predict(forecast_horizon=5)
        
        # Analyze external factor impacts
        weather_impacts = []
        holiday_impacts = []
        
        for forecast in forecasts:
            if 'weather_impact' in forecast.external_factors:
                weather_impacts.append(forecast.external_factors['weather_impact'])
            if 'holiday_impact' in forecast.external_factors:
                holiday_impacts.append(forecast.external_factors['holiday_impact'])
        
        # Check that external factors are within reasonable bounds
        if weather_impacts:
            assert all(-1 <= impact <= 1 for impact in weather_impacts)
        if holiday_impacts:
            assert all(-1 <= impact <= 1 for impact in holiday_impacts)
    
    def test_confidence_interval_coverage(self, comprehensive_training_data):
        """Test confidence interval coverage properties"""
        forecaster = ProphetForecaster()
        forecaster.train(comprehensive_training_data)
        
        # Generate multiple forecasts
        forecasts = forecaster.predict(forecast_horizon=10)
        
        # Check confidence interval properties
        for forecast in forecasts:
            intervals = forecast.confidence_intervals
            
            # P10 <= P50 <= P90 ordering
            assert intervals['P10'] <= intervals['P50'] <= intervals['P90']
            
            # Reasonable interval widths
            interval_width = intervals['P90'] - intervals['P10']
            assert 0 < interval_width <= forecast.predicted_demand * 2  # Not too wide
            
            # P50 should equal predicted demand
            assert abs(intervals['P50'] - forecast.predicted_demand) < 0.01

if __name__ == "__main__":
    pytest.main([__file__, "-v"])