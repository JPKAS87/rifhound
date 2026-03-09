# app.py
# RIFHound v2 — Streamlit Web Interface
# Run with: streamlit run app.py

import streamlit as st
import pandas as pd
import json
import os
import subprocess
from datetime import datetime, timezone, timedelta
from rifhound_core import run_pipeline

# ─────────────────────────────────────────
# PLAYWRIGHT INSTALL (runs once on cold start)
# Streamlit Cloud doesn't persist installed browsers
# between deploys, so we install on startup.
# ─────────────────────────────────────────
@st.cache_resource
def install_playwright():
    """
    Installs Playwright's Chromium binary with all system deps.
    Uses --with-deps to handle missing system libraries on Streamlit Cloud.
    Cached so it only runs once per cold start.
    """
    try:
        # Install chromium + all required system dependencies
        result = subprocess.run(
            ["playwright", "install", "chromium", "--with-deps"],
            capture_output=True, text=True, timeout=180,
            env={**os.environ, "PLAYWRIGHT_BROWSERS_PATH": "/home/adminuser/.cache/ms-playwright"}
        )
        return result.returncode
    except Exception as e:
        return str(e)

_pw_status = install_playwright()

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
    RIFHound design system — matched to brand logo palette.
    Logo palette:
        brand_color  = #A61C1C  (crimson red)
        accent_color = #D94040  (lighter red for hover)
        sidebar_bg   = #0D1B2A  (near-black with warm tint)
        main_bg      = #111111  (dark canvas)
        text_main    = #F0F0F0  (off-white)
    Typography: Bebas Neue for headers, Barlow for body, DM Mono for data.
    """
    brand_color  = "#003F8A"
    accent_color = "#1A6EC4"
    sidebar_bg   = "#0D1B2A"
    main_bg      = "#060D18"
    text_main    = "#F0F0F0"
    border_col   = "#1A2A3A"

    st.markdown(f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Bebas+Neue&family=Barlow:wght@400;500;600;700&family=DM+Mono:wght@400;500&display=swap');

    html, body, [class*="css"] {{
        font-family: 'Barlow', sans-serif;
        line-height: 1.6;
        color: {text_main};
        background-color: {main_bg};
    }}
    .main .block-container {{
        padding: 2rem 2.5rem 3rem;
        max-width: 1200px;
    }}

    /* SIDEBAR */
    [data-testid="stSidebar"] {{
        background: {sidebar_bg} !important;
        border-right: 1px solid {border_col} !important;
    }}
    [data-testid="stSidebar"] .stMarkdown p,
    [data-testid="stSidebar"] label {{
        color: #888 !important;
        font-size: 0.85rem !important;
        line-height: 1.6 !important;
    }}
    [data-testid="stSidebar"] h3 {{
        color: {text_main} !important;
        font-size: 0.72rem !important;
        font-weight: 700 !important;
        text-transform: uppercase !important;
        letter-spacing: 2px !important;
        margin-bottom: 0.6rem !important;
    }}

    /* HEADER */
    .rh-header {{
        background: linear-gradient(135deg, #080F1A 0%, #0D1B2A 100%);
        border: 1px solid #0A1A2E;
        border-left: 4px solid {brand_color};
        border-radius: 12px;
        padding: 1.6rem 2rem;
        margin-bottom: 1.8rem;
        display: flex;
        align-items: center;
        gap: 1.5rem;
    }}
    .rh-logo {{ flex-shrink: 0; }}
    .rh-header-text h1 {{
        font-family: 'Bebas Neue', sans-serif;
        font-size: 3rem;
        font-weight: 400;
        color: {text_main};
        margin: 0;
        letter-spacing: 2px;
        line-height: 1;
    }}
    .rh-header-text h1 em {{ color: {brand_color}; font-style: normal; }}
    .rh-header-text p {{
        color: #888;
        margin: 0.4rem 0 0;
        font-size: 0.9rem;
        line-height: 1.5;
    }}

    /* RUN BUTTON */
    div[data-testid="stButton"] > button {{
        background: {brand_color} !important;
        color: #ffffff !important;
        border: none !important;
        border-radius: 6px !important;
        font-family: 'Bebas Neue', sans-serif !important;
        font-size: 1.2rem !important;
        letter-spacing: 2.5px !important;
        padding: 0.65rem 2rem !important;
        width: 100% !important;
        transition: background 0.2s ease, transform 0.1s ease, box-shadow 0.2s ease !important;
        box-shadow: 0 2px 10px rgba(0,63,138,0.35) !important;
    }}
    div[data-testid="stButton"] > button:hover {{
        background: {accent_color} !important;
        box-shadow: 0 4px 18px rgba(0,63,138,0.5) !important;
        transform: translateY(-1px) !important;
    }}
    div[data-testid="stButton"] > button:active {{
        transform: translateY(0px) !important;
        background: #002D6B !important;
    }}

    /* STAT CARDS */
    .stat-card {{
        background: #0D1B2A;
        border: 1px solid {border_col};
        border-radius: 10px;
        padding: 1.2rem;
        text-align: center;
        transition: border-color 0.2s;
    }}
    .stat-card:hover {{ border-color: {brand_color}; }}
    .stat-num {{
        font-family: 'Bebas Neue', sans-serif;
        font-size: 2.2rem;
        color: {brand_color};
        line-height: 1;
        letter-spacing: 1px;
    }}
    .stat-label {{
        font-size: 0.68rem;
        color: #666;
        text-transform: uppercase;
        letter-spacing: 1.5px;
        margin-top: 0.35rem;
        font-weight: 600;
    }}

    /* PILL BADGES */
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
    .pill-green  {{ background: #0D2A0D; color: #4ADE80; border: 1px solid #166534; }}
    .pill-yellow {{ background: #2D1F00; color: #E3B341; border: 1px solid #9E6A03; }}
    .pill-red    {{ background: #0A1525; color: #F87171; border: 1px solid #003F8A; }}
    .pill-gray   {{ background: #1C1C1C; color: #666;    border: 1px solid #2A2A2A; }}

    /* SECTION HEADERS */
    .sec-head {{
        font-family: 'Bebas Neue', sans-serif;
        font-size: 0.95rem;
        font-weight: 400;
        color: #666;
        letter-spacing: 3px;
        border-bottom: 1px solid {border_col};
        padding-bottom: 0.4rem;
        margin: 1.4rem 0 0.9rem;
    }}

    /* TIP BOXES */
    .tip-box {{
        background: #0D1B2A;
        border: 1px solid {border_col};
        border-radius: 8px;
        padding: 0.9rem 1.1rem;
        font-size: 0.85rem;
        color: #888;
        margin-bottom: 0.8rem;
        line-height: 1.6;
    }}
    .tip-box strong {{ color: {text_main}; }}
    .tip-box a {{ color: {accent_color}; text-decoration: none; }}
    .tip-box a:hover {{ text-decoration: underline; }}

    /* CSV STATUS */
    .csv-status {{
        background: #0D1B2A;
        border: 1px solid {border_col};
        border-radius: 8px;
        padding: 0.8rem 1rem;
        font-size: 0.83rem;
        color: #888;
        margin-bottom: 0.6rem;
        line-height: 1.6;
    }}
    .csv-status strong {{ color: {text_main}; }}

    /* ALERT BOXES */
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
        background: #080F1A;
        border: 1px solid #003F8A;
        border-left: 3px solid {brand_color};
        border-radius: 8px;
        padding: 1rem 1.2rem;
        font-size: 0.88rem;
        color: #F87171;
        margin-bottom: 1rem;
        line-height: 1.6;
    }}
    .urgent-box strong {{ color: #FCA5A5; }}
    .urgent-box a {{ color: #F87171; }}

    /* BOOLEAN BOX */
    .bool-box {{
        background: #060D18;
        border: 1px solid {border_col};
        border-left: 3px solid {brand_color};
        border-radius: 8px;
        padding: 1.2rem 1.5rem;
        font-family: 'DM Mono', monospace;
        font-size: 0.82rem;
        color: #888;
        white-space: pre-wrap;
        word-break: break-all;
        max-height: 280px;
        overflow-y: auto;
        line-height: 1.7;
    }}

    /* DATAFRAME — sticky headers + zebra stripes */
    [data-testid="stDataFrame"] table {{ border-collapse: collapse !important; width: 100% !important; }}
    [data-testid="stDataFrame"] thead th {{
        position: sticky !important;
        top: 0 !important;
        background: #0D1B2A !important;
        color: {accent_color} !important;
        font-size: 0.72rem !important;
        font-weight: 700 !important;
        text-transform: uppercase !important;
        letter-spacing: 1px !important;
        padding: 0.65rem 0.9rem !important;
        border-bottom: 2px solid {brand_color} !important;
        z-index: 1 !important;
    }}
    [data-testid="stDataFrame"] tbody tr:nth-child(odd) td  {{ background: #111111 !important; }}
    [data-testid="stDataFrame"] tbody tr:nth-child(even) td {{ background: #080F1A !important; }}
    [data-testid="stDataFrame"] tbody tr:hover td {{ background: #0A1A2E !important; }}
    [data-testid="stDataFrame"] tbody td {{
        color: {text_main} !important;
        font-size: 0.85rem !important;
        padding: 0.55rem 0.9rem !important;
        border-bottom: 1px solid {border_col} !important;
        line-height: 1.6 !important;
    }}

    /* INPUT FIELDS */
    [data-testid="stTextInput"] input {{
        background: #060D18 !important;
        border: 1px solid {border_col} !important;
        border-radius: 6px !important;
        color: {text_main} !important;
        font-family: 'DM Mono', monospace !important;
        font-size: 0.85rem !important;
    }}
    [data-testid="stTextInput"] input:focus {{
        border-color: {brand_color} !important;
        box-shadow: 0 0 0 2px rgba(0,63,138,0.2) !important;
    }}

    /* DOWNLOAD BUTTONS */
    [data-testid="stDownloadButton"] button {{
        background: #0D1B2A !important;
        color: {text_main} !important;
        border: 1px solid {border_col} !important;
        border-radius: 6px !important;
        font-weight: 600 !important;
        font-size: 0.88rem !important;
        transition: border-color 0.2s, background 0.2s !important;
    }}
    [data-testid="stDownloadButton"] button:hover {{
        border-color: {brand_color} !important;
        background: #0A1A2E !important;
        color: {accent_color} !important;
    }}

    /* SCROLLBAR */
    ::-webkit-scrollbar {{ width: 6px; height: 6px; }}
    ::-webkit-scrollbar-track {{ background: #060D18; }}
    ::-webkit-scrollbar-thumb {{ background: #1A2A3A; border-radius: 3px; }}
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
  <div class="rh-logo">
    <svg width="72" height="72" viewBox="0 0 120 120" fill="none" xmlns="http://www.w3.org/2000/svg">
      <!-- Geometric dog head body -->
      <polygon points="20,95 40,30 80,20 105,55 95,95" fill="#003F8A"/>
      <!-- White face panel -->
      <polygon points="42,85 55,38 85,32 98,65 88,85" fill="#FFFFFF"/>
      <!-- Ear -->
      <polygon points="20,95 40,30 28,15 10,45" fill="#002D6B"/>
      <!-- Eye -->
      <circle cx="72" cy="52" r="6" fill="#003F8A"/>
      <!-- Magnifying glass circle -->
      <circle cx="66" cy="58" r="11" stroke="#003F8A" stroke-width="4" fill="none"/>
      <!-- Magnifying glass handle -->
      <line x1="74" y1="67" x2="83" y2="76" stroke="#003F8A" stroke-width="4" stroke-linecap="round"/>
      <!-- Signal waves -->
      <path d="M95,38 Q103,30 103,22" stroke="#003F8A" stroke-width="3.5" fill="none" stroke-linecap="round"/>
      <path d="M100,44 Q112,33 112,18" stroke="#003F8A" stroke-width="3" fill="none" stroke-linecap="round" opacity="0.7"/>
      <path d="M105,50 Q121,36 121,14" stroke="#003F8A" stroke-width="2.5" fill="none" stroke-linecap="round" opacity="0.45"/>
    </svg>
  </div>
  <div class="rh-header-text">
    <h1>RIF<em>Hound</em></h1>
    <p>Recruiting Intelligence Engine — Surfaces layoffs, WARN notices &amp; M&amp;A signals into a recruiter-ready pipeline report.</p>
  </div>
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
# PEERLIST SCRAPER
# ─────────────────────────────────────────

def scrape_peerlist() -> pd.DataFrame:
    """
    Scrapes peerlist.io/layoffs-tracker using Playwright in headless mode.
    Scrolls the virtualized table, stops at entries older than 90 days.
    Returns a deduplicated DataFrame with columns:
        Company, Layoffs, Date, Industry, Location
    Cloud-compatible: uses --no-sandbox and --disable-gpu flags.
    """
    from datetime import date, timedelta
    import re

    cutoff = date.today() - timedelta(days=90)
    rows = []
    seen = set()

    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        st.error("Playwright is not installed. Add 'playwright' to requirements.txt and run 'playwright install chromium'.")
        return pd.DataFrame()

    # Set browser path explicitly for Streamlit Cloud
    os.environ["PLAYWRIGHT_BROWSERS_PATH"] = "/home/adminuser/.cache/ms-playwright"

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-gpu",
                "--disable-dev-shm-usage",
                "--disable-setuid-sandbox",
                "--single-process",
                "--no-zygote",
                "--disable-extensions",
                "--disable-background-networking",
                "--disable-default-apps",
            ],
        )
        page = browser.new_page(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
        )

        try:
            page.goto("https://peerlist.io/layoffs-tracker", wait_until="networkidle", timeout=30000)
            page.wait_for_timeout(2000)

            stop_scraping = False
            last_row_count = 0
            stall_count = 0

            while not stop_scraping:
                # Find all table rows — Peerlist uses tr elements inside a table/tbody
                row_elements = page.query_selector_all("table tbody tr, [role='row']:not([role='columnheader'])")

                for row_el in row_elements:
                    try:
                        cells = row_el.query_selector_all("td, [role='cell']")
                        if len(cells) < 3:
                            continue

                        # Extract text from cells — Peerlist columns: Company | Layoffs | Date | Industry | Location
                        cell_texts = [c.inner_text().strip() for c in cells]

                        company  = cell_texts[0] if len(cell_texts) > 0 else ""
                        layoffs  = cell_texts[1] if len(cell_texts) > 1 else ""
                        date_str = cell_texts[2] if len(cell_texts) > 2 else ""
                        industry = cell_texts[3] if len(cell_texts) > 3 else ""
                        location = cell_texts[4] if len(cell_texts) > 4 else ""

                        # Clean company name
                        company = company.split("\n")[0].strip()
                        if not company or len(company) < 2:
                            continue

                        # Deduplicate
                        company_key = company.lower().strip()
                        if company_key in seen:
                            continue

                        # Parse date — Peerlist uses formats like "Mar 5, 2026" or "2026-03-05"
                        event_date = None
                        for fmt in ["%b %d, %Y", "%B %d, %Y", "%Y-%m-%d", "%d %b %Y", "%m/%d/%Y"]:
                            try:
                                event_date = datetime.strptime(date_str.strip(), fmt).date()
                                break
                            except (ValueError, AttributeError):
                                continue

                        if event_date is None:
                            # Try extracting just a year+month if full date fails
                            match = re.search(r"(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{1,2},?\s+20\d{2}", date_str, re.IGNORECASE)
                            if match:
                                try:
                                    event_date = datetime.strptime(match.group(0).replace(",", ""), "%b %d %Y").date()
                                except ValueError:
                                    pass

                        if event_date is None:
                            continue

                        # Stop condition — date older than 90 days
                        if event_date < cutoff:
                            stop_scraping = True
                            break

                        seen.add(company_key)
                        rows.append({
                            "Date":     event_date.strftime("%Y-%m-%d"),
                            "Company":  company,
                            "Layoffs":  layoffs,
                            "Industry": industry,
                            "Location": location,
                        })

                    except Exception:
                        continue

                if stop_scraping:
                    break

                # Scroll down to load more rows
                page.evaluate("window.scrollBy(0, 800)")
                page.wait_for_timeout(800)

                # Stall detection — stop if no new rows after 5 scrolls
                current_count = len(seen)
                if current_count == last_row_count:
                    stall_count += 1
                    if stall_count >= 5:
                        break
                else:
                    stall_count = 0
                last_row_count = current_count

        except Exception as e:
            st.warning(f"Scraper encountered an issue: {str(e)}")
        finally:
            browser.close()

    if not rows:
        return pd.DataFrame(columns=["Date", "Company", "Layoffs", "Industry", "Location"])

    df = pd.DataFrame(rows)
    df = df.sort_values("Date", ascending=False).reset_index(drop=True)
    return df


# Peerlist scraper UI
st.markdown('<div class="sec-head">Peerlist Layoffs Scraper</div>', unsafe_allow_html=True)

with st.expander("ℹ️ About this scraper", expanded=False):
    st.markdown("""
    <div class="tip-box">
    Scrapes <strong>peerlist.io/layoffs-tracker</strong> in real time using a headless browser.<br>
    Returns all layoff events from the <strong>last 90 days</strong>, deduplicated by company.<br>
    Results are separate from the main RIFHound pipeline and can be downloaded independently.
    </div>
    """, unsafe_allow_html=True)

pl_col_l, pl_col_m, pl_col_r = st.columns([1, 2, 1])
with pl_col_m:
    scrape_btn = st.button("🕷️  Scrape Peerlist", key="scrape_peerlist")

if scrape_btn:
    with st.spinner("Launching headless browser and scraping peerlist.io..."):
        pl_df = scrape_peerlist()

    if pl_df.empty:
        st.info("No results returned. The page structure may have changed or the scraper timed out.")
    else:
        st.success(f"✅ Found **{len(pl_df)} companies** with layoffs in the last 90 days from Peerlist.")

        st.markdown('<div class="sec-head">Peerlist Results</div>', unsafe_allow_html=True)

        # Filters
        pl_f1, pl_f2 = st.columns(2)
        with pl_f1:
            if "Industry" in pl_df.columns and pl_df["Industry"].nunique() > 1:
                ind_filter = st.multiselect("Filter by Industry",
                    options=sorted(pl_df["Industry"].dropna().unique()), placeholder="All industries",
                    key="pl_industry")
            else:
                ind_filter = []
        with pl_f2:
            if "Location" in pl_df.columns and pl_df["Location"].nunique() > 1:
                loc_filter = st.multiselect("Filter by Location",
                    options=sorted(pl_df["Location"].dropna().unique()), placeholder="All locations",
                    key="pl_location")
            else:
                loc_filter = []

        pl_filtered = pl_df.copy()
        if ind_filter: pl_filtered = pl_filtered[pl_filtered["Industry"].isin(ind_filter)]
        if loc_filter: pl_filtered = pl_filtered[pl_filtered["Location"].isin(loc_filter)]

        st.dataframe(pl_filtered, use_container_width=True, hide_index=True, height=380)
        st.caption(f"Showing {len(pl_filtered)} of {len(pl_df)} companies — last 90 days")

        st.download_button(
            "📥 Download Peerlist Results (CSV)",
            data=pl_filtered.to_csv(index=False).encode("utf-8"),
            file_name=f"peerlist_layoffs_{datetime.today().strftime('%Y%m%d')}.csv",
            mime="text/csv",
        )

st.markdown("---")

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
                     "Headcount": r.headcount or "—",
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
    st.markdown("""
    <style>
    .how-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 1rem; margin-bottom: 1.5rem; }
    .how-card {
        background: #0D1B2A;
        border: 1px solid #0F2035;
        border-radius: 10px;
        padding: 1.4rem 1.6rem;
    }
    .how-card-title {
        font-family: 'Bebas Neue', sans-serif;
        font-size: 1rem;
        letter-spacing: 2px;
        color: #1A6EC4;
        margin-bottom: 0.75rem;
        display: flex;
        align-items: center;
        gap: 0.5rem;
    }
    .how-card ul {
        margin: 0;
        padding-left: 1.1rem;
        list-style: none;
    }
    .how-card ul li {
        color: #8899AA;
        font-size: 0.85rem;
        line-height: 1.7;
        padding: 0.1rem 0;
        position: relative;
        padding-left: 1rem;
    }
    .how-card ul li::before {
        content: '—';
        position: absolute;
        left: 0;
        color: #003F8A;
        font-weight: 700;
    }
    .how-card ul li strong { color: #C8D8E8; }
    .setup-box {
        background: #0D1B2A;
        border: 1px solid #0F2035;
        border-left: 3px solid #003F8A;
        border-radius: 10px;
        padding: 1.4rem 1.8rem;
        margin-top: 0.5rem;
    }
    .setup-box-title {
        font-family: 'Bebas Neue', sans-serif;
        font-size: 1rem;
        letter-spacing: 2px;
        color: #1A6EC4;
        margin-bottom: 1rem;
    }
    .setup-steps {
        display: grid;
        grid-template-columns: repeat(4, 1fr);
        gap: 1rem;
    }
    .setup-step {
        display: flex;
        flex-direction: column;
        gap: 0.4rem;
    }
    .step-num {
        font-family: 'Bebas Neue', sans-serif;
        font-size: 1.8rem;
        color: #003F8A;
        line-height: 1;
        opacity: 0.6;
    }
    .step-label {
        font-size: 0.78rem;
        font-weight: 700;
        color: #C8D8E8;
        text-transform: uppercase;
        letter-spacing: 0.8px;
    }
    .step-desc {
        font-size: 0.8rem;
        color: #8899AA;
        line-height: 1.5;
    }
    .step-desc a { color: #1A6EC4; text-decoration: none; }
    </style>

    <div class="sec-head" style="font-family:'Bebas Neue',sans-serif;font-size:0.95rem;letter-spacing:3px;color:#555;border-bottom:1px solid #0F2035;padding-bottom:0.4rem;margin:0 0 1.2rem">
        How It Works
    </div>

    <div class="how-grid">

      <div class="how-card">
        <div class="how-card-title">📡 Data Sources</div>
        <ul>
          <li><strong>WARN Act Notices</strong> — Federal law requires 60-day advance notice before mass layoffs. RIFHound pulls all 50 states daily via WARNFirehose API.</li>
          <li><strong>SEC 8-K Item 2.05 Filings</strong> — Confirmed restructuring charges filed with the SEC. The strongest corporate signal of an impending layoff.</li>
          <li><strong>M&amp;A News Scanner</strong> — Tavily searches in real time for layoff, merger, and restructuring announcements — often surfaces signals before WARN notices are even filed.</li>
          <li><strong>Layoffs.FYI CSV</strong> — Upload the free 90-day export once. RIFHound saves it automatically and reminds you when it needs refreshing.</li>
        </ul>
      </div>

      <div class="how-card">
        <div class="how-card-title">📋 What You Get</div>
        <ul>
          <li><strong>Talent Availability Report</strong> — Every company with an active layoff signal, sorted by date with source, location, and headcount.</li>
          <li><strong>Target Group Mapping</strong> — RIFHound auto-classifies affected roles (Software Engineering, Sales, Field Ops, etc.) so you know who to recruit.</li>
          <li><strong>LinkedIn Boolean String</strong> — Ready-to-paste Current Company search string. Drop it directly into LinkedIn Recruiter and start sourcing.</li>
          <li><strong>CSV Export</strong> — Full report and filtered view, both downloadable for pipeline tracking or sharing with your team.</li>
        </ul>
      </div>

    </div>

    <div class="setup-box">
      <div class="setup-box-title">Quick Start Guide</div>
      <div class="setup-steps">
        <div class="setup-step">
          <div class="step-num">01</div>
          <div class="step-label">Get API Keys</div>
          <div class="step-desc">Sign up free at <a href="https://warnfirehose.com/account" target="_blank">warnfirehose.com</a> and <a href="https://app.tavily.com" target="_blank">app.tavily.com</a>. No credit card required.</div>
        </div>
        <div class="setup-step">
          <div class="step-num">02</div>
          <div class="step-label">Enter Keys</div>
          <div class="step-desc">Paste both keys into the sidebar. They save automatically — you only do this once.</div>
        </div>
        <div class="setup-step">
          <div class="step-num">03</div>
          <div class="step-label">Upload CSV (Optional)</div>
          <div class="step-desc">Download the free 90-day CSV from <a href="https://layoffs.fyi" target="_blank">layoffs.fyi</a> and upload it for additional coverage.</div>
        </div>
        <div class="setup-step">
          <div class="step-num">04</div>
          <div class="step-label">Run &amp; Export</div>
          <div class="step-desc">Hit Run RIFHound. Filter results by role group, download your report, and paste the Boolean string into LinkedIn Recruiter.</div>
        </div>
      </div>
    </div>
    """, unsafe_allow_html=True)
