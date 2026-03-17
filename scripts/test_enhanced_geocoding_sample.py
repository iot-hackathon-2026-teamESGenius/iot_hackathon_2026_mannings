#!/usr/bin/env python3
"""
Test Enhanced Geocoding on Sample Stores
========================================

Test the enhanced geocoding system on a small sample of stores to verify accuracy.
"""

import pandas as pd
import sys
import os

# Add the current directory to Python path to import our modules
sys.path.append('.')

# Import our enhanced geocoder
from scripts.geocode_stores_enhanced_v2 import EnhancedGeocoder

def test_sample_stores():
    """Test enhanced geocoding on a sample of stores"""
    print("🧪 Testing Enhanced Geocoding on Sample Stores")
    print("=" * 55)
    
    # Load store data
    try:
        df = pd.read_csv('data/dfi/raw/dim_store.csv')
        print(f"📊 Loaded {len(df)} stores from dim_store.csv")
    except FileNotFoundError:
        print("❌ Could not find data/dfi/raw/dim_store.csv")
        return
    
    # Select a sample of stores for testing (first 5 stores)
    sample_df = df.head(5)
    
    print(f"🎯 Testing on {len(sample_df)} sample stores:")
    print("-" * 55)
    
    # Initialize geocoder
    geocoder = EnhancedGeocoder()
    
    results = []
    
    for idx, row in sample_df.iterrows():
        store_code = row['store \ncode']
        district = row['18 Districts']
        address = row['ADDRESS']
        
        print(f"\n🏪 Store {idx+1}: {store_code}")
        print(f"   District: {district}")
        print(f"   Address: {address}")
        
        # Geocode the address
        lat, lng, status, note = geocoder.geocode_address(address, district)
        
        print(f"   Result: {lat:.6f}, {lng:.6f}")
        print(f"   Status: {status}")
        print(f"   Note: {note}")
        
        # Store result
        results.append({
            'store_code': store_code,
            'district': district,
            'address': address,
            'latitude': lat,
            'longitude': lng,
            'geocode_status': status,
            'note': note
        })
    
    # Create results DataFrame
    results_df = pd.DataFrame(results)
    
    # Save sample results
    output_file = 'data/dfi/processed/store_coordinates_sample_test.csv'
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    results_df.to_csv(output_file, index=False, encoding='utf-8')
    
    print(f"\n📊 Sample Test Statistics:")
    print(f"  Google Maps: {geocoder.stats['google_success']} successes")
    print(f"  CSDI: {geocoder.stats['csdi_success']} successes")
    print(f"  LocationIQ: {geocoder.stats['locationiq_success']} successes")
    print(f"  Nominatim: {geocoder.stats['nominatim_success']} successes")
    print(f"  District Fallback: {geocoder.stats['district_fallback']} used")
    
    # Calculate success rates
    total_stores = len(results_df)
    precise_geocoding = (geocoder.stats['google_success'] + 
                        geocoder.stats['csdi_success'] + 
                        geocoder.stats['locationiq_success'] + 
                        geocoder.stats['nominatim_success'])
    
    precise_rate = (precise_geocoding / total_stores) * 100
    
    print(f"\n🎯 Sample Results Summary:")
    print(f"  Total stores tested: {total_stores}")
    print(f"  Precise geocoding: {precise_geocoding} ({precise_rate:.1f}%)")
    print(f"  District fallback: {geocoder.stats['district_fallback']} ({(geocoder.stats['district_fallback']/total_stores)*100:.1f}%)")
    print(f"  Results saved to: {output_file}")
    
    # Show coordinate comparison
    print(f"\n📍 Coordinate Comparison:")
    print("-" * 55)
    
    # Load old coordinates for comparison
    try:
        old_df = pd.read_csv('data/dfi/processed/store_coordinates_district_centers.csv')
        old_sample = old_df.head(5)
        
        print("Store | Old Coordinates | New Coordinates | Improvement")
        print("-" * 55)
        
        for i, (old_row, new_row) in enumerate(zip(old_sample.iterrows(), results_df.iterrows())):
            old_lat, old_lng = old_row[1]['latitude'], old_row[1]['longitude']
            new_lat, new_lng = new_row[1]['latitude'], new_row[1]['longitude']
            
            # Calculate distance improvement (rough estimate)
            lat_diff = abs(new_lat - old_lat)
            lng_diff = abs(new_lng - old_lng)
            distance_diff = ((lat_diff**2 + lng_diff**2)**0.5) * 111000  # Convert to meters
            
            improvement = "✅ Improved" if distance_diff > 100 else "➡️ Similar"
            
            print(f"{new_row[1]['store_code']:<5} | {old_lat:.4f},{old_lng:.4f} | {new_lat:.4f},{new_lng:.4f} | {improvement}")
            
    except FileNotFoundError:
        print("⚠️ Old coordinates file not found for comparison")
    
    print("\n✅ Sample test completed successfully!")
    print("🚀 Ready to run full geocoding with: python scripts/geocode_stores_enhanced_v2.py")

if __name__ == "__main__":
    test_sample_stores()