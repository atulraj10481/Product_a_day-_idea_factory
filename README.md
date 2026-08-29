# 🚀 Product-a-Day Idea Factory

An automated, end-to-end intelligence pipeline that reverse-engineers hiring needs and job descriptions from top startup platforms (**Y Combinator, Work at a Startup, LinkedIn, Wellfound, YC RFS**) into validated, build-ready product opportunities.

Equipped with a modern **Streamlit Dashboard**, **Binary Build Decision Engine**, **Claude-Style Split Artifact Inspector**, and **Automated 4-Day Rotating Cloud Scraping via GitHub Actions**.

---

## ⚡ Architecture Overview

```
                      ┌───────────────────────────────────────────────┐
                      │          Job Postings & Hiring Data           │
                      │   (YC • Work at a Startup • LinkedIn • Wellfound)
                      └───────────────────────┬───────────────────────┘
                                              │ (Playwright Headless Scrapers)
                                              ▼
                      ┌───────────────────────────────────────────────┐
                      │              Raw Jobs Ingestion               │
                      │             (data/raw_jobs.json)              │
                      └───────────────────────┬───────────────────────┘
                                              │ (DuckDuckGo Context Enrichment)
                                              ▼
                      ┌───────────────────────────────────────────────┐
                      │        Multi-Provider AI Analysis Engine       │
                      │  • Primary: OpenRouter (Nvidia Nemotron 550B) │
                      │  • Fallback 1: Groq (GPT-OSS 120B / Qwen)     │
                      │  • Fallback 2: Google Gemini (3.6 Flash)      │
                      └───────────────────────┬───────────────────────┘
                                              │ (Structured Product Synthesis)
                                              ▼
                      ┌───────────────────────────────────────────────┐
                      │             Persistent Database               │
                      │              (data/factory.db)                │
                      └───────────────────────┬───────────────────────┘
                                              │
               ┌──────────────────────────────┴──────────────────────────────┐
               ▼                                                             ▼
┌───────────────────────────────────────────┐                 ┌───────────────────────────────────────────┐
│        Interactive Web Dashboard          │                 │       Automated Cloud CI/CD Pipeline      │
│           (dashboard/app.py)              │                 │      (.github/workflows/daily_...)        │
├───────────────────────────────────────────┤                 ├───────────────────────────────────────────┤
│ • Binary Build Decision (🔨 Build / ❌)   │                 │ • 4-Day Rotating Platform Scraper         │
│ • Claude-Style Split-View README Preview  │                 │ • Daily 5:30 AM IST (00:00 UTC) Cron      │
│ • Rendered Mermaid Architecture Graphs    │                 │ • Auto-commits fresh database to GitHub   │
│ • Multi-criteria Filtering & CSV Export   │                 │ • Auto-syncs live on Streamlit Cloud      │
└───────────────────────────────────────────┘                 └───────────────────────────────────────────┘
```

---

## 🎯 Key Features

1. **Multi-Platform Scrapers**:
   - **Work at a Startup (YC)**: Targeted role search across high-growth YC startups.
   - **YC Requests for Startups (RFS)**: Direct extraction of problems YC wants founders to build.
   - **LinkedIn Jobs**: Role query search with cookie-authenticated and guest-mode scraping.
   - **Wellfound (AngelList Talent)**: Startup hiring opportunities with Cloudflare challenge resilience.

2. **Multi-Provider AI Fallback Engine**:
   - **Primary Model**: `nvidia/nemotron-3-ultra-550b-a55b:free` via OpenRouter.
   - **Instant Fallback**: `openai/gpt-oss-120b` via Groq whenever rate limits or capacity constraints occur.
   - **Outputs**: Market Pain Point, Standalone Workflow Product Idea, Zero-to-One Classification, Mermaid.js Architecture Diagram, Recommended Stack, and Feasibility/MVP Score.

3. **Founder Decision Board & Claude-Style Inspector**:
   - **Binary Build Decision**: One-click toggling between **`⏳ Unreviewed`**, **`🔨 Build`**, or **`❌ Skip`**.
   - **Inline Notes & Remarks**: Add thoughts and rationale with real-time auto-saving to SQLite.
   - **Claude-Style Split View**: Clicking **`📖 View README`** docks an artifact inspector on the right with formatted Markdown preview, raw code view, and live rendered Mermaid flowchart.

4. **100% Free Rotating Cloud Pipeline**:
   - Daily GitHub Actions cron runs at **5:30 AM IST (00:00 UTC)**, rotating 1 platform every 4 days.
   - Automatically commits updated database and raw jobs to GitHub, triggering Streamlit Cloud to update live.

---

## 🛠️ Local Quickstart

### Prerequisites
- **Node.js**: v18.0 or higher
- **Python**: v3.10 or higher
- **Playwright Chromium**: For browser scraping

### 1. Clone & Install Dependencies

```bash
# Clone the repository
git clone https://github.com/YourUsername/Product_a_day_idea_factory.git
cd Product_a_day_idea_factory

# Install Node.js dependencies & Playwright browsers
npm install
npx playwright install chromium

# Create and activate Python virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install Python dependencies
pip install -r requirements.txt
```

### 2. Configure Environment Variables

Create a `.env` file in the project root:

