# rifhound_core.py
# RIFHound – Recruiting Intelligence Engine v2
# Data sources:
#   - WARNFirehose API  → WARN Act notices (all 50 states) + SEC 8-K filings
#   - Tavily Search API → News signals (M&A, restructuring, layoffs)
#   - Optional CSV upload → Layoffs.FYI manual export

import csv
import io
import requests
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import List, Optional, Callable

# =========================
# CONFIG
# =========================
DAYS_BACK = 90
TODAY = datetime.now(timezone.utc).date()
CUTOFF_DATE = TODAY - timedelta(days=DAYS_BACK)

WARNFIREHOSE_BASE = "https://warnfirehose.com/api"
TAVILY_BASE = "https://api.tavily.com"

IMMUNE_KEYWORDS = {"kastle", "kastle systems"}
RETAIL_KEYWORDS = {"cashier", "store associate", "hourly retail", "fast food", "restaurant"}

# =========================
# DATA MODEL
# =========================
@dataclass
class EventRecord:
    date: datetime
    company: str
    location: Optional[str]
    target_group: Optional[str]
    target_roles: Optional[str]
    pitch_angle: str
    reason: str
    headcount: Optional[str]
    source: str
    raw_text: Optional[str] = field(default=None, repr=False)

    def to_row(self) -> List[str]:
        return [
            self.date.strftime("%Y-%m-%d"),
            self.company,
            self.location or "",
            self.target_group or "Review Needed",
            self.target_roles or "",
            self.pitch_angle,
            self.reason,
            self.headcount or "",
            self.source,
        ]

# =========================
# MATCHING & PITCH LOGIC
# =========================
def map_target_group(text: str) -> Optional[str]:
    t = text.lower()
    # Explicit role titles checked first — most specific wins
    if any(k in t for k in ["software engineer", "swe", "full stack", "backend engineer", "frontend engineer"]):
        return "Software Engineering"
    if any(k in t for k in ["sales engineer", "solutions engineer", "pre-sales", "design engineer"]):
        return "Sales Engineering"
    if any(k in t for k in ["project manager", "program manager", "pmp", "construction pm"]):
        return "Project Management"
    if any(k in t for k in ["account executive", "enterprise sales", "proptech", "b2b saas", "hunter"]):
        return "Sales (Enterprise)"
    if any(k in t for k in ["recruiter", "talent acquisition", "hr manager", "people ops"]):
        return "HR / Talent"
    if any(k in t for k in ["technician", "installer", "low voltage", "fiber", "cabling", "field tech"]):
        return "Field Operations"
    if any(k in t for k in ["firmware", "embedded", "iot", "semiconductor", "robotics"]):
        return "Embedded Engineering"
    # Broader tech signals — checked after explicit titles
    if any(k in t for k in ["computer vision", "video ai", "opencv", "ml engineer", "c++", ".net", "azure", "backend", "cloud"]):
        return "Software Engineering"
    if any(k in t for k in ["python", "machine learning", "ai engineer", "deep learning"]):
        return "Software Engineering"
    return None

def build_pitch(source: str, reason: str, raw: str = "") -> str:
    combined = (reason + " " + raw).lower()
    if source == "SEC_8K":
        return "SEC 8-K Item 2.05 filed — confirmed restructuring, candidates likely active soon"
    if source == "WARN":
        return "WARN notice filed — federal law requires 60-day advance notice, reach out now before they start searching"
    if "merger" in combined or "acqui" in combined:
        return "M&A activity creates role redundancy — strong window to recruit before integration"
    if "bankrupt" in combined or "chapter 11" in combined:
        return "Company instability — candidates urgently seeking new roles"
    if "restructur" in combined or "reorg" in combined:
        return "Restructuring underway — uncertainty drives top performers to look elsewhere"
    if "layoff" in combined or "reduction" in combined or "rif" in combined:
        return "Confirmed layoff — candidates are active and available immediately"
    return "Organizational change creates candidate availability window"

