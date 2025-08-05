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
import threading
import queue
import concurrent.futures
from functools import lru_cache

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

# Thread-local storage for drivers
_thread_local = threading.local()

def get_ultra_fast_chrome_options():
    """Ultra-optimized Chrome options for maximum speed"""
    chrome_options = Options()
    
    # Core settings for speed
    chrome_options.add_argument("--headless=new")  # Use new headless mode
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--disable-software-rasterizer")
    chrome_options.add_argument("--disable-background-timer-throttling")
    chrome_options.add_argument("--disable-backgrounding-occluded-windows")
    chrome_options.add_argument("--disable-renderer-backgrounding")
    chrome_options.add_argument("--disable-features=TranslateUI,BlinkGenPropertyTrees")
    chrome_options.add_argument("--disable-ipc-flooding-protection")
    
    # Minimal window
    chrome_options.add_argument("--window-size=800,600")
    chrome_options.add_argument("--virtual-time-budget=1000")
    
    # Disable everything we don't need
    chrome_options.add_argument("--disable-extensions")
    chrome_options.add_argument("--disable-plugins")
    chrome_options.add_argument("--disable-images")
    chrome_options.add_argument("--disable-javascript")
    chrome_options.add_argument("--disable-web-security")
    chrome_options.add_argument("--disable-features=VizDisplayCompositor")
    chrome_options.add_argument("--disable-background-networking")
    chrome_options.add_argument("--disable-sync")
    chrome_options.add_argument("--disable-default-apps")
    chrome_options.add_argument("--disable-client-side-phishing-detection")
    chrome_options.add_argument("--disable-hang-monitor")
    chrome_options.add_argument("--disable-popup-blocking")
    chrome_options.add_argument("--disable-prompt-on-repost")
    chrome_options.add_argument("--disable-domain-reliability")
    chrome_options.add_argument("--disable-component-update")
    
    # Memory optimizations
    chrome_options.add_argument("--memory-pressure-off")
    chrome_options.add_argument("--max_old_space_size=512")  # Reduced memory
    chrome_options.add_argument("--aggressive-cache-discard")
    
    # Network optimizations
    chrome_options.add_argument("--disable-background-networking")
    chrome_options.add_argument("--disable-component-extensions-with-background-pages")
    
    # Logging
    chrome_options.add_argument("--log-level=3")  # Only fatal errors
    chrome_options.add_argument("--silent")
    
    return chrome_options

def get_thread_driver():
    """Get thread-local Chrome driver"""
    if not hasattr(_thread_local, 'driver') or _thread_local.driver is None:
        chrome_options = get_ultra_fast_chrome_options()
        
        chrome_binary = os.environ.get('GOOGLE_CHROME_BIN') or '/usr/bin/google-chrome-stable'
        if os.path.isfile(chrome_binary):
            chrome_options.binary_location = chrome_binary
        
        try:
            chromedriver_path = os.environ.get('CHROMEDRIVER_PATH') or '/usr/bin/chromedriver'
            
            if os.path.isfile(chromedriver_path):
                service = Service(chromedriver_path)
                _thread_local.driver = webdriver.Chrome(service=service, options=chrome_options)
            else:
                _thread_local.driver = webdriver.Chrome(options=chrome_options)
            
            # Aggressive timeouts
            _thread_local.driver.set_page_load_timeout(10)  # Reduced from 30
            _thread_local.driver.implicitly_wait(2)  # Reduced from 5
            
        except Exception as e:
            print(f"[ERROR] Failed to create driver: {e}")
            raise
    
    return _thread_local.driver

def cleanup_thread_driver():
    """Cleanup thread-local driver"""
    if hasattr(_thread_local, 'driver') and _thread_local.driver:
        try:
            _thread_local.driver.quit()
        except:
            pass
        finally:
            _thread_local.driver = None

@lru_cache(maxsize=100)
def cached_event_extraction(url):
    """Cache event extraction results"""
    return debug_url_and_event_extraction(url)

def debug_url_and_event_extraction(url):
    """Debug function to extract event information from URL"""
    from urllib.parse import urlparse, parse_qs
    parsed_url = urlparse(url)
    query_params = parse_qs(parsed_url.query)
    
    if 'event' in query_params:
        raw_event = query_params['event'][0]
        decoded_event = urllib.parse.unquote(raw_event)
        
        if decoded_event in EVENT_CODE_TO_NAME:
            event_name = EVENT_CODE_TO_NAME[decoded_event]
            return decoded_event, event_name
    
    # Fallback to regex method
    m = re.search(r"event=([^&]+)", url)
    if m:
        raw_code = m.group(1).replace("%7C", "|")
        event_name = EVENT_CODE_TO_NAME.get(raw_code, f"Unknown ({raw_code})")
        return raw_code, event_name
    
    return None, "Unknown Event"

def fast_scrape_swimmer_times(url, timeout=8):
    """
    Ultra-fast scraping function with minimal waits
    """
    event_code, event_name = cached_event_extraction(url)
    
    driver = get_thread_driver()
    
    try:
        # Immediate navigation with short timeout
        driver.get(url)
        
        # Minimal wait - just check if basic content loaded
        try:
            WebDriverWait(driver, timeout).until(
                lambda d: d.find_element(By.TAG_NAME, "body")
            )
        except:
            print(f"[WARNING] Timeout on {url}")
            return []
        
        # Quick parse without saving debug files
        soup = BeautifulSoup(driver.page_source, "html.parser")
        
        # Fast extraction
        times_data = extract_swimcloud_times_table_fast(soup, default_event=event_name)
        
        return times_data
        
    except Exception as e:
        print(f"[ERROR] Failed to scrape {url}: {e}")
        return []

