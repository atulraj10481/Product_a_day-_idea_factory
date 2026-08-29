import streamlit as st
import sqlite3
import pandas as pd
import streamlit_mermaid as st_mermaid
import os
import subprocess
import json
from datetime import datetime

# ─── Page Config ─────────────────────────────────────────────────────────────
st.set_page_config(page_title="🚀 Product Idea Factory V2", layout="wide", initial_sidebar_state="expanded")

# ─── Custom CSS ──────────────────────────────────────────────────────────────
st.markdown("""
<style>
    .stApp { background-color: #0e1117; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; }
    
    /* Header styling */
    .main-header { 
        background: linear-gradient(135deg, #4f46e5 0%, #7c3aed 50%, #9333ea 100%);
        padding: 1.25rem 2rem; border-radius: 12px; margin-bottom: 1.25rem;
        color: white; text-align: center; box-shadow: 0 4px 20px rgba(124, 58, 237, 0.2);
    }
    .main-header h1 { color: white; margin: 0; font-size: 1.85rem; font-weight: 700; letter-spacing: -0.5px; }
    .main-header p { color: rgba(255,255,255,0.85); margin: 0.25rem 0 0 0; font-size: 0.9rem; }
    
    /* Stat cards */
    .stat-card {
        background: linear-gradient(135deg, #131722 0%, #1a2035 100%);
        border: 1px solid #28334e; border-radius: 10px; padding: 0.85rem;
        text-align: center; margin-bottom: 0.4rem; box-shadow: 0 2px 8px rgba(0,0,0,0.2);
    }
    .stat-card h3 { font-size: 1.5rem; margin: 0; font-weight: 700; }
    .stat-card p { color: #94a3b8; font-size: 0.75rem; margin: 0.2rem 0 0 0; text-transform: uppercase; letter-spacing: 0.5px; }
    
    /* Badges */
    .source-badge {
        display: inline-block; padding: 3px 8px; border-radius: 6px;
        font-size: 0.7rem; font-weight: 700; color: white; margin-right: 6px;
    }
    .badge-yc { background: #ea580c; }
    .badge-linkedin { background: #0284c7; }
    .badge-wellfound { background: #e11d48; }
    .badge-yc_rfs { background: #9333ea; }
    .badge-unknown { background: #475569; }
    
    .decision-badge {
        display: inline-block; padding: 3px 10px; border-radius: 20px;
        font-size: 0.72rem; font-weight: 700; letter-spacing: 0.3px; margin-right: 6px;
    }
    .decision-BUILD { background: rgba(34, 197, 94, 0.15); color: #4ade80; border: 1px solid #22c55e; }
    .decision-SKIP { background: rgba(239, 68, 68, 0.15); color: #f87171; border: 1px solid #ef4444; }
    .decision-UNREVIEWED { background: rgba(148, 163, 184, 0.15); color: #94a3b8; border: 1px solid #475569; }
    
    /* Expanders */
    div[data-testid="stExpander"] {
        border: 1px solid #1e293b; border-radius: 10px;
        background-color: #0f172a; margin-bottom: 0.6rem;
        transition: border-color 0.2s ease, box-shadow 0.2s ease;
    }
    div[data-testid="stExpander"]:hover {
        border-color: #3b82f6; box-shadow: 0 4px 12px rgba(59, 130, 246, 0.08);
    }
    
    /* Claude-style Artifact Panel */
    .claude-artifact-container {
        background: #111827; border: 1px solid #374151; border-radius: 12px;
        padding: 1.25rem; box-shadow: 0 8px 30px rgba(0,0,0,0.5);
        margin-bottom: 1rem;
    }
    .claude-artifact-header {
        display: flex; align-items: center; justify-content: space-between;
        border-bottom: 1px solid #374151; padding-bottom: 0.75rem; margin-bottom: 1rem;
    }
    .claude-tag {
        background: #1f2937; color: #d97706; padding: 2px 8px; border-radius: 4px;
        font-size: 0.75rem; font-weight: 600; font-family: monospace; border: 1px solid #78350f;
    }
    .claude-title {
        color: #f3f4f6; font-size: 1.2rem; font-weight: 600; margin: 0.35rem 0 0 0;
    }
</style>
""", unsafe_allow_html=True)