def is_immune(company: str) -> bool:
    return any(k in company.lower() for k in IMMUNE_KEYWORDS)

def is_retail(text: str) -> bool:
    return any(k in (text or "").lower() for k in RETAIL_KEYWORDS)

def in_window(date: datetime) -> bool:
    return date.date() >= CUTOFF_DATE

# =========================
# SOURCE 1: WARNFIREHOSE — WARN NOTICES
# =========================
def fetch_warn_notices(api_key: str) -> List[EventRecord]:
    """
    Pulls WARN Act notices from all 50 states via WARNFirehose API.
    Free tier: 50 calls/day. Each call returns up to 100 records.
    Docs: https://warnfirehose.com/developers
    """
    records = []
    if not api_key or api_key.strip() == "YOUR_WARNFIREHOSE_KEY":
        return records

    date_from = CUTOFF_DATE.strftime("%Y-%m-%d")
    url = f"{WARNFIREHOSE_BASE}/records"
    params = {
        "date_from": date_from,
        "limit": 500,
        "offset": 0,
    }
    headers = {"X-API-Key": api_key.strip()}

    try:
        resp = requests.get(url, params=params, headers=headers, timeout=20)
        resp.raise_for_status()
        data = resp.json()

        # WARNFirehose returns { records: [...], total: N }
        items = data.get("records") or data.get("data") or []
        if isinstance(data, list):
            items = data

        for item in items:
            company = (item.get("company_name") or item.get("employer") or "").strip()
            if not company or is_immune(company):
                continue

            date_str = item.get("notice_date") or item.get("date") or item.get("effective_date") or ""
            try:
                event_date = datetime.strptime(date_str[:10], "%Y-%m-%d")
            except (ValueError, TypeError):
                event_date = datetime.now(timezone.utc)

            if not in_window(event_date):
                continue

            location_parts = [
                item.get("city", ""),
                item.get("state", ""),
            ]
            location = ", ".join(p for p in location_parts if p) or None
            headcount = str(item.get("employees_affected") or item.get("num_workers") or "")
            raw = f"{company} {location or ''} layoff warn"

            if is_retail(raw):
                continue

            records.append(EventRecord(
                date=event_date,
                company=company,
                location=location,
                target_group=map_target_group(raw),
                target_roles=None,
                pitch_angle=build_pitch("WARN", "WARN notice filed", raw),
                reason=f"WARN Act notice — {item.get('state', 'US')}",
                headcount=headcount or None,
                source="WARN",
                raw_text=raw,
            ))

    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 401:
            print("[RIFHound] WARN: Invalid API key — check your WARNFirehose key")
        elif e.response.status_code == 429:
            print("[RIFHound] WARN: Rate limit hit — free tier is 50 calls/day")
        else:
            print(f"[RIFHound] WARN API error: {e}")
    except Exception as e:
        print(f"[RIFHound] WARN fetch error: {e}")

    return records

