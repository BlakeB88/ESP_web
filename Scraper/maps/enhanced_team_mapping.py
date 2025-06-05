import requests
from bs4 import BeautifulSoup
import json
import re
import time
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, Optional, Tuple
import argparse

class TeamMappingConfig:
    """Configuration class for team mapping parameters."""
    
    # Known college teams that don't have "university" or "college" in their name
    KNOWN_COLLEGES = {
        'ucla', 'usc', 'mit', 'cal', 'stanford', 'duke', 'rice', 'yale', 
        'harvard', 'princeton', 'dartmouth', 'brown', 'columbia', 'cornell',
        'upenn', 'penn', 'northwestern', 'vanderbilt', 'emory', 'wake forest',
        'villanova', 'georgetown', 'notre dame', 'bc', 'boston college',
        'ga tech', 'georgia tech', 'cal tech', 'caltech', 'johns hopkins',
        'carnegie mellon', 'tufts', 'brandeis', 'colgate', 'bucknell',
        'lafayette', 'lehigh', 'navy', 'army', 'air force', 'coast guard',
        'usma', 'usna', 'usafa', 'uscga'
    }
    
    # College indicators (positive matches)
    COLLEGE_INDICATORS = [
        r'\buniversity\b', r'\bcollege\b', r'\binstitute\b', r'\bacademy\b',
        r'\b(u of|univ of|university of)\b', r'\btech\b', r'\bstate\b'
    ]
    
    # High school exclusions (priority exclusions)
    HIGH_SCHOOL_EXCLUSIONS = [
        r'\bhigh school\b', r'\bhigh\b', r'\bhs\b', r'\bprep\b', 
        r'\bpreparatory\b', r'\bacademy\b.*\bhigh\b', r'\bsecondary\b',
        r'\b(9th|10th|11th|12th)\b', r'\bfreshman\b', r'\bsophomore\b',
        r'\bjunior\b.*\bhigh\b', r'\bsenior\b.*\bhigh\b'
    ]
    
    # Club team exclusions
    CLUB_EXCLUSIONS = [
        r'\bclub\b', r'\bswim club\b', r'\baquatic club\b', r'\bswimming club\b',
        r'\bmasters\b', r'\byouth\b', r'\bage group\b', r'\blearn to swim\b',
        r'\bcompetitive club\b', r'\bsummer league\b'
    ]

class TeamClassifier:
    """Handles team classification logic."""
    
    def __init__(self, config: TeamMappingConfig):
        self.config = config
    
    def is_high_school_team(self, team_name: str) -> bool:
        """Check if team is a high school team (priority exclusion)."""
        team_name_lower = team_name.lower()
        return any(re.search(pattern, team_name_lower) for pattern in self.config.HIGH_SCHOOL_EXCLUSIONS)
    
    def is_club_team(self, team_name: str) -> bool:
        """Check if team is a club team (priority exclusion)."""
        team_name_lower = team_name.lower()
        return any(re.search(pattern, team_name_lower) for pattern in self.config.CLUB_EXCLUSIONS)
    
    def is_known_college(self, team_name: str) -> bool:
        """Check if team is a known college without standard indicators."""
        team_name_lower = team_name.lower().strip()
        return any(known_college in team_name_lower for known_college in self.config.KNOWN_COLLEGES)
    
    def has_college_indicators(self, team_name: str) -> bool:
        """Check if team has standard college indicators."""
        team_name_lower = team_name.lower()
        return any(re.search(indicator, team_name_lower) for indicator in self.config.COLLEGE_INDICATORS)
    
    def is_college_team(self, team_name: str) -> Tuple[bool, str]:
        """
        Determine if team is a college team with reasoning.
        Returns (is_college, reason).
        """
        if not team_name:
            return False, "No team name"
        
        # Priority exclusions first
        if self.is_high_school_team(team_name):
            return False, "High school team"
        
        if self.is_club_team(team_name):
            return False, "Club team"
        
        # Check for college indicators
        if self.is_known_college(team_name):
            return True, "Known college"
        
        if self.has_college_indicators(team_name):
            return True, "College indicators"
        
        return False, "No college indicators"

class TeamFetcher:
    """Handles fetching team information from Swimcloud."""
    
    def __init__(self, max_workers: int = 5):
        self.max_workers = max_workers
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
    
    def get_team_name(self, team_id: int, session: requests.Session) -> Optional[str]:
        """Fetch team name from Swimcloud team page."""
        url = f"https://www.swimcloud.com/team/{team_id}/"
        
        try:
            response = session.get(url, headers=self.headers, timeout=10)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Try multiple selectors for team name
            selectors = ['h1', '.team-name', '.page-title', 'title']
            
            for selector in selectors:
                element = soup.select_one(selector)
                if element:
                    team_name = element.get_text().strip()
                    # Clean up title tags that might have extra text
                    if selector == 'title':
                        team_name = team_name.split('|')[0].strip()
                    if team_name:
                        return team_name
            
            return None
            
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 403:
                print(f"403 Forbidden for team ID {team_id}")
            elif e.response.status_code == 404:
                print(f"Team ID {team_id} not found (404)")
            else:
                print(f"HTTP error for team ID {team_id}: {e}")
            return None
        except Exception as e:
            print(f"Error fetching team ID {team_id}: {e}")
            return None

