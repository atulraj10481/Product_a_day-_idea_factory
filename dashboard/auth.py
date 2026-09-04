import os
import secrets
import requests
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv
import streamlit as st
from datetime import datetime

load_dotenv(override=True)

from dashboard.db import (
    store_otp,
    verify_otp,
    check_otp_rate_limits,
    record_otp_audit,
    get_or_create_user,
    get_user_review_stats,
    get_admin_email,
    is_admin_email
)

DEFAULT_FROM_EMAIL = "Product Idea Factory <onboarding@resend.dev>"

def generate_otp_code():
    """Generate a cryptographically secure 6-digit numeric OTP."""
    return f"{secrets.randbelow(900000) + 100000}"

def get_resend_api_key():
    """Retrieve Resend API Key from environment or Streamlit secrets."""
    key = os.getenv("RESEND_API_KEY", "").strip()
    if not key:
        try:
            if hasattr(st, "secrets") and "RESEND_API_KEY" in st.secrets:
                key = str(st.secrets["RESEND_API_KEY"]).strip()
        except Exception:
            pass
    return key

def get_from_email():
    """Retrieve sender email from environment or secrets."""
    sender = os.getenv("RESEND_FROM_EMAIL", "").strip()
    if not sender:
        try:
            if hasattr(st, "secrets") and "RESEND_FROM_EMAIL" in st.secrets:
                sender = str(st.secrets["RESEND_FROM_EMAIL"]).strip()
        except Exception:
            pass
    return sender if sender else DEFAULT_FROM_EMAIL

def send_via_smtp(to_email, otp_code):
    """SMTP dispatch (e.g. Brevo / Sendinblue or Gmail SMTP) if credentials exist in .env."""
    load_dotenv(override=True)
    smtp_host = os.getenv("SMTP_HOST", "smtp-relay.brevo.com").strip()
    smtp_user = os.getenv("SMTP_USER", "").strip()
    smtp_pass = os.getenv("SMTP_PASSWORD", "").strip()
    smtp_port = int(os.getenv("SMTP_PORT", "587"))
    from_email = os.getenv("SMTP_FROM_EMAIL", "").strip()
    if not from_email:
        from_email = f"Product Idea Factory <{smtp_user}>"
    
    if not (smtp_user and smtp_pass):
        return False, None
    
    try:
        msg = MIMEMultipart('alternative')
        msg['Subject'] = f"Your Product Idea Factory Verification Code: {otp_code}"
        msg['From'] = from_email
        msg['To'] = to_email
        
        text = f"Your login verification code is: {otp_code}\nValid for 10 minutes."
        html = f"""
        <div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #0f172a; color: #f8fafc; padding: 28px; border-radius: 12px; border: 1px solid #334155; max-width: 480px;">
            <h2 style="color: #a855f7; margin-top: 0; letter-spacing: -0.5px;">Product Idea Factory</h2>
            <p style="color: #cbd5e1; font-size: 15px;">Your 6-digit login verification code is:</p>
            <div style="background: #1e293b; border: 2px dashed #a855f7; border-radius: 8px; padding: 16px; font-size: 32px; font-weight: 800; letter-spacing: 8px; color: #38bdf8; text-align: center; font-family: monospace;">{otp_code}</div>
            <p style="color: #94a3b8; font-size: 13px; margin-bottom: 0; margin-top: 16px;">Valid for <strong>10 minutes</strong>. If you did not request this code, please ignore this email.</p>
        </div>
        """
        msg.attach(MIMEText(text, 'plain'))
        msg.attach(MIMEText(html, 'html'))
        
        server = smtplib.SMTP(smtp_host, smtp_port, timeout=12)
        server.starttls()
        server.login(smtp_user, smtp_pass)
        envelope_from = from_email.split("<")[-1].replace(">", "").strip() if "<" in from_email else smtp_user
        server.sendmail(envelope_from, [to_email], msg.as_string())
        server.quit()
        return True, f"Verification code sent to **{to_email}** via SMTP."
    except Exception as e:
        return False, str(e)

