#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unit tests for Prophet Forecaster
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

from modules.forecasting.prophet_forecaster import ProphetForecaster
from core.data_schema import DemandForecast

class TestProphetForecaster:
    
    @pytest.fixture
    def sample_training_data(self):
        """Create sample training data"""
        dates = pd.date_range(start='2025-01-01', end='2025-12-31', freq='D')
        return pd.DataFrame({
            'order_date': dates,
            'fulfillment_store_code': np.random.choice(['417', '331', '213'], len(dates)),
            'total_quantity': np.random.poisson(50, len(dates)),
            'unique_sku_count': np.random.poisson(20, len(dates)),
            'weather_temperature_high': 25 + 5 * np.sin(2 * np.pi * np.arange(len(dates)) / 365) + np.random.normal(0, 2, len(dates)),
            'weather_humidity': 70 + 10 * np.sin(2 * np.pi * np.arange(len(dates)) / 365) + np.random.normal(0, 5, len(dates)),
            'is_weekend': dates.dayofweek.isin([5, 6]).astype(int),
            'is_holiday': np.random.choice([0, 1], len(dates), p=[0.95, 0.05])
        })
    
    @pytest.fixture
    def forecaster(self):
        """Create forecaster instance"""
        return ProphetForecaster()
    
    def test_forecaster_initialization(self, forecaster):
        """Test forecaster initialization"""
        assert forecaster is not None
        assert not forecaster.is_trained
        assert forecaster.models == {}
        assert isinstance(forecaster.config, dict)
    
    def test_config_validation(self, forecaster):
        """Test configuration validation"""
        config = forecaster.config
        
        # Check required config keys
        required_keys = [
            'seasonality_mode', 'yearly_seasonality', 'weekly_seasonality',
            'holidays_prior_scale', 'seasonality_prior_scale', 'changepoint_prior_scale',
            'interval_width', 'uncertainty_samples'
        ]
        
        for key in required_keys:
            assert key in config
        
        # Check value ranges
        assert 0 < config['interval_width'] <= 1
        assert config['uncertainty_samples'] >= 0
    
    def test_data_preprocessing(self, forecaster, sample_training_data):
        """Test data preprocessing"""
        processed_data = forecaster._preprocess_training_data(sample_training_data)
        
        # Check required columns exist
        assert 'ds' in processed_data.columns
        assert 'y' in processed_data.columns
        assert 'store_code' in processed_data.columns
        
        # Check data types
        assert pd.api.types.is_datetime64_any_dtype(processed_data['ds'])
        assert pd.api.types.is_numeric_dtype(processed_data['y'])
        
        # Check non-negative demand
        assert (processed_data['y'] >= 0).all()
        
        # Check feature columns are identified
        assert len(forecaster.feature_columns) > 0
    
    def test_prophet_data_preparation(self, forecaster, sample_training_data):
        """Test Prophet data preparation"""
        processed_data = forecaster._preprocess_training_data(sample_training_data)
        store_data = processed_data[processed_data['store_code'] == '417'].copy()
        
        prophet_data = forecaster._prepare_prophet_data(store_data)
        
        # Check required Prophet columns
        assert 'ds' in prophet_data.columns
        assert 'y' in prophet_data.columns
        
        # Check data is sorted by date
        assert prophet_data['ds'].is_monotonic_increasing
        
        # Check external regressors are included
        for col in forecaster.feature_columns:
            if col in store_data.columns:
                assert col in prophet_data.columns
    
    def test_holidays_dataframe_creation(self, forecaster):
        """Test holidays dataframe creation"""
        holidays_df = forecaster._create_holidays_dataframe()
        
        if not holidays_df.empty:
            # Check required columns
            required_cols = ['holiday', 'ds', 'lower_window', 'upper_window']
            for col in required_cols:
                assert col in holidays_df.columns
            
            # Check data types
            assert pd.api.types.is_datetime64_any_dtype(holidays_df['ds'])
            assert pd.api.types.is_string_dtype(holidays_df['holiday'])
    
    def test_future_features_addition(self, forecaster, sample_training_data):
        """Test future features addition"""
        # Train first to set feature columns
        forecaster._preprocess_training_data(sample_training_data)
        
        # Create future dataframe
        future_dates = pd.date_range(start=date.today(), periods=7, freq='D')
        future_df = pd.DataFrame({'ds': future_dates})
        
        # Add features
        enhanced_future = forecaster._add_future_features(future_df, '417')
        
        # Check time features are added
        assert 'is_weekend' in enhanced_future.columns
        assert 'is_month_end' in enhanced_future.columns
        assert 'is_month_start' in enhanced_future.columns
        
        # Check values are valid
        assert enhanced_future['is_weekend'].isin([0, 1]).all()
        assert enhanced_future['is_month_end'].isin([0, 1]).all()
        assert enhanced_future['is_month_start'].isin([0, 1]).all()
    
    def test_confidence_intervals_calculation(self, forecaster):
        """Test confidence intervals calculation"""
        prediction = 50.0
        confidence_levels = [0.1, 0.5, 0.9]
        
        intervals = forecaster.get_confidence_intervals(prediction, confidence_levels)
        
        # Check all levels are present
        assert 'P10' in intervals
        assert 'P50' in intervals
        assert 'P90' in intervals
        
        # Check ordering constraint: P10 <= P50 <= P90
        assert intervals['P10'] <= intervals['P50'] <= intervals['P90']
        
        # Check non-negative values
        for value in intervals.values():
            assert value >= 0
        
        # Check P50 equals prediction
        assert intervals['P50'] == prediction
    
    @patch('modules.forecasting.prophet_forecaster.PROPHET_AVAILABLE', True)
    def test_training_with_sufficient_data(self, forecaster, sample_training_data):
        """Test training with sufficient data"""
        # Mock Prophet to avoid actual training
        with patch('modules.forecasting.prophet_forecaster.Prophet') as mock_prophet:
            mock_model = Mock()
            mock_prophet.return_value = mock_model
            
            forecaster.train(sample_training_data)
            
            # Check training completed
            assert forecaster.is_trained
            assert len(forecaster.models) > 0
            
            # Check Prophet was called with correct parameters
            mock_prophet.assert_called()
    
    def test_training_with_insufficient_data(self, forecaster):
        """Test training with insufficient data"""
        # Create minimal dataset
        insufficient_data = pd.DataFrame({
            'order_date': pd.date_range(start='2025-01-01', periods=5, freq='D'),
            'fulfillment_store_code': ['417'] * 5,
            'total_quantity': [10, 15, 12, 18, 14],
            'unique_sku_count': [2, 3, 2, 4, 3]
        })
        
        # Should handle insufficient data gracefully
        forecaster.train(insufficient_data)
        
        # No models should be trained due to insufficient data
        assert len(forecaster.models) == 0
    
    def test_prediction_without_training(self, forecaster):
        """Test prediction without training raises error"""
        with pytest.raises(ValueError, match="模型尚未训练"):
            forecaster.predict(forecast_horizon=7)
    
    def test_single_store_prediction(self, forecaster, sample_training_data):
        """Test single store prediction"""
        # Mock training
        forecaster.is_trained = True
        mock_model = Mock()
        mock_model.make_future_dataframe.return_value = pd.DataFrame({
            'ds': [datetime.now()]
        })
        mock_model.predict.return_value = pd.DataFrame({
            'ds': [datetime.now()],
            'yhat': [50.0],
            'yhat_lower': [45.0],
            'yhat_upper': [55.0]
        })
        forecaster.models['417'] = mock_model
        
        # Test prediction
        forecast = forecaster.predict_store_demand('417', 'SKU001', date.today())
        
        # Check result
        assert isinstance(forecast, DemandForecast)
        assert forecast.store_code == '417'
        assert forecast.sku_id == 'SKU001'
        assert forecast.predicted_demand >= 0
        assert 'P10' in forecast.confidence_intervals
        assert 'P50' in forecast.confidence_intervals
        assert 'P90' in forecast.confidence_intervals
    
    def test_batch_prediction(self, forecaster):
        """Test batch prediction"""
        # Mock training
        forecaster.is_trained = True
        mock_model = Mock()
        mock_model.make_future_dataframe.return_value = pd.DataFrame({
            'ds': [datetime.now()]
        })
        mock_model.predict.return_value = pd.DataFrame({
            'ds': [datetime.now()],
            'yhat': [50.0],
            'yhat_lower': [45.0],
            'yhat_upper': [55.0]
        })
        forecaster.models['417'] = mock_model
        
        # Test batch prediction
        forecasts = forecaster.predict_batch_demand(
            store_codes=['417'],
            sku_ids=['SKU001', 'SKU002'],
            forecast_dates=[date.today(), date.today() + timedelta(days=1)]
        )
        
        # Check results
        assert len(forecasts) == 4  # 1 store × 2 SKUs × 2 dates
        for forecast in forecasts:
            assert isinstance(forecast, DemandForecast)
    
    def test_external_factors_extraction(self, forecaster):
        """Test external factors extraction"""
        forecast_row = pd.Series({
            'is_holiday': 1,
            'is_weekend': 0,
            'weather_temperature_high': 30.0
        })
        
        factors = forecaster._extract_external_factors(forecast_row)
        
        # Check factors are extracted
        assert isinstance(factors, dict)
        assert 'holiday_impact' in factors
        assert 'weekend_impact' in factors
        assert 'weather_impact' in factors
        
        # Check values are reasonable
        assert factors['holiday_impact'] == 1.0
        assert factors['weekend_impact'] == 0.0
        assert isinstance(factors['weather_impact'], float)
    
    def test_model_persistence(self, forecaster, tmp_path):
        """Test model saving and loading"""
        # Setup mock model
        forecaster.is_trained = True
        forecaster.models = {'417': Mock()}
        forecaster.feature_columns = ['is_weekend', 'weather_temperature_high']
        
        # Test saving
        model_path = tmp_path / "test_model.pkl"
        forecaster.save_model(str(model_path))
        
        assert model_path.exists()
        
        # Test loading
        new_forecaster = ProphetForecaster()
        new_forecaster.load_model(str(model_path))
        
        assert new_forecaster.is_trained
        assert len(new_forecaster.models) == 1
        assert new_forecaster.feature_columns == ['is_weekend', 'weather_temperature_high']

if __name__ == "__main__":
    pytest.main([__file__])