import time
import pandas as pd
import signal
import concurrent.futures
from contextlib import contextmanager
from .team_mappings import load_team_mappings, find_team_id
from .url_builder import build_swimcloud_times_url, test_times_url, EVENT_MAPPINGS
from .data_processor import create_times_dataframe, save_to_excel

# Import the optimized scraper functions
try:
    from .data_scraper import fast_scrape_swimmer_times, cleanup_all_drivers
except ImportError:
    # Fallback to original if optimized version not available
    from .data_scraper import scrape_swimmer_times as fast_scrape_swimmer_times
    def cleanup_all_drivers():
        pass

class TimeoutException(Exception):
    pass

def timeout_handler(signum, frame):
    raise TimeoutException("Operation timed out")

@contextmanager
def timeout_context(seconds):
    """Context manager for operation timeout"""
    old_handler = signal.signal(signal.SIGALRM, timeout_handler)
    signal.alarm(seconds)
    
    try:
        yield
    finally:
        signal.signal(signal.SIGALRM, old_handler)
        signal.alarm(0)

def scrape_event_with_timeout(event_info, timeout_seconds=8):
    """Scrape a single event with timeout protection"""
    event_name, event_code, times_url = event_info
    
    try:
        print(f"→ Processing event: {event_name}")
        
        # Quick URL test (optional, can be skipped for speed)
        # if not test_times_url(times_url):
        #     print(f"[DEBUG] Event {event_name} URL failed, skipping...")
        #     return []
        
        # Use optimized scraper with timeout
        with timeout_context(timeout_seconds):
            times_data = fast_scrape_swimmer_times(times_url, timeout=6)
            
        if times_data:
            print(f"   ✓ Successfully scraped {len(times_data)} entries for {event_name}")
            return times_data
        else:
            print(f"   ⚠️  No times data returned for {event_name}")
            return []
            
    except TimeoutException:
        print(f"   ⚠️  Timeout scraping {event_name}")
        return []
    except Exception as e:
        print(f"[DEBUG] Failed to scrape {event_name}: {e}")
        return []

def parallel_scrape_events(event_infos, max_workers=3, timeout_per_event=8):
    """Scrape multiple events in parallel"""
    all_times_data = []
    
    # Use ThreadPoolExecutor for parallel processing
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Submit all tasks
        future_to_event = {
            executor.submit(scrape_event_with_timeout, event_info, timeout_per_event): event_info[0]
            for event_info in event_infos
        }
        
        # Collect results as they complete
        for future in concurrent.futures.as_completed(future_to_event, timeout=60):
            event_name = future_to_event[future]
            try:
                result = future.result(timeout=10)
                all_times_data.extend(result)
            except Exception as e:
                print(f"[ERROR] Event {event_name} failed: {e}")
                continue
    
    return all_times_data

