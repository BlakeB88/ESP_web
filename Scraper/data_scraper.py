import os
import time
import json
import re
from urllib.parse import urlparse, parse_qs, unquote
import requests
from bs4 import BeautifulSoup

def extract_event_name_from_url(url):
    """Extract event name from SwimCloud URL"""
    try:
        parsed_url = urlparse(url)
        query_params = parse_qs(parsed_url.query)
        
        print(f"[DEBUG] Original URL: {url}")
        print(f"[DEBUG] Parsed query parameters: {query_params}")
        
        if 'event' in query_params:
            raw_event = query_params['event'][0]
            print(f"[DEBUG] Raw event parameter: {raw_event}")
            
            # URL decode the event parameter
            decoded_event = unquote(raw_event)
            print(f"[DEBUG] URL decoded event: {decoded_event}")
            
            # Event format is typically: stroke_id|distance|course_id
            # Examples: "1|50|1" = 50 Free, "4|200|1" = 200 IM
            event_mapping = {
                # Freestyle events
                "1|50|1": "50 Free",
                "1|100|1": "100 Free", 
                "1|200|1": "200 Free",
                "1|500|1": "500 Free",
                "1|1000|1": "1000 Free",
                "1|1650|1": "1650 Free",
                
                # Backstroke events
                "2|50|1": "50 Back",
                "2|100|1": "100 Back",
                "2|200|1": "200 Back",
                
                # Breaststroke events
                "3|50|1": "50 Breast",
                "3|100|1": "100 Breast", 
                "3|200|1": "200 Breast",
                
                # Butterfly events
                "4|50|1": "50 Fly",
                "4|100|1": "100 Fly",
                "4|200|1": "200 Fly",
                
                # IM events (Individual Medley uses stroke_id 5)
                "5|100|1": "100 IM",
                "5|200|1": "200 IM",
                "5|400|1": "400 IM",
            }
            
            if decoded_event in event_mapping:
                event_name = event_mapping[decoded_event]
                print(f"[DEBUG] Found event name: {event_name}")
                return event_name
            else:
                print(f"[DEBUG] Unknown event code: {decoded_event}")
                return "Unknown Event"
        
        return "Unknown Event"
    except Exception as e:
        print(f"[DEBUG] Error extracting event name: {e}")
        return "Unknown Event"

def test_url_accessibility(url, max_retries=3):
    """Test if URL is accessible and returns expected content"""
    for attempt in range(max_retries):
        try:
            print(f"[DEBUG] Testing URL (attempt {attempt + 1}): {url}")
            
            # First test with requests
            headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.5 Safari/605.1.15'
            }
            
            response = requests.get(url, headers=headers, timeout=10)
            if response.status_code == 200:
                # Look for time indicators in the HTML
                soup = BeautifulSoup(response.content, 'html.parser')
                
                # Check for common time patterns (MM:SS.ss format)
                time_pattern = r'\d{1,2}:\d{2}\.\d{2}'
                time_matches = re.findall(time_pattern, response.text)
                
                # Also look for time elements or classes that might contain times
                time_elements = soup.find_all(['td', 'div', 'span'], class_=re.compile(r'time|result', re.I))
                
                print(f"[DEBUG] Found {len(time_matches)} time patterns")
                print(f"[DEBUG] Found {len(time_elements)} time elements")
                
                if time_matches or time_elements:
                    print(f"[DEBUG] URL appears to have timing data")
                    return True, len(time_matches) + len(time_elements)
                else:
                    print(f"[DEBUG] No timing data found in response")
            
            else:
                print(f"[DEBUG] HTTP {response.status_code} response")
        
        except Exception as e:
            print(f"[DEBUG] URL test failed (attempt {attempt + 1}): {e}")
            if attempt < max_retries - 1:
                time.sleep(2)
    
    return False, 0

def scrape_swimmer_times(url):
    """
    Scrape swimmer times from SwimCloud URL using requests + BeautifulSoup
    Returns a list of dictionaries containing swimmer data
    """
    try:
        # Extract event name from URL for context
        event_name = extract_event_name_from_url(url)
        print(f"[DEBUG] Scraping event: {event_name}")
        
        # Test URL accessibility first
        print(f"[DEBUG] Testing URL: {url}")
        is_accessible, indicator_count = test_url_accessibility(url)
        
        if is_accessible:
            print(f"[DEBUG] Found {indicator_count} time indicators")
            print(f"[DEBUG] Found {max(0, indicator_count - 1)} time entries")  # Subtract header
            print(f"[DEBUG] Working URL confirmed: {url}")
        else:
            print(f"[WARNING] URL may not contain expected data: {url}")
        
        print(f"[DEBUG] Scraping swimmer times from: {url}")
        
        # Use requests + BeautifulSoup approach (no Selenium needed)
        print(f"[DEBUG] Using requests + BeautifulSoup approach...")
        return scrape_with_requests_fallback(url)
    
    except Exception as e:
        print(f"[ERROR] Critical error in scrape_swimmer_times: {e}")
        import traceback
        traceback.print_exc()
        return []