# ─── Database ────────────────────────────────────────────────────────────────
def get_db():
    os.makedirs('data', exist_ok=True)
    conn = sqlite3.connect('data/factory.db', check_same_thread=False)
    conn.execute("""CREATE TABLE IF NOT EXISTS cache (company TEXT PRIMARY KEY, context TEXT)""")
    conn.execute("""CREATE TABLE IF NOT EXISTS ideas (
        id INTEGER PRIMARY KEY, company TEXT, role TEXT, idea_name TEXT,
        problem TEXT, mermaid_code TEXT, stack TEXT, priority TEXT,
        company_profile TEXT, job_summary TEXT, mvp_score TEXT,
        source TEXT, scraped_at TEXT, job_link TEXT, job_description TEXT,
        decision TEXT DEFAULT 'UNREVIEWED', remark TEXT DEFAULT '')""")
    
    # Ensure decision and remark columns exist
    cursor = conn.cursor()
    cursor.execute("PRAGMA table_info(ideas)")
    existing_cols = [r[1] for r in cursor.fetchall()]
    if 'decision' not in existing_cols:
        cursor.execute("ALTER TABLE ideas ADD COLUMN decision TEXT DEFAULT 'UNREVIEWED'")
    if 'remark' not in existing_cols:
        cursor.execute("ALTER TABLE ideas ADD COLUMN remark TEXT DEFAULT ''")
    conn.commit()
    return conn

def update_idea_analysis(idea_id, decision, remark):
    conn = get_db()
    conn.execute("UPDATE ideas SET decision = ?, remark = ? WHERE id = ?", (str(decision), str(remark), int(idea_id)))
    conn.commit()

def get_raw_jobs_count():
    if os.path.exists('data/raw_jobs.json'):
        try:
            with open('data/raw_jobs.json', 'r', encoding='utf-8') as f:
                return len(json.load(f))
        except: return 0
    return 0

def clean_ideas_dataframe(raw_df):
    if raw_df is None or raw_df.empty:
        return pd.DataFrame()
    
    df = raw_df.copy()
    if 'id' in df.columns:
        df['id'] = df['id'].astype(int)
        
    text_cols = ['company', 'role', 'idea_name', 'problem', 'mermaid_code', 'stack', 'priority', 
                 'company_profile', 'job_summary', 'mvp_score', 'source', 'scraped_at', 
                 'job_link', 'job_description', 'decision', 'remark']
    for col in text_cols:
        if col not in df.columns:
            df[col] = ''
        else:
            df[col] = df[col].fillna('').astype(str)
            
    return df

def generate_markdown_content(row, source, scraped):
    decision_text = str(row.get('decision') or 'UNREVIEWED')
    remark_text = str(row.get('remark') or '')
    
    md = f"""# {row.get('idea_name', 'Product Idea')}

> **Status:** `{decision_text}` | **Company Target:** {row.get('company', 'Unknown')} | **Priority:** {row.get('priority', 'Zero-to-One')}

---

## 1. Company Profile
{row.get('company_profile') or 'Company background context not available.'}

## 2. Job Description Summary
{row.get('job_summary') or 'Job posting summary not available.'}

## 3. Product Opportunity & Problem Solved
**Core Pain Point:**
{row.get('problem') or 'Problem statement not available.'}

**Hiring Role Context:**
{row.get('role', 'N/A')}

## 4. Workflow & System Architecture
```mermaid
{row.get('mermaid_code', '')}
```

## 5. Recommended Tech Stack
```text
{row.get('stack') or 'Stack recommendations not available.'}
```

## 6. MVP Score & Feasibility Justification
{row.get('mvp_score') or 'MVP evaluation not available.'}

---

## 7. Analysis & Build Decision
- **Build Decision:** `{decision_text}`
- **Founder Remarks:** {remark_text if remark_text else '_No remarks recorded yet._'}

---
*Source: {source.upper()} | Scraped: {scraped} | Job Link: {row.get('job_link', 'N/A')}*
"""
    return md

