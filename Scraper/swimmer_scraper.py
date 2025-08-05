import time
import pandas as pd
from .team_mappings import load_team_mappings, find_team_id
from .url_builder import build_swimcloud_times_url, test_times_url, EVENT_MAPPINGS
from .data_scraper import scrape_swimmer_times, scrape_multiple_events_parallel
from .data_processor import create_times_dataframe, save_to_excel
import signal
import multiprocessing

class TimeoutException(Exception):
    pass

def timeout_handler(signum, frame):
    raise TimeoutException("Operation timed out")

def scrape_and_save(team_name, year=2024, gender="M", filename="swimmer_times.xlsx", 
    mappings_file="Scraper/maps/team_mappings/all_college_teams.json", 
    selected_events=None, timeout_seconds=45):
    """
    Main function to scrape swimmer time data with timeout protection.
    Heavily optimized to prevent worker timeouts.
    
    Args:
    team_name: Name of the team to scrape
    year: Season year
    gender: "M" or "F"
    filename: Output Excel filename
    mappings_file: Path to team mappings JSON file
    selected_events: List of event codes to scrape
    timeout_seconds: Maximum time allowed for scraping operation
    """
    
    # Set up timeout protection
    if hasattr(signal, 'SIGALRM'):  # Unix systems only
        signal.signal(signal.SIGALRM, timeout_handler)
        signal.alarm(timeout_seconds)
    
    try:
        start_time = time.time()
        
        # Load team mappings quickly
        print(f"→ Loading team mappings from {mappings_file}...")
        mappings = load_team_mappings(mappings_file)
        
        if not mappings:
            raise Exception(f"No team mappings loaded from {mappings_file}")
        
        # Find team ID
        print(f"→ Finding SwimCloud ID for '{team_name}'...")
        team_id = find_team_id(team_name, mappings)
        
        if not team_id:
            raise Exception(f"Team '{team_name}' not found in mappings")
        
        # Determine events to scrape (limit to prevent timeout)
        if selected_events is None:
            # Limit to most common events when scraping all
            priority_events = ['50_free', '100_free', '200_free', '100_back', '100_breast', '100_fly']
            events_to_scrape = [(event_name, EVENT_MAPPINGS[event_name]) 
                               for event_name in priority_events if event_name in EVENT_MAPPINGS]
            print(f"→ Scraping {len(events_to_scrape)} priority events (timeout optimization)")
        else:
            # Use only selected events, but limit to 10 max
            events_to_scrape = [(event_name, EVENT_MAPPINGS[event_name]) 
                               for event_name in selected_events[:10] if event_name in EVENT_MAPPINGS]
            print(f"→ Scraping {len(events_to_scrape)} selected events: {[name for name, _ in events_to_scrape]}")
        
        if not events_to_scrape:
            raise Exception("No valid events to scrape")
        
        # Check elapsed time
        elapsed = time.time() - start_time
        remaining_time = timeout_seconds - elapsed - 5  # Keep 5 second buffer
        
        if remaining_time <= 0:
            raise TimeoutException("Insufficient time remaining for scraping")
        
        print(f"→ Scraping swimmer times for team ID: {team_id} (max {remaining_time:.1f}s)...")
        
        # Use optimized scraping approach
        all_times_data = scrape_events_with_timeout(
            team_id, year, gender, events_to_scrape, 
            max_time=remaining_time
        )
        
        if not all_times_data:
            raise Exception("No data scraped for any events")
        
        print(f"→ Total entries collected: {len(all_times_data)}")
        
        # Quick data processing
        final_df = create_times_dataframe_fast(all_times_data)
        
        print(f"→ Final processed data: {final_df.shape[0]} swimmers")
        
        # Save to Excel
        result = save_to_excel(final_df, filename)
        
        total_time = time.time() - start_time
        print(f"✓ Successfully completed in {total_time:.1f}s - saved to {filename}")
        return result
        
    except TimeoutException:
        print("✗ Operation timed out - returning partial results if any")
        # Try to return whatever data we have
        return {"status": "timeout", "message": "Operation timed out"}
        
    except Exception as e:
        print(f"✗ Error: {e}")
        raise
        
    finally:
        # Clear the alarm
        if hasattr(signal, 'SIGALRM'):
            signal.alarm(0)

