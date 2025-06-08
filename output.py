# output.py

from utils import time_to_seconds
import pandas as pd


def print_individual_lineup(lineup_df):
    """Print individual event lineups with proper error handling."""
    if lineup_df.empty:
        print("No individual lineup generated.")
        return
        
    print("\n=== INDIVIDUAL LINEUP ===")
    
    # Check if we have the required columns
    if 'Event' not in lineup_df.columns or 'Swimmer' not in lineup_df.columns or 'Time' not in lineup_df.columns:
        print("Error: Missing required columns in lineup data.")
        print(f"Available columns: {list(lineup_df.columns)}")
        return
    
    for event in sorted(lineup_df['Event'].unique()):
        print(f"\n{event}:")
        event_swimmers = lineup_df[lineup_df['Event'] == event]
        
        # Sort by time for better display
        event_swimmers = event_swimmers.copy()
        event_swimmers['Time_Sec'] = event_swimmers['Time'].apply(time_to_seconds)
        event_swimmers = event_swimmers.sort_values('Time_Sec')
        
        for _, row in event_swimmers.iterrows():
            print(f"  {row['Swimmer']} – {row['Time']}")


def print_relay_lineup(relay_df):
    """Print relay lineups with proper error handling."""
    if relay_df.empty:
        print("No relay lineup generated.")
        return
        
    print("\n=== RELAY LINEUP ===")
    
    # Check if we have the required columns
    required_cols = ['Relay', 'Swimmer', 'Time', 'Leg']
    missing_cols = [col for col in required_cols if col not in relay_df.columns]
    
    if missing_cols:
        print(f"Error: Missing required columns: {missing_cols}")
        print(f"Available columns: {list(relay_df.columns)}")
        return
    
    for relay in sorted(relay_df['Relay'].unique()):
        print(f"\n{relay}:")
        subset = relay_df[relay_df['Relay'] == relay].copy()
        subset = subset.sort_values('Leg')
        for _, row in subset.iterrows():
            print(f"  {row['Leg']}: {row['Swimmer']} – {row['Time']}")


def print_detailed_lineup(individual_df, relay_df, swimmer_counts=None):
    """Print detailed lineup with swimmer event counts."""
    choice = input("\nShow detailed lineup? (y/n): ").strip().lower()
    if choice != 'y':
        return

    print("\n=== DETAILED INDIVIDUAL LINEUP ===")
    # Check if individual_df is empty or missing required columns
    if individual_df.empty:
        print("No individual events to display.")
    elif 'Event' not in individual_df.columns:
        print("Error: Individual lineup missing 'Event' column.")
        print(f"Available columns: {list(individual_df.columns)}")
    else:
        for event in sorted(individual_df['Event'].unique()):
            print(f"\n{event}:")
            block = individual_df[individual_df['Event'] == event].copy()
            
            # Add time in seconds for sorting
            block['Time_Sec'] = block['Time'].apply(time_to_seconds)
            block = block.sort_values('Time_Sec')
            
            for i, (_, row) in enumerate(block.iterrows(), 1):
                extra = ""
                if 'Strategic_Points' in row and pd.notna(row['Strategic_Points']):
                    extra = f" (Strategic Points: {row['Strategic_Points']})"
                print(f"  {i}. {row['Swimmer']} – {row['Time']}{extra}")

    print("\n=== DETAILED RELAY LINEUP ===")
    # Check if relay_df is empty or missing required columns
    if relay_df.empty:
        print("No relay events to display.")
    elif 'Relay' not in relay_df.columns:
        print("Error: Relay lineup missing 'Relay' column.")
        print(f"Available columns: {list(relay_df.columns)}")
    else:
        for relay in sorted(relay_df['Relay'].unique()):
            print(f"\n{relay}:")
            block = relay_df[relay_df['Relay'] == relay].copy()
            block = block.sort_values('Leg')
            for _, row in block.iterrows():
                print(f"  {row['Leg']}: {row['Swimmer']} – {row['Time']}")
    
    # Print swimmer event counts if provided
    if swimmer_counts is not None and isinstance(swimmer_counts, dict):
        print("\n=== SWIMMER EVENT COUNTS ===")
        for swimmer, count in sorted(swimmer_counts.items()):
            print(f"{swimmer}: {count} events")


def export_lineup_to_file(individual_df, relay_df, filename="lineup_export.txt"):
    """Export lineup to a text file for coaches."""
    try:
        with open(filename, 'w') as f:
            f.write("=== MEET LINEUP EXPORT ===\n\n")
            
            # Individual Events
            f.write("=== INDIVIDUAL EVENTS ===\n")
            if not individual_df.empty and 'Event' in individual_df.columns:
                for event in sorted(individual_df['Event'].unique()):
                    f.write(f"\n{event}:\n")
                    event_swimmers = individual_df[individual_df['Event'] == event].copy()
                    event_swimmers['Time_Sec'] = event_swimmers['Time'].apply(time_to_seconds)
                    event_swimmers = event_swimmers.sort_values('Time_Sec')
                    
                    for i, (_, row) in enumerate(event_swimmers.iterrows(), 1):
                        f.write(f"  {i}. {row['Swimmer']} – {row['Time']}\n")
            else:
                f.write("No individual events to export.\n")
            
            # Relay Events
            f.write("\n=== RELAY EVENTS ===\n")
            if not relay_df.empty and 'Relay' in relay_df.columns:
                for relay in sorted(relay_df['Relay'].unique()):
                    f.write(f"\n{relay}:\n")
                    subset = relay_df[relay_df['Relay'] == relay].copy()
                    subset = subset.sort_values('Leg')
                    for _, row in subset.iterrows():
                        f.write(f"  {row['Leg']}: {row['Swimmer']} – {row['Time']}\n")
            else:
                f.write("No relay events to export.\n")
        
        print(f"\n✅ Lineup exported to '{filename}'")
        
    except Exception as e:
        print(f"❌ Error exporting lineup: {e}")


def print_lineup_summary(individual_df, relay_df):
    """Print a summary of the lineup."""
    print("\n=== LINEUP SUMMARY ===")
    
    # Individual events summary
    if not individual_df.empty and 'Event' in individual_df.columns:
        num_ind_events = individual_df['Event'].nunique()
        num_ind_swimmers = individual_df['Swimmer'].nunique()
        print(f"Individual Events: {num_ind_events} events, {num_ind_swimmers} swimmers")
    else:
        print("Individual Events: None")
    
    # Relay events summary
    if not relay_df.empty and 'Relay' in relay_df.columns:
        num_relay_events = relay_df['Relay'].nunique()
        num_relay_swimmers = relay_df['Swimmer'].nunique()
        print(f"Relay Events: {num_relay_events} relays, {num_relay_swimmers} swimmers")
    else:
        print("Relay Events: None")
    
    # Overall participation
    all_swimmers = set()
    if not individual_df.empty and 'Swimmer' in individual_df.columns:
        all_swimmers.update(individual_df['Swimmer'].unique())
    if not relay_df.empty and 'Swimmer' in relay_df.columns:
        all_swimmers.update(relay_df['Swimmer'].unique())
    
    print(f"Total swimmers competing: {len(all_swimmers)}")
    print("="*40)