# app.py
# RIFHound v2 — Streamlit Web Interface
# Run with: streamlit run app.py

import streamlit as st
import pandas as pd
import json
from datetime import datetime, timezone, timedelta
from rifhound_core import run_pipeline

# ─────────────────────────────────────────
# PAGE CONFIG
# ─────────────────────────────────────────
st.set_page_config(
    page_title="RIFHound — Recruiting Intelligence",
    page_icon="🐾",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─────────────────────────────────────────
# PERSISTENT STORAGE HELPERS
# ─────────────────────────────────────────

def load_saved_settings():
    if "settings_loaded" not in st.session_state:
        st.session_state.settings_loaded = True
        st.session_state.warn_key = ""
        st.session_state.tavily_key = ""
        st.session_state.csv_content = None
        st.session_state.csv_upload_date = None
        st.session_state.csv_filename = None
        try:
            if hasattr(st, "secrets"):
                st.session_state.warn_key = st.secrets.get("WARNFIREHOSE_KEY", "")
                st.session_state.tavily_key = st.secrets.get("TAVILY_KEY", "")
        except Exception:
            pass

def save_keys(warn_key, tavily_key):
    st.session_state.warn_key = warn_key
    st.session_state.tavily_key = tavily_key

def save_csv(content, filename):
    st.session_state.csv_content = content
    st.session_state.csv_upload_date = datetime.now(timezone.utc).isoformat()
    st.session_state.csv_filename = filename

def get_csv_age_days():
    if not st.session_state.get("csv_upload_date"):
        return -1
    try:
        uploaded = datetime.fromisoformat(st.session_state.csv_upload_date)
        return (datetime.now(timezone.utc) - uploaded).days
    except Exception:
        return -1

def clear_csv():
    st.session_state.csv_content = None
    st.session_state.csv_upload_date = None
    st.session_state.csv_filename = None

# ─────────────────────────────────────────
# STYLE FUNCTION
# ─────────────────────────────────────────

def style_app():
    """
    Applies the RIFHound "Recruiter Tech" design system.
    Dark mode primary palette:
        brand_color  = #2EA043  (Hunting Green)
        accent_color = #38BDF8  (Intelligence Blue)
        sidebar_bg   = #161B22
        main_bg      = #0E1117
        text_main    = #E6EDF3
    Typography: Inter (Google Fonts) for body, DM Mono for code/data.
    """
    brand_color  = "#2EA043"
    accent_color = "#38BDF8"
    sidebar_bg   = "#161B22"
    main_bg      = "#0E1117"
    text_main    = "#E6EDF3"

    st.markdown(f"""
    <style>
    /* ── FONTS ── */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=DM+Mono:wght@400;500&display=swap');

    /* ── BASE ── */
    html, body, [class*="css"] {{
        font-family: 'Inter', sans-serif;
        line-height: 1.6;
        color: {text_main};
        background-color: {main_bg};
    }}

    /* ── MAIN CANVAS ── */
    .main .block-container {{
        padding: 2rem 2.5rem 3rem;
        max-width: 1200px;
    }}

    /* ── SIDEBAR ── */
    [data-testid="stSidebar"] {{
        background: {sidebar_bg} !important;
        border-right: 1px solid #30363D !important;
    }}
    [data-testid="stSidebar"] .stMarkdown p,
    [data-testid="stSidebar"] label {{
        color: #8B949E !important;
        font-size: 0.85rem !important;
        line-height: 1.6 !important;
    }}
    [data-testid="stSidebar"] h3 {{
        color: {text_main} !important;
        font-size: 0.78rem !important;
        font-weight: 700 !important;
        text-transform: uppercase !important;
        letter-spacing: 1.4px !important;
        margin-bottom: 0.6rem !important;
    }}

    /* ── EXPANDER (API Keys section) ── */
    [data-testid="stExpander"] {{
        background: #161B22 !important;
        border: 1px solid #30363D !important;
        border-radius: 8px !important;
        margin-bottom: 0.6rem !important;
    }}
    [data-testid="stExpander"] summary {{
        font-weight: 600 !important;
        font-size: 0.85rem !important;
        color: {text_main} !important;
        padding: 0.7rem 1rem !important;
    }}
    [data-testid="stExpander"] summary:hover {{
        color: {accent_color} !important;
    }}

    /* ── HEADER ── */
    .rh-header {{
        background: linear-gradient(135deg, #0D1117 0%, #161B22 100%);
        border: 1px solid #30363D;
        border-left: 4px solid {brand_color};
        border-radius: 12px;
        padding: 2rem 2.5rem;
        margin-bottom: 1.8rem;
    }}
    .rh-header h1 {{
        font-size: 2.4rem;
        font-weight: 800;
        color: {text_main};
        margin: 0;
        letter-spacing: -1px;
        line-height: 1.2;
    }}
    .rh-header h1 em {{
        color: {brand_color};
        font-style: normal;
    }}
    .rh-header p {{
        color: #8B949E;
        margin: 0.5rem 0 0;
        font-size: 0.95rem;
        line-height: 1.6;
    }}

    /* ── RUN BUTTON ── */
    div[data-testid="stButton"] > button {{
        background: {brand_color} !important;
        color: #ffffff !important;
        border: none !important;
        border-radius: 8px !important;
        font-weight: 700 !important;
        font-family: 'Inter', sans-serif !important;
        font-size: 1rem !important;
        letter-spacing: 0.3px !important;
        padding: 0.7rem 2rem !important;
        width: 100% !important;
        transition: background 0.2s ease, transform 0.1s ease, box-shadow 0.2s ease !important;
        box-shadow: 0 2px 8px rgba(46, 160, 67, 0.25) !important;
    }}
    div[data-testid="stButton"] > button:hover {{
        background: #3FB950 !important;
        box-shadow: 0 4px 16px rgba(46, 160, 67, 0.4) !important;
        transform: translateY(-1px) !important;
    }}
    div[data-testid="stButton"] > button:active {{
        transform: translateY(0px) !important;
        background: #238636 !important;
    }}

    /* ── STAT CARDS ── */
    .stat-card {{
        background: #161B22;
        border: 1px solid #30363D;
        border-radius: 10px;
        padding: 1.2rem;
        text-align: center;
        transition: border-color 0.2s;
    }}
    .stat-card:hover {{ border-color: {brand_color}; }}
    .stat-num {{
        font-size: 1.9rem;
        font-weight: 800;
        color: {brand_color};
        font-family: 'DM Mono', monospace;
        line-height: 1;
    }}
    .stat-label {{
        font-size: 0.7rem;
        color: #8B949E;
        text-transform: uppercase;
        letter-spacing: 1.3px;
        margin-top: 0.35rem;
        font-weight: 500;
    }}

    /* ── SOURCE STATUS PILLS ── */
    .pill {{
        display: inline-flex;
        align-items: center;
        gap: 0.3rem;
        padding: 0.2rem 0.65rem;
        border-radius: 999px;
        font-size: 0.72rem;
        font-weight: 600;
        font-family: 'DM Mono', monospace;
        letter-spacing: 0.3px;
        margin: 0.15rem 0.1rem;
    }}
    .pill-green  {{ background: #0D3320; color: #3FB950; border: 1px solid #238636; }}
    .pill-yellow {{ background: #2D1F00; color: #E3B341; border: 1px solid #9E6A03; }}
    .pill-red    {{ background: #2D0E0E; color: #F85149; border: 1px solid #8E1519; }}
    .pill-gray   {{ background: #1C2128; color: #8B949E; border: 1px solid #30363D; }}
    .pill-blue   {{ background: #0C2135; color: {accent_color}; border: 1px solid #1158A7; }}

    /* ── SECTION HEADERS ── */
    .sec-head {{
        font-size: 0.72rem;
        font-weight: 700;
        color: #8B949E;
        text-transform: uppercase;
        letter-spacing: 1.6px;
        border-bottom: 1px solid #21262D;
        padding-bottom: 0.45rem;
        margin: 1.4rem 0 0.9rem;
    }}

    /* ── TIP / INFO BOXES ── */
    .tip-box {{
        background: #161B22;
        border: 1px solid #30363D;
        border-radius: 8px;
        padding: 0.9rem 1.1rem;
        font-size: 0.85rem;
        color: #8B949E;
        margin-bottom: 0.8rem;
        line-height: 1.6;
    }}
    .tip-box strong {{ color: {text_main}; }}
    .tip-box a {{ color: {accent_color}; text-decoration: none; }}
    .tip-box a:hover {{ text-decoration: underline; }}

    /* ── CSV STATUS ── */
    .csv-status {{
        background: #161B22;
        border: 1px solid #30363D;
        border-radius: 8px;
        padding: 0.8rem 1rem;
        font-size: 0.83rem;
        color: #8B949E;
        margin-bottom: 0.6rem;
        line-height: 1.6;
    }}
    .csv-status strong {{ color: {text_main}; }}

    /* ── ALERT BOXES ── */
    .reminder-box {{
        background: #2D1F00;
        border: 1px solid #9E6A03;
        border-left: 3px solid #E3B341;
        border-radius: 8px;
        padding: 1rem 1.2rem;
        font-size: 0.88rem;
        color: #E3B341;
        margin-bottom: 1rem;
        line-height: 1.6;
    }}
    .reminder-box strong {{ color: #F0C040; }}
    .reminder-box a {{ color: #E3B341; }}

    .urgent-box {{
        background: #2D0E0E;
        border: 1px solid #8E1519;
        border-left: 3px solid #F85149;
        border-radius: 8px;
        padding: 1rem 1.2rem;
        font-size: 0.88rem;
        color: #F85149;
        margin-bottom: 1rem;
        line-height: 1.6;
    }}
    .urgent-box strong {{ color: #FF7B72; }}
    .urgent-box a {{ color: #F85149; }}

    /* ── BOOLEAN STRING BOX ── */
    .bool-box {{
        background: #0D1117;
        border: 1px solid #30363D;
        border-left: 3px solid {brand_color};
        border-radius: 8px;
        padding: 1.2rem 1.5rem;
        font-family: 'DM Mono', monospace;
        font-size: 0.82rem;
        color: #8B949E;
        white-space: pre-wrap;
        word-break: break-all;
        max-height: 280px;
        overflow-y: auto;
        line-height: 1.7;
    }}

    /* ── DATAFRAME — sticky headers + zebra stripes ── */
    [data-testid="stDataFrame"] table {{
        border-collapse: collapse !important;
        width: 100% !important;
    }}
    [data-testid="stDataFrame"] thead th {{
        position: sticky !important;
        top: 0 !important;
        background: #161B22 !important;
        color: {accent_color} !important;
        font-size: 0.75rem !important;
        font-weight: 700 !important;
        text-transform: uppercase !important;
        letter-spacing: 0.8px !important;
        padding: 0.65rem 0.9rem !important;
        border-bottom: 2px solid #30363D !important;
        z-index: 1 !important;
    }}
    [data-testid="stDataFrame"] tbody tr:nth-child(odd) td {{
        background: #0D1117 !important;
    }}
    [data-testid="stDataFrame"] tbody tr:nth-child(even) td {{
        background: #161B22 !important;
    }}
    [data-testid="stDataFrame"] tbody tr:hover td {{
        background: #1C2A1C !important;
    }}
    [data-testid="stDataFrame"] tbody td {{
        color: {text_main} !important;
        font-size: 0.85rem !important;
        padding: 0.55rem 0.9rem !important;
        border-bottom: 1px solid #21262D !important;
        line-height: 1.6 !important;
    }}

    /* ── INPUT FIELDS ── */
    [data-testid="stTextInput"] input {{
        background: #0D1117 !important;
        border: 1px solid #30363D !important;
        border-radius: 6px !important;
        color: {text_main} !important;
        font-family: 'DM Mono', monospace !important;
        font-size: 0.85rem !important;
    }}
    [data-testid="stTextInput"] input:focus {{
        border-color: {brand_color} !important;
        box-shadow: 0 0 0 2px rgba(46,160,67,0.2) !important;
    }}

    /* ── TOGGLE ── */
    [data-testid="stToggle"] span[data-checked="true"] {{
        background: {brand_color} !important;
    }}

    /* ── SUCCESS / WARNING / INFO ALERTS ── */
    [data-testid="stAlert"] {{
        border-radius: 8px !important;
        font-size: 0.88rem !important;
        line-height: 1.6 !important;
    }}

    /* ── DOWNLOAD BUTTONS ── */
    [data-testid="stDownloadButton"] button {{
        background: #161B22 !important;
        color: {text_main} !important;
        border: 1px solid #30363D !important;
        border-radius: 8px !important;
        font-weight: 600 !important;
        font-size: 0.88rem !important;
        transition: border-color 0.2s, background 0.2s !important;
    }}
    [data-testid="stDownloadButton"] button:hover {{
        border-color: {brand_color} !important;
        background: #1C2A1C !important;
        color: {brand_color} !important;
    }}

    /* ── SCROLLBAR ── */
    ::-webkit-scrollbar {{ width: 6px; height: 6px; }}
    ::-webkit-scrollbar-track {{ background: #0D1117; }}
    ::-webkit-scrollbar-thumb {{ background: #30363D; border-radius: 3px; }}
    ::-webkit-scrollbar-thumb:hover {{ background: {brand_color}; }}

    </style>
    """, unsafe_allow_html=True)

# ─────────────────────────────────────────
# INIT
# ─────────────────────────────────────────
load_saved_settings()
style_app()

# ─────────────────────────────────────────
# HEADER
# ─────────────────────────────────────────
st.markdown("""
<div class="rh-header">
  <h1>🐾 RIF<em>Hound</em></h1>
  <p>Recruiting Intelligence Engine — Surfaces layoffs, WARN notices &amp; M&amp;A signals into a recruiter-ready pipeline report.</p>
</div>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────
# 90-DAY CSV REMINDER BANNER
# ─────────────────────────────────────────
csv_age = get_csv_age_days()

if csv_age >= 90:
    st.markdown(f"""
    <div class="urgent-box">
    <strong>⚠️ Your Layoffs.FYI data is {csv_age} days old and is now stale.</strong><br>
    Go to <a href="https://layoffs.fyi" target="_blank">layoffs.fyi</a>,
    download a fresh CSV, and upload it in the sidebar to keep your results current.
    </div>
    """, unsafe_allow_html=True)
elif csv_age >= 75:
    st.markdown(f"""
    <div class="reminder-box">
    <strong>📅 Heads up — your Layoffs.FYI CSV is {csv_age} days old.</strong><br>
    It covers a 90-day window, so it'll expire in about {90 - csv_age} days.
    Download a fresh one soon from <a href="https://layoffs.fyi" target="_blank">layoffs.fyi</a>.
    </div>
    """, unsafe_allow_html=True)

# ─────────────────────────────────────────
# SIDEBAR
# ─────────────────────────────────────────
with st.sidebar:
    st.markdown("### 🔑 API Keys")
    st.markdown("""
    <div class="tip-box">
    Enter once — saved for your session automatically.<br><br>
    <strong>WARNFirehose</strong> — Free key at
    <a href="https://warnfirehose.com/account" target="_blank">warnfirehose.com/account</a><br><br>
    <strong>Tavily</strong> — Free key at
    <a href="https://app.tavily.com" target="_blank">app.tavily.com</a>
    </div>
    """, unsafe_allow_html=True)

    warn_key_input = st.text_input(
        "WARNFirehose API Key",
        value=st.session_state.warn_key,
        type="password",
        placeholder="wfh_xxxxxxxxxxxxxxxx",
    )
    tavily_key_input = st.text_input(
        "Tavily API Key",
        value=st.session_state.tavily_key,
        type="password",
        placeholder="tvly-xxxxxxxxxxxxxxxx",
    )

    if warn_key_input != st.session_state.warn_key or tavily_key_input != st.session_state.tavily_key:
        save_keys(warn_key_input, tavily_key_input)
        if warn_key_input or tavily_key_input:
            st.success("✅ Keys saved for this session")

    st.markdown("---")
    st.markdown("### ⚙️ Data Sources")
    include_warn = st.toggle("🔴 WARN Act Notices", value=True)
    include_sec  = st.toggle("🟣 SEC 8-K Filings",  value=True)
    include_news = st.toggle("🔵 News & M&A Scanner", value=True)

    st.markdown("---")
    st.markdown("### 📁 Layoffs.FYI CSV")

    if st.session_state.csv_content:
        age = get_csv_age_days()
        age_color = "#f87171" if age >= 90 else "#f59e0b" if age >= 75 else "#4ade80"
        age_note  = "⚠️ Refresh now" if age >= 90 else "⚠️ Refresh soon" if age >= 75 else "✓ Fresh"
        st.markdown(f"""
        <div class="csv-status">
        <strong>✅ {st.session_state.csv_filename or 'layoffs.csv'}</strong><br>
        <span style="color:{age_color}">Uploaded {age} day{'s' if age != 1 else ''} ago — {age_note}</span>
        </div>
        """, unsafe_allow_html=True)
        if st.button("🗑️ Clear saved CSV"):
            clear_csv()
            st.rerun()
    else:
        st.markdown("""
        <div class="tip-box">
        Go to <a href="https://layoffs.fyi" target="_blank">layoffs.fyi</a>,
        enter your email, download the free CSV.<br><br>
        <strong>Upload once — RIFHound saves it automatically.</strong>
        You'll get a reminder at 75 days and again at 90 days to refresh it.
        </div>
        """, unsafe_allow_html=True)

    uploaded_file = st.file_uploader("Upload Layoffs.FYI CSV", type=["csv"], label_visibility="collapsed")
    if uploaded_file is not None:
        content = uploaded_file.read().decode("utf-8", errors="replace")
        save_csv(content, uploaded_file.name)
        st.success(f"✅ Saved: {uploaded_file.name}")

    st.markdown("---")
    st.markdown("### 📡 Source Status")

    def _pill(label, ready, extra=""):
        cls = "pill-green" if ready else "pill-gray"
        dot = "●" if ready else "○"
        return f'<span class="pill {cls}">{dot} {label}{extra}</span>'

    warn_ready   = bool(st.session_state.warn_key)
    tavily_ready = bool(st.session_state.tavily_key)
    csv_ready    = bool(st.session_state.csv_content)
    csv_extra    = f" ({csv_age}d)" if csv_ready else ""

    st.markdown(
        _pill("WARN Notices", warn_ready) + " " +
        _pill("SEC 8-K", warn_ready) + "<br>" +
        _pill("News Scanner", tavily_ready) + " " +
        _pill("Layoffs.FYI", csv_ready, csv_extra),
        unsafe_allow_html=True
    )

# ─────────────────────────────────────────
# RUN BUTTON
# ─────────────────────────────────────────
has_any_source = (
    (st.session_state.warn_key and (include_warn or include_sec)) or
    (st.session_state.tavily_key and include_news) or
    st.session_state.csv_content is not None
)

if not has_any_source:
    st.markdown("""
    <div class="tip-box" style="border-left:3px solid #e53e3e;color:#888">
    ⚠️ Add at least one API key or upload a CSV to get started.
    </div>
    """, unsafe_allow_html=True)

col_l, col_m, col_r = st.columns([1, 2, 1])
with col_m:
    run_btn = st.button("🔍  Run RIFHound", disabled=not has_any_source)

# ─────────────────────────────────────────
# PIPELINE
# ─────────────────────────────────────────
if run_btn:
    progress = st.progress(0)
    status_el = st.empty()

    def on_progress(msg, pct):
        progress.progress(pct / 100)
        status_el.markdown(f"**{msg}**")

    try:
        results = run_pipeline(
            warnfirehose_key=st.session_state.warn_key or "",
            tavily_key=st.session_state.tavily_key or "",
            uploaded_csv=st.session_state.csv_content,
            include_warn=include_warn,
            include_sec=include_sec,
            include_news=include_news,
            progress_callback=on_progress,
        )
        progress.empty()
        status_el.empty()

        for err in results["errors"]:
            st.warning(f"⚠️ {err}")

        total   = results["total"]
        records = results["records"]
        sc      = results["source_counts"]

        if total == 0:
            st.info("No results found. Try adding API keys or uploading a Layoffs.FYI CSV.")
        else:
            st.success(f"✅ RIFHound found **{total} companies** with active talent availability signals.")

            st.markdown('<div class="sec-head">Results Breakdown</div>', unsafe_allow_html=True)
            c1, c2, c3, c4, c5 = st.columns(5)
            for col, label, key in [
                (c1, "Total", None), (c2, "WARN Notices", "WARN"),
                (c3, "SEC 8-K", "SEC_8K"), (c4, "Layoffs.FYI", "LAYOFFS_FYI"),
                (c5, "News Signals", "NEWS"),
            ]:
                count = total if key is None else sc.get(key, 0)
                with col:
                    st.markdown(f'<div class="stat-card"><div class="stat-num">{count}</div><div class="stat-label">{label}</div></div>', unsafe_allow_html=True)

            st.markdown('<div class="sec-head">Talent Availability Report</div>', unsafe_allow_html=True)
            rows = [{"Date": r.date.strftime("%Y-%m-%d"), "Company": r.company,
                     "Location": r.location or "—", "Target Group": r.target_group or "Review",
                     "Headcount": r.headcount or "—", "Pitch Angle": r.pitch_angle,
                     "Source": r.source, "Reason": r.reason} for r in records]
            df = pd.DataFrame(rows)

            f1, f2 = st.columns(2)
            with f1:
                grp_filter = st.multiselect("Filter by Target Group", options=sorted(df["Target Group"].unique()), placeholder="All groups")
            with f2:
                src_filter = st.multiselect("Filter by Source", options=sorted(df["Source"].unique()), placeholder="All sources")

            filtered = df.copy()
            if grp_filter: filtered = filtered[filtered["Target Group"].isin(grp_filter)]
            if src_filter:  filtered = filtered[filtered["Source"].isin(src_filter)]

            st.dataframe(filtered, use_container_width=True, hide_index=True, height=420)
            st.caption(f"Showing {len(filtered)} of {total} companies")

            st.markdown('<div class="sec-head">Export</div>', unsafe_allow_html=True)
            d1, d2 = st.columns(2)
            with d1:
                st.download_button("📥 Full Report (CSV)", data=results["csv_bytes"],
                    file_name=f"rifhound_{datetime.today().strftime('%Y%m%d')}.csv",
                    mime="text/csv", use_container_width=True)
            with d2:
                st.download_button("📥 Filtered View (CSV)",
                    data=filtered.to_csv(index=False).encode("utf-8"),
                    file_name=f"rifhound_filtered_{datetime.today().strftime('%Y%m%d')}.csv",
                    mime="text/csv", use_container_width=True)

            st.markdown('<div class="sec-head">LinkedIn Recruiter Boolean String</div>', unsafe_allow_html=True)
            st.markdown('<div class="tip-box">Paste into the <strong>Current Company</strong> filter in LinkedIn Recruiter. Set to <strong>"Current"</strong>.</div>', unsafe_allow_html=True)
            if results["boolean_str"]:
                st.markdown(f'<div class="bool-box">{results["boolean_str"]}</div>', unsafe_allow_html=True)
                st.download_button("📋 Download Boolean String (.txt)",
                    data=results["boolean_str"].encode("utf-8"),
                    file_name=f"rifhound_boolean_{datetime.today().strftime('%Y%m%d')}.txt",
                    mime="text/plain")

    except Exception as e:
        progress.empty()
        status_el.empty()
        st.error(f"Something went wrong: {str(e)}")
        st.info("Check your API keys are correct and try again.")

else:
    st.markdown('<div class="sec-head">How It Works</div>', unsafe_allow_html=True)
    c1, c2, c3, c4 = st.columns(4)
    for col, icon, title, desc in zip([c1,c2,c3,c4],
        ["🔴","🟣","🔵","📁"],
        ["WARN Act Notices","SEC 8-K Filings","M&A News Scanner","Layoffs.FYI CSV"],
        [
            "Federal law requires 60-day advance notice before mass layoffs. RIFHound pulls all 50 states daily.",
            "Item 2.05 = confirmed workforce restructuring filed with the SEC. Most reliable corporate signal.",
            "Tavily searches for layoff, merger, and restructuring news — catches signals before WARN notices are filed.",
            "Upload once, saved automatically. You'll get a reminder at 75 days and again at 90 days to refresh it.",
        ]):
        with col:
            st.markdown(f'<div class="stat-card" style="text-align:left;padding:1.4rem"><div style="font-size:1.6rem;margin-bottom:0.6rem">{icon}</div><div style="font-weight:700;color:#ccc;margin-bottom:0.4rem;font-size:0.9rem">{title}</div><div style="color:#555;font-size:0.8rem;line-height:1.5">{desc}</div></div>', unsafe_allow_html=True)

    st.markdown('<div class="tip-box" style="margin-top:1.5rem;text-align:center"><strong>Ready to start?</strong> Add your API keys in the sidebar — saved automatically. Both WARNFirehose and Tavily offer <strong>free tiers</strong>.</div>', unsafe_allow_html=True)