# ─── Initialize Session State ────────────────────────────────────────────────
if 'preview_idea_id' not in st.session_state:
    st.session_state['preview_idea_id'] = None

# ─── Header ──────────────────────────────────────────────────────────────────
st.markdown("""
<div class="main-header">
    <h1>🚀 Product Idea Factory V2</h1>
    <p>Multi-platform scraping • AI gap analysis • Binary build decisions & Claude-style artifact inspector</p>
</div>
""", unsafe_allow_html=True)

# ─── Sidebar: Command Center ────────────────────────────────────────────────
st.sidebar.markdown("## ⚡ Command Center")

col1, col2 = st.sidebar.columns(2)
with col1:
    run_all = st.button("🔄 Run All Scrapers", use_container_width=True)
with col2:
    run_analyzer = st.button("🧠 Run Analyzer", use_container_width=True)

st.sidebar.markdown("---")
st.sidebar.markdown("### 🕸️ Scrapers")
c1, c2 = st.sidebar.columns(2)
with c1:
    run_yc = st.button("🟠 YC Jobs", use_container_width=True)
    run_wellfound = st.button("🔴 Wellfound", use_container_width=True)
with c2:
    run_linkedin = st.button("🔵 LinkedIn", use_container_width=True)
    run_rfs = st.button("🟣 YC RFS", use_container_width=True)

# Handle button clicks
def run_script(cmd, label):
    with st.spinner(f"Running {label}..."):
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, cwd=os.getcwd(), timeout=300, encoding='utf-8', errors='replace')
            if result.returncode == 0:
                st.sidebar.success(f"✅ {label} complete!")
                st.sidebar.code(result.stdout[-400:] if len(result.stdout) > 400 else result.stdout, language="text")
            else:
                st.sidebar.error(f"❌ {label} failed!")
                st.sidebar.code(result.stderr[-400:] if len(result.stderr) > 400 else result.stderr, language="text")
        except subprocess.TimeoutExpired:
            st.sidebar.warning(f"⏳ {label} timed out (5 min limit).")
        except Exception as e:
            st.sidebar.error(f"Error: {e}")

if run_yc:
    run_script(["node", "scrapers/yc_scraper.js"], "YC Scraper")
if run_linkedin:
    run_script(["node", "scrapers/linkedin_scraper.js"], "LinkedIn Scraper")
if run_wellfound:
    run_script(["node", "scrapers/wellfound_scraper.js"], "Wellfound Scraper")
if run_rfs:
    run_script(["node", "scrapers/yc_rfs_scraper.js"], "YC RFS Scraper")
if run_all:
    for cmd, label in [
        (["node", "scrapers/yc_scraper.js"], "YC"),
        (["node", "scrapers/linkedin_scraper.js"], "LinkedIn"),
        (["node", "scrapers/wellfound_scraper.js"], "Wellfound"),
        (["node", "scrapers/yc_rfs_scraper.js"], "YC RFS"),
    ]:
        run_script(cmd, label)
if run_analyzer:
    run_script(["python", "engine/analyzer.py"], "Analyzer")

# Auth Status Indicator
has_auth_file = os.path.exists('data/auth_state.json')
if has_auth_file:
    st.sidebar.caption("🟢 **Scraper Session:** Authenticated (`auth_state.json`)")
else:
    st.sidebar.caption("🟡 **Scraper Session:** Public / Guest Mode (`auth_state.json` absent)")

# ─── Load & Clean Data ──────────────────────────────────────────────────────
try:
    df_raw = pd.read_sql("SELECT * FROM ideas ORDER BY id DESC", get_db())
    df = clean_ideas_dataframe(df_raw)
    raw_count = get_raw_jobs_count()
except Exception as e:
    df = pd.DataFrame()
    raw_count = 0

