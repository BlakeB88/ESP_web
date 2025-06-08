# Enhanced event_sorter.py

import pandas as pd
from Scraper.swimmer_scraper import scrape_and_save
from Scraper.data_processor import lineup_spread
from preferences import (
    get_dual_meet_mode,
    get_single_team_info,
    get_meet_configuration,
    get_opponent_team_info,
    get_user_event_preferences,
    get_user_relay_preferences,
    get_scraper_event_codes,
    get_pool_configuration,
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
)


def get_team_info(team_description):
    """Helper function to get team information"""
    return input(f"Enter {team_description} name: ").strip()


def main():
    print("=== Dual Meet Lineup Builder ===")
    mode = get_dual_meet_mode()
    
    # Get pool configuration for both modes
    total_lanes, swimmers_per_event = get_pool_configuration()
    print(f"→ Pool configuration: {total_lanes} lanes, {swimmers_per_event} swimmers per event")

    if mode == 1:
        # Single-team optimization
        print("\n🏊‍♀️ SINGLE TEAM OPTIMIZATION MODE 🏊‍♂️")
        print("Creating optimal lineup for best overall performance...")
        
        team_name, year, gender = get_single_team_info()
        distance_events, im_events = get_user_event_preferences()
        relay_events = get_user_relay_preferences()

        print(f"\n→ Team: {team_name} ({gender}, {year})")
        print(f"→ Selected distance events: {distance_events}")
        print(f"→ Selected IM events:       {im_events}")
        print(f"→ Selected relay events:    {relay_events}")

        events_to_scrape = get_scraper_event_codes(distance_events, im_events)
        filename = f"{team_name.replace(' ', '_')}_times.xlsx"
        
        try:
            print(f"→ Scraping SwimCloud for {team_name} ({gender}, {year})...")
            scrape_and_save(
                team_name=team_name,
                year=year,
                gender=gender,
                filename=filename,
                selected_events=events_to_scrape,
            )
        except Exception as e:
            print(f"❌ Error during scraping: {e}")
            return

        print(f"→ Processing lineup from '{filename}'...")
        times_df = pd.read_excel(filename)
        
        # Clean and validate data
        times_df = clean_time_data(times_df)
        if not validate_swimmer_data(times_df):
            print("❌ Data validation failed. Please check your data file.")
            return

        print(f"→ Loaded {len(times_df)} swimmers")

        # Create relay teams first
        print(f"\n→ Creating relay teams...")
        relay_lineup_df, swimmer_relay_counts = create_relay_teams(
            times_df, 
            relay_events,
            max_total_events=4
        )

        # Filter events for individual assignments
        print(f"→ Filtering events for individual assignments...")
        individual_times_df = filter_events_by_preferences(times_df, distance_events, im_events)

        # Create individual assignments
        print(f"→ Creating individual event assignments...")
        individual_lineup_df, final_swimmer_counts = round_robin_assignment(
            individual_times_df,
            max_events_per_swimmer=4,
            swimmers_per_event=swimmers_per_event,
            swimmer_relay_counts=swimmer_relay_counts,
        )

        # Display results
        print(f"\n{'='*60}")
        print(f"🏊‍♀️ {team_name.upper()} OPTIMIZED LINEUP 🏊‍♂️")
        print(f"{'='*60}")
        
        print_individual_lineup(individual_lineup_df)
        print_relay_lineup(relay_lineup_df)
        print_detailed_lineup(individual_lineup_df, relay_lineup_df, final_swimmer_counts)

    else:
        # Strategic dual-team
        print("\n🏊‍♀️ STRATEGIC DUAL MEET MODE 🏊‍♂️")
        print("Optimizing lineups to maximize points against opponent...")
        
        # Get shared meet configuration
        year, gender = get_meet_configuration()
        
        # Get team names
        user_team = get_team_info("Your team")
        opponent_team = get_opponent_team_info()
        
        # Get event preferences
        distance_events, im_events = get_user_event_preferences()
        relay_events = get_user_relay_preferences()

        print(f"\n→ Your Team: {user_team} ({gender}, {year})")
        print(f"→ Opponent:  {opponent_team} ({gender}, {year})")
        print(f"→ Events: {distance_events + im_events}")
        print(f"→ Relays: {relay_events}")

        events_to_scrape = get_scraper_event_codes(distance_events, im_events)
        user_filename = f"user_{user_team.replace(' ', '_')}_times.xlsx"
        opp_filename  = f"opp_{opponent_team.replace(' ', '_')}_times.xlsx"

        try:
            print(f"\n→ Scraping data for {user_team}...")
            scrape_and_save(
                team_name=user_team,
                year=year,
                gender=gender,
                filename=user_filename,
                selected_events=events_to_scrape,
            )
            print(f"→ Scraping data for {opponent_team}...")
            scrape_and_save(
                team_name=opponent_team,
                year=year,
                gender=gender,
                filename=opp_filename,
                selected_events=events_to_scrape,
            )
        except Exception as e:
            print(f"❌ Error during scraping: {e}")
            return

        print("\n→ Processing strategic dual-meet lineups…")
        user_df = pd.read_excel(user_filename)
        opponent_df = pd.read_excel(opp_filename)
        
        # Clean and validate data
        user_df = clean_time_data(user_df)
        opponent_df = clean_time_data(opponent_df)
        
        if not validate_swimmer_data(user_df) or not validate_swimmer_data(opponent_df):
            print("❌ Data validation failed. Please check your data files.")
            return

        print(f"→ Loaded {len(user_df)} swimmers for your team")
        print(f"→ Loaded {len(opponent_df)} swimmers for opponent")

        # Create relay teams for both teams
        print("\n→ Creating relay lineups...")
        user_relay_df, user_relay_counts = create_relay_teams(
            user_df, 
            relay_events,
            max_total_events=4
        )
        opponent_relay_df, opponent_relay_counts = create_relay_teams(
            opponent_df, 
            relay_events,
            max_total_events=4
        )

        # Filter for individual events
        print("→ Processing individual events...")
        user_ind_df = filter_events_by_preferences(user_df, distance_events, im_events)
        opponent_ind_df = filter_events_by_preferences(opponent_df, distance_events, im_events)

        # Strategic individual assignments
        print("→ Optimizing individual event assignments...")
        user_ind_lineup, user_final_counts = strategic_dual_meet_assignment(
            user_ind_df, 
            opponent_ind_df,
            max_events_per_swimmer=4,
            swimmers_per_event=swimmers_per_event,
            swimmer_relay_counts=user_relay_counts,
            relay_events=relay_events
        )

        # Strategic relay assignments
        print("→ Optimizing relay assignments...")
        user_strat_relay_df, _ = create_strategic_relay_teams(
            user_df,
            opponent_df,
            relay_events,
            max_total_events=4
        )

        # Create opponent lineup for comparison (using round robin)
        print("→ Creating opponent reference lineup...")
        opponent_ind_lineup, opponent_final_counts = round_robin_assignment(
            opponent_ind_df,
            max_events_per_swimmer=4,
            swimmers_per_event=swimmers_per_event,
            swimmer_relay_counts=opponent_relay_counts
        )

        # Calculate and display the projected dual meet score
        print("\n" + "="*60)
        print("🏊‍♀️ STRATEGIC LINEUP ANALYSIS 🏊‍♂️")
        print("="*60)
        
        user_total_pts, opponent_total_pts = calculate_dual_meet_score(
            user_ind_lineup,
            user_strat_relay_df,
            opponent_ind_lineup,
            opponent_relay_df,
        )

        # Display lineups
        print(f"\n{'='*60}")
        print(f"YOUR OPTIMIZED LINEUP ({user_team.upper()}):")
        print(f"{'='*60}")
        print_individual_lineup(user_ind_lineup)
        print_relay_lineup(user_strat_relay_df)

        print(f"\n{'='*60}")
        print(f"OPPONENT LINEUP ({opponent_team.upper()}) - for reference:")
        print(f"{'='*60}")
        print_individual_lineup(opponent_ind_lineup)
        print_relay_lineup(opponent_relay_df)

        # Final summary
        print(f"\n{'='*60}")
        print(f"📊 MEET PROJECTION SUMMARY")
        print(f"{'='*60}")
        
        if user_total_pts > opponent_total_pts:
            result = "WIN"
            margin = user_total_pts - opponent_total_pts
            emoji = "🎉"
            message = f"Congratulations! Your strategic lineup should win by {margin} points!"
        elif user_total_pts < opponent_total_pts:
            result = "LOSE"
            margin = opponent_total_pts - user_total_pts
            emoji = "😤"
            message = f"Time to train harder! You're projected to lose by {margin} points."
        else:
            result = "TIE"
            margin = 0
            emoji = "🤝"
            message = "It's going to be a nail-biter - a projected tie!"
        
        print(f"This lineup is projected to {result}")
        print(f"Final Score: {user_team} {user_total_pts} - {opponent_team} {opponent_total_pts}")
        print(f"{emoji} {message}")
        
        if user_total_pts < opponent_total_pts:
            print("💡 Consider adjusting event assignments or developing specific events.")
        
        print(f"{'='*60}")

        # Display detailed lineup analysis
        print_detailed_lineup(user_ind_lineup, user_strat_relay_df, user_final_counts)


if __name__ == "__main__":
    main()