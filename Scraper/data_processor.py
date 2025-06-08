import pandas as pd
import re
import numpy as np
from collections import defaultdict

def standardize_event_name(event_name):
    """
    Standardize event names to match the exact format from EVENT_CODE_TO_NAME mappings.
    This ensures compatibility with url_builder.py and data_scraper.py.
    """
    if not event_name or event_name == "Unknown Event":
        return event_name
    
    event_lower = event_name.lower().strip()
    
    # Direct mappings for exact matches (handles output from EVENT_CODE_TO_NAME)
    direct_mappings = {
        '50 free': '50 free',
        '100 free': '100 free', 
        '200 free': '200 free',
        '500 free': '500 free',
        '1000 free': '1000 free',
        '1500 free': '1500 free',
        '1650 free': '1650 free',
        '50 back': '50 back',
        '100 back': '100 back',
        '200 back': '200 back',
        '50 breast': '50 breast',
        '100 breast': '100 breast',
        '200 breast': '200 breast',
        '50 fly': '50 fly',
        '100 fly': '100 fly',
        '200 fly': '200 fly',
        '200 im': '200 IM',
        '400 im': '400 IM'
    }
    
    # Check for direct match first
    if event_lower in direct_mappings:
        return direct_mappings[event_lower]
    
    # Alternative name mappings for common variations
    standardized = {
        '50 free': ['50 freestyle', '50 fr', '50free', 'fifty free'],
        '100 free': ['100 freestyle', '100 fr', '100free', 'hundred free'],
        '200 free': ['200 freestyle', '200 fr', '200free', 'two hundred free'],
        '500 free': ['500 freestyle', '500 fr', '500free', 'five hundred free'],
        '1000 free': ['1000 freestyle', '1000 fr', '1000free', 'thousand free'],
        '1500 free': ['1500 freestyle', '1500 fr', '1500free', 'fifteen hundred free'],
        '1650 free': ['1650 freestyle', '1650 fr', '1650free', 'mile', '1650 yard'],
        '50 back': ['50 backstroke', '50 bk', '50back', 'fifty back'],
        '100 back': ['100 backstroke', '100 bk', '100back', 'hundred back'],
        '200 back': ['200 backstroke', '200 bk', '200back', 'two hundred back'],
        '50 breast': ['50 breaststroke', '50 br', '50breast', 'fifty breast'],
        '100 breast': ['100 breaststroke', '100 br', '100breast', 'hundred breast'],
        '200 breast': ['200 breaststroke', '200 br', '200breast', 'two hundred breast'],
        '50 fly': ['50 butterfly', '50 fl', '50fly', 'fifty fly'],
        '100 fly': ['100 butterfly', '100 fl', '100fly', 'hundred fly'],
        '200 fly': ['200 butterfly', '200 fl', '200fly', 'two hundred fly'],
        '200 IM': ['200 individual medley', '200 im', '200im', 'two hundred im'],
        '400 IM': ['400 individual medley', '400 im', '400im', 'four hundred im']
    }
    
    for standard_name, variations in standardized.items():
        if any(var in event_lower for var in variations):
            return standard_name
    
    return event_name

def create_times_dataframe(data):
    """
    Create a DataFrame from time data with improved cleaning and validation.
    """
    if not data:
        raise Exception("No time data to process")
    
    print(f"[DEBUG] Processing {len(data)} raw time records")
    
    df = pd.DataFrame(data, columns=["Swimmer", "Event", "Time"])
    print(f"[DEBUG] Initial DataFrame shape: {df.shape}")
    
    # Remove duplicates
    df = df.drop_duplicates()
    print(f"[DEBUG] After removing duplicates: {df.shape}")
    
    # Clean swimmer names
    df["Swimmer"] = df["Swimmer"].str.replace(r'\(.*?\)', '', regex=True).str.strip()
    df["Swimmer"] = df["Swimmer"].str.replace(r'\s+', ' ', regex=True)
    
    # Filter out invalid swimmer names
    df = df[df["Swimmer"].str.len() > 2]
    df = df[~df["Swimmer"].str.isdigit()]
    print(f"[DEBUG] After filtering swimmer names: {df.shape}")
    
    # Clean and validate times
    df = df[df["Time"].str.contains(r'\d+:\d+|\d+\.\d+', na=False)]
    print(f"[DEBUG] After filtering times: {df.shape}")
    
    # Clean event names and standardize
    df["Event"] = df["Event"].str.strip().str.replace(r'\s+', ' ', regex=True)
    df["Event"] = df["Event"].apply(standardize_event_name)
    
    # Remove rows with unknown events if they're the majority
    unknown_count = (df["Event"] == "Unknown Event").sum()
    total_count = len(df)
    if unknown_count > total_count * 0.5:
        print(f"[WARNING] {unknown_count}/{total_count} events are unknown - may indicate parsing issues")
    
    print(f"[DEBUG] Final processed DataFrame: {df.shape}")
    print(f"[DEBUG] Events found: {df['Event'].unique().tolist()}")
    print(f"[DEBUG] Sample data:")
    print(df.head())
    
    if len(df) == 0:
        raise Exception("No valid data after cleaning")
    
    try:
        # Create pivot table
        pivot_df = df.pivot_table(
            index="Swimmer",
            columns="Event",
            values="Time",
            aggfunc="first"
        ).reset_index()
        
        pivot_df.columns.name = None
        print(f"[DEBUG] Created pivot table: {pivot_df.shape[0]} swimmers, {pivot_df.shape[1]-1} events")
        print(f"[DEBUG] Events in pivot: {[col for col in pivot_df.columns if col != 'Swimmer']}")
        return pivot_df
    except Exception as e:
        print(f"[DEBUG] Pivot table creation failed: {e}")
        print(f"[DEBUG] Returning long-format DataFrame instead")
        return df

