# Technical Architecture
- **Ingestion**: Node.js + Playwright (Headless/Persistent Auth).
- **Enrichment**: Python + DuckDuckGo Search API.
- **Synthesis**: Google Gemini 1.5 Flash (Chain-of-thought prompting).
- **Storage**: SQLite for leads, cache, and final ideas.
- **UI**: Streamlit with Mermaid.js rendering.
