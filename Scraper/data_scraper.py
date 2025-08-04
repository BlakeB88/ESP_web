import os
import time
import json
import re
from urllib.parse import urlparse, parse_qs, unquote
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException, NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager
import requests
from bs4 import BeautifulSoup

def setup_chrome_driver():
    """Setup Chrome WebDriver with proper configuration for Render deployment"""
  
    options = Options()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-gpu')
    options.add_argument('--window-size=1920,1080')
    options.add_argument('--disable-extensions')
    options.add_argument('--disable-plugins')
    options.add_argument('--disable-images')
    options.add_argument('--remote-debugging-port=9222')
    options.add_argument('--disable-web-security')
    options.add_argument('--disable-features=VizDisplayCompositor')
    options.add_argument('--disable-background-timer-throttling')
    options.add_argument('--disable-backgrounding-occluded-windows')
    options.add_argument('--disable-renderer-backgrounding')
    options.add_argument('--disable-features=TranslateUI')
    options.add_argument('--disable-ipc-flooding-protection')
    options.add_argument('--disable-blink-features=AutomationControlled')
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)
  
    # Chrome binary detection with better error handling
    chrome_paths = [
        os.environ.get('CHROME_BIN'),
        os.environ.get('GOOGLE_CHROME_BIN'),
        '/usr/bin/google-chrome-stable',
        '/usr/bin/google-chrome',
        '/usr/bin/chromium-browser',
        '/usr/bin/chromium',
        '/opt/google/chrome/google-chrome',
        '/usr/local/bin/google-chrome',
    ]
  
    chrome_binary = None
    print("[DEBUG] Searching for Chrome binary...")
  
    for path in chrome_paths:
        if path and os.path.exists(path) and os.access(path, os.X_OK):
            chrome_binary = path
            print(f"[DEBUG] Found executable Chrome binary: {chrome_binary}")
            break
        elif path:
            print(f"[DEBUG] Chrome path not found or not executable: {path}")
  
    # Try 'which' command as fallback
    if not chrome_binary:
        try:
            import subprocess
            for cmd in ['google-chrome-stable', 'google-chrome', 'chromium-browser']:
                result = subprocess.run(['which', cmd], capture_output=True, text=True, timeout=5)
                if result.returncode == 0 and result.stdout.strip():
                    chrome_binary = result.stdout.strip()
                    print(f"[DEBUG] Found Chrome via 'which {cmd}': {chrome_binary}")
                    break
        except Exception as e:
            print(f"[DEBUG] 'which' command failed: {e}")
  
    if chrome_binary:
        options.binary_location = chrome_binary
        print(f"[DEBUG] Using Chrome binary: {chrome_binary}")
    else:
        print("[ERROR] Chrome binary not found!")
        # List available binaries for debugging
        debug_paths = ['/usr/bin', '/usr/local/bin', '/opt/google/chrome']
        for location in debug_paths:
            if os.path.exists(location):
                try:
                    files = [f for f in os.listdir(location) if 'chrome' in f.lower() or 'chromium' in f.lower()]
                    if files:
                        print(f"[DEBUG] Chrome-related files in {location}: {files}")
                except Exception as e:
                    print(f"[DEBUG] Error listing {location}: {e}")
      
        raise Exception("Chrome binary not found. Please ensure Chrome is installed.")
  
    # Environment debug information
    print(f"[DEBUG] Environment Debug Information:")
    print(f"[DEBUG] OS: {os.name}")
    print(f"[DEBUG] CHROME_BIN env: {os.environ.get('CHROME_BIN', 'Not set')}")
    print(f"[DEBUG] GOOGLE_CHROME_BIN env: {os.environ.get('GOOGLE_CHROME_BIN', 'Not set')}")
  
    # Try to create WebDriver
    driver = None
  
    # Approach 1: Use ChromeDriverManager
    try:
        print("[DEBUG] Attempting to create WebDriver with ChromeDriverManager...")
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)
        print("[DEBUG] Successfully created Chrome WebDriver with ChromeDriverManager")
        return driver
    except Exception as e:
        print(f"[DEBUG] ChromeDriverManager failed: {e}")
  
    # Approach 2: Try without explicit service
    try:
        print("[DEBUG] Attempting to create WebDriver without explicit service...")
        driver = webdriver.Chrome(options=options)
        print("[DEBUG] Successfully created Chrome WebDriver without explicit service")
        return driver
    except Exception as e:
        print(f"[DEBUG] Chrome WebDriver creation without service failed: {e}")
  
    # Approach 3: Try with system ChromeDriver
    chromedriver_paths = [
        os.environ.get('CHROMEDRIVER_PATH'),
        '/usr/bin/chromedriver',
        '/usr/local/bin/chromedriver',
    ]
  
    for chromedriver_path in chromedriver_paths:
        if chromedriver_path and os.path.exists(chromedriver_path):
            try:
                print(f"[DEBUG] Attempting to use ChromeDriver at: {chromedriver_path}")
                service = Service(chromedriver_path)
                driver = webdriver.Chrome(service=service, options=options)
                print(f"[DEBUG] Successfully created Chrome WebDriver with {chromedriver_path}")
                return driver
            except Exception as e:
                print(f"[DEBUG] Failed with ChromeDriver at {chromedriver_path}: {e}")
  
    # If all approaches fail
    raise Exception(
        f"Cannot create Chrome WebDriver. Chrome binary: {chrome_binary}. "
        f"Please ensure Chrome and ChromeDriver are properly installed. "
        f"Environment: CHROME_BIN={os.environ.get('CHROME_BIN')}, "
        f"GOOGLE_CHROME_BIN={os.environ.get('GOOGLE_CHROME_BIN')}"
    )

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
    Scrape swimmer times from SwimCloud URL
    Returns a list of dictionaries containing swimmer data
    """
    driver = None
    
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
        
        # Setup WebDriver
        print(f"[DEBUG] Setting up Chrome WebDriver...")
        driver = setup_chrome_driver()
        
        # Navigate to URL
        print(f"[DEBUG] Navigating to URL...")
        driver.get(url)
        
        # Wait for page to load
        print(f"[DEBUG] Waiting for page to load...")
        try:
            WebDriverWait(driver, 20).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
        except TimeoutException:
            print("[WARNING] Timeout waiting for page body, continuing anyway...")
        
        # Give additional time for dynamic content
        time.sleep(3)
        
        # Extract swimmer data
        swimmers_data = []
        
        try:
            # Look for common table structures used by SwimCloud
            # Try multiple selectors to find swimmer data
            selectors_to_try = [
                "table tbody tr",  # Standard table rows
                ".time-row",       # SwimCloud specific class
                ".athlete-row",    # Alternative class name
                "tr[class*='time']", # Any row with 'time' in class
                "tr[class*='athlete']", # Any row with 'athlete' in class
            ]
            
            rows_found = []
            for selector in selectors_to_try:
                try:
                    rows = driver.find_elements(By.CSS_SELECTOR, selector)
                    if rows:
                        print(f"[DEBUG] Found {len(rows)} rows with selector: {selector}")
                        rows_found = rows
                        break
                except NoSuchElementException:
                    continue
            
            if not rows_found:
                # Fallback: get all table rows
                rows_found = driver.find_elements(By.CSS_SELECTOR, "tr")
                print(f"[DEBUG] Fallback: Found {len(rows_found)} total table rows")
            
            # Process each row
            for i, row in enumerate(rows_found):
                try:
                    row_text = row.text.strip()
                    if not row_text or row_text.lower() in ['name', 'athlete', 'time', 'year']:
                        continue  # Skip headers and empty rows
                    
                    # Look for time pattern in the row
                    time_pattern = r'(\d{1,2}):(\d{2})\.(\d{2})'
                    time_match = re.search(time_pattern, row_text)
                    
                    if time_match:
                        # Extract swimmer name (usually first part of row text)
                        cells = row.find_elements(By.TAG_NAME, "td")
                        
                        swimmer_data = {
                            'name': '',
                            'time': time_match.group(0),
                            'event': event_name,
                            'year': '',
                            'additional_info': row_text
                        }
                        
                        # Try to extract structured data from cells
                        if len(cells) >= 2:
                            # Typically: Name | Time | Year | Other info
                            swimmer_data['name'] = cells[0].text.strip()
                            
                            # Look for year information
                            for cell in cells:
                                cell_text = cell.text.strip()
                                if re.match(r'^\d{4}$', cell_text):  # 4-digit year
                                    swimmer_data['year'] = cell_text
                                    break
                                elif any(year in cell_text for year in ['FR', 'SO', 'JR', 'SR']):
                                    swimmer_data['year'] = cell_text
                                    break
                        else:
                            # Parse from combined text
                            parts = row_text.split()
                            if len(parts) >= 2:
                                # Assume first part(s) are name, look for time
                                name_parts = []
                                for part in parts:
                                    if not re.search(time_pattern, part):
                                        name_parts.append(part)
                                    else:
                                        break
                                swimmer_data['name'] = ' '.join(name_parts[:2])  # Take first 2 parts as name
                        
                        if swimmer_data['name']:  # Only add if we found a name
                            swimmers_data.append(swimmer_data)
                            print(f"[DEBUG] Extracted: {swimmer_data['name']} - {swimmer_data['time']}")
                
                except Exception as e:
                    print(f"[DEBUG] Error processing row {i}: {e}")
                    continue
        
        except Exception as e:
            print(f"[ERROR] Error extracting swimmer data: {e}")
            
            # Fallback: try to get page source and parse with BeautifulSoup
            try:
                print("[DEBUG] Attempting fallback parsing...")
                page_source = driver.page_source
                soup = BeautifulSoup(page_source, 'html.parser')
                
                # Look for time patterns in the entire page
                time_pattern = r'(\d{1,2}:\d{2}\.\d{2})'
                times = re.findall(time_pattern, page_source)
                
                print(f"[DEBUG] Fallback found {len(times)} time patterns")
                
                # Create basic entries for found times
                for i, time_str in enumerate(times[:10]):  # Limit to first 10
                    swimmers_data.append({
                        'name': f'Swimmer {i+1}',
                        'time': time_str,
                        'event': event_name,
                        'year': '',
                        'additional_info': 'Parsed from fallback method'
                    })
                    
            except Exception as fallback_error:
                print(f"[ERROR] Fallback parsing also failed: {fallback_error}")
        
        print(f"[DEBUG] Successfully extracted {len(swimmers_data)} swimmer records")
        return swimmers_data
        
    except Exception as e:
        print(f"[ERROR] Critical error in scrape_swimmer_times: {e}")
        import traceback
        traceback.print_exc()
        return []
        
    finally:
        if driver:
            try:
                driver.quit()
                print("[DEBUG] WebDriver closed successfully")
            except:
                print("[WARNING] Error closing WebDriver")

def scrape_with_requests_fallback(url):
    """
    Fallback scraping method using requests + BeautifulSoup
    Use this when Selenium fails
    """
    try:
        print(f"[DEBUG] Attempting requests fallback for: {url}")
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Extract event name
        event_name = extract_event_name_from_url(url)
        
        # Look for swimmer data in tables
        swimmers_data = []
        
        # Find all table rows
        rows = soup.find_all('tr')
        
        for row in rows:
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
                if cells:
                    swimmer_data['name'] = cells[0].get_text(strip=True)
                    
                    # Look for year in other cells
                    for cell in cells[1:]:
                        cell_text = cell.get_text(strip=True)
                        if re.match(r'^\d{4}$', cell_text) or cell_text in ['FR', 'SO', 'JR', 'SR']:
                            swimmer_data['year'] = cell_text
                            break
                
                if swimmer_data['name'] and swimmer_data['name'].lower() not in ['name', 'athlete']:
                    swimmers_data.append(swimmer_data)
        
        print(f"[DEBUG] Requests fallback extracted {len(swimmers_data)} records")
        return swimmers_data
        
    except Exception as e:
        print(f"[ERROR] Requests fallback failed: {e}")
        return []

def scrape_swimmer_times_with_fallback(url):
    """
    Main scraping function that tries Selenium first, then falls back to requests
    """
    try:
        # Try Selenium first
        data = scrape_swimmer_times(url)
        if data:
            return data
        else:
            print("[DEBUG] Selenium returned no data, trying requests fallback...")
            return scrape_with_requests_fallback(url)
            
    except Exception as e:
        print(f"[ERROR] Selenium scraping failed: {e}")
        print("[DEBUG] Trying requests fallback...")
        return scrape_with_requests_fallback(url)

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