import requests
from bs4 import BeautifulSoup
import time
import re
from urllib.parse import urlparse, parse_qs, unquote
import concurrent.futures
from functools import partial

def scrape_swimmer_times(url):
    """
    Scrape swimmer times from SwimCloud using requests + BeautifulSoup.
    Heavily optimized for performance.
    """
    print(f"[DEBUG] Scraping swimmer times from: {url}")
    
    return scrape_with_requests_fallback(url)

def scrape_with_requests_fallback(url, max_attempts=1):  # Reduced to single attempt
    """
    Fallback scraping method using requests + BeautifulSoup.
    Maximum optimization for speed.
    """
    print(f"[DEBUG] Attempting requests for: {url}")
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Encoding': 'gzip, deflate',
        'Connection': 'keep-alive',
        'Cache-Control': 'no-cache'
    }
    
    try:
        # Single attempt with very short timeout
        response = requests.get(url, headers=headers, timeout=3)
        response.raise_for_status()
        
        # Fast extraction without BeautifulSoup for initial check
        if not quick_data_check(response.text):
            print(f"[DEBUG] No data indicators found, skipping...")
            return []
        
        # Use BeautifulSoup only if quick check passes
        soup = BeautifulSoup(response.content, 'html.parser')
        event_name = extract_event_name_from_url(url)
        
        # Try structured extraction first (faster)
        records = extract_swimmer_data_optimized(soup, event_name)
        
        if records:
            print(f"[DEBUG] Extracted {len(records)} records")
            return records[:15]  # Limit results to prevent timeout
        else:
            # Quick pattern matching as last resort
            records = extract_with_pattern_matching_optimized(response.text, event_name)
            return records[:15]  # Limit results
            
    except requests.exceptions.Timeout:
        print(f"[DEBUG] Request timeout for: {url}")
        return []
    except requests.exceptions.RequestException as e:
        print(f"[DEBUG] Request failed: {e}")
        return []
    except Exception as e:
        print(f"[DEBUG] Unexpected error: {e}")
        return []

def quick_data_check(html_content):
    """Ultra-fast check for swimmer data presence."""
    # Look for key indicators without full parsing
    indicators = [
        r'\b\d{1,2}:\d{2}\.\d{2}\b',  # Time patterns MM:SS.ss
        r'\b\d{2}\.\d{2}\b',          # Time patterns SS.ss
        '<td',                        # Table cells
        'swimmer',                    # Swimmer references
        'time'                        # Time references
    ]
    
    content_lower = html_content.lower()
    for pattern in indicators:
        if pattern.startswith('<') or pattern == 'swimmer' or pattern == 'time':
            if pattern in content_lower:
                return True
        else:
            if re.search(pattern, html_content):
                return True
    return False

def extract_event_name_from_url(url):
    """Optimized event name extraction."""
    try:
        parsed_url = urlparse(url)
        query_params = parse_qs(parsed_url.query)
        
        if 'event' in query_params:
            event_param = unquote(query_params['event'][0])
            
            if '|' in event_param:
                parts = event_param.split('|')
                if len(parts) >= 2:
                    stroke_code = parts[0]
                    distance = parts[1]
                    
                    stroke_map = {
                        '1': 'Free', '2': 'Back', '3': 'Breast', 
                        '4': 'Fly', '5': 'IM'
                    }
                    
                    stroke_name = stroke_map.get(stroke_code, f'Stroke{stroke_code}')
                    return f"{distance} {stroke_name}"
        
        return "Unknown Event"
    except:
        return "Unknown Event"