```env
# AI Providers (At least one required)
OPENROUTER_API_KEY=sk-or-v1-your-openrouter-key
GROQ_API_KEY=gsk_your-groq-key(Optional)
GEMINI_API_KEY=AIzaSy-your-gemini-key(Optional)

# Product stack preferences
KNOWN_STACK=Node.js, Python, React
```

### 3. Generate Scraper Auth Cookies (Optional for LinkedIn/Wellfound)

```bash
node scrapers/auth_manager.js
```
*Opens interactive browser tabs for YC, LinkedIn, and Wellfound. Once logged in, press ENTER in the terminal to save `data/auth_state.json` and generate `data/auth_state.b64.txt`.*

### 4. Run Scrapers & Idea Generation

```bash
# Option A: Run individual scraper
node scrapers/yc_scraper.js
node scrapers/yc_rfs_scraper.js
node scrapers/linkedin_scraper.js
node scrapers/wellfound_scraper.js

# Option B: Run AI Analyzer Engine
python engine/analyzer.py
```

### 5. Launch the Dashboard

```bash
streamlit run dashboard/app.py
```
Open **`http://localhost:8501`** in your browser.

---

## ☁️ 100% Free Cloud Deployment

### 1. Push Repository to GitHub

```bash
git add .
git commit -m "Initial commit of Product Idea Factory"
git push origin main
```

### 2. Configure GitHub Actions Secrets
In your GitHub repository, go to **Settings > Secrets and variables > Actions > New repository secret** and add:

| Secret Name | Value |
| :--- | :--- |
| `AUTH_STATE_BASE64` | Paste content from `data/auth_state.b64.txt` *(Emits warning & runs public scrapers if omitted)* |
| `OPENROUTER_API_KEY` | Your OpenRouter API key |
| `GROQ_API_KEY` | Your Groq API key |
| `GEMINI_API_KEY` | Your Gemini API key |

### 3. Deploy Dashboard on Streamlit Community Cloud
1. Navigate to **[share.streamlit.io](https://share.streamlit.io/)** and sign in with GitHub.
2. Click **"New app"** and fill in:
   - **Repository**: `YourUsername/Product_a_day_idea_factory`
   - **Branch**: `main`
   - **Main file path**: `dashboard/app.py`
3. Under **Advanced settings > Secrets (TOML)**, paste:
   ```toml
   OPENROUTER_API_KEY = "sk-or-v1-..."
   GROQ_API_KEY = "gsk_..."
   GEMINI_API_KEY = "AIzaSy..."
   KNOWN_STACK = "Node.js, Python, React"
   ```
4. Click **Deploy**. Your dashboard is now live on a public URL.

---

## 📅 Rotating 4-Day Schedule Breakdown

The GitHub Actions workflow (`.github/workflows/daily_rotating_factory.yml`) runs every morning at **00:00 UTC (5:30 AM IST)** on a 4-day rotating cycle:

| Day Index (`DayOfYear % 4`) | Scraper Executed | Notes |
| :---: | :--- | :--- |
| **Day 0** | **Work at a Startup (YC)** | Focuses on Product Manager, Founding Engineer, & GTM roles |
| **Day 1** | **YC Requests for Startups (RFS)** | 100% Public YC founder problem statements |
| **Day 2** | **LinkedIn Jobs** | Authenticated via `AUTH_STATE_BASE64` (or guest fallback) |
| **Day 3** | **Wellfound (AngelList)** | Startup hiring opportunities with Cloudflare challenge resilience |

*After each scraper finishes, `engine/analyzer.py` immediately analyzes new jobs and commits `data/factory.db` to GitHub, which automatically updates your live Streamlit Cloud app.*

---

## 📂 Project Structure

```
├── .github/
│   └── workflows/
│       └── daily_rotating_factory.yml # 4-day rotating scheduled workflow
├── .streamlit/
│   └── config.toml                    # Production theme & server settings
├── builds/                            # Exported individual idea Markdown files & CSVs
├── dashboard/
│   └── app.py                         # Streamlit UI with Split-View Claude Inspector
├── data/
│   ├── factory.db                     # SQLite database (leads, ideas, remarks, decisions)
│   ├── raw_jobs.json                  # Ingested raw job postings
│   ├── auth_state.json                # Local scraper session cookies (gitignored)
│   └── auth_state.b64.txt             # Gzip-compressed Base64 secret string (gitignored)
├── engine/
│   └── analyzer.py                    # Multi-provider AI gap analysis & JSON synthesis
├── scrapers/
│   ├── auth_manager.js                # Interactive multi-platform login & cookie compressor
│   ├── linkedin_scraper.js            # LinkedIn Playwright scraper
│   ├── wellfound_scraper.js           # Wellfound Playwright scraper
│   ├── yc_scraper.js                  # Work at a Startup scraper
│   └── yc_rfs_scraper.js              # YC Requests for Startups scraper
├── .env.example                       # Environment variables template
├── .gitignore                         # Protects secrets & node_modules
├── package.json                       # Node dependencies (Playwright)
├── requirements.txt                   # Python dependencies (Streamlit, Pandas, GenAI, Groq)
└── README.md                          # Documentation
```

---

## 📄 License
MIT License. Built for builders, founders, and product engineers.
