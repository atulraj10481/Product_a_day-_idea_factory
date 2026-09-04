import sqlite3
import os
import sys
import json
from datetime import datetime
import pandas as pd

_CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
_PROJECT_ROOT = os.path.dirname(_CURRENT_DIR)
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)
if _CURRENT_DIR not in sys.path:
    sys.path.insert(0, _CURRENT_DIR)

DB_PATH = os.path.join(_PROJECT_ROOT, 'data', 'factory.db')
DEFAULT_ADMIN_EMAIL = 'warrioratul7146@gmail.com'

def get_admin_emails():
    """Retrieve list of designated Admin emails from environment or secrets."""
    admin_str = os.getenv("ADMIN_EMAIL", DEFAULT_ADMIN_EMAIL).strip().lower()
    emails = [e.strip().lower() for e in admin_str.replace(';', ',').split(',') if e.strip()]
    if DEFAULT_ADMIN_EMAIL not in emails:
        emails.append(DEFAULT_ADMIN_EMAIL)
    if "rajatul.official@gmail.com" not in emails:
        emails.append("rajatul.official@gmail.com")
    return emails

def is_admin_email(email):
    """Check if email matches any designated admin email."""
    if not email:
        return False
    return email.strip().lower() in get_admin_emails()

def get_admin_email():
    """Retrieve primary Admin email for display."""
    return get_admin_emails()[0]

def get_db():
    """Return a thread-safe sqlite3 connection and ensure all tables exist."""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    init_schema(conn)
    return conn

