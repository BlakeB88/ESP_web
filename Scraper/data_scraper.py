import re
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service
import time

# Map SwimCloud event codes to event names
EVENT_CODE_TO_NAME = {
    "1|50|1": "50 free",
    "1|100|1": "100 free",
    "1|200|1": "200 free",
    "1|500|1": "500 free",
    "1|1650|1": "1650 free",
    "2|100|1": "100 back",
    "2|200|1": "200 back",
    "3|100|1": "100 breast",
    "3|200|1": "200 breast",
    "4|100|1": "100 fly",
    "4|200|1": "200 fly",
    "5|200|1": "200 IM",
    "5|400|1": "400 IM"
}

def scrape_swimmer_times(url):
    """
    Scrape swimmer times from a SwimCloud URL using Selenium for dynamic content.
    """
    print(f"[DEBUG] Scraping swimmer times from: {url}")
    
    # Set up Selenium
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    
    try:
        driver.get(url)
        time.sleep(5)  # Wait for JavaScript to load
        soup = BeautifulSoup(driver.page_source, "html.parser")
        
        print(f"[DEBUG] Page title: {soup.title.string if soup.title else 'No title'}")
        
        # Save debug file
        with open('debug_swimcloud_page.html', 'w', encoding='utf-8') as f:
            f.write(driver.page_source)
        print("[DEBUG] Saved page content to debug_swimcloud_page.html")
        
        # Extract event code from URL
        event_code = re.search(r'event=([^&]+)', url)
        event_name = EVENT_CODE_TO_NAME.get(event_code.group(1).replace('%7C', '|'), "Unknown Event") if event_code else "Unknown Event"
        print(f"[DEBUG] Event name from URL: {event_name}")
        
        # Try different extraction strategies
        times_data = extract_swimcloud_times_table(soup, default_event=event_name)
        if times_data and len(times_data) > 0:
            print(f"[DEBUG] Found {len(times_data)} time records from SwimCloud table")
            return times_data
        
        times_data = extract_times_from_any_table(soup, default_event=event_name)
        if times_data and len(times_data) > 0:
            print(f"[DEBUG] Found {len(times_data)} time records from general tables")
            return times_data
        
        times_data = extract_times_from_scripts(soup)
        if times_data:
            print(f"[DEBUG] Found {len(times_data)} time records from scripts")
            return times_data
        
        raise Exception("No time data found on page - check debug_swimcloud_page.html")
    
    finally:
        driver.quit()

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
        '1650 free': r'1650\s*free',
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