import requests
from bs4 import BeautifulSoup
import time
import re
from urllib.parse import urlparse, parse_qs, unquote

def scrape_swimmer_times(url):
    """
    Scrape swimmer times from SwimCloud using requests + BeautifulSoup.
    Optimized for faster performance with reduced retries and delays.
    """
    print(f"[DEBUG] Scraping swimmer times from: {url}")
    print(f"[DEBUG] Using requests + BeautifulSoup approach...")
    
    return scrape_with_requests_fallback(url)

def scrape_with_requests_fallback(url, max_attempts=2):  # Reduced from 3 to 2
    """
    Fallback scraping method using requests + BeautifulSoup.
    Optimized for speed with fewer retries.
    """
    print(f"[DEBUG] Attempting requests fallback for: {url}")
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Accept-Encoding': 'gzip, deflate',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
    }
    
    for attempt in range(1, max_attempts + 1):
        try:
            print(f"[DEBUG] Requests attempt {attempt}")
            
            # Make the request with shorter timeout
            response = requests.get(url, headers=headers, timeout=5)  # Reduced from 10 to 5
            response.raise_for_status()
            
            # Parse with BeautifulSoup
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Extract event name from URL for debugging
            event_name = extract_event_name_from_url(url)
            print(f"[DEBUG] Found event name: {event_name}")
            
            # Try to find swimmer data in tables
            records = extract_swimmer_data_from_soup(soup, event_name)
            
            if records:
                print(f"[DEBUG] Requests fallback extracted {len(records)} records")
                return records
            else:
                print(f"[DEBUG] No structured data found, trying pattern matching...")
                # Try pattern matching as fallback
                records = extract_with_pattern_matching(response.text, event_name)
                if records:
                    print(f"[DEBUG] Pattern matching extracted {len(records)} records")
                    return records
            
            if attempt < max_attempts:
                time.sleep(0.5)  # Reduced delay from 1 to 0.5 seconds
                
        except requests.exceptions.RequestException as e:
            print(f"[DEBUG] Request attempt {attempt} failed: {e}")
            if attempt < max_attempts:
                time.sleep(0.5)  # Reduced delay
            continue
        except Exception as e:
            print(f"[DEBUG] Unexpected error in attempt {attempt}: {e}")
            if attempt < max_attempts:
                time.sleep(0.5)  # Reduced delay
            continue
    
    print(f"[WARNING] All requests attempts failed for: {url}")
    return []

def extract_event_name_from_url(url):
    """Extract event name from SwimCloud URL for debugging purposes."""
    try:
        parsed_url = urlparse(url)
        query_params = parse_qs(parsed_url.query)
        
        print(f"[DEBUG] Original URL: {url}")
        print(f"[DEBUG] Parsed query parameters: {query_params}")
        
        if 'event' in query_params:
            event_param = query_params['event'][0]
            print(f"[DEBUG] Raw event parameter: {event_param}")
            
            # URL decode the event parameter
            decoded_event = unquote(event_param)
            print(f"[DEBUG] URL decoded event: {decoded_event}")
            
            # Parse the event code (format: stroke|distance|course)
            if '|' in decoded_event:
                parts = decoded_event.split('|')
                if len(parts) >= 2:
                    stroke_code = parts[0]
                    distance = parts[1]
                    
                    # Map stroke codes to names
                    stroke_map = {
                        '1': 'Free',
                        '2': 'Back', 
                        '3': 'Breast',
                        '4': 'Fly',
                        '5': 'IM'
                    }
                    
                    stroke_name = stroke_map.get(stroke_code, f'Stroke{stroke_code}')
                    event_name = f"{distance} {stroke_name}"
                    print(f"[DEBUG] Found event name: {event_name}")
                    return event_name
        
        return "Unknown Event"
    except Exception as e:
        print(f"[DEBUG] Error extracting event name: {e}")
        return "Unknown Event"

