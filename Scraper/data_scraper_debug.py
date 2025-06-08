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
    Enhanced debugging for 1650 free event.
    """
    print(f"[DEBUG] Scraping swimmer times from: {url}")

    # Check if this is a 1650 URL
    is_1650_url = "1650" in url or "1%7C1650%7C1" in url
    if is_1650_url:
        print(f"[1650 DEBUG] *** PROCESSING 1650 FREE EVENT ***")
        print(f"[1650 DEBUG] URL contains 1650 pattern: {url}")

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

        # Save debug file with special naming for 1650
        debug_filename = 'debug_swimcloud_1650_page.html' if is_1650_url else 'debug_swimcloud_page.html'
        with open(debug_filename, 'w', encoding='utf-8') as f:
            f.write(driver.page_source)
        print(f"[DEBUG] Saved page content to {debug_filename}")

        if is_1650_url:
            print(f"[1650 DEBUG] Checking page content for 1650 indicators...")
            page_text = soup.get_text().lower()

            # Check for 1650 indicators
            indicators_1650 = ['1650', '1,650', 'mile', 'distance']
            found_indicators = [ind for ind in indicators_1650 if ind in page_text]
            print(f"[1650 DEBUG] Found 1650 indicators: {found_indicators}")

            # Check for time patterns that might be 1650 times (longer times)
            long_time_pattern = r'1[5-9]:\d{2}\.\d{2}|2[0-9]:\d{2}\.\d{2}'
            long_times = re.findall(long_time_pattern, driver.page_source)
            print(f"[1650 DEBUG] Found potential 1650 time patterns: {long_times[:5]}")  # Show first 5

            # Check if page shows "No results" or similar
            no_results_indicators = ['no results', 'no times', 'no data', 'not found']
            no_results_found = [ind for ind in no_results_indicators if ind in page_text]
            if no_results_found:
                print(f"[1650 DEBUG] WARNING: Page may have no results: {no_results_found}")

        # Extract event code from URL
        event_code = re.search(r'event=([^&]+)', url)
        event_name = EVENT_CODE_TO_NAME.get(event_code.group(1).replace('%7C', '|'), "Unknown Event") if event_code else "Unknown Event"
        print(f"[DEBUG] Event name from URL: {event_name}")

        if is_1650_url:
            print(f"[1650 DEBUG] Extracted event name: {event_name}")
            if event_name != "1650 free":
                print(f"[1650 DEBUG] WARNING: Event name mismatch! Expected '1650 free', got '{event_name}'")

        # Try different extraction strategies
        times_data = extract_swimcloud_times_table(soup, default_event=event_name, is_1650=is_1650_url)
        if times_data and len(times_data) > 0:
            print(f"[DEBUG] Found {len(times_data)} time records from SwimCloud table")
            if is_1650_url:
                print(f"[1650 DEBUG] SUCCESS: Found {len(times_data)} 1650 records!")
                for i, record in enumerate(times_data[:3]):  # Show first 3
                    print(f"[1650 DEBUG] Record {i+1}: {record}")
            return times_data

        times_data = extract_times_from_any_table(soup, default_event=event_name, is_1650=is_1650_url)
        if times_data and len(times_data) > 0:
            print(f"[DEBUG] Found {len(times_data)} time records from general tables")
            if is_1650_url:
                print(f"[1650 DEBUG] SUCCESS: Found {len(times_data)} 1650 records from general tables!")
            return times_data

        times_data = extract_times_from_scripts(soup, is_1650=is_1650_url)
        if times_data:
            print(f"[DEBUG] Found {len(times_data)} time records from scripts")
            if is_1650_url:
                print(f"[1650 DEBUG] SUCCESS: Found {len(times_data)} 1650 records from scripts!")
            return times_data

        if is_1650_url:
            print(f"[1650 DEBUG] FAILURE: No 1650 data found using any extraction method")
            print(f"[1650 DEBUG] Check {debug_filename} to see what SwimCloud returned")

        raise Exception(f"No time data found on page - check {debug_filename}")

    finally:
        driver.quit()

def extract_swimcloud_times_table(soup, default_event="Unknown Event", is_1650=False):
    """
    Extract times from SwimCloud's specific table structure with robust parsing.
    Enhanced debugging for 1650.
    """
    data = []

    if is_1650:
        print(f"[1650 DEBUG] Starting table extraction for 1650...")

    # Find all tables that might contain times
    tables = soup.find_all("table", class_=re.compile(r'table|times|results|data', re.I)) or soup.find_all("table")

    if is_1650:
        print(f"[1650 DEBUG] Found {len(tables)} tables to analyze")

    for table_idx, table in enumerate(tables):
        if is_1650:
            print(f"[1650 DEBUG] Analyzing table {table_idx + 1}...")

        # Get all rows
        rows = table.find_all("tr")
        if len(rows) < 2:
            if is_1650:
                print(f"[1650 DEBUG] Table {table_idx + 1} has too few rows ({len(rows)}), skipping")
            continue

        # Get headers
        header_row = rows[0]
        headers = [th.get_text(strip=True).lower() for th in header_row.find_all(["th", "td"])]

        if is_1650:
            print(f"[1650 DEBUG] Table {table_idx + 1} headers: {headers}")

        # Check if this looks like a SwimCloud times table
        header_text = ' '.join(headers).lower()
        if not ('name' in header_text and 'time' in header_text):
            if is_1650:
                print(f"[1650 DEBUG] Table {table_idx + 1} doesn't contain name and time columns, skipping")
            continue

        if is_1650:
            print(f"[1650 DEBUG] Table {table_idx + 1} looks like a times table, processing rows...")

        # Process data rows (skip header row)
        for i, row in enumerate(rows[1:], 1):
            cols = row.find_all(["td", "th"])

            if is_1650 and i <= 3:  # Debug first few rows for 1650
                print(f"[1650 DEBUG] Row {i}: Found {len(cols)} columns")
                row_text = [col.get_text(strip=True) for col in cols]
                print(f"[1650 DEBUG] Row {i} content: {row_text}")

            if len(cols) < 4:  # SwimCloud tables typically have at least 4-5 columns
                if is_1650 and i <= 3:
                    print(f"[1650 DEBUG] Row {i} has too few columns: {len(cols)}")
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
                        if is_1650 and i <= 3:
                            print(f"[1650 DEBUG] Found swimmer name in column {col_idx}: {swimmer_name}")
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
                        if is_1650 and i <= 3:
                            print(f"[1650 DEBUG] Found time in column {col_idx}: {time_value}")
                        continue

                if swimmer_name and time_value:
                    # Validate swimmer name
                    if len(swimmer_name) < 3 or swimmer_name.isdigit():
                        if is_1650 and i <= 3:
                            print(f"[1650 DEBUG] Invalid swimmer name: {swimmer_name}")
                        continue

                    # Validate time format
                    if not re.match(r'(\d+:\d{2}\.\d+|\d+\.\d+|\d+:\d{2}:\d{2}\.\d+)', time_value):
                        if is_1650 and i <= 3:
                            print(f"[1650 DEBUG] Invalid time format: {time_value}")
                        continue

                    data.append((swimmer_name, default_event, time_value))
                    if is_1650:
                        print(f"[1650 DEBUG] Added record: {swimmer_name}, {default_event}, {time_value}")
                else:
                    if is_1650 and i <= 3:
                        print(f"[1650 DEBUG] Row {i}: Could not find both name ({swimmer_name}) and time ({time_value})")

            except Exception as e:
                if is_1650:
                    print(f"[1650 DEBUG] Error processing row {i}: {e}")
                continue

    if is_1650:
        print(f"[1650 DEBUG] Table extraction complete. Found {len(data)} records.")

    return data

def extract_times_from_any_table(soup, default_event="Unknown Event", is_1650=False):
    """
    Extract time data from any table, using default_event if event not in table.
    Enhanced debugging for 1650.
    """
    data = []
    tables = soup.find_all("table")

    if is_1650:
        print(f"[1650 DEBUG] Starting general table extraction, found {len(tables)} tables")

    for table_idx, table in enumerate(tables):
        table_text = table.get_text().lower()

        if not any(indicator in table_text for indicator in ['time', 'swimmer', 'free', 'back', 'breast', 'fly']):
            if is_1650:
                print(f"[1650 DEBUG] Table {table_idx + 1} lacks time/swimmer indicators, skipping")
            continue

        rows = table.find_all("tr")
        if len(rows) < 2:
            if is_1650:
                print(f"[1650 DEBUG] Table {table_idx + 1} has too few rows, skipping")
            continue

        header_row = rows[0]
        headers = [th.get_text(strip=True) for th in header_row.find_all(["th", "td"])]

        if is_1650:
            print(f"[1650 DEBUG] Table {table_idx + 1} headers: {headers}")

        name_col = find_column_index(headers, ['swimmer', 'name', 'athlete'])
        time_col = find_column_index(headers, ['time', 'result', 'best', 'season', 'personal'])

        if name_col is not None and time_col is not None:
            if is_1650:
                print(f"[1650 DEBUG] Table {table_idx + 1} has name column {name_col} and time column {time_col}")

            for row_idx, row in enumerate(rows[1:], 1):
                cols = row.find_all(["td", "th"])
                if len(cols) > max(name_col, time_col):
                    try:
                        raw_name = cols[name_col].get_text(strip=True)
                        raw_time = cols[time_col].get_text(strip=True)
                        time_value = re.sub(r'[^\d:.]', '', raw_time)

                        if is_1650 and row_idx <= 3:
                            print(f"[1650 DEBUG] Row {row_idx} - Name: {raw_name}, Time: {raw_time} -> {time_value}")

                        if not raw_name or raw_name.isdigit() or len(raw_name) < 3:
                            if is_1650 and row_idx <= 3:
                                print(f"[1650 DEBUG] Skipped row {row_idx} - Invalid name: {raw_name}")
                            continue

                        if time_value and re.match(r'\d+:\d+\.?\d*|\d+\.\d+', time_value):
                            data.append((raw_name, default_event, time_value))
                            if is_1650:
                                print(f"[1650 DEBUG] Added record: {raw_name}, {default_event}, {time_value}")
                        else:
                            if is_1650 and row_idx <= 3:
                                print(f"[1650 DEBUG] Skipped row {row_idx} - Invalid time format: {time_value}")
                    except (IndexError, AttributeError) as e:
                        if is_1650:
                            print(f"[1650 DEBUG] Error processing row {row_idx}: {e}")
                        continue

    if is_1650:
        print(f"[1650 DEBUG] General table extraction complete. Found {len(data)} records.")

    return data

def extract_times_from_scripts(soup, is_1650=False):
    """
    Extract data from embedded JavaScript/JSON.
    Enhanced debugging for 1650.
    """
    data = []
    scripts = soup.find_all("script")

    if is_1650:
        print(f"[1650 DEBUG] Starting script extraction, found {len(scripts)} scripts")

    for script_idx, script in enumerate(scripts):
        if script.string:
            script_text = script.string
            json_matches = re.findall(r'\{[^}]*"time"[^}]*\}', script_text, re.IGNORECASE)

            if is_1650 and json_matches:
                print(f"[1650 DEBUG] Script {script_idx + 1} has {len(json_matches)} JSON matches with 'time'")

            for match in json_matches:
                try:
                    if '"name"' in match.lower() and '"time"' in match.lower():
                        name_match = re.search(r'"name":\s*"([^"]+)"', match, re.IGNORECASE)
                        time_match = re.search(r'"time":\s*"([^"]+)"', match, re.IGNORECASE)
                        if name_match and time_match:
                            time_value = re.sub(r'[^\d:.]', '', time_match.group(1))
                            if re.match(r'\d+:\d+\.?\d*|\d+\.\d+', time_value):
                                data.append((name_match.group(1), "Unknown Event", time_value))
                                if is_1650:
                                    print(f"[1650 DEBUG] Added script record: {name_match.group(1)}, Unknown Event, {time_value}")
                except Exception as e:
                    if is_1650:
                        print(f"[1650 DEBUG] Error processing script: {e}")
                    continue

    if is_1650:
        print(f"[1650 DEBUG] Script extraction complete. Found {len(data)} records.")

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
