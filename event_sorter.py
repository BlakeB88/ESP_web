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
    
    # Configuration for lineup optimization
    MAX_EVENTS_PER_SWIMMER = 4
    SWIMMERS_PER_EVENT = 5
    
    try:
        # Load the Excel file into a DataFrame first
        times_df = pd.read_excel(filename)
        print(f"→ Loaded {len(times_df)} swimmers from Excel file")
        
        # Now call lineup_spread with explicit parameters for talent distribution
        print(f"→ Optimizing lineup: {SWIMMERS_PER_EVENT} swimmers per event, max {MAX_EVENTS_PER_SWIMMER} events per swimmer")
        lineup_df = lineup_spread(
            times_df, 
            max_events_per_swimmer=MAX_EVENTS_PER_SWIMMER, 
            swimmers_per_event=SWIMMERS_PER_EVENT
        )
                        
    except Exception as e:
        print(f"Error in lineup_spread: {e}")
        return

    # 6) Print out the assignment for each event with talent analysis
    print("\n=== DUAL MEET LINEUP ===")
    
    # Group by events and display with talent spread analysis
    events = lineup_df['Event'].unique()
    event_stats = []
    
    for event in events:
        event_swimmers = lineup_df[lineup_df['Event'] == event].sort_values('Time')
        print(f"\n{event}:")
        
        times = []
        for i, (_, row) in enumerate(event_swimmers.iterrows(), 1):
            print(f"  {i}. {row['Swimmer']:<25}  {row['Time']}")
            times.append(row['Time'])
        
        # Calculate event strength metrics (convert times to seconds for calculations)
        if times:
            # Convert time strings to seconds for mathematical operations
            times_in_seconds = []
            for time_str in times:
                try:
                    if ':' in str(time_str):
                        parts = str(time_str).split(':')
                        minutes = int(parts[0])
                        seconds = float(parts[1])
                        time_seconds = minutes * 60 + seconds
                    else:
                        time_seconds = float(time_str)
                    times_in_seconds.append(time_seconds)
                except (ValueError, IndexError):
                    continue
            
            if times_in_seconds:
                avg_time = sum(times_in_seconds) / len(times_in_seconds)
                fastest_time = min(times_in_seconds)
                slowest_time = max(times_in_seconds)
                event_stats.append({
                    'Event': event,
                    'Avg_Time': avg_time,
                    'Fastest': fastest_time,
                    'Slowest': slowest_time,
                    'Range': slowest_time - fastest_time,
                    'Swimmers': len(times_in_seconds)
                })
    
    # 7) Display talent distribution summary
    print(f"\n=== LINEUP SUMMARY ===")
    print(f"Total Events: {len(events)}")
    print(f"Total Lineup Entries: {len(lineup_df)}")
    
    # Show swimmer event counts
    swimmer_counts = lineup_df['Swimmer'].value_counts()
    print(f"\nSwimmer Event Distribution:")
    print(f"  Swimmers with {MAX_EVENTS_PER_SWIMMER} events: {sum(swimmer_counts == MAX_EVENTS_PER_SWIMMER)}")
    print(f"  Swimmers with 3 events: {sum(swimmer_counts == 3)}")
    print(f"  Swimmers with 2 events: {sum(swimmer_counts == 2)}")
    print(f"  Swimmers with 1 event: {sum(swimmer_counts == 1)}")
    
    # Show talent spread across events
    if event_stats:
        stats_df = pd.DataFrame(event_stats)
        print(f"\nTalent Distribution Across Events:")
        print(f"  Average time range across events: {stats_df['Range'].mean():.2f} seconds")
        print(f"  Most competitive event: {stats_df.loc[stats_df['Range'].idxmin(), 'Event']} (range: {stats_df['Range'].min():.2f}s)")
        print(f"  Least competitive event: {stats_df.loc[stats_df['Range'].idxmax(), 'Event']} (range: {stats_df['Range'].max():.2f}s)")
    
    print(f"\n=== Lineup Complete: Optimized for even talent distribution ===")


if __name__ == "__main__":
    main()