def init_schema(conn):
    """Ensure database schema is up to date with multi-user auth and reviews."""
    cur = conn.cursor()
    
    # Core research cache table
    cur.execute("""
    CREATE TABLE IF NOT EXISTS cache (
        company TEXT PRIMARY KEY,
        context TEXT
    )
    """)
    
    # Ideas table
    cur.execute("""
    CREATE TABLE IF NOT EXISTS ideas (
        id INTEGER PRIMARY KEY,
        company TEXT,
        role TEXT,
        idea_name TEXT,
        problem TEXT,
        mermaid_code TEXT,
        stack TEXT,
        priority TEXT,
        company_profile TEXT,
        job_summary TEXT,
        mvp_score TEXT,
        source TEXT,
        scraped_at TEXT,
        job_link TEXT,
        job_description TEXT,
        decision TEXT DEFAULT 'UNREVIEWED',
        remark TEXT DEFAULT ''
    )
    """)
    
    # Users table
    cur.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        email TEXT UNIQUE NOT NULL,
        name TEXT NOT NULL,
        role TEXT DEFAULT 'user',
        created_at TEXT NOT NULL
    )
    """)
    
    # OTPs table
    cur.execute("""
    CREATE TABLE IF NOT EXISTS otps (
        email TEXT PRIMARY KEY,
        otp_code TEXT NOT NULL,
        created_at TEXT NOT NULL,
        attempts INTEGER DEFAULT 0
    )
    """)
    
    # Multi-user reviews table
    cur.execute("""
    CREATE TABLE IF NOT EXISTS user_reviews (
        user_id INTEGER NOT NULL,
        idea_id INTEGER NOT NULL,
        decision TEXT DEFAULT 'UNREVIEWED',
        remark TEXT DEFAULT '',
        updated_at TEXT NOT NULL,
        PRIMARY KEY(user_id, idea_id),
        FOREIGN KEY(user_id) REFERENCES users(id),
        FOREIGN KEY(idea_id) REFERENCES ideas(id)
    )
    """)
    
    # OTP Audit Log for rate limiting & security limits
    cur.execute("""
    CREATE TABLE IF NOT EXISTS otp_audit_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        email TEXT NOT NULL,
        created_at TEXT NOT NULL
    )
    """)
    
    # Check if admin user already exists; if not, seed admin placeholder
    admin_email = get_admin_email()
    cur.execute("SELECT id FROM users WHERE LOWER(email) = ?", (admin_email,))
    admin_row = cur.fetchone()
    if not admin_row:
        cur.execute(
            "INSERT INTO users (email, name, role, created_at) VALUES (?, ?, 'admin', ?)",
            (admin_email, "Admin (Founder)", datetime.utcnow().isoformat())
        )
    
    # Migrate any existing non-empty reviews from ideas to admin's reviews
    cur.execute("SELECT COUNT(*) FROM user_reviews")
    review_count = cur.fetchone()[0]
    if review_count == 0:
        cur.execute("SELECT id FROM users WHERE LOWER(email) = ?", (admin_email,))
        admin_user = cur.fetchone()
        if admin_user:
            admin_id = admin_user[0]
            cur.execute("""
            INSERT OR IGNORE INTO user_reviews (user_id, idea_id, decision, remark, updated_at)
            SELECT ?, id, decision, remark, datetime('now')
            FROM ideas
            WHERE (decision != 'UNREVIEWED' AND decision != '' AND decision IS NOT NULL)
               OR (remark != '' AND remark IS NOT NULL)
            """, (admin_id,))

    conn.commit()

# ─── Auth & User Helpers ─────────────────────────────────────────────────────

def get_or_create_user(email, name=None):
    """Fetch user by email or create new user. Grants admin role if matches ADMIN_EMAIL."""
    email_clean = email.strip().lower()
    if not name:
        name = email_clean.split('@')[0].capitalize()
    
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT id, email, name, role, created_at FROM users WHERE LOWER(email) = ?", (email_clean,))
    row = cur.fetchone()
    
    is_admin = is_admin_email(email_clean)
    expected_role = 'admin' if is_admin else 'user'
    
    if row:
        user = dict(row)
        # Update role if matches admin
        if user['role'] != expected_role:
            cur.execute("UPDATE users SET role = ? WHERE id = ?", (expected_role, user['id']))
            conn.commit()
            user['role'] = expected_role
        return user
    
    now = datetime.utcnow().isoformat()
    cur.execute(
        "INSERT INTO users (email, name, role, created_at) VALUES (?, ?, ?, ?)",
        (email_clean, name, expected_role, now)
    )
    conn.commit()
    user_id = cur.lastrowid
    return {
        'id': user_id,
        'email': email_clean,
        'name': name,
        'role': expected_role,
        'created_at': now
    }

def check_otp_rate_limits(email):
    """
    Enforce security limits:
    1. Cooldown: 60 seconds between requests for same email.
    2. Burst limit: Max 5 requests per hour for same email.
    3. Global daily cap: Max 280 emails per 24h across system (safely under Brevo 300/day limit).
    """
    conn = get_db()
    cur = conn.cursor()
    email_clean = email.strip().lower()
    
    # 1. Cooldown check (last requested)
    cur.execute("""
        SELECT created_at FROM otp_audit_log 
        WHERE email = ? 
        ORDER BY id DESC LIMIT 1
    """, (email_clean,))
    last_row = cur.fetchone()
    if last_row:
        try:
            last_dt = datetime.fromisoformat(last_row[0])
            elapsed = (datetime.utcnow() - last_dt).total_seconds()
            if elapsed < 60:
                remaining = int(60 - elapsed)
                return False, f"⏳ Cooldown active. Please wait {remaining}s before requesting another code."
        except Exception:
            pass
            
    # 2. Hourly burst limit (max 5/hour per email)
    cur.execute("""
        SELECT COUNT(*) FROM otp_audit_log
        WHERE email = ? AND datetime(created_at) >= datetime('now', '-1 hour')
    """, (email_clean,))
    hourly_count = cur.fetchone()[0] or 0
    if hourly_count >= 5:
        return False, "⚠️ Hourly limit reached for this email (max 5 codes/hour). Please try again later."
        
    # 3. Global daily cap (max 280/24h)
    cur.execute("""
        SELECT COUNT(*) FROM otp_audit_log
        WHERE datetime(created_at) >= datetime('now', '-24 hours')
    """)
    daily_count = cur.fetchone()[0] or 0
    if daily_count >= 280:
        return False, "⚠️ Daily verification limit reached (280/day). Please try again tomorrow."
        
    return True, None

def record_otp_audit(email):
    """Record an OTP request in audit log for rate limiting."""
    conn = get_db()
    email_clean = email.strip().lower()
    now = datetime.utcnow().isoformat()
    conn.execute("INSERT INTO otp_audit_log (email, created_at) VALUES (?, ?)", (email_clean, now))
    conn.commit()

def store_otp(email, code):
    """Store 6-digit OTP for email with current UTC timestamp."""
    conn = get_db()
    email_clean = email.strip().lower()
    now = datetime.utcnow().isoformat()
    conn.execute(
        "INSERT OR REPLACE INTO otps (email, otp_code, created_at, attempts) VALUES (?, ?, ?, 0)",
        (email_clean, str(code).strip(), now)
    )
    conn.commit()

def verify_otp(email, code):
    """
    Verify OTP for email. Returns (True, None) on success.
    Returns (False, error_message) on failure.
    Valid within 10 minutes (600 seconds).
    """
    conn = get_db()
    email_clean = email.strip().lower()
    cur = conn.cursor()
    cur.execute("SELECT otp_code, created_at, attempts FROM otps WHERE email = ?", (email_clean,))
    row = cur.fetchone()
    
    if not row:
        return False, "No OTP requested for this email. Please request a new code."
    
    stored_code = row['otp_code']
    created_at_str = row['created_at']
    attempts = row['attempts']
    
    if attempts >= 5:
        conn.execute("DELETE FROM otps WHERE email = ?", (email_clean,))
        conn.commit()
        return False, "Too many failed attempts. Please request a new verification code."
    
    # Check expiry (10 minutes)
    try:
        created_at = datetime.fromisoformat(created_at_str)
        elapsed_seconds = (datetime.utcnow() - created_at).total_seconds()
        if elapsed_seconds > 600:
            conn.execute("DELETE FROM otps WHERE email = ?", (email_clean,))
            conn.commit()
            return False, "Verification code has expired. Please request a new one."
    except Exception:
        pass
    
    if stored_code == str(code).strip():
        # Valid: delete used OTP
        conn.execute("DELETE FROM otps WHERE email = ?", (email_clean,))
        conn.commit()
        return True, None
    else:
        conn.execute("UPDATE otps SET attempts = attempts + 1 WHERE email = ?", (email_clean,))
        conn.commit()
        return False, "Invalid verification code. Please check your inbox and try again."

# ─── Metrics & Community Stats ───────────────────────────────────────────────

def get_raw_jobs_count():
    """Count number of items in data/raw_jobs.json."""
    if os.path.exists('data/raw_jobs.json'):
        try:
            with open('data/raw_jobs.json', 'r', encoding='utf-8') as f:
                data = json.load(f)
                return len(data) if isinstance(data, list) else 0
        except Exception:
            return 0
    return 0

def get_community_metrics():
    """Calculate community-wide aggregated stats from ideas and user_reviews."""
    conn = get_db()
    cur = conn.cursor()
    
    # Total ideas
    cur.execute("SELECT COUNT(*) FROM ideas")
    total_ideas = cur.fetchone()[0] or 0
    
    # Jobs scraped
    raw_count = get_raw_jobs_count()
    
    # Aggregate community decisions across distinct ideas
    cur.execute("""
        SELECT 
            COUNT(DISTINCT CASE WHEN decision = 'BUILD' THEN idea_id END) AS community_build,
            COUNT(DISTINCT CASE WHEN decision = 'SKIP' THEN idea_id END) AS community_skip,
            COUNT(DISTINCT user_id) AS total_reviewers,
            COUNT(*) AS total_reviews_submitted
        FROM user_reviews
        WHERE decision IN ('BUILD', 'SKIP') OR (remark != '' AND remark IS NOT NULL)
    """)
    row = cur.fetchone()
    
    community_build = row['community_build'] or 0
    community_skip = row['community_skip'] or 0
    total_reviewers = row['total_reviewers'] or 0
    total_reviews_submitted = row['total_reviews_submitted'] or 0
    
    # Unreviewed count: ideas that haven't received any community BUILD or SKIP
    cur.execute("""
        SELECT COUNT(*) FROM ideas 
        WHERE id NOT IN (
            SELECT DISTINCT idea_id FROM user_reviews WHERE decision IN ('BUILD', 'SKIP')
        )
    """)
    community_unreviewed = cur.fetchone()[0] or 0
    
    return {
        'total_ideas': total_ideas,
        'raw_count': raw_count,
        'community_build': community_build,
        'community_skip': community_skip,
        'community_unreviewed': community_unreviewed,
        'total_reviewers': total_reviewers,
        'total_reviews_submitted': total_reviews_submitted
    }

def get_user_review_stats(user_id):
    """Return specific user's review counts."""
    if not user_id:
        return {'reviewed': 0, 'build': 0, 'skip': 0, 'unreviewed': 0}
    
    conn = get_db()
    cur = conn.cursor()
    
    cur.execute("SELECT COUNT(*) FROM ideas")
    total_ideas = cur.fetchone()[0] or 0
    
    cur.execute("""
        SELECT 
            COUNT(CASE WHEN decision = 'BUILD' THEN 1 END) AS count_build,
            COUNT(CASE WHEN decision = 'SKIP' THEN 1 END) AS count_skip,
            COUNT(CASE WHEN decision IN ('BUILD', 'SKIP') OR (remark != '' AND remark IS NOT NULL) THEN 1 END) AS count_reviewed
        FROM user_reviews
        WHERE user_id = ?
    """, (user_id,))
    row = cur.fetchone()
    
    build_c = row['count_build'] or 0
    skip_c = row['count_skip'] or 0
    reviewed_c = row['count_reviewed'] or 0
    unreviewed_c = max(0, total_ideas - (build_c + skip_c))
    
    return {
        'reviewed': reviewed_c,
        'build': build_c,
        'skip': skip_c,
        'unreviewed': unreviewed_c
    }

