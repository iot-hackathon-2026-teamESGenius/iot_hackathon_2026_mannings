"""
获取香港交通数据
从 data.gov.hk 获取实时交通数据和路径规划数据

支持的数据源:
1. Traffic Data of Strategic/Major Roads (实时交通数据)
2. TDAS API (路径规划API)
3. Traffic Speed Map (交通速度地图)

使用方法:
    python scripts/fetch_traffic_data.py
"""
import requests
import json
from pathlib import Path
from datetime import datetime, timedelta
import sys

# 添加项目根目录到路径
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# 文件路径
OUTPUT_DIR = PROJECT_ROOT / 'data/official/traffic'
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# API 端点
TDAS_API_URL = "https://tdas-api.hkemobility.gov.hk/tdas/api/route"
DATA_GOV_API_BASE = "https://api.data.gov.hk/v2/filter"

def fetch_tdas_route_data():
    """获取 TDAS 路径规划数据 (示例)"""
    
    print("正在测试 TDAS 路径规划 API...")
    print(f"API: {TDAS_API_URL}\n")
    
    # 示例: 从中环到旺角的路径规划
    payload = {
        "start": {
            "lat": 22.2860,  # 中环
            "long": 114.1510
        },
        "end": {
            "lat": 22.3193,  # 旺角
            "long": 114.1694
        },
        "departIn": 15,
        "lang": "en",
        "type": "ST",
        "tunnel": "wht"
    }
    
    try:
        response = requests.post(TDAS_API_URL, json=payload, timeout=30)
        response.raise_for_status()
        
        data = response.json()
        
        # 保存数据
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        json_file = OUTPUT_DIR / f'tdas_route_example_{timestamp}.json'
        
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        print(f"✓ TDAS 路径数据已保存至: {json_file}")
        
        # 显示结果摘要
        if 'jSpeed' in data:
            print(f"✓ 路径信息:")
            print(f"  平均速度: {data.get('jSpeed', 'N/A')}")
            print(f"  距离: {data.get('distU', 'N/A')}")
            print(f"  预计时间: {data.get('eta', 'N/A')}")
            
            # 显示可选路线
            if 'ar' in data and data['ar']:
                print(f"  可选路线: {len(data['ar'])} 条")
                for i, route in enumerate(data['ar'][:3], 1):
                    print(f"    {i}. {route.get('name', 'Unknown')}: {route.get('distU', 'N/A')}, {route.get('eta', 'N/A')}")
        
        return data
        
    except requests.RequestException as e:
        print(f"✗ TDAS API 请求失败: {e}")
        return None
    except json.JSONDecodeError as e:
        print(f"✗ TDAS API 响应解析失败: {e}")
        return None

