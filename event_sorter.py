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


def get_user_event_preferences():
    """
    Get user preferences for distance and IM events
    """
    print("\n=== EVENT SELECTION ===")
    
    # Distance Event Selection
    print("\nDistance Event Options:")
    print("1. 1650 Free only")
    print("2. 1000 Free only")
    print("3. Both 1650 and 1000 Free")
    
    while True:
        distance_choice = input("Choose distance events (1-3): ").strip()
        if distance_choice in ['1', '2', '3']:
            break
        print("Please enter 1, 2, or 3")
    
    # IM Event Selection
    print("\nIndividual Medley Event Options:")
    print("1. 200 IM only")
    print("2. 400 IM only") 
    print("3. Both 200 IM and 400 IM")
    
    while True:
        im_choice = input("Choose IM events (1-3): ").strip()
        if im_choice in ['1', '2', '3']:
            break
        print("Please enter 1, 2, or 3")
    
    # Convert choices to event lists
    distance_events = []
    if distance_choice == '1':
        distance_events = ['1650 free']
    elif distance_choice == '2':
        distance_events = ['1000 free']
    else:  # choice == '3'
        distance_events = ['1650 free', '1000 free']
    
    im_events = []
    if im_choice == '1':
        im_events = ['200 IM']
    elif im_choice == '2':
        im_events = ['400 IM']
    else:  # choice == '3'
        im_events = ['200 IM', '400 IM']
    
    return distance_events, im_events


def get_user_relay_preferences():
    """
    Get user preferences for relay events
    """
    print("\n=== RELAY SELECTION ===")
    print("Relay Event Options:")
    print("1. 200 Medley Relay and 200 Free Relay")
    print("2. 200 Medley Relay and 400 Free Relay")
    print("3. 400 Medley Relay and 200 Free Relay")
    print("4. All Relays (200 Medley, 400 Medley, 200 Free, 400 Free)")
    
    while True:
        relay_choice = input("Choose relay events (1-4): ").strip()
        if relay_choice in ['1', '2', '3', '4']:
            break
        print("Please enter 1, 2, 3, or 4")
    
    # Convert choice to relay list
    relay_events = []
    if relay_choice == '1':
        relay_events = ['200 Medley Relay', '200 Free Relay']
    elif relay_choice == '2':
        relay_events = ['200 Medley Relay', '400 Free Relay']
    elif relay_choice == '3':
        relay_events = ['400 Medley Relay', '200 Free Relay']
    else:  # choice == '4'
        relay_events = ['200 Medley Relay', '400 Medley Relay', '200 Free Relay', '400 Free Relay']
    
    return relay_events


def get_scraper_event_codes(distance_events, im_events):
    """
    Convert user-selected events to scraper event codes
    Note: We always scrape all stroke events for relay formation
    """
    # All events needed for both individual and relay lineups
    all_event_codes = [
        '50_free', '100_free', '200_free', '500_free',
        '50_back', '100_back', '200_back',
        '50_breast', '100_breast', '200_breast',
        '50_fly', '100_fly', '200_fly'
    ]
    
    # Map distance events to scraper codes
    for event in distance_events:
        if event == '1650 free':
            all_event_codes.append('1650_free')
        elif event == '1000 free':
            all_event_codes.append('1000_free')
    
    # Map IM events to scraper codes
    for event in im_events:
        if event == '200 IM':
            all_event_codes.append('200_im')
        elif event == '400 IM':
            all_event_codes.append('400_im')
    
    print(f"→ Events to scrape: {all_event_codes}")
    return all_event_codes


def filter_events_by_preferences(times_df, distance_events, im_events):
    """
    Filter the times DataFrame to only include selected events for INDIVIDUAL lineup
    Excludes 50 back, breast, and fly from individual events (kept for relays)
    """
    # Standard individual events (excluding 50 back, breast, fly)
    standard_events = [
        '50 free', '100 free', '200 free', '500 free',
        '100 back', '200 back',
        '100 breast', '200 breast', 
        '100 fly', '200 fly'
    ]
    
    # Combine all selected events for individual lineup
    selected_events = standard_events + distance_events + im_events
    
    print(f"\n→ Selected events for individual lineup: {selected_events}")
    
    # If we're working with pivot table format, filter columns
    if 'Event' not in times_df.columns:
        # This is pivot format - filter columns
        available_columns = [col for col in times_df.columns if col != 'Swimmer']
        filtered_columns = ['Swimmer'] + [col for col in available_columns if col in selected_events]
        
        print(f"→ Available events in data: {available_columns}")
        print(f"→ Filtered to columns: {filtered_columns}")
        
        return times_df[filtered_columns]
    else:
        # This is long format - filter rows
        filtered_df = times_df[times_df['Event'].isin(selected_events)].copy()
        print(f"→ Filtered from {len(times_df)} to {len(filtered_df)} swimmer-event combinations")
        return filtered_df


