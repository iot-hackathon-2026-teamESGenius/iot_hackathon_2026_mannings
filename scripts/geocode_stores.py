"""
门店地址地理编码脚本
使用 Google Maps Geocoding API 获取门店经纬度

使用方法:
    # Windows PowerShell
    $env:GOOGLE_MAPS_API_KEY = "your-api-key"
    python scripts/geocode_stores.py

    # Linux/Mac
    export GOOGLE_MAPS_API_KEY="your-api-key"
    python scripts/geocode_stores.py
"""
import pandas as pd
import googlemaps
import time
import os
from pathlib import Path
import sys

# 添加项目根目录到路径
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# ========== 配置 ==========
# 方式1: 环境变量 (推荐)
API_KEY = os.getenv('GOOGLE_MAPS_API_KEY')

# 方式2: 从 .env 文件读取
try:
    from dotenv import load_dotenv
    load_dotenv()
    if not API_KEY:
        API_KEY = os.getenv('GOOGLE_MAPS_API_KEY')
except ImportError:
    pass

# 文件路径
INPUT_FILE = PROJECT_ROOT / 'data/dfi/raw/dim_store.csv'
OUTPUT_FILE = PROJECT_ROOT / 'data/dfi/processed/store_coordinates.csv'

def geocode_stores():
    """批量获取门店坐标"""
    if not API_KEY:
        print("错误: 请设置 GOOGLE_MAPS_API_KEY 环境变量")
        print("\nWindows PowerShell:")
        print('  $env:GOOGLE_MAPS_API_KEY = "your-api-key"')
        print("\nLinux/Mac:")
        print('  export GOOGLE_MAPS_API_KEY="your-api-key"')
        print("\n或者在项目根目录创建 .env 文件:")
        print('  GOOGLE_MAPS_API_KEY=your-api-key')
        return None
    
    print("初始化 Google Maps 客户端...")
    gmaps = googlemaps.Client(key=API_KEY)
    
    # 读取门店数据
    if not INPUT_FILE.exists():
        print(f"错误: 找不到输入文件 {INPUT_FILE}")
        return None
    
    df = pd.read_csv(INPUT_FILE)
    print(f"共 {len(df)} 家门店待处理\n")
    
    results = []
    success_count = 0
    
    for idx, row in df.iterrows():
        store_code = row['store \ncode']
        address = row['ADDRESS']
        district = row['18 Districts']
        
        # 构建完整地址 (添加Hong Kong后缀提高准确率)
        full_address = f"{address}, {district}, Hong Kong"
        
        try:
            # 调用API
            result = gmaps.geocode(full_address)
            
            if result:
                location = result[0]['geometry']['location']
                lat = location['lat']
                lng = location['lng']
                status = 'SUCCESS'
                success_count += 1
                print(f"✓ [{idx + 1}/{len(df)}] {store_code}: {lat:.6f}, {lng:.6f}")
            else:
                lat, lng = None, None
                status = 'NOT_FOUND'
                print(f"✗ [{idx + 1}/{len(df)}] {store_code}: 地址未找到")
                
        except Exception as e:
            lat, lng = None, None
            status = f'ERROR: {str(e)}'
            print(f"✗ [{idx + 1}/{len(df)}] {store_code}: 错误 - {str(e)}")
        
        results.append({
            'store_code': store_code,
            'district': district,
            'address': address,
            'latitude': lat,
            'longitude': lng,
            'geocode_status': status
        })
        
        # 避免超过API配额 (50 requests/second for Geocoding)
        time.sleep(0.1)
    
    # 保存结果
    result_df = pd.DataFrame(results)
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    result_df.to_csv(OUTPUT_FILE, index=False, encoding='utf-8-sig')
    
    # 统计
    print(f"\n{'='*60}")
    print(f"完成! 成功: {success_count}/{len(df)} ({success_count/len(df)*100:.1f}%)")
    print(f"结果保存至: {OUTPUT_FILE}")
    print(f"{'='*60}")
    
    return result_df

if __name__ == '__main__':
    geocode_stores()