# =========================
# SOURCE 2: WARNFIREHOSE — SEC 8-K FILINGS
# =========================
def fetch_sec_filings(api_key: str) -> List[EventRecord]:
    """
    Pulls SEC 8-K Item 2.05 filings (restructuring/workforce reductions)
    from WARNFirehose. Item 2.05 = "Departure of Directors or Certain Officers"
    / restructuring charges — the most reliable public signal of layoffs.
    """
    records = []
    if not api_key or api_key.strip() == "YOUR_WARNFIREHOSE_KEY":
        return records

    date_from = CUTOFF_DATE.strftime("%Y-%m-%d")
    url = f"{WARNFIREHOSE_BASE}/sec-filings"
    params = {
        "items": "2.05",
        "start": date_from,
        "limit": 200,
    }
    headers = {"X-API-Key": api_key.strip()}

    try:
        resp = requests.get(url, params=params, headers=headers, timeout=20)
        resp.raise_for_status()
        data = resp.json()

        items = data.get("filings") or data.get("records") or data.get("data") or []
        if isinstance(data, list):
            items = data

        for item in items:
            company = (item.get("company_name") or item.get("company") or "").strip()
            if not company or is_immune(company):
                continue

            date_str = item.get("filing_date") or item.get("date") or ""
            try:
                event_date = datetime.strptime(date_str[:10], "%Y-%m-%d")
            except (ValueError, TypeError):
                event_date = datetime.now(timezone.utc)

            if not in_window(event_date):
                continue

            ticker = item.get("ticker", "")
            raw = f"{company} {ticker} restructuring workforce reduction SEC filing"

            if is_retail(raw):
                continue

            records.append(EventRecord(
                date=event_date,
                company=company,
                location=None,
                target_group=map_target_group(raw),
                target_roles=None,
                pitch_angle=build_pitch("SEC_8K", "SEC 8-K Item 2.05", raw),
                reason=f"SEC 8-K Item 2.05 filed{' (' + ticker + ')' if ticker else ''}",
                headcount=None,
                source="SEC_8K",
                raw_text=raw,
            ))

    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 401:
            print("[RIFHound] SEC: Invalid API key")
        elif e.response.status_code == 429:
            print("[RIFHound] SEC: Rate limit hit")
        else:
            print(f"[RIFHound] SEC API error: {e}")
    except Exception as e:
        print(f"[RIFHound] SEC fetch error: {e}")

    return records

# =========================
# SOURCE 3: TAVILY — NEWS SIGNALS
# =========================
def fetch_news_signals(tavily_key: str) -> List[EventRecord]:
    """
    Uses Tavily Search API to find recent M&A, restructuring, and layoff news.
    Tavily returns clean, structured search results — no HTML scraping needed.
    Docs: https://docs.tavily.com
    """
    records = []
    if not tavily_key or tavily_key.strip() == "YOUR_TAVILY_KEY":
        return records

    queries = [
        "tech company layoffs 2025 2026",
        "corporate restructuring workforce reduction announcement",
        "company acquisition merger employee redundancy",
        "startup layoffs funding cuts employees",
    ]

    headers = {"Content-Type": "application/json"}
    url = f"{TAVILY_BASE}/search"
    seen_companies = set()

    for query in queries:
        try:
            payload = {
                "api_key": tavily_key.strip(),
                "query": query,
                "search_depth": "basic",
                "max_results": 10,
                "include_answer": False,
                "include_raw_content": False,
            }

            resp = requests.post(url, json=payload, headers=headers, timeout=20)
            resp.raise_for_status()
            data = resp.json()

            results = data.get("results") or []

            for result in results:
                title = result.get("title") or ""
                content = result.get("content") or ""
                published = result.get("published_date") or ""
                full_text = f"{title} {content}"

                # Extract company name — look for capitalized proper nouns before action words
                import re
                company_match = re.search(
                    r'\b([A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+){0,3})\s+(?:lays off|laid off|cuts|reduces|acquires|merges|files for|announces layoff)',
                    title
                )
                if not company_match:
                    continue

                company = company_match.group(1).strip()

                # Filter noise
                skip_words = {"The", "A", "An", "This", "That", "How", "Why", "When", "Where", "Tech", "New"}
                if company in skip_words or len(company) < 3:
                    continue

                if is_immune(company):
                    continue

                company_key = company.lower()
                if company_key in seen_companies:
                    continue
                seen_companies.add(company_key)

                # Parse date
                try:
                    event_date = datetime.strptime(published[:10], "%Y-%m-%d")
                except (ValueError, TypeError):
                    event_date = datetime.now(timezone.utc)

                if not in_window(event_date):
                    continue

                if is_retail(full_text):
                    continue

                records.append(EventRecord(
                    date=event_date,
                    company=company,
                    location=None,
                    target_group=map_target_group(full_text),
                    target_roles=None,
                    pitch_angle=build_pitch("NEWS", title, content),
                    reason=f"News signal: {title[:100]}",
                    headcount=None,
                    source="NEWS",
                    raw_text=full_text[:300],
                ))

        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 401:
                print("[RIFHound] Tavily: Invalid API key")
                break
            elif e.response.status_code == 429:
                print("[RIFHound] Tavily: Rate limit hit")
                break
            else:
                print(f"[RIFHound] Tavily error: {e}")
        except Exception as e:
            print(f"[RIFHound] News fetch error: {e}")

    return records

