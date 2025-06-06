# event_sorter.py
import pandas as pd
from Scraper.swimmer_scraper import scrape_and_save
from Scraper.data_processor import lineup_spread
from datetime import datetime
import numpy as np


def time_to_seconds(time_str):
    """Convert time string to seconds for comparison"""
    try:
        if pd.isna(time_str) or time_str == '':
            return float('inf')
        if ':' in str(time_str):
            parts = str(time_str).split(':')
            minutes = int(parts[0])
            seconds = float(parts[1])
            return minutes * 60 + seconds
        else:
            return float(time_str)
    except (ValueError, IndexError):
        return float('inf')  # Return infinity for invalid times


def pivot_to_long_format(pivot_df):
    """
    Convert pivot table format to long format for lineup assignment
    """
    long_data = []
    
    # Get all event columns (everything except 'Swimmer')
    event_columns = [col for col in pivot_df.columns if col != 'Swimmer']
    
    for _, row in pivot_df.iterrows():
        swimmer = row['Swimmer']
        for event in event_columns:
            time_value = row[event]
            # Only include valid times (not NaN, not empty)
            if pd.notna(time_value) and str(time_value).strip() != '':
                long_data.append({
                    'Swimmer': swimmer,
                    'Event': event,
                    'Time': str(time_value).strip()
                })
    
    return pd.DataFrame(long_data)


def round_robin_assignment(times_df, max_events_per_swimmer=4, swimmers_per_event=4):
    """
    Assign swimmers to events using round-robin approach for balanced talent distribution
    """
    if times_df.empty:
        raise Exception("No swimmer data provided")
    
    # Check if we need to convert from pivot format
    if 'Event' not in times_df.columns:
        print("→ Converting pivot table format to long format...")
        times_df = pivot_to_long_format(times_df)
        print(f"→ Converted to {len(times_df)} swimmer-event combinations")
    
    if times_df.empty:
        raise Exception("No valid swimmer-event combinations found after conversion")
    
    # Get all unique events
    all_events = times_df['Event'].unique()
    print(f"→ Found {len(all_events)} events: {list(all_events)}")
    
    # Initialize tracking structures
    event_assignments = {event: [] for event in all_events}
    swimmer_event_counts = {}
    
    # Create a sorted list of all swimmer-event combinations by performance
    swimmer_event_pairs = []
    
    for _, row in times_df.iterrows():
        swimmer = row['Swimmer']
        event = row['Event']
        time = row['Time']
        time_seconds = time_to_seconds(time)
        
        # Skip invalid times
        if time_seconds == float('inf'):
            continue
        
        swimmer_event_pairs.append({
            'Swimmer': swimmer,
            'Event': event,
            'Time': time,
            'Time_Seconds': time_seconds
        })
    
    print(f"→ Processing {len(swimmer_event_pairs)} valid swimmer-event combinations")
    
    # Sort by time performance (fastest first)
    swimmer_event_pairs.sort(key=lambda x: x['Time_Seconds'])
    
    # Round-robin assignment
    assignment_round = 0
    events_list = list(all_events)
    
    print("→ Starting round-robin assignment...")
    
    while True:
        assignments_made = False
        
        # Go through each event in round-robin fashion
        for event_idx, current_event in enumerate(events_list):
            # Skip if this event already has enough swimmers
            if len(event_assignments[current_event]) >= swimmers_per_event:
                continue
            
            # Find the best available swimmer for this event
            best_swimmer = None
            best_pair_idx = None
            
            for idx, pair in enumerate(swimmer_event_pairs):
                if pair['Event'] != current_event:
                    continue
                
                swimmer = pair['Swimmer']
                
                # Check if swimmer is available (hasn't reached max events)
                current_events = swimmer_event_counts.get(swimmer, 0)
                if current_events >= max_events_per_swimmer:
                    continue
                
                # Check if swimmer is already assigned to this event
                if swimmer in [s['Swimmer'] for s in event_assignments[current_event]]:
                    continue
                
                # This is our best available swimmer for this event
                best_swimmer = pair
                best_pair_idx = idx
                break
            
            # Assign the best swimmer if found
            if best_swimmer:
                event_assignments[current_event].append(best_swimmer)
                swimmer_event_counts[best_swimmer['Swimmer']] = swimmer_event_counts.get(best_swimmer['Swimmer'], 0) + 1
                # Remove this pair so it's not considered again
                swimmer_event_pairs.pop(best_pair_idx)
                assignments_made = True
                
                print(f"→ Assigned {best_swimmer['Swimmer']} to {current_event} (Time: {best_swimmer['Time']})")
        
        # If no assignments were made in this round, we're done
        if not assignments_made:
            break
        
        assignment_round += 1
        
        # Safety check to prevent infinite loops
        if assignment_round > 100:
            print("Warning: Assignment process terminated after 100 rounds")
            break
    
    # Convert assignments back to DataFrame format
    lineup_data = []
    for event, swimmers in event_assignments.items():
        for swimmer_data in swimmers:
            lineup_data.append({
                'Event': event,
                'Swimmer': swimmer_data['Swimmer'],
                'Time': swimmer_data['Time']
            })
    
    # Fill remaining spots if some events don't have enough swimmers
    for event in all_events:
        current_count = len(event_assignments[event])
        if current_count < swimmers_per_event:
            print(f"Warning: {event} only has {current_count} swimmers (target: {swimmers_per_event})")
    
    return pd.DataFrame(lineup_data)


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
    SWIMMERS_PER_EVENT = 4  # Changed to 4 as required
    
    try:
        # Load the Excel file into a DataFrame first
        times_df = pd.read_excel(filename)
        print(f"→ Loaded {len(times_df)} swimmers from Excel file")
        print(f"→ Columns in file: {list(times_df.columns)}")
        
        # Now call round_robin_assignment with the pivot table data
        print(f"→ Optimizing lineup: {SWIMMERS_PER_EVENT} swimmers per event, max {MAX_EVENTS_PER_SWIMMER} events per swimmer")
        lineup_df = round_robin_assignment(
            times_df, 
            max_events_per_swimmer=MAX_EVENTS_PER_SWIMMER, 
            swimmers_per_event=SWIMMERS_PER_EVENT
        )
                        
    except Exception as e:
        print(f"Error in round_robin_assignment: {e}")
        import traceback
        traceback.print_exc()
        return

    # 6) Create CSV output filename with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    csv_filename = f"lineup_{team_name.replace(' ', '_')}_{gender}_{year}_{timestamp}.csv"
    
    # 7) Prepare enhanced lineup data for CSV export
    csv_data = []
    events = lineup_df['Event'].unique()
    
    for event in events:
        event_swimmers = lineup_df[lineup_df['Event'] == event].copy()
        
        # Sort by time (convert to seconds for proper sorting)
        event_swimmers['Time_Seconds'] = event_swimmers['Time'].apply(time_to_seconds)
        event_swimmers = event_swimmers.sort_values('Time_Seconds')
        
        # Calculate event statistics
        times_in_seconds = event_swimmers['Time_Seconds'].tolist()
        
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
        event_swimmers = lineup_df[lineup_df['Event'] == event].copy()
        event_swimmers['Time_Seconds'] = event_swimmers['Time'].apply(time_to_seconds)
        event_swimmers = event_swimmers.sort_values('Time_Seconds')
        
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