import json

def load_team_mappings(json_file="Scraper/maps/team_mappings/all_college_teams.json"):
    """
    Load team ID to name mappings from JSON file.
    Expected format: {"34": "Georgia Institute of Technology", ...}
    """
    try:
        with open(json_file, 'r', encoding='utf-8') as f:
            mappings = json.load(f)
        print(f"[DEBUG] Loaded {len(mappings)} team mappings from {json_file}")
        return mappings
    except FileNotFoundError:
        print(f"[ERROR] Mapping file {json_file} not found")
        return {}
    except json.JSONDecodeError as e:
        print(f"[ERROR] Invalid JSON in {json_file}: {e}")
        return {}

def find_team_id(team_name, mappings):
    """
    Find SwimCloud ID for a team using various matching strategies.
    """
    if not mappings:
        return None
    
    print(f"[DEBUG] Looking for team: '{team_name}'")
    
    # Direct match (case-insensitive)
    for team_id, mapped_name in mappings.items():
        if team_name.lower() == mapped_name.lower():
            print(f"[DEBUG] Direct match found: {mapped_name} -> {team_id}")
            return team_id
    
    # Partial match strategies
    team_lower = team_name.lower()
    
    # Check if input is contained in any mapping
    for team_id, mapped_name in mappings.items():
        mapped_lower = mapped_name.lower()
        if team_lower in mapped_lower or mapped_lower in team_lower:
            print(f"[DEBUG] Partial match found: {mapped_name} -> {team_id}")
            return team_id
    
    # Try common university variations
    variations = [
        f"University of {team_name}",
        f"{team_name} University",
        f"University {team_name}",
        f"{team_name} State University",
        f"{team_name} State",
        f"{team_name} College"
    ]
    
    for variation in variations:
        for team_id, mapped_name in mappings.items():
            if variation.lower() == mapped_name.lower():
                print(f"[DEBUG] Variation match found: {mapped_name} -> {team_id}")
                return team_id
    
    # Fuzzy matching with word overlap
    team_words = set(team_lower.split())
    best_match = None
    best_score = 0
    
    for team_id, mapped_name in mappings.items():
        mapped_words = set(mapped_name.lower().split())
        if team_words and mapped_words:
            overlap = len(team_words.intersection(mapped_words))
            total_words = len(team_words.union(mapped_words))
            score = overlap / total_words if total_words > 0 else 0
            
            if score > best_score and score > 0.5:
                best_match = team_id
                best_score = score
    
    if best_match:
        print(f"[DEBUG] Fuzzy match found with score {best_score:.2f} -> {best_match}")
        return best_match
    
    print(f"[DEBUG] No match found for '{team_name}'")
    return None