# =========================
# SOURCE 4: CSV UPLOAD (Layoffs.FYI)
# =========================
def parse_uploaded_csv(content: str) -> List[EventRecord]:
    """
    Parses a CSV exported from Layoffs.FYI.
    Download at: https://layoffs.fyi (click Export / CSV)
    Accepts any CSV with Company and Date columns.
    """
    records = []
    try:
        reader = csv.DictReader(io.StringIO(content))
        # Normalize column names
        rows = list(reader)
        if not rows:
            return records

        # Detect column names flexibly
        sample = rows[0]
        keys = {k.lower().strip(): k for k in sample.keys()}

        def get(row, *options):
            for opt in options:
                if opt in keys:
                    return (row.get(keys[opt]) or "").strip()
            return ""

        for row in rows:
            company = get(row, "company", "company_name", "employer")
            if not company or is_immune(company):
                continue

            date_str = get(row, "date", "date_added", "notice_date", "event_date")
            try:
                event_date = datetime.strptime(date_str[:10], "%Y-%m-%d")
            except (ValueError, TypeError):
                try:
                    event_date = datetime.strptime(date_str, "%m/%d/%Y")
                except (ValueError, TypeError):
                    event_date = datetime.now(timezone.utc)

            if not in_window(event_date):
                continue

            location = get(row, "location", "hq_location", "city", "state")
            headcount = get(row, "laid_off_count", "employees", "num_workers", "headcount", "affected")
            industry = get(row, "industry", "sector")
            stage = get(row, "stage", "funding_stage")
            raw = f"{company} {location} {industry} {stage}".strip()

            if is_retail(raw):
                continue

            records.append(EventRecord(
                date=event_date,
                company=company,
                location=location or None,
                target_group=map_target_group(raw),
                target_roles=None,
                pitch_angle=build_pitch("CSV", "Layoffs.FYI confirmed layoff", raw),
                reason=f"Layoffs.FYI{' — ' + industry if industry else ''}",
                headcount=headcount or None,
                source="LAYOFFS_FYI",
                raw_text=raw,
            ))

    except Exception as e:
        print(f"[RIFHound] CSV parse error: {e}")

    return records

# =========================
# DEDUPLICATION
# =========================
def deduplicate(records: List[EventRecord]) -> List[EventRecord]:
    """
    Keeps one record per company. Priority order:
    WARN > SEC_8K > LAYOFFS_FYI > NEWS
    (Most authoritative source wins)
    """
    source_priority = {"WARN": 0, "SEC_8K": 1, "LAYOFFS_FYI": 2, "NEWS": 3}
    best: dict = {}

    for r in records:
        key = r.company.lower().strip()
        if key not in best:
            best[key] = r
        else:
            existing_priority = source_priority.get(best[key].source, 99)
            new_priority = source_priority.get(r.source, 99)
            if new_priority < existing_priority:
                best[key] = r

    return list(best.values())

# =========================
# BOOLEAN STRING GENERATOR
# =========================
def generate_boolean_string(records: List[EventRecord]) -> str:
    if not records:
        return ""

    names = []
    for r in records:
        name = r.company.strip()
        if name and len(name) > 2:
            names.append(f'"{name}"')

    if not names:
        return ""

    # Split into chunks of 40 (LinkedIn character limit safety)
    chunk_size = 40
    chunks = []
    for i in range(0, len(names), chunk_size):
        chunk = names[i:i + chunk_size]
        chunks.append("(" + " OR ".join(chunk) + ")")

    lines = [
        "📋 LinkedIn Recruiter — Current Company Boolean String",
        "Paste into the 'Current Company' field. Set filter to 'Current'.",
        "",
    ]
    if len(chunks) == 1:
        lines.append(chunks[0])
    else:
        for i, chunk in enumerate(chunks, 1):
            lines.append(f"--- String {i} of {len(chunks)} ---")
            lines.append(chunk)
            lines.append("")

    return "\n".join(lines)