# ─── Sidebar: Stats & Decisions Bar ─────────────────────────────────────────
st.sidebar.markdown("---")
st.sidebar.markdown("### 📊 Pipeline & Decisions")

total_ideas = len(df)
count_build = len(df[df['decision'] == 'BUILD']) if not df.empty else 0
count_skip = len(df[df['decision'] == 'SKIP']) if not df.empty else 0
count_unrev = total_ideas - count_build - count_skip

s1, s2 = st.sidebar.columns(2)
with s1:
    st.markdown(f'<div class="stat-card"><h3 style="color:#60a5fa;">{raw_count}</h3><p>Jobs Scraped</p></div>', unsafe_allow_html=True)
    st.markdown(f'<div class="stat-card"><h3 style="color:#4ade80;">{count_build}</h3><p>🔨 To Build</p></div>', unsafe_allow_html=True)
with s2:
    st.markdown(f'<div class="stat-card"><h3 style="color:#a78bfa;">{total_ideas}</h3><p>Ideas Generated</p></div>', unsafe_allow_html=True)
    st.markdown(f'<div class="stat-card"><h3 style="color:#f87171;">{count_skip}</h3><p>❌ Skipped</p></div>', unsafe_allow_html=True)

# ─── Sidebar: Filters ───────────────────────────────────────────────────────
st.sidebar.markdown("---")
st.sidebar.markdown("### 🔍 Filters")

decision_filter_map = {
    "All": "ALL",
    "🔨 To Build": "BUILD",
    "❌ Skipped": "SKIP",
    "⏳ Unreviewed": "UNREVIEWED"
}
selected_decision_label = st.sidebar.selectbox("Build Decision Status", list(decision_filter_map.keys()), index=0)
selected_decision = decision_filter_map[selected_decision_label]

if not df.empty:
    priority_options = [p for p in df['priority'].unique().tolist() if p]
    priority = st.sidebar.multiselect("Priority", priority_options, default=priority_options)

    source_options = [s for s in df['source'].unique().tolist() if s]
    source_filter = st.sidebar.multiselect("Source Platform", source_options, default=source_options) if source_options else []
    search_term = st.sidebar.text_input("🔎 Search company, idea, or remarks")
else:
    priority = []
    source_filter = []
    search_term = ""

if st.sidebar.button("🗑️ Clear Research Cache"):
    conn = get_db()
    conn.execute("DELETE FROM cache")
    conn.commit()
    st.sidebar.success("Cache cleared!")

# ─── Main Content Area ───────────────────────────────────────────────────────
if df.empty:
    st.warning("🚧 No ideas generated yet. Use the Command Center in the sidebar to run scrapers and the analyzer.")
