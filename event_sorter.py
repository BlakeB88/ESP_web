# Enhanced event_sorter.py

import pandas as pd
from Scraper.swimmer_scraper import scrape_and_save
from Scraper.data_processor import lineup_spread
from preferences import (
    get_dual_meet_mode,
    get_team_info,
    get_opponent_team_info,
    get_user_event_preferences,
    get_user_relay_preferences,
    get_scraper_event_codes,
)
from utils import filter_events_by_preferences
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


def main():
    print("=== Dual Meet Lineup Builder ===")
    mode = get_dual_meet_mode()

    if mode == 1:
        # Single-team optimization
        team_name, year, gender = get_team_info()
        distance_events, im_events = get_user_event_preferences()
        relay_events = get_user_relay_preferences()

        print(f"\n→ Selected distance events: {distance_events}")
        print(f"→ Selected IM events:       {im_events}")
        print(f"→ Selected relay events:    {relay_events}")

        events_to_scrape = get_scraper_event_codes(distance_events, im_events)
        filename = "swimmer_times.xlsx"
        

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
            print(f"Error during scraping: {e}")
            return

        print(f"→ Processing lineup from '{filename}'...")
        times_df = pd.read_excel(filename)

        print(f"[DEBUG] Loaded Excel file shape: {times_df.shape}")
        print(f"[DEBUG] Columns in loaded data: {times_df.columns.tolist()}")
        print(f"[DEBUG] Sample of loaded data:")
        print(times_df.head())

        print(f"→ Loaded {len(times_df)} swimmers")

        # Before relay team creation
        print(f"[DEBUG] About to create relay teams with {len(times_df)} swimmers")
        print(f"[DEBUG] Relay events requested: {relay_events}")

        # Create relay teams first
        relay_lineup_df, swimmer_relay_counts = create_relay_teams(times_df, relay_events)
        
        # After relay team creation - now we can safely reference the variables
        print(f"[DEBUG] Relay lineup shape: {relay_lineup_df.shape if not relay_lineup_df.empty else 'EMPTY'}")
        print(f"[DEBUG] Swimmer relay counts: {dict(swimmer_relay_counts) if swimmer_relay_counts else 'EMPTY'}")

        # Check what events you're filtering for
        print(f"[DEBUG] Distance events for filtering: {distance_events}")
        print(f"[DEBUG] IM events for filtering: {im_events}")

        # Filter events for individual assignments
        individual_times_df = filter_events_by_preferences(times_df, distance_events, im_events)
        
        # After filtering
        print(f"[DEBUG] After filtering - shape: {individual_times_df.shape}")
        print(f"[DEBUG] After filtering - columns: {individual_times_df.columns.tolist()}")
        print(f"[DEBUG] After filtering - sample:")
        print(individual_times_df.head())

        # Before individual assignment
        print(f"[DEBUG] About to assign individuals with {len(individual_times_df)} swimmers")

        # Create individual assignments
        individual_lineup_df, _ = round_robin_assignment(
            individual_times_df,
            swimmer_relay_counts=swimmer_relay_counts,
        )

        # After individual assignment
        print(f"[DEBUG] Individual lineup shape: {individual_lineup_df.shape if not individual_lineup_df.empty else 'EMPTY'}")
        if not individual_lineup_df.empty:
            print(f"[DEBUG] Individual lineup columns: {individual_lineup_df.columns.tolist()}")
            print(f"[DEBUG] Individual lineup sample:")
            print(individual_lineup_df.head())

        print_individual_lineup(individual_lineup_df)
        print_relay_lineup(relay_lineup_df)
        print_detailed_lineup(individual_lineup_df, relay_lineup_df)

    else:
        # Strategic dual-team
        print("\n🏊‍♀️ STRATEGIC DUAL MEET MODE 🏊‍♂️")
        print("Optimizing lineups to maximize points against opponent...")
        
        user_team, user_year, user_gender = get_team_info("Your team")
        opponent_team, opponent_year, opponent_gender = get_opponent_team_info()
        distance_events, im_events = get_user_event_preferences()
        relay_events = get_user_relay_preferences()

        print(f"\n→ Your Team: {user_team} ({user_gender}, {user_year})")
        print(f"→ Opponent:  {opponent_team} ({opponent_gender}, {opponent_year})")
        print(f"→ Events: {distance_events + im_events}")
        print(f"→ Relays: {relay_events}")

        events_to_scrape = get_scraper_event_codes(distance_events, im_events)
        user_filename = f"user_{user_team.replace(' ', '_')}_times.xlsx"
        opp_filename  = f"opp_{opponent_team.replace(' ', '_')}_times.xlsx"

        try:
            print(f"\n→ Scraping data for {user_team}...")
            scrape_and_save(
                team_name=user_team,
                year=user_year,
                gender=user_gender,
                filename=user_filename,
                selected_events=events_to_scrape,
            )
            print(f"→ Scraping data for {opponent_team}...")
            scrape_and_save(
                team_name=opponent_team,
                year=opponent_year,
                gender=opponent_gender,
                filename=opp_filename,
                selected_events=events_to_scrape,
            )
        except Exception as e:
            print(f"❌ Error during scraping: {e}")
            return

        print("\n→ Processing strategic dual-meet lineups…")
        user_df     = pd.read_excel(user_filename)
        opponent_df = pd.read_excel(opp_filename)

        print(f"→ Loaded {len(user_df)} swimmers for your team")
        print(f"→ Loaded {len(opponent_df)} swimmers for opponent")

        # Create relay teams for both teams
        print("\n→ Creating relay lineups...")
        user_relay_df, user_relay_counts = create_relay_teams(user_df, relay_events)
        opponent_relay_df, opponent_relay_counts = create_relay_teams(opponent_df, relay_events)

        # Filter for individual events
        print("→ Processing individual events...")
        user_ind_df     = filter_events_by_preferences(user_df, distance_events, im_events)
        opponent_ind_df = filter_events_by_preferences(opponent_df, distance_events, im_events)

        # Strategic individual assignments
        print("→ Optimizing individual event assignments...")
        user_ind_lineup, _ = strategic_dual_meet_assignment(
            user_ind_df, 
            opponent_ind_df,
            swimmer_relay_counts=user_relay_counts
        )

        # Strategic relay assignments (for now, same as regular relay creation)
        print("→ Optimizing relay assignments...")
        user_strat_relay_df = user_relay_df  # Can be enhanced later for true strategic relay optimization

        # Calculate and display the projected dual meet score
        print("\n" + "="*60)
        print("🏊‍♀️ STRATEGIC LINEUP ANALYSIS 🏊‍♂️")
        print("="*60)
        
        user_total_pts, opponent_total_pts = calculate_dual_meet_score(
            user_ind_lineup,
            user_strat_relay_df,
            opponent_ind_df,  # Use opponent individual data for scoring
            opponent_relay_df,
        )

        # Display lineups
        print(f"\n{'='*60}")
        print(f"YOUR OPTIMIZED LINEUP:")
        print(f"{'='*60}")
        print_individual_lineup(user_ind_lineup)
        print_relay_lineup(user_strat_relay_df)

        print(f"\n{'='*60}")
        print(f"OPPONENT LINEUP (for reference):")
        print(f"{'='*60}")
        
        # Create opponent lineup for display (using round robin)
        opponent_ind_lineup, _ = round_robin_assignment(
            opponent_ind_df,
            swimmer_relay_counts=opponent_relay_counts
        )
        
        print_individual_lineup(opponent_ind_lineup)
        print_relay_lineup(opponent_relay_df)

        # Final summary
        print(f"\n{'='*60}")
        print(f"📊 MEET PROJECTION SUMMARY")
        print(f"{'='*60}")
        print(f"This lineup is projected to {'WIN' if user_total_pts > opponent_total_pts else 'LOSE' if user_total_pts < opponent_total_pts else 'TIE'}")
        print(f"Final Score: {user_team} {user_total_pts} - {opponent_team} {opponent_total_pts}")
        
        if user_total_pts > opponent_total_pts:
            print(f"🎉 Congratulations! Your strategic lineup should win by {user_total_pts - opponent_total_pts} points!")
        elif user_total_pts < opponent_total_pts:
            print(f"😤 Time to train harder! You're projected to lose by {opponent_total_pts - user_total_pts} points.")
            print("💡 Consider adjusting event assignments or developing specific events.")
        else:
            print("🤝 It's going to be a nail-biter - a projected tie!")
        
        print(f"{'='*60}")


if __name__ == "__main__":
    main()