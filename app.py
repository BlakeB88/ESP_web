# app.py - Main Flask application
from flask import Flask, render_template, request, jsonify, send_file
import json
import pandas as pd
from datetime import datetime
import os

# Import your existing modules
from Scraper.swimmer_scraper import scrape_and_save
from Scraper.data_processor import lineup_spread
from preferences import (
    get_scraper_event_codes,
)
from utils import filter_events_by_preferences, validate_swimmer_data, clean_time_data
from assignment import (
    create_relay_teams,
    round_robin_assignment,
    strategic_dual_meet_assignment,
    create_strategic_relay_teams,
)
from scoring import calculate_dual_meet_score
from output import (
    print_individual_lineup,
    print_relay_lineup,
    print_detailed_lineup,
    export_lineup_to_files,  # You'll need to create this function
)

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'generated_lineups'

# Create upload folder if it doesn't exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# FIXED: Updated RELAY_EVENT_MAPPING to match HTML values exactly
RELAY_EVENT_MAPPING = {
    # HTML radio button values (matching your UI exactly)
    1: ["200 Medley Relay", "200 Free Relay"],        # "200 Medley & 200 Free"
    2: ["200 Medley Relay", "400 Free Relay"],        # "200 Medley & 400 Free"
    3: ["400 Medley Relay", "200 Free Relay"],        # "400 Medley & 200 Free"
    4: ["400 Medley Relay", "400 Free Relay"],        # "400 Medley & 400 Free"
    5: ["200 Medley Relay", "400 Medley Relay", "200 Free Relay", "400 Free Relay"],  # "All four relays"
    6: ["200 Medley Relay", "400 Medley Relay"],      # "Medley relays only (200 & 400)"
    7: ["200 Free Relay", "400 Free Relay"],          # "Free relays only (200 & 400)"
    
    # String versions for backward compatibility
    "1": ["200 Medley Relay", "200 Free Relay"],
    "2": ["200 Medley Relay", "400 Free Relay"],
    "3": ["400 Medley Relay", "200 Free Relay"],
    "4": ["400 Medley Relay", "400 Free Relay"],
    "5": ["200 Medley Relay", "400 Medley Relay", "200 Free Relay", "400 Free Relay"],
    "6": ["200 Medley Relay", "400 Medley Relay"],
    "7": ["200 Free Relay", "400 Free Relay"],
    
    # Direct event names (for backward compatibility)
    "200 Medley Relay": ["200 Medley Relay"],
    "400 Medley Relay": ["400 Medley Relay"], 
    "200 Free Relay": ["200 Free Relay"],
    "400 Free Relay": ["400 Free Relay"],
    
    # Frontend radio button text values (for extra safety)
    "200 Medley & 200 Free": ["200 Medley Relay", "200 Free Relay"],
    "200 Medley & 400 Free": ["200 Medley Relay", "400 Free Relay"],
    "400 Medley & 200 Free": ["400 Medley Relay", "200 Free Relay"],
    "400 Medley & 400 Free": ["400 Medley Relay", "400 Free Relay"],
    "All four relays": ["200 Medley Relay", "400 Medley Relay", "200 Free Relay", "400 Free Relay"],
    "Medley relays only (200 & 400)": ["200 Medley Relay", "400 Medley Relay"],
    "Free relays only (200 & 400)": ["200 Free Relay", "400 Free Relay"]
}

