"""
测试所有外部数据接入功能
验证各个数据源的连通性和数据质量

使用方法:
    python scripts/test_data_integration.py
"""
import sys
from pathlib import Path

# 添加项目根目录到路径
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

def test_hko_weather_api():
    """测试 HKO 天气 API"""
    print(f"\n{'='*60}")
    print("测试 P1: HKO 天气数据 API")
    print(f"{'='*60}\n")
    
    try:
        from src.modules.data.implementations.hko_weather_api import HKOWeatherAPI
        
        api = HKOWeatherAPI()
        
        # 测试当前天气
        print("1. 当前天气:")
        current = api.get_current_weather()
        print(f"   ✓ 温度: {current.temperature}°C")
        print(f"   ✓ 湿度: {current.humidity}%")
        print(f"   ✓ 更新时间: {current.update_time}")
        
        # 测试9天预报
        print("\n2. 9天天气预报:")
        forecasts = api.get_9day_forecast()
        print(f"   ✓ 获取到 {len(forecasts)} 天预报")
        if forecasts:
            f = forecasts[0]
            print(f"   ✓ 示例: {f.forecast_date} - {f.temp_min}~{f.temp_max}°C")
        
        # 测试天气警告
        print("\n3. 天气警告:")
        warnings = api.get_weather_warnings()
        if warnings:
            print(f"   ⚠️  当前有 {len(warnings)} 个警告: {list(warnings.keys())}")
        else:
            print(f"   ✓ 当前无警告")
        
        print("\n✅ HKO API 测试通过!")
        return True
        
    except Exception as e:
        print(f"\n❌ HKO API 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_store_coordinates():
    """测试门店坐标数据"""
    print(f"\n{'='*60}")
    print("测试 P0: 门店坐标数据")
    print(f"{'='*60}\n")
    
    import pandas as pd
    
    # 检查原始门店数据
    store_file = PROJECT_ROOT / 'data/dfi/raw/dim_store.csv'
    if not store_file.exists():
        print(f"❌ 找不到门店数据文件: {store_file}")
        return False
    
    df = pd.read_csv(store_file)
    print(f"✓ 门店数据文件存在: {len(df)} 家门店")
    
    # 检查是否已有坐标数据
    coord_file = PROJECT_ROOT / 'data/dfi/processed/store_coordinates.csv'
    coord_file_district = PROJECT_ROOT / 'data/dfi/processed/store_coordinates_district_centers.csv'
    
    if coord_file.exists():
        coord_df = pd.read_csv(coord_file)
        success_count = len(coord_df[coord_df['geocode_status'] == 'SUCCESS'])
        print(f"✓ 坐标数据文件存在 (Google Maps): {success_count}/{len(coord_df)} 成功获取坐标")
        
        if success_count > 0:
            print(f"\n示例坐标:")
            sample = coord_df[coord_df['geocode_status'] == 'SUCCESS'].head(3)
            for _, row in sample.iterrows():
                print(f"  {row['store_code']}: ({row['latitude']:.6f}, {row['longitude']:.6f})")
            print("\n✅ 门店坐标数据测试通过!")
            return True
        else:
            print(f"\n⚠️  坐标数据存在但无成功记录")
            print(f"   请运行: python scripts/geocode_stores.py")
            return False
    elif coord_file_district.exists():
        coord_df = pd.read_csv(coord_file_district)
        success_count = len(coord_df[coord_df['geocode_status'] == 'SUCCESS_DISTRICT_CENTER'])
        print(f"✓ 坐标数据文件存在 (区域中心点): {success_count}/{len(coord_df)} 成功获取坐标")
        
        if success_count > 0:
            print(f"\n示例坐标:")
            sample = coord_df[coord_df['geocode_status'] == 'SUCCESS_DISTRICT_CENTER'].head(3)
            for _, row in sample.iterrows():
                print(f"  {row['store_code']}: ({row['latitude']:.6f}, {row['longitude']:.6f})")
            print(f"\n⚠️  注意: 使用的是区域中心点近似坐标,精度较低")
            print(f"   推荐运行: python scripts/geocode_stores.py (需要 Google Maps API Key)")
            print("\n✅ 门店坐标数据测试通过 (使用区域中心点)!")
            return True
        else:
            print(f"\n⚠️  坐标数据存在但无成功记录")
            return False
    else:
        print(f"\n⚠️  坐标数据文件不存在: {coord_file}")
        print(f"   请先运行以下命令之一:")
        print(f"   1. python scripts/geocode_stores.py (需要 Google Maps API Key)")
        print(f"   2. python scripts/geocode_stores_district_centers.py (使用区域中心点)")
        return False

def test_public_holidays():
    """测试公众假期数据"""
    print(f"\n{'='*60}")
    print("测试 P3: 公众假期数据")
    print(f"{'='*60}\n")
    
    import json
    
    holiday_file = PROJECT_ROOT / 'data/official/public_holidays_2025.json'
    
    if holiday_file.exists():
        with open(holiday_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        if 'vcalendar' in data and len(data['vcalendar']) > 0:
            events = data['vcalendar'][0].get('vevent', [])
            print(f"✓ 公众假期数据文件存在: {len(events)} 个假期")
            
            # 显示前3个假期
            print(f"\n示例假期:")
            for i, event in enumerate(events[:3], 1):
                date_str = event.get('dtstart', [''])[0]
                if len(date_str) == 8:
                    date_formatted = f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}"
                    print(f"  {i}. {date_formatted}: {event.get('summary', 'Unknown')}")
            
            print("\n✅ 公众假期数据测试通过!")
            return True
        else:
            print(f"❌ 公众假期数据格式错误")
            return False
    else:
        print(f"⚠️  公众假期数据文件不存在: {holiday_file}")
        print(f"   请运行: python scripts/download_public_holidays.py")
        return False

def test_traffic_data():
    """测试交通数据"""
    print(f"\n{'='*60}")
    print("测试 P2: 交通数据")
    print(f"{'='*60}\n")
    
    import json
    from pathlib import Path
    
    traffic_dir = PROJECT_ROOT / 'data/official/traffic'
    
    if not traffic_dir.exists():
        print(f"⚠️  交通数据目录不存在: {traffic_dir}")
        print(f"   请运行: python scripts/fetch_traffic_data.py")
        return False
    
    # 查找最新的交通数据文件
    json_files = list(traffic_dir.glob('traffic_speed_map_*.json'))
    
    if json_files:
        latest_file = max(json_files, key=lambda p: p.stat().st_mtime)
        
        with open(latest_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        print(f"✓ 找到交通数据文件: {latest_file.name}")
        print(f"✓ 路段数据: {len(data)} 条")
        
        if data:
            print(f"\n示例数据:")
            # 检查数据结构
            if isinstance(data, list):
                for i, segment in enumerate(data[:3], 1):
                    print(f"  {i}. {segment.get('road_name', 'Unknown')}")
                    print(f"     速度: {segment.get('traffic_speed', 'N/A')}")
            elif isinstance(data, dict):
                print(f"  数据类型: {type(data)}")
                print(f"  键: {list(data.keys())[:5]}")
            else:
                print(f"  数据类型: {type(data)}")
                print(f"  内容: {str(data)[:200]}...")
        
        print("\n✅ 交通数据测试通过!")
        return True
    else:
        print(f"⚠️  交通数据目录存在但无数据文件")
        print(f"   请运行: python scripts/fetch_traffic_data.py")
        return False

def main():
    """主函数"""
    print(f"\n{'#'*60}")
    print("# 外部数据接入测试")
    print(f"{'#'*60}")
    
    results = {
        'HKO Weather API (P1)': test_hko_weather_api(),
        'Store Coordinates (P0)': test_store_coordinates(),
        'Public Holidays (P3)': test_public_holidays(),
        'Traffic Data (P2)': test_traffic_data(),
    }
    
    # 总结
    print(f"\n{'='*60}")
    print("测试总结")
    print(f"{'='*60}\n")
    
    for name, result in results.items():
        status = "✅ 通过" if result else "❌ 失败"
        print(f"{status} - {name}")
    
    passed = sum(results.values())
    total = len(results)
    
    print(f"\n总计: {passed}/{total} 通过")
    
    if passed == total:
        print("\n🎉 所有数据源测试通过!")
    else:
        print("\n⚠️  部分数据源需要配置,请查看上面的提示")
    
    print(f"\n{'='*60}")

if __name__ == '__main__':
    main()