def fetch_traffic_data_strategic_roads():
    """获取主要道路交通数据"""
    
    print(f"\n{'='*60}")
    print("正在获取主要道路交通数据...")
    
    # 使用 data.gov.hk API v2 获取最新数据
    # 数据集ID: hk-td-sm_4-traffic-data-strategic-major-roads
    
    try:
        # 构建查询参数
        query_params = {
            "q": json.dumps({
                "resource": "https://api.data.gov.hk/v2/filter",
                "section": 1,
                "format": "json"
            })
        }
        
        # 尝试获取数据集信息
        info_url = "https://data.gov.hk/en-data/api/3/action/package_show"
        info_params = {"id": "hk-td-sm_4-traffic-data-strategic-major-roads"}
        
        response = requests.get(info_url, params=info_params, timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            json_file = OUTPUT_DIR / f'traffic_strategic_roads_info_{timestamp}.json'
            
            with open(json_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            print(f"✓ 数据集信息已保存至: {json_file}")
            
            # 尝试获取实际数据资源
            if 'result' in data and 'resources' in data['result']:
                resources = data['result']['resources']
                print(f"✓ 找到 {len(resources)} 个数据资源")
                
                for i, resource in enumerate(resources[:3], 1):
                    print(f"  {i}. {resource.get('name', 'Unknown')}")
                    print(f"     格式: {resource.get('format', 'Unknown')}")
                    print(f"     URL: {resource.get('url', 'N/A')[:80]}...")
                    
                    # 尝试下载第一个资源
                    if i == 1 and resource.get('url'):
                        try:
                            data_response = requests.get(resource['url'], timeout=30)
                            if data_response.status_code == 200:
                                data_file = OUTPUT_DIR / f'traffic_strategic_roads_data_{timestamp}.{resource.get("format", "txt").lower()}'
                                
                                with open(data_file, 'wb') as f:
                                    f.write(data_response.content)
                                
                                print(f"     ✓ 数据已下载至: {data_file}")
                            else:
                                print(f"     ✗ 数据下载失败: HTTP {data_response.status_code}")
                        except Exception as e:
                            print(f"     ✗ 数据下载失败: {e}")
            
            return data
        else:
            print(f"✗ 获取数据集信息失败: HTTP {response.status_code}")
            return None
            
    except requests.RequestException as e:
        print(f"✗ 请求失败: {e}")
        return None
    except Exception as e:
        print(f"✗ 处理失败: {e}")
        return None

def fetch_traffic_speed_map():
    """获取交通速度地图数据"""
    
    print(f"\n{'='*60}")
    print("正在获取交通速度地图数据...")
    
    try:
        # 获取数据集信息
        info_url = "https://data.gov.hk/en-data/api/3/action/package_show"
        info_params = {"id": "hk-td-sm_1-traffic-speed-map"}
        
        response = requests.get(info_url, params=info_params, timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            json_file = OUTPUT_DIR / f'traffic_speed_map_info_{timestamp}.json'
            
            with open(json_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            print(f"✓ 交通速度地图信息已保存至: {json_file}")
            
            # 检查资源
            if 'result' in data and 'resources' in data['result']:
                resources = data['result']['resources']
                print(f"✓ 找到 {len(resources)} 个数据资源")
                
                for i, resource in enumerate(resources[:3], 1):
                    print(f"  {i}. {resource.get('name', 'Unknown')}")
                    print(f"     格式: {resource.get('format', 'Unknown')}")
                    print(f"     更新: {resource.get('last_modified', 'Unknown')}")
            
            return data
        else:
            print(f"✗ 获取交通速度地图信息失败: HTTP {response.status_code}")
            return None
            
    except Exception as e:
        print(f"✗ 获取交通速度地图失败: {e}")
        return None

def test_historical_data_api():
    """测试历史数据 API"""
    
    print(f"\n{'='*60}")
    print("正在测试历史数据 API...")
    
    # 测试昨天的数据
    yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y%m%d')
    
    test_urls = [
        f"https://api.data.gov.hk/v1/historical-archive/list-file-versions?url=https://resource.data.one.gov.hk/td/speedmap.xml&start={yesterday}&end={yesterday}",
        f"https://api.data.gov.hk/v1/historical-archive/list-file-versions?url=https://api.data.gov.hk/v2/filter&start={yesterday}&end={yesterday}"
    ]
    
    for i, url in enumerate(test_urls, 1):
        try:
            print(f"\n测试 API {i}: {url[:80]}...")
            response = requests.get(url, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                print(f"✓ API {i} 响应成功")
                print(f"  版本数: {data.get('version-count', 0)}")
                print(f"  总大小: {data.get('total-size', 0)} bytes")
                
                if data.get('timestamps'):
                    print(f"  时间戳: {len(data['timestamps'])} 个")
                    print(f"  示例: {data['timestamps'][:3]}")
            else:
                print(f"✗ API {i} 失败: HTTP {response.status_code}")
                print(f"  响应: {response.text[:200]}")
                
        except Exception as e:
            print(f"✗ API {i} 异常: {e}")

def main():
    """主函数"""
    print(f"{'='*60}")
    print("香港交通数据获取工具 (更新版)")
    print(f"{'='*60}\n")
    
    results = {}
    
    # 1. 测试 TDAS 路径规划 API
    print("1. TDAS 路径规划 API")
    results['tdas'] = fetch_tdas_route_data()
    
    # 2. 获取主要道路交通数据
    print("\n2. 主要道路交通数据")
    results['strategic_roads'] = fetch_traffic_data_strategic_roads()
    
    # 3. 获取交通速度地图
    print("\n3. 交通速度地图")
    results['speed_map'] = fetch_traffic_speed_map()
    
    # 4. 测试历史数据 API
    print("\n4. 历史数据 API 测试")
    test_historical_data_api()
    
    # 总结
    print(f"\n{'='*60}")
    print("获取结果总结:")
    print(f"{'='*60}")
    
    success_count = sum(1 for v in results.values() if v is not None)
    total_count = len(results)
    
    for name, result in results.items():
        status = "✅ 成功" if result is not None else "❌ 失败"
        print(f"{status} - {name}")
    
    print(f"\n总计: {success_count}/{total_count} 成功")
    print(f"数据保存目录: {OUTPUT_DIR}")
    
    if success_count > 0:
        print(f"\n💡 使用建议:")
        print(f"  - TDAS API 适用于实时路径规划和配送优化")
        print(f"  - 主要道路数据适用于交通状况分析")
        print(f"  - 交通速度地图适用于配送时间估算")
    
    print(f"\n{'='*60}")

if __name__ == '__main__':
    main()
