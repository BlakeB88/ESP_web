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


def create_swimmer_event_mapping(individual_df, relay_df):
    """
    Create a comprehensive mapping of each swimmer to all their events.
    
    Args:
        individual_df: DataFrame with individual event assignments
        relay_df: DataFrame with relay event assignments
    
    Returns:
        DataFrame with columns: Swimmer, Event, Event_Type, Time, Additional_Info
    """
    mapping_data = []
    
    try:
        # Process individual events
        if not individual_df.empty and 'Swimmer' in individual_df.columns and 'Event' in individual_df.columns:
            for _, row in individual_df.iterrows():
                swimmer_data = {
                    'Swimmer': row['Swimmer'],
                    'Event': row['Event'],
                    'Event_Type': 'Individual',
                    'Time': row.get('Time', 'N/A'),
                    'Additional_Info': ''
                }
                
                # Add strategic points if available
                if 'Strategic_Points' in row and pd.notna(row['Strategic_Points']):
                    swimmer_data['Additional_Info'] = f"Strategic Points: {row['Strategic_Points']}"
                
                mapping_data.append(swimmer_data)
        
        # Process relay events
        if not relay_df.empty and 'Swimmer' in relay_df.columns and 'Relay' in relay_df.columns:
            for _, row in relay_df.iterrows():
                swimmer_data = {
                    'Swimmer': row['Swimmer'],
                    'Event': row['Relay'],
                    'Event_Type': 'Relay',
                    'Time': row.get('Time', 'N/A'),
                    'Additional_Info': f"Leg: {row.get('Leg', 'Unknown')}"
                }
                mapping_data.append(swimmer_data)
        
        # Convert to DataFrame
        if mapping_data:
            mapping_df = pd.DataFrame(mapping_data)
            
            # Sort by swimmer name, then by event type (Individual first), then by event name
            mapping_df['Sort_Event_Type'] = mapping_df['Event_Type'].map({'Individual': 1, 'Relay': 2})
            mapping_df = mapping_df.sort_values(['Swimmer', 'Sort_Event_Type', 'Event'])
            mapping_df = mapping_df.drop('Sort_Event_Type', axis=1)
            
            # Add event count per swimmer
            swimmer_counts = mapping_df['Swimmer'].value_counts().to_dict()
            mapping_df['Total_Events'] = mapping_df['Swimmer'].map(swimmer_counts)
            
            # Reorder columns for better readability
            column_order = ['Swimmer', 'Total_Events', 'Event', 'Event_Type', 'Time', 'Additional_Info']
            mapping_df = mapping_df[column_order]
            
            return mapping_df
        else:
            # Return empty DataFrame with proper columns if no data
            return pd.DataFrame(columns=['Swimmer', 'Total_Events', 'Event', 'Event_Type', 'Time', 'Additional_Info'])
            
    except Exception as e:
        print(f"❌ Error creating swimmer event mapping: {e}")
        # Return empty DataFrame with proper columns on error
        return pd.DataFrame(columns=['Swimmer', 'Total_Events', 'Event', 'Event_Type', 'Time', 'Additional_Info'])


def create_swimmer_summary_mapping(individual_df, relay_df):
    """
    Create a condensed summary showing each swimmer and their event count breakdown.
    
    Args:
        individual_df: DataFrame with individual event assignments
        relay_df: DataFrame with relay event assignments
    
    Returns:
        DataFrame with columns: Swimmer, Individual_Events, Relay_Events, Total_Events, Event_List
    """
    try:
        # Collect all swimmers and their events
        swimmer_events = {}
        
        # Process individual events
        if not individual_df.empty and 'Swimmer' in individual_df.columns:
            for _, row in individual_df.iterrows():
                swimmer = row['Swimmer']
                event = row['Event']
                
                if swimmer not in swimmer_events:
                    swimmer_events[swimmer] = {'individual': [], 'relay': []}
                
                swimmer_events[swimmer]['individual'].append(event)
        
        # Process relay events
        if not relay_df.empty and 'Swimmer' in relay_df.columns:
            for _, row in relay_df.iterrows():
                swimmer = row['Swimmer']
                relay = row['Relay']
                leg = row.get('Leg', '')
                
                if swimmer not in swimmer_events:
                    swimmer_events[swimmer] = {'individual': [], 'relay': []}
                
                # Format relay with leg info
                relay_info = f"{relay} ({leg})" if leg else relay
                swimmer_events[swimmer]['relay'].append(relay_info)
        
        # Build summary data
        summary_data = []
        for swimmer, events in swimmer_events.items():
            individual_count = len(events['individual'])
            relay_count = len(events['relay'])
            total_count = individual_count + relay_count
            
            # Create event list string
            all_events = []
            if events['individual']:
                all_events.extend(events['individual'])
            if events['relay']:
                all_events.extend(events['relay'])
            
            event_list = '; '.join(all_events)
            
            summary_data.append({
                'Swimmer': swimmer,
                'Individual_Events': individual_count,
                'Relay_Events': relay_count,
                'Total_Events': total_count,
                'Event_List': event_list
            })
        
        # Convert to DataFrame and sort
        if summary_data:
            summary_df = pd.DataFrame(summary_data)
            summary_df = summary_df.sort_values(['Total_Events', 'Swimmer'], ascending=[False, True])
            return summary_df
        else:
            return pd.DataFrame(columns=['Swimmer', 'Individual_Events', 'Relay_Events', 'Total_Events', 'Event_List'])
            
    except Exception as e:
        print(f"❌ Error creating swimmer summary mapping: {e}")
        return pd.DataFrame(columns=['Swimmer', 'Individual_Events', 'Relay_Events', 'Total_Events', 'Event_List'])


