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
        
        # Process events
        distance_events = events.get('distanceEvents', [])
        im_events = events.get('imEvents', [])
        relay_events = events.get('relayEvents', [])
        
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
        return jsonify({'error': f'Error processing lineup: {str(e)}'}), 500

def process_single_team_lineup(team_name, year, gender, distance_events, 
                              im_events, relay_events, pool_config, filename):
    """Process single team optimization"""
    
    # Get events to scrape
    events_to_scrape = get_scraper_event_codes(distance_events, im_events)
    
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
    
    # Scrape both teams
    scrape_and_save(team_name, year, gender, user_filename, events_to_scrape)
    scrape_and_save(opponent_name, year, gender, opp_filename, events_to_scrape)
    
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