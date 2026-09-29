#!/usr/bin/env python3
"""
Tarheel Vendor & Industry Watch — standalone edition.

Pulls Google News RSS feeds for every company on the watchlist (plus a few
industry-wide queries), keeps only structural changes (mergers, acquisitions,
closures, openings, bankruptcies, ownership changes, supply disruptions),
and regenerates dashboard.html with the results baked in.

No AI, no API keys, no cost. Uses only the Python standard library (3.8+).

Usage:
    python vendor_watch.py

Files it manages (all in the same folder as this script):
    config.json      — watchlist + settings (created with defaults on first run; edit freely)
    watch_data.json  — saved findings and run history (don't edit by hand)
    dashboard.html   — the dashboard; open it or share it on a network drive
"""

import json
import os
import sys
import time
import urllib.parse
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from html import unescape
import re

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(SCRIPT_DIR, "config.json")
DATA_PATH = os.path.join(SCRIPT_DIR, "watch_data.json")

DEFAULT_CONFIG = {
    "watchlist": [
        {"name": "Sigma Stretch Film", "category": "packaging"},
        {"name": "Intertape Polymer Group", "category": "packaging"},
        {"name": "Marcal", "category": "janitorial"},
        {"name": "Inteplast Group", "category": "packaging"},
        {"name": "Avery Dennison", "category": "packaging"},
        {"name": "Berry Global", "category": "packaging"},
        {"name": "Cousins Packaging", "category": "packaging"},
        {"name": "Crown Matting Technologies", "category": "janitorial"},
        {"name": "DuBose Strapping", "category": "packaging"},
        {"name": "Encore Label", "category": "packaging"},
        {"name": "EnvirOx", "category": "janitorial"},
        {"name": "Fromm Packaging", "category": "packaging"},
        {"name": "GOJO Industries", "category": "janitorial"},
        {"name": "Gordon Paper Company", "category": "packaging"},
        {"name": "Georgia-Pacific", "category": "packaging"},
        {"name": "Henry Molded Products", "category": "packaging"},
        {"name": "Highlight Industries", "category": "packaging"},
        {"name": "Hospeco Brands", "category": "janitorial"},
        {"name": "Karcher", "category": "janitorial"},
        {"name": "Great Northern Laminations", "category": "packaging"},
        {"name": "MCR Safety", "category": "safety"},
        {"name": "National Chemical Laboratories", "category": "janitorial"},
        {"name": "PAC Strapping", "category": "packaging"},
        {"name": "Pregis", "category": "packaging"},
        {"name": "Radians", "category": "safety"},
        {"name": "SC Johnson Professional", "category": "janitorial"},
        {"name": "Sealed Air", "category": "packaging"},
        {"name": "Solaris Paper", "category": "janitorial"},
        {"name": "SpillTech", "category": "safety"},
        {"name": "Storopack", "category": "packaging"},
        {"name": "Christeyns", "category": "janitorial"},
        {"name": "Vanguard Safety", "category": "safety"},
        {"name": "ABCO Cleaning Products", "category": "janitorial"},
        {"name": "Automated Solutions LLC", "category": "packaging"}
    ],
    "competitors": [
        "Imperial Dade", "Veritiv", "Bunzl Distribution",
        "SouthEastern Paper Group"
    ],
    "industry_queries": [
        "packaging manufacturer merger OR acquisition OR \"plant closure\"",
        "janitorial supplies company acquisition OR bankruptcy OR closure",
        "safety products PPE manufacturer acquisition OR \"new plant\" OR closure",
        "corrugated OR \"stretch film\" plant closing OR opening OR expansion"
    ],
    "commodity_series": [
        {"id": "WPU0662", "label": "Plastic Resins (PPI)", "unit": "index"},
        {"id": "WPU0912", "label": "Paper (PPI)", "unit": "index"},
        {"id": "WPU0913", "label": "Paperboard (PPI)", "unit": "index"},
        {"id": "APU000074717", "label": "Diesel, US average", "unit": "$/gal"}
    ],
    "regulatory_queries": [
        {"term": "\"personal protective equipment\"",
         "agencies": ["occupational-safety-and-health-administration"]},
        {"term": "disinfectant",
         "agencies": ["environmental-protection-agency"]},
        {"term": "packaging",
         "agencies": ["environmental-protection-agency", "food-and-drug-administration"]}
    ],
    "regulatory_title_terms": [
        "packag", "protective equipment", "ppe", "disinfect", "sanitiz",
        "antimicrobial", "pesticide", "respirator", "glove", "hazardous materials",
        "recycl", "plastic", "container", "hazard communication"
    ],
    "first_run_lookback_days": 90,
    "overlap_days": 7,
    "max_items": 250,
    "request_delay_seconds": 1.5,
    "bls_api_key": "",
    "blocked_sources": ["AD HOC NEWS"],
    "stale_after_days": 3,
    "output_file": "dashboard.html"
}

# Terms appended to every vendor query so the feed itself is pre-filtered.
STRUCTURAL_TERMS = ('(merger OR acquisition OR acquires OR bankruptcy OR "chapter 11" '
                    'OR closure OR "shuts down" OR "new plant" OR "new facility" '
                    'OR "distribution center" OR restructuring OR divestiture OR expansion)')