def send_otp_email(to_email, otp_code):
    """
    Dispatch OTP code via Resend API or SMTP.
    Provides sandbox detection and fallback test code display so local testing is never blocked.
    Returns: (success: bool, delivery_status: str, message: str)
    """
    to_email_clean = to_email.strip().lower()
    
    # 1. Try custom SMTP if configured
    smtp_ok, smtp_msg = send_via_smtp(to_email_clean, otp_code)
    if smtp_ok:
        return True, "delivered", smtp_msg
    
    # 2. Try Resend API
    api_key = get_resend_api_key()
    from_email = get_from_email()
    
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <style>
            body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background-color: #0f172a; color: #f8fafc; padding: 24px; }}
            .card {{ max-width: 480px; margin: 0 auto; background: #1e293b; border-radius: 12px; padding: 32px; border: 1px solid #334155; text-align: center; }}
            .title {{ font-size: 20px; font-weight: 700; color: #ffffff; margin-bottom: 12px; }}
            .desc {{ font-size: 14px; color: #94a3b8; line-height: 1.5; margin-bottom: 24px; }}
            .otp-box {{ background: #0f172a; border: 2px dashed #a855f7; border-radius: 8px; padding: 16px; font-size: 32px; font-weight: 800; letter-spacing: 8px; color: #38bdf8; margin-bottom: 24px; font-family: monospace; }}
            .footer {{ font-size: 12px; color: #64748b; margin-top: 24px; border-top: 1px solid #334155; padding-top: 16px; }}
        </style>
    </head>
    <body>
        <div class="card">
            <div class="title">Product Idea Factory</div>
            <p class="desc">Enter the 6-digit code below to access your account, review product ideas, and record founder remarks.</p>
            <div class="otp-box">{otp_code}</div>
            <p class="desc" style="margin-bottom: 0;">This code is valid for <strong>10 minutes</strong>.</p>
            <div class="footer">Product Idea Factory • Automated Intelligence Pipeline</div>
        </div>
    </body>
    </html>
    """

    if not api_key:
        return True, "dev_mode", f"Local Dev Mode: No Resend API key configured. Your code is: **{otp_code}**"

    try:
        response = requests.post(
            "https://api.resend.com/emails",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            },
            json={
                "from": from_email,
                "to": [to_email_clean],
                "subject": f"Your Product Idea Factory Verification Code: {otp_code}",
                "html": html_content
            },
            timeout=10
        )
        
        if response.status_code in [200, 201]:
            return True, "delivered", f"Verification code sent to **{to_email_clean}**! Please check your inbox."
        
        err_data = response.json() if response.content else {}
        err_msg = err_data.get('message', f"HTTP {response.status_code}")
        
        if response.status_code == 403 or "only send testing emails to your own email address" in err_msg:
            return True, "sandbox_restricted", err_msg
        else:
            return True, "api_error", f"Resend notice: {err_msg}"
            
    except Exception as e:
        return True, "network_error", f"Network error connecting to email provider: {str(e)}"

# ─── Current User Helpers ───────────────────────────────────────────────────

def get_current_user():
    """Retrieve logged-in user dict or None from session state."""
    return st.session_state.get('user', None)

def is_admin():
    """Check if current session belongs to a designated Admin."""
    user = get_current_user()
    if not user:
        return False
    return (
        user.get('role') == 'admin' or 
        is_admin_email(user.get('email', ''))
    )

def logout_user():
    """Clear user session and rerun."""
    if 'user' in st.session_state:
        del st.session_state['user']
    if 'otp_pending_email' in st.session_state:
        del st.session_state['otp_pending_email']
    if 'otp_code_display' in st.session_state:
        del st.session_state['otp_code_display']
    if 'show_auth_dialog' in st.session_state:
        st.session_state['show_auth_dialog'] = False
    st.toast("Signed out successfully.")
    st.rerun()

# ─── Streamlit Dialogs ───────────────────────────────────────────────────────

@st.dialog("Sign In / Sign Up", width="small")
def render_auth_dialog():
    """
    Native Streamlit modal dialog for passwordless email OTP authentication.
    Uses fragment reruns so the modal remains open across email input and OTP verification.
    """
    st.markdown("""
    <div style="text-align: center; margin-bottom: 1.25rem;">
        <h3 style="margin: 0; color: #f8fafc; font-size: 1.3rem; font-weight: 700;">Product Idea Factory</h3>
        <p style="color: #94a3b8; font-size: 0.88rem; margin-top: 4px;">
            Passwordless access • Enter your email for instant 6-digit code
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    pending_email = st.session_state.get('otp_pending_email')
    
    if not pending_email:
        # ─── STEP 1: Request Email ──────────────────────────────────────────
        email_input = st.text_input(
            "Email Address",
            placeholder="e.g. warrioratul7146@gmail.com",
            key="auth_email_input"
        )
        
        col_send, col_close = st.columns([3, 2])
        with col_send:
            if st.button("Send 6-Digit Code", icon=":material/send:", use_container_width=True, type="primary"):
                email_clean = email_input.strip().lower()
                if not email_clean or "@" not in email_clean or "." not in email_clean:
                    st.error("Please enter a valid email address.")
                    return
                
                # Enforce security rate limits (cooldown, burst limit, daily global limit)
                allowed, limit_err = check_otp_rate_limits(email_clean)
                if not allowed:
                    st.error(limit_err)
                    return
                
                with st.spinner("Dispatching verification code..."):
                    code = generate_otp_code()
                    record_otp_audit(email_clean)
                    store_otp(email_clean, code)
                    ok, status, msg = send_otp_email(email_clean, code)
                    
                    st.session_state['otp_pending_email'] = email_clean
                    st.session_state['otp_status'] = status
                    st.session_state['otp_msg'] = msg
                    st.session_state['otp_code_display'] = code
                    st.session_state['show_auth_dialog'] = True
                    st.rerun(scope="fragment")
        with col_close:
            if st.button("Cancel", icon=":material/close:", use_container_width=True):
                st.session_state['show_auth_dialog'] = False
                st.rerun(scope="app")
    else:
        # ─── STEP 2: Verify 6-Digit Code ────────────────────────────────────
        status = st.session_state.get('otp_status', '')
        disp_code = st.session_state.get('otp_code_display', '')
        
        if status == "delivered":
            st.success(f"We emailed a 6-digit code to **{pending_email}**.\nPlease check your inbox (and spam folder).")
        elif status == "sandbox_restricted":
            st.warning(
                f"Resend Sandbox Restriction: Testing domain (onboarding@resend.dev) delivers only to rajatul.official@gmail.com.\n\n"
                f"For testing with **{pending_email}**, use the code below:"
            )
            st.info(f"Verification Code: `{disp_code}`")
        else:
            st.info(f"Verification Code for {pending_email}: `{disp_code}`")
            
        # One-click auto-fill button for fast testing
        if disp_code:
            if st.button("Auto-fill code", icon=":material/content_paste:", use_container_width=True):
                st.session_state['auth_otp_input'] = disp_code
                st.rerun(scope="fragment")
                
        otp_input = st.text_input(
            "6-Digit Verification Code",
            max_chars=6,
            placeholder="123456",
            key="auth_otp_input"
        )
        
        col_v1, col_v2 = st.columns([3, 2])
        with col_v1:
            if st.button("Verify & Enter", icon=":material/check_circle:", use_container_width=True, type="primary"):
                if not otp_input or len(otp_input.strip()) != 6:
                    st.error("Please enter the complete 6-digit code.")
                    return
                
                valid, err = verify_otp(pending_email, otp_input.strip())
                if valid:
                    user = get_or_create_user(pending_email)
                    st.session_state['user'] = user
                    st.session_state['show_auth_dialog'] = False
                    
                    # Clean up temporary OTP states
                    if 'otp_pending_email' in st.session_state:
                        del st.session_state['otp_pending_email']
                    if 'otp_code_display' in st.session_state:
                        del st.session_state['otp_code_display']
                    if 'otp_status' in st.session_state:
                        del st.session_state['otp_status']
                        
                    role_title = "Admin" if user['role'] == 'admin' else "Reviewer"
                    st.toast(f"Welcome back, {user['name']} ({role_title})!")
                    st.rerun(scope="app")
                else:
                    st.error(err)
        with col_v2:
            if st.button("Change Email", icon=":material/sync:", use_container_width=True):
                if 'otp_pending_email' in st.session_state:
                    del st.session_state['otp_pending_email']
                if 'otp_code_display' in st.session_state:
                    del st.session_state['otp_code_display']
                st.rerun(scope="fragment")

@st.dialog("User Profile & Activity", width="small")
def render_profile_dialog():
    """Native Streamlit modal displaying user profile and personal review statistics."""
    user = get_current_user()
    if not user:
        st.warning("No active session found.")
        return
    
    is_user_admin = is_admin()
    role_badge = '<span style="background: rgba(147, 51, 234, 0.2); color: #c084fc; border: 1px solid #a855f7; padding: 2px 10px; border-radius: 20px; font-size: 0.75rem; font-weight: 700; letter-spacing: 0.5px;">ADMIN</span>' if is_user_admin else '<span style="background: rgba(2, 132, 199, 0.2); color: #38bdf8; border: 1px solid #0284c7; padding: 2px 10px; border-radius: 20px; font-size: 0.75rem; font-weight: 700; letter-spacing: 0.5px;">REVIEWER</span>'
    
    st.markdown(f"""
    <div style="background: #1e293b; border: 1px solid #334155; border-radius: 10px; padding: 1rem; margin-bottom: 1rem;">
        <div style="display: flex; justify-content: space-between; align-items: center;">
            <h3 style="margin: 0; color: #f8fafc; font-size: 1.2rem;">{user.get('name', 'User')}</h3>
            {role_badge}
        </div>
        <p style="color: #94a3b8; font-size: 0.85rem; margin: 4px 0 0 0;">{user.get('email')}</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Personal statistics
    stats = get_user_review_stats(user['id'])
    
    st.markdown("##### Your Review Activity")
    c1, c2, c3 = st.columns(3)
    with c1:
        st.metric("Reviewed", stats['reviewed'])
    with c2:
        st.metric("To Build", stats['build'])
    with c3:
        st.metric("Skipped", stats['skip'])
        
    st.markdown("---")
    if is_user_admin:
        st.caption("Administrator Session: Command Center controls in sidebar are active.")
    else:
        st.caption("Reviewer Session: You have full access to personal build decisions and idea remarks.")
        
    col_out, col_close = st.columns(2)
    with col_out:
        if st.button("Sign Out", icon=":material/logout:", use_container_width=True, type="secondary"):
            logout_user()
    with col_close:
        if st.button("Close", icon=":material/close:", use_container_width=True):
            if 'show_profile_dialog' in st.session_state:
                st.session_state['show_profile_dialog'] = False
            st.rerun(scope="app")
