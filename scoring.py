# scoring.py

import pandas as pd
from utils import time_to_seconds


def calculate_individual_points_vs_opponent(our_time, opponent_times):
    """
    Individual scoring 9-4-3-2-1-0 for places 1–6.
    """
    if not opponent_times:
        return 9
    
    our_time_secs = time_to_seconds(our_time) if isinstance(our_time, str) else float(our_time)
    opp_times_secs = []
    
    for t in opponent_times:
        if isinstance(t, str):
            time_secs = time_to_seconds(t)
        else:
            time_secs = float(t)
        if time_secs != float('inf'):
            opp_times_secs.append(time_secs)
    
    if not opp_times_secs or our_time_secs == float('inf'):
        return 0 if our_time_secs == float('inf') else 9
        
    beaten = sum(1 for t in opp_times_secs if our_time_secs < t)
    opp_n = len(opp_times_secs)
    
    if beaten == opp_n:           return 9
    if beaten >= opp_n - 1:       return 4
    if beaten >= opp_n - 2:       return 3
    if beaten >= opp_n - 3:       return 2
    if beaten >= opp_n - 4:       return 1
    return 0


def calculate_relay_times(relay_df):
    """
    Calculate total relay times by summing individual leg times.
    Returns dict of {relay_name: total_time_seconds}
    """
    relay_times = {}
    
    if relay_df.empty or 'Relay' not in relay_df.columns:
        return relay_times
    
    # Group by relay name
    for relay_name in relay_df['Relay'].unique():
        relay_legs = relay_df[relay_df['Relay'] == relay_name]
        total_time = 0
        valid_relay = True
        
        for _, leg in relay_legs.iterrows():
            if 'Time' not in leg:
                valid_relay = False
                break
                
            leg_time_secs = time_to_seconds(leg['Time'])
            if leg_time_secs == float('inf'):
                valid_relay = False
                break
            total_time += leg_time_secs
        
        if valid_relay and total_time > 0:
            # Remove A/B designation for comparison
            base_relay_name = relay_name.replace(' A', '').replace(' B', '')
            if base_relay_name not in relay_times:
                relay_times[base_relay_name] = {}
            
            team_letter = 'A' if ' A' in relay_name else 'B' if ' B' in relay_name else 'A'
            relay_times[base_relay_name][team_letter] = total_time
    
    return relay_times


def calculate_relay_points_vs_opponent(our_relay_times, opponent_relay_times):
    """
    Relay scoring 11-4-2-0 for places 1–4.
    Compare our best relay time against opponent's best relay time.
    """
    if not opponent_relay_times:
        return 11 if our_relay_times else 0
    
    # Get our best time (A or B relay)
    our_best = min(our_relay_times.values()) if our_relay_times else float('inf')
    
    # Get opponent's times sorted
    opp_times = sorted(opponent_relay_times.values())
    
    if our_best == float('inf'):
        return 0
    
    if not opp_times:
        return 11
    
    # Count how many opponent times we beat
    beaten = sum(1 for t in opp_times if our_best < t)
    
    if beaten == len(opp_times):        return 11  # 1st place
    elif beaten >= len(opp_times) - 1:  return 4   # 2nd place  
    elif beaten >= len(opp_times) - 2:  return 2   # 3rd place
    else:                               return 0   # 4th+ place


def ensure_long_format(df):
    """Convert DataFrame to long format if needed."""
    if df.empty:
        return df
        
    if 'Event' not in df.columns:
        from utils import pivot_to_long_format
        return pivot_to_long_format(df)
    return df