# Ordered classification rules — first match wins. A headline that matches
# nothing here is discarded (that's the structural-changes-only filter).
# Each pattern is a regular expression matched at word starts, so "strike"
# no longer matches "strikes a deal" and "closing" no longer matches "enclosing".
TYPE_RULES = [
    ("bankruptcy", [r"bankrupt", r"chapter (?:11|7)\b", r"insolven", r"receivership",
                    r"liquidat"]),
    ("merger",     [r"merger\b", r"merges\b", r"to merge\b", r"merging\b"]),
    ("acquisition", [r"acquisition", r"acquir", r"takeover\b", r"to buy\b", r"buys\b",
                     r"purchase of\b", r"purchases\b"]),
    ("ownership",  [r"private equity", r"majority stake", r"minority stake", r"sells stake",
                    r"new owner", r"ownership change", r"investment from", r"divest"]),
    ("closure",    [r"closing\b(?! (?:of|on) (?:the )?(?:deal|acquisition|sale|transaction))",
                    r"closure", r"shuts down", r"shutting down", r"to close\b(?! (?:the )?deal)",
                    r"closes\b(?! (?:acquisition|deal|sale|purchase))", r"winds down",
                    r"ceases operations", r"shutter", r"layoffs?\b"]),
    ("opening",    [r"opens (?:a|an|its|new|second|third|first)\b", r"new plant", r"new facility", r"new distribution center",
                    r"new warehouse", r"grand opening", r"breaks ground", r"groundbreaking",
                    r"relocat", r"new headquarters", r"__EXPANSION__"]),
    ("supply",     [r"shortage", r"supply disruption", r"strike\b", r"force majeure",
                    r"price increase", r"tariffs?\b", r"recall", r"fire at\b",
                    r"explosion at\b"]),
]
TYPE_REGEX = [(name, re.compile("|".join(r"\b" + p for p in pats if p != "__EXPANSION__"),
                                re.I))
              for name, pats in TYPE_RULES]

# "Expands" / "expansion" only counts as an opening when a physical site is
# involved — "expands product line" is exactly the noise we don't want.
EXPANSION_RE = re.compile(r"\bexpan(?:d|ds|ded|sion|ding)\b", re.I)
FACILITY_RE = re.compile(r"\b(?:plant|facility|facilities|warehouse|distribution center|"
                         r"\bdc\b|mill|factory|site|campus|headquarters|capacity|"
                         r"location|branch|footprint)", re.I)

# Headlines containing these are market commentary, not structural news — skip them.
NOISE_PHRASES = ["stock hold", "stock rise", "stock fall", "stock jump", "stock slip",
                 "stock analysis", "shares rise", "shares fall", "shares jump",
                 "price target", "analyst", "investors eye", "dividend",
                 "earnings preview", "earnings call", "how to invest",
                 "investigation notice", "investor alert", "class action",
                 "law firm", "shareholder", "lawsuit",
                 "number of employees", "employee count", "net worth", "revenue and",
                 "stock gains", "stock draws", "stock delisted", "stock soars",
                 "stock drops", "shares climb", "shares slide",
                 # roundups mention many companies; the matched deal is usually someone else's
                 "pulse:", "roundup", "round-up", "in brief", "news briefs",
                 "week in review", "recap", "this week in"]

# Industry-wide items must mention at least one of these to count as relevant.
CATEGORY_TERMS = ["packag", "corrugat", "stretch film", "shrink film", "janitorial",
                  "sanitat", "cleaning", "hygiene", "ppe", "safety suppl",
                  "safety product", "glove", "tissue", "paper", "label", "tape",
                  "adhesive", "foam", "strapping", "mailer", "void fill", "liner",
                  "towel", "chemical", "disinfect"]

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) TarheelVendorWatch/1.0"

BLS_URL = "https://api.bls.gov/publicAPI/v1/timeseries/data/"
FEDREG_URL = "https://www.federalregister.gov/api/v1/documents.json"
AGENCY_ABBREV = {
    "Environmental Protection Agency": "EPA",
    "Occupational Safety and Health Administration": "OSHA",
    "Food and Drug Administration": "FDA",
    "Consumer Product Safety Commission": "CPSC",
    "Department of Transportation": "DOT",
    "Department of Labor": "DOL",
    "Health and Human Services Department": "HHS",
}


def vendor_pair(v):
    """Accept a watchlist entry as either a plain string or {name, category}."""
    if isinstance(v, dict):
        return (v.get("name") or "").strip(), (v.get("category") or "other").lower()
    return str(v).strip(), "other"


# ---------------------------------------------------------------- helpers ----

def load_json(path, fallback):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return fallback


def atomic_write(path, text):
    """Write to a temp file, then swap it in, so a crash or someone opening the
    file mid-write never sees a half-written dashboard or corrupts saved data."""
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(text)
    os.replace(tmp, path)


def save_json(path, obj):
    atomic_write(path, json.dumps(obj, indent=2, ensure_ascii=False))


def strip_tags(text):
    return unescape(re.sub(r"<[^>]+>", " ", text or ""))


def norm_key(title):
    return re.sub(r"[^a-z0-9]", "", (title or "").lower())[:80]


def classify(text):
    for type_name, rx in TYPE_REGEX:
        if rx.search(text):
            return type_name
    if EXPANSION_RE.search(text) and FACILITY_RE.search(text):
        return "opening"
    return None