# =========================
# CSV EXPORT
# =========================
def to_csv_bytes(records: List[EventRecord]) -> bytes:
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "Date", "Company", "Location", "Target Group",
        "Target Roles", "Pitch Angle", "Reason",
        "Headcount Affected", "Source"
    ])
    for r in records:
        writer.writerow(r.to_row())
    return output.getvalue().encode("utf-8")

# =========================
# MAIN PIPELINE
# =========================
def run_pipeline(
    warnfirehose_key: str = "",
    tavily_key: str = "",
    uploaded_csv: Optional[str] = None,
    include_warn: bool = True,
    include_sec: bool = True,
    include_news: bool = True,
    progress_callback: Optional[Callable[[str, int], None]] = None,
) -> dict:
    """
    Main entry point for RIFHound.

    Args:
        warnfirehose_key: API key from warnfirehose.com (free at /account)
        tavily_key:        API key from tavily.com (free tier available)
        uploaded_csv:      Optional CSV string from Layoffs.FYI export
        include_warn:      Fetch WARN notices
        include_sec:       Fetch SEC 8-K Item 2.05 filings
        include_news:      Fetch news signals via Tavily
        progress_callback: Optional fn(message, percent) for UI progress

    Returns dict with:
        records       List[EventRecord]
        csv_bytes     bytes
        boolean_str   str
        source_counts dict
        total         int
        errors        list of any error messages
    """
    all_records: List[EventRecord] = []
    errors = []

    def update(msg: str, pct: int):
        if progress_callback:
            progress_callback(msg, pct)

    # Step 1: CSV upload
    if uploaded_csv:
        update("📁 Processing uploaded Layoffs.FYI file...", 10)
        csv_records = parse_uploaded_csv(uploaded_csv)
        all_records.extend(csv_records)
        update(f"📁 Found {len(csv_records)} records from uploaded file", 20)

    # Step 2: WARN notices
    if include_warn and warnfirehose_key:
        update("🔴 Fetching WARN Act notices (all 50 states)...", 30)
        warn_records = fetch_warn_notices(warnfirehose_key)
        all_records.extend(warn_records)
        update(f"🔴 Found {len(warn_records)} WARN notices", 45)
    elif include_warn and not warnfirehose_key:
        errors.append("WARN notices skipped — WARNFirehose API key not provided")

    # Step 3: SEC 8-K filings
    if include_sec and warnfirehose_key:
        update("📑 Fetching SEC 8-K restructuring filings...", 55)
        sec_records = fetch_sec_filings(warnfirehose_key)
        all_records.extend(sec_records)
        update(f"📑 Found {len(sec_records)} SEC filings", 65)
    elif include_sec and not warnfirehose_key:
        errors.append("SEC filings skipped — WARNFirehose API key not provided")

    # Step 4: News signals
    if include_news and tavily_key:
        update("🔵 Scanning news for M&A and layoff signals...", 70)
        news_records = fetch_news_signals(tavily_key)
        all_records.extend(news_records)
        update(f"🔵 Found {len(news_records)} news signals", 82)
    elif include_news and not tavily_key:
        errors.append("News scan skipped — Tavily API key not provided")

    # Step 5: Deduplicate + sort
    update("✨ Deduplicating and sorting results...", 88)
    final = deduplicate(all_records)
    final.sort(key=lambda r: r.date, reverse=True)

    # Step 6: Counts
    source_counts = {}
    for r in final:
        source_counts[r.source] = source_counts.get(r.source, 0) + 1

    update("✅ Done!", 100)

    return {
        "records": final,
        "csv_bytes": to_csv_bytes(final),
        "boolean_str": generate_boolean_string(final),
        "source_counts": source_counts,
        "total": len(final),
        "errors": errors,
    }
