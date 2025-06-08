#!/usr/bin/env python3
"""
Test script to debug 1650 free event scraping issues.
Run this to test just the 1650 event URL building and scraping.
"""

import sys
import os
sys.path.append('.')  # Add current directory to path

from url_builder import build_swimcloud_times_url, test_times_url, EVENT_MAPPINGS
from data_scraper_debug import scrape_swimmer_times

def test_1650_debugging():
    """Test 1650 event specifically with enhanced debugging"""

    print("=== 1650 FREE EVENT DEBUG TEST ===\n")

    # Test parameters - you can modify these
    team_id = "2697"  # Example team ID - replace with your actual team ID
    year = 2024
    gender = "M"
    event_code = EVENT_MAPPINGS["1650_free"]  # Should be "1|1650|1"

    print(f"Testing with:")
    print(f"  Team ID: {team_id}")
    print(f"  Year: {year}")
    print(f"  Gender: {gender}")
    print(f"  Event Code: {event_code}")
    print()

    # Step 1: Build the URL
    print("Step 1: Building 1650 URL...")
    url_1650 = build_swimcloud_times_url(team_id, year, gender, event=event_code)
    print(f"Built URL: {url_1650}")
    print()

    # Step 2: Test if URL is accessible
    print("Step 2: Testing URL accessibility...")
    url_works = test_times_url(url_1650)
    print(f"URL test result: {'PASS' if url_works else 'FAIL'}")
    print()

    if not url_works:
        print("❌ URL test failed. Possible issues:")
        print("  - Team doesn't have 1650 times for this year/gender")
        print("  - SwimCloud changed their URL structure")
        print("  - Network/access issues")
        print("  - Team ID is incorrect")
        print()
        print("Try these debugging steps:")
        print("  1. Manually visit the URL in your browser")
        print("  2. Check if the team has 1650 times on SwimCloud")
        print("  3. Try a different year or gender")
        print("  4. Verify the team ID is correct")
        return

    # Step 3: Try to scrape the data
    print("Step 3: Attempting to scrape 1650 data...")
    print("(This will create debug_swimcloud_1650_page.html)")
    print()

    try:
        times_data = scrape_swimmer_times(url_1650)

        if times_data:
            print(f"✅ SUCCESS! Found {len(times_data)} 1650 records:")
            for i, (swimmer, event, time) in enumerate(times_data[:5], 1):
                print(f"  {i}. {swimmer} - {event} - {time}")
            if len(times_data) > 5:
                print(f"  ... and {len(times_data) - 5} more")
        else:
            print("❌ No data returned from scraper")

    except Exception as e:
        print(f"❌ Scraping failed with error: {e}")
        print()
        print("Check the debug file 'debug_swimcloud_1650_page.html' to see what SwimCloud returned")

    print()
    print("=== DEBUG FILES CREATED ===")
    print("  - debug_swimcloud_1650_page.html (page content)")
    print("  - Check console output above for detailed debugging info")

def test_all_events_for_comparison():
    """Test a few other events to compare with 1650"""

    print("\n=== COMPARISON TEST: OTHER EVENTS ===\n")

    team_id = "2697"  # Replace with your team ID
    year = 2024
    gender = "M"

    # Test a few other events for comparison
    test_events = ["100_free", "200_free", "500_free"]

    for event_name in test_events:
        print(f"Testing {event_name}...")
        event_code = EVENT_MAPPINGS[event_name]
        url = build_swimcloud_times_url(team_id, year, gender, event=event_code)
        works = test_times_url(url)
        print(f"  {event_name}: {'✅ WORKS' if works else '❌ FAILS'}")

    print()

if __name__ == "__main__":
    print("1650 Free Event Debug Tool")
    print("=" * 50)

    # Get team ID from user
    team_id = input("Enter your team ID (or press Enter for default 2697): ").strip()
    if not team_id:
        team_id = "2697"

    # Update the test functions to use the provided team ID
    globals()['team_id'] = team_id

    print(f"\nUsing team ID: {team_id}")
    print("Starting debug test...\n")

    # Run the main test
    test_1650_debugging()

    # Ask if user wants to test other events for comparison
    test_others = input("\nTest other events for comparison? (y/n): ").strip().lower()
    if test_others == 'y':
        test_all_events_for_comparison()

    print("\n=== DEBUG TEST COMPLETE ===")
    print("Check the debug output above and the HTML file for clues about the 1650 issue.")
