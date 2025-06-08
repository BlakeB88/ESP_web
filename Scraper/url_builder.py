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

# Comprehensive event mappings for SwimCloud - matches data_scraper.py
EVENT_MAPPINGS = {
    # Freestyle events
    "50_free": "1|50|1",
    "100_free": "1|100|1", 
    "200_free": "1|200|1",
    "500_free": "1|500|1",
    "1000_free": "1|1000|1",  # Added to match scraper
    "1650_free": "1|1500|1",  # Maps to 1500 code but represents 1650 data
    
    # Backstroke events
    "50_back": "2|50|1",      # Added to match scraper
    "100_back": "2|100|1",
    "200_back": "2|200|1", 
    
    # Breaststroke events
    "50_breast": "3|50|1",    # Added to match scraper
    "100_breast": "3|100|1",
    "200_breast": "3|200|1",
    
    # Butterfly events
    "50_fly": "4|50|1",       # Added to match scraper
    "100_fly": "4|100|1",
    "200_fly": "4|200|1",
    
    # Individual Medley events
    "200_im": "5|200|1",
    "400_im": "5|400|1"
}

# Reverse mapping for the scraper - maps SwimCloud codes back to readable names
EVENT_CODE_TO_NAME = {
    "1|50|1": "50 free",
    "1|100|1": "100 free",
    "1|200|1": "200 free",
    "1|500|1": "500 free",
    "1|1000|1": "1000 free",
    "1|1500|1": "1650 free",  # FIXED: Maps 1500 code to 1650 name (since SwimCloud returns 1650 data)
    "2|50|1": "50 back",
    "2|100|1": "100 back",
    "2|200|1": "200 back",
    "3|50|1": "50 breast",
    "3|100|1": "100 breast",
    "3|200|1": "200 breast",
    "4|50|1": "50 fly",
    "4|100|1": "100 fly",
    "4|200|1": "200 fly",
    "5|200|1": "200 IM",
    "5|400|1": "400 IM"
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

def get_event_code(event_name):
    """
    Convert event name (like "50_free") to SwimCloud event code (like "1|50|1").
    """
    return EVENT_MAPPINGS.get(event_name)

def get_event_name_from_code(event_code):
    """
    Convert SwimCloud event code back to readable name.
    This helps the scraper identify what event it's processing.
    """
    return EVENT_CODE_TO_NAME.get(event_code, f"Unknown ({event_code})")

def get_available_events():
    """
    Return list of all available event names that can be used with this builder.
    """
    return list(EVENT_MAPPINGS.keys())

def build_swimcloud_times_url(team_id, year=2024, gender="M", event=None):
    """
    Build a SwimCloud times URL for a single event or all events if event=None.
    
    Args:
        team_id: SwimCloud team ID
        year: Season year
        gender: "M" or "F"
        event: Event name like "50_free" or SwimCloud code like "1|50|1", or None for all events
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
        # Handle both event names ("50_free") and event codes ("1|50|1")
        if event in EVENT_MAPPINGS:
            # It's an event name, convert to code
            event_code = EVENT_MAPPINGS[event]
            params['event'] = event_code
            print(f"[DEBUG] Building URL for event name '{event}' -> code '{event_code}'")
        elif event in EVENT_CODE_TO_NAME:
            # It's already an event code
            params['event'] = event
            print(f"[DEBUG] Building URL for event code: {event}")
        else:
            print(f"[WARNING] Unknown event '{event}'. Available events: {get_available_events()}")
            return None
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

# Example usage and testing
if __name__ == "__main__":
    print("Available events:")
    for event in get_available_events():
        code = get_event_code(event)
        name = get_event_name_from_code(code)
        print(f"  {event} -> {code} -> {name}")
    
    print("\nTesting URL building:")
    # Test with event name
    url1 = build_swimcloud_times_url(34, 2025, "M", "50_free")
    print(f"Event name URL: {url1}")
    
    # Test with event code
    url2 = build_swimcloud_times_url(34, 2025, "M", "1|50|1")
    print(f"Event code URL: {url2}")
    
    # Test all events
    url3 = build_swimcloud_times_url(34, 2025, "M")
    print(f"All events URL: {url3}")