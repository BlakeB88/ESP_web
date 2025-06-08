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


def get_team_info(team_label="team"):
    """
    Get team name, year, and gender.
    """
    name = input(f"Enter the {team_label} name: ").strip()
    year_input = input(f"Enter year for {name} [default = 2025]: ").strip()
    year = int(year_input) if year_input else 2025
    gender_input = input(f"Enter gender for {name} (M/F): ").strip().upper()
    gender = gender_input if gender_input in ("M", "F") else "M"
    return name, year, gender


def get_opponent_team_info():
    """
    Get opponent team info for strategic mode.
    """
    print("\n=== OPPONENT TEAM INFO ===")
    name = input("Enter opponent team name: ").strip()
    year_input = input(f"Enter opponent year [default = 2025]: ").strip()
    year = int(year_input) if year_input else 2025
    gender_input = input("Enter opponent gender (M/F): ").strip().upper()
    gender = gender_input if gender_input in ("M", "F") else "M"
    return name, year, gender


def get_user_event_preferences():
    """
    Distance and IM event selection.
    """
    print("\n=== EVENT SELECTION ===")
    # Distance
    print("\nDistance Options:\n1. 1650 Free only\n2. 1000 Free only\n3. Both")
    while True:
        d = input("Choose distance (1-3): ").strip()
        if d in ('1','2','3'): break
        print("Enter 1, 2, or 3")
    if d=='1': distance = ['1650 free']
    elif d=='2': distance = ['1000 free']
    else:        distance = ['1650 free','1000 free']
    # IM
    print("\nIM Options:\n1. 200 IM\n2. 400 IM\n3. Both")
    while True:
        i = input("Choose IM (1-3): ").strip()
        if i in ('1','2','3'): break
        print("Enter 1, 2, or 3")
    if i=='1': im = ['200 IM']
    elif i=='2': im = ['400 IM']
    else:        im = ['200 IM','400 IM']
    return distance, im


def get_user_relay_preferences():
    """
    Relay event selection.
    """
    print("\n=== RELAY SELECTION ===")
    print("1. 200 Medley & 200 Free\n2. 200 Medley & 400 Free\n"
          "3. 400 Medley & 200 Free\n4. All four relays")
    while True:
        r = input("Choose relay (1-4): ").strip()
        if r in ('1','2','3','4'): break
        print("Enter 1–4")
    if r=='1': relays = ['200 Medley Relay','200 Free Relay']
    elif r=='2': relays = ['200 Medley Relay','400 Free Relay']
    elif r=='3': relays = ['400 Medley Relay','200 Free Relay']
    else:       relays = ['200 Medley Relay','400 Medley Relay',
                           '200 Free Relay','400 Free Relay']
    return relays


def get_scraper_event_codes(distance_events, im_events):
    """
    Map user selections to the scraper’s event codes.
    """
    codes = [
        '50_free','100_free','200_free','500_free',
        '50_back','100_back','200_back',
        '50_breast','100_breast','200_breast',
        '50_fly','100_fly','200_fly'
    ]
    for e in distance_events:
        if e=='1650 free': codes.append('1650_free')
        if e=='1000 free': codes.append('1000_free')
    for e in im_events:
        if e=='200 IM': codes.append('200_im')
        if e=='400 IM': codes.append('400_im')
    print(f"→ Events to scrape: {codes}")
    return codes