# ─── Review Persistence ───────────────────────────────────────────────────────

def save_user_review(user_id, idea_id, decision, remark):
    """Upsert user's review and sync to ideas table if admin."""
    conn = get_db()
    cur = conn.cursor()
    now = datetime.utcnow().isoformat()
    
    decision_clean = str(decision).strip().upper()
    if decision_clean not in ['BUILD', 'SKIP', 'UNREVIEWED']:
        decision_clean = 'UNREVIEWED'
    remark_clean = str(remark or '').strip()
    
    cur.execute("""
    INSERT INTO user_reviews (user_id, idea_id, decision, remark, updated_at)
    VALUES (?, ?, ?, ?, ?)
    ON CONFLICT(user_id, idea_id) DO UPDATE SET
        decision = excluded.decision,
        remark = excluded.remark,
        updated_at = excluded.updated_at
    """, (int(user_id), int(idea_id), decision_clean, remark_clean, now))
    
    # If user is admin, also sync to legacy ideas columns
    cur.execute("SELECT role FROM users WHERE id = ?", (int(user_id),))
    u_row = cur.fetchone()
    if u_row and u_row['role'] == 'admin':
        cur.execute("UPDATE ideas SET decision = ?, remark = ? WHERE id = ?", (decision_clean, remark_clean, int(idea_id)))
        
    conn.commit()