def extract_swimcloud_times_table_fast(soup, default_event="Unknown Event"):
    """Ultra-fast table extraction with minimal processing"""
    data = []
    
    # Find first table with swimmer links
    for table in soup.find_all("table", limit=3):  # Limit search to first 3 tables
        swimmer_links = table.find_all("a", href=re.compile(r"/swimmer/\d+"), limit=20)
        
        if not swimmer_links:
            continue
        
        # Quick row processing
        rows = table.find_all("tr")[1:]  # Skip header
        
        for row in rows[:25]:  # Limit to first 25 swimmers
            cols = row.find_all(["td", "th"])
            
            if len(cols) < 3:
                continue
            
            swimmer_name = None
            time_value = None
            
            # Fast column scanning
            for col in cols[:6]:  # Only check first 6 columns
                col_text = col.get_text(strip=True)
                
                # Swimmer name check
                if not swimmer_name:
                    swimmer_link = col.find('a', href=re.compile(r'/swimmer/\d+'))
                    if swimmer_link:
                        swimmer_name = swimmer_link.get_text(strip=True)[:50]  # Limit length
                        continue
                
                # Time check with simple regex
                if not time_value and re.search(r'\d+[:.]\d+', col_text):
                    time_value = re.search(r'(\d+[:.]\d{2}(?:\.\d+)?)', col_text)
                    if time_value:
                        time_value = time_value.group(1)
                        break
            
            # Quick validation and add
            if (swimmer_name and time_value and 
                len(swimmer_name) >= 3 and not swimmer_name.isdigit()):
                
                data.append((swimmer_name, default_event, time_value))
                
                if len(data) >= 20:  # Limit results per event
                    break
        
        if data:  # Return first successful table
            break
    
    return data

def parallel_scrape_urls(urls, max_workers=3):
    """
    Scrape URLs in parallel with controlled concurrency
    """
    all_results = []
    
    # Use smaller thread pool to avoid overwhelming the system
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Submit all tasks
        future_to_url = {
            executor.submit(fast_scrape_swimmer_times, url, 6): url 
            for url in urls
        }
        
        # Process completed tasks
        for future in concurrent.futures.as_completed(future_to_url, timeout=60):
            url = future_to_url[future]
            try:
                result = future.result(timeout=10)
                all_results.extend(result)
                print(f"[DEBUG] ✓ Completed {url}: {len(result)} records")
            except Exception as e:
                print(f"[ERROR] Failed {url}: {e}")
                continue
    
    return all_results

def batch_scrape_times_optimized(urls, batch_size=6):
    """
    Optimized batch processing with better memory management
    """
    all_results = []
    total_batches = (len(urls) + batch_size - 1) // batch_size
    
    for i in range(0, len(urls), batch_size):
        batch = urls[i:i + batch_size]
        batch_num = i // batch_size + 1
        
        print(f"[DEBUG] Processing batch {batch_num}/{total_batches}: {len(batch)} URLs")
        
        try:
            # Process batch in parallel
            batch_results = parallel_scrape_urls(batch, max_workers=2)
            all_results.extend(batch_results)
            
            print(f"[DEBUG] Batch {batch_num} completed: {len(batch_results)} total records")
            
        except Exception as e:
            print(f"[ERROR] Batch {batch_num} failed: {e}")
            # Try sequential fallback for this batch
            for url in batch:
                try:
                    result = fast_scrape_swimmer_times(url, timeout=5)
                    all_results.extend(result)
                except:
                    continue
        
        # Cleanup after each batch
        cleanup_all_drivers()
        
        # Brief pause between batches
        time.sleep(0.5)
    
    return all_results

def cleanup_all_drivers():
    """Cleanup all thread-local drivers"""
    try:
        cleanup_thread_driver()
    except:
        pass

# Quick test for specific events only
def quick_scrape_essential_events(base_url, team_id, essential_events=None):
    """
    Scrape only essential events for faster processing
    """
    if essential_events is None:
        # Focus on most common events
        essential_events = [
            "1|50|1",   # 50 Free
            "1|100|1",  # 100 Free
            "1|200|1",  # 200 Free
            "2|100|1",  # 100 Back
            "3|100|1",  # 100 Breast
            "4|100|1",  # 100 Fly
        ]
    
    urls = []
    for event_code in essential_events:
        url = f"{base_url}&event={urllib.parse.quote(event_code)}"
        urls.append(url)
    
    return batch_scrape_times_optimized(urls, batch_size=3)

# Test function
if __name__ == "__main__":
    test_urls = [
        "https://www.swimcloud.com/team/34/times/?dont_group=false&event_course=Y&gender=M&page=1&season_id=28&team_id=34&year=2025&region=&tag_id=&event=1%7C50%7C1",
        "https://www.swimcloud.com/team/34/times/?dont_group=false&event_course=Y&gender=M&page=1&season_id=28&team_id=34&year=2025&region=&tag_id=&event=1%7C100%7C1"
    ]
    
    try:
        start_time = time.time()
        results = batch_scrape_times_optimized(test_urls)
        end_time = time.time()
        
        print(f"\n[RESULTS] Found {len(results)} total results in {end_time - start_time:.2f} seconds")
        for result in results[:10]:  # Show first 10
            print(result)
    finally:
        cleanup_all_drivers()