def convert_relay_events(relay_event_data):
    """Convert relay event selection to event names - IMPROVED VERSION"""
    print(f"[DEBUG] convert_relay_events input: {relay_event_data} (type: {type(relay_event_data)})")
    
    converted_events = []
    
    # Handle different input formats
    if isinstance(relay_event_data, list):
        # If it's a list, process each item
        for event in relay_event_data:
            print(f"[DEBUG] Processing list item: {event} (type: {type(event)})")
            
            # Convert to string or int for lookup
            lookup_key = event
            if isinstance(event, str) and event.isdigit():
                lookup_key = int(event)
            
            if lookup_key in RELAY_EVENT_MAPPING:
                result = RELAY_EVENT_MAPPING[lookup_key]
                print(f"[DEBUG] Found mapping: {lookup_key} -> {result}")
                if isinstance(result, list):
                    converted_events.extend(result)
                else:
                    converted_events.append(result)
            else:
                # Try as direct event name
                if isinstance(event, str) and any(event in relay_name for relay_name in ["200 Medley Relay", "400 Medley Relay", "200 Free Relay", "400 Free Relay"]):
                    converted_events.append(event)
                    print(f"[DEBUG] Added direct event name: {event}")
                else:
                    print(f"[WARNING] Unknown relay event in list: {event}")
    
    elif isinstance(relay_event_data, (str, int)):
        # Single selection
        print(f"[DEBUG] Processing single selection: {relay_event_data}")
        
        # Convert to appropriate type for lookup
        lookup_key = relay_event_data
        if isinstance(relay_event_data, str) and relay_event_data.isdigit():
            lookup_key = int(relay_event_data)
        
        if lookup_key in RELAY_EVENT_MAPPING:
            result = RELAY_EVENT_MAPPING[lookup_key]
            print(f"[DEBUG] Found mapping: {lookup_key} -> {result}")
            if isinstance(result, list):
                converted_events.extend(result)
            else:
                converted_events.append(result)
        else:
            # Try as direct event name
            if isinstance(relay_event_data, str) and any(relay_event_data in relay_name for relay_name in ["200 Medley Relay", "400 Medley Relay", "200 Free Relay", "400 Free Relay"]):
                converted_events.append(relay_event_data)
                print(f"[DEBUG] Added direct event name: {relay_event_data}")
            else:
                print(f"[WARNING] Unknown relay event: {relay_event_data}")
    
    else:
        print(f"[ERROR] Unexpected relay_event_data type: {type(relay_event_data)}")
    
    # Remove duplicates while preserving order
    unique_events = []
    for event in converted_events:
        if event not in unique_events:
            unique_events.append(event)
    
    print(f"[DEBUG] Final converted relay events: {unique_events}")
    return unique_events

# Add event mapping functions
def convert_distance_events(distance_event_list):
    """Convert distance event IDs to event names"""
    DISTANCE_MAPPING = {
        1: ["1650 Free"],
        2: ["1000 Free"],
        3: ["1650 Free", "1000 Free"],
        4: []  # Neither
    }
    converted_events = []
    for event in distance_event_list:
        if isinstance(event, int) and event in DISTANCE_MAPPING:
            converted_events.extend(DISTANCE_MAPPING[event])
        elif isinstance(event, str) and event.isdigit():
            int_event = int(event)
            if int_event in DISTANCE_MAPPING:
                converted_events.extend(DISTANCE_MAPPING[int_event])
        elif isinstance(event, str):
            converted_events.append(event)
    return converted_events

def convert_im_events(im_event_list):
    """Convert IM event IDs to event names"""
    IM_MAPPING = {
        1: ["200 IM"],
        2: ["400 IM"],
        3: ["200 IM", "400 IM"],
        4: []  # Neither
    }
    converted_events = []
    for event in im_event_list:
        if isinstance(event, int) and event in IM_MAPPING:
            converted_events.extend(IM_MAPPING[event])
        elif isinstance(event, str) and event.isdigit():
            int_event = int(event)
            if int_event in IM_MAPPING:
                converted_events.extend(IM_MAPPING[int_event])
        elif isinstance(event, str):
            converted_events.append(event)
    return converted_events

@app.route('/')
def index():
    """Serve the main web interface"""
    return render_template('index.html')