else:
    # Apply filters
    filtered = df.copy()
    if priority:
        filtered = filtered[filtered['priority'].isin(priority)]
    if source_filter:
        filtered = filtered[filtered['source'].isin(source_filter) | (filtered['source'] == '')]
    
    if selected_decision != "ALL":
        if selected_decision == "UNREVIEWED":
            filtered = filtered[(filtered['decision'] == 'UNREVIEWED') | (filtered['decision'] == '')]
        else:
            filtered = filtered[filtered['decision'] == selected_decision]

    if search_term:
        st_clean = str(search_term).lower()
        mask = (
            filtered['company'].str.lower().str.contains(st_clean, na=False) |
            filtered['idea_name'].str.lower().str.contains(st_clean, na=False) |
            filtered['problem'].str.lower().str.contains(st_clean, na=False) |
            filtered['remark'].str.lower().str.contains(st_clean, na=False)
        )
        filtered = filtered[mask]

    # Top bar with export & view layout controls
    col_heading, col_actions = st.columns([3, 2])
    with col_heading:
        st.markdown(f"### 💡 Showing **{len(filtered)}** of **{len(df)}** Ideas")
    with col_actions:
        ac1, ac2 = st.columns(2)
        with ac1:
            if st.button("📥 Export CSV", use_container_width=True):
                os.makedirs('builds', exist_ok=True)
                filtered.to_csv('builds/all_ideas.csv', index=False)
                st.success("Saved to builds/all_ideas.csv")
        with ac2:
            if st.session_state['preview_idea_id'] is not None:
                if st.button("✕ Close Preview", use_container_width=True):
                    st.session_state['preview_idea_id'] = None
                    st.rerun()

    # Check if Split-View is active
    preview_id = st.session_state.get('preview_idea_id')
    has_preview = preview_id is not None and int(preview_id) in df['id'].values

    if has_preview:
        col_list, col_preview = st.columns([11, 10])
    else:
        col_list = st.container()

    # Render Left Column: Ideas List
    with col_list:
        for _, row in filtered.iterrows():
            row_id = int(row['id'])
            source = str(row.get('source') or 'unknown').lower()
            badge_class = f"badge-{source}" if source in ['yc', 'linkedin', 'wellfound', 'yc_rfs'] else 'badge-unknown'
            
            scraped = str(row.get('scraped_at') or '')
            if scraped and scraped.lower() not in ['none', 'nan', '']:
                try:
                    scraped = datetime.fromisoformat(scraped.replace('Z', '+00:00')).strftime('%b %d, %Y')
                except Exception:
                    scraped = scraped[:10]
            else:
                scraped = ''

            current_decision = str(row.get('decision') or 'UNREVIEWED').strip()
            if current_decision not in ["BUILD", "SKIP", "UNREVIEWED"]:
                current_decision = "UNREVIEWED"
                
            current_remark = str(row.get('remark') or '').strip()
            is_selected = (has_preview and int(preview_id) == row_id)
            
            # Header markup with decision badge
            decision_badge_html = f'<span class="decision-badge decision-{current_decision}">{current_decision}</span>'
            source_badge_html = f'<span class="source-badge {badge_class}">{source.upper()}</span>'
            card_title = f"{row.get('idea_name', 'Untitled')} — {row.get('company', '')}"

            with st.expander(f"{'🔎 [PREVIEWING] ' if is_selected else ''}{current_decision} | {row.get('idea_name', 'Untitled')} — {row.get('company', '')}", expanded=is_selected):
                st.markdown(f"{source_badge_html} {decision_badge_html} **{row.get('priority', '')}** | {card_title}", unsafe_allow_html=True)
                st.markdown("---")

                # ─── Binary Decision & Remark Section ───────────────────
                st.markdown("##### 🎯 Build Decision & Analysis")
                d_col1, d_col2 = st.columns([3, 4])
                
                decision_options = ["⏳ Unreviewed", "🔨 Build", "❌ Skip"]
                decision_val_map = {"⏳ Unreviewed": "UNREVIEWED", "🔨 Build": "BUILD", "❌ Skip": "SKIP"}
                rev_val_map = {"UNREVIEWED": "⏳ Unreviewed", "BUILD": "🔨 Build", "SKIP": "❌ Skip"}
                
                default_idx = 0
                if current_decision in rev_val_map:
                    default_idx = decision_options.index(rev_val_map[current_decision])

                with d_col1:
                    chosen_label = st.radio(
                        "Decision",
                        decision_options,
                        index=default_idx,
                        key=f"dec_radio_{row_id}",
                        horizontal=True,
                        label_visibility="collapsed"
                    )
                    chosen_decision = decision_val_map[chosen_label]

                with d_col2:
                    remark_input = st.text_input(
                        "Remark",
                        value=current_remark,
                        key=f"rem_input_{row_id}",
                        placeholder="Add brief reason / notes...",
                        label_visibility="collapsed"
                    )

                # Save decision if changed
                if chosen_decision != current_decision or remark_input != current_remark:
                    update_idea_analysis(row_id, chosen_decision, remark_input)
                    st.toast(f"Saved: {row.get('idea_name', 'Idea')} ➔ {chosen_decision}", icon="💾")
                    st.rerun()

                st.markdown("---")

                # ─── Idea Details ───────────────────────────────────────
                st.markdown(f"**🎯 Problem:** {row.get('problem', 'N/A')}")
                st.markdown(f"**💼 Role:** {row.get('role', 'N/A')}")
                
                mvp = row.get('mvp_score')
                if mvp and str(mvp).lower() not in ['none', 'nan', '']:
                    st.markdown(f"**📊 MVP Score:** {mvp}")

                # Stack snippet
                st.markdown("**🛠️ Suggested Stack:**")
                st.code(row.get('stack', 'N/A'), language="text")

                # Action buttons (View in Claude Panel / Export)
                btn_c1, btn_c2, btn_c3 = st.columns([3, 3, 4])
                with btn_c1:
                    if st.button("📖 View README", key=f"btn_preview_{row_id}", use_container_width=True):
                        st.session_state['preview_idea_id'] = row_id
                        st.rerun()
                with btn_c2:
                    safe_name = str(row.get('idea_name') or 'idea').replace(' ', '_').replace('/', '_')
                    md_content = generate_markdown_content(row, source, scraped)
                    st.download_button(
                        "📥 Download .md",
                        data=md_content,
                        file_name=f"{safe_name}.md",
                        mime="text/markdown",
                        key=f"dl_{row_id}",
                        use_container_width=True
                    )
                with btn_c3:
                    job_link = str(row.get('job_link', '')).strip()
                    if job_link and job_link.lower() not in ['none', 'nan', ''] and (job_link.startswith('http://') or job_link.startswith('https://')):
                        st.link_button("🔗 Job Posting", job_link, use_container_width=True)

    # Render Right Column: Claude-Style Artifact Panel
    if has_preview:
        with col_preview:
            preview_row = df[df['id'] == int(preview_id)].iloc[0]
            p_source = str(preview_row.get('source') or 'unknown').lower()
            p_scraped = str(preview_row.get('scraped_at') or '')
            if p_scraped and p_scraped.lower() not in ['none', 'nan', '']:
                try:
                    p_scraped = datetime.fromisoformat(p_scraped.replace('Z', '+00:00')).strftime('%b %d, %Y')
                except Exception:
                    p_scraped = p_scraped[:10]
            else:
                p_scraped = ''

            safe_name = str(preview_row.get('idea_name') or 'idea').replace(' ', '_').replace('/', '_')
            md_content = generate_markdown_content(preview_row, p_source, p_scraped)

            st.markdown(f"""
            <div class="claude-artifact-container">
                <div class="claude-artifact-header">
                    <div>
                        <span class="claude-tag">ARTIFACT: README.MD</span>
                        <h3 class="claude-title">{preview_row.get('idea_name', 'Idea')}</h3>
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)

            tab_preview, tab_raw, tab_graph = st.tabs(["📖 Document Preview", "💻 Raw Markdown", "📊 Mermaid Graph"])
            
            with tab_preview:
                st.markdown(md_content)

            with tab_raw:
                st.code(md_content, language="markdown")

            with tab_graph:
                mermaid_code = preview_row.get('mermaid_code', '')
                if mermaid_code and str(mermaid_code).lower() not in ['none', 'nan', '']:
                    try:
                        st_mermaid.st_mermaid(mermaid_code)
                    except Exception:
                        st.code(mermaid_code, language="text")
                else:
                    st.info("No Mermaid code available for this idea.")

            # Bottom control in preview panel
            p_col1, p_col2 = st.columns(2)
            with p_col1:
                if st.button("💾 Save to builds/*.md", key=f"save_md_{preview_id}", use_container_width=True):
                    os.makedirs('builds', exist_ok=True)
                    with open(f"builds/{safe_name}.md", 'w', encoding='utf-8') as f:
                        f.write(md_content)
                    st.success(f"Saved `builds/{safe_name}.md`")
            with p_col2:
                if st.button("✕ Close Inspector", key="close_side_pane", use_container_width=True):
                    st.session_state['preview_idea_id'] = None
                    st.rerun()
