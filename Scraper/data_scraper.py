import re
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service
import time
import urllib.parse

# Updated Map SwimCloud event codes to event names - FIXED 1500 to 1650 mapping
EVENT_CODE_TO_NAME = {
    "1|50|1": "50 Free",      # Changed from "50 free"
    "1|100|1": "100 Free",    # Changed from "100 free"
    "1|200|1": "200 Free",    # Changed from "200 free"
    "1|500|1": "500 Free",    # Changed from "500 free"
    "1|1000|1": "1000 Free",  # Changed from "1000 free"
    "1|1500|1": "1650 Free",  # Changed from "1650 free"
    "2|50|1": "50 Back",      # Changed from "50 back"
    "2|100|1": "100 Back",    # Changed from "100 back"
    "2|200|1": "200 Back",    # Changed from "200 back"
    "3|50|1": "50 Breast",    # Changed from "50 breast"
    "3|100|1": "100 Breast",  # Changed from "100 breast"
    "3|200|1": "200 Breast",  # Changed from "200 breast"
    "4|50|1": "50 Fly",       # Changed from "50 fly"
    "4|100|1": "100 Fly",     # Changed from "100 fly"
    "4|200|1": "200 Fly",     # Changed from "200 fly"
    "5|200|1": "200 IM",
    "5|400|1": "400 IM"
}

def debug_url_and_event_extraction(url):
    """
    Debug function to better understand URL parsing and event extraction.
    """
    print(f"[DEBUG] Original URL: {url}")
    
    # Parse the URL to extract parameters
    from urllib.parse import urlparse, parse_qs
    parsed_url = urlparse(url)
    query_params = parse_qs(parsed_url.query)
    
    print(f"[DEBUG] Parsed query parameters: {query_params}")
    
    # Look for event parameter
    if 'event' in query_params:
        raw_event = query_params['event'][0]
        print(f"[DEBUG] Raw event parameter: {raw_event}")
        
        # URL decode it
        decoded_event = urllib.parse.unquote(raw_event)
        print(f"[DEBUG] URL decoded event: {decoded_event}")
        
        # Check if it's in our mapping
        if decoded_event in EVENT_CODE_TO_NAME:
            event_name = EVENT_CODE_TO_NAME[decoded_event]
            print(f"[DEBUG] Found event name: {event_name}")
        else:
            print(f"[DEBUG] Event code '{decoded_event}' not found in mapping!")
            print(f"[DEBUG] Available event codes: {list(EVENT_CODE_TO_NAME.keys())}")
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