def fetch_feed(query):
    """Fetch a Google News RSS feed for a search query. Returns a list of entries.

    Google briefly rate-limits bursts of requests (HTTP 429/503); those are
    retried with a growing pause before giving up on this feed for this run.
    """
    url = ("https://news.google.com/rss/search?q="
           + urllib.parse.quote(query)
           + "&hl=en-US&gl=US&ceid=US:en")
    raw = None
    for attempt, pause in enumerate((0, 8, 25)):
        if pause:
            time.sleep(pause)
        try:
            req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
            with urllib.request.urlopen(req, timeout=20) as resp:
                raw = resp.read()
            break
        except urllib.error.HTTPError as exc:
            if exc.code not in (429, 500, 502, 503, 504) or attempt == 2:
                raise
        except (urllib.error.URLError, TimeoutError):
            if attempt == 2:
                raise
    root = ET.fromstring(raw)
    entries = []
    for item in root.iter("item"):
        entry = {
            "title": strip_tags(item.findtext("title", "")).strip(),
            "link": (item.findtext("link", "") or "").strip(),
            "pubdate": (item.findtext("pubDate", "") or "").strip(),
            "source": strip_tags(item.findtext("source", "")).strip(),
            "desc": strip_tags(item.findtext("description", "")).strip(),
        }
        # Google appends " - Outlet Name" to every headline; the dashboard shows
        # the outlet separately, so drop the duplicate.
        suffix = " - " + entry["source"]
        if entry["source"] and entry["title"].endswith(suffix):
            entry["title"] = entry["title"][: -len(suffix)].strip()
        if entry["title"]:
            entries.append(entry)
    return entries


def parse_date(pubdate):
    try:
        return parsedate_to_datetime(pubdate).astimezone(timezone.utc)
    except (TypeError, ValueError):
        return None


def fetch_commodities(series_cfg, api_key=""):
    """Fetch commodity index series from the free BLS public API.

    Works with no key (v1, 25 requests/day per network). A free BLS
    registration key, if provided in config.json, switches to v2 (500/day).
    """
    ids = [s["id"] for s in series_cfg]
    if not ids:
        return []
    year = datetime.now().year
    req_body = {"seriesid": ids, "startyear": str(year - 1), "endyear": str(year)}
    url = BLS_URL
    if api_key:
        req_body["registrationkey"] = api_key
        url = BLS_URL.replace("/v1/", "/v2/")
    body = json.dumps(req_body).encode()
    last_err, reply = None, None
    for _ in range(3):  # the endpoint occasionally hiccups; retry briefly
        try:
            req = urllib.request.Request(
                url, data=body,
                headers={"Content-Type": "application/json", "User-Agent": USER_AGENT})
            with urllib.request.urlopen(req, timeout=20) as resp:
                reply = json.loads(resp.read())
            if reply.get("status") == "REQUEST_SUCCEEDED":
                break
            last_err = "; ".join(reply.get("message", [])) or reply.get("status")
        except Exception as exc:
            last_err = str(exc)
        reply = None
        time.sleep(2)
    if reply is None:
        raise RuntimeError(f"BLS request failed ({last_err})")

    by_id = {s["seriesID"]: s.get("data", []) for s in reply["Results"]["series"]}
    out = []
    for cfg in series_cfg:
        obs = []
        for r in by_id.get(cfg["id"], []):
            per = r.get("period", "")
            if not per.startswith("M") or per == "M13":  # monthly obs only
                continue
            try:
                obs.append((datetime(int(r["year"]), int(per[1:]), 1).date(),
                            float(r["value"])))
            except (ValueError, KeyError):
                continue
        obs.sort()
        if not obs:
            continue
        latest_date, latest_val = obs[-1]

        def val_at(months_back):
            ty, tm = latest_date.year, latest_date.month - months_back
            while tm < 1:
                tm += 12
                ty -= 1
            best = None
            for d, v in obs:
                if (d.year, d.month) <= (ty, tm):
                    best = v
            return best

        def pct(prev):
            return round((latest_val - prev) / prev * 100, 1) if prev else None

        out.append({"label": cfg["label"], "unit": cfg.get("unit", "index"),
                    "value": latest_val, "date": latest_date.strftime("%b %Y"),
                    "chg1": pct(val_at(1)), "chg3": pct(val_at(3))})
    return out