def ensure_directory_exists(filepath):
    """Ensure the directory for the given filepath exists."""
    directory = os.path.dirname(filepath)
    if directory and not os.path.exists(directory):
        try:
            os.makedirs(directory, exist_ok=True)
            print(f"Created directory: {directory}")
        except Exception as e:
            print(f"Error creating directory {directory}: {e}")
            raise


def export_lineup_to_txt(individual_df, relay_df, team_name="Team", filename=None):
    """Export lineup to a text file for coaches."""
    if filename is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_team_name = "".join(c for c in team_name if c.isalnum() or c in (' ', '-', '_')).rstrip()
        filename = f"{safe_team_name.replace(' ', '_')}_lineup_{timestamp}.txt"
    
    try:
        # Ensure directory exists
        ensure_directory_exists(filename)
        
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
            
            # Swimmer Event Summary
            f.write("\n=== SWIMMER EVENT ASSIGNMENTS ===\n")
            swimmer_summary = create_swimmer_summary_mapping(individual_df, relay_df)
            if not swimmer_summary.empty:
                for _, row in swimmer_summary.iterrows():
                    f.write(f"\n{row['Swimmer']} ({row['Total_Events']} events total):\n")
                    if row['Individual_Events'] > 0:
                        individual_events = [e for e in row['Event_List'].split('; ') if not any(relay in e for relay in ['Relay'])]
                        if individual_events:
                            f.write(f"  Individual: {', '.join(individual_events)}\n")
                    if row['Relay_Events'] > 0:
                        relay_events = [e for e in row['Event_List'].split('; ') if any(relay in e for relay in ['Relay'])]
                        if relay_events:
                            f.write(f"  Relays: {', '.join(relay_events)}\n")
            else:
                f.write("No swimmer assignments to export.\n")
            
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
        
        print(f"✅ Text file exported successfully: {filename}")
        return filename
        
    except Exception as e:
        print(f"❌ Error exporting lineup: {e}")
        return None


def export_lineup_to_excel(individual_df, relay_df, team_name="Team", filename=None):
    """Export lineup to Excel file with multiple sheets including swimmer event mapping."""
    if filename is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_team_name = "".join(c for c in team_name if c.isalnum() or c in (' ', '-', '_')).rstrip()
        filename = f"{safe_team_name.replace(' ', '_')}_lineup_{timestamp}.xlsx"
    
    try:
        # Ensure directory exists
        ensure_directory_exists(filename)
        
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
            
            # Swimmer Event Mapping Sheet (Detailed)
            swimmer_mapping = create_swimmer_event_mapping(individual_df, relay_df)
            if not swimmer_mapping.empty:
                swimmer_mapping.to_excel(writer, sheet_name='Swimmer Events', index=False)
            
            # Swimmer Summary Sheet (Condensed)
            swimmer_summary = create_swimmer_summary_mapping(individual_df, relay_df)
            if not swimmer_summary.empty:
                swimmer_summary.to_excel(writer, sheet_name='Swimmer Summary', index=False)
            
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
        
        print(f"✅ Excel file exported successfully: {filename}")
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
            ensure_directory_exists(individual_filename)
            
            export_individual = individual_df.copy()
            export_individual['Time_Sec'] = export_individual['Time'].apply(time_to_seconds)
            export_individual = export_individual.sort_values(['Event', 'Time_Sec'])
            export_individual = export_individual.drop('Time_Sec', axis=1)
            export_individual.to_csv(individual_filename, index=False)
            exported_files.append(individual_filename)
        
        # Export relay events
        if not relay_df.empty and 'Relay' in relay_df.columns:
            relay_filename = f"{base_filename}_relay.csv"
            ensure_directory_exists(relay_filename)
            
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


def export_lineup_to_files(individual_df, relay_df, team_name="Team", output_folder=None):
    """
    Export lineup to multiple file formats for web application.
    
    Args:
        individual_df: DataFrame with individual event lineup
        relay_df: DataFrame with relay event lineup  
        team_name: Name of the team for filename generation
        output_folder: Directory to save files (if None, saves to current directory)
    
    Returns:
        List of successfully exported filenames (relative paths for web download)
    """
    exported_files = []
    
    try:
        # Generate timestamp for unique filenames
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_team_name = "".join(c for c in team_name if c.isalnum() or c in (' ', '-', '_')).rstrip()
        base_filename = f"{safe_team_name.replace(' ', '_')}_lineup_{timestamp}"
        
        # Ensure output folder exists
        if output_folder:
            os.makedirs(output_folder, exist_ok=True)
        
        # Export to text file
        txt_filename = f"{base_filename}.txt"
        if output_folder:
            txt_filepath = os.path.join(output_folder, txt_filename)
        else:
            txt_filepath = txt_filename
            
        txt_file = export_lineup_to_txt(individual_df, relay_df, team_name, txt_filepath)
        if txt_file:
            exported_files.append(os.path.basename(txt_file))
        
        # Export to Excel file
        excel_filename = f"{base_filename}.xlsx"
        if output_folder:
            excel_filepath = os.path.join(output_folder, excel_filename)
        else:
            excel_filepath = excel_filename
            
        excel_file = export_lineup_to_excel(individual_df, relay_df, team_name, excel_filepath)
        if excel_file:
            exported_files.append(os.path.basename(excel_file))
        
        return exported_files
        
    except Exception as e:
        print(f"❌ Error in export_lineup_to_files: {e}")
        return exported_files


# Legacy function for backward compatibility
def export_lineup_to_file(individual_df, relay_df, filename="lineup_export.txt"):
    """Legacy export function - maintained for backward compatibility."""
    return export_lineup_to_txt(individual_df, relay_df, "Team", filename)