🏊 Dual Meet Lineup Builder

Optimize swim meet lineups using real-time performance data from SwimCloud.

📌 Overview

The Dual Meet Lineup Builder is a Python application that helps college swim coaches and analysts create the most competitive meet lineups possible.

Built for NCAA dual meets, it automates the data collection and lineup selection process based on real swimmer times.

🧠 Mode Selection

1️⃣ Single Team Lineup (Best Overall Performance)
Selects the fastest possible lineup for a single team, maximizing potential point scoring using the top swimmers available in each event.
Use case:

Prepare for conference or championship meets
Identify team strengths and swimmer roles
Benchmark top performance scenarios
2️⃣ Strategic Dual Team Lineup (Beat a Specific Opponent)
(Coming soon) Builds a competitive lineup against a specific opposing team, using performance data for both teams to maximize the likelihood of a win.
Use case:

Head-to-head meet planning
Optimize matchups strategically (not just by fastest time)
Conserve swimmer energy while targeting winnable events
✅ Features

🧠 Intelligent event assignment based on real times
🕵️‍♂️ Web scraper for SwimCloud college team data
📊 Relay and individual event sorting
📁 Exports to .xlsx, .csv, and .txt
🧮 Swimmer usage control to avoid overloading athletes

🚀 Quick Start
Follow the interactive prompts to:

Select your mode (Single or Dual Team)
Choose pool configuration (8 or 10 lanes)
Input your team, year, and gender
Choose which events to include
View and export your lineup

📂 Output Files

individual_lineup.txt — readable event summary
lineup.csv — swimmer assignments per event
YourTeamName_times.xlsx — detailed swimmer times per event
