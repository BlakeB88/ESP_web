# event_sorter.py
import pandas as pd
from Scraper.swimmer_scraper import scrape_and_save
from Scraper.data_processor import lineup_spread


def main():
    print("=== Dual Meet Lineup Builder ===")

    # 1) Ask for user inputs
    team_name = input("Enter the college/team name: ").strip()
    year_input = input("Enter year [default=2024]: ").strip()
    year = int(year_input) if year_input else 2024
    gender_input = input("Enter gender (M/F) [default=M]: ").strip().upper()
    gender = gender_input if gender_input in ("M", "F") else "M"

    # 2) Where the JSON lives (relative to this file)
    mappings_file = "Scraper/maps/team_mappings/all_college_teams.json"
    # 3) Where we will write the raw swimmer‐times Excel
    filename = "swimmer_times.xlsx"

    # 4) Scrape and save all times
    try:
        print(f"→ Scraping SwimCloud for {team_name} ({gender}, {year}) using mappings from {mappings_file}...")
        scrape_and_save(
            team_name=team_name,
            year=year,
            gender=gender,
            filename=filename,
            mappings_file=mappings_file
        )
    except Exception as e:
        print(f"Error during scraping: {e}")
        return

    # 5) Now load that same Excel and do the lineup‐assignment
    print(f"→ Running lineup optimization from '{filename}'...")
    try:
        # Load the Excel file into a DataFrame first
        times_df = pd.read_excel(filename)
        print(f"→ Loaded {len(times_df)} swimmers from Excel file")
        
        # Now call lineup_spread with the DataFrame
        lineup_df = lineup_spread(times_df, max_events_per_swimmer=4, swimmers_per_event=5)
                        
    except Exception as e:
        print(f"Error in lineup_spread: {e}")
        return

    # 6) Print out the assignment for each event
    print("\n=== DUAL MEET LINEUP ===")
    
    # Group by events and display
    events = lineup_df['Event'].unique()
    for event in events:
        event_swimmers = lineup_df[lineup_df['Event'] == event]
        print(f"\n{event}:")
        for _, row in event_swimmers.iterrows():
            print(f"  {row['Swimmer']:<25}  {row['Time']}")
    
    print(f"\n=== Lineup Complete: {len(events)} events, {len(lineup_df)} total entries ===")


if __name__ == "__main__":
    main()