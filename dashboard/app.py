import streamlit as st
import sqlite3
import pandas as pd
import streamlit_mermaid as st_mermaid
import os
import sys
import subprocess
import json
import base64
from datetime import datetime
from dotenv import load_dotenv

# Ensure repository root and current directory are in sys.path
_CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
_PROJECT_ROOT = os.path.dirname(_CURRENT_DIR)
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)
if _CURRENT_DIR not in sys.path:
    sys.path.insert(0, _CURRENT_DIR)

load_dotenv(override=True)

# UTF-8 stdout configuration
if sys.stdout:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
if sys.stderr:
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

try:
    from dashboard.db import (
        get_db,
        get_admin_email,
        get_community_metrics,
        get_user_review_stats,
        save_user_review,
        get_paginated_ideas,
        get_distinct_filter_values
    )
    from dashboard.auth import (
        get_current_user,
        is_admin,
        logout_user,
        render_auth_dialog,
        render_profile_dialog
    )
except (ModuleNotFoundError, ImportError):
    from db import (
        get_db,
        get_admin_email,
        get_community_metrics,
        get_user_review_stats,
        save_user_review,
        get_paginated_ideas,
        get_distinct_filter_values
    )
    from auth import (
        get_current_user,
        is_admin,
        logout_user,
        render_auth_dialog,
        render_profile_dialog
    )

# ─── Logo Helper ─────────────────────────────────────────────────────────────
_LOGO_FILE = os.path.join(_CURRENT_DIR, "assets", "logo.png")
if os.path.exists(_LOGO_FILE):
    LOGO_PATH = _LOGO_FILE
else:
    LOGO_PATH = os.path.join(_PROJECT_ROOT, "dashboard", "assets", "logo.png")

def get_base64_logo():
    if os.path.exists(LOGO_PATH):
        try:
            with open(LOGO_PATH, "rb") as f:
                return base64.b64encode(f.read()).decode("utf-8")
        except Exception:
            return ""
    return ""

