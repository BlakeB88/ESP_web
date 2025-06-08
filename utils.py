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
    
    # Standard swimming events
    standard = [
        '50 free', '100 free', '200 free', '500 free',
        '100 back', '200 back',
        '100 breast', '200 breast',
        '100 fly', '200 fly'
    ]
    
    # Combine all selected events
    selected_events = standard + distance_events + im_events
    
    print(f"→ Filtering for events: {selected_events}")
    
    if 'Event' not in times_df.columns:
        # Wide format - filter columns
        available_cols = [c for c in times_df.columns if c in selected_events or c == 'Swimmer']
        
        if 'Swimmer' not in available_cols:
            print("Warning: No 'Swimmer' column found in wide format")
            return pd.DataFrame()
        
        print(f"→ Filtering wide format to columns: {available_cols}")
        filtered_df = times_df[available_cols].copy()
        
        # Check if we have any event data
        event_cols = [c for c in available_cols if c != 'Swimmer']
        if not event_cols:
            print("Warning: No event columns found after filtering")
            return pd.DataFrame()
            
        return filtered_df
    else:
        # Long format - filter rows
        filtered_df = times_df[times_df['Event'].isin(selected_events)].copy()
        print(f"→ Filtered to {len(filtered_df)} swimmer-event rows from {len(times_df)} original rows")
        
        if filtered_df.empty:
            print("Warning: No events matched the filter criteria")
            available_events = times_df['Event'].unique()
            print(f"Available events in data: {list(available_events)}")
        
        return filtered_df


def pivot_to_long_format(pivot_df):
    """
    Turn a wide pivot (Swimmer × event-columns) into long DataFrame.
    """
    if pivot_df.empty:
        return pd.DataFrame(columns=['Swimmer', 'Event', 'Time'])
    
    if 'Swimmer' not in pivot_df.columns:
        print("Warning: No 'Swimmer' column found in pivot_to_long_format")
        return pd.DataFrame(columns=['Swimmer', 'Event', 'Time'])
    
    rows = []
    event_columns = [col for col in pivot_df.columns if col != 'Swimmer']
    
    print(f"Converting {len(pivot_df)} swimmers × {len(event_columns)} events to long format")
    
    for _, row in pivot_df.iterrows():
        swimmer_name = row['Swimmer']
        
        for event_col in event_columns:
            time_value = row[event_col]
            
            # Check if time is valid (not NaN, not empty string, not 'nan')
            if (pd.notna(time_value) and 
                str(time_value).strip() != '' and 
                str(time_value).lower() != 'nan'):
                
                rows.append({
                    'Swimmer': swimmer_name,
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
    
    # Check for empty swimmer names
    empty_names = times_df['Swimmer'].isna().sum()
    if empty_names > 0:
        print(f"WARNING: {empty_names} rows with empty swimmer names")
    
    # If wide format, check event columns
    if 'Event' not in times_df.columns:
        event_cols = [col for col in times_df.columns if col != 'Swimmer']
        print(f"Event columns: {len(event_cols)}")
        
        # Count valid times per event
        for col in event_cols:
            valid_times = times_df[col].apply(lambda x: 
                pd.notna(x) and str(x).strip() != '' and str(x).lower() != 'nan'
            ).sum()
            print(f"  {col}: {valid_times} valid times")
    else:
        # Long format
        unique_events = times_df['Event'].nunique()
        print(f"Unique events: {unique_events}")
        print(f"Event list: {list(times_df['Event'].unique())}")
        
        valid_times = times_df['Time'].apply(lambda x: 
            pd.notna(x) and str(x).strip() != '' and str(x).lower() != 'nan'
        ).sum()
        print(f"Valid times: {valid_times} out of {len(times_df)}")
    
    print("=== END VALIDATION REPORT ===\n")
    return True


def clean_time_data(times_df):
    """
    Clean and standardize time data in the DataFrame.
    """
    if times_df.empty:
        return times_df
    
    cleaned_df = times_df.copy()
    
    # If wide format, clean event columns
    if 'Event' not in cleaned_df.columns:
        event_cols = [col for col in cleaned_df.columns if col != 'Swimmer']
        
        for col in event_cols:
            # Replace various "no time" indicators with NaN
            cleaned_df[col] = cleaned_df[col].replace(['', 'NT', 'ns', 'NS', 'DQ', 'dq'], pd.NA)
            
            # Convert numeric strings to proper format
            cleaned_df[col] = cleaned_df[col].apply(lambda x: 
                x if pd.isna(x) or ':' in str(x) else str(x) if pd.notna(x) else pd.NA
            )
    else:
        # Long format - clean Time column
        cleaned_df['Time'] = cleaned_df['Time'].replace(['', 'NT', 'ns', 'NS', 'DQ', 'dq'], pd.NA)
    
    return cleaned_df