def extract_swimmer_data_optimized(soup, event_name):
    """Optimized swimmer data extraction with early exits."""
    records = []
    
    # Find tables more efficiently
    tables = soup.find_all('table', limit=3)  # Limit table search
    
    for table in tables:
        rows = table.find_all('tr', limit=20)  # Limit rows processed
        
        for row in rows:
            cells = row.find_all(['td', 'th'])
            if len(cells) < 3:
                continue
                
            # Quick text extraction
            cell_texts = [cell.get_text(strip=True) for cell in cells[:5]]  # Only first 5 cells
            row_text = ' '.join(cell_texts)
            
            # Quick time pattern check
            time_match = re.search(r'\b(?:(\d{1,2}):)?(\d{1,2})\.(\d{2})\b', row_text)
            if not time_match:
                continue
            
            # Find swimmer name (first non-numeric, non-time cell)
            swimmer_name = None
            for text in cell_texts:
                if (text and len(text) > 2 and 
                    not text.isdigit() and 
                    not re.search(r'\b\d{1,2}:\d{2}\.\d{2}\b|\b\d{2}\.\d{2}\b', text) and
                    text.lower() not in ['rank', 'time', 'name', 'swimmer']):
                    swimmer_name = text
                    break
            
            if swimmer_name:
                time_str = time_match.group(0)
                records.append((swimmer_name, event_name, time_str))
                
                # Early exit if we have enough data
                if len(records) >= 15:
                    return records
    
    return records

def extract_with_pattern_matching_optimized(html_content, event_name):
    """Ultra-fast pattern matching with limits."""
    records = []
    
    # More targeted pattern
    pattern = r'([A-Za-z][A-Za-z\s,\'-]{2,25}?)\s+(?:[^<>]*?\s+)?(\d{1,2}:\d{2}\.\d{2}|\d{2}\.\d{2})'
    
    # Process only first part of content to avoid timeouts
    content_sample = html_content[:50000]  # First 50KB only
    matches = re.findall(pattern, content_sample)
    
    seen_names = set()
    for match in matches:
        name = match[0].strip()
        time_str = match[1].strip()
        
        # Quick filtering
        if (len(name) > 2 and 
            name not in seen_names and
            not name.lower() in ['time', 'rank', 'place'] and
            not name.isdigit()):
            
            records.append((name, event_name, time_str))
            seen_names.add(name)
            
            # Early exit
            if len(records) >= 10:
                break
    
    return records

def test_times_url(url, max_attempts=1):
    """
    Ultra-fast URL testing with immediate return.
    """
    print(f"[DEBUG] Testing URL: {url}")
    
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
    
    try:
        response = requests.get(url, headers=headers, timeout=2)
        
        if response.status_code == 200:
            # Very quick content check
            has_times = bool(re.search(r'\b\d{1,2}:\d{2}\.\d{2}\b|\b\d{2}\.\d{2}\b', response.text[:5000]))
            has_tables = '<td' in response.text[:5000]
            
            if has_times or has_tables:
                print(f"[DEBUG] URL confirmed working: {url}")
                return True
        
        print(f"[DEBUG] URL test failed - no data indicators")
        return False
        
    except:
        print(f"[DEBUG] URL test failed - connection error")
        return False

# Additional optimization: Batch processing function
def scrape_multiple_events_parallel(team_id, year, gender, event_codes, max_workers=3):
    """
    Scrape multiple events in parallel with controlled concurrency.
    """
    from .url_builder import build_swimcloud_times_url
    
    def scrape_single_event(event_info):
        event_name, event_code = event_info
        url = build_swimcloud_times_url(team_id, year, gender, event=event_code)
        
        if not test_times_url(url):
            return []
        
        return scrape_swimmer_times(url)
    
    all_results = []
    
    # Process in small batches to avoid overwhelming the server
    batch_size = 3
    for i in range(0, len(event_codes), batch_size):
        batch = event_codes[i:i + batch_size]
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = [executor.submit(scrape_single_event, event_info) for event_info in batch]
            
            for future in concurrent.futures.as_completed(futures, timeout=15):  # 15 sec timeout per batch
                try:
                    result = future.result()
                    if result:
                        all_results.extend(result)
                except Exception as e:
                    print(f"[DEBUG] Batch scraping error: {e}")
                    continue
        
        # Brief pause between batches
        if i + batch_size < len(event_codes):
            time.sleep(1)
    
    return all_results