def scrape_with_requests_fallback(url):
    """
    Fallback scraping method using requests + BeautifulSoup
    Use this when Selenium fails
    """
    try:
        print(f"[DEBUG] Attempting requests fallback for: {url}")
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        }
        
        # Try multiple times with different approaches
        for attempt in range(3):
            try:
                print(f"[DEBUG] Requests attempt {attempt + 1}")
                
                session = requests.Session()
                session.headers.update(headers)
                
                response = session.get(url, timeout=15)
                response.raise_for_status()
                
                soup = BeautifulSoup(response.content, 'html.parser')
                
                # Extract event name
                event_name = extract_event_name_from_url(url)
                
                # Look for swimmer data in tables
                swimmers_data = []
                
                # Find all table rows
                rows = soup.find_all('tr')
                print(f"[DEBUG] Found {len(rows)} table rows")
                
                for i, row in enumerate(rows):
                    try:
                        row_text = row.get_text(strip=True)
                        if not row_text:
                            continue
                        
                        # Look for time pattern
                        time_pattern = r'(\d{1,2}:\d{2}\.\d{2})'
                        time_match = re.search(time_pattern, row_text)
                        
                        if time_match:
                            cells = row.find_all(['td', 'th'])
                            
                            swimmer_data = {
                                'name': '',
                                'time': time_match.group(0),
                                'event': event_name,
                                'year': '',
                                'additional_info': row_text
                            }
                            
                            # Extract name from first cell
                            if cells and len(cells) > 0:
                                swimmer_data['name'] = cells[0].get_text(strip=True)
                                
                                # Look for year in other cells
                                for cell in cells[1:]:
                                    cell_text = cell.get_text(strip=True)
                                    if re.match(r'^\d{4}$', cell_text) or cell_text in ['FR', 'SO', 'JR', 'SR']:
                                        swimmer_data['year'] = cell_text
                                        break
                            
                            # Only add if we have a valid name and it's not a header
                            if (swimmer_data['name'] and 
                                swimmer_data['name'].lower() not in ['name', 'athlete', 'swimmer', 'time'] and
                                len(swimmer_data['name']) > 1):
                                swimmers_data.append(swimmer_data)
                                print(f"[DEBUG] Extracted: {swimmer_data['name']} - {swimmer_data['time']}")
                    
                    except Exception as row_error:
                        print(f"[DEBUG] Error processing row {i}: {row_error}")
                        continue
                
                print(f"[DEBUG] Requests fallback extracted {len(swimmers_data)} records")
                
                # If we got data, return it
                if swimmers_data:
                    return swimmers_data
                
                # If no structured data found, try to extract times from the entire page
                print(f"[DEBUG] No structured data found, trying pattern matching...")
                time_pattern = r'(\d{1,2}:\d{2}\.\d{2})'
                all_times = re.findall(time_pattern, response.text)
                
                if all_times:
                    print(f"[DEBUG] Found {len(all_times)} time patterns in page")
                    # Create basic entries for found times
                    for i, time_str in enumerate(all_times[:10]):  # Limit to first 10
                        swimmers_data.append({
                            'name': f'Swimmer {i+1}',
                            'time': time_str,
                            'event': event_name,
                            'year': '',
                            'additional_info': 'Extracted via pattern matching'
                        })
                    return swimmers_data
                
                time.sleep(1)  # Brief pause between attempts
                
            except Exception as attempt_error:
                print(f"[DEBUG] Attempt {attempt + 1} failed: {attempt_error}")
                if attempt < 2:  # Don't sleep on last attempt
                    time.sleep(2)
        
        print(f"[WARNING] All requests attempts failed for: {url}")
        return []
    
    except Exception as e:
        print(f"[ERROR] Requests fallback failed: {e}")
        return []

def scrape_swimmer_times_with_fallback(url):
    """
    Main scraping function that uses requests + BeautifulSoup
    """
    return scrape_swimmer_times(url)

# For backwards compatibility
def main():
    """Test function for development"""
    test_url = "https://www.swimcloud.com/team/34/times/?dont_group=false&event_course=Y&gender=M&page=1&season_id=28&team_id=34&year=2025&region=&tag_id=&event=1%7C50%7C1"
    
    print("Testing swimmer data scraping...")
    data = scrape_swimmer_times_with_fallback(test_url)
    
    print(f"\nResults: {len(data)} swimmers found")
    for swimmer in data[:5]:  # Show first 5
        print(f"- {swimmer['name']}: {swimmer['time']} ({swimmer['event']})")

if __name__ == "__main__":
    main()