class TeamMappingManager:
    """Main class for managing team mapping operations."""
    
    def __init__(self, output_dir: str = "team_mappings"):
        self.output_dir = output_dir
        self.config = TeamMappingConfig()
        self.classifier = TeamClassifier(self.config)
        self.fetcher = TeamFetcher()
        
        # Ensure output directory exists
        os.makedirs(output_dir, exist_ok=True)
    
    def load_existing_mappings(self, filename: str) -> Dict[str, str]:
        """Load existing mappings from file."""
        filepath = os.path.join(self.output_dir, filename)
        try:
            with open(filepath, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            return {}
    
    def save_mappings(self, mappings: Dict[str, str], filename: str):
        """Save mappings to file."""
        filepath = os.path.join(self.output_dir, filename)
        with open(filepath, 'w') as f:
            json.dump(mappings, f, indent=4, sort_keys=True)
    
    def save_debug_info(self, debug_info: Dict, filename: str):
        """Save debug information to file."""
        filepath = os.path.join(self.output_dir, filename)
        with open(filepath, 'w') as f:
            json.dump(debug_info, f, indent=4, sort_keys=True)
    
    def process_team_batch(self, start_id: int, end_id: int, batch_size: int = 50):
        """Process a batch of team IDs with multithreading."""
        college_mappings_file = f"college_teams_{start_id}_{end_id}.json"
        excluded_mappings_file = f"excluded_teams_{start_id}_{end_id}.json"
        debug_file = f"debug_info_{start_id}_{end_id}.json"
        
        # Load existing mappings
        college_mappings = self.load_existing_mappings(college_mappings_file)
        excluded_mappings = self.load_existing_mappings(excluded_mappings_file)
        debug_info = self.load_existing_mappings(debug_file) if os.path.exists(os.path.join(self.output_dir, debug_file)) else {}
        
        # Create session pool
        sessions = [requests.Session() for _ in range(self.fetcher.max_workers)]
        
        def process_team(team_id: int, session: requests.Session) -> Tuple[int, Optional[str], bool, str]:
            """Process a single team ID."""
            team_name = self.fetcher.get_team_name(team_id, session)
            if team_name:
                is_college, reason = self.classifier.is_college_team(team_name)
                return team_id, team_name, is_college, reason
            return team_id, None, False, "Team not found"
        
        # Process teams in batches
        team_ids_to_process = [
            tid for tid in range(start_id, end_id + 1) 
            if str(tid) not in college_mappings and str(tid) not in excluded_mappings
        ]
        
        print(f"Processing {len(team_ids_to_process)} teams from {start_id} to {end_id}")
        
        processed_count = 0
        with ThreadPoolExecutor(max_workers=self.fetcher.max_workers) as executor:
            # Submit tasks in batches to control memory usage
            for i in range(0, len(team_ids_to_process), batch_size):
                batch = team_ids_to_process[i:i + batch_size]
                
                # Submit batch
                future_to_team = {
                    executor.submit(process_team, team_id, sessions[j % len(sessions)]): team_id 
                    for j, team_id in enumerate(batch)
                }
                
                # Process results
                for future in as_completed(future_to_team):
                    team_id, team_name, is_college, reason = future.result()
                    team_id_str = str(team_id)
                    
                    # Store debug information
                    debug_info[team_id_str] = {
                        "team_name": team_name,
                        "is_college": is_college,
                        "reason": reason
                    }
                    
                    if team_name:
                        if is_college:
                            college_mappings[team_id_str] = team_name
                            print(f"✓ College team {team_id}: {team_name} ({reason})")
                        else:
                            excluded_mappings[team_id_str] = team_name
                            print(f"✗ Excluded team {team_id}: {team_name} ({reason})")
                    else:
                        print(f"? Team {team_id}: Not found")
                    
                    processed_count += 1
                    
                    # Save progress every 10 teams
                    if processed_count % 10 == 0:
                        self.save_mappings(college_mappings, college_mappings_file)
                        self.save_mappings(excluded_mappings, excluded_mappings_file)
                        self.save_debug_info(debug_info, debug_file)
                        print(f"Progress: {processed_count}/{len(team_ids_to_process)} teams processed")
                
                # Small delay between batches
                time.sleep(0.5)
        
        # Final save
        self.save_mappings(college_mappings, college_mappings_file)
        self.save_mappings(excluded_mappings, excluded_mappings_file)
        self.save_debug_info(debug_info, debug_file)
        
        # Close sessions
        for session in sessions:
            session.close()
        
        print(f"Batch complete: {len(college_mappings)} college teams, {len(excluded_mappings)} excluded teams")
        return college_mappings, excluded_mappings, debug_info

def main():
    """Main function with command line argument parsing."""
    parser = argparse.ArgumentParser(description="Map Swimcloud team IDs to college teams")
    parser.add_argument("--start", type=int, default=1, help="Start team ID")
    parser.add_argument("--end", type=int, default=1000, help="End team ID")
    parser.add_argument("--output-dir", type=str, default="team_mappings", help="Output directory")
    parser.add_argument("--batch-size", type=int, default=50, help="Batch size for processing")
    
    args = parser.parse_args()
    
    manager = TeamMappingManager(output_dir=args.output_dir)
    manager.process_team_batch(args.start, args.end, args.batch_size)
    
    print(f"Team mapping completed. Check {args.output_dir}/ for results.")

if __name__ == "__main__":
    main()