def save_to_excel(df, filename):
    """
    Save DataFrame to Excel with improved formatting.
    """
    print(f"→ Saving to {filename}...")
    
    # Save to Excel
    with pd.ExcelWriter(filename, engine='openpyxl') as writer:
        df.to_excel(writer, sheet_name='Swimmer Times', index=False)
        
        # Get the workbook and worksheet
        workbook = writer.book
        worksheet = writer.sheets['Swimmer Times']
        
        # Auto-adjust column widths
        for column in worksheet.columns:
            max_length = 0
            column_letter = column[0].column_letter
            for cell in column:
                try:
                    if len(str(cell.value)) > max_length:
                        max_length = len(str(cell.value))
                except:
                    pass
            adjusted_width = min(max_length + 2, 50)  # Cap at 50 characters
            worksheet.column_dimensions[column_letter].width = adjusted_width
    
    print(f"→ Success! Saved {df.shape[0]} swimmers with times")
    if len(df.columns) > 1:
        events = [col for col in df.columns if col != 'Swimmer']
        print(f"→ Events found: {events}")
    return df

def convert_time_to_seconds(time_str):
    """
    Convert time string (e.g., '1:23.45' or '23.45') to seconds for comparison.
    """
    if pd.isna(time_str) or not isinstance(time_str, str):
        return float('inf')
    
    try:
        # Handle different time formats
        time_str = time_str.strip()
        
        if ':' in time_str:
            # Format: M:SS.ss or MM:SS.ss
            parts = time_str.split(':')
            if len(parts) == 2:
                minutes = int(parts[0])
                seconds = float(parts[1])
                return minutes * 60 + seconds
            elif len(parts) == 3:
                # Format: H:MM:SS.ss (for very long events)
                hours = int(parts[0])
                minutes = int(parts[1])
                seconds = float(parts[2])
                return hours * 3600 + minutes * 60 + seconds
        else:
            # Format: SS.ss
            return float(time_str)
    except (ValueError, IndexError):
        return float('inf')

def calculate_swimmer_strength(times_dict, events):
    """
    Calculate overall strength of a swimmer based on their average converted time.
    Returns a score where lower is better (faster swimmer).
    """
    total_score = 0
    valid_events = 0
    
    for event in events:
        if event in times_dict and times_dict[event] != float('inf'):
            # Convert time to seconds for comparison
            total_score += times_dict[event]
            valid_events += 1
    
    return total_score / valid_events if valid_events > 0 else float('inf')