def create_relay_teams(times_df, relay_events, max_total_events=4):
    """
    Create relay teams from swimmer times data
    Creates 2 teams per relay type (A and B relays)
    Returns relay assignments and swimmer event counts
    """
    print(f"\n→ Creating relay teams for: {relay_events}")
    
    relay_lineups = []
    swimmer_relay_counts = {}  # Track how many relays each swimmer is in
    
    for relay_event in relay_events:
        print(f"\n→ Processing {relay_event}...")
        
        if relay_event == '200 Medley Relay':
            # Order: Back, Breast, Fly, Free
            stroke_events = ['50 back', '50 breast', '50 fly', '50 free']
            stroke_names = ['Backstroke', 'Breaststroke', 'Butterfly', 'Freestyle']
        elif relay_event == '400 Medley Relay':
            # Order: Back, Breast, Fly, Free
            stroke_events = ['100 back', '100 breast', '100 fly', '100 free']
            stroke_names = ['Backstroke', 'Breaststroke', 'Butterfly', 'Freestyle']
        elif relay_event == '200 Free Relay':
            # All freestyle
            stroke_events = ['50 free', '50 free', '50 free', '50 free']
            stroke_names = ['Leg 1', 'Leg 2', 'Leg 3', 'Leg 4']
        elif relay_event == '400 Free Relay':
            # All freestyle
            stroke_events = ['100 free', '100 free', '100 free', '100 free']
            stroke_names = ['Leg 1', 'Leg 2', 'Leg 3', 'Leg 4']
        else:
            continue
        
        # Get swimmers for each stroke/leg
        stroke_swimmers = {}
        
        for i, stroke_event in enumerate(stroke_events):
            stroke_name = stroke_names[i]
            
            # Get all swimmers who have times for this stroke
            if 'Event' in times_df.columns:
                # Long format
                stroke_data = times_df[times_df['Event'] == stroke_event].copy()
                if not stroke_data.empty:
                    stroke_data['Time_Seconds'] = stroke_data['Time'].apply(time_to_seconds)
                    stroke_data = stroke_data[stroke_data['Time_Seconds'] != float('inf')]
                    stroke_data = stroke_data.sort_values('Time_Seconds')
                    stroke_swimmers[stroke_name] = stroke_data[['Swimmer', 'Time']].values.tolist()
            else:
                # Pivot format
                if stroke_event in times_df.columns:
                    stroke_data = times_df[['Swimmer', stroke_event]].copy()
                    stroke_data = stroke_data.dropna(subset=[stroke_event])
                    stroke_data['Time_Seconds'] = stroke_data[stroke_event].apply(time_to_seconds)
                    stroke_data = stroke_data[stroke_data['Time_Seconds'] != float('inf')]
                    stroke_data = stroke_data.sort_values('Time_Seconds')
                    stroke_swimmers[stroke_name] = [[row['Swimmer'], row[stroke_event]] for _, row in stroke_data.iterrows()]
        
        # Create A and B relay teams
        for team_letter in ['A', 'B']:
            team_name = f"{relay_event} {team_letter}"
            relay_team = []
            used_swimmers = set()  # Track swimmers already used in this relay
            
            # Assign swimmers to each leg/stroke
            for stroke_name in stroke_names:
                assigned = False
                
                if stroke_name in stroke_swimmers:
                    # Try to assign best available swimmer not already used
                    for swimmer_data in stroke_swimmers[stroke_name]:
                        swimmer_name = swimmer_data[0]
                        swimmer_time = swimmer_data[1]
                        
                        # Check if swimmer is already used in this relay
                        if swimmer_name in used_swimmers:
                            continue
                        
                        # Check if adding this relay would exceed max events
                        current_relay_count = swimmer_relay_counts.get(swimmer_name, 0)
                        if current_relay_count >= max_total_events:
                            continue
                        
                        # Assign this swimmer
                        relay_team.append({
                            'Relay': team_name,
                            'Leg': stroke_name,
                            'Swimmer': swimmer_name,
                            'Time': swimmer_time
                        })
                        used_swimmers.add(swimmer_name)
                        swimmer_relay_counts[swimmer_name] = current_relay_count + 1
                        assigned = True
                        break
                
                # If no swimmer assigned (not enough swimmers), leave empty
                if not assigned:
                    relay_team.append({
                        'Relay': team_name,
                        'Leg': stroke_name,
                        'Swimmer': 'TBD',
                        'Time': 'N/A'
                    })
            
            relay_lineups.extend(relay_team)
            
            # Remove assigned swimmers from available pools for B relay
            if team_letter == 'A':
                for stroke_name in stroke_names:
                    if stroke_name in stroke_swimmers:
                        # Remove swimmers used in A relay
                        stroke_swimmers[stroke_name] = [
                            swimmer_data for swimmer_data in stroke_swimmers[stroke_name]
                            if swimmer_data[0] not in used_swimmers
                        ]
    
    return pd.DataFrame(relay_lineups), swimmer_relay_counts


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


