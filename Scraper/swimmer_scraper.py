import time
import pandas as pd
from .team_mappings import load_team_mappings, find_team_id
from .url_builder import build_swimcloud_times_url, test_times_url, EVENT_MAPPINGS
from .data_scraper import scrape_swimmer_times
from .data_processor import create_times_dataframe, save_to_excel
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
import os


def scrape_and_save(team_name, year=2024, gender="M", filename="swimmer_times.xlsx", 
                   mappings_file="Scraper/maps/team_mappings/all_college_teams.json", 
                   selected_events=None):
    """
    Main function to scrape swimmer time data for selected events.
    
    Args:
        team_name: Name of the team to scrape
        year: Season year
        gender: "M" or "F"
        filename: Output Excel filename
        mappings_file: Path to team mappings JSON file
        selected_events: List of event codes to scrape (e.g., ['50_free', '100_free'])
                        If None, scrapes all events
    """
    try:
        # Load team mappings
        print(f"→ Loading team mappings from {mappings_file}...")
        mappings = load_team_mappings(mappings_file)
        
        if not mappings:
            raise Exception(f"No team mappings loaded from {mappings_file}")
        
        # Find team ID
        print(f"→ Finding SwimCloud ID for '{team_name}'...")
        team_id = find_team_id(team_name, mappings)
        
        if not team_id:
            available_teams = list(mappings.values())[:10]
            raise Exception(f"Team '{team_name}' not found in mappings. Available teams include: {available_teams}")
        
        # Determine which events to scrape
        if selected_events is None:
            # Scrape all events (original behavior)
            events_to_scrape = EVENT_MAPPINGS.items()
            print(f"→ Scraping all {len(EVENT_MAPPINGS)} events...")
        else:
            # Scrape only selected events
            events_to_scrape = [(event_name, event_code) for event_name, event_code in EVENT_MAPPINGS.items() 
                               if event_name in selected_events]
            print(f"→ Scraping {len(events_to_scrape)} selected events: {[name for name, _ in events_to_scrape]}")
            
            # Warn about any requested events that aren't in EVENT_MAPPINGS
            missing_events = [event for event in selected_events if event not in EVENT_MAPPINGS]
            if missing_events:
                print(f"⚠️  Warning: These requested events are not available in EVENT_MAPPINGS: {missing_events}")
                print(f"   Available events: {list(EVENT_MAPPINGS.keys())}")
        
        # Scrape data for each event
        print(f"→ Scraping swimmer times for team ID: {team_id}...")
        all_times_data = []  # Store raw times data instead of DataFrames
        
        for event_name, event_code in events_to_scrape:
            print(f"→ Processing event: {event_name}")
            times_url = build_swimcloud_times_url(team_id, year, gender, event=event_code)
            
            if not test_times_url(times_url):
                print(f"[DEBUG] Event {event_name} URL failed, skipping...")
                continue
            
            time.sleep(2)  # Respectful delay
            try:
                # Get raw times data (list of tuples)
                times_data = scrape_swimmer_times(times_url)
                if times_data:
                    # Add the raw data to our collection
                    all_times_data.extend(times_data)
                    print(f"   ✓ Successfully scraped {len(times_data)} entries for {event_name}")
                else:
                    print(f"   ⚠️  No times data returned for {event_name}")
            except Exception as e:
                print(f"[DEBUG] Failed to scrape {event_name}: {e}")
                continue
        
        if not all_times_data:
            raise Exception("No data scraped for any events")
        
        print(f"→ Total raw entries collected: {len(all_times_data)}")
        
        # Process all data at once using the existing create_times_dataframe function
        # This will handle deduplication, cleaning, and pivot table creation
        final_df = create_times_dataframe(all_times_data)
        
        print(f"→ Final processed data: {final_df.shape[0]} swimmers")
        if len(final_df.columns) > 1:
            events_in_final = [col for col in final_df.columns if col != 'Swimmer']
            print(f"→ Events in final dataset: {events_in_final}")
        
        # Save to Excel
        result = save_to_excel(final_df, filename)
        
        print(f"✓ Successfully scraped and saved {len(events_to_scrape)} events to {filename}")
        return result
        
    except Exception as e:
        print(f"✗ Error: {e}")
        print("\n💡 Troubleshooting suggestions:")
        print("1. Check the debug_swimcloud_page.html file to see what SwimCloud returned")
        print("2. The URL structure may have changed - compare with your working URL")
        print("3. SwimCloud may be blocking automated requests")
        print("4. Try manually visiting the URL to see if data is available")
        print("5. Consider adding delays between requests or using different headers")
        raise