def scrape_events_with_timeout(team_id, year, gender, events_to_scrape, max_time=30):
    """
    Scrape events with strict time limits and early termination.
    """
    start_time = time.time()
    all_times_data = []
    
    # Calculate time per event
    time_per_event = min(max_time / len(events_to_scrape), 8)  # Max 8 seconds per event
    
    for i, (event_name, event_code) in enumerate(events_to_scrape):
        event_start = time.time()
        elapsed_total = event_start - start_time
        
        # Check if we're running out of time
        if elapsed_total >= max_time - 2:  # Keep 2 second buffer
            print(f"[DEBUG] Time limit reached, stopping at event {i+1}/{len(events_to_scrape)}")
            break
        
        print(f"→ Processing event {i+1}/{len(events_to_scrape)}: {event_name}")
        
        try:
            # Build URL
            times_url = build_swimcloud_times_url(team_id, year, gender, event=event_code)
            
            # Quick URL test with very short timeout
            if not test_times_url(times_url):
                print(f"[DEBUG] Event {event_name} URL failed, skipping...")
                continue
            
            # Scrape with timeout protection
            times_data = scrape_swimmer_times_with_limit(times_url, max_seconds=time_per_event)
            
            if times_data:
                all_times_data.extend(times_data)
                print(f"   ✓ Collected {len(times_data)} entries for {event_name}")
            else:
                print(f"   ⚠️  No data for {event_name}")
                
        except Exception as e:
            print(f"[DEBUG] Failed to scrape {event_name}: {e}")
            continue
        
        # Brief pause only if we have time
        event_time = time.time() - event_start
        if event_time < time_per_event - 1 and elapsed_total < max_time - 3:
            time.sleep(0.5)
    
    return all_times_data

def scrape_swimmer_times_with_limit(url, max_seconds=5):
    """
    Scrape swimmer times with strict time limit.
    """
    start_time = time.time()
    
    try:
        # Use the optimized scraper
        result = scrape_swimmer_times(url)
        
        elapsed = time.time() - start_time
        if elapsed > max_seconds:
            print(f"[DEBUG] Scraping took {elapsed:.1f}s (limit: {max_seconds}s)")
        
        return result
        
    except Exception as e:
        print(f"[DEBUG] Scraping error: {e}")
        return []

def create_times_dataframe_fast(all_times_data):
    """
    Fast DataFrame creation with minimal processing.
    """
    if not all_times_data:
        return pd.DataFrame()
    
    # Convert to DataFrame quickly
    df = pd.DataFrame(all_times_data, columns=['Swimmer', 'Event', 'Time'])
    
    # Basic deduplication - keep first occurrence
    df = df.drop_duplicates(subset=['Swimmer', 'Event'], keep='first')
    
    # Simple pivot without complex processing
    try:
        pivot_df = df.pivot(index='Swimmer', columns='Event', values='Time')
        pivot_df = pivot_df.reset_index()
        return pivot_df
    except Exception as e:
        print(f"[DEBUG] Pivot failed, returning simple format: {e}")
        # Return grouped format as fallback
        return df.groupby('Swimmer').first().reset_index()

# Alternative: Process in separate process to avoid worker timeout
def scrape_and_save_multiprocess(team_name, year=2024, gender="M", filename="swimmer_times.xlsx", 
    mappings_file="Scraper/maps/team_mappings/all_college_teams.json", 
    selected_events=None, timeout_seconds=45):
    """
    Run scraping in separate process to avoid worker timeout.
    """
    
    def target_function(queue, team_name, year, gender, filename, mappings_file, selected_events):
        try:
            result = scrape_and_save(team_name, year, gender, filename, mappings_file, selected_events, timeout_seconds=40)
            queue.put(('success', result))
        except Exception as e:
            queue.put(('error', str(e)))
    
    # Create process and queue
    queue = multiprocessing.Queue()
    process = multiprocessing.Process(
        target=target_function, 
        args=(queue, team_name, year, gender, filename, mappings_file, selected_events)
    )
    
    # Start process
    process.start()
    
    # Wait for completion with timeout
    process.join(timeout=timeout_seconds)
    
    if process.is_alive():
        # Force terminate if still running
        process.terminate()
        process.join()
        return {"status": "timeout", "message": "Scraping process timed out"}
    
    # Get result from queue
    try:
        status, result = queue.get_nowait()
        if status == 'success':
            return result
        else:
            raise Exception(result)
    except:
        return {"status": "error", "message": "Process completed but no result returned"}