# Product-a-Day Idea Factory
An automated agent that extracts market gaps from job postings and synthesizes 1,000+ unique, buildable product ideas.

## Setup Instructions
1. **API Keys**: Get a Gemini API key from Google AI Studio.
2. **Environment**: Copy `.env.example` to `.env` and add your key.
3. **Install Node.js Dependencies**: `npm install`
4. **Install Python Dependencies**: `pip install -r requirements.txt`
5. **Auth**: Run `node scrapers/auth_manager.js` to log in to YC or Otta.
6. **Scrape**: Run `node scrapers/yc_scraper.js` or `node scrapers/otta_scraper.js`.
7. **Analyze**: Run `python engine/analyzer.py`.
8. **Dashboard**: Run `streamlit run dashboard/app.py`.