@app.route('/api/generate-lineup', methods=['POST'])
def generate_lineup():
    """Process lineup generation request"""
    try:
        data = request.json
        
        # Extract form data
        mode = data.get('mode')
        pool_config = data.get('poolConfig')
        team_name = data.get('teamName')
        year = data.get('year')
        gender = data.get('gender')
        opponent_name = data.get('opponentName', '')
        events = data.get('events')
        
        # Validate required fields
        if not all([team_name, year, gender]):
            return jsonify({'error': 'Missing required team information'}), 400
        
        if mode == 'dual' and not opponent_name:
            return jsonify({'error': 'Opponent name required for dual meet mode'}), 400
        
        # Process events - convert IDs to names BEFORE cleaning
        distance_events_raw = events.get('distanceEvents', [])
        im_events_raw = events.get('imEvents', [])
        relay_events_raw = events.get('relayEvents', [])
        
        # Convert event IDs to names BEFORE cleaning
        distance_events = convert_distance_events(distance_events_raw)
        im_events = convert_im_events(im_events_raw)
        relay_events = convert_relay_events(relay_events_raw)
        
        # Log what we received for debugging
        print(f"Debug - Raw distance events: {distance_events_raw}")
        print(f"Debug - Raw IM events: {im_events_raw}")
        print(f"Debug - Raw relay events: {relay_events_raw}")
        print(f"Debug - Converted distance events: {distance_events}")
        print(f"Debug - Converted IM events: {im_events}")
        print(f"Debug - Converted relay events: {relay_events}")
        
        if not (distance_events or im_events or relay_events):
            return jsonify({'error': 'At least one event must be selected'}), 400
        
        # Generate unique filenames
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        user_filename = f"{team_name.replace(' ', '_')}_{timestamp}_times.xlsx"
        
        if mode == 'single':
            result = process_single_team_lineup(
                team_name, year, gender, distance_events, im_events, 
                relay_events, pool_config, user_filename
            )
        else:
            opp_filename = f"{opponent_name.replace(' ', '_')}_{timestamp}_times.xlsx"
            result = process_dual_team_lineup(
                team_name, opponent_name, year, gender, distance_events, 
                im_events, relay_events, pool_config, user_filename, opp_filename
            )
        
        return jsonify(result)
        
    except Exception as e:
        print(f"Error in generate_lineup: {str(e)}")  # Debug logging
        return jsonify({'error': f'Error processing lineup: {str(e)}'}), 500

def process_single_team_lineup(team_name, year, gender, distance_events, 
                              im_events, relay_events, pool_config, filename):
    """Process single team optimization"""
    
    # Get events to scrape
    events_to_scrape = get_scraper_event_codes(distance_events, im_events)
    
    print(f"Debug - Processing single team with relay events: {relay_events}")
    
    # Scrape data
    scrape_and_save(
        team_name=team_name,
        year=year,
        gender=gender,
        filename=filename,
        selected_events=events_to_scrape,
    )
    
    # Load and process data
    times_df = pd.read_excel(filename)
    times_df = clean_time_data(times_df)
    
    if not validate_swimmer_data(times_df):
        raise ValueError("Data validation failed")
    
    # Create relay teams
    relay_lineup_df, swimmer_relay_counts = create_relay_teams(
        times_df, relay_events, max_total_events=4
    )
    
    # Filter and assign individual events
    individual_times_df = filter_events_by_preferences(times_df, distance_events, im_events)
    individual_lineup_df, final_swimmer_counts = round_robin_assignment(
        individual_times_df,
        max_events_per_swimmer=4,
        swimmers_per_event=pool_config['swimmers'],
        swimmer_relay_counts=swimmer_relay_counts,
    )
    
    # Generate output files
    output_files = export_lineup_to_files(
        individual_lineup_df, relay_lineup_df, team_name, 
        app.config['UPLOAD_FOLDER']
    )
    
    return {
        'success': True,
        'mode': 'single',
        'team_name': team_name,
        'swimmer_count': len(times_df),
        'individual_events': len(distance_events + im_events),
        'relay_events': len(relay_events),
        'output_files': output_files,
        'summary': {
            'total_swimmers': len(times_df),
            'events_assigned': len(individual_lineup_df),
            'relays_created': len(relay_lineup_df)
        }
    }

