# output.py

from utils import time_to_seconds


def print_individual_lineup(lineup_df):
    if lineup_df.empty:
        print("No individual lineup generated.")
        return
    print("\n=== INDIVIDUAL LINEUP ===")
    for event in sorted(lineup_df['Event'].unique()):
        print(f"\n{event}:")
        for _, row in lineup_df[lineup_df['Event'] == event].iterrows():
            print(f"  {row['Swimmer']} – {row['Time']}")


def print_relay_lineup(relay_df):
    if relay_df.empty:
        print("No relay lineup generated.")
        return
    print("\n=== RELAY LINEUP ===")
    for relay in sorted(relay_df['Relay'].unique()):
        print(f"\n{relay}:")
        subset = relay_df[relay_df['Relay'] == relay].copy()
        subset = subset.sort_values('Leg')
        for _, row in subset.iterrows():
            print(f"  {row['Leg']}: {row['Swimmer']} – {row['Time']}")


def print_detailed_lineup(individual_df, relay_df):
    choice = input("\nShow detailed lineup? (y/n): ").strip().lower()
    if choice != 'y':
        return

    print("\n=== DETAILED INDIVIDUAL LINEUP ===")
    # Check if individual_df is empty or missing 'Event' column
    if individual_df.empty or 'Event' not in individual_df.columns:
        print("No individual events to display.")
    else:
        for event in sorted(individual_df['Event'].unique()):
            print(f"\n{event}:")
            block = individual_df[individual_df['Event'] == event].copy()
            block['Time_Sec'] = block['Time'].apply(time_to_seconds)
            block = block.sort_values('Time_Sec')
            for i, (_, row) in enumerate(block.iterrows(), 1):
                extra = f" (Strategic Points: {row['Strategic_Points']})" if 'Strategic_Points' in row else ""
                print(f"  {i}. {row['Swimmer']} – {row['Time']}{extra}")

    print("\n=== DETAILED RELAY LINEUP ===")
    # Check if relay_df is empty or missing 'Relay' column
    if relay_df.empty or 'Relay' not in relay_df.columns:
        print("No relay events to display.")
    else:
        for relay in sorted(relay_df['Relay'].unique()):
            print(f"\n{relay}:")
            block = relay_df[relay_df['Relay'] == relay].copy()
            block = block.sort_values('Leg')
            for _, row in block.iterrows():
                print(f"  {row['Leg']}: {row['Swimmer']} – {row['Time']}")