def round_robin_assignment(times_df, max_events_per_swimmer=4, swimmers_per_event=4, swimmer_relay_counts=None):
    """
    Assign swimmers to events using round-robin approach for balanced talent distribution
    Now considers relay participation when calculating max events per swimmer
    """
    if times_df.empty:
        raise Exception("No swimmer data provided")
    
    # Initialize relay counts if not provided
    if swimmer_relay_counts is None:
        swimmer_relay_counts = {}
    
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
    swimmer_individual_counts = {}
    
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
    
    print("→ Starting round-robin assignment with relay consideration...")
    
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
                
                # Calculate total events for this swimmer (individual + relay)
                current_individual_events = swimmer_individual_counts.get(swimmer, 0)
                current_relay_events = swimmer_relay_counts.get(swimmer, 0)
                total_events = current_individual_events + current_relay_events
                
                # Check if swimmer is available (hasn't reached max total events)
                if total_events >= max_events_per_swimmer:
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
                swimmer_individual_counts[best_swimmer['Swimmer']] = swimmer_individual_counts.get(best_swimmer['Swimmer'], 0) + 1
                # Remove this pair so it's not considered again
                swimmer_event_pairs.pop(best_pair_idx)
                assignments_made = True
                
                swimmer_name = best_swimmer['Swimmer']
                total_events = swimmer_individual_counts[swimmer_name] + swimmer_relay_counts.get(swimmer_name, 0)
                print(f"→ Assigned {swimmer_name} to {current_event} (Time: {best_swimmer['Time']}, Total Events: {total_events})")
        
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
    
    return pd.DataFrame(lineup_data), swimmer_individual_counts


