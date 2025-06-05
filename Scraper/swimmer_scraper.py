import time
import pandas as pd
from .team_mappings import load_team_mappings, find_team_id
from .url_builder import build_swimcloud_times_url, test_times_url, EVENT_MAPPINGS
from .data_scraper import scrape_swimmer_times
from .data_processor import create_times_dataframe, save_to_excel

def scrape_and_save(team_name, year=2024, gender="M", filename="swimmer_times.xlsx", mappings_file="Scraper/maps/team_mappings/all_college_teams.json"):
    """
    Main function to scrape swimmer time data for all events.
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
        
        # Scrape data for each event
        print(f"→ Scraping swimmer times for team ID: {team_id}...")
        all_dfs = []
        
        for event_name, event_code in EVENT_MAPPINGS.items():
            print(f"→ Processing event: {event_name}")
            times_url = build_swimcloud_times_url(team_id, year, gender, event=event_code)
            
            if not test_times_url(times_url):
                print(f"[DEBUG] Event {event_name} URL failed, skipping...")
                continue
            
            time.sleep(2)  # Respectful delay
            try:
                times_data = scrape_swimmer_times(times_url)
                if times_data:
                    df = create_times_dataframe(times_data)
                    if not df.empty:
                        all_dfs.append(df)
            except Exception as e:
                print(f"[DEBUG] Failed to scrape {event_name}: {e}")
                continue
        
        if not all_dfs:
            raise Exception("No data scraped for any events")
        
        # Combine dataframes
        combined_df = pd.concat(all_dfs, ignore_index=True)
        combined_df = combined_df.drop_duplicates()
        
        # Pivot to final format
        try:
            pivot_df = combined_df.pivot_table(
                index="Swimmer",
                columns="Event",
                values="Time",
                aggfunc="first"
            ).reset_index()
            pivot_df.columns.name = None
            print(f"[DEBUG] Created pivot table: {pivot_df.shape[0]} swimmers, {pivot_df.shape[1]-1} events")
        except Exception as e:
            print(f"[DEBUG] Pivot table creation failed: {e}")
            pivot_df = combined_df
        
        # Save to Excel
        return save_to_excel(pivot_df, filename)
        
    except Exception as e:
        print(f"✗ Error: {e}")
        print("\n💡 Troubleshooting suggestions:")
        print("1. Check the debug_swimcloud_page.html file to see what SwimCloud returned")
        print("2. The URL structure may have changed - compare with your working URL")
        print("3. SwimCloud may be blocking automated requests")
        print("4. Try manually visiting the URL to see if data is available")
        print("5. Consider adding delays between requests or using different headers")
        raise