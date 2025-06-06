# event_sorter.py
import pandas as pd
from Scraper.swimmer_scraper import scrape_and_save
from Scraper.data_processor import lineup_spread
from datetime import datetime


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

    # 6) Create CSV output filename with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    csv_filename = f"lineup_{team_name.replace(' ', '_')}_{gender}_{year}_{timestamp}.csv"
    
    # 7) Prepare enhanced lineup data for CSV export
    csv_data = []
    events = lineup_df['Event'].unique()
    
    for event in events:
        event_swimmers = lineup_df[lineup_df['Event'] == event].sort_values('Time')
        
        # Calculate event statistics
        times = []
        for _, row in event_swimmers.iterrows():
            times.append(row['Time'])
        
        # Convert times to seconds for calculations
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
                times_in_seconds.append(0)
        
        # Calculate event metrics
        if times_in_seconds:
            avg_time = sum(times_in_seconds) / len(times_in_seconds)
            fastest_time = min(times_in_seconds)
            slowest_time = max(times_in_seconds)
            time_range = slowest_time - fastest_time
        else:
            avg_time = fastest_time = slowest_time = time_range = 0
        
        # Add each swimmer to CSV data with event context
        for i, (_, row) in enumerate(event_swimmers.iterrows(), 1):
            csv_data.append({
                'Event': event,
                'Position': i,
                'Swimmer': row['Swimmer'],
                'Time': row['Time'],
                'Event_Avg_Time': f"{avg_time:.2f}s" if avg_time > 0 else "N/A",
                'Event_Fastest': f"{fastest_time:.2f}s" if fastest_time > 0 else "N/A",
                'Event_Slowest': f"{slowest_time:.2f}s" if slowest_time > 0 else "N/A",
                'Event_Range': f"{time_range:.2f}s" if time_range > 0 else "N/A",
                'Swimmers_In_Event': len(event_swimmers)
            })
    
    # 8) Create and save CSV
    csv_df = pd.DataFrame(csv_data)
    csv_df.to_csv(csv_filename, index=False)
    print(f"→ Lineup saved to CSV: {csv_filename}")
    
    # 9) Create summary CSV with team-level statistics
    summary_filename = f"lineup_summary_{team_name.replace(' ', '_')}_{gender}_{year}_{timestamp}.csv"
    
    # Calculate swimmer event distribution
    swimmer_counts = lineup_df['Swimmer'].value_counts()
    
    summary_data = {
        'Team': [team_name],
        'Gender': [gender],
        'Year': [year],
        'Total_Events': [len(events)],
        'Total_Lineup_Entries': [len(lineup_df)],
        'Swimmers_4_Events': [sum(swimmer_counts == MAX_EVENTS_PER_SWIMMER)],
        'Swimmers_3_Events': [sum(swimmer_counts == 3)],
        'Swimmers_2_Events': [sum(swimmer_counts == 2)],
        'Swimmers_1_Event': [sum(swimmer_counts == 1)],
        'Generated_At': [datetime.now().strftime("%Y-%m-%d %H:%M:%S")]
    }
    
    # Add event statistics if available
    if csv_data:
        event_ranges = [float(row['Event_Range'].replace('s', '')) for row in csv_data 
                       if row['Event_Range'] != "N/A" and row['Position'] == 1]  # Only get one per event
        if event_ranges:
            summary_data['Avg_Event_Range'] = [f"{sum(event_ranges)/len(event_ranges):.2f}s"]
            summary_data['Min_Event_Range'] = [f"{min(event_ranges):.2f}s"]
            summary_data['Max_Event_Range'] = [f"{max(event_ranges):.2f}s"]
        else:
            summary_data['Avg_Event_Range'] = ["N/A"]
            summary_data['Min_Event_Range'] = ["N/A"]
            summary_data['Max_Event_Range'] = ["N/A"]
    
    summary_df = pd.DataFrame(summary_data)
    summary_df.to_csv(summary_filename, index=False)
    print(f"→ Summary saved to CSV: {summary_filename}")

    # 10) Print out the assignment for each event (console output remains)
    print("\n=== DUAL MEET LINEUP ===")
    
    for event in events:
        event_swimmers = lineup_df[lineup_df['Event'] == event].sort_values('Time')
        print(f"\n{event}:")
        
        for i, (_, row) in enumerate(event_swimmers.iterrows(), 1):
            print(f"  {i}. {row['Swimmer']:<25}  {row['Time']}")
    
    # 11) Display summary statistics
    print(f"\n=== LINEUP SUMMARY ===")
    print(f"Total Events: {len(events)}")
    print(f"Total Lineup Entries: {len(lineup_df)}")
    
    # Show swimmer event counts
    print(f"\nSwimmer Event Distribution:")
    print(f"  Swimmers with {MAX_EVENTS_PER_SWIMMER} events: {sum(swimmer_counts == MAX_EVENTS_PER_SWIMMER)}")
    print(f"  Swimmers with 3 events: {sum(swimmer_counts == 3)}")
    print(f"  Swimmers with 2 events: {sum(swimmer_counts == 2)}")
    print(f"  Swimmers with 1 event: {sum(swimmer_counts == 1)}")
    
    print(f"\n=== Files Generated ===")
    print(f"  Main lineup: {csv_filename}")
    print(f"  Summary stats: {summary_filename}")
    print(f"=== Lineup Complete: Optimized for even talent distribution ===")


if __name__ == "__main__":
    main()