def main():
    print("=== Dual Meet Lineup Builder ===")

    # 1) Ask for user inputs
    team_name = input("Enter the college/team name: ").strip()
    year_input = input("Enter year [default = 2025]: ").strip()
    year = int(year_input) if year_input else 2025
    gender_input = input("Enter gender (M/F): ").strip().upper()
    gender = gender_input if gender_input in ("M", "F") else "M"

    # 2) Get user event preferences
    distance_events, im_events = get_user_event_preferences()
    relay_events = get_user_relay_preferences()
    
    print(f"\n→ Selected distance events: {distance_events}")
    print(f"→ Selected IM events: {im_events}")
    print(f"→ Selected relay events: {relay_events}")

    # 3) Convert user preferences to scraper event codes (includes all events for relays)
    events_to_scrape = get_scraper_event_codes(distance_events, im_events)

    # 4) Where the JSON lives (relative to this file)
    mappings_file = "Scraper/maps/team_mappings/all_college_teams.json"
    # 5) Where we will write the raw swimmer‐times Excel
    filename = "swimmer_times.xlsx"

    # 6) Scrape and save all events (including those needed for relays)
    try:
        print(f"→ Scraping SwimCloud for {team_name} ({gender}, {year}) using mappings from {mappings_file}...")
        scrape_and_save(
            team_name=team_name,
            year=year,
            gender=gender,
            filename=filename,
            mappings_file=mappings_file,
            selected_events=events_to_scrape
        )
    except Exception as e:
        print(f"Error during scraping: {e}")
        return

    # 7) Load the Excel file and process relay and individual lineups
    print(f"→ Processing lineup optimization from '{filename}'...")
    
    # Configuration for lineup optimization
    MAX_TOTAL_EVENTS_PER_SWIMMER = 4  # Total events including relays
    SWIMMERS_PER_EVENT = 4
    
    try:
        # Load the Excel file into a DataFrame first
        times_df = pd.read_excel(filename)
        print(f"→ Loaded {len(times_df)} swimmers from Excel file")
        print(f"→ Columns in file: {list(times_df.columns)}")
        
        # Create relay lineups first (using all data including 50 strokes)
        # This gives us a count of how many relay events each swimmer is in
        relay_lineup_df, swimmer_relay_counts = create_relay_teams(
            times_df, 
            relay_events, 
            max_total_events=MAX_TOTAL_EVENTS_PER_SWIMMER
        )
        print(f"→ Created {len(relay_lineup_df)} relay assignments")
        print(f"→ Relay participation counts: {swimmer_relay_counts}")
        
        # Filter events for individual lineup (excludes 50 back, breast, fly)
        individual_times_df = filter_events_by_preferences(times_df, distance_events, im_events)
        print(f"→ Filtered data shape for individual events: {individual_times_df.shape}")
        
        # Create individual lineup considering relay participation
        print(f"→ Optimizing individual lineup: {SWIMMERS_PER_EVENT} swimmers per event, max {MAX_TOTAL_EVENTS_PER_SWIMMER} total events per swimmer (including relays)")
        individual_lineup_df, swimmer_individual_counts = round_robin_assignment(
            individual_times_df, 
            max_events_per_swimmer=MAX_TOTAL_EVENTS_PER_SWIMMER, 
            swimmers_per_event=SWIMMERS_PER_EVENT,
            swimmer_relay_counts=swimmer_relay_counts
        )
                        
    except Exception as e:
        print(f"Error in lineup processing: {e}")
        import traceback
        traceback.print_exc()
        return

    # 8) Create CSV output filenames with timestamp and event selection info
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Create event selection suffix
    distance_suffix = ""
    if len(distance_events) == 1:
        distance_suffix = distance_events[0].replace(" ", "").replace("free", "")
    else:
        distance_suffix = "1650_1000"
    
    im_suffix = ""
    if len(im_events) == 1:
        im_suffix = im_events[0].replace(" ", "").replace("IM", "IM")
    else:
        im_suffix = "200_400IM"
    
    relay_suffix = f"relays_{len(relay_events)}"
    
    # Individual lineup CSV
    individual_csv_filename = f"individual_lineup_{team_name.replace(' ', '_')}_{gender}_{year}_{distance_suffix}_{im_suffix}_{timestamp}.csv"
    
    # Relay lineup CSV
    relay_csv_filename = f"relay_lineup_{team_name.replace(' ', '_')}_{gender}_{year}_{relay_suffix}_{timestamp}.csv"
    
    # 9) Prepare enhanced individual lineup data for CSV export
    individual_csv_data = []
    individual_events = individual_lineup_df['Event'].unique() if not individual_lineup_df.empty else []
    
    for event in individual_events:
        event_swimmers = individual_lineup_df[individual_lineup_df['Event'] == event].copy()
        
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
            individual_csv_data.append({
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
    
    # 10) Save individual lineup CSV
    if individual_csv_data:
        individual_csv_df = pd.DataFrame(individual_csv_data)
        individual_csv_df.to_csv(individual_csv_filename, index=False)
        print(f"→ Individual lineup saved to CSV: {individual_csv_filename}")
    
    # 11) Save relay lineup CSV
    if not relay_lineup_df.empty:
        relay_lineup_df.to_csv(relay_csv_filename, index=False)
        print(f"→ Relay lineup saved to CSV: {relay_csv_filename}")
    
    # 12) Create summary CSV with team-level statistics
    summary_filename = f"lineup_summary_{team_name.replace(' ', '_')}_{gender}_{year}_{distance_suffix}_{im_suffix}_{relay_suffix}_{timestamp}.csv"
    
    # Calculate total event distribution (individual + relay)
    swimmer_total_counts = {}
    for swimmer, individual_count in swimmer_individual_counts.items():
        relay_count = swimmer_relay_counts.get(swimmer, 0)
        swimmer_total_counts[swimmer] = individual_count + relay_count
    
    # Add swimmers who are only in relays
    for swimmer, relay_count in swimmer_relay_counts.items():
        if swimmer not in swimmer_total_counts:
            swimmer_total_counts[swimmer] = relay_count
    
    total_counts_series = pd.Series(swimmer_total_counts)
    
    summary_data = {
        'Team': [team_name],
        'Gender': [gender],
        'Year': [year],
        'Distance_Events': [', '.join(distance_events)],
        'IM_Events': [', '.join(im_events)],
        'Relay_Events': [', '.join(relay_events)],
        'Total_Individual_Events': [len(individual_events)],
        'Total_Individual_Entries': [len(individual_lineup_df)],
        'Total_Relay_Entries': [len(relay_lineup_df)],
        'Swimmers_4_Total_Events': [sum(total_counts_series == 4)],
        'Swimmers_3_Total_Events': [sum(total_counts_series == 3)],
        'Swimmers_2_Total_Events': [sum(total_counts_series == 2)],
        'Swimmers_1_Total_Event': [sum(total_counts_series == 1)],
        'Generated_At': [datetime.now().strftime("%Y-%m-%d %H:%M:%S")]
    }
    
    summary_df = pd.DataFrame(summary_data)
    summary_df.to_csv(summary_filename, index=False)
    print(f"→ Summary saved to CSV: {summary_filename}")

    # 13) Print out the assignment for each event (console output)
    print("\n=== DUAL MEET LINEUP ===")
    print(f"Distance Events: {', '.join(distance_events)}")
    print(f"IM Events: {', '.join(im_events)}")
    print(f"Relay Events: {', '.join(relay_events)}")
    
    # Print individual events
    print(f"\n=== INDIVIDUAL EVENTS ===")
    for event in individual_events:
        event_swimmers = individual_lineup_df[individual_lineup_df['Event'] == event].copy()
        event_swimmers['Time_Seconds'] = event_swimmers['Time'].apply(time_to_seconds)
        event_swimmers = event_swimmers.sort_values('Time_Seconds')
        
        print(f"\n{event}:")
        
        for i, (_, row) in enumerate(event_swimmers.iterrows(), 1):
            swimmer_name = row['Swimmer']
            total_events = swimmer_total_counts.get(swimmer_name, 0)
            print(f"  {i}. {swimmer_name:<25}  {row['Time']:<10} (Total Events: {total_events})")
    
    # Print relay events
    if not relay_lineup_df.empty:
        print(f"\n=== RELAY EVENTS ===")
        relay_teams = relay_lineup_df['Relay'].unique()
        
        for relay_team in relay_teams:
            team_swimmers = relay_lineup_df[relay_lineup_df['Relay'] == relay_team]
            print(f"\n{relay_team}:")
            
            for _, row in team_swimmers.iterrows():
                swimmer_name = row['Swimmer']
                total_events = swimmer_total_counts.get(swimmer_name, 0) if swimmer_name != 'TBD' else 0
                event_info = f" (Total Events: {total_events})" if swimmer_name != 'TBD' else ""
                print(f"  {row['Leg']:<12}: {swimmer_name:<25}  {row['Time']:<10}{event_info}")
    
    # 14) Display summary statistics
    print(f"\n=== LINEUP SUMMARY ===")
    print(f"Individual Events: {len(individual_events)}")
    print
    print(f"Individual Entries: {len(individual_lineup_df)}")
    print(f"Relay Events: {len(relay_events)}")
    print(f"Relay Entries: {len(relay_lineup_df)}")
    print(f"Total Swimmers Used: {len(swimmer_total_counts)}")
    print(f"Swimmers with 4 Total Events: {sum(total_counts_series == 4)}")
    print(f"Swimmers with 3 Total Events: {sum(total_counts_series == 3)}")
    print(f"Swimmers with 2 Total Events: {sum(total_counts_series == 2)}")
    print(f"Swimmers with 1 Total Event: {sum(total_counts_series == 1)}")
    
    # 15) Display event distribution
    if len(swimmer_total_counts) > 0:
        print(f"\n=== EVENT DISTRIBUTION ===")
        for swimmer, total_events in sorted(swimmer_total_counts.items(), key=lambda x: (-x[1], x[0])):
            individual_events = swimmer_individual_counts.get(swimmer, 0)
            relay_events_count = swimmer_relay_counts.get(swimmer, 0)
            print(f"{swimmer:<25}: {total_events} total ({individual_events} individual + {relay_events_count} relay)")
    
    print(f"\n=== FILES GENERATED ===")
    if individual_csv_data:
        print(f"Individual Lineup: {individual_csv_filename}")
    if not relay_lineup_df.empty:
        print(f"Relay Lineup: {relay_csv_filename}")
    print(f"Summary: {summary_filename}")
    print(f"Raw Data: {filename}")
    
    print("\n=== LINEUP BUILDER COMPLETE ===")


if __name__ == "__main__":
    main()