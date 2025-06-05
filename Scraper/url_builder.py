import requests
from urllib.parse import urlencode
import re

BASE_URL = "https://www.swimcloud.com"

# Season ID mappings for SwimCloud
SEASON_MAPPINGS = {
    2025: 28,  # Based on provided URLs
    2024: 28,  # Updated to match provided URLs
    2023: 27,
    2022: 26,
    2021: 25,
    2020: 24,
    2019: 23
}

# Event mappings for SwimCloud
EVENT_MAPPINGS = {
    "50_free": "1|50|1",
    "100_free": "1|100|1", 
    "200_free": "1|200|1",
    "500_free": "1|500|1",
    "1650_free": "1|1650|1",
    "100_back": "2|100|1",
    "200_back": "2|200|1", 
    "100_breast": "3|100|1",
    "200_breast": "3|200|1",
    "100_fly": "4|100|1",
    "200_fly": "4|200|1",
    "200_im": "5|200|1",
    "400_im": "5|400|1"
}

def get_season_id(year):
    """
    Get SwimCloud season ID for a given year.
    """
    if year in SEASON_MAPPINGS:
        return SEASON_MAPPINGS[year]
    else:
        # Guess based on pattern
        base_year = 2025
        base_season = 28
        return base_season + (year - base_year)

def build_swimcloud_times_url(team_id, year=2024, gender="M", event=None):
    """
    Build a SwimCloud times URL for a single event or all events if event=None.
    """
    season_id = get_season_id(year)
    print(f"[DEBUG] Using season_id {season_id} for year {year}")
    
    base_url = f"{BASE_URL}/team/{team_id}/times/"
    
    params = {
        'dont_group': 'false',
        'event_course': 'Y',  # Short Course Yards
        'gender': gender.upper(),
        'page': '1',
        'season_id': str(season_id),
        'team_id': str(team_id),
        'year': str(year),
        'region': '',  # Match provided URLs
        'tag_id': ''   # Match provided URLs
    }
    
    if event:
        params['event'] = event
        print(f"[DEBUG] Building URL for event: {event}")
    else:
        print(f"[DEBUG] Building URL for all events")
    
    url = f"{base_url}?{urlencode(params)}"
    print(f"[DEBUG] Built URL: {url}")
    return url

def test_times_url(url):
    """
    Test if a URL returns valid time data with relaxed criteria.
    """
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
        "Connection": "keep-alive"
    }
    
    try:
        print(f"[DEBUG] Testing URL: {url}")
        response = requests.get(url, headers=headers, timeout=15)
        
        if response.status_code == 200:
            content = response.text.lower()
            
            # Look for time data indicators
            time_indicators = [
                'time', 'swimmer', 'event', 'season',
                '1:', '2:', ':00.', ':01.', ':02.',  # Time formats
                'freestyle', 'backstroke', 'butterfly', 'breaststroke',
                'free', 'back', 'fly', 'breast', 'medley', 'im'
            ]
            
            found_indicators = [indicator for indicator in time_indicators if indicator in content]
            
            if len(found_indicators) >= 2:  # Relaxed criteria
                print(f"[DEBUG] Found {len(found_indicators)} time indicators")
                
                # More flexible time pattern
                time_pattern = r'\d{1,2}:\d{2}\.\d{1,2}|\d{1,2}\.\d{1,2}'
                time_matches = re.findall(time_pattern, response.text)
                
                if len(time_matches) >= 1:
                    print(f"[DEBUG] Found {len(time_matches)} time entries")
                    print(f"[DEBUG] Working URL confirmed: {url}")
                    return True
                    
        print(f"[DEBUG] URL test failed - Status: {response.status_code}")
        return False
        
    except Exception as e:
        print(f"[DEBUG] URL test failed for {url}: {e}")
        return False