def extract_swimmer_data_from_soup(soup, event_name):
    """Extract swimmer data from BeautifulSoup parsed HTML."""
    records = []
    
    # Look for table rows that might contain swimmer data
    table_rows = soup.find_all('tr')
    print(f"[DEBUG] Found {len(table_rows)} table rows")
    
    for row in table_rows:
        cells = row.find_all(['td', 'th'])
        if len(cells) >= 3:  # Need at least name, time, and some other data
            # Look for swimmer name and time patterns
            row_text = ' '.join([cell.get_text(strip=True) for cell in cells])
            
            # Pattern for swimmer times (MM:SS.ss or SS.ss format)
            time_pattern = r'\b(?:(\d{1,2}):)?(\d{1,2})\.(\d{2})\b'
            time_matches = re.findall(time_pattern, row_text)
            
            if time_matches:
                # Try to extract swimmer name (usually in first few cells)
                name_candidates = [cell.get_text(strip=True) for cell in cells[:3]]
                swimmer_name = None
                
                for candidate in name_candidates:
                    # Skip cells that look like times, numbers, or common table headers
                    if (candidate and 
                        not re.match(r'^\d+$', candidate) and  # Not just a number
                        not re.search(time_pattern, candidate) and  # Not a time
                        len(candidate) > 2 and  # Reasonable length
                        not candidate.lower() in ['rank', 'time', 'name', 'swimmer']):
                        swimmer_name = candidate
                        break
                
                if swimmer_name:
                    # Use the first time found
                    time_match = time_matches[0]
                    if time_match[0]:  # Has minutes
                        time_str = f"{time_match[0]}:{time_match[1]}.{time_match[2]}"
                    else:  # Seconds only
                        time_str = f"{time_match[1]}.{time_match[2]}"
                    
                    records.append((swimmer_name, event_name, time_str))
    
    return records

def extract_with_pattern_matching(html_content, event_name):
    """Extract swimmer data using regex pattern matching as fallback."""
    records = []
    
    # More flexible pattern to find swimmer names and times
    # Look for patterns like: "Name" followed by time within reasonable distance
    name_time_pattern = r'([A-Za-z\s,\'-]+?)\s+(?:.*?\s+)?(\d{1,2}:\d{2}\.\d{2}|\d{2}\.\d{2})'
    
    matches = re.findall(name_time_pattern, html_content)
    
    for match in matches:
        name = match[0].strip()
        time_str = match[1].strip()
        
        # Filter out obvious non-names
        if (len(name) > 2 and 
            not name.isdigit() and 
            not name.lower() in ['time', 'rank', 'place', 'event', 'swimmer']):
            records.append((name, event_name, time_str))
    
    return records[:10]  # Limit to first 10 matches to avoid noise

def test_times_url(url, max_attempts=2):  # Reduced attempts
    """
    Test if a SwimCloud times URL contains swimmer data.
    Optimized for speed.
    """
    print(f"[DEBUG] Testing URL: {url}")
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }
    
    for attempt in range(1, max_attempts + 1):
        try:
            print(f"[DEBUG] Testing URL (attempt {attempt}): {url}")
            response = requests.get(url, headers=headers, timeout=3)  # Reduced timeout
            
            if response.status_code == 200:
                # Quick check for time patterns
                time_patterns = re.findall(r'\b\d{1,2}:\d{2}\.\d{2}\b|\b\d{2}\.\d{2}\b', response.text)
                print(f"[DEBUG] Found {len(time_patterns)} time patterns")
                
                # Quick check for table elements
                time_elements = response.text.count('<td')
                print(f"[DEBUG] Found {len(time_elements)} time elements")
                
                if time_patterns or time_elements > 5:
                    print(f"[DEBUG] Working URL confirmed: {url}")
                    return True
                else:
                    print(f"[DEBUG] No timing data found in response")
            
            if attempt < max_attempts:
                time.sleep(0.2)  # Very short delay
                
        except Exception as e:
            print(f"[DEBUG] URL test attempt {attempt} failed: {e}")
            if attempt < max_attempts:
                time.sleep(0.2)
    
    print(f"[WARNING] URL may not contain expected data: {url}")
    return False  # Changed to False to skip problematic URLs faster