def process_dual_team_lineup(team_name, opponent_name, year, gender, 
                           distance_events, im_events, relay_events, 
                           pool_config, user_filename, opp_filename):
    """Process dual team strategic lineup"""
    
    events_to_scrape = get_scraper_event_codes(distance_events, im_events)
    
    print(f"Debug - Processing dual team with relay events: {relay_events}")
    
    # Scrape both teams - FIXED: Pass selected_events parameter correctly
    scrape_and_save(
        team_name=team_name,
        year=year,
        gender=gender,
        filename=user_filename,
        selected_events=events_to_scrape
    )
    scrape_and_save(
        team_name=opponent_name,
        year=year,
        gender=gender,
        filename=opp_filename,
        selected_events=events_to_scrape
    )
    
    # Load and process data
    user_df = clean_time_data(pd.read_excel(user_filename))
    opponent_df = clean_time_data(pd.read_excel(opp_filename))
    
    if not (validate_swimmer_data(user_df) and validate_swimmer_data(opponent_df)):
        raise ValueError("Data validation failed")
    
    # Create relay teams
    user_relay_df, user_relay_counts = create_relay_teams(
        user_df, relay_events, max_total_events=4
    )
    opponent_relay_df, opponent_relay_counts = create_relay_teams(
        opponent_df, relay_events, max_total_events=4
    )
    
    # Strategic assignments
    user_ind_df = filter_events_by_preferences(user_df, distance_events, im_events)
    opponent_ind_df = filter_events_by_preferences(opponent_df, distance_events, im_events)
    
    user_ind_lineup, user_final_counts = strategic_dual_meet_assignment(
        user_ind_df, opponent_ind_df,
        max_events_per_swimmer=4,
        swimmers_per_event=pool_config['swimmers'],
        swimmer_relay_counts=user_relay_counts,
        relay_events=relay_events
    )
    
    user_strat_relay_df, _ = create_strategic_relay_teams(
        user_df, opponent_df, relay_events, max_total_events=4
    )
    
    opponent_ind_lineup, _ = round_robin_assignment(
        opponent_ind_df,
        max_events_per_swimmer=4,
        swimmers_per_event=pool_config['swimmers'],
        swimmer_relay_counts=opponent_relay_counts
    )
    
    # Calculate scores
    user_total_pts, opponent_total_pts = calculate_dual_meet_score(
        user_ind_lineup, user_strat_relay_df,
        opponent_ind_lineup, opponent_relay_df,
    )
    
    # Generate output files
    output_files = export_lineup_to_files(
        user_ind_lineup, user_strat_relay_df, team_name, 
        app.config['UPLOAD_FOLDER']
    )
    
    # Determine result
    if user_total_pts > opponent_total_pts:
        result = 'WIN'
        margin = user_total_pts - opponent_total_pts
    elif user_total_pts < opponent_total_pts:
        result = 'LOSE'
        margin = opponent_total_pts - user_total_pts
    else:
        result = 'TIE'
        margin = 0
    
    return {
        'success': True,
        'mode': 'dual',
        'team_name': team_name,
        'opponent_name': opponent_name,
        'user_score': user_total_pts,
        'opponent_score': opponent_total_pts,
        'result': result,
        'margin': margin,
        'output_files': output_files,
        'summary': {
            'user_swimmers': len(user_df),
            'opponent_swimmers': len(opponent_df),
            'projected_result': f"{result} by {margin}" if margin > 0 else "TIE"
        }
    }

@app.route('/api/download/<filename>')
def download_file(filename):
    """Serve generated files for download"""
    try:
        return send_file(
            os.path.join(app.config['UPLOAD_FOLDER'], filename), 
            as_attachment=True
        )
    except FileNotFoundError:
        return jsonify({'error': 'File not found'}), 404

if __name__ == '__main__':
    app.run(debug=True)