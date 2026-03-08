# app.py
# RIFHound v2 — Streamlit Web Interface
# Run with: streamlit run app.py

import streamlit as st
import pandas as pd
from datetime import datetime
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
# STYLES
# ─────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Syne:wght@400;600;700;800&family=DM+Mono:wght@400;500&display=swap');

html, body, [class*="css"] { font-family: 'Syne', sans-serif; }

/* Header */
.rh-header {
    background: #0d0d0d;
    border: 1px solid #222;
    border-left: 4px solid #e53e3e;
    border-radius: 12px;
    padding: 2rem 2.5rem;
    margin-bottom: 1.5rem;
}
.rh-header h1 {
    font-size: 2.6rem;
    font-weight: 800;
    color: #fff;
    margin: 0;
    letter-spacing: -1px;
}
.rh-header h1 em { color: #e53e3e; font-style: normal; }
.rh-header p { color: #666; margin: 0.4rem 0 0; font-size: 0.95rem; }

/* Stat cards */
.stat-row { display: flex; gap: 1rem; margin: 1rem 0; }
.stat-card {
    flex: 1;
    background: #0d0d0d;
    border: 1px solid #1e1e1e;
    border-radius: 10px;
    padding: 1.2rem;
    text-align: center;
}
.stat-num {
    font-size: 2rem;
    font-weight: 800;
    color: #e53e3e;
    font-family: 'DM Mono', monospace;
    line-height: 1;
}
.stat-label {
    font-size: 0.72rem;
    color: #555;
    text-transform: uppercase;
    letter-spacing: 1.2px;
    margin-top: 0.3rem;
}

/* Source badges */
.badge {
    display: inline-block;
    padding: 0.15rem 0.5rem;
    border-radius: 4px;
    font-size: 0.7rem;
    font-weight: 700;
    font-family: 'DM Mono', monospace;
    letter-spacing: 0.5px;
}
.badge-WARN       { background:#2d1515; color:#f87171; border:1px solid #4a2020; }
.badge-SEC_8K     { background:#1a1a2d; color:#818cf8; border:1px solid #2a2a4a; }
.badge-LAYOFFS_FYI{ background:#1a2d1a; color:#4ade80; border:1px solid #2a4a2a; }
.badge-NEWS       { background:#1a2030; color:#60a5fa; border:1px solid #2a3050; }

/* Boolean output */
.bool-box {
    background: #080808;
    border: 1px solid #1e1e1e;
    border-left: 3px solid #e53e3e;
    border-radius: 8px;
    padding: 1.2rem 1.5rem;
    font-family: 'DM Mono', monospace;
    font-size: 0.82rem;
    color: #aaa;
    white-space: pre-wrap;
    word-break: break-all;
    max-height: 280px;
    overflow-y: auto;
    line-height: 1.6;
}

/* Info / tip boxes */
.tip-box {
    background: #0d0d0d;
    border: 1px solid #1e1e1e;
    border-radius: 8px;
    padding: 0.9rem 1.1rem;
    font-size: 0.85rem;
    color: #666;
    margin-bottom: 0.8rem;
    line-height: 1.5;
}
.tip-box strong { color: #aaa; }
.tip-box a { color: #e53e3e; text-decoration: none; }

/* Section headers */
.sec-head {
    font-size: 0.75rem;
    font-weight: 700;
    color: #555;
    text-transform: uppercase;
    letter-spacing: 1.5px;
    border-bottom: 1px solid #1e1e1e;
    padding-bottom: 0.4rem;
    margin: 1.2rem 0 0.8rem;
}

/* Run button */
div[data-testid="stButton"] > button {
    background: #e53e3e !important;
    color: white !important;
    border: none !important;
    border-radius: 8px !important;
    font-weight: 700 !important;
    font-family: 'Syne', sans-serif !important;
    font-size: 1rem !important;
    padding: 0.65rem 2rem !important;
    letter-spacing: 0.3px !important;
    transition: background 0.2s !important;
    width: 100% !important;
}
div[data-testid="stButton"] > button:hover {
    background: #c53030 !important;
}

/* Sidebar */
[data-testid="stSidebar"] { background: #080808 !important; }
[data-testid="stSidebar"] .stMarkdown p { color: #666; font-size: 0.85rem; }

/* Warning/error callouts */
.warn-note {
    background: #1a1200;
    border: 1px solid #3a2a00;
    border-radius: 6px;
    padding: 0.6rem 0.9rem;
    font-size: 0.82rem;
    color: #b8860b;
    margin-top: 0.5rem;
}
</style>
""", unsafe_allow_html=True)

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
# SIDEBAR — API KEYS + SETTINGS
# ─────────────────────────────────────────
with st.sidebar:
    st.markdown("### 🔑 API Keys")

    st.markdown("""
    <div class="tip-box">
    <strong>WARNFirehose</strong> — Free key at
    <a href="https://warnfirehose.com/account" target="_blank">warnfirehose.com/account</a><br>
    Powers WARN notices + SEC 8-K filings.
    </div>
    """, unsafe_allow_html=True)

    warn_key = st.text_input(
        "WARNFirehose API Key",
        type="password",
        placeholder="wfh_xxxxxxxxxxxxxxxx",
        help="Get a free key at warnfirehose.com/account (50 calls/day free)"
    )

    st.markdown("""
    <div class="tip-box" style="margin-top:0.6rem">
    <strong>Tavily</strong> — Free key at
    <a href="https://app.tavily.com" target="_blank">app.tavily.com</a><br>
    Powers the news &amp; M&amp;A scanner.
    </div>
    """, unsafe_allow_html=True)

    tavily_key = st.text_input(
        "Tavily API Key",
        type="password",
        placeholder="tvly-xxxxxxxxxxxxxxxx",
        help="Get a free key at app.tavily.com"
    )

    st.markdown("---")
    st.markdown("### ⚙️ Data Sources")

    include_warn = st.toggle("🔴 WARN Act Notices", value=True,
        help="All 50 states via WARNFirehose. Most reliable layoff signal — 60-day advance notice required by law.")
    include_sec = st.toggle("🟣 SEC 8-K Filings", value=True,
        help="Item 2.05 = confirmed restructuring/workforce reduction filed with SEC.")
    include_news = st.toggle("🔵 News & M&A Scanner", value=True,
        help="Uses Tavily to scan for layoff, M&A, and restructuring news signals.")

    st.markdown("---")
    st.markdown("### 📁 Layoffs.FYI Upload")
    st.markdown("""
    <div class="tip-box">
    <strong>Optional but recommended.</strong><br>
    Go to <a href="https://layoffs.fyi" target="_blank">layoffs.fyi</a>, 
    enter your email, and download the free CSV (last 90 days, up to 500 rows). 
    Upload it here to combine with API data.
    </div>
    """, unsafe_allow_html=True)

    uploaded_file = st.file_uploader(
        "Upload Layoffs.FYI CSV",
        type=["csv"],
        label_visibility="collapsed"
    )

    st.markdown("---")

    # Key status indicators
    st.markdown("### 📡 Source Status")
    warn_status = "✅ Connected" if warn_key else "⚠️ Key needed"
    tavily_status = "✅ Connected" if tavily_key else "⚠️ Key needed"
    csv_status = "✅ Uploaded" if uploaded_file else "—  Not uploaded"

    st.markdown(f"""
    <div class="tip-box">
    🔴 WARN notices: <strong>{warn_status}</strong><br>
    🟣 SEC 8-K filings: <strong>{warn_status}</strong><br>
    🔵 News scanner: <strong>{tavily_status}</strong><br>
    📁 Layoffs.FYI: <strong>{csv_status}</strong>
    </div>
    """, unsafe_allow_html=True)

# ─────────────────────────────────────────
# VALIDATION + RUN BUTTON
# ─────────────────────────────────────────
has_any_source = (
    (warn_key and (include_warn or include_sec)) or
    (tavily_key and include_news) or
    uploaded_file is not None
)

if not has_any_source:
    st.markdown("""
    <div class="warn-note">
    ⚠️ Add at least one API key or upload a CSV to get started. 
    Both WARNFirehose and Tavily offer free tiers — see sidebar for links.
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
    status = st.empty()

    def on_progress(msg: str, pct: int):
        progress.progress(pct / 100)
        status.markdown(f"**{msg}**")

    uploaded_content = None
    if uploaded_file:
        uploaded_content = uploaded_file.read().decode("utf-8", errors="replace")

    try:
        results = run_pipeline(
            warnfirehose_key=warn_key or "",
            tavily_key=tavily_key or "",
            uploaded_csv=uploaded_content,
            include_warn=include_warn,
            include_sec=include_sec,
            include_news=include_news,
            progress_callback=on_progress,
        )

        progress.empty()
        status.empty()

        # Surface any skipped-source warnings
        if results["errors"]:
            for err in results["errors"]:
                st.warning(f"⚠️ {err}")

        total = results["total"]
        records = results["records"]
        sc = results["source_counts"]

        if total == 0:
            st.info("No results found. Try adding more API keys or uploading a Layoffs.FYI CSV.")
        else:
            st.success(f"✅ RIFHound found **{total} companies** with active talent availability signals.")

            # ── STATS ──
            st.markdown('<div class="sec-head">Results Breakdown</div>', unsafe_allow_html=True)
            c1, c2, c3, c4, c5 = st.columns(5)
            for col, label, key in [
                (c1, "Total", None),
                (c2, "WARN Notices", "WARN"),
                (c3, "SEC 8-K", "SEC_8K"),
                (c4, "Layoffs.FYI", "LAYOFFS_FYI"),
                (c5, "News Signals", "NEWS"),
            ]:
                count = total if key is None else sc.get(key, 0)
                with col:
                    st.markdown(f"""
                    <div class="stat-card">
                        <div class="stat-num">{count}</div>
                        <div class="stat-label">{label}</div>
                    </div>
                    """, unsafe_allow_html=True)

            # ── TABLE ──
            st.markdown('<div class="sec-head">Talent Availability Report</div>', unsafe_allow_html=True)

            rows = []
            for r in records:
                rows.append({
                    "Date": r.date.strftime("%Y-%m-%d"),
                    "Company": r.company,
                    "Location": r.location or "—",
                    "Target Group": r.target_group or "Review",
                    "Headcount": r.headcount or "—",
                    "Pitch Angle": r.pitch_angle,
                    "Source": r.source,
                    "Reason": r.reason,
                })
            df = pd.DataFrame(rows)

            # Filters
            f1, f2 = st.columns(2)
            with f1:
                grp_filter = st.multiselect(
                    "Filter by Target Group",
                    options=sorted(df["Target Group"].unique()),
                    placeholder="All groups"
                )
            with f2:
                src_filter = st.multiselect(
                    "Filter by Source",
                    options=sorted(df["Source"].unique()),
                    placeholder="All sources"
                )

            filtered = df.copy()
            if grp_filter:
                filtered = filtered[filtered["Target Group"].isin(grp_filter)]
            if src_filter:
                filtered = filtered[filtered["Source"].isin(src_filter)]

            st.dataframe(filtered, use_container_width=True, hide_index=True, height=420)
            st.caption(f"Showing {len(filtered)} of {total} companies")

            # ── DOWNLOADS ──
            st.markdown('<div class="sec-head">Export</div>', unsafe_allow_html=True)
            d1, d2 = st.columns(2)
            with d1:
                st.download_button(
                    "📥 Full Report (CSV)",
                    data=results["csv_bytes"],
                    file_name=f"rifhound_{datetime.today().strftime('%Y%m%d')}.csv",
                    mime="text/csv",
                    use_container_width=True,
                )
            with d2:
                filtered_csv = filtered.to_csv(index=False).encode("utf-8")
                st.download_button(
                    "📥 Filtered View (CSV)",
                    data=filtered_csv,
                    file_name=f"rifhound_filtered_{datetime.today().strftime('%Y%m%d')}.csv",
                    mime="text/csv",
                    use_container_width=True,
                )

            # ── BOOLEAN STRING ──
            st.markdown('<div class="sec-head">LinkedIn Recruiter Boolean String</div>', unsafe_allow_html=True)
            st.markdown("""
            <div class="tip-box">
            Paste into the <strong>Current Company</strong> filter in LinkedIn Recruiter. 
            Set the filter to <strong>"Current"</strong> to target people still employed at these companies.
            </div>
            """, unsafe_allow_html=True)

            bool_str = results["boolean_str"]
            if bool_str:
                st.markdown(f'<div class="bool-box">{bool_str}</div>', unsafe_allow_html=True)
                st.download_button(
                    "📋 Download Boolean String (.txt)",
                    data=bool_str.encode("utf-8"),
                    file_name=f"rifhound_boolean_{datetime.today().strftime('%Y%m%d')}.txt",
                    mime="text/plain",
                )
            else:
                st.info("No companies found — unable to generate Boolean string.")

    except Exception as e:
        progress.empty()
        status.empty()
        st.error(f"Something went wrong: {str(e)}")
        st.info("Check that your API keys are correct and try again.")

# ─────────────────────────────────────────
# EMPTY STATE
# ─────────────────────────────────────────
else:
    st.markdown('<div class="sec-head">How It Works</div>', unsafe_allow_html=True)
    c1, c2, c3, c4 = st.columns(4)
    cards = [
        ("🔴", "WARN Act Notices",
         "Federal law requires 60-day advance notice before mass layoffs. RIFHound pulls all 50 states daily via WARNFirehose API."),
        ("🟣", "SEC 8-K Filings",
         "Item 2.05 filings = confirmed workforce restructuring. Publicly filed with the SEC — RIFHound surfaces them automatically."),
        ("🔵", "M&A News Scanner",
         "Tavily searches for recent layoff, merger, and restructuring news. Catches signals before WARN notices are even filed."),
        ("📁", "Layoffs.FYI Upload",
         "Download the free 90-day CSV from Layoffs.fyi and upload it here. RIFHound merges it with API data and deduplicates everything."),
    ]
    for col, (icon, title, desc) in zip([c1, c2, c3, c4], cards):
        with col:
            st.markdown(f"""
            <div class="stat-card" style="text-align:left; padding:1.4rem;">
                <div style="font-size:1.6rem; margin-bottom:0.6rem;">{icon}</div>
                <div style="font-weight:700; color:#ccc; margin-bottom:0.4rem; font-size:0.9rem;">{title}</div>
                <div style="color:#555; font-size:0.8rem; line-height:1.5;">{desc}</div>
            </div>
            """, unsafe_allow_html=True)

    st.markdown("""
    <div class="tip-box" style="margin-top:1.5rem; text-align:center;">
    <strong>Ready to start?</strong> Add your API keys in the sidebar, then click <strong>Run RIFHound</strong>.<br>
    Both WARNFirehose and Tavily offer <strong>free tiers</strong> — no credit card required.
    </div>
    """, unsafe_allow_html=True)
