# 🐾 RIFHound v2 — Recruiting Intelligence Engine

Surfaces layoffs, WARN notices, SEC filings, and M&A signals into a 
recruiter-ready pipeline report with LinkedIn Boolean strings.

---

## Data Sources

| Source | Provider | Cost | What it gives you |
|--------|----------|------|-------------------|
| WARN Act Notices | WARNFirehose API | Free (50 calls/day) | All 50 states, updated daily, 60-day advance notice |
| SEC 8-K Filings | WARNFirehose API | Free (same key) | Item 2.05 = confirmed restructuring filings |
| M&A / News | Tavily API | Free tier available | Real-time layoff and M&A news signals |
| Layoffs.FYI | Manual CSV upload | Free | Community-sourced tech layoff tracker |

No scraping. No IP concerns. All legitimate APIs.

---

## Setup (5 Minutes)

### 1. Get your free API keys

**WARNFirehose** (covers WARN + SEC):
- Go to https://warnfirehose.com/account
- Sign up and copy your API key
- Free tier: 50 calls/day, no credit card required

**Tavily** (news scanner):
- Go to https://app.tavily.com
- Sign up and copy your API key
- Free tier available

### 2. Install and run

```bash
# Install dependencies
pip install -r requirements.txt

# Run the app
streamlit run app.py
```

The app opens automatically at http://localhost:8501

### 3. Add your keys in the sidebar

Paste your WARNFirehose and Tavily keys into the sidebar fields.
Keys are never stored — enter them each session or hardcode them in a .env file.

---

## Optional: Layoffs.FYI CSV

1. Go to https://layoffs.fyi
2. Enter your email when prompted
3. Download the CSV (last 90 days, up to 500 rows — free)
4. Upload it in the RIFHound sidebar

RIFHound merges it with API data and removes duplicates automatically.

---

## Deploying Online (Streamlit Cloud — Free)

1. Create account at https://streamlit.io/cloud
2. Push this folder to a private GitHub repo
3. Connect to Streamlit Cloud and deploy
4. Share the URL — buyers just enter their own API keys

Total hosting cost: $0/month on free tier.

---

## File Structure

```
rifhound/
├── rifhound_core.py   # Engine — all data fetching, processing, output
├── app.py             # Streamlit web UI
├── requirements.txt   # Dependencies (3 packages)
└── README.md          # This file
```

---

## No IP Concerns

- WARNFirehose: Licensed API, terms allow commercial use
- Tavily: Licensed API, terms allow commercial use  
- Layoffs.FYI: User manually downloads their own free export
- SEC EDGAR: Public government data
- WARN Act notices: Public government records

---

*RIFHound is a private tool. Not for redistribution without permission.*
