"""
Generate mock data for testing
生成Stage 1关键 - Mock数据
"""

import pandas as pd
import numpy as np


def generate_mock_data(n_stores: int = 10, seed: int = 42) -> pd.DataFrame:
    """
    Generate mock forecast data for testing
    生成模拟预测数据用于测试
    
    Args:
        n_stores: Number of stores to generate
        seed: Random seed for reproducibility
    
    Returns:
        DataFrame with mock forecast data
    """
    np.random.seed(seed)
    
    data = []
    
    for i in range(n_stores):
        store_data = {
            'store_id': i + 1,
            'demand': np.random.randint(10, 50),  # Demand between 10-50 units
            'tw_start': 8 * 60 + np.random.randint(0, 120),  # 8:00-10:00 AM
            'tw_end': 18 * 60,  # Fixed end time at 6:00 PM
            'lat': 40.7 + np.random.uniform(-0.1, 0.1),  # Near NYC
            'lon': -74.0 + np.random.uniform(-0.1, 0.1)
        }
        data.append(store_data)
    
    df = pd.DataFrame(data)
    
    # Rename to match interface requirements
    df = df.rename(columns={
        'tw_start': 'time_window_start',
        'tw_end': 'time_window_end'
    })
    
    return df


def save_mock_data(df: pd.DataFrame, file_path: str):
    """
    Save mock data to file
    保存模拟数据到文件
    
    Args:
        df: DataFrame with mock data
        file_path: Output file path
    """
    if file_path.endswith('.csv'):
        df.to_csv(file_path, index=False)
    elif file_path.endswith(('.xls', '.xlsx')):
        df.to_excel(file_path, index=False)
    else:
        raise ValueError(f"Unsupported file format: {file_path}")
    
    print(f"Mock data saved to: {file_path}")


if __name__ == "__main__":
    # Generate mock data
    mock_df = generate_mock_data(n_stores=10)
    
    # Display
    print("Generated Mock Data:")
    print(mock_df.to_string())
    
    # Save to CSV
    save_mock_data(mock_df, "../data/mock/mock_forecast.csv")