def scrape_and_save_optimized(team_name, year=2024, gender="M", filename="swimmer_times.xlsx", 
                             mappings_file="Scraper/maps/team_mappings/all_college_teams.json", 
                             selected_events=None, max_total_time=25):
    """
    Optimized version of the main scraping function with timeout protection.
    
    Args:
        team_name: Name of the team to scrape
        year: Season year
        gender: "M" or "F"
        filename: Output Excel filename
        mappings_file: Path to team mappings JSON file
        selected_events: List of event codes to scrape (e.g., ['50_free', '100_free'])
                        If None, scrapes all events
        max_total_time: Maximum time allowed for entire operation (seconds)
    """
    start_time = time.time()
    
    try:
        with timeout_context(max_total_time):
            # Load team mappings
            print(f"→ Loading team mappings from {mappings_file}...")
            mappings = load_team_mappings(mappings_file)
            
            if not mappings:
                raise Exception(f"No team mappings loaded from {mappings_file}")
            
            # Find team ID
            print(f"→ Finding SwimCloud ID for '{team_name}'...")
            team_id = find_team_id(team_name, mappings)
            
            if not team_id:
                available_teams = list(mappings.values())[:10]
                raise Exception(f"Team '{team_name}' not found in mappings. Available teams include: {available_teams}")
            
            # Determine which events to scrape (with limits for performance)
            if selected_events is None:
                # Limit to most common events for speed
                priority_events = ['50_free', '100_free', '200_free', '100_back', '100_breast', '100_fly', '200_im']
                events_to_scrape = [(name, code) for name, code in EVENT_MAPPINGS.items() 
                                   if name in priority_events]
                print(f"→ Scraping {len(events_to_scrape)} priority events for speed...")
            else:
                # Scrape only selected events (limit to first 10 for timeout safety)
                events_to_scrape = [(event_name, event_code) for event_name, event_code in EVENT_MAPPINGS.items() 
                                   if event_name in selected_events][:10]
                print(f"→ Scraping {len(events_to_scrape)} selected events: {[name for name, _ in events_to_scrape]}")
                
                # Warn about any requested events that aren't in EVENT_MAPPINGS
                missing_events = [event for event in selected_events if event not in EVENT_MAPPINGS]
                if missing_events:
                    print(f"⚠️  Warning: These requested events are not available: {missing_events}")
            
            # Build URLs for all events
            print(f"→ Building URLs for team ID: {team_id}...")
            event_infos = []
            for event_name, event_code in events_to_scrape:
                times_url = build_swimcloud_times_url(team_id, year, gender, event=event_code)
                event_infos.append((event_name, event_code, times_url))
            
            # Calculate time per event
            remaining_time = max_total_time - (time.time() - start_time) - 5  # 5 second buffer
            time_per_event = max(6, min(10, remaining_time // len(event_infos))) if event_infos else 8
            
            print(f"→ Parallel scraping {len(event_infos)} events with {time_per_event}s per event...")
            
            # Scrape all events in parallel
            all_times_data = parallel_scrape_events(
                event_infos, 
                max_workers=min(3, len(event_infos)), 
                timeout_per_event=time_per_event
            )
            
            if not all_times_data:
                raise Exception("No data scraped for any events")
            
            print(f"→ Total raw entries collected: {len(all_times_data)}")
            
            # Process all data at once using the existing create_times_dataframe function
            final_df = create_times_dataframe(all_times_data)
            
            print(f"→ Final processed data: {final_df.shape[0]} swimmers")
            if len(final_df.columns) > 1:
                events_in_final = [col for col in final_df.columns if col != 'Swimmer']
                print(f"→ Events in final dataset: {events_in_final}")
            
            # Save to Excel
            result = save_to_excel(final_df, filename)
            
            elapsed_time = time.time() - start_time
            print(f"✓ Successfully scraped and saved {len(events_to_scrape)} events to {filename} in {elapsed_time:.1f}s")
            
            return result
            
    except TimeoutException:
        elapsed_time = time.time() - start_time
        print(f"✗ Operation timed out after {elapsed_time:.1f}s")
        raise Exception(f"Scraping timed out after {max_total_time} seconds")
        
    except Exception as e:
        elapsed_time = time.time() - start_time
        print(f"✗ Error after {elapsed_time:.1f}s: {e}")
        print("\n💡 Troubleshooting suggestions:")
        print("1. Try reducing the number of events to scrape")
        print("2. Check if SwimCloud is accessible")
        print("3. Consider increasing the timeout limit")
        print("4. Verify team name spelling")
        raise
        
    finally:
        # Always cleanup browser resources
        cleanup_all_drivers()

# Backward compatibility - keep the original function name
def scrape_and_save(team_name, year=2024, gender="M", filename="swimmer_times.xlsx", 
                   mappings_file="Scraper/maps/team_mappings/all_college_teams.json", 
                   selected_events=None):
    """
    Original function signature - now uses optimized implementation
    """
    return scrape_and_save_optimized(
        team_name=team_name,
        year=year,
        gender=gender,
        filename=filename,
        mappings_file=mappings_file,
        selected_events=selected_events,
        max_total_time=25  # Safe default for most deployments
    )

# Quick scrape function for essential events only
def scrape_essential_events_only(team_name, year=2024, gender="M", filename="swimmer_times.xlsx",
                                mappings_file="Scraper/maps/team_mappings/all_college_teams.json"):
    """
    Quick scrape of only the most essential events for fastest processing
    """
    essential_events = ['50_free', '100_free', '200_free', '100_back', '100_breast', '100_fly']
    
    return scrape_and_save_optimized(
        team_name=team_name,
        year=year,
        gender=gender,
        filename=filename,
        mappings_file=mappings_file,
        selected_events=essential_events,
        max_total_time=20
    )