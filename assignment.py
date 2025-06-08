# assignment.py

import pandas as pd
from utils import time_to_seconds, pivot_to_long_format
from itertools import product, combinations
from collections import defaultdict


def create_relay_teams(times_df, relay_events, max_total_events=4):
    """
    Build A/B relays for each selected relay_event.
    Returns DataFrame with 'Relay', 'Leg', 'Swimmer', 'Time' columns
    """
    print(f"\n→ Creating relay teams for: {relay_events}")
    relay_lineups = []
    swimmer_relay_counts = defaultdict(int)

    for relay_event in relay_events:
        print(f"→ Processing {relay_event}…")
        
        # Define strokes and names for each relay type
        if relay_event == '200 Medley Relay':
            strokes = ['50 back', '50 breast', '50 fly', '50 free']
            names = ['Backstroke', 'Breaststroke', 'Butterfly', 'Freestyle']
        elif relay_event == '400 Medley Relay':
            strokes = ['100 back', '100 breast', '100 fly', '100 free']
            names = ['Backstroke', 'Breaststroke', 'Butterfly', 'Freestyle']
        elif relay_event == '200 Free Relay':
            strokes = ['50 free'] * 4
            names = [f'Leg {i+1}' for i in range(4)]
        elif relay_event == '400 Free Relay':
            strokes = ['100 free'] * 4
            names = [f'Leg {i+1}' for i in range(4)]
        else:
            print(f"Unknown relay event: {relay_event}")
            continue

        # Build stroke→[(Swimmer, Time_secs), ...] mapping
        stroke_swimmers = {}
        for stroke, name in zip(strokes, names):
            if stroke not in times_df.columns:
                print(f"Warning: {stroke} not in data columns")
                stroke_swimmers[name] = []
                continue
                
            # Get swimmers with valid times for this stroke
            stroke_data = times_df[['Swimmer', stroke]].copy()
            stroke_data = stroke_data.dropna()
            stroke_data = stroke_data[stroke_data[stroke] != '']
            
            if stroke_data.empty:
                print(f"Warning: No swimmers found for {stroke}")
                stroke_swimmers[name] = []
                continue
            
            # Convert times to seconds and sort
            stroke_data['Time_secs'] = stroke_data[stroke].apply(time_to_seconds)
            stroke_data = stroke_data[stroke_data['Time_secs'] != float('inf')]
            stroke_data = stroke_data.sort_values('Time_secs')
            
            stroke_swimmers[name] = [(row['Swimmer'], row[stroke], row['Time_secs']) 
                                   for _, row in stroke_data.iterrows()]
            
            print(f"  {name}: {len(stroke_swimmers[name])} swimmers available")

        # Check if we have enough swimmers for at least one relay
        min_swimmers = min(len(swimmers) for swimmers in stroke_swimmers.values())
        if min_swimmers < 1:
            print(f"  Cannot form {relay_event} - insufficient swimmers")
            continue

        # For freestyle relays, we need to prevent the same swimmer swimming multiple legs
        if relay_event in ['200 Free Relay', '400 Free Relay']:
            # Get all swimmers sorted by their freestyle time
            all_free_swimmers = stroke_swimmers['Leg 1']  # All legs have same swimmers for free relays
            
            # Create A and B relays with different swimmers per leg
            relays_to_create = min(2, len(all_free_swimmers) // 4)  # Need 4 different swimmers per relay
            
            used_swimmers = set()
            
            for relay_num in range(relays_to_create):
                relay_name = f"{relay_event} {'A' if relay_num == 0 else 'B'}"
                
                # Find 4 fastest available swimmers for this relay
                relay_swimmers = []
                for swimmer, time_str, time_secs in all_free_swimmers:
                    if swimmer not in used_swimmers and len(relay_swimmers) < 4:
                        relay_swimmers.append((swimmer, time_str, time_secs))
                        used_swimmers.add(swimmer)
                
                if len(relay_swimmers) == 4:
                    # Add each swimmer to a different leg
                    for i, (swimmer, time_str, time_secs) in enumerate(relay_swimmers):
                        relay_lineups.append({
                            'Relay': relay_name,
                            'Leg': f'Leg {i+1}',
                            'Swimmer': swimmer,
                            'Time': time_str
                        })
                        
                        # Only count relay participation once per relay, not per leg
                        if i == 0:  # Only increment on first leg
                            swimmer_relay_counts[swimmer] += 1
                    
                    swimmers_list = [swimmer for swimmer, _, _ in relay_swimmers]
                    print(f"  Created {relay_name}: {', '.join(swimmers_list)}")
                else:
                    print(f"  Cannot create {relay_name} - need 4 different swimmers, only have {len(relay_swimmers)}")
        
        else:
            # For medley relays, use original logic (different strokes)
            relays_to_create = min(2, min_swimmers)  # A and B relay
            
            for relay_num in range(relays_to_create):
                relay_name = f"{relay_event} {'A' if relay_num == 0 else 'B'}"
                
                # Add each swimmer as a separate row with their leg/stroke
                for i, name in enumerate(names):
                    if len(stroke_swimmers[name]) > relay_num:
                        swimmer, time_str, time_secs = stroke_swimmers[name][relay_num]
                        
                        relay_lineups.append({
                            'Relay': relay_name,
                            'Leg': name,
                            'Swimmer': swimmer,
                            'Time': time_str
                        })
                        
                        # Only count relay participation once per relay, not per leg
                        if i == 0:  # Only increment on first leg to avoid counting 4 times
                            swimmer_relay_counts[swimmer] += 1
                    else:
                        # Not enough swimmers for this relay
                        break
                
                # Check if we successfully created a complete relay (4 legs)
                current_relay_legs = [entry for entry in relay_lineups if entry['Relay'] == relay_name]
                if len(current_relay_legs) == 4:
                    swimmers_list = [entry['Swimmer'] for entry in current_relay_legs]
                    print(f"  Created {relay_name}: {', '.join(swimmers_list)}")
                else:
                    # Remove incomplete relay
                    relay_lineups = [entry for entry in relay_lineups if entry['Relay'] != relay_name]

    return pd.DataFrame(relay_lineups), dict(swimmer_relay_counts)


def round_robin_assignment(times_df, max_events_per_swimmer=4,
                           swimmers_per_event=4, swimmer_relay_counts=None):
    """
    Balanced individual assignment, considering relay loads.
    """
    if times_df.empty:
        print("No individual lineup generated.")
        return pd.DataFrame(), {}
    
    if swimmer_relay_counts is None:
        swimmer_relay_counts = {}

    # Convert to long format if needed
    if 'Event' not in times_df.columns:
        print("→ Converting wide to long format…")
        times_df = pivot_to_long_format(times_df)
    
    if times_df.empty:
        print("No individual lineup generated.")
        return pd.DataFrame(), {}

    # Get all available events
    available_events = times_df['Event'].unique()
    print(f"Available events for assignment: {list(available_events)}")
    
    # Initialize tracking
    swimmer_event_counts = defaultdict(int)
    event_assignments = defaultdict(list)
    lineup_results = []
    
    # Add relay counts to swimmer event counts
    for swimmer, count in swimmer_relay_counts.items():
        swimmer_event_counts[swimmer] += count
    
    # Process each event
    for event in available_events:
        event_data = times_df[times_df['Event'] == event].copy()
        event_data['Time_secs'] = event_data['Time'].apply(time_to_seconds)
        event_data = event_data[event_data['Time_secs'] != float('inf')]
        event_data = event_data.sort_values('Time_secs')
        
        assigned_count = 0
        for _, row in event_data.iterrows():
            swimmer = row['Swimmer']
            
            # Check if swimmer can take another event
            if (swimmer_event_counts[swimmer] < max_events_per_swimmer and 
                assigned_count < swimmers_per_event):
                
                lineup_results.append({
                    'Event': event,
                    'Swimmer': swimmer,
                    'Time': row['Time'],
                    'Place': assigned_count + 1
                })
                
                swimmer_event_counts[swimmer] += 1
                assigned_count += 1
                
                if assigned_count >= swimmers_per_event:
                    break
        
        print(f"  {event}: Assigned {assigned_count} swimmers")
    
    return pd.DataFrame(lineup_results), dict(swimmer_event_counts)


def strategic_dual_meet_assignment(user_times_df, opponent_times_df,
                                   max_events_per_swimmer=4,
                                   swimmers_per_event=4,
                                   swimmer_relay_counts=None, relay_events=None):
    """
    Maximize points against opponent.
    """
    if user_times_df.empty:
        print("No user data for strategic assignment")
        return pd.DataFrame(), {}
    
    if opponent_times_df.empty:
        print("No opponent data - falling back to round robin")
        return round_robin_assignment(user_times_df, max_events_per_swimmer,
                                      swimmers_per_event, swimmer_relay_counts)

    if swimmer_relay_counts is None:
        swimmer_relay_counts = {}

    # Convert both to long format if needed
    if 'Event' not in user_times_df.columns:
        user_times_df = pivot_to_long_format(user_times_df)
    if 'Event' not in opponent_times_df.columns:
        opponent_times_df = pivot_to_long_format(opponent_times_df)

    # Get common events
    user_events = set(user_times_df['Event'].unique())
    opp_events = set(opponent_times_df['Event'].unique())
    common_events = user_events.intersection(opp_events)
    
    print(f"Strategic assignment for {len(common_events)} common events")
    
    # Initialize tracking
    swimmer_event_counts = defaultdict(int)
    lineup_results = []
    
    # Add relay counts
    for swimmer, count in swimmer_relay_counts.items():
        swimmer_event_counts[swimmer] += count
    
    # Process each event strategically
    for event in common_events:
        user_event_data = user_times_df[user_times_df['Event'] == event].copy()
        opp_event_data = opponent_times_df[opponent_times_df['Event'] == event].copy()
        
        # Convert times to seconds for comparison
        user_event_data['Time_secs'] = user_event_data['Time'].apply(time_to_seconds)
        opp_event_data['Time_secs'] = opp_event_data['Time'].apply(time_to_seconds)
        
        # Remove invalid times
        user_event_data = user_event_data[user_event_data['Time_secs'] != float('inf')]
        opp_event_data = opp_event_data[opp_event_data['Time_secs'] != float('inf')]
        
        if user_event_data.empty:
            continue
        
        # Sort by time
        user_event_data = user_event_data.sort_values('Time_secs')
        opp_event_data = opp_event_data.sort_values('Time_secs')
        
        # Get opponent times for scoring calculation
        opp_times = list(opp_event_data['Time_secs'])
        
        # Assign up to swimmers_per_event swimmers strategically
        assigned_count = 0
        for _, row in user_event_data.iterrows():
            swimmer = row['Swimmer']
            time_secs = row['Time_secs']
            
            if (swimmer_event_counts[swimmer] < max_events_per_swimmer and 
                assigned_count < swimmers_per_event):
                
                # Calculate expected place against opponents
                place = 1 + sum(1 for opp_time in opp_times if opp_time < time_secs)
                
                lineup_results.append({
                    'Event': event,
                    'Swimmer': swimmer,
                    'Time': row['Time'],
                    'Place': assigned_count + 1,
                    'Expected_Place': place
                })
                
                swimmer_event_counts[swimmer] += 1
                assigned_count += 1
                
                if assigned_count >= swimmers_per_event:
                    break
        
        print(f"  {event}: Assigned {assigned_count} swimmers")
    
    return pd.DataFrame(lineup_results), dict(swimmer_event_counts)


def analyze_event_scenarios(user_swimmers, opponent_swimmers, event_name, relay_events):
    """
    Evaluate place-point scenarios for one event.
    """
    # Simple scenario analysis - can be expanded
    scenarios = {}
    
    if not user_swimmers or not opponent_swimmers:
        return scenarios
    
    # Calculate potential points for different swimmer combinations
    user_times = [time_to_seconds(s[1]) for s in user_swimmers]
    opp_times = [time_to_seconds(s[1]) for s in opponent_swimmers]
    
    # Dual meet scoring: 1st=5pts, 2nd=3pts, 3rd=1pt
    point_values = [5, 3, 1]
    
    for i, (swimmer, time_str) in enumerate(user_swimmers[:3]):
        time_secs = time_to_seconds(time_str)
        place = 1 + sum(1 for opp_time in opp_times if opp_time < time_secs)
        
        if place <= 3:
            points = point_values[place - 1]
        else:
            points = 0
            
        scenarios[swimmer] = {
            'time': time_str,
            'expected_place': place,
            'expected_points': points
        }
    
    return scenarios


def create_strategic_relay_teams(user_times_df, opponent_times_df, relay_events,
                                 max_total_events=4):
    """
    Choose relays to out-point opponent relays.
    """
    print(f"\n→ Strategic relay planning for: {relay_events}")
    
    # For now, use the same logic as regular relay creation
    # This can be enhanced to compare against opponent relay times
    user_relay_df, user_relay_counts = create_relay_teams(user_times_df, relay_events, max_total_events)
    
    # Could add opponent analysis here to optimize relay composition
    
    return user_relay_df, user_relay_counts


def find_optimal_relay_combinations(stroke_swimmers, stroke_names,
                                    opponent_relay_times, current_relay_counts, max_events):
    """
    Brute-force best A/B relay pairs.
    """
    best_combinations = []
    
    # This is a simplified version - can be expanded for more sophisticated optimization
    for stroke_name in stroke_names:
        if stroke_name in stroke_swimmers:
            available_swimmers = stroke_swimmers[stroke_name]
            
            # Filter swimmers who haven't exceeded event limits
            valid_swimmers = [
                (swimmer, time_secs) for swimmer, time_secs in available_swimmers
                if current_relay_counts.get(swimmer, 0) < max_events
            ]
            
            if valid_swimmers:
                best_combinations.append(valid_swimmers[0])  # Take the fastest available
    
    return best_combinations