def lineup_spread(times_df, max_events_per_swimmer=4, swimmers_per_event=5):
    """
    Create an optimized dual meet lineup with even talent distribution across events.
    Uses a balanced assignment algorithm to ensure competitive equity across all events.
    """
    if times_df.empty:
        raise Exception("No swimmer times provided for lineup optimization")
    
    print(f"[DEBUG] Starting lineup optimization: {swimmers_per_event} swimmers per event, max {max_events_per_swimmer} events per swimmer")
    
    # Copy the DataFrame to avoid modifying the original
    df = times_df.copy()
    
    # Convert all times to seconds for comparison
    time_columns = [col for col in df.columns if col != 'Swimmer']
    print(f"[DEBUG] Processing events: {time_columns}")
    
    for col in time_columns:
        df[col] = df[col].apply(convert_time_to_seconds)
    
    # Create swimmer rankings for each event
    event_rankings = {}
    for event in time_columns:
        valid_times = df[['Swimmer', event]].copy()
        valid_times = valid_times[valid_times[event] != float('inf')]
        
        if len(valid_times) == 0:
            print(f"[WARNING] No valid times found for {event}")
            continue
            
        valid_times = valid_times.sort_values(by=event)
        valid_times['rank'] = range(1, len(valid_times) + 1)
        event_rankings[event] = dict(zip(valid_times['Swimmer'], valid_times['rank']))
        print(f"[DEBUG] {event}: {len(valid_times)} swimmers with valid times")
    
    # Calculate overall swimmer strength scores
    swimmer_strengths = {}
    for _, row in df.iterrows():
        swimmer = row['Swimmer']
        times_dict = {event: row[event] for event in time_columns}
        swimmer_strengths[swimmer] = calculate_swimmer_strength(times_dict, time_columns)
    
    # Sort swimmers by overall strength (best to worst)
    sorted_swimmers = sorted(swimmer_strengths.items(), key=lambda x: x[1])
    print(f"[DEBUG] Ranked {len(sorted_swimmers)} swimmers by overall strength")
    
    # Initialize tracking structures
    lineup = {event: [] for event in time_columns}
    swimmer_event_counts = defaultdict(int)
    event_strength_scores = defaultdict(float)
    
    # Talent distribution algorithm
    print("[DEBUG] Distributing talent across events...")
    
    # First pass: Assign top swimmers strategically to balance events
    top_swimmers = [swimmer for swimmer, _ in sorted_swimmers[:len(time_columns) * 2]]
    
    for swimmer in top_swimmers:
        if swimmer_event_counts[swimmer] >= max_events_per_swimmer:
            continue
        
        # Find events this swimmer can compete in
        available_events = []
        swimmer_row = df[df['Swimmer'] == swimmer].iloc[0]
        
        for event in time_columns:
            if (swimmer_row[event] != float('inf') and 
                len(lineup[event]) < swimmers_per_event):
                available_events.append(event)
        
        if not available_events:
            continue
        
        # Sort events by current strength (weakest first) to balance talent
        event_scores = [(event, event_strength_scores[event]) for event in available_events]
        event_scores.sort(key=lambda x: x[1])
        
        # Assign to the weakest event that needs swimmers
        events_to_assign = min(max_events_per_swimmer - swimmer_event_counts[swimmer], len(event_scores))
        for event, _ in event_scores[:events_to_assign]:
            if len(lineup[event]) < swimmers_per_event:
                lineup[event].append(swimmer)
                swimmer_event_counts[swimmer] += 1
                # Add swimmer's strength to event (lower rank = stronger swimmer)
                event_strength_scores[event] += event_rankings[event].get(swimmer, 999)
                
                if swimmer_event_counts[swimmer] >= max_events_per_swimmer:
                    break
    
    # Second pass: Fill remaining spots with best available swimmers
    print("[DEBUG] Filling remaining lineup spots...")
    
    for event in time_columns:
        if len(lineup[event]) >= swimmers_per_event:
            continue
        
        # Get all swimmers with valid times for this event, not yet at max events
        candidates = []
        for _, row in df.iterrows():
            swimmer = row['Swimmer']
            if (row[event] != float('inf') and 
                swimmer not in lineup[event] and 
                swimmer_event_counts[swimmer] < max_events_per_swimmer):
                candidates.append((swimmer, row[event]))
        
        # Sort by time (fastest first) and fill remaining spots
        candidates.sort(key=lambda x: x[1])
        spots_needed = swimmers_per_event - len(lineup[event])
        
        for swimmer, time in candidates[:spots_needed]:
            lineup[event].append(swimmer)
            swimmer_event_counts[swimmer] += 1
    
    # Convert lineup to DataFrame for output
    lineup_data = []
    for event, swimmers in lineup.items():
        for swimmer in swimmers:
            # Retrieve original time string from input DataFrame
            original_time = times_df.loc[times_df['Swimmer'] == swimmer, event]
            if not original_time.empty and pd.notna(original_time.iloc[0]):
                time_str = original_time.iloc[0]
                lineup_data.append([event, swimmer, time_str])
    
    lineup_df = pd.DataFrame(lineup_data, columns=['Event', 'Swimmer', 'Time'])
    
    # Print talent distribution summary
    print(f"[DEBUG] Lineup optimization complete:")
    print(f"[DEBUG] - Generated lineup for {len([e for e in lineup.values() if e])} events")
    print(f"[DEBUG] - Total assignments: {len(lineup_df)}")
    
    # Show swimmer distribution
    if not lineup_df.empty:
        swimmer_counts = lineup_df['Swimmer'].value_counts()
        print(f"[DEBUG] - Swimmers with {max_events_per_swimmer} events: {sum(swimmer_counts == max_events_per_swimmer)}")
        print(f"[DEBUG] - Swimmers with 3 events: {sum(swimmer_counts == 3)}")
        print(f"[DEBUG] - Swimmers with 2 events: {sum(swimmer_counts == 2)}")
        print(f"[DEBUG] - Swimmers with 1 event: {sum(swimmer_counts == 1)}")
    
    if lineup_df.empty:
        raise Exception("No valid lineup generated - check that swimmers have valid times")
    
    return lineup_df