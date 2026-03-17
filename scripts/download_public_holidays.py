"""
下载香港公众假期数据
从 data.gov.hk 下载官方公众假期数据,并与 DFI 的 dim_date 进行对比验证

使用方法:
    python scripts/download_public_holidays.py
"""
import requests
import json
import pandas as pd
from pathlib import Path
from datetime import datetime
import sys

# 添加项目根目录到路径
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# 文件路径
OUTPUT_DIR = PROJECT_ROOT / 'data/official'
OUTPUT_FILE = OUTPUT_DIR / 'public_holidays_2025.json'
DIM_DATE_FILE = PROJECT_ROOT / 'data/dfi/raw/dim_date.csv'

# 香港政府公众假期API
HOLIDAY_API_URL = "https://www.1823.gov.hk/common/ical/en.json"

def download_public_holidays():
    """下载香港公众假期数据"""
    
    print("正在下载香港公众假期数据...")
    print(f"API: {HOLIDAY_API_URL}\n")
    
    try:
        response = requests.get(HOLIDAY_API_URL, timeout=30)
        response.raise_for_status()
        
        data = response.json()
        
        # 保存原始数据
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        print(f"✓ 数据已保存至: {OUTPUT_FILE}")
        
        # 解析假期列表
        if 'vcalendar' in data and len(data['vcalendar']) > 0:
            events = data['vcalendar'][0].get('vevent', [])
            
            holidays = []
            for event in events:
                if 'dtstart' in event and 'summary' in event:
                    date_str = event['dtstart'][0]
                    # 转换日期格式 YYYYMMDD -> YYYY-MM-DD
                    if len(date_str) == 8:
                        date_formatted = f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}"
                        holidays.append({
                            'date': date_formatted,
                            'name': event['summary']
                        })
            
            print(f"\n找到 {len(holidays)} 个公众假期:")
            for h in sorted(holidays, key=lambda x: x['date']):
                print(f"  {h['date']}: {h['name']}")
            
            return holidays
        else:
            print("警告: 无法解析假期数据")
            return []
            
    except requests.RequestException as e:
        print(f"✗ 下载失败: {e}")
        return None
    except json.JSONDecodeError as e:
        print(f"✗ JSON解析失败: {e}")
        return None

def verify_with_dim_date(official_holidays):
    """与 DFI 的 dim_date 进行对比验证"""
    
    if not DIM_DATE_FILE.exists():
        print(f"\n⚠️  找不到 dim_date 文件: {DIM_DATE_FILE}")
        print("   跳过验证步骤")
        return
    
    print(f"\n{'='*60}")
    print("验证 DFI dim_date 中的假期标记...")
    print(f"{'='*60}\n")
    
    # 读取 dim_date
    dim_date = pd.read_csv(DIM_DATE_FILE)
    
    # 确保日期格式一致
    dim_date['calendar_date'] = pd.to_datetime(dim_date['calendar_date']).dt.strftime('%Y-%m-%d')
    
    # 提取 DFI 标记的假期
    dfi_holidays = dim_date[dim_date['if_public_holiday'] == 1]['calendar_date'].tolist()
    
    # 提取官方假期日期
    official_dates = [h['date'] for h in official_holidays]
    
    # 对比
    print(f"DFI 假期数: {len(dfi_holidays)}")
    print(f"官方假期数: {len(official_dates)}")
    
    # 找出差异
    dfi_only = set(dfi_holidays) - set(official_dates)
    official_only = set(official_dates) - set(dfi_holidays)
    
    if dfi_only:
        print(f"\n⚠️  仅在 DFI 中标记为假期的日期 ({len(dfi_only)}):")
        for date in sorted(dfi_only):
            print(f"  {date}")
    
    if official_only:
        print(f"\n⚠️  仅在官方数据中的假期 ({len(official_only)}):")
        for date in sorted(official_only):
            # 找到对应的假期名称
            holiday_name = next((h['name'] for h in official_holidays if h['date'] == date), 'Unknown')
            print(f"  {date}: {holiday_name}")
    
    if not dfi_only and not official_only:
        print("\n✓ 验证通过! DFI 假期标记与官方数据完全一致")
    
    print(f"\n{'='*60}")

def main():
    """主函数"""
    holidays = download_public_holidays()
    
    if holidays:
        verify_with_dim_date(holidays)
        
        print(f"\n{'='*60}")
        print("完成!")
        print(f"{'='*60}")

if __name__ == '__main__':
    main()
