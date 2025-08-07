Dual Meet Lineup Builder
Dual Meet Lineup Builder is a web based tool that helps swim coaches generate optimal swim meet lineups using real time performance data. The application lets users configure pool size, select events, set swimmer limits, and choose a lineup strategy, then generates a complete lineup including individual events, relays, and downloadable Excel or text files ready for use in competition planning.

What It Does
The app lets users choose between a single team lineup that maximizes overall point scoring and a strategic dual team lineup that optimizes lineups against a specific opponent. Users can select pool lane configuration, specify team information, choose which distance, IM, and relay events to include, set the maximum number of events per swimmer, and pick a lineup generation strategy (balanced, depth focused, or speed focused). After configuration, the app generates a detailed lineup, displays summary statistics, and provides download links for the generated files.

Core Features
Mode selection lets users switch between single team and strategic dual team modes, with the interface adapting to show the appropriate fields.
Pool configuration lets users choose an 8 lane or 10 lane pool, which determines the number of swimmers per event.
Team information captures team name, year, gender, and opponent name (in dual mode).
Event selection lets users include or exclude distance, IM, and relay events, with options for 1650 Free, 1000 Free, 200 IM, 400 IM, and various relay combinations.
Swimmer event limits let users set a conservative (3), standard (4), or aggressive (5) event limit per swimmer.
Lineup strategy (balanced, depth focused, speed focused) is available for single team mode.
Result display shows a summary of total swimmers, events assigned, relays created, and a score board for dual team results, with clear status indicators (ready, processing, error).
Downloadable files include Excel sheets for individual events, relay events, swimmer event mapping, swimmer summary, and an overall summary, plus a plain text version for coaches.
Technology Stack
The project is built with HTML, CSS, and JavaScript for the front end, while the back end uses Python with Flask to handle API requests. The application is containerized with Docker, which installs Chromium and ChromeDriver for headless browsing. The API endpoint /api/generate-lineup receives a JSON payload that matches the front end state and returns a JSON object containing the generated lineup and a list of output files.

Installation & Running Locally
Clone the repository and navigate to the project directory.
Create a Python virtual environment, activate it, and install the dependencies from requirements.txt.
Run the Flask application with python app.py (or use the provided Dockerfile).
Open http://localhost:5000 in a browser to access the UI.
