# utils.py

import pandas as pd
import numpy as np

def time_to_seconds(time_str):
    """Convert 'M:SS.hh' or seconds string to float seconds."""
    try:
        if pd.isna(time_str) or str(time_str).strip() == '' or str(time_str).lower() == 'nan':
            return float('inf')
        
        s = str(time_str).strip()
        
        # Handle empty strings
        if not s:
            return float('inf')
            
        # Handle time format MM:SS.ss
        if ':' in s:
            parts = s.split(':')
            if len(parts) == 2:
                try:
                    mins = int(parts[0])
                    secs = float(parts[1])
                    return mins * 60 + secs
                except ValueError:
                    return float('inf')
        
        # Handle seconds only format
        try:
            return float(s)
        except ValueError:
            return float('inf')
            
    except Exception as e:
        print(f"Warning: Could not parse time '{time_str}': {e}")
        return float('inf')


def seconds_to_time_string(seconds):
    """Convert seconds back to MM:SS.ss format."""
    if seconds == float('inf') or pd.isna(seconds):
        return "NT"
    
    try:
        minutes = int(seconds // 60)
        remaining_seconds = seconds % 60
        
        if minutes > 0:
            return f"{minutes}:{remaining_seconds:05.2f}"
        else:
            return f"{remaining_seconds:.2f}"
    except:
        return "NT"


def filter_events_by_preferences(times_df, distance_events, im_events):
    """
    Filter DataFrame for only the individual events the user selected.
    Handles both pivoted (wide) and long formats.
    """
    if times_df.empty:
        print("Warning: Empty DataFrame provided to filter_events_by_preferences")
        return times_df
    
    # Standard swimming events - using exact names that match scraped data
    standard = [
        '50 free', '100 free', '200 free', '500 free',
        '50 back', '100 back', '200 back',
        '50 breast', '100 breast', '200 breast', 
        '50 fly', '100 fly', '200 fly'
    ]
    
    # Combine all selected events
    selected_events = standard + distance_events + im_events
    
    print(f"→ Filtering for events: {selected_events}")
    
    # Check if this is wide format (no 'Event' column) or long format
    if 'Event' not in times_df.columns:
        # Wide format - filter columns
        # First, ensure we have a Swimmer column
        if 'Swimmer' not in times_df.columns:
            print("Error: No 'Swimmer' column found in DataFrame")
            print(f"Available columns: {list(times_df.columns)}")
            return pd.DataFrame()
        
        # Find matching columns (case-insensitive and flexible matching)
        available_cols = ['Swimmer']  # Always include swimmer column
        
        for event in selected_events:
            # Look for exact matches first
            matching_cols = [col for col in times_df.columns if col.lower() == event.lower()]
            
            # If no exact match, try partial matching
            if not matching_cols:
                matching_cols = [col for col in times_df.columns 
                               if event.lower().replace(' ', '').replace('_', '') in 
                               col.lower().replace(' ', '').replace('_', '')]
            
            available_cols.extend(matching_cols)
        
        # Remove duplicates while preserving order
        available_cols = list(dict.fromkeys(available_cols))
        
        print(f"→ Filtering wide format to columns: {available_cols}")
        
        if len(available_cols) <= 1:  # Only swimmer column found
            print("Warning: No event columns found after filtering")
            print(f"Available columns in data: {list(times_df.columns)}")
            return pd.DataFrame()
        
        filtered_df = times_df[available_cols].copy()
        return filtered_df
    else:
        # Long format - filter rows by Event column
        # Use case-insensitive matching for events
        mask = times_df['Event'].str.lower().isin([e.lower() for e in selected_events])
        filtered_df = times_df[mask].copy()
        
        print(f"→ Filtered to {len(filtered_df)} swimmer-event rows from {len(times_df)} original rows")
        
        if filtered_df.empty:
            print("Warning: No events matched the filter criteria")
            available_events = times_df['Event'].unique()
            print(f"Available events in data: {list(available_events)}")
            print(f"Looking for events: {selected_events}")
        
        return filtered_df


def pivot_to_long_format(pivot_df):
    """
    Turn a wide pivot (Swimmer × event-columns) into long DataFrame.
    """
    if pivot_df.empty:
        return pd.DataFrame(columns=['Swimmer', 'Event', 'Time'])
    
    if 'Swimmer' not in pivot_df.columns:
        print("Error: No 'Swimmer' column found in pivot_to_long_format")
        print(f"Available columns: {list(pivot_df.columns)}")
        return pd.DataFrame(columns=['Swimmer', 'Event', 'Time'])
    
    rows = []
    event_columns = [col for col in pivot_df.columns if col != 'Swimmer']
    
    print(f"Converting {len(pivot_df)} swimmers × {len(event_columns)} events to long format")
    
    for _, row in pivot_df.iterrows():
        swimmer_name = row['Swimmer']
        
        if pd.isna(swimmer_name) or str(swimmer_name).strip() == '':
            continue  # Skip rows with invalid swimmer names
        
        for event_col in event_columns:
            time_value = row[event_col]
            
            # Check if time is valid (not NaN, not empty string, not 'nan')
            if (pd.notna(time_value) and 
                str(time_value).strip() != '' and 
                str(time_value).lower() not in ['nan', 'nt', 'ns', 'dq']):
                
                rows.append({
                    'Swimmer': str(swimmer_name).strip(),
                    'Event': event_col,
                    'Time': str(time_value).strip()
                })
    
    result_df = pd.DataFrame(rows)
    print(f"Created long format with {len(result_df)} valid swimmer-event combinations")
    
    if result_df.empty:
        print("Warning: No valid times found during pivot to long format")
        # Print sample of original data for debugging
        print("Sample of original data:")
        print(pivot_df.head())
        print("Event columns found:", event_columns)
    
    return result_df


def validate_swimmer_data(times_df):
    """
    Validate and report on swimmer data quality.
    """
    print("\n=== DATA VALIDATION REPORT ===")
    
    if times_df.empty:
        print("ERROR: DataFrame is empty")
        return False
    
    print(f"Total rows: {len(times_df)}")
    print(f"Total columns: {len(times_df.columns)}")
    print(f"Columns: {list(times_df.columns)}")
    
    if 'Swimmer' not in times_df.columns:
        print("ERROR: No 'Swimmer' column found")
        return False
    
    unique_swimmers = times_df['Swimmer'].nunique()
    print(f"Unique swimmers: {unique_swimmers}")
    
    if unique_swimmers == 0:
        print("ERROR: No valid swimmers found")
        return False
    
    # Check for empty swimmer names
    empty_names = times_df['Swimmer'].isna().sum()
    if empty_names > 0:
        print(f"WARNING: {empty_names} rows with empty swimmer names")
    
    # If wide format, check event columns
    if 'Event' not in times_df.columns:
        event_cols = [col for col in times_df.columns if col != 'Swimmer']
        print(f"Event columns: {len(event_cols)}")
        
        if len(event_cols) == 0:
            print("ERROR: No event columns found")
            return False
        
        # Count valid times per event
        total_valid_times = 0
        for col in event_cols:
            valid_times = times_df[col].apply(lambda x: 
                pd.notna(x) and 
                str(x).strip() != '' and 
                str(x).lower() not in ['nan', 'nt', 'ns', 'dq']
            ).sum()
            print(f"  {col}: {valid_times} valid times")
            total_valid_times += valid_times
        
        if total_valid_times == 0:
            print("ERROR: No valid times found in any event")
            return False
            
    else:
        # Long format
        unique_events = times_df['Event'].nunique()
        print(f"Unique events: {unique_events}")
        
        if unique_events == 0:
            print("ERROR: No events found")
            return False
            
        print(f"Event list: {list(times_df['Event'].unique())}")
        
        if 'Time' not in times_df.columns:
            print("ERROR: No 'Time' column found in long format")
            return False
        
        valid_times = times_df['Time'].apply(lambda x: 
            pd.notna(x) and 
            str(x).strip() != '' and 
            str(x).lower() not in ['nan', 'nt', 'ns', 'dq']
        ).sum()
        print(f"Valid times: {valid_times} out of {len(times_df)}")
        
        if valid_times == 0:
            print("ERROR: No valid times found")
            return False
    
    print("=== END VALIDATION REPORT ===\n")
    return True


def clean_time_data(times_df):
    """
    Clean and standardize time data in the DataFrame.
    """
    if times_df.empty:
        return times_df
    
    cleaned_df = times_df.copy()
    
    # Clean swimmer names
    if 'Swimmer' in cleaned_df.columns:
        cleaned_df['Swimmer'] = cleaned_df['Swimmer'].astype(str).str.strip()
        # Remove rows with empty swimmer names
        cleaned_df = cleaned_df[cleaned_df['Swimmer'] != '']
        cleaned_df = cleaned_df[cleaned_df['Swimmer'].str.lower() != 'nan']
    
    # If wide format, clean event columns
    if 'Event' not in cleaned_df.columns:
        event_cols = [col for col in cleaned_df.columns if col != 'Swimmer']
        
        for col in event_cols:
            # Replace various "no time" indicators with NaN
            cleaned_df[col] = cleaned_df[col].replace([
                '', 'NT', 'ns', 'NS', 'DQ', 'dq', 'SCR', 'scr', 
                'DNS', 'dns', 'DNF', 'dnf', 'DSQ', 'dsq'
            ], pd.NA)
            
            # Convert to string and strip whitespace
            cleaned_df[col] = cleaned_df[col].astype(str).str.strip()
            
            # Replace 'nan' strings with actual NaN
            cleaned_df[col] = cleaned_df[col].replace('nan', pd.NA)
    else:
        # Long format - clean Time column
        if 'Time' in cleaned_df.columns:
            cleaned_df['Time'] = cleaned_df['Time'].replace([
                '', 'NT', 'ns', 'NS', 'DQ', 'dq', 'SCR', 'scr',
                'DNS', 'dns', 'DNF', 'dnf', 'DSQ', 'dsq'
            ], pd.NA)
            
            # Convert to string and strip whitespace
            cleaned_df['Time'] = cleaned_df['Time'].astype(str).str.strip()
            
            # Replace 'nan' strings with actual NaN
            cleaned_df['Time'] = cleaned_df['Time'].replace('nan', pd.NA)
            
            # Remove rows with invalid times
            cleaned_df = cleaned_df.dropna(subset=['Time'])
    
    return cleaned_df


def get_swimmer_best_times(times_df, swimmer_name):
    """
    Get best times for a specific swimmer across all events.
    Returns a dictionary of {event: best_time}.
    """
    if times_df.empty:
        return {}
    
    best_times = {}
    
    if 'Event' not in times_df.columns:
        # Wide format
        swimmer_row = times_df[times_df['Swimmer'] == swimmer_name]
        if swimmer_row.empty:
            return {}
        
        swimmer_row = swimmer_row.iloc[0]
        event_cols = [col for col in times_df.columns if col != 'Swimmer']
        
        for col in event_cols:
            time_val = swimmer_row[col]
            if pd.notna(time_val) and str(time_val).strip() != '':
                time_seconds = time_to_seconds(time_val)
                if time_seconds != float('inf'):
                    best_times[col] = time_val
    else:
        # Long format
        swimmer_times = times_df[times_df['Swimmer'] == swimmer_name]
        
        for event in swimmer_times['Event'].unique():
            event_times = swimmer_times[swimmer_times['Event'] == event]
            
            # Find best time for this event
            best_seconds = float('inf')
            best_time_str = None
            
            for _, row in event_times.iterrows():
                time_seconds = time_to_seconds(row['Time'])
                if time_seconds < best_seconds:
                    best_seconds = time_seconds
                    best_time_str = row['Time']
            
            if best_time_str is not None:
                best_times[event] = best_time_str
    
    return best_times


def standardize_event_names(times_df):
    """
    Standardize event names to ensure consistency across the system.
    """
    if times_df.empty:
        return times_df
    
    # Mapping of common variations to standard names
    event_mapping = {
        # Distance events
        '1650_free': '1650 free',
        '1650free': '1650 free',
        '1650 freestyle': '1650 free',
        '1000_free': '1000 free',
        '1000free': '1000 free', 
        '1000 freestyle': '1000 free',
        
        # Standard events
        '50_free': '50 free',
        '50free': '50 free',
        '50 freestyle': '50 free',
        '100_free': '100 free',
        '100free': '100 free',
        '100 freestyle': '100 free',
        '200_free': '200 free',
        '200free': '200 free',
        '200 freestyle': '200 free',
        '500_free': '500 free',
        '500free': '500 free',
        '500 freestyle': '500 free',
        
        # Backstroke
        '50_back': '50 back',
        '50back': '50 back',
        '50 backstroke': '50 back',
        '100_back': '100 back', 
        '100back': '100 back',
        '100 backstroke': '100 back',
        '200_back': '200 back',
        '200back': '200 back',
        '200 backstroke': '200 back',
        
        # Breaststroke
        '50_breast': '50 breast',
        '50breast': '50 breast',
        '50 breaststroke': '50 breast',
        '100_breast': '100 breast',
        '100breast': '100 breast', 
        '100 breaststroke': '100 breast',
        '200_breast': '200 breast',
        '200breast': '200 breast',
        '200 breaststroke': '200 breast',
        
        # Butterfly
        '50_fly': '50 fly',
        '50fly': '50 fly',
        '50 butterfly': '50 fly',
        '100_fly': '100 fly',
        '100fly': '100 fly',
        '100 butterfly': '100 fly',
        '200_fly': '200 fly',
        '200fly': '200 fly', 
        '200 butterfly': '200 fly',
        
        # IM
        '200_im': '200 IM',
        '200im': '200 IM',
        '200 individual medley': '200 IM',
        '400_im': '400 IM',
        '400im': '400 IM',
        '400 individual medley': '400 IM',
    }
    
    standardized_df = times_df.copy()
    
    if 'Event' in standardized_df.columns:
        # Long format - standardize Event column
        standardized_df['Event'] = standardized_df['Event'].replace(event_mapping)
    else:
        # Wide format - standardize column names
        column_mapping = {}
        for old_name in standardized_df.columns:
            if old_name in event_mapping:
                column_mapping[old_name] = event_mapping[old_name]
        
        standardized_df = standardized_df.rename(columns=column_mapping)
    
    return standardized_df