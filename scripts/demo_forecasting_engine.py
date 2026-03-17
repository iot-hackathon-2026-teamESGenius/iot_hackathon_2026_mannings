#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Demo script for Prophet-based Forecasting Engine and SLA Predictor
Demonstrates Task 2.1 and Task 2.3 implementations
"""

import pandas as pd
import numpy as np
from datetime import date, datetime, timedelta
import sys
from pathlib import Path

# Add src to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root / "src"))

from modules.forecasting.prophet_forecaster import ProphetForecaster
from modules.forecasting.sla_predictor import MLSLAPredictor

def create_comprehensive_demo_data():
    """Create comprehensive demo data with all features"""
    print("📊 Creating comprehensive demo dataset...")
    
    # Generate 18 months of data
    dates = pd.date_range(start='2025-01-01', end='2026-06-30', freq='D')
    n_days = len(dates)
    
    # Create realistic seasonal and weekly patterns
    day_of_year = np.arange(n_days) % 365.25
    day_of_week = np.arange(n_days) % 7
    
    # Seasonal demand pattern (higher in winter/holidays)
    seasonal_base = 50 + 15 * np.sin(2 * np.pi * day_of_year / 365.25 + np.pi)
    
    # Weekly pattern (higher on weekends)
    weekly_pattern = 8 * np.sin(2 * np.pi * day_of_week / 7 + np.pi/2)
    
    # Holiday spikes
    holiday_boost = np.zeros(n_days)
    for i, d in enumerate(dates):
        if d.month == 12 and d.day >= 20:  # Christmas period
            holiday_boost[i] = 20
        elif d.month == 2 and 10 <= d.day <= 20:  # Chinese New Year period
            holiday_boost[i] = 25
        elif d.month == 10 and d.day == 1:  # National Day
            holiday_boost[i] = 15
    
    # Generate store-specific data
    stores = ['417', '331', '213', '418', '419']
    store_multipliers = {'417': 1.2, '331': 0.9, '213': 1.1, '418': 0.8, '419': 1.3}
    
    data_rows = []
    
    for i, date_val in enumerate(dates):
        for store in stores:
            # Base demand with patterns
            base_demand = (seasonal_base[i] + weekly_pattern[i] + holiday_boost[i]) * store_multipliers[store]
            
            # Add noise
            demand = max(1, int(base_demand + np.random.normal(0, 8)))
            
            # Weather data (seasonal patterns)
            temp_high = 25 + 8 * np.sin(2 * np.pi * day_of_year[i] / 365.25) + np.random.normal(0, 3)
            temp_low = temp_high - 8 + np.random.normal(0, 2)
            humidity = 70 + 15 * np.sin(2 * np.pi * day_of_year[i] / 365.25 + np.pi) + np.random.normal(0, 8)
            
            # Rainfall (more in summer)
            is_rainy_season = 5 <= date_val.month <= 9
            rainfall = np.random.exponential(5 if is_rainy_season else 1)
            
            # Wind speed
            wind_speed = 10 + 5 * np.sin(2 * np.pi * day_of_year[i] / 365.25) + np.random.normal(0, 3)
            
            # Traffic patterns
            is_weekday = date_val.weekday() < 5
            congestion = 3 if is_weekday else 2
            congestion += np.random.normal(0, 0.5)
            speed = max(20, 60 - (congestion - 1) * 8 + np.random.normal(0, 5))
            
            # SLA performance (inversely related to demand and external factors)
            base_sla = 0.95
            demand_impact = -min(0.1, (demand - 40) * 0.001)  # Higher demand reduces SLA
            weather_impact = -max(0, (temp_high - 32) * 0.002)  # Extreme heat reduces SLA
            rain_impact = -min(0.05, rainfall * 0.005)  # Rain reduces SLA
            traffic_impact = -max(0, (congestion - 3) * 0.02)  # Traffic reduces SLA
            
            sla_rate = base_sla + demand_impact + weather_impact + rain_impact + traffic_impact
            sla_rate = max(0.8, min(0.99, sla_rate + np.random.normal(0, 0.02)))
            
            data_rows.append({
                'order_date': date_val,
                'fulfillment_store_code': store,
                'total_quantity': demand,
                'unique_sku_count': max(1, int(demand * 0.4 + np.random.normal(0, 3))),
                
                # Weather features
                'weather_temperature_high': temp_high,
                'weather_temperature_low': temp_low,
                'weather_humidity': max(30, min(95, humidity)),
                'weather_rainfall': rainfall,
                'weather_wind_speed': max(0, wind_speed),
                
                # Time features
                'is_weekend': int(date_val.weekday() >= 5),
                'is_holiday': int(holiday_boost[i] > 0),
                
                # Traffic features
                'traffic_congestion_level': max(1, min(5, congestion)),
                'traffic_speed_avg': speed,
                
                # SLA data
                'sla_rate': sla_rate
            })
    
    df = pd.DataFrame(data_rows)
    print(f"✅ Created dataset with {len(df)} records covering {len(dates)} days and {len(stores)} stores")
    return df

def demo_prophet_forecaster(data):
    """Demonstrate Prophet forecaster capabilities"""
    print("\n🔮 PROPHET FORECASTER DEMONSTRATION")
    print("=" * 50)
    
    # Initialize forecaster
    forecaster = ProphetForecaster()
    print("✅ Prophet forecaster initialized")
    
    # Train the model
    print("\n🚀 Training Prophet models...")
    forecaster.train(data)
    
    print(f"✅ Training completed!")
    print(f"   📊 Trained models for {len(forecaster.models)} stores")
    print(f"   🔧 Using {len(forecaster.feature_columns)} external features:")
    for i, feature in enumerate(forecaster.feature_columns, 1):
        print(f"      {i}. {feature}")
    
    # Generate forecasts
    print("\n📈 Generating 7-day demand forecasts...")
    forecasts = forecaster.predict(forecast_horizon=7)
    
    print(f"✅ Generated {len(forecasts)} forecasts")
    
    # Display sample forecasts
    print("\n📋 Sample Demand Forecasts:")
    print("-" * 80)
    print(f"{'Date':<12} {'Store':<6} {'Predicted':<10} {'P10':<8} {'P50':<8} {'P90':<8} {'Ext.Factors'}")
    print("-" * 80)
    
    for forecast in forecasts[:10]:  # Show first 10
        ext_factors = len(forecast.external_factors)
        print(f"{forecast.forecast_date} {forecast.store_code:<6} "
              f"{forecast.predicted_demand:>8.1f} "
              f"{forecast.confidence_intervals['P10']:>6.1f} "
              f"{forecast.confidence_intervals['P50']:>6.1f} "
              f"{forecast.confidence_intervals['P90']:>6.1f} "
              f"{ext_factors:>8} factors")
    
    # Test single store prediction
    print(f"\n🎯 Single Store Prediction Example:")
    single_forecast = forecaster.predict_store_demand('417', 'SKU001', date.today() + timedelta(days=1))
    print(f"   Store: {single_forecast.store_code}")
    print(f"   SKU: {single_forecast.sku_id}")
    print(f"   Date: {single_forecast.forecast_date}")
    print(f"   Predicted Demand: {single_forecast.predicted_demand:.1f}")
    print(f"   Confidence Intervals: P10={single_forecast.confidence_intervals['P10']:.1f}, "
          f"P50={single_forecast.confidence_intervals['P50']:.1f}, "
          f"P90={single_forecast.confidence_intervals['P90']:.1f}")
    print(f"   External Factors: {single_forecast.external_factors}")
    
    # Test batch prediction
    print(f"\n📦 Batch Prediction Example:")
    batch_forecasts = forecaster.predict_batch_demand(
        store_codes=['417', '331'],
        sku_ids=['SKU001', 'SKU002'],
        forecast_dates=[date.today() + timedelta(days=i) for i in range(1, 4)]
    )
    print(f"   Generated {len(batch_forecasts)} batch forecasts")
    print(f"   Stores: 2, SKUs: 2, Dates: 3 → Total: {len(batch_forecasts)} forecasts")
    
    return forecaster, forecasts

def demo_sla_predictor(data):
    """Demonstrate SLA predictor capabilities"""
    print("\n⏱️ SLA PREDICTOR DEMONSTRATION")
    print("=" * 50)
    
    # Initialize predictor
    predictor = MLSLAPredictor()
    print("✅ SLA predictor initialized")
    
    # Train the model
    print("\n🚀 Training SLA prediction model...")
    predictor.train(data)
    
    print(f"✅ Training completed!")
    print(f"   🎯 Model type: {predictor.config['model_type']}")
    print(f"   📊 Target SLA rate: {predictor.config['target_sla_rate']:.1%}")
    print(f"   ⏰ SLA time window: {predictor.config['sla_time_window_hours']} hours")
    
    # Generate SLA forecasts
    print("\n📊 Generating 7-day SLA forecasts...")
    sla_forecasts = predictor.predict(forecast_horizon=7, store_codes=['417', '331', '213'])
    
    print(f"✅ Generated {len(sla_forecasts)} SLA forecasts")
    
    # Display sample SLA forecasts
    print("\n📋 Sample SLA Forecasts:")
    print("-" * 90)
    print(f"{'Date':<12} {'Store':<6} {'Pred.SLA':<9} {'Conf.Int.':<15} {'Risk Factors':<12} {'Recommendations'}")
    print("-" * 90)
    
    for forecast in sla_forecasts[:10]:  # Show first 10
        conf_int = f"({forecast.confidence_interval[0]:.3f},{forecast.confidence_interval[1]:.3f})"
        risk_count = len(forecast.risk_factors)
        rec_count = len(forecast.improvement_recommendations)
        
        print(f"{forecast.forecast_date} {forecast.store_code:<6} "
              f"{forecast.predicted_sla_rate:>7.3f} "
              f"{conf_int:<15} "
              f"{risk_count:>8} risks "
              f"{rec_count:>8} recs")
    
    # Detailed analysis for one forecast
    sample_forecast = sla_forecasts[0]
    print(f"\n🔍 Detailed Analysis for {sample_forecast.store_code} on {sample_forecast.forecast_date}:")
    print(f"   Predicted SLA Rate: {sample_forecast.predicted_sla_rate:.3f}")
    print(f"   Confidence Interval: [{sample_forecast.confidence_interval[0]:.3f}, {sample_forecast.confidence_interval[1]:.3f}]")
    
    print(f"\n   🚨 Risk Factors:")
    for factor, value in sample_forecast.risk_factors.items():
        print(f"      • {factor}: {value:.3f}")
    
    print(f"\n   💡 Improvement Recommendations:")
    for i, rec in enumerate(sample_forecast.improvement_recommendations, 1):
        print(f"      {i}. {rec}")
    
    # Test risk factor identification
    print(f"\n🎯 Risk Factor Analysis Example:")
    risk_factors = predictor.identify_risk_factors('417', date.today() + timedelta(days=1))
    print(f"   Store: 417, Date: {date.today() + timedelta(days=1)}")
    print(f"   Identified {len(risk_factors)} risk factors:")
    for factor, value in risk_factors.items():
        severity = "🔴 High" if value > 0.2 else "🟡 Medium" if value > 0.1 else "🟢 Low"
        print(f"      • {factor}: {value:.3f} ({severity})")
    
    # Test real-time monitoring
    print(f"\n📡 Real-time Monitoring Simulation:")
    from unittest.mock import Mock
    
    # Create mock active orders
    active_orders = []
    for i in range(15):
        order = Mock()
        order.fulfillment_store_code = np.random.choice(['417', '331', '213'])
        order.order_create_time = datetime.now() - timedelta(hours=np.random.randint(1, 48))
        active_orders.append(order)
    
    metrics = predictor.monitor_real_time_sla_performance(active_orders)
    print(f"   Monitoring {len(active_orders)} active orders")
    print(f"   Real-time metrics:")
    for metric, value in metrics.items():
        if isinstance(value, float):
            if 'sla_rate' in metric:
                print(f"      • {metric}: {value:.3f}")
            elif 'time' in metric:
                print(f"      • {metric}: {value:.1f} hours")
            else:
                print(f"      • {metric}: {value:.2f}")
        else:
            print(f"      • {metric}: {value}")
    
    # Test alert generation
    print(f"\n🚨 Alert Generation:")
    alerts = predictor.generate_sla_alerts(sla_forecasts, threshold=0.92)
    print(f"   Generated {len(alerts)} alerts (threshold: 92%)")
    
    for alert in alerts[:3]:  # Show first 3 alerts
        print(f"   🔔 {alert['alert_type'].upper()} - Store {alert['store_code']}")
        print(f"      Severity: {alert['severity'].upper()}")
        if 'predicted_sla' in alert:
            print(f"      Predicted SLA: {alert['predicted_sla']:.3f}")
        print(f"      Timestamp: {alert['alert_timestamp'].strftime('%Y-%m-%d %H:%M:%S')}")
    
    return predictor, sla_forecasts

def demo_integration_analysis(forecaster, sla_predictor, demand_forecasts, sla_forecasts):
    """Demonstrate integration between forecasting components"""
    print("\n🔗 INTEGRATION ANALYSIS")
    print("=" * 50)
    
    # Analyze correlation between demand and SLA
    print("📊 Demand vs SLA Correlation Analysis:")
    
    # Group forecasts by store and date
    demand_by_store_date = {}
    sla_by_store_date = {}
    
    for forecast in demand_forecasts:
        key = (forecast.store_code, forecast.forecast_date)
        demand_by_store_date[key] = forecast.predicted_demand
    
    for forecast in sla_forecasts:
        key = (forecast.store_code, forecast.forecast_date)
        sla_by_store_date[key] = forecast.predicted_sla_rate
    
    # Find matching forecasts
    matching_keys = set(demand_by_store_date.keys()) & set(sla_by_store_date.keys())
    
    if matching_keys:
        print(f"   Found {len(matching_keys)} matching forecasts")
        
        # Calculate correlation
        demands = [demand_by_store_date[key] for key in matching_keys]
        slas = [sla_by_store_date[key] for key in matching_keys]
        
        correlation = np.corrcoef(demands, slas)[0, 1]
        print(f"   Demand-SLA Correlation: {correlation:.3f}")
        
        # Show examples
        print(f"\n   Sample Demand-SLA Pairs:")
        print(f"   {'Store':<6} {'Date':<12} {'Demand':<8} {'SLA':<8} {'Relationship'}")
        print(f"   {'-'*50}")
        
        for key in list(matching_keys)[:5]:
            store, date = key
            demand = demand_by_store_date[key]
            sla = sla_by_store_date[key]
            
            if demand > 60 and sla < 0.93:
                relationship = "High demand → Low SLA"
            elif demand < 40 and sla > 0.95:
                relationship = "Low demand → High SLA"
            else:
                relationship = "Normal"
            
            print(f"   {store:<6} {date} {demand:>6.1f} {sla:>6.3f} {relationship}")
    
    # External factor impact analysis
    print(f"\n🌤️ External Factor Impact Analysis:")
    
    weather_impacts = []
    holiday_impacts = []
    
    for forecast in demand_forecasts:
        if 'weather_impact' in forecast.external_factors:
            weather_impacts.append(forecast.external_factors['weather_impact'])
        if 'holiday_impact' in forecast.external_factors:
            holiday_impacts.append(forecast.external_factors['holiday_impact'])
    
    if weather_impacts:
        avg_weather_impact = np.mean(weather_impacts)
        print(f"   Average weather impact on demand: {avg_weather_impact:+.3f}")
        print(f"   Weather impact range: [{min(weather_impacts):+.3f}, {max(weather_impacts):+.3f}]")
    
    if holiday_impacts:
        avg_holiday_impact = np.mean(holiday_impacts)
        print(f"   Average holiday impact on demand: {avg_holiday_impact:+.3f}")
        print(f"   Holiday impact range: [{min(holiday_impacts):+.3f}, {max(holiday_impacts):+.3f}]")
    
    # Risk factor analysis
    print(f"\n⚠️ Risk Factor Summary:")
    
    all_risk_factors = {}
    for forecast in sla_forecasts:
        for factor, value in forecast.risk_factors.items():
            if factor not in all_risk_factors:
                all_risk_factors[factor] = []
            all_risk_factors[factor].append(value)
    
    print(f"   Identified {len(all_risk_factors)} types of risk factors:")
    for factor, values in all_risk_factors.items():
        avg_risk = np.mean(values)
        max_risk = max(values)
        frequency = len([v for v in values if v > 0.1])  # Significant risk occurrences
        
        print(f"   • {factor}:")
        print(f"     Average: {avg_risk:.3f}, Max: {max_risk:.3f}, Significant occurrences: {frequency}")

def main():
    """Main demonstration function"""
    print("🚀 PROPHET-BASED FORECASTING ENGINE & SLA PREDICTOR DEMO")
    print("=" * 60)
    print("Demonstrating Task 2.1 and Task 2.3 implementations")
    print("=" * 60)
    
    # Create demo data
    data = create_comprehensive_demo_data()
    
    # Demonstrate Prophet forecaster
    forecaster, demand_forecasts = demo_prophet_forecaster(data)
    
    # Demonstrate SLA predictor
    sla_predictor, sla_forecasts = demo_sla_predictor(data)
    
    # Demonstrate integration
    demo_integration_analysis(forecaster, sla_predictor, demand_forecasts, sla_forecasts)
    
    print("\n🎉 DEMONSTRATION COMPLETED!")
    print("=" * 60)
    print("✅ Task 2.1: Prophet-based Forecasting Engine - IMPLEMENTED")
    print("   • True Prophet model training with seasonality detection")
    print("   • External regressor support (weather, holidays, traffic)")
    print("   • Confidence interval calculation (P10/P50/P90)")
    print("   • Model persistence and loading capabilities")
    print()
    print("✅ Task 2.3: SLA Predictor with Risk Assessment - IMPLEMENTED")
    print("   • SLA compliance probability prediction")
    print("   • Comprehensive risk factor identification")
    print("   • Improvement recommendation generation")
    print("   • Real-time SLA monitoring capabilities")
    print()
    print("🔗 Integration Features:")
    print("   • Demand-SLA correlation analysis")
    print("   • External factor impact assessment")
    print("   • Comprehensive risk factor analysis")
    print("   • Alert generation and monitoring")
    print("=" * 60)

if __name__ == "__main__":
    main()