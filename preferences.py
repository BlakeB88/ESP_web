# preferences.py

def get_dual_meet_mode():
    """
    Ask user whether they want single-team or dual-team strategic lineup.
    """
    print("\n=== DUAL MEET MODE SELECTION ===")
    print("1. Single Team Lineup (best overall performance)")
    print("2. Strategic Dual Team Lineup (beat a specific opponent)")
    while True:
        choice = input("Choose mode (1-2): ").strip()
        if choice in ('1', '2'):
            return int(choice)
        print("Please enter 1 or 2")


def get_pool_configuration():
    """
    Get pool lane configuration to determine swimmers per event.
    """
    print("\n=== POOL CONFIGURATION ===")
    print("1. 8-lane pool (4 swimmers per event)")
    print("2. 10-lane pool (5 swimmers per event)")
    while True:
        choice = input("Choose pool configuration (1-2): ").strip()
        if choice == '1':
            return 8, 4  # lanes, swimmers_per_event
        elif choice == '2':
            return 10, 5  # lanes, swimmers_per_event
        print("Please enter 1 or 2")


def get_team_info(team_label="team"):
    """
    Get team name only (year and gender will be shared in strategic mode).
    """
    name = input(f"Enter the {team_label} name: ").strip()
    return name


def get_meet_configuration():
    """
    Get shared year and gender for both teams in strategic mode.
    """
    print("\n=== MEET CONFIGURATION ===")
    year_input = input("Enter meet year [default = 2025]: ").strip()
    year = int(year_input) if year_input else 2025
    
    while True:
        gender_input = input("Enter gender for both teams (M/F): ").strip().upper()
        if gender_input in ("M", "F"):
            return year, gender_input
        print("Please enter M or F")


def get_single_team_info():
    """
    Get team info for single team mode.
    """
    name = input("Enter the team name: ").strip()
    year_input = input(f"Enter year for {name} [default = 2025]: ").strip()
    year = int(year_input) if year_input else 2025
    
    while True:
        gender_input = input(f"Enter gender for {name} (M/F): ").strip().upper()
        if gender_input in ("M", "F"):
            return name, year, gender_input
        print("Please enter M or F")


def get_opponent_team_info():
    """
    Get opponent team info for strategic mode (year and gender are shared).
    """
    print("\n=== OPPONENT TEAM INFO ===")
    name = input("Enter opponent team name: ").strip()
    return name


def get_user_event_preferences():
    """
    Distance and IM event selection.
    """
    print("\n=== EVENT SELECTION ===")
    
    # Distance events
    print("\nDistance Options:")
    print("1. 1650 Free only")
    print("2. 1000 Free only") 
    print("3. Both 1650 and 1000 Free")
    print("4. Neither (skip distance events)")
    
    while True:
        d = input("Choose distance events (1-4): ").strip()
        if d in ('1','2','3','4'): 
            break
        print("Enter 1, 2, 3, or 4")
    
    if d == '1': 
        distance = ['1650 free']
    elif d == '2': 
        distance = ['1000 free']
    elif d == '3':        
        distance = ['1650 free','1000 free']
    else:
        distance = []  # Skip distance events
    
    # IM events
    print("\nIM Options:")
    print("1. 200 IM only")
    print("2. 400 IM only")
    print("3. Both 200 and 400 IM")
    print("4. Neither (skip IM events)")
    
    while True:
        i = input("Choose IM events (1-4): ").strip()
        if i in ('1','2','3','4'): 
            break
        print("Enter 1, 2, 3, or 4")
    
    if i == '1': 
        im = ['200 IM']
    elif i == '2': 
        im = ['400 IM']
    elif i == '3':        
        im = ['200 IM','400 IM']
    else:
        im = []  # Skip IM events
    
    return distance, im


