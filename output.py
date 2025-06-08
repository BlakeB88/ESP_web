# output.py

from utils import time_to_seconds
import pandas as pd
import os
from datetime import datetime


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


def export_lineup_to_txt(individual_df, relay_df, team_name="Team", filename=None):
    """Export lineup to a text file for coaches."""
    if filename is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_team_name = "".join(c for c in team_name if c.isalnum() or c in (' ', '-', '_')).rstrip()
        filename = f"{safe_team_name.replace(' ', '_')}_lineup_{timestamp}.txt"
    
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(f"=== {team_name.upper()} MEET LINEUP ===\n")
            f.write(f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            
            # Individual Events
            f.write("=== INDIVIDUAL EVENTS ===\n")
            if not individual_df.empty and 'Event' in individual_df.columns:
                for event in sorted(individual_df['Event'].unique()):
                    f.write(f"\n{event}:\n")
                    event_swimmers = individual_df[individual_df['Event'] == event].copy()
                    event_swimmers['Time_Sec'] = event_swimmers['Time'].apply(time_to_seconds)
                    event_swimmers = event_swimmers.sort_values('Time_Sec')
                    
                    for i, (_, row) in enumerate(event_swimmers.iterrows(), 1):
                        extra = ""
                        if 'Strategic_Points' in row and pd.notna(row['Strategic_Points']):
                            extra = f" (Strategic Points: {row['Strategic_Points']})"
                        f.write(f"  {i}. {row['Swimmer']} – {row['Time']}{extra}\n")
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
            
            # Summary statistics
            f.write("\n=== LINEUP SUMMARY ===\n")
            if not individual_df.empty and 'Event' in individual_df.columns:
                num_ind_events = individual_df['Event'].nunique()
                num_ind_swimmers = individual_df['Swimmer'].nunique()
                f.write(f"Individual Events: {num_ind_events} events, {num_ind_swimmers} swimmers\n")
            else:
                f.write("Individual Events: None\n")
            
            if not relay_df.empty and 'Relay' in relay_df.columns:
                num_relay_events = relay_df['Relay'].nunique()
                num_relay_swimmers = relay_df['Swimmer'].nunique()
                f.write(f"Relay Events: {num_relay_events} relays, {num_relay_swimmers} swimmers\n")
            else:
                f.write("Relay Events: None\n")
            
            # Overall participation
            all_swimmers = set()
            if not individual_df.empty and 'Swimmer' in individual_df.columns:
                all_swimmers.update(individual_df['Swimmer'].unique())
            if not relay_df.empty and 'Swimmer' in relay_df.columns:
                all_swimmers.update(relay_df['Swimmer'].unique())
            
            f.write(f"Total swimmers competing: {len(all_swimmers)}\n")
        
        return filename
        
    except Exception as e:
        print(f"❌ Error exporting lineup: {e}")
        return None


def export_lineup_to_excel(individual_df, relay_df, team_name="Team", filename=None):
    """Export lineup to Excel file with multiple sheets."""
    if filename is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_team_name = "".join(c for c in team_name if c.isalnum() or c in (' ', '-', '_')).rstrip()
        filename = f"{safe_team_name.replace(' ', '_')}_lineup_{timestamp}.xlsx"
    
    try:
        with pd.ExcelWriter(filename, engine='openpyxl') as writer:
            # Individual Events Sheet
            if not individual_df.empty and 'Event' in individual_df.columns:
                # Create a formatted version for export
                export_individual = individual_df.copy()
                export_individual['Time_Sec'] = export_individual['Time'].apply(time_to_seconds)
                export_individual = export_individual.sort_values(['Event', 'Time_Sec'])
                export_individual = export_individual.drop('Time_Sec', axis=1)
                export_individual.to_excel(writer, sheet_name='Individual Events', index=False)
            
            # Relay Events Sheet
            if not relay_df.empty and 'Relay' in relay_df.columns:
                export_relay = relay_df.copy()
                export_relay = export_relay.sort_values(['Relay', 'Leg'])
                export_relay.to_excel(writer, sheet_name='Relay Events', index=False)
            
            # Summary Sheet
            summary_data = []
            
            # Individual events summary
            if not individual_df.empty and 'Event' in individual_df.columns:
                for event in sorted(individual_df['Event'].unique()):
                    event_swimmers = individual_df[individual_df['Event'] == event]
                    summary_data.append({
                        'Event Type': 'Individual',
                        'Event': event,
                        'Number of Swimmers': len(event_swimmers)
                    })
            
            # Relay events summary
            if not relay_df.empty and 'Relay' in relay_df.columns:
                for relay in sorted(relay_df['Relay'].unique()):
                    relay_swimmers = relay_df[relay_df['Relay'] == relay]
                    summary_data.append({
                        'Event Type': 'Relay',
                        'Event': relay,
                        'Number of Swimmers': len(relay_swimmers)
                    })
            
            if summary_data:
                summary_df = pd.DataFrame(summary_data)
                summary_df.to_excel(writer, sheet_name='Summary', index=False)
        
        return filename
        
    except Exception as e:
        print(f"❌ Error exporting to Excel: {e}")
        return None


def export_lineup_to_csv(individual_df, relay_df, team_name="Team"):
    """Export lineup to CSV files (separate files for individual and relay)."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_team_name = "".join(c for c in team_name if c.isalnum() or c in (' ', '-', '_')).rstrip()
    base_filename = f"{safe_team_name.replace(' ', '_')}_lineup_{timestamp}"
    
    exported_files = []
    
    try:
        # Export individual events
        if not individual_df.empty and 'Event' in individual_df.columns:
            individual_filename = f"{base_filename}_individual.csv"
            export_individual = individual_df.copy()
            export_individual['Time_Sec'] = export_individual['Time'].apply(time_to_seconds)
            export_individual = export_individual.sort_values(['Event', 'Time_Sec'])
            export_individual = export_individual.drop('Time_Sec', axis=1)
            export_individual.to_csv(individual_filename, index=False)
            exported_files.append(individual_filename)
        
        # Export relay events
        if not relay_df.empty and 'Relay' in relay_df.columns:
            relay_filename = f"{base_filename}_relay.csv"
            export_relay = relay_df.copy()
            export_relay = export_relay.sort_values(['Relay', 'Leg'])
            export_relay.to_csv(relay_filename, index=False)
            exported_files.append(relay_filename)
        
        return exported_files
        
    except Exception as e:
        print(f"❌ Error exporting to CSV: {e}")
        return []


def prompt_and_export_lineup(individual_df, relay_df, team_name="Team"):
    """Prompt user for export preferences and export accordingly."""
    print("\n" + "="*50)
    print("📁 EXPORT LINEUP OPTIONS")
    print("="*50)
    
    export_choice = input(
        "Export lineup to file? \n"
        "1. Text file (.txt)\n"
        "2. Excel file (.xlsx)\n"
        "3. CSV files (.csv)\n"
        "4. All formats\n"
        "5. Skip export\n"
        "Choose (1-5): "
    ).strip()
    
    if export_choice == '5':
        print("Skipping export.")
        return
    
    exported_files = []
    
    if export_choice in ['1', '4']:
        # Export to TXT
        txt_file = export_lineup_to_txt(individual_df, relay_df, team_name)
        if txt_file:
            exported_files.append(txt_file)
            print(f"✅ Text file exported: {txt_file}")
    
    if export_choice in ['2', '4']:
        # Export to Excel
        excel_file = export_lineup_to_excel(individual_df, relay_df, team_name)
        if excel_file:
            exported_files.append(excel_file)
            print(f"✅ Excel file exported: {excel_file}")
    
    if export_choice in ['3', '4']:
        # Export to CSV
        csv_files = export_lineup_to_csv(individual_df, relay_df, team_name)
        if csv_files:
            exported_files.extend(csv_files)
            for csv_file in csv_files:
                print(f"✅ CSV file exported: {csv_file}")
    
    if exported_files:
        print(f"\n🎉 Successfully exported {len(exported_files)} file(s)!")
        print("Files are saved in the current directory and ready for download.")
        
        # Show file locations
        print("\nExported files:")
        for file in exported_files:
            file_size = os.path.getsize(file) if os.path.exists(file) else 0
            print(f"  📄 {file} ({file_size} bytes)")
    else:
        print("❌ No files were exported successfully.")


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


# Legacy function for backward compatibility
def export_lineup_to_file(individual_df, relay_df, filename="lineup_export.txt"):
    """Legacy export function - maintained for backward compatibility."""
    return export_lineup_to_txt(individual_df, relay_df, "Team", filename)