def calculate_dual_meet_score(user_lineup_df, user_relay_df, opponent_lineup_df, opponent_relay_df):
    """
    Calculate complete dual meet score for both teams.
    """
    user_individual_pts = 0
    user_relay_pts = 0
    opponent_individual_pts = 0
    opponent_relay_pts = 0
    
    print("\n=== DUAL MEET SCORING BREAKDOWN ===")
    
    # Individual Events Scoring
    if not user_lineup_df.empty and not opponent_lineup_df.empty:
        # Ensure both DataFrames are in long format
        user_long_df = ensure_long_format(user_lineup_df)
        opponent_long_df = ensure_long_format(opponent_lineup_df)
        
        if not user_long_df.empty and not opponent_long_df.empty:
            # Get all events
            user_events = set(user_long_df['Event'].unique())
            opp_events = set(opponent_long_df['Event'].unique())
            all_events = user_events.union(opp_events)
            
            print("\nINDIVIDUAL EVENTS:")
            for event in sorted(all_events):
                user_event_data = user_long_df[user_long_df['Event'] == event]
                opp_event_data = opponent_long_df[opponent_long_df['Event'] == event]
                
                # Get times for this event
                user_times = list(user_event_data['Time']) if not user_event_data.empty else []
                opp_times = list(opp_event_data['Time']) if not opp_event_data.empty else []
                
                event_user_pts = 0
                event_opp_pts = 0
                
                # Calculate points for each user swimmer
                for time in user_times:
                    pts = calculate_individual_points_vs_opponent(time, opp_times)
                    event_user_pts += pts
                
                # Calculate points for each opponent swimmer  
                for time in opp_times:
                    pts = calculate_individual_points_vs_opponent(time, user_times)
                    event_opp_pts += pts
                
                user_individual_pts += event_user_pts
                opponent_individual_pts += event_opp_pts
                
                print(f"  {event:25} | Your Team: {event_user_pts:2d} pts | Opponent: {event_opp_pts:2d} pts")
    
    # Relay Events Scoring
    if not user_relay_df.empty and not opponent_relay_df.empty:
        user_relay_times = calculate_relay_times(user_relay_df)
        opp_relay_times = calculate_relay_times(opponent_relay_df)
        
        all_relay_types = set(user_relay_times.keys()).union(set(opp_relay_times.keys()))
        
        if all_relay_types:
            print("\nRELAY EVENTS:")
            for relay_type in sorted(all_relay_types):
                user_times = user_relay_times.get(relay_type, {})
                opp_times = opp_relay_times.get(relay_type, {})
                
                # Calculate points for user team
                if user_times:
                    user_pts = calculate_relay_points_vs_opponent(user_times, opp_times)
                    user_relay_pts += user_pts
                else:
                    user_pts = 0
                
                # Calculate points for opponent team
                if opp_times:
                    opp_pts = calculate_relay_points_vs_opponent(opp_times, user_times)
                    opponent_relay_pts += opp_pts
                else:
                    opp_pts = 0
                
                print(f"  {relay_type:25} | Your Team: {user_pts:2d} pts | Opponent: {opp_pts:2d} pts")
                
                # Show relay times for context
                if user_times:
                    user_best = min(user_times.values())
                    user_best_formatted = f"{int(user_best//60)}:{user_best%60:05.2f}"
                    print(f"    Your best time: {user_best_formatted}")
                if opp_times:
                    opp_best = min(opp_times.values())
                    opp_best_formatted = f"{int(opp_best//60)}:{opp_best%60:05.2f}"
                    print(f"    Opponent best time: {opp_best_formatted}")
    
    # Final Score Summary
    user_total = user_individual_pts + user_relay_pts
    opponent_total = opponent_individual_pts + opponent_relay_pts
    
    print(f"\n{'='*50}")
    print(f"FINAL PROJECTED SCORE:")
    print(f"{'='*50}")
    print(f"Individual Events  | Your Team: {user_individual_pts:3d} | Opponent: {opponent_individual_pts:3d}")
    print(f"Relay Events       | Your Team: {user_relay_pts:3d} | Opponent: {opponent_relay_pts:3d}")
    print(f"{'-'*50}")
    print(f"TOTAL SCORE        | Your Team: {user_total:3d} | Opponent: {opponent_total:3d}")
    print(f"{'='*50}")
    
    if user_total > opponent_total:
        margin = user_total - opponent_total
        print(f"🏆 PROJECTED WINNER: YOUR TEAM by {margin} points!")
    elif opponent_total > user_total:
        margin = opponent_total - user_total
        print(f"😞 PROJECTED WINNER: OPPONENT by {margin} points")
    else:
        print(f"🤝 PROJECTED TIE!")
    
    print(f"{'='*50}")
    
    return user_total, opponent_total