def fetch_regulatory(queries, since_iso, title_terms=None):
    """Fetch proposed/final rules from the free, keyless Federal Register API.

    The API's term search matches full text, which is loose — so a rule only
    counts if its TITLE contains one of title_terms (when provided).
    """
    title_terms = [t.lower() for t in (title_terms or [])]
    found = []
    for q in queries:
        params = [("conditions[term]", q.get("term", "")),
                  ("conditions[type][]", "RULE"),
                  ("conditions[type][]", "PRORULE"),
                  ("conditions[publication_date][gte]", since_iso),
                  ("per_page", "20"), ("order", "newest")]
        for slug in q.get("agencies", []):
            params.append(("conditions[agencies][]", slug))
        for f in ("title", "type", "publication_date", "html_url",
                  "document_number", "agency_names"):
            params.append(("fields[]", f))
        req = urllib.request.Request(FEDREG_URL + "?" + urllib.parse.urlencode(params),
                                     headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(req, timeout=20) as resp:
            reply = json.loads(resp.read())
        for r in reply.get("results", []):
            title = (r.get("title") or "").strip()
            if not title:
                continue
            if title_terms and not any(t in title.lower() for t in title_terms):
                continue
            agencies = ", ".join(AGENCY_ABBREV.get(a, a)
                                 for a in (r.get("agency_names") or []))
            found.append({
                "d": r.get("publication_date", ""),
                "t": "Proposed rule" if r.get("type") == "Proposed Rule" else "Final rule",
                "a": agencies,
                "h": title,
                "u": r.get("html_url", ""),
                "k": "reg" + str(r.get("document_number", "")),
            })
        time.sleep(0.3)
    return found


# ------------------------------------------------------------------- main ----

def load_config():
    if not os.path.exists(CONFIG_PATH):
        save_json(CONFIG_PATH, DEFAULT_CONFIG)
        print("Created config.json with the default watchlist - edit it any time.")
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            user_cfg = json.load(f)
    except ValueError as exc:
        # Fail loudly: silently falling back to defaults would ignore your edits.
        sys.exit(f"config.json has a formatting error ({exc}).\n"
                 "Fix it (a missing comma or quote is the usual cause) and run again.")
    return {**DEFAULT_CONFIG, **user_cfg}


def main():
    config = load_config()
    data = load_json(DATA_PATH, {"items": [], "seen": [], "last_run": None})
    seen_list = list(data.get("seen", []))
    seen = set(seen_list)
    feed_ok = data.get("feed_ok", {})   # per-source checkpoint: source id -> last success

    now = datetime.now(timezone.utc)
    run_id = now.isoformat(timespec="seconds")
    lookback = timedelta(days=config["first_run_lookback_days"])
    overlap = timedelta(days=config["overlap_days"])
    legacy_last = data.get("last_run")  # from older versions without per-source checkpoints

    def since_for(source_id):
        """Each source resumes from its own last successful check. A source that
        failed last time is retried from where it left off, and a vendor newly
        added to config.json automatically gets the full first-run lookback."""
        if source_id in feed_ok:
            return datetime.fromisoformat(feed_ok[source_id]) - overlap
        if legacy_last and not data.get("feed_ok"):
            return datetime.fromisoformat(legacy_last) - overlap
        return now - lookback

    print(f"Vendor Watch run {now.astimezone():%Y-%m-%d %H:%M}")

    # Build the query list: vendors + competitors + industry-wide queries -
    vendors = [vendor_pair(v) for v in config["watchlist"]]
    jobs = [("v:" + name, name, cat, f'"{name}" {STRUCTURAL_TERMS}')
            for name, cat in vendors if name]
    jobs += [("c:" + str(c), str(c), "competitor", f'"{c}" {STRUCTURAL_TERMS}')
             for c in config.get("competitors", [])]
    jobs += [("i:" + q, "Industry", "industry", q) for q in config["industry_queries"]]

    # One event, one entry: if we already have an item for the same company and
    # change type within 7 days, later coverage of it from other outlets is skipped.
    def to_date(s):
        return datetime.fromisoformat(s).date()

    def cluster_name(company, title):
        # Industry items have no single company, so cluster them by the first
        # words of the headline (usually the acquirer's name).
        if company != "Industry":
            return company
        return " ".join(title.lower().split()[:2])

    clusters = [(cluster_name(it["c"], it["h"]), it["t"], to_date(it["d"]))
                for it in data["items"]]

    def is_duplicate_event(company, change_type, day):
        return any(c == company and t == change_type and abs((day - d).days) <= 7
                   for c, t, d in clusters)

    def remember(key):
        seen.add(key)
        seen_list.append(key)

    blocked = {b.strip().lower() for b in config.get("blocked_sources", []) if b.strip()}

    new_items, failed = [], []
    for idx, (source_id, company, cat, query) in enumerate(jobs, 1):
        label = company if company != "Industry" else "industry-wide"
        print(f"  [{idx}/{len(jobs)}] {label} ...", end=" ", flush=True)
        since = since_for(source_id)
        try:
            entries = fetch_feed(query)
        except Exception as exc:  # one bad feed shouldn't kill the run
            failed.append(label)
            print(f"skipped ({exc}) - will retry next run")
            time.sleep(config["request_delay_seconds"])
            continue

        kept = 0
        for e in entries:
            when = parse_date(e["pubdate"])
            if when is None or when < since:
                continue
            title_low = e["title"].lower()
            if any(p in title_low for p in NOISE_PHRASES):
                continue
            if e["source"].strip().lower() in blocked:
                continue
            change_type = classify(e["title"] + " " + e["desc"])
            if change_type is None:
                continue
            if company == "Industry":
                combined = title_low + " " + e["desc"].lower()
                if not any(t in combined for t in CATEGORY_TERMS):
                    continue
            key = norm_key(e["title"])
            if not key or key in seen:
                continue
            cname = cluster_name(company, e["title"])
            if is_duplicate_event(cname, change_type, when.date()):
                remember(key)
                continue
            remember(key)
            clusters.append((cname, change_type, when.date()))
            new_items.append({
                "d": when.date().isoformat(),
                "c": company,
                "cat": cat,
                "t": change_type,
                "h": e["title"],
                "u": e["link"],
                "src": e["source"] or "Google News",
                "k": key,
                "added": run_id,
            })
            kept += 1
        feed_ok[source_id] = run_id
        print(f"{kept} new" if kept else "nothing new")
        time.sleep(config["request_delay_seconds"])

    # Drop checkpoints for sources removed from config.json
    live_ids = {j[0] for j in jobs}
    feed_ok = {k: v for k, v in feed_ok.items() if k in live_ids or k.startswith("reg:")}

    # Merge, sort, cap ----------------------------------------------------
    data["items"] = sorted(new_items + data["items"],
                           key=lambda it: it["d"], reverse=True)[: config["max_items"]]
    data["seen"] = seen_list[-3000:]          # ordered, so the oldest keys age out first
    data["feed_ok"] = feed_ok
    data["last_run"] = run_id
    data["run"] = {"id": run_id, "new": len(new_items),
                   "sources": len(jobs), "failed": len(failed)}

    # Commodity indexes ----------------------------------------------------
    print("Fetching commodity indexes (BLS) ...", end=" ", flush=True)
    try:
        # A key in the BLS_API_KEY environment variable (a GitHub Secret when
        # running on GitHub) wins, so the key never has to sit in config.json.
        bls_key = os.environ.get("BLS_API_KEY", "").strip() or config.get("bls_api_key", "")
        items = fetch_commodities(config.get("commodity_series", []), bls_key)
        data["commodities"] = {"fetched": run_id, "items": items}
        print(f"{len(items)} series")
    except Exception as exc:
        print(f"skipped ({exc}) - keeping previous values")
        data.setdefault("commodities", {"fetched": None, "items": []})

    # Regulatory watch (own checkpoint, so a failed check is retried) ------
    print("Checking the Federal Register ...", end=" ", flush=True)
    reg_seen = list(data.get("reg_seen", []))
    reg_seen_set = set(reg_seen)
    reg_since = since_for("reg:fedreg")
    new_regs = []
    try:
        for reg in fetch_regulatory(config.get("regulatory_queries", []),
                                    reg_since.date().isoformat(),
                                    config.get("regulatory_title_terms", [])):
            if reg["k"] in reg_seen_set:
                continue
            reg_seen_set.add(reg["k"])
            reg_seen.append(reg["k"])
            reg["added"] = run_id
            new_regs.append(reg)
        data["feed_ok"]["reg:fedreg"] = run_id
        print(f"{len(new_regs)} new rule(s)")
    except Exception as exc:
        print(f"skipped ({exc}) - will retry next run")
    data["regs"] = sorted(new_regs + data.get("regs", []),
                          key=lambda r: r["d"], reverse=True)[:50]
    data["reg_seen"] = reg_seen[-500:]
    data["run"]["new_regs"] = len(new_regs)

    save_json(DATA_PATH, data)

    # Render --------------------------------------------------------------
    out_path = os.path.join(SCRIPT_DIR, config["output_file"])
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    render_dashboard(out_path, data, config, now)

    print()
    print(f"Done: {len(new_items)} new news item(s), {len(new_regs)} new rule(s), "
          f"{len(data['items'])} news items total on the dashboard.")
    if failed:
        print(f"{len(failed)} of {len(jobs)} sources could not be reached this run and "
              "will be retried from where they left off next time.")
    print(f"Dashboard written to: {out_path}")


# --------------------------------------------------------------- rendering ----

TEMPLATE = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Tarheel Vendor &amp; Industry Watch</title>
<style>
  /* Tokens from the Tarheel Paper & Supply design system */
  :root{--red:#ce1126;--red-pressed:#a30d1e;--blue:#002d5c;--blue-pressed:#001f40;
    --gray:#4b4f54;--pack:#5d89b4;--pack-text:#3e6a96;--pack-tint:#eef3f8;
    --jan:#00833e;--jan-text:#006b33;--jan-tint:#e8f3ec;
    --safe:#ffb819;--safe-text:#8a5a00;--safe-tint:#fff4d9;
    --paper:#fff;--surface:#f2f3f4;--blue-tint:#e6ecf3;--ink:#1f2327;--slate:#5b6478;
    --border:#8c9196;--hairline:#d4d6d9;--dont-tint:#fbecec;}
  *{box-sizing:border-box;margin:0;padding:0}
  body{background:var(--surface);color:var(--ink);font-size:15px;line-height:1.5;
    font-family:Arial,Arimo,Helvetica,sans-serif}
  .disp{font-family:"Arial Black","Archivo Black",Arial,sans-serif;font-weight:900}
  header{background:var(--blue);color:#fff;padding:18px 24px 20px;border-bottom:6px solid var(--red)}
  .mast{max-width:1000px;margin:0 auto;display:flex;align-items:center;gap:14px;flex-wrap:wrap}
  .logo{width:44px;height:44px;flex:none;background:var(--red);display:flex;align-items:center;
    justify-content:center;font-size:28px;color:#fff}
  .mt{flex:1;min-width:220px}
  .co{font-weight:700;font-size:12px;letter-spacing:.14em;text-transform:uppercase;color:#c9d1e6}
  .h1{font-size:24px;line-height:1.15}
  .upd{font-size:12.5px;color:#c9d1e6;text-align:right}
  .upd strong{color:#fff}
  main{max-width:1000px;margin:0 auto;padding:18px 24px 40px}
  .banner{padding:10px 14px;font-size:13.5px;margin-top:10px;border-left:4px solid var(--red);
    background:var(--dont-tint);color:var(--ink)}
  .banner.info{border-left-color:var(--blue);background:var(--blue-tint)}
  .ribbon{display:inline-block;background:var(--red);color:#fff;font-size:14px;
    letter-spacing:.06em;text-transform:uppercase;padding:7px 30px 7px 14px;
    clip-path:polygon(0 0,100% 0,calc(100% - 14px) 100%,0 100%);margin:24px 0 12px}
  .ribbon.blue{background:var(--blue)}
  .ribbon.gray{background:var(--gray)}
  .filters{display:flex;gap:8px;flex-wrap:wrap;align-items:center;margin:4px 0 12px}
  .chip{background:var(--paper);border:1px solid var(--border);color:var(--ink);font:inherit;
    font-size:13px;padding:5px 12px;border-radius:2px;cursor:pointer}
  .chip:hover{border-color:var(--blue)}
  .chip[aria-pressed="true"]{background:var(--blue);border-color:var(--blue);color:#fff;font-weight:700}
  .search{flex:1;min-width:160px;max-width:280px;margin-left:auto;border:1px solid var(--border);
    background:var(--paper);padding:6px 10px;font:inherit;font-size:13.5px;border-radius:2px}
  .chip:focus-visible,.search:focus-visible,a:focus-visible,button:focus-visible{
    outline:2px solid var(--blue);outline-offset:2px}
  .ledger{background:var(--paper);border:1px solid var(--hairline)}
  .row{display:grid;grid-template-columns:96px 1fr 34px;gap:0 16px;padding:14px 16px;
    border-bottom:1px solid var(--hairline)}
  .row:last-child{border-bottom:none}
  .row.fresh{background:var(--blue-tint)}
  .date{font-weight:700;font-size:12.5px;color:var(--slate);padding-top:3px}
  .badge{display:inline-block;font-size:11px;font-weight:700;letter-spacing:.05em;
    text-transform:uppercase;padding:2px 8px;border-radius:2px;color:#fff;margin-right:8px}
  .b-mna{background:var(--blue)}.b-close{background:var(--red)}
  .b-open{background:var(--gray)}.b-supply{background:var(--slate)}
  .new{display:inline-block;font-size:10.5px;font-weight:700;letter-spacing:.05em;
    text-transform:uppercase;color:var(--red);margin-right:6px}
  .head{font-weight:700;font-size:15px}
  .cco{color:var(--blue)}
  .meta{font-size:12.5px;margin-top:4px;color:var(--slate)}
  .meta a{color:var(--blue)}
  .cat{display:inline-block;font-size:10.5px;font-weight:700;letter-spacing:.04em;
    text-transform:uppercase;border-radius:2px;padding:0 6px;margin-right:6px}
  .cat-packaging{background:var(--pack-tint);color:var(--pack-text)}
  .cat-janitorial{background:var(--jan-tint);color:var(--jan-text)}
  .cat-safety{background:var(--safe-tint);color:var(--safe-text)}
  .cat-competitor{background:var(--dont-tint);color:var(--red)}
  .cat-industry,.cat-other{background:var(--surface);color:var(--gray)}
  .x{background:none;border:none;color:var(--border);font-size:16px;line-height:1;height:26px;
    width:26px;cursor:pointer;border-radius:2px}
  .x:hover{background:var(--surface);color:var(--red)}
  .empty{background:var(--paper);border:1px dashed var(--border);padding:30px 24px;
    text-align:center;color:var(--slate);font-size:14px}
  .commods{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:1px;
    background:var(--hairline);border:1px solid var(--hairline)}
  .cm{background:var(--paper);padding:12px 14px}
  .cm .lbl{font-size:12px;color:var(--slate)}
  .cm .val{font-size:20px;color:var(--blue)}
  .cm .when{font-family:Arial,sans-serif;font-size:11px;color:var(--slate);font-weight:400}
  .cm .chg{font-size:12px;margin-top:3px}
  .up{color:var(--red);font-weight:700}
  .dn{color:var(--blue);font-weight:700}
  .flat{color:var(--slate)}
  .note{font-size:12px;color:var(--slate);margin-top:6px}
  .rtype{font-weight:700;color:var(--blue);font-size:12px}
  .tags{background:var(--paper);border:1px solid var(--hairline);padding:6px 16px 14px}
  .tagrow{margin-top:8px}
  .tagrow strong{font-size:12px;color:var(--blue)}
  .tag{background:var(--surface);border:1px solid var(--hairline);font-size:12.5px;
    padding:3px 10px;border-radius:2px;display:inline-block;margin:3px 4px 0 0}
  footer{max-width:1000px;margin:0 auto;padding:0 24px 40px;font-size:12px;color:var(--slate)}
  footer button{background:none;border:none;color:var(--blue);text-decoration:underline;
    cursor:pointer;font:inherit;font-size:12px;padding:0}
  @media (max-width:560px){.row{grid-template-columns:1fr 30px}
    .date{grid-column:1/-1;padding-top:0;margin-bottom:2px}.upd{text-align:left}}
  @media print{header{border-bottom-width:3px}.filters,.x,footer button{display:none}
    .row.fresh{background:none}}
</style>
</head>
<body>
<header><div class="mast">
  <div class="logo disp" aria-hidden="true">T</div>
  <div class="mt"><div class="co">Tarheel Paper &amp; Supply</div>
    <h1 class="h1 disp">Vendor &amp; Industry Watch</h1></div>
  <div class="upd">Last updated<br><strong id="gen"></strong><br><span id="runsum"></span></div>
</div></header>
<main>
  <div id="banners"></div>

  <div class="ribbon gray disp">Commodity Signals</div>
  <div class="commods" id="commods"></div>
  <p class="note" id="commodnote">Producer Price Indexes and U.S. average diesel price from the
    U.S. Bureau of Labor Statistics, vs. 1 and 3 months prior. Red = cost rising, blue = falling.</p>

  <div class="ribbon disp">Structural Changes</div>
  <div class="filters" id="filters">
    <button class="chip" data-f="all" aria-pressed="true">All changes</button>
    <button class="chip" data-f="new" aria-pressed="false">New this run</button>
    <button class="chip" data-f="mna" aria-pressed="false">M&amp;A &amp; Ownership</button>
    <button class="chip" data-f="close" aria-pressed="false">Closures</button>
    <button class="chip" data-f="open" aria-pressed="false">Openings</button>
    <button class="chip" data-f="supply" aria-pressed="false">Supply</button>
    <input class="search" id="q" type="search" placeholder="Filter by company or keyword"
      aria-label="Filter changes">
  </div>
  <div class="filters" id="catfilters">
    <button class="chip" data-c="all" aria-pressed="true">All categories</button>
    <button class="chip" data-c="packaging" aria-pressed="false">Packaging</button>
    <button class="chip" data-c="janitorial" aria-pressed="false">Janitorial</button>
    <button class="chip" data-c="safety" aria-pressed="false">Safety</button>
    <button class="chip" data-c="competitor" aria-pressed="false">Competitors</button>
    <button class="chip" data-c="industry" aria-pressed="false">Industry</button>
  </div>
  <div id="list"></div>

  <div class="ribbon blue disp">Regulatory Watch</div>
  <div id="regs"></div>

  <div class="ribbon gray disp">Watchlist</div>
  <div class="tags" id="tags"></div>
  <p class="note">To add vendors, competitors, commodity series, or regulatory searches, edit
    config.json next to vendor_watch.py. New vendors automatically get a full 90-day first scan.</p>
</main>
<footer>
  News via Google News, price indexes via the U.S. Bureau of Labor Statistics, rules via the
  Federal Register. Structural changes only &mdash; not product releases. Dates are when the news
  outlet published; occasionally an older story is re-published and appears with a recent date.
  Hidden items are remembered on this computer only. <button id="restore">Restore hidden items</button>
</footer>
<script>
const DATA = __DATA__;
const GROUP = {merger:"mna",acquisition:"mna",ownership:"mna",bankruptcy:"close",closure:"close",
  opening:"open",supply:"supply",other:"supply"};
const LABEL = {merger:"Merger",acquisition:"Acquisition",ownership:"Ownership",
  bankruptcy:"Bankruptcy",closure:"Closure",opening:"Opening",supply:"Supply",other:"Industry"};
const CLS = {mna:"b-mna",close:"b-close",open:"b-open",supply:"b-supply"};
const CATNAME = {packaging:"Packaging",janitorial:"Janitorial",safety:"Safety",
  competitor:"Competitor",industry:"Industry",other:"Other"};
const RUN = DATA.run || {};
let filter="all", cat="all", term="";
const $=id=>document.getElementById(id);
const esc=s=>String(s??"").replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",
  '"':"&quot;","'":"&#39;"}[c]));
function hidden(){try{return JSON.parse(localStorage.getItem("tpws-hidden")||"[]")}catch(e){return[]}}
function setHidden(a){try{localStorage.setItem("tpws-hidden",JSON.stringify(a.slice(-500)))}catch(e){}}
function fmt(d){const t=new Date(d+"T12:00:00");
  return isNaN(t)?d:t.toLocaleDateString(undefined,{month:"short",day:"numeric",year:"numeric"})}
function cleanTitle(it){const suf=" - "+(it.src||"");
  return it.src&&it.h.endsWith(suf)?it.h.slice(0,-suf.length):it.h;}
function itemCat(it){return it.cat||(it.c==="Industry"?"industry":"other")}
function isNew(it){return RUN.id&&it.added===RUN.id}
function chg(v){if(v===null||v===undefined)return '<span class="flat">&ndash;</span>';
  const cls=v>0?"up":v<0?"dn":"flat";const arrow=v>0?"\u25B2":v<0?"\u25BC":"\u25AC";
  return '<span class="'+cls+'">'+arrow+' '+Math.abs(v).toFixed(1)+'%</span>';}
function hideBtn(k){return '<button class="x" data-k="'+esc(k)
  +'" title="Hide this item" aria-label="Hide item">&times;</button>';}

function renderHeader(){
  const g=new Date(DATA.generated);
  $("gen").textContent=isNaN(g)?"":g.toLocaleString(undefined,{month:"short",day:"numeric",
    year:"numeric",hour:"numeric",minute:"2-digit"});
  const n=(RUN.new||0)+(RUN.new_regs||0);
  $("runsum").textContent=n?(n+" new this run"):"No new changes this run";
  const b=[];
  const ageDays=(Date.now()-g.getTime())/864e5;
  if(!isNaN(g)&&ageDays>(DATA.stale_days||3)){
    b.push('<div class="banner"><strong>This dashboard may be out of date.</strong> It was last '
      +'refreshed '+Math.floor(ageDays)+' days ago &mdash; the scheduled run may have stopped. '
      +(DATA.host==="github"?'Check the Actions tab of the GitHub repository for a failed or '
      +'disabled workflow.':'Check vendor_watch.log next to the script.')+'</div>');}
  if(RUN.failed){
    b.push('<div class="banner info">'+RUN.failed+' of '+RUN.sources+' news sources could not be '
      +'reached on the last run. They will be caught up automatically on the next run.</div>');}
  $("banners").innerHTML=b.join('');
}
function renderCommods(){
  const el=$("commods");
  if(!DATA.commodities||!DATA.commodities.length){
    el.innerHTML='<div class="cm"><span class="lbl">No index data yet &mdash; the BLS service '
      +'could not be reached. It will be retried on the next run.</span></div>';return;}
  el.innerHTML=DATA.commodities.map(c=>{
    const val=c.unit==="$/gal"?"$"+Number(c.value).toFixed(2):Number(c.value).toFixed(1);
    return '<div class="cm"><div class="lbl">'+esc(c.label)+'</div>'
      +'<div class="val disp">'+val+' <span class="when">'+esc(c.date)+'</span></div>'
      +'<div class="chg">1 mo '+chg(c.chg1)+' &nbsp; 3 mo '+chg(c.chg3)+'</div></div>';
  }).join('');
  if(DATA.commod_fetched&&RUN.id&&DATA.commod_fetched!==RUN.id){
    $("commodnote").insertAdjacentHTML("beforeend",' <strong>Showing values saved on '
      +esc(fmt(DATA.commod_fetched.slice(0,10)))+'</strong> &mdash; the latest refresh could not reach BLS.');}
}
function renderRegs(){
  const hid=new Set(hidden());
  const regs=(DATA.regs||[]).filter(r=>!hid.has(r.k));
  $("regs").innerHTML=!regs.length
    ?'<div class="empty">No new proposed or final rules match the tracked topics.</div>'
    :'<div class="ledger">'+regs.map(r=>
      '<div class="row'+(isNew(r)?' fresh':'')+'"><div class="date">'+esc(fmt(r.d))+'</div><div>'
      +'<div class="rtype">'+(isNew(r)?'<span class="new">New</span>':'')+esc(r.t)
      +(r.a?' &middot; '+esc(r.a):'')+'</div>'
      +'<div class="head">'+esc(r.h)+'</div>'
      +(/^https?:\/\//.test(r.u)?'<div class="meta"><a href="'+esc(r.u)
        +'" target="_blank" rel="noopener noreferrer">Read on federalregister.gov</a></div>':'')
      +'</div>'+hideBtn(r.k)+'</div>').join('')+'</div>';
}
function render(){
  const hid=new Set(hidden());
  const items=DATA.items.filter(it=>{
    if(hid.has(it.k))return false;
    const g=GROUP[it.t]||"supply";
    if(filter==="new"){if(!isNew(it))return false;}
    else if(filter!=="all"&&g!==filter)return false;
    if(cat!=="all"&&itemCat(it)!==cat)return false;
    if(term&&!((it.c+" "+it.h).toLowerCase().includes(term)))return false;
    return true;});
  $("list").innerHTML = !DATA.items.length
    ? '<div class="empty"><strong>No changes found yet.</strong><br>Run vendor_watch.py to scan.</div>'
    : !items.length
    ? '<div class="empty">No saved changes match this filter.</div>'
    : '<div class="ledger">'+items.map(it=>{
        const g=GROUP[it.t]||"supply", c=itemCat(it);
        const link=/^https?:\/\//.test(it.u)
          ?' &middot; <a href="'+esc(it.u)+'" target="_blank" rel="noopener noreferrer">Read article</a>':'';
        return '<div class="row'+(isNew(it)?' fresh':'')+'"><div class="date">'+esc(fmt(it.d))+'</div><div>'
          +'<div class="head">'+(isNew(it)?'<span class="new">New</span>':'')
          +'<span class="badge '+CLS[g]+'">'+LABEL[it.t]+'</span>'
          +(it.c!=="Industry"?'<span class="cco">'+esc(it.c)+'</span> &mdash; ':'')
          +esc(cleanTitle(it))+'</div>'
          +'<div class="meta"><span class="cat cat-'+esc(c)+'">'+esc(CATNAME[c]||c)+'</span>'
          +esc(it.src)+link+'</div></div>'+hideBtn(it.k)+'</div>';
      }).join('')+'</div>';
  $("tags").innerHTML=Object.entries(DATA.watch_groups||{}).map(([g,names])=>
    '<div class="tagrow"><strong>'+esc(g)+':</strong><br>'
    +names.map(n=>'<span class="tag">'+esc(n)+'</span>').join('')+'</div>').join('');
  renderRegs();
}
function hideHandler(e){const b=e.target.closest("[data-k]");if(!b)return;
  const a=hidden();a.push(b.dataset.k);setHidden(a);render();}
function chipGroup(id,attr,set){$(id).addEventListener("click",e=>{
  const b=e.target.closest(".chip");if(!b)return;set(b.dataset[attr]);
  document.querySelectorAll("#"+id+" .chip").forEach(c=>
    c.setAttribute("aria-pressed",c===b?"true":"false"));render();});}
chipGroup("filters","f",v=>filter=v);
chipGroup("catfilters","c",v=>cat=v);
$("q").addEventListener("input",e=>{term=e.target.value.trim().toLowerCase();render();});
$("list").addEventListener("click",hideHandler);
$("regs").addEventListener("click",hideHandler);
$("restore").addEventListener("click",()=>{setHidden([]);render();});
renderHeader();
renderCommods();
render();
</script>
</body>
</html>
"""


def render_dashboard(out_path, data, config, now):
    watch_groups = {}
    for v in config["watchlist"]:
        name, cat = vendor_pair(v)
        if name:
            watch_groups.setdefault(cat.capitalize(), []).append(name)
    if config.get("competitors"):
        watch_groups["Competitors"] = [str(c) for c in config["competitors"]]
    commod = data.get("commodities", {})
    payload = {
        "items": data["items"],
        "watch_groups": watch_groups,
        "commodities": commod.get("items", []),
        "commod_fetched": commod.get("fetched"),
        "regs": data.get("regs", []),
        "run": data.get("run", {}),
        "generated": now.isoformat(timespec="seconds"),
        "stale_days": config.get("stale_after_days", 3),
        "host": "github" if os.environ.get("GITHUB_ACTIONS") == "true" else "local",
    }
    data_json = json.dumps(payload, ensure_ascii=False).replace("</", "<\\/")
    html_out = TEMPLATE.replace("__DATA__", data_json)
    atomic_write(out_path, html_out)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit("\nCancelled.")
