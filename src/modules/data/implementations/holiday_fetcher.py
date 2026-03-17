#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Hong Kong Public Holiday Data Fetcher
Implements HolidayDataFetcher interface for data.gov.hk API

Created: 2026-03-17
Author: Team ESGenius
"""

import requests
import json
import logging
from datetime import datetime, date
from typing import List, Optional, Dict, Any
from pathlib import Path

try:
    from ...core.interfaces import HolidayDataFetcher
    from ...core.data_schema import PublicHoliday
except ImportError:
    # For direct execution
    import sys
    sys.path.append(str(Path(__file__).parent.parent.parent.parent))
    from src.core.interfaces import HolidayDataFetcher
    from src.core.data_schema import PublicHoliday

logger = logging.getLogger(__name__)

class HKHolidayFetcher(HolidayDataFetcher):
    """Hong Kong Public Holiday Data Fetcher"""
    
    def __init__(self, timeout: int = 10, cache_dir: str = "data/official"):
        self.timeout = timeout
        self.api_url = "https://www.1823.gov.hk/common/ical/en.json"
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self._cache = {}
        self._cache_ttl = 86400  # 24 hours cache for holidays
    
    def fetch_data(self, start_date: date, end_date: date, **kwargs) -> List[PublicHoliday]:
        """Fetch holiday data for date range"""
        try:
            # Get year range
            start_year = start_date.year
            end_year = end_date.year
            
            all_holidays = []
            for year in range(start_year, end_year + 1):
                year_holidays = self.fetch_holidays(year)
                all_holidays.extend(year_holidays)
            
            # Filter by date range
            filtered = []
            for holiday in all_holidays:
                if start_date <= holiday.date <= end_date:
                    filtered.append(holiday)
            
            return filtered
        except Exception as e:
            logger.error(f"Failed to fetch holiday data: {e}")
            return []
    
    def is_available(self) -> bool:
        """Check if holiday API is available"""
        try:
            response = requests.get(self.api_url, timeout=5)
            return response.status_code == 200
        except:
            return False
    
    def get_last_update_time(self) -> Optional[datetime]:
        """Get last update time (not available for this API)"""
        return None
    
    def fetch_holidays(self, year: int) -> List[PublicHoliday]:
        """Fetch holidays for specific year"""
        cache_key = f'holidays_{year}'
        
        # Check cache first
        if cache_key in self._cache:
            cache_time, holidays = self._cache[cache_key]
            if (datetime.now() - cache_time).total_seconds() < self._cache_ttl:
                return holidays
        
        try:
            # Try online API first
            holidays = self._fetch_online_holidays(year)
            
            if not holidays:
                # Fallback to local cache file
                holidays = self._load_cached_holidays(year)
            else:
                # Save to local cache
                self._save_holidays_cache(holidays, year)
            
            # Update memory cache
            self._cache[cache_key] = (datetime.now(), holidays)
            
            return holidays
            
        except Exception as e:
            logger.error(f"Failed to fetch holidays for {year}: {e}")
            return []
    
    def is_holiday(self, check_date: date) -> bool:
        """Check if specific date is a holiday"""
        holidays = self.fetch_holidays(check_date.year)
        return any(h.date == check_date for h in holidays)
    
    def _fetch_online_holidays(self, year: int) -> List[PublicHoliday]:
        """Fetch holidays from online API"""
        try:
            logger.info(f"Fetching holidays for {year} from online API...")
            
            response = requests.get(self.api_url, timeout=self.timeout)
            response.raise_for_status()
            
            data = response.json()
            holidays = []
            
            if 'vcalendar' in data and len(data['vcalendar']) > 0:
                events = data['vcalendar'][0].get('vevent', [])
                
                for event in events:
                    if 'dtstart' in event and 'summary' in event:
                        date_str = event['dtstart'][0]
                        
                        if len(date_str) == 8:  # YYYYMMDD format
                            event_date = datetime.strptime(date_str, '%Y%m%d').date()
                            
                            if event_date.year == year:
                                holiday = PublicHoliday(
                                    date=event_date,
                                    name=event['summary'],
                                    type="public"
                                )
                                holidays.append(holiday)
            
            logger.info(f"Successfully fetched {len(holidays)} holidays for {year}")
            return holidays
            
        except Exception as e:
            logger.error(f"Failed to fetch online holidays: {e}")
            return []
    
    def _load_cached_holidays(self, year: int) -> List[PublicHoliday]:
        """Load holidays from local cache file"""
        try:
            cache_file = self.cache_dir / f"public_holidays_{year}.json"
            
            if cache_file.exists():
                logger.info(f"Loading holidays from cache: {cache_file}")
                
                with open(cache_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                holidays = []
                if 'vcalendar' in data and len(data['vcalendar']) > 0:
                    events = data['vcalendar'][0].get('vevent', [])
                    
                    for event in events:
                        if 'dtstart' in event and 'summary' in event:
                            date_str = event['dtstart'][0]
                            
                            if len(date_str) == 8:
                                event_date = datetime.strptime(date_str, '%Y%m%d').date()
                                
                                if event_date.year == year:
                                    holiday = PublicHoliday(
                                        date=event_date,
                                        name=event['summary'],
                                        type="public"
                                    )
                                    holidays.append(holiday)
                
                logger.info(f"Loaded {len(holidays)} holidays from cache")
                return holidays
            else:
                logger.warning(f"No cache file found: {cache_file}")
                return []
                
        except Exception as e:
            logger.error(f"Failed to load cached holidays: {e}")
            return []
    
    def _save_holidays_cache(self, holidays: List[PublicHoliday], year: int):
        """Save holidays to local cache file"""
        try:
            cache_file = self.cache_dir / f"public_holidays_{year}.json"
            
            # Convert holidays back to iCal format for consistency
            events = []
            for holiday in holidays:
                event = {
                    'dtstart': [holiday.date.strftime('%Y%m%d')],
                    'summary': holiday.name,
                    'uid': f"holiday_{holiday.date.strftime('%Y%m%d')}@hk.gov"
                }
                events.append(event)
            
            data = {
                'vcalendar': [{
                    'vevent': events,
                    'prodid': 'HK Government Holiday Calendar',
                    'version': '2.0'
                }]
            }
            
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"Saved {len(holidays)} holidays to cache: {cache_file}")
            
        except Exception as e:
            logger.error(f"Failed to save holidays cache: {e}")
    
    def get_holiday_summary(self, year: int) -> Dict[str, Any]:
        """Get holiday summary for a year"""
        holidays = self.fetch_holidays(year)
        
        summary = {
            'year': year,
            'total_holidays': len(holidays),
            'holidays': []
        }
        
        for holiday in sorted(holidays, key=lambda h: h.date):
            summary['holidays'].append({
                'date': holiday.date.isoformat(),
                'name': holiday.name,
                'day_of_week': holiday.date.strftime('%A')
            })
        
        return summary

# Test function
def test_holiday_fetcher():
    """Test Holiday Fetcher"""
    fetcher = HKHolidayFetcher()
    
    print("Testing HK Holiday Fetcher...")
    print(f"API Available: {fetcher.is_available()}")
    
    # Test current year holidays
    current_year = datetime.now().year
    holidays = fetcher.fetch_holidays(current_year)
    print(f"Holidays for {current_year}: {len(holidays)}")
    
    for holiday in holidays[:5]:  # Show first 5
        print(f"  {holiday.date}: {holiday.name}")
    
    # Test specific date
    today = date.today()
    is_holiday = fetcher.is_holiday(today)
    print(f"Is today ({today}) a holiday? {is_holiday}")
    
    # Test summary
    summary = fetcher.get_holiday_summary(current_year)
    print(f"Holiday summary: {summary['total_holidays']} holidays")

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    test_holiday_fetcher()