def scrape_swimmer_times(url):
    """
    Enhanced scrape swimmer times function with better debugging.
    """
    driver = None
    try:
        print(f"[DEBUG] Scraping swimmer times from: {url}")
        
        # Debug the URL and event extraction first
        event_code, event_name = debug_url_and_event_extraction(url)
        
        # ── Step 1: Launch Chrome headless ───────────────────────────────────
        options = Options()
        options.add_argument("--headless")
        options.add_argument("--disable-gpu")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        # Add more realistic user agent
        options.add_argument(
            "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        )
        # Disable images to speed up loading
        prefs = {"profile.managed_default_content_settings.images": 2}
        options.add_experimental_option("prefs", prefs)

        driver = webdriver.Chrome(
            service=Service(ChromeDriverManager().install()),
            options=options
        )

        # ── Step 2: Navigate and wait for content ───────────────────────────────────
        driver.get(url)
        
        # Wait longer and check for different loading states
        print("[DEBUG] Waiting for page to load...")
        time.sleep(3)
        
        # Check if we got redirected or if there's a "No times" message
        current_url = driver.current_url
        print(f"[DEBUG] Current URL after load: {current_url}")
        
        # Look for loading indicators or "No times" messages
        try:
            no_times_element = driver.find_element("xpath", "//*[contains(text(), 'No times') or contains(text(), 'no times')]")
            if no_times_element:
                print("[DEBUG] Found 'No times' message on page")
        except:
            pass
        
        # Wait a bit more for dynamic content
        time.sleep(2)
        
        page_html = driver.page_source

        # Always save out whatever we just got, so you can inspect it.
        with open("debug_swimcloud_page.html", "w", encoding="utf-8") as f:
            f.write(page_html)
        print("[DEBUG] Saved page content to debug_swimcloud_page.html")

        # ── Step 3: Parse with BeautifulSoup ─────────────────────────────────
        soup = BeautifulSoup(page_html, "html.parser")
        
        # Debug: Look for key elements that indicate what's on the page
        print("[DEBUG] Looking for key page elements...")
        
        # Check for "No times" message
        no_times_elements = soup.find_all(text=re.compile(r"No times|no times", re.I))
        if no_times_elements:
            print(f"[DEBUG] Found 'No times' text: {no_times_elements}")
        
        # Check for filter information
        filter_elements = soup.find_all(text=re.compile(r"Filter|filter", re.I))
        if filter_elements:
            print(f"[DEBUG] Found filter-related text")
        
        # Look for any tables
        tables = soup.find_all("table")
        print(f"[DEBUG] Found {len(tables)} tables on page")
        
        # Look for swimmer data in various formats
        swimmer_links = soup.find_all("a", href=re.compile(r"/swimmer/\d+"))
        if swimmer_links:
            print(f"[DEBUG] Found {len(swimmer_links)} swimmer links")
        else:
            print("[DEBUG] No swimmer links found")

        # ── Step 4: Try different extraction methods ─────────────────────────────────
        print(f"[DEBUG] Event name from URL: {event_name}")

        # First attempt: look for the standard SwimCloud <table> layout
        times_data = extract_swimcloud_times_table(soup, default_event=event_name)
        if times_data and len(times_data) > 0:
            print(f"[DEBUG] Found {len(times_data)} time records from SwimCloud table")
            return times_data

        # Second attempt: look for any <table> on the page that has times
        times_data = extract_times_from_any_table(soup, default_event=event_name)
        if times_data and len(times_data) > 0:
            print(f"[DEBUG] Found {len(times_data)} time records from general tables")
            return times_data

        # Third attempt: maybe the times are embedded in a <script> tag
        times_data = extract_times_from_scripts(soup)
        if times_data and len(times_data) > 0:
            print(f"[DEBUG] Found {len(times_data)} time records from scripts")
            return times_data

        # Fourth attempt: Look for any time-like patterns in the entire page
        times_data = extract_times_from_page_text(soup, default_event=event_name)
        if times_data and len(times_data) > 0:
            print(f"[DEBUG] Found {len(times_data)} time records from page text")
            return times_data

        # If we reach here, no times were found
        print("[DEBUG] No time data found using any method → returning empty list")
        
        # Final debug: show some of the page content
        page_text = soup.get_text()[:1000]  # First 1000 characters
        print(f"[DEBUG] First 1000 characters of page: {page_text}")
        
        return []

    except Exception as e:
        print(f"[DEBUG] Exception inside scrape_swimmer_times: {e}")
        raise

    finally:
        if driver:
            try:
                driver.quit()
                print("[DEBUG] driver.quit() successful")
            except Exception as e_quit:
                print(f"[DEBUG] Exception during driver.quit(): {e_quit}")

def extract_times_from_page_text(soup, default_event="Unknown Event"):
    """
    New method: Extract times from any text on the page that matches swimmer patterns.
    """
    data = []
    
    # Get all text from the page
    page_text = soup.get_text()
    
    # Look for patterns like "Name Time" or swimmer data
    # This is a more aggressive approach for when tables fail
    lines = page_text.split('\n')
    
    for i, line in enumerate(lines):
        line = line.strip()
        if not line:
            continue
            
        # Look for time patterns (MM:SS.SS or SS.SS)
        time_matches = re.findall(r'\b\d+:\d{2}\.\d{2}\b|\b\d{1,2}\.\d{2}\b', line)
        
        if time_matches:
            # Look for names in nearby lines
            for j in range(max(0, i-2), min(len(lines), i+3)):
                nearby_line = lines[j].strip()
                
                # Simple heuristic: if it's not the time line and has reasonable length
                if j != i and 3 <= len(nearby_line) <= 50 and not re.search(r'\d+:\d{2}\.\d{2}|\d{1,2}\.\d{2}', nearby_line):
                    # Could be a name
                    potential_name = nearby_line
                    
                    # Basic validation
                    if not potential_name.isdigit() and ' ' in potential_name:
                        for time_val in time_matches:
                            data.append((potential_name, default_event, time_val))
                            print(f"[DEBUG] Added from page text: {potential_name}, {default_event}, {time_val}")
                        break
    
    return data

# Keep all your existing extraction functions but add this debug function:

def debug_swimcloud_event_codes():
    """
    Helper function to debug what event codes SwimCloud actually uses.
    Call this to see if there are patterns we're missing.
    """
    # This would be used to manually check various event URLs
    common_events = [
        "1|50|1", "1|100|1", "1|200|1", "1|500|1", "1|1000|1", "1|1500|1", "1|1650|1",
        "2|50|1", "2|100|1", "2|200|1", 
        "3|50|1", "3|100|1", "3|200|1",
        "4|50|1", "4|100|1", "4|200|1",
        "5|200|1", "5|400|1"
    ]
    
    print("Event code mapping:")
    for code in common_events:
        name = EVENT_CODE_TO_NAME.get(code, "MISSING")
        print(f"  {code} -> {name}")

# Copy all your existing extraction functions here:
def extract_swimcloud_times_table(soup, default_event="Unknown Event"):
    """
    Extract times from SwimCloud's specific table structure with robust parsing.
    """
    data = []
    
    # Find all tables that might contain times
    tables = soup.find_all("table", class_=re.compile(r'table|times|results|data', re.I)) or soup.find_all("table")
    
    for table in tables:
        print(f"[DEBUG] Analyzing table...")
        
        # Get all rows
        rows = table.find_all("tr")
        if len(rows) < 2:
            print("[DEBUG] Table has too few rows, skipping")
            continue
        
        # Get headers
        header_row = rows[0]
        headers = [th.get_text(strip=True).lower() for th in header_row.find_all(["th", "td"])]
        print(f"[DEBUG] Table headers: {headers}")
        
        # Check if this looks like a SwimCloud times table
        header_text = ' '.join(headers).lower()
        if not ('name' in header_text and 'time' in header_text):
            print("[DEBUG] Table doesn't contain name and time columns, skipping")
            continue
        
        # Process data rows (skip header row)
        for i, row in enumerate(rows[1:], 1):
            cols = row.find_all(["td", "th"])
            print(f"[DEBUG] Row {i}: Found {len(cols)} columns")
            
            if len(cols) < 4:  # SwimCloud tables typically have at least 4-5 columns
                print(f"[DEBUG] Row {i} has too few columns: {len(cols)}")
                continue
            
            try:
                # For SwimCloud structure: [rank, name, meet, time, flags]
                # Try different column combinations based on what we see
                swimmer_name = None
                time_value = None
                
                # Look through columns to find name and time
                for col_idx, col in enumerate(cols):
                    col_text = col.get_text(strip=True)
                    
                    # Check if this column contains a swimmer name (has a link to /swimmer/)
                    swimmer_link = col.find('a', href=re.compile(r'/swimmer/\d+'))
                    if swimmer_link:
                        swimmer_name = swimmer_link.get_text(strip=True)
                        print(f"[DEBUG] Found swimmer name in column {col_idx}: {swimmer_name}")
                        continue
                    
                    # Check if this column contains a time (format like MM:SS.SS)
                    if re.search(r'\d+:\d{2}\.\d{2}|\d+\.\d{2}', col_text):
                        # Extract just the time from any links
                        time_link = col.find('a')
                        if time_link:
                            time_value = time_link.get_text(strip=True)
                        else:
                            time_value = col_text
                        
                        # Clean the time value
                        time_value = re.sub(r'[^\d:.]', '', time_value)
                        print(f"[DEBUG] Found time in column {col_idx}: {time_value}")
                        continue
                
                if swimmer_name and time_value:
                    # Validate swimmer name
                    if len(swimmer_name) < 3 or swimmer_name.isdigit():
                        print(f"[DEBUG] Invalid swimmer name: {swimmer_name}")
                        continue
                    
                    # Validate time format
                    if not re.match(r'(\d+:\d{2}\.\d+|\d+\.\d+|\d+:\d{2}:\d{2}\.\d+)', time_value):
                        print(f"[DEBUG] Invalid time format: {time_value}")
                        continue
                    
                    data.append((swimmer_name, default_event, time_value))
                    print(f"[DEBUG] Added record: {swimmer_name}, {default_event}, {time_value}")
                else:
                    print(f"[DEBUG] Row {i}: Could not find both name and time")
                    print(f"[DEBUG] Row {i} raw data: {[col.get_text(strip=True) for col in cols]}")
                
            except Exception as e:
                print(f"[DEBUG] Error processing row {i}: {e}")
                continue
    
    return data

def extract_times_from_any_table(soup, default_event="Unknown Event"):
    """
    Extract time data from any table, using default_event if event not in table.
    """
    data = []
    tables = soup.find_all("table")
    
    for table in tables:
        table_text = table.get_text().lower()
        
        if not any(indicator in table_text for indicator in ['time', 'swimmer', 'free', 'back', 'breast', 'fly']):
            print("[DEBUG] Table lacks time/swimmer indicators, skipping")
            continue
        
        rows = table.find_all("tr")
        if len(rows) < 2:
            print("[DEBUG] Table has too few rows, skipping")
            continue
        
        header_row = rows[0]
        headers = [th.get_text(strip=True) for th in header_row.find_all(["th", "td"])]
        print(f"[DEBUG] Table headers: {headers}")
        
        name_col = find_column_index(headers, ['swimmer', 'name', 'athlete'])
        time_col = find_column_index(headers, ['time', 'result', 'best', 'season', 'personal'])
        
        if name_col is not None and time_col is not None:
            for row in rows[1:]:
                cols = row.find_all(["td", "th"])
                if len(cols) > max(name_col, time_col):
                    try:
                        raw_name = cols[name_col].get_text(strip=True)
                        raw_time = cols[time_col].get_text(strip=True)
                        time_value = re.sub(r'[^\d:.]', '', raw_time)
                        print(f"[DEBUG] Raw row data - Name: {raw_name}, Time: {raw_time}")
                        
                        if not raw_name or raw_name.isdigit() or len(raw_name) < 3:
                            print(f"[DEBUG] Skipped row - Invalid name: {raw_name}")
                            continue
                        
                        if time_value and re.match(r'\d+:\d+\.?\d*|\d+\.\d+', time_value):
                            data.append((raw_name, default_event, time_value))
                            print(f"[DEBUG] Added record: {raw_name}, {default_event}, {time_value}")
                        else:
                            print(f"[DEBUG] Skipped row - Invalid time format: {time_value}")
                    except (IndexError, AttributeError) as e:
                        print(f"[DEBUG] Error processing row: {e}")
                        continue
    
    return data

def extract_times_from_scripts(soup):
    """
    Extract data from embedded JavaScript/JSON.
    """
    data = []
    scripts = soup.find_all("script")
    
    for script in scripts:
        if script.string:
            script_text = script.string
            json_matches = re.findall(r'\{[^}]*"time"[^}]*\}', script_text, re.IGNORECASE)
            for match in json_matches:
                try:
                    if '"name"' in match.lower() and '"time"' in match.lower():
                        name_match = re.search(r'"name":\s*"([^"]+)"', match, re.IGNORECASE)
                        time_match = re.search(r'"time":\s*"([^"]+)"', match, re.IGNORECASE)
                        if name_match and time_match:
                            time_value = re.sub(r'[^\d:.]', '', time_match.group(1))
                            if re.match(r'\d+:\d+\.?\d*|\d+\.\d+', time_value):
                                data.append((name_match.group(1), "Unknown Event", time_value))
                                print(f"[DEBUG] Added script record: {name_match.group(1)}, Unknown Event, {time_value}")
                except Exception as e:
                    print(f"[DEBUG] Error processing script: {e}")
                    continue
    
    return data

def find_column_index(headers, search_terms):
    """
    Find the index of a column based on search terms.
    """
    for i, header in enumerate(headers):
        header_lower = header.lower()
        if any(term in header_lower for term in search_terms):
            return i
    return None

def extract_event_from_row(row):
    """
    Extract event information from a row (fallback, rarely used).
    """
    row_text = row.get_text().lower()
    
    event_patterns = {
        '50 free': r'50\s*free',
        '100 free': r'100\s*free',
        '200 free': r'200\s*free',
        '500 free': r'500\s*free',
        '1000 free': r'1000\s*free',
        '1650 free': r'1650\s*free',  # Updated to match 1650 output
        '100 back': r'100\s*back',
        '200 back': r'200\s*back',
        '100 breast': r'100\s*breast',
        '200 breast': r'200\s*breast',
        '100 fly': r'100\s*fly',
        '200 fly': r'200\s*fly',
        '200 IM': r'200\s*im',
        '400 IM': r'400\s*im'
    }
    
    for event_name, pattern in event_patterns.items():
        if re.search(pattern, row_text):
            print(f"[DEBUG] Found event in row: {event_name}")
            return event_name
    
    return None

# Test the event code debugging
if __name__ == "__main__":
    debug_swimcloud_event_codes()
    
    # Test URL parsing
    test_url = "https://www.swimcloud.com/team/34/times/?dont_group=false&event_course=Y&gender=M&page=1&season_id=28&team_id=34&year=2025&region=&tag_id=&event=1%7C1650%7C1"
    debug_url_and_event_extraction(test_url)