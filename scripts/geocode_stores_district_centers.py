"""
门店地址地理编码脚本 - 使用区域中心点
这是一个快速原型方案,使用香港18区的中心点作为门店坐标的近似值

注意: 此方案精度较低(~2-5km误差),仅适合快速验证算法
推荐使用 geocode_stores.py (Google Maps API) 获取精确坐标

使用方法:
    python scripts/geocode_stores_district_centers.py
"""
import pandas as pd
from pathlib import Path
import sys

# 添加项目根目录到路径
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# 香港18区中心点坐标 (纬度, 经度)
HK_DISTRICT_CENTERS = {
    'Central & Western': (22.2860, 114.1510),
    'Wan Chai': (22.2780, 114.1710),
    'Eastern': (22.2840, 114.2240),
    'Southern': (22.2470, 114.1580),
    'Yau Tsim Mong': (22.3120, 114.1720),
    'Sham Shui Po': (22.3310, 114.1620),
    'Kowloon City': (22.3280, 114.1910),
    'Wong Tai Sin': (22.3420, 114.1950),
    'Kwun Tong': (22.3130, 114.2260),
    'Tsuen Wan': (22.3710, 114.1140),
    'Tuen Mun': (22.3910, 113.9770),
    'Yuen Long': (22.4450, 114.0220),
    'North': (22.4940, 114.1380),
    'Tai Po': (22.4510, 114.1640),
    'Sha Tin': (22.3870, 114.1950),
    'Sai Kung': (22.3830, 114.2700),
    'Kwai Tsing': (22.3560, 114.1300),
    'Islands': (22.2610, 113.9460),
}

# 文件路径
INPUT_FILE = PROJECT_ROOT / 'data/dfi/raw/dim_store.csv'
OUTPUT_FILE = PROJECT_ROOT / 'data/dfi/processed/store_coordinates_district_centers.csv'

def geocode_stores_by_district():
    """使用区域中心点为门店分配坐标"""
    
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
        
        # 查找区域中心点
        if district in HK_DISTRICT_CENTERS:
            lat, lng = HK_DISTRICT_CENTERS[district]
            status = 'SUCCESS_DISTRICT_CENTER'
            success_count += 1
            print(f"✓ [{idx + 1}/{len(df)}] {store_code} ({district}): {lat:.6f}, {lng:.6f}")
        else:
            lat, lng = None, None
            status = f'DISTRICT_NOT_FOUND: {district}'
            print(f"✗ [{idx + 1}/{len(df)}] {store_code}: 区域未找到 - {district}")
        
        results.append({
            'store_code': store_code,
            'district': district,
            'address': address,
            'latitude': lat,
            'longitude': lng,
            'geocode_status': status,
            'note': 'District center approximation - not exact location'
        })
    
    # 保存结果
    result_df = pd.DataFrame(results)
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    result_df.to_csv(OUTPUT_FILE, index=False, encoding='utf-8-sig')
    
    # 统计
    print(f"\n{'='*60}")
    print(f"完成! 成功: {success_count}/{len(df)} ({success_count/len(df)*100:.1f}%)")
    print(f"结果保存至: {OUTPUT_FILE}")
    print(f"\n⚠️  注意: 这些坐标是区域中心点的近似值,精度较低")
    print(f"    推荐使用 geocode_stores.py 获取精确坐标")
    print(f"{'='*60}")
    
    return result_df

if __name__ == '__main__':
    geocode_stores_by_district()
