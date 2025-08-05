import re
import os
import shutil
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import urllib.parse
from contextlib import contextmanager

# Updated Map SwimCloud event codes to event names
EVENT_CODE_TO_NAME = {
    "1|50|1": "50 Free",
    "1|100|1": "100 Free",
    "1|200|1": "200 Free",
    "1|500|1": "500 Free",
    "1|1000|1": "1000 Free",
    "1|1500|1": "1650 Free",
    "2|50|1": "50 Back",
    "2|100|1": "100 Back",
    "2|200|1": "200 Back",
    "3|50|1": "50 Breast",
    "3|100|1": "100 Breast",
    "3|200|1": "200 Breast",
    "4|50|1": "50 Fly",
    "4|100|1": "100 Fly",
    "4|200|1": "200 Fly",
    "5|200|1": "200 IM",
    "5|400|1": "400 IM"
}

# Global driver instance for reuse
_driver_instance = None

def get_optimized_chrome_options():
    """Get optimized Chrome options for faster scraping"""
    chrome_options = Options()
    
    # Performance optimizations
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--disable-features=VizDisplayCompositor")
    chrome_options.add_argument("--window-size=1280,720")  # Smaller window
    chrome_options.add_argument("--remote-debugging-port=9222")
    
    # Speed optimizations
    chrome_options.add_argument("--disable-extensions")
    chrome_options.add_argument("--disable-plugins")
    chrome_options.add_argument("--disable-images")
    chrome_options.add_argument("--disable-javascript")  # Most scraping doesn't need JS
    chrome_options.add_argument("--disable-css")  # Don't load CSS
    chrome_options.add_argument("--disable-web-security")
    chrome_options.add_argument("--disable-features=TranslateUI")
    chrome_options.add_argument("--disable-iframes")
    chrome_options.add_argument("--disable-popup-blocking")
    chrome_options.add_argument("--disable-background-timer-throttling")
    chrome_options.add_argument("--disable-renderer-backgrounding")
    chrome_options.add_argument("--disable-backgrounding-occluded-windows")
    
    # Memory optimizations
    chrome_options.add_argument("--memory-pressure-off")
    chrome_options.add_argument("--max_old_space_size=4096")
    
    # Network optimizations
    chrome_options.add_argument("--aggressive-cache-discard")
    chrome_options.add_argument("--disable-background-networking")
    
    # Set user agent
    chrome_options.add_argument("--user-agent=Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    
    return chrome_options

def get_chrome_driver():
    """Initialize Chrome WebDriver with optimized settings"""
    global _driver_instance
    
    # Reuse existing driver if available
    if _driver_instance:
        try:
            # Test if driver is still alive
            _driver_instance.current_url
            return _driver_instance
        except:
            _driver_instance = None
    
    chrome_options = get_optimized_chrome_options()
    
    # Try to find Chrome binary
    chrome_binary = os.environ.get('GOOGLE_CHROME_BIN') or '/usr/bin/google-chrome-stable'
    if os.path.isfile(chrome_binary):
        chrome_options.binary_location = chrome_binary
        print(f"[DEBUG] Using Chrome binary: {chrome_binary}")
    else:
        print("[DEBUG] Chrome binary not found, using default")
    
    try:
        # Try environment variable path first
        chromedriver_path = os.environ.get('CHROMEDRIVER_PATH') or '/usr/bin/chromedriver'
        
        if os.path.isfile(chromedriver_path):
            service = Service(chromedriver_path)
            _driver_instance = webdriver.Chrome(service=service, options=chrome_options)
            print(f"[DEBUG] Chrome driver initialized with: {chromedriver_path}")
        else:
            # Fallback to default
            _driver_instance = webdriver.Chrome(options=chrome_options)
            print("[DEBUG] Chrome driver initialized with default")
        
        # Set timeouts
        _driver_instance.set_page_load_timeout(30)
        _driver_instance.implicitly_wait(5)
        
        return _driver_instance
        
    except Exception as e:
        print(f"[DEBUG] Chrome driver initialization failed: {e}")
        raise

@contextmanager
def managed_driver():
    """Context manager for driver lifecycle"""
    driver = None
    try:
        driver = get_chrome_driver()
        yield driver
    finally:
        # Don't quit the driver, reuse it
        pass

def cleanup_driver():
    """Cleanup the global driver instance"""
    global _driver_instance
    if _driver_instance:
        try:
            _driver_instance.quit()
            print("[DEBUG] Driver cleanup successful")
        except:
            print("[DEBUG] Driver cleanup failed")
        finally:
            _driver_instance = None

def debug_url_and_event_extraction(url):
    """Debug function to extract event information from URL"""
    print(f"[DEBUG] Original URL: {url}")
    
    from urllib.parse import urlparse, parse_qs
    parsed_url = urlparse(url)
    query_params = parse_qs(parsed_url.query)
    
    print(f"[DEBUG] Parsed query parameters: {query_params}")
    
    if 'event' in query_params:
        raw_event = query_params['event'][0]
        print(f"[DEBUG] Raw event parameter: {raw_event}")
        
        decoded_event = urllib.parse.unquote(raw_event)
        print(f"[DEBUG] URL decoded event: {decoded_event}")
        
        if decoded_event in EVENT_CODE_TO_NAME:
            event_name = EVENT_CODE_TO_NAME[decoded_event]
            print(f"[DEBUG] Found event name: {event_name}")
        else:
            print(f"[DEBUG] Event code '{decoded_event}' not found in mapping!")
            event_name = f"Unknown ({decoded_event})"
        
        return decoded_event, event_name
    
    # Fallback to regex method
    m = re.search(r"event=([^&]+)", url)
    if m:
        raw_code = m.group(1).replace("%7C", "|")
        print(f"[DEBUG] Regex extracted event code: {raw_code}")
        event_name = EVENT_CODE_TO_NAME.get(raw_code, f"Unknown ({raw_code})")
        return raw_code, event_name
    
    return None, "Unknown Event"

def scrape_swimmer_times(url, timeout=20):
    """
    Optimized scrape swimmer times function with better performance
    """
    print(f"[DEBUG] Scraping swimmer times from: {url}")
    
    # Debug the URL and event extraction first
    event_code, event_name = debug_url_and_event_extraction(url)
    
    with managed_driver() as driver:
        try:
            # Navigate with timeout
            print("[DEBUG] Waiting for page to load...")
            driver.get(url)
            
            # Wait for specific elements instead of arbitrary sleep
            try:
                # Wait for either table or "no times" message
                WebDriverWait(driver, timeout).until(
                    lambda d: d.find_element(By.TAG_NAME, "table") or 
                             "no times" in d.page_source.lower()
                )
            except:
                print("[DEBUG] Timeout waiting for page elements")
            
            current_url = driver.current_url
            print(f"[DEBUG] Current URL after load: {current_url}")
            
            page_html = driver.page_source
            
            # Save debug file (optional, comment out in production)
            # with open("debug_swimcloud_page.html", "w", encoding="utf-8") as f:
            #     f.write(page_html)
            # print("[DEBUG] Saved page content to debug_swimcloud_page.html")
            
            # Parse with BeautifulSoup
            soup = BeautifulSoup(page_html, "html.parser")
            
            print("[DEBUG] Looking for key page elements...")
            
            # Check for "No times" message
            no_times_elements = soup.find_all(text=re.compile(r"No times|no times", re.I))
            if no_times_elements:
                print(f"[DEBUG] Found 'No times' message")
                return []
            
            # Quick checks
            tables = soup.find_all("table")
            print(f"[DEBUG] Found {len(tables)} tables on page")
            
            swimmer_links = soup.find_all("a", href=re.compile(r"/swimmer/\d+"))
            print(f"[DEBUG] Found {len(swimmer_links)} swimmer links")
            
            print(f"[DEBUG] Event name from URL: {event_name}")
            
            # Try extraction methods in order of efficiency
            times_data = extract_swimcloud_times_table(soup, default_event=event_name)
            if times_data:
                print(f"[DEBUG] Found {len(times_data)} time records from SwimCloud table")
                return times_data
            
            times_data = extract_times_from_any_table(soup, default_event=event_name)
            if times_data:
                print(f"[DEBUG] Found {len(times_data)} time records from general tables")
                return times_data
            
            print("[DEBUG] No time data found → returning empty list")
            return []
            
        except Exception as e:
            print(f"[DEBUG] Exception inside scrape_swimmer_times: {e}")
            import traceback
            traceback.print_exc()
            return []

def extract_swimcloud_times_table(soup, default_event="Unknown Event"):
    """Extract times from SwimCloud's table structure - optimized version"""
    data = []
    
    tables = soup.find_all("table")
    
    for table in tables:
        print(f"[DEBUG] Analyzing table...")
        
        rows = table.find_all("tr")
        if len(rows) < 2:
            continue
        
        # Get headers
        header_row = rows[0]
        headers = [th.get_text(strip=True).lower() for th in header_row.find_all(["th", "td"])]
        print(f"[DEBUG] Table headers: {headers}")
        
        # Quick check for time table
        header_text = ' '.join(headers).lower()
        if not ('name' in header_text and 'time' in header_text):
            continue
        
        # Process data rows efficiently
        for i, row in enumerate(rows[1:], 1):
            cols = row.find_all(["td", "th"])
            
            if len(cols) < 4:
                continue
            
            swimmer_name = None
            time_value = None
            
            # Look for swimmer name and time in columns
            for col in cols:
                col_text = col.get_text(strip=True)
                
                # Check for swimmer name (has link to /swimmer/)
                if not swimmer_name:
                    swimmer_link = col.find('a', href=re.compile(r'/swimmer/\d+'))
                    if swimmer_link:
                        swimmer_name = swimmer_link.get_text(strip=True)
                        print(f"[DEBUG] Found swimmer name: {swimmer_name}")
                        continue
                
                # Check for time
                if not time_value and re.search(r'\d+:\d{2}\.\d{2}|\d+\.\d{2}', col_text):
                    time_link = col.find('a')
                    time_value = time_link.get_text(strip=True) if time_link else col_text
                    time_value = re.sub(r'[^\d:.]', '', time_value)
                    print(f"[DEBUG] Found time: {time_value}")
                    continue
            
            # Validate and add record
            if (swimmer_name and time_value and 
                len(swimmer_name) >= 3 and not swimmer_name.isdigit() and
                re.match(r'(\d+:\d{2}\.\d+|\d+\.\d+|\d+:\d{2}:\d{2}\.\d+)', time_value)):
                
                data.append((swimmer_name, default_event, time_value))
                print(f"[DEBUG] Added record: {swimmer_name}, {default_event}, {time_value}")
    
    return data

def extract_times_from_any_table(soup, default_event="Unknown Event"):
    """Fallback method for extracting times from any table"""
    data = []
    tables = soup.find_all("table")
    
    for table in tables:
        table_text = table.get_text().lower()
        
        # Quick relevance check
        if not any(word in table_text for word in ['time', 'swimmer', 'free', 'back', 'breast', 'fly']):
            continue
        
        rows = table.find_all("tr")
        if len(rows) < 2:
            continue
        
        header_row = rows[0]
        headers = [th.get_text(strip=True) for th in header_row.find_all(["th", "td"])]
        
        name_col = find_column_index(headers, ['swimmer', 'name', 'athlete'])
        time_col = find_column_index(headers, ['time', 'result', 'best', 'season'])
        
        if name_col is not None and time_col is not None:
            for row in rows[1:]:
                cols = row.find_all(["td", "th"])
                if len(cols) > max(name_col, time_col):
                    try:
                        raw_name = cols[name_col].get_text(strip=True)
                        raw_time = cols[time_col].get_text(strip=True)
                        time_value = re.sub(r'[^\d:.]', '', raw_time)
                        
                        if (raw_name and not raw_name.isdigit() and len(raw_name) >= 3 and
                            time_value and re.match(r'\d+:\d+\.?\d*|\d+\.\d+', time_value)):
                            
                            data.append((raw_name, default_event, time_value))
                            print(f"[DEBUG] Added record: {raw_name}, {default_event}, {time_value}")
                            
                    except (IndexError, AttributeError):
                        continue
    
    return data

def find_column_index(headers, search_terms):
    """Find column index based on search terms"""
    for i, header in enumerate(headers):
        header_lower = header.lower()
        if any(term in header_lower for term in search_terms):
            return i
    return None

def batch_scrape_times(urls, batch_size=5):
    """Scrape multiple URLs in batches to manage memory"""
    all_results = []
    
    for i in range(0, len(urls), batch_size):
        batch = urls[i:i + batch_size]
        print(f"[DEBUG] Processing batch {i//batch_size + 1}: {len(batch)} URLs")
        
        for url in batch:
            try:
                result = scrape_swimmer_times(url, timeout=15)  # Shorter timeout
                all_results.extend(result)
            except Exception as e:
                print(f"[DEBUG] Failed to scrape {url}: {e}")
                continue
        
        # Clean up every few batches
        if (i // batch_size + 1) % 3 == 0:
            cleanup_driver()
            time.sleep(1)  # Brief pause
    
    return all_results

# Test function
if __name__ == "__main__":
    test_url = "https://www.swimcloud.com/team/34/times/?dont_group=false&event_course=Y&gender=M&page=1&season_id=28&team_id=34&year=2025&region=&tag_id=&event=1%7C50%7C1"
    try:
        results = scrape_swimmer_times(test_url)
        print(f"Found {len(results)} results")
        for result in results[:5]:  # Show first 5
            print(result)
    finally:
        cleanup_driver()