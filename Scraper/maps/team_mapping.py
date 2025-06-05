"""
Simple runner script for team mapping with common configurations.
"""

from enhanced_team_mapping import TeamMappingManager
import os
import json

def run_mapping_ranges():
    """Run mapping for predefined ranges."""
    
    ranges = [
        (1, 10000),      # First 500 teams
        #(501, 1000),   # Next 500 teams
        #(1001, 1500),  # Next 500 teams
        #(1501, 2000),  # Next 500 teams
    ]
    
    manager = TeamMappingManager(output_dir="team_mappings")
    
    for start, end in ranges:
        print(f"\n{'='*50}")
        print(f"Processing teams {start} to {end}")
        print(f"{'='*50}")
        
        try:
            college_mappings, excluded_mappings, debug_info = manager.process_team_batch(start, end)
            print(f"Range {start}-{end} completed successfully!")
            print(f"  College teams found: {len(college_mappings)}")
            print(f"  Teams excluded: {len(excluded_mappings)}")
        except Exception as e:
            print(f"Error processing range {start}-{end}: {e}")
            continue

def merge_results():
    """Merge all result files into consolidated files."""
    
    output_dir = "team_mappings"
    if not os.path.exists(output_dir):
        print("No team_mappings directory found!")
        return
    
    all_college_teams = {}
    all_excluded_teams = {}
    all_debug_info = {}
    
    # Find all result files
    files = os.listdir(output_dir)
    college_files = [f for f in files if f.startswith("college_teams_")]
    excluded_files = [f for f in files if f.startswith("excluded_teams_")]
    debug_files = [f for f in files if f.startswith("debug_info_")]
    
    # Merge college teams
    for filename in college_files:
        filepath = os.path.join(output_dir, filename)
        with open(filepath, 'r') as f:
            data = json.load(f)
            all_college_teams.update(data)
    
    # Merge excluded teams
    for filename in excluded_files:
        filepath = os.path.join(output_dir, filename)
        with open(filepath, 'r') as f:
            data = json.load(f)
            all_excluded_teams.update(data)
    
    # Merge debug info
    for filename in debug_files:
        filepath = os.path.join(output_dir, filename)
        with open(filepath, 'r') as f:
            data = json.load(f)
            all_debug_info.update(data)
    
    # Save merged results
    with open(os.path.join(output_dir, "all_college_teams.json"), 'w') as f:
        json.dump(all_college_teams, f, indent=4, sort_keys=True)
    
    with open(os.path.join(output_dir, "all_excluded_teams.json"), 'w') as f:
        json.dump(all_excluded_teams, f, indent=4, sort_keys=True)
    
    with open(os.path.join(output_dir, "all_debug_info.json"), 'w') as f:
        json.dump(all_debug_info, f, indent=4, sort_keys=True)
    
    print(f"Merged results saved:")
    print(f"  Total college teams: {len(all_college_teams)}")
    print(f"  Total excluded teams: {len(all_excluded_teams)}")
    print(f"  Files processed: {len(college_files)} college, {len(excluded_files)} excluded")

def show_stats():
    """Show statistics from the mapping results."""
    
    output_dir = "team_mappings"
    
    try:
        with open(os.path.join(output_dir, "all_college_teams.json"), 'r') as f:
            college_teams = json.load(f)
        
        with open(os.path.join(output_dir, "all_excluded_teams.json"), 'r') as f:
            excluded_teams = json.load(f)
        
        with open(os.path.join(output_dir, "all_debug_info.json"), 'r') as f:
            debug_info = json.load(f)
        
        print(f"Team Mapping Statistics:")
        print(f"  College teams found: {len(college_teams)}")
        print(f"  Teams excluded: {len(excluded_teams)}")
        print(f"  Total teams processed: {len(debug_info)}")
        
        # Breakdown by exclusion reason
        reasons = {}
        for team_id, info in debug_info.items():
            reason = info.get('reason', 'Unknown')
            reasons[reason] = reasons.get(reason, 0) + 1
        
        print(f"\nBreakdown by classification:")
        for reason, count in sorted(reasons.items()):
            print(f"  {reason}: {count}")
        
        # Sample college teams
        print(f"\nSample college teams found:")
        sample_teams = list(college_teams.items())[:10]
        for team_id, team_name in sample_teams:
            print(f"  {team_id}: {team_name}")
        
    except FileNotFoundError:
        print("Merged results not found. Run merge_results() first.")

def main():
    """Interactive menu for running different operations."""
    
    while True:
        print(f"\n{'='*50}")
        print("Team Mapping Tool")
        print(f"{'='*50}")
        print("1. Run mapping for predefined ranges")
        print("2. Merge all results into consolidated files")
        print("3. Show statistics")
        print("4. Exit")
        
        choice = input("\nEnter your choice (1-4): ").strip()
        
        if choice == '1':
            run_mapping_ranges()
        elif choice == '2':
            merge_results()
        elif choice == '3':
            show_stats()
        elif choice == '4':
            break
        else:
            print("Invalid choice. Please enter 1-4.")

if __name__ == "__main__":
    main()