# ─── Query & Pagination ───────────────────────────────────────────────────────

def get_paginated_ideas(
    page=1,
    page_size=25,
    search_term="",
    decision_filter="ALL",
    source_filter=None,
    priority_filter=None,
    sort_by="newest",
    current_user_id=None
):
    """
    Query ideas with user-specific reviews, community aggregates, filters, sorting, and pagination.
    Returns: (dataframe, total_matching_records)
    """
    conn = get_db()
    
    base_query = """
    FROM ideas i
    LEFT JOIN user_reviews ur ON i.id = ur.idea_id AND ur.user_id = :user_id
    LEFT JOIN (
        SELECT 
            idea_id,
            COUNT(user_id) AS total_reviews,
            SUM(CASE WHEN decision = 'BUILD' THEN 1 ELSE 0 END) AS community_build,
            SUM(CASE WHEN decision = 'SKIP' THEN 1 ELSE 0 END) AS community_skip
        FROM user_reviews
        WHERE decision IN ('BUILD', 'SKIP') OR (remark != '' AND remark IS NOT NULL)
        GROUP BY idea_id
    ) agg ON i.id = agg.idea_id
    WHERE 1=1
    """
    
    params = {'user_id': current_user_id if current_user_id else -1}
    where_clauses = []
    
    # 1. Search term filter
    if search_term and search_term.strip():
        term = f"%{search_term.strip().lower()}%"
        params['term'] = term
        where_clauses.append("""
            (LOWER(i.company) LIKE :term 
             OR LOWER(i.idea_name) LIKE :term 
             OR LOWER(i.problem) LIKE :term 
             OR LOWER(i.role) LIKE :term 
             OR LOWER(i.stack) LIKE :term 
             OR LOWER(i.job_summary) LIKE :term
             OR LOWER(COALESCE(ur.remark, '')) LIKE :term)
        """)
    
    # 2. Source Platform filter
    if source_filter and len(source_filter) > 0:
        placeholders = []
        for idx, src in enumerate(source_filter):
            p_key = f"src_{idx}"
            placeholders.append(f":{p_key}")
            params[p_key] = src.lower()
        where_clauses.append(f"LOWER(i.source) IN ({', '.join(placeholders)})")
        
    # 3. Priority filter
    if priority_filter and len(priority_filter) > 0:
        placeholders = []
        for idx, prio in enumerate(priority_filter):
            p_key = f"prio_{idx}"
            placeholders.append(f":{p_key}")
            params[p_key] = prio
        where_clauses.append(f"i.priority IN ({', '.join(placeholders)})")
        
    # 4. Decision filter
    if decision_filter and decision_filter != "ALL":
        if current_user_id:
            # Filter by current logged-in user's review
            if decision_filter == "UNREVIEWED":
                where_clauses.append("(ur.decision IS NULL OR ur.decision = 'UNREVIEWED' OR ur.decision = '')")
            else:
                params['dec_filter'] = decision_filter
                where_clauses.append("ur.decision = :dec_filter")
        else:
            # Guest mode: filter by community consensus
            if decision_filter == "BUILD":
                where_clauses.append("COALESCE(agg.community_build, 0) > 0")
            elif decision_filter == "SKIP":
                where_clauses.append("COALESCE(agg.community_skip, 0) > 0")
            elif decision_filter == "UNREVIEWED":
                where_clauses.append("(agg.total_reviews IS NULL OR agg.total_reviews = 0)")

    if where_clauses:
        full_where = base_query + " AND " + " AND ".join(where_clauses)
    else:
        full_where = base_query
        
    # Count total matching
    count_sql = f"SELECT COUNT(*) {full_where}"
    cur = conn.cursor()
    cur.execute(count_sql, params)
    total_records = cur.fetchone()[0] or 0
    
    # Sorting
    if sort_by == "most_reviewed":
        order_clause = "ORDER BY COALESCE(agg.total_reviews, 0) DESC, COALESCE(agg.community_build, 0) DESC, i.id DESC"
    elif sort_by == "highest_mvp":
        order_clause = "ORDER BY CAST(SUBSTR(i.mvp_score, 1, INSTR(i.mvp_score, '/') - 1) AS REAL) DESC, i.id DESC"
    elif sort_by == "company":
        order_clause = "ORDER BY i.company COLLATE NOCASE ASC, i.id DESC"
    else: # newest
        order_clause = "ORDER BY i.id DESC"
        
    # Pagination
    offset = max(0, (page - 1) * page_size)
    params['limit'] = page_size
    params['offset'] = offset
    
    select_sql = f"""
    SELECT 
        i.id, i.company, i.role, i.idea_name, i.problem, i.mermaid_code,
        i.stack, i.priority, i.company_profile, i.job_summary, i.mvp_score,
        i.source, i.scraped_at, i.job_link, i.job_description,
        COALESCE(ur.decision, 'UNREVIEWED') AS user_decision,
        COALESCE(ur.remark, '') AS user_remark,
        COALESCE(agg.total_reviews, 0) AS total_reviews,
        COALESCE(agg.community_build, 0) AS community_build,
        COALESCE(agg.community_skip, 0) AS community_skip
    {full_where}
    {order_clause}
    LIMIT :limit OFFSET :offset
    """
    
    df = pd.read_sql_query(select_sql, conn, params=params)
    return df, total_records

def get_distinct_filter_values():
    """Retrieve unique priority and source options for filter dropdowns."""
    conn = get_db()
    cur = conn.cursor()
    
    cur.execute("SELECT DISTINCT priority FROM ideas WHERE priority IS NOT NULL AND priority != ''")
    priorities = [r[0] for r in cur.fetchall()]
    
    cur.execute("SELECT DISTINCT source FROM ideas WHERE source IS NOT NULL AND source != ''")
    sources = [r[0] for r in cur.fetchall()]
    
    return priorities, sources