# ─── Page Configuration ──────────────────────────────────────────────────────
page_icon_val = LOGO_PATH if os.path.exists(LOGO_PATH) else ":material/factory:"
st.set_page_config(
    page_title="Product Idea Factory",
    page_icon=page_icon_val,
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ─── Modern Aesthetics & Design System ───────────────────────────────────────
st.markdown("""
<style>
    .stApp {
        background-color: #0b0f19;
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
    }
    
    /* Top Header */
    .hero-header {
        background: linear-gradient(135deg, #131b2e 0%, #1e1b4b 50%, #2e1065 100%);
        border: 1px solid #312e81;
        padding: 1.25rem 2rem;
        border-radius: 14px;
        margin-bottom: 1.25rem;
        color: white;
        box-shadow: 0 8px 30px rgba(0, 0, 0, 0.35);
    }
    .hero-title {
        font-size: 1.85rem;
        font-weight: 800;
        margin: 0;
        letter-spacing: -0.5px;
        color: #ffffff;
    }
    .hero-subtitle {
        color: #94a3b8;
        font-size: 0.92rem;
        margin: 0.35rem 0 0 0;
        font-weight: 400;
    }
    
    /* SaaS KPI Metric Cards (No Emojis, Modern Status Accents) */
    .metrics-container {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
        gap: 0.85rem;
        margin-bottom: 1.25rem;
    }
    .metric-box {
        background: #111827;
        border: 1px solid #1f2937;
        border-radius: 12px;
        padding: 1rem 1.15rem;
        text-align: left;
        box-shadow: 0 4px 16px rgba(0, 0, 0, 0.2);
        transition: transform 0.2s ease, border-color 0.2s ease;
    }
    .metric-box:hover {
        transform: translateY(-2px);
    }
    .metric-accent-ideas { border-top: 3px solid #818cf8; }
    .metric-accent-jobs { border-top: 3px solid #38bdf8; }
    .metric-accent-build { border-top: 3px solid #34d399; }
    .metric-accent-skip { border-top: 3px solid #f87171; }
    .metric-accent-unrev { border-top: 3px solid #94a3b8; }
    .metric-accent-users { border-top: 3px solid #fbbf24; }
    
    .metric-val {
        font-size: 1.6rem;
        font-weight: 800;
        margin: 0;
        line-height: 1.2;
        color: #f8fafc;
        letter-spacing: -0.5px;
    }
    .metric-lbl {
        color: #94a3b8;
        font-size: 0.72rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.8px;
        margin: 0.35rem 0 0 0;
    }
    
    /* Top Search & Filter Container */
    .filter-panel {
        background: #111827;
        border: 1px solid #1f2937;
        border-radius: 12px;
        padding: 1.15rem 1.25rem;
        margin-bottom: 1.25rem;
        box-shadow: 0 4px 16px rgba(0, 0, 0, 0.2);
    }
    
    /* Clean Outline Tags */
    .source-badge {
        display: inline-block;
        padding: 2px 8px;
        border-radius: 4px;
        font-size: 0.72rem;
        font-weight: 700;
        letter-spacing: 0.5px;
        margin-right: 8px;
    }
    .badge-yc { background: rgba(234, 88, 12, 0.15); color: #fb923c; border: 1px solid rgba(234, 88, 12, 0.4); }
    .badge-linkedin { background: rgba(2, 132, 199, 0.15); color: #38bdf8; border: 1px solid rgba(2, 132, 199, 0.4); }
    .badge-wellfound { background: rgba(225, 29, 72, 0.15); color: #fb7185; border: 1px solid rgba(225, 29, 72, 0.4); }
    .badge-yc_rfs { background: rgba(147, 51, 234, 0.15); color: #c084fc; border: 1px solid rgba(147, 51, 234, 0.4); }
    .badge-unknown { background: rgba(71, 85, 105, 0.15); color: #94a3b8; border: 1px solid rgba(71, 85, 105, 0.4); }
    
    /* Modern Status Indicator Pills */
    .status-pill {
        display: inline-flex;
        align-items: center;
        gap: 5px;
        padding: 3px 10px;
        border-radius: 20px;
        font-size: 0.72rem;
        font-weight: 700;
        letter-spacing: 0.4px;
        margin-right: 8px;
    }
    .status-BUILD {
        background: rgba(34, 197, 94, 0.12);
        color: #4ade80;
        border: 1px solid rgba(34, 197, 94, 0.35);
    }
    .status-SKIP {
        background: rgba(239, 68, 68, 0.12);
        color: #f87171;
        border: 1px solid rgba(239, 68, 68, 0.35);
    }
    .status-UNREVIEWED {
        background: rgba(148, 163, 184, 0.1);
        color: #94a3b8;
        border: 1px solid #334155;
    }
    .status-dot {
        width: 6px;
        height: 6px;
        border-radius: 50%;
        display: inline-block;
    }
    .dot-BUILD { background: #22c55e; box-shadow: 0 0 6px #22c55e; }
    .dot-SKIP { background: #ef4444; }
    .dot-UNREVIEWED { background: #64748b; }
    
    .community-counter-pill {
        display: inline-block;
        padding: 3px 10px;
        border-radius: 20px;
        font-size: 0.72rem;
        font-weight: 600;
        background: rgba(99, 102, 241, 0.12);
        color: #c7d2fe;
        border: 1px solid rgba(99, 102, 241, 0.3);
        margin-right: 8px;
    }
    
    /* Idea Card Expanders */
    div[data-testid="stExpander"] {
        border: 1px solid #1f2937;
        border-radius: 12px;
        background-color: #111827;
        margin-bottom: 0.65rem;
        transition: border-color 0.2s ease, box-shadow 0.2s ease;
    }
    div[data-testid="stExpander"]:hover {
        border-color: #6366f1;
        box-shadow: 0 4px 16px rgba(99, 102, 241, 0.1);
    }
    
    /* Claude-style Artifact Header in Dialog */
    .claude-artifact-container {
        background: #0f172a;
        border: 1px solid #1e293b;
        border-radius: 12px;
        padding: 1.25rem;
        box-shadow: 0 8px 30px rgba(0,0,0,0.5);
        margin-bottom: 1rem;
    }
    .claude-tag {
        background: #1e293b;
        color: #f59e0b;
        padding: 2px 8px;
        border-radius: 4px;
        font-size: 0.75rem;
        font-weight: 700;
        font-family: monospace;
        letter-spacing: 0.5px;
        border: 1px solid #78350f;
    }

    /* Metrics Popup Modal Grid */
    .modal-metrics-grid {
        display: grid;
        grid-template-columns: repeat(2, 1fr);
        gap: 0.75rem;
        margin-bottom: 1rem;
    }

    /* Mobile-First Responsive Styles (<768px) - Desktop (>=769px) remains 100% untouched */
    @media (max-width: 768px) {
        .hero-header {
            padding: 0.85rem 1rem !important;
            border-radius: 12px !important;
            margin-bottom: 0.75rem !important;
        }
        .hero-title {
            font-size: 1.35rem !important;
            letter-spacing: -0.3px !important;
        }
        .hero-subtitle {
            font-size: 0.75rem !important;
            margin-top: 0.2rem !important;
        }
        .hero-header img {
            width: 40px !important;
            height: 40px !important;
        }
        .auth-card-box {
            padding: 0.65rem 0.85rem !important;
            margin-bottom: 0.5rem !important;
        }
        /* Hide bulky 400px metrics block from mobile feed (opened via Metrics button) */
        .metrics-feed-container {
            display: none !important;
        }
        /* Hide top pagination on mobile so ideas appear near top */
        .top-pagination-strip {
            display: none !important;
        }
        .filter-panel {
            padding: 0.75rem 0.85rem !important;
            margin-bottom: 0.75rem !important;
        }
        /* Mobile 2x2 Filter Grid */
        .filter-columns-wrapper div[data-testid="stHorizontalBlock"] {
            display: grid !important;
            grid-template-columns: repeat(2, 1fr) !important;
            gap: 0.5rem !important;
        }
        .filter-columns-wrapper div[data-testid="stHorizontalBlock"] > div {
            width: 100% !important;
            min-width: 0 !important;
        }
        div[data-testid="stExpander"] {
            margin-bottom: 0.5rem !important;
        }
        div[data-testid="stExpander"] summary {
            font-size: 0.88rem !important;
            padding: 0.65rem 0.85rem !important;
            word-break: break-word !important;
        }
    }

    @media (max-width: 480px) {
        .hero-title {
            font-size: 1.18rem !important;
        }
        .hero-subtitle {
            font-size: 0.68rem !important;
        }
        .hero-header img {
            width: 36px !important;
            height: 36px !important;
        }
        .hero-header {
            padding: 0.75rem 0.85rem !important;
        }
    }
</style>
""", unsafe_allow_html=True)

# ─── Helper: Generate Markdown Content ───────────────────────────────────────
def generate_markdown_content(row, source, scraped, user_decision=None, user_remark=None):
    decision_text = str(user_decision or row.get('user_decision') or row.get('decision') or 'UNREVIEWED')
    remark_text = str(user_remark if user_remark is not None else row.get('user_remark') or row.get('remark') or '')
    
    md = f"""# {row.get('idea_name', 'Product Idea')}

> **Status:** `{decision_text}` | **Company:** {row.get('company', 'Unknown')} | **Priority:** {row.get('priority', 'Zero-to-One')}

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

## 6. Feasibility & Opportunity Score
{row.get('mvp_score') or 'Feasibility evaluation not available.'}

---

## 7. Analysis & Build Decision
- **Build Decision:** `{decision_text}`
- **Founder Remarks:** {remark_text if remark_text else '_No remarks recorded yet._'}

---
*Source: {str(source).upper()} | Scraped: {scraped} | Job Link: {row.get('job_link', 'N/A')}*
"""
    return md

# ─── Native Modal Dialog for README.md ───────────────────────────────────────
@st.dialog("README Artifact", width="large")
def open_readme_dialog(row_dict):
    """Render full idea README.md artifact with tabs and diagrams inside a modal."""
    with st.spinner("Rendering artifact preview & diagrams..."):
        source = str(row_dict.get('source') or 'unknown').lower()
        scraped = str(row_dict.get('scraped_at') or '')
        if scraped and scraped.lower() not in ['none', 'nan', '']:
            try:
                scraped = datetime.fromisoformat(scraped.replace('Z', '+00:00')).strftime('%b %d, %Y')
            except Exception:
                scraped = scraped[:10]
        else:
            scraped = ''
            
        idea_name = row_dict.get('idea_name') or 'Product Idea'
        company = row_dict.get('company') or 'Unknown'
        safe_name = str(idea_name).replace(' ', '_').replace('/', '_')
        md_content = generate_markdown_content(row_dict, source, scraped)
        
        st.markdown(f"""
        <div class="claude-artifact-container">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.5rem;">
                <span class="claude-tag">ARTIFACT: README.MD</span>
                <span style="color: #94a3b8; font-size: 0.8rem;">Target: <strong>{company}</strong></span>
            </div>
            <h2 style="margin: 0; color: #f8fafc; font-size: 1.4rem; font-weight: 700;">{idea_name}</h2>
        </div>
        """, unsafe_allow_html=True)
        
        tab_preview, tab_raw, tab_mermaid = st.tabs(["Document Preview", "Raw Markdown", "System Architecture"])
        
        with tab_preview:
            st.markdown(md_content)
            
        with tab_raw:
            st.code(md_content, language="markdown")
            
        with tab_mermaid:
            mermaid_code = row_dict.get('mermaid_code', '')
            if mermaid_code and str(mermaid_code).lower() not in ['none', 'nan', '']:
                try:
                    st_mermaid.st_mermaid(mermaid_code)
                except Exception:
                    st.code(mermaid_code, language="text")
            else:
                st.info("No system architecture diagram available for this idea.")
                
        st.markdown("---")
        b1, b2, b3 = st.columns(3)
        with b1:
            st.download_button(
                "Download .md",
                icon=":material/download:",
                data=md_content,
                file_name=f"{safe_name}.md",
                mime="text/markdown",
                use_container_width=True,
                key=f"modal_dl_{row_dict.get('id')}"
            )
        with b2:
            if st.button("Save to builds/", icon=":material/save:", use_container_width=True, key=f"modal_save_{row_dict.get('id')}"):
                os.makedirs('builds', exist_ok=True)
                with open(f"builds/{safe_name}.md", 'w', encoding='utf-8') as f:
                    f.write(md_content)
                st.success(f"Saved `builds/{safe_name}.md`")
        with b3:
            job_link = str(row_dict.get('job_link', '')).strip()
            if job_link and (job_link.startswith('http://') or job_link.startswith('https://')):
                st.link_button("View Job Posting", job_link, icon=":material/open_in_new:", use_container_width=True)

# ─── Native Modal Dialog for Community Metrics ──────────────────────────────
@st.dialog("Community Metrics & Key Analytics", width="medium")
def render_metrics_dialog():
    """Render community analytics cards cleanly inside a popup modal."""
    m = get_community_metrics()
    st.markdown("""
    <div style="margin-bottom: 0.85rem;">
        <p style="color: #94a3b8; font-size: 0.85rem; margin: 0;">
            Platform-wide aggregated hiring signals and community review metrics.
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown(f"""
    <div class="modal-metrics-grid">
        <div class="metric-box metric-accent-ideas">
            <div class="metric-val">{m['total_ideas']:,}</div>
            <div class="metric-lbl">Total Ideas</div>
        </div>
        <div class="metric-box metric-accent-jobs">
            <div class="metric-val">{m['raw_count']:,}</div>
            <div class="metric-lbl">Jobs Scraped</div>
        </div>
        <div class="metric-box metric-accent-build">
            <div class="metric-val">{m['community_build']:,}</div>
            <div class="metric-lbl">Community To Build</div>
        </div>
        <div class="metric-box metric-accent-skip">
            <div class="metric-val">{m['community_skip']:,}</div>
            <div class="metric-lbl">Community Skipped</div>
        </div>
        <div class="metric-box metric-accent-unrev">
            <div class="metric-val">{m['community_unreviewed']:,}</div>
            <div class="metric-lbl">Pending Review</div>
        </div>
        <div class="metric-box metric-accent-users">
            <div class="metric-val">{m['total_reviewers']:,}</div>
            <div class="metric-lbl">Active Reviewers</div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    if st.button("Close", icon=":material/close:", use_container_width=True):
        st.session_state['show_metrics_dialog'] = False
        st.rerun()

# ─── Script Runner for Admin Command Center ─────────────────────────────────
def run_admin_script(cmd, label):
    """Execute scraping or analysis script and output to sidebar."""
    with st.spinner(f"Executing {label}..."):
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                cwd=_PROJECT_ROOT,
                timeout=300,
                encoding='utf-8',
                errors='replace'
            )
            if result.returncode == 0:
                st.sidebar.success(f"{label} completed successfully.")
                st.sidebar.code(result.stdout[-400:] if len(result.stdout) > 400 else result.stdout, language="text")
            else:
                st.sidebar.error(f"{label} failed.")
                st.sidebar.code(result.stderr[-400:] if len(result.stderr) > 400 else result.stderr, language="text")
        except subprocess.TimeoutExpired:
            st.sidebar.warning(f"{label} timed out (5 min limit).")
        except Exception as e:
            st.sidebar.error(f"Error: {e}")

# ─── Active User & Session State ─────────────────────────────────────────────
current_user = get_current_user()
admin_active = is_admin()

if 'current_page' not in st.session_state:
    st.session_state['current_page'] = 1
if 'show_auth_dialog' not in st.session_state:
    st.session_state['show_auth_dialog'] = False
if 'show_profile_dialog' not in st.session_state:
    st.session_state['show_profile_dialog'] = False
if 'show_metrics_dialog' not in st.session_state:
    st.session_state['show_metrics_dialog'] = False

# Render modals if active
if st.session_state.get('show_auth_dialog'):
    render_auth_dialog()
if st.session_state.get('show_profile_dialog'):
    render_profile_dialog()
if st.session_state.get('show_metrics_dialog'):
    render_metrics_dialog()

# ─── Top Header & Auth Widget ────────────────────────────────────────────────
col_hero, col_auth = st.columns([7, 3])

logo_b64 = get_base64_logo()
logo_img_tag = f'<img src="data:image/png;base64,{logo_b64}" style="width: 52px; height: 52px; border-radius: 12px; box-shadow: 0 0 16px rgba(168, 85, 247, 0.4); object-fit: cover;" alt="Logo" />' if logo_b64 else ''

with col_hero:
    st.markdown(f"""
    <div class="hero-header">
        <div style="display: flex; align-items: center; gap: 16px;">
            {logo_img_tag}
            <div>
                <h1 class="hero-title">Product Idea Factory</h1>
                <p class="hero-subtitle">Startup Hiring Intelligence • AI Opportunity Engine • Community Reviews</p>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

with col_auth:
    if current_user:
        role_label = "ADMIN" if admin_active else "REVIEWER"
        role_bg = "rgba(147, 51, 234, 0.2)" if admin_active else "rgba(2, 132, 199, 0.2)"
        role_color = "#c084fc" if admin_active else "#38bdf8"
        role_border = "#a855f7" if admin_active else "#0284c7"
        
        st.markdown(f"""
        <div class="auth-card-box" style="background: #111827; border: 1px solid #1f2937; border-radius: 12px; padding: 0.85rem 1rem; margin-bottom: 0.5rem; text-align: right;">
            <div style="color: #f8fafc; font-weight: 700; font-size: 0.95rem;">{current_user.get('name', 'User')}</div>
            <div style="margin-top: 4px;">
                <span style="background: {role_bg}; color: {role_color}; border: 1px solid {role_border}; padding: 1px 8px; border-radius: 12px; font-size: 0.72rem; font-weight: 700; letter-spacing: 0.5px;">{role_label}</span>
                <span style="color: #94a3b8; font-size: 0.78rem; margin-left: 6px;">{current_user.get('email')}</span>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        btn_c1, btn_c2, btn_c3 = st.columns([1, 1, 1])
        with btn_c1:
            if st.button("Profile", icon=":material/account_circle:", use_container_width=True):
                st.session_state['show_profile_dialog'] = True
                st.rerun()
        with btn_c2:
            if st.button("Metrics", icon=":material/bar_chart:", use_container_width=True):
                st.session_state['show_metrics_dialog'] = True
                st.rerun()
        with btn_c3:
            if st.button("Sign Out", icon=":material/logout:", use_container_width=True):
                logout_user()
    else:
        st.markdown("""
        <div class="auth-card-box" style="background: #111827; border: 1px solid #1f2937; border-radius: 12px; padding: 0.85rem 1rem; margin-bottom: 0.5rem; text-align: right;">
            <div style="color: #94a3b8; font-size: 0.82rem;">Browsing as <strong>Guest</strong></div>
            <div style="color: #64748b; font-size: 0.75rem;">Sign in with OTP to save build decisions</div>
        </div>
        """, unsafe_allow_html=True)
        g_c1, g_c2 = st.columns([3, 2])
        with g_c1:
            if st.button("Sign In / Sign Up", icon=":material/login:", use_container_width=True, type="primary"):
                st.session_state['show_auth_dialog'] = True
                st.rerun()
        with g_c2:
            if st.button("Metrics", icon=":material/bar_chart:", use_container_width=True):
                st.session_state['show_metrics_dialog'] = True
                st.rerun()

# ─── Top Community Metrics (SaaS KPI Style, No Emojis) ───────────────────────
metrics = get_community_metrics()

st.markdown(f"""
<div class="metrics-feed-container">
    <div class="metrics-container">
        <div class="metric-box metric-accent-ideas">
            <div class="metric-val">{metrics['total_ideas']:,}</div>
            <div class="metric-lbl">Total Ideas</div>
        </div>
        <div class="metric-box metric-accent-jobs">
            <div class="metric-val">{metrics['raw_count']:,}</div>
            <div class="metric-lbl">Jobs Scraped</div>
        </div>
        <div class="metric-box metric-accent-build">
            <div class="metric-val">{metrics['community_build']:,}</div>
            <div class="metric-lbl">Community To Build</div>
        </div>
        <div class="metric-box metric-accent-skip">
            <div class="metric-val">{metrics['community_skip']:,}</div>
            <div class="metric-lbl">Community Skipped</div>
        </div>
        <div class="metric-box metric-accent-unrev">
            <div class="metric-val">{metrics['community_unreviewed']:,}</div>
            <div class="metric-lbl">Pending Review</div>
        </div>
        <div class="metric-box metric-accent-users">
            <div class="metric-val">{metrics['total_reviewers']:,}</div>
            <div class="metric-lbl">Active Reviewers</div>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

# ─── Top Search & Filter Bar ─────────────────────────────────────────────────
priorities_avail, sources_avail = get_distinct_filter_values()

with st.container():
    st.markdown('<div class="filter-panel">', unsafe_allow_html=True)
    
    # Row 1: Search Input
    search_query = st.text_input(
        "Search Query",
        value="",
        placeholder="Search 850+ ideas by company name, job role, problem statement, recommended stack, or remarks...",
        label_visibility="collapsed",
        key="top_search_bar"
    )
    
    # Row 2: Filters & Sorting (Clean labels, no raw emojis - Responsive 2x2 on mobile)
    st.markdown('<div class="filter-columns-wrapper">', unsafe_allow_html=True)
    f_col1, f_col2, f_col3, f_col4 = st.columns([3, 2, 3, 2])
    
    with f_col1:
        sort_options = {
            "Most Reviewed First": "most_reviewed",
            "Newest First": "newest",
            "Highest Feasibility Score": "highest_mvp",
            "Company Name (A-Z)": "company"
        }
        chosen_sort_label = st.selectbox("Sort By", list(sort_options.keys()), index=0)
        chosen_sort = sort_options[chosen_sort_label]
        
    with f_col2:
        decision_options = {
            "All Decisions": "ALL",
            "To Build": "BUILD",
            "Skipped": "SKIP",
            "Unreviewed": "UNREVIEWED"
        }
        chosen_dec_label = st.selectbox("Decision Status", list(decision_options.keys()), index=0)
        chosen_dec = decision_options[chosen_dec_label]
        
    with f_col3:
        source_options = sources_avail if sources_avail else ["yc", "linkedin", "wellfound", "yc_rfs"]
        chosen_sources = st.multiselect("Source Platforms", source_options, default=source_options)
        
    with f_col4:
        prio_options = priorities_avail if priorities_avail else ["Zero-to-One", "Scale"]
        chosen_prio = st.multiselect("Priority", prio_options, default=prio_options)
        
    st.markdown('</div></div>', unsafe_allow_html=True)

# ─── Fetch Ideas with Pagination ─────────────────────────────────────────────
PAGE_SIZE = 25
user_id_param = current_user['id'] if current_user else None

with st.spinner("Loading ideas from database..."):
    df_page, total_matches = get_paginated_ideas(
        page=st.session_state['current_page'],
        page_size=PAGE_SIZE,
        search_term=search_query,
        decision_filter=chosen_dec,
        source_filter=chosen_sources,
        priority_filter=chosen_prio,
        sort_by=chosen_sort,
        current_user_id=user_id_param
    )

total_pages = max(1, (total_matches + PAGE_SIZE - 1) // PAGE_SIZE)
if st.session_state['current_page'] > total_pages:
    st.session_state['current_page'] = 1

# ─── Pagination Controls (Top - Visible on Desktop, Hidden on Mobile) ────────
st.markdown('<div class="top-pagination-strip">', unsafe_allow_html=True)
p_col1, p_col2, p_col3, p_col4 = st.columns([4, 2, 2, 2])

with p_col1:
    start_num = min(total_matches, (st.session_state['current_page'] - 1) * PAGE_SIZE + 1) if total_matches > 0 else 0
    end_num = min(total_matches, st.session_state['current_page'] * PAGE_SIZE)
    st.markdown(f"#### Showing **{start_num}–{end_num}** of **{total_matches}** Ideas (Page **{st.session_state['current_page']}** of **{total_pages}**)")

with p_col2:
    if st.button("Previous Page", icon=":material/chevron_left:", disabled=(st.session_state['current_page'] <= 1), use_container_width=True):
        st.session_state['current_page'] -= 1
        st.rerun()

with p_col3:
    if st.button("Next Page", icon=":material/chevron_right:", disabled=(st.session_state['current_page'] >= total_pages), use_container_width=True):
        st.session_state['current_page'] += 1
        st.rerun()

with p_col4:
    if not df_page.empty:
        csv_bytes = df_page.to_csv(index=False).encode('utf-8')
        st.download_button(
            "Export Page CSV",
            icon=":material/download:",
            data=csv_bytes,
            file_name=f"ideas_page_{st.session_state['current_page']}.csv",
            mime="text/csv",
            use_container_width=True
        )
st.markdown('</div>', unsafe_allow_html=True)

# ─── Render Ideas List ───────────────────────────────────────────────────────
if df_page.empty:
    st.warning("No ideas match your current search and filters. Try adjusting your query or resetting filters.")
else:
    for _, row in df_page.iterrows():
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
            
        tot_revs = int(row.get('total_reviews') or 0)
        c_build = int(row.get('community_build') or 0)
        c_skip = int(row.get('community_skip') or 0)
        
        user_dec = str(row.get('user_decision') or 'UNREVIEWED').strip().upper()
        if user_dec not in ['BUILD', 'SKIP', 'UNREVIEWED']:
            user_dec = 'UNREVIEWED'
        user_rem = str(row.get('user_remark') or '').strip()
        
        # Clean HTML Badges (No raw emojis)
        source_html = f'<span class="source-badge {badge_class}">{source.upper()}</span>'
        community_pill_html = f'<span class="community-counter-pill">{tot_revs} reviews ({c_build} build, {c_skip} skip)</span>'
        
        dec_label_map = {"BUILD": "To Build", "SKIP": "Skipped", "UNREVIEWED": "Unreviewed"}
        user_dec_html = f'<span class="status-pill status-{user_dec}"><span class="status-dot dot-{user_dec}"></span>{dec_label_map.get(user_dec, user_dec)}</span>' if current_user else ''
        
        expander_title = f"{row.get('idea_name', 'Untitled')} — {row.get('company', '')} | {tot_revs} reviews"
        
        with st.expander(expander_title, expanded=False):
            st.markdown(f"{source_html} {community_pill_html} {user_dec_html} <span style='color: #94a3b8; font-size: 0.8rem;'>{row.get('priority', '')}</span>", unsafe_allow_html=True)
            st.markdown("---")
            
            # ─── Review & Remarks Section ───────────────────────────────
            st.markdown("##### Build Decision & Remarks")
            if current_user:
                r_col1, r_col2 = st.columns([3, 5])
                
                dec_labels = ["Unreviewed", "Build", "Skip"]
                dec_map = {"Unreviewed": "UNREVIEWED", "Build": "BUILD", "Skip": "SKIP"}
                rev_map = {"UNREVIEWED": "Unreviewed", "BUILD": "Build", "SKIP": "Skip"}
                
                curr_idx = dec_labels.index(rev_map.get(user_dec, "Unreviewed"))
                
                with r_col1:
                    chosen_lbl = st.radio(
                        "Decision",
                        dec_labels,
                        index=curr_idx,
                        key=f"user_dec_{row_id}",
                        horizontal=True,
                        label_visibility="collapsed"
                    )
                    chosen_decision = dec_map[chosen_lbl]
                    
                with r_col2:
                    remark_input = st.text_input(
                        "Remark",
                        value=user_rem,
                        key=f"user_rem_{row_id}",
                        placeholder="Add build notes, evaluation reasons, or stack remarks...",
                        label_visibility="collapsed"
                    )
                    
                if chosen_decision != user_dec or remark_input != user_rem:
                    save_user_review(current_user['id'], row_id, chosen_decision, remark_input)
                    st.toast(f"Saved review for {row.get('idea_name')}: {chosen_decision}")
                    st.rerun()
            else:
                g_col1, g_col2 = st.columns([4, 6])
                with g_col1:
                    st.caption("Personal reviewing disabled in Guest mode.")
                with g_col2:
                    if st.button(f"Sign in with OTP to review idea #{row_id}", icon=":material/login:", key=f"guest_rev_btn_{row_id}"):
                        st.session_state['show_auth_dialog'] = True
                        st.rerun()
                        
            st.markdown("---")
            
            # ─── Idea Opportunity Details ───────────────────────────────
            st.markdown(f"**Problem Solved:** {row.get('problem', 'N/A')}")
            st.markdown(f"**Hiring Role:** {row.get('role', 'N/A')}")
            
            mvp = row.get('mvp_score')
            if mvp and str(mvp).lower() not in ['none', 'nan', '']:
                st.markdown(f"**Feasibility Score:** `{mvp}`")
                
            st.markdown("**Suggested Stack:**")
            st.code(row.get('stack', 'N/A'), language="text")
            
            # ─── Action Buttons (Clean Material Symbols) ────────────────
            act1, act2, act3 = st.columns([3, 3, 4])
            with act1:
                row_dict = dict(row)
                if st.button("View README", icon=":material/description:", key=f"btn_modal_{row_id}", use_container_width=True):
                    open_readme_dialog(row_dict)
                    
            with act2:
                safe_name = str(row.get('idea_name') or 'idea').replace(' ', '_').replace('/', '_')
                md_bytes = generate_markdown_content(row, source, scraped, user_dec, user_rem)
                st.download_button(
                    "Download .md",
                    icon=":material/download:",
                    data=md_bytes,
                    file_name=f"{safe_name}.md",
                    mime="text/markdown",
                    key=f"dl_card_{row_id}",
                    use_container_width=True
                )
            with act3:
                job_link = str(row.get('job_link', '')).strip()
                if job_link and (job_link.startswith('http://') or job_link.startswith('https://')):
                    st.link_button("Job Posting", job_link, icon=":material/open_in_new:", use_container_width=True)

# ─── Bottom Pagination Strip ─────────────────────────────────────────────────
if total_pages > 1:
    st.markdown("---")
    b_col1, b_col2, b_col3 = st.columns([3, 4, 3])
    with b_col1:
        if st.button("First Page", icon=":material/first_page:", disabled=(st.session_state['current_page'] <= 1), use_container_width=True, key="bottom_first"):
            st.session_state['current_page'] = 1
            st.rerun()
    with b_col2:
        st.markdown(f"<div style='text-align: center; color: #94a3b8; padding-top: 6px; font-size: 0.9rem;'>Page <strong>{st.session_state['current_page']}</strong> of <strong>{total_pages}</strong></div>", unsafe_allow_html=True)
    with b_col3:
        if st.button("Last Page", icon=":material/last_page:", disabled=(st.session_state['current_page'] >= total_pages), use_container_width=True, key="bottom_last"):
            st.session_state['current_page'] = total_pages
            st.rerun()

# ─── Admin-Only Command Center (Sidebar) ─────────────────────────────────────
if admin_active:
    st.sidebar.markdown("## Admin Command Center")
    st.sidebar.caption(f"Authenticated session: **{get_admin_email()}**")
    
    st.sidebar.markdown("---")
    st.sidebar.markdown("### Pipeline Automation")
    
    col_sc1, col_sc2 = st.sidebar.columns(2)
    with col_sc1:
        run_all_btn = st.sidebar.button("Run All Scrapers", icon=":material/play_circle:", use_container_width=True)
    with col_sc2:
        run_analyzer_btn = st.sidebar.button("Run Analyzer", icon=":material/psychology:", use_container_width=True)
        
    st.sidebar.markdown("### Platform Scrapers")
    s_col1, s_col2 = st.sidebar.columns(2)
    with s_col1:
        run_yc = st.button("YC Jobs", icon=":material/work:", use_container_width=True)
        run_wellfound = st.button("Wellfound", icon=":material/rocket_launch:", use_container_width=True)
    with s_col2:
        run_linkedin = st.button("LinkedIn", icon=":material/business:", use_container_width=True)
        run_rfs = st.button("YC RFS", icon=":material/lightbulb:", use_container_width=True)
        
    if run_yc:
        run_admin_script(["node", "scrapers/yc_scraper.js"], "YC Scraper")
    if run_linkedin:
        run_admin_script(["node", "scrapers/linkedin_scraper.js"], "LinkedIn Scraper")
    if run_wellfound:
        run_admin_script(["node", "scrapers/wellfound_scraper.js"], "Wellfound Scraper")
    if run_rfs:
        run_admin_script(["node", "scrapers/yc_rfs_scraper.js"], "YC RFS Scraper")
    if run_all_btn:
        for cmd, label in [
            (["node", "scrapers/yc_scraper.js"], "YC"),
            (["node", "scrapers/linkedin_scraper.js"], "LinkedIn"),
            (["node", "scrapers/wellfound_scraper.js"], "Wellfound"),
            (["node", "scrapers/yc_rfs_scraper.js"], "YC RFS"),
        ]:
            run_admin_script(cmd, label)
    if run_analyzer_btn:
        run_admin_script(["python", "engine/analyzer.py"], "Analyzer")
        
    st.sidebar.markdown("---")
    if st.sidebar.button("Clear Research Cache", icon=":material/delete_outline:", use_container_width=True):
        conn = get_db()
        conn.execute("DELETE FROM cache")
        conn.commit()
        st.sidebar.success("Research cache cleared.")
        
    # Cloud Pipeline Indicator
    has_auth_file = os.path.exists('data/auth_state.json')
    if has_auth_file:
        st.sidebar.caption("● Local Scraper Session: Authenticated")
    else:
        st.sidebar.caption("● Scraping Pipeline: Automated on GitHub Actions (Daily 5:30 AM IST)")
