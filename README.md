🏊 Dual Meet Lineup Builder

Optimize college swim meet lineups using real performance data from SwimCloud.

📌 Overview

The Dual Meet Lineup Builder is a Python-based tool for generating optimal lineups for NCAA swimming dual meets. It scrapes event times directly from SwimCloud, processes performance data, and builds competitive individual and relay assignments for a selected team.

It supports:

Single Team Optimization (best individual/team performance)
Strategic Matchups (future: beat a specific opponent)

=== Dual Meet Lineup Builder ===

1. Single Team Lineup (best overall performance)
2. Strategic Dual Team Lineup (beat a specific opponent)
Choose mode (1-2): 1

Choose pool configuration (1-2): 1 → 8-lane pool

Enter team name: Georgia Institute of Technology
Enter year: 2025
Enter gender (M/F): M

Distance Events: 1650 Free only
IM Events: 200 IM only
Relays: 200 Medley & 200 Free

→ Scraping 15 events from SwimCloud...
✓ Successfully collected 150 time entries
✓ Lineup optimized and saved to `Georgia_Institute_of_Technology_times.xlsx`


✅ Features

Interactive CLI for user inputs (team, year, gender, events, relays)
Automated scraping of SwimCloud event data using Selenium
Data processing pipeline:
Raw swimmer time extraction
Pivoting and cleaning
Performance-based assignment for:
Individual events
200 Free/Medley Relay teams (A/B squads)
Output options: .txt, .csv, .xlsx
Swimmer usage tracking to balance lineups
📂 Outputs

A full event-by-event lineup:
Top 4 swimmers per individual event
Relay squads with legs assigned by best times
Exported in multiple formats:
Georgia_Institute_of_Technology_times.xlsx
individual_lineup.txt
lineup.csv
🧠 Example Output Snapshot

200 Free Relay A

Leandro Odorici – 19.26
Robin Yeboah – 19.63
David Gapinski – 19.84
Ricky Balduccini – 20.04
100 Fly

Antonio Romero – 45.78
Stephen Jones – 45.90
Ricky Balduccini – 46.28
Robin Yeboah – 46.66

⚙️ Requirements

Python 3.8+
pandas, selenium, openpyxl, beautifulsoup4, lxml

🧑‍💻 Author

Blake Burnley
Georgia Institute of Technology
