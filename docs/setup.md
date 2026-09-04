Quick Setup Plan
Initialize Environment:
Extract the ZIP and open your terminal in the folder.
Run npm install to set up Playwright.
Run pip install -r requirements.txt for the Python agents.
Create a .env file from the .env.example template and add your Gemini API Key.
Handle Authentication:
Run node scrapers/auth_manager.js.
A browser will open. Log into Work at a Startup (YC) and Otta.
Once logged in, wait 5 seconds and close the browser. This saves your session cookies to data/auth_state.json.
Run the Pipeline:
Scrape: Run node scrapers/yc_scraper.js. It will auto-scroll and capture ~150 leads.
Analyze: Run python engine/analyzer.py. This script will research the companies, synthesize ideas via Gemini, and generate Mermaid diagrams.
Launch: Run python -m streamlit run dashboard/app.py. 
Daily Build:
Filter for "Zero-to-One" ideas in the dashboard.
Pick an idea, click "Export README", and use the generated build spec in your /builds folder to launch your MVP.
Final Pro-Tip: Since you are using the Gemini Free Tier, the analyzer.py script includes a 4-second delay between requests. This ensures you don't hit the 15 RPM (Requests Per Minute) limit while generating your 1000+ ideas. 