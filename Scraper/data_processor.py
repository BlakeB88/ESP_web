import pandas as pd
import re
import numpy as np

def standardize_event_name(event_name):
    """
    Standardize event names to common formats.
    """
    if not event_name or event_name == "Unknown Event":
        return event_name
    
    event_lower = event_name.lower()
    
    standardized = {
        '50 free': ['50 freestyle', '50 fr', '50free'],
        '100 free': ['100 freestyle', '100 fr', '100free'],
        '200 free': ['200 freestyle', '200 fr', '200free'],
        '500 free': ['500 freestyle', '500 fr', '500free'],
        '1650 free': ['1650 freestyle', '1650 fr', '1650free', 'mile'],
        '100 back': ['100 backstroke', '100 bk', '100back'],
        '200 back': ['200 backstroke', '200 bk', '200back'],
        '100 breast': ['100 breaststroke', '100 br', '100breast'],
        '200 breast': ['200 breaststroke', '200 br', '200breast'],
        '100 fly': ['100 butterfly', '100 fl', '100fly'],
        '200 fly': ['200 butterfly', '200 fl', '200fly'],
        '200 IM': ['200 individual medley', '200 im', '200im'],
        '400 IM': ['400 individual medley', '400 im', '400im']
    }
    
    for standard_name, variations in standardized.items():
        if any(var in event_lower for var in variations):
            return standard_name
    
    return event_name

def create_times_dataframe(data):
    """
    Create a DataFrame from time data.
    """
    if not data:
        raise Exception("No time data to process")
    
    df = pd.DataFrame(data, columns=["Swimmer", "Event", "Time"])
    df = df.drop_duplicates()
    df = df[df["Swimmer"].str.len() > 2]
    df = df[df["Time"].str.contains(r'\d+:\d+|\d+\.\d+', na=False)]
    
    df["Swimmer"] = df["Swimmer"].str.replace(r'\(.*?\)', '', regex=True).str.strip()
    df["Swimmer"] = df["Swimmer"].str.replace(r'\s+', ' ', regex=True)
    df["Event"] = df["Event"].str.strip().replace(r'\s+', ' ', regex=True)
    df["Event"] = df["Event"].apply(standardize_event_name)
    
    print(f"[DEBUG] Processed {len(df)} swimmer-event-time records")
    print(f"[DEBUG] Sample data:")
    print(df.head())
    
    if len(df) == 0:
        raise Exception("No valid data after cleaning")
    
    try:
        pivot_df = df.pivot_table(
            index="Swimmer",
            columns="Event",
            values="Time",
            aggfunc="first"
        ).reset_index()
        
        pivot_df.columns.name = None
        print(f"[DEBUG] Created pivot table: {pivot_df.shape[0]} swimmers, {pivot_df.shape[1]-1} events")
        print(f"[DEBUG] Events: {list(pivot_df.columns)[1:]}")
        return pivot_df
    except Exception as e:
        print(f"[DEBUG] Pivot table creation failed: {e}")
        return df

def save_to_excel(df, filename):
    """
    Save DataFrame to Excel.
    """
    print(f"→ Saving to {filename}...")
    df.to_excel(filename, index=False)
    print(f"→ Success! Saved {df.shape[0]} swimmers with times")
    if len(df.columns) > 1:
        events = [col for col in df.columns if col != 'Swimmer']
        print(f"→ Events found: {events}")
    return df

def convert_time_to_seconds(time_str):
    """
    Convert time string (e.g., '1:23.45' or '23.45') to seconds.
    """
    if pd.isna(time_str) or not isinstance(time_str, str):
        return float('inf')
    
    try:
        if ':' in time_str:
            parts = time_str.split(':')
            minutes = int(parts[0])
            seconds = float(parts[1])
            return minutes * 60 + seconds
        else:
            return float(time_str)
    except (ValueError, IndexError):
        return float('inf')

def lineup_spread(times_df, max_events_per_swimmer=3, swimmers_per_event=3):
    """
    Create an optimized dual meet lineup, assigning swimmers to events based on fastest times.
    Each swimmer can compete in up to max_events_per_swimmer individual events.
    Each event gets up to swimmers_per_event swimmers.
    """
    if times_df.empty:
        raise Exception("No swimmer times provided for lineup optimization")
    
    # Copy the DataFrame to avoid modifying the original
    df = times_df.copy()
    
    # Convert all times to seconds for comparison
    for col in df.columns:
        if col != 'Swimmer':
            df[col] = df[col].apply(convert_time_to_seconds)
    
    # Initialize lineup dictionary: {event: [swimmer1, swimmer2, ...]}
    lineup = {event: [] for event in df.columns if event != 'Swimmer'}
    swimmer_counts = {swimmer: 0 for swimmer in df['Swimmer']}
    
    # For each event, assign up to swimmers_per_event swimmers with the fastest times
    for event in lineup:
        # Get swimmers with valid times for this event, sorted by time
        event_times = df[['Swimmer', event]].copy()
        event_times = event_times[event_times[event].ne(float('inf'))]
        event_times = event_times.sort_values(by=event)
        
        # Assign swimmers who haven't exceeded max_events_per_swimmer
        assigned = 0
        for _, row in event_times.iterrows():
            swimmer = row['Swimmer']
            if swimmer_counts[swimmer] < max_events_per_swimmer and assigned < swimmers_per_event:
                lineup[event].append(swimmer)
                swimmer_counts[swimmer] += 1
                assigned += 1
            if assigned >= swimmers_per_event:
                break
    
    # Convert lineup to DataFrame for output
    lineup_data = []
    for event, swimmers in lineup.items():
        for swimmer in swimmers:
            # Retrieve original time string from input DataFrame
            time_str = times_df.loc[times_df['Swimmer'] == swimmer, event].iloc[0]
            if pd.notna(time_str):
                lineup_data.append([event, swimmer, time_str])
    
    lineup_df = pd.DataFrame(lineup_data, columns=['Event', 'Swimmer', 'Time'])
    
    print(f"[DEBUG] Generated lineup for {len(lineup)} events")
    print(f"[DEBUG] Lineup sample:")
    print(lineup_df.head())
    
    if lineup_df.empty:
        raise Exception("No valid lineup generated")
    
    return lineup_df