def get_user_relay_preferences():
    """
    Relay event selection.
    """
    print("\n=== RELAY SELECTION ===")
    print("1. 200 Medley & 200 Free")
    print("2. 200 Medley & 400 Free")
    print("3. 400 Medley & 200 Free")
    print("4. 400 Medley & 400 Free")
    print("5. All four relays")
    print("6. Medley relays only (200 & 400)")
    print("7. Free relays only (200 & 400)")
    
    while True:
        r = input("Choose relay events (1-7): ").strip()
        if r in ('1','2','3','4','5','6','7'): 
            break
        print("Enter 1-7")
    
    if r == '1': 
        relays = ['200 Medley Relay','200 Free Relay']
    elif r == '2': 
        relays = ['200 Medley Relay','400 Free Relay']
    elif r == '3': 
        relays = ['400 Medley Relay','200 Free Relay']
    elif r == '4':
        relays = ['400 Medley Relay','400 Free Relay']
    elif r == '5':       
        relays = ['200 Medley Relay','400 Medley Relay',
                  '200 Free Relay','400 Free Relay']
    elif r == '6':
        relays = ['200 Medley Relay','400 Medley Relay']
    else:  # r == '7'
        relays = ['200 Free Relay','400 Free Relay']
    
    return relays


def get_scraper_event_codes(distance_events, im_events):
    """
    Map user selections to the scraper's event codes.
    Returns comprehensive list of standard events plus user-selected distance/IM.
    """
    # Standard events that are always included
    codes = [
        '50_free','100_free','200_free','500_free',
        '50_back','100_back','200_back',
        '50_breast','100_breast','200_breast',
        '50_fly','100_fly','200_fly'
    ]
    
    # Add distance events
    for event in distance_events:
        if event == '1650 free': 
            codes.append('1650_free')
        elif event == '1000 free': 
            codes.append('1000_free')
    
    # Add IM events
    for event in im_events:
        if event == '200 IM': 
            codes.append('200_im')
        elif event == '400 IM': 
            codes.append('400_im')
    
    print(f"→ Events to scrape: {codes}")
    return codes


def get_max_events_per_swimmer():
    """
    Get the maximum number of events a swimmer can compete in.
    """
    print("\n=== SWIMMER EVENT LIMITS ===")
    print("Maximum events per swimmer (including relays):")
    print("1. 3 events (conservative)")
    print("2. 4 events (standard)")
    print("3. 5 events (aggressive)")
    
    while True:
        choice = input("Choose event limit (1-3): ").strip()
        if choice == '1':
            return 3
        elif choice == '2':
            return 4
        elif choice == '3':
            return 5
        print("Please enter 1, 2, or 3")


def get_lineup_strategy():
    """
    Get the lineup strategy preference for single team mode.
    """
    print("\n=== LINEUP STRATEGY ===")
    print("1. Balanced (round-robin assignment)")
    print("2. Depth-focused (maximize participation)")
    print("3. Speed-focused (fastest swimmers get priority)")
    
    while True:
        choice = input("Choose strategy (1-3): ").strip()
        if choice in ('1', '2', '3'):
            return int(choice)
        print("Please enter 1, 2, or 3")


def confirm_selections(team_name, year, gender, distance_events, im_events, relay_events, max_events):
    """
    Display and confirm all user selections before proceeding.
    """
    print(f"\n{'='*50}")
    print("LINEUP CONFIGURATION SUMMARY")
    print(f"{'='*50}")
    print(f"Team: {team_name}")
    print(f"Year: {year}")
    print(f"Gender: {gender}")
    print(f"Max events per swimmer: {max_events}")
    print(f"Distance events: {distance_events if distance_events else 'None'}")
    print(f"IM events: {im_events if im_events else 'None'}")
    print(f"Relay events: {relay_events}")
    print(f"{'='*50}")
    
    while True:
        confirm = input("Proceed with these settings? (y/n): ").strip().lower()
        if confirm in ('y', 'yes'):
            return True
        elif confirm in ('n', 'no'):
            return False
        print("Please enter y or n")