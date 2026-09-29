# Tarheel Vendor & Industry Watch — Standalone Edition

> **Running on GitHub?** Follow `GITHUB_SETUP.md` instead of the PC setup below.
> In this copy, `config.json` writes the dashboard to `site/index.html`
> (the folder GitHub publishes) rather than `dashboard.html`. If you run it on a
> PC instead, set `"output_file": "dashboard.html"` in config.json.

Runs entirely on your own machine. No Claude, no AI, no API keys, no cost.
Each run pulls from three free public sources and rebuilds `dashboard.html`:

- **Google News** — structural changes (mergers, acquisitions, closures,
  openings, bankruptcies, ownership changes, supply disruptions) for every
  vendor and competitor on your watchlist, plus industry-wide searches.
- **U.S. Bureau of Labor Statistics** — commodity signals: Producer Price
  Indexes for plastic resins, paper, and paperboard, plus the U.S. average
  diesel price, each with 1-month and 3-month direction.
- **Federal Register** — proposed and final rules from EPA, OSHA, and FDA
  touching packaging, PPE, and disinfectants.

## Setup (one time)

1. Install Python 3 from python.org if it isn't already installed
   (during install, check "Add Python to PATH").
2. Put `vendor_watch.py` and `run_watch.bat` together in a folder —
   a network share works well so the whole team can open the dashboard.

## Running it

Double-click `run_watch.bat` (or run `python vendor_watch.py` from a prompt).
A run takes about a minute and prints its progress. When it finishes:

- `config.json` — created on first run; everything is tuned here. Edit and
  re-run the script to apply. If you have a config.json from an older version,
  delete it once so the new categorized default is regenerated.
- `watch_data.json` — saved findings and run history. Leave it alone; delete it
  only if you want to start fresh with a full 90-day scan.
- `dashboard.html` — the dashboard. Open it in any browser or point the team to
  it on the shared drive. It needs no internet and works offline.

The first run looks back 90 days. After that, each source resumes from its own
last successful check, so:

- a source that couldn't be reached (Google occasionally rate-limits) is caught
  up automatically on the next run instead of silently skipped;
- a vendor you add to config.json later gets its own full 90-day first scan;
- re-running daily or weekly is quick and never duplicates.

Items found in the most recent run are marked **New** and highlighted, and the
"New this run" filter shows only those.

## What's in config.json

- **watchlist** — your vendors, each with a `category` (packaging, janitorial,
  or safety) that powers the category filter on the dashboard.
- **competitors** — distributors and prospects to track the same way. Their
  news is tagged Competitor on the dashboard and has its own filter. The
  defaults are common national/regional distributors — edit to match who you
  actually compete with. (BradyPLUS was removed from the defaults: it merged
  into Imperial Dade in March 2026.)
- **blocked_sources** — news outlets to ignore entirely, matched against the
  outlet name shown on the dashboard. Useful for stock-chatter sites that
  re-post old news with fresh dates.
- **bls_api_key** — optional. Leave blank to use the keyless BLS service
  (25 requests/day per network; the script uses one per run). If several
  people on the same office network run the script, register for a free key at
  data.bls.gov/registrationEngine and paste it here for 500/day.
- **stale_after_days** — how old the dashboard can get before it shows an
  "out of date" warning banner (default 3).
- **commodity_series** — the BLS series shown in the Commodity Signals strip.
  Any BLS series ID works; add or swap entries (find IDs at bls.gov/data).
- **regulatory_queries** — the Federal Register searches (term + agencies).
- **regulatory_title_terms** — a rule only makes the dashboard if its title
  contains one of these words. The Federal Register's search matches full
  document text, which is very loose; this list is what keeps unrelated air
  permits and medical-device rules out. Loosen or extend it if you feel rules
  are being missed.

## Scheduling it (optional)

1. Open **Task Scheduler** → **Create Basic Task**.
2. Name it "Vendor Watch", set the trigger (e.g., daily at 7:00 AM).
3. Action: **Start a program** → browse to `run_watch.bat`.
4. In **Add arguments**, type `/auto` — this is important. Without it the
   launcher waits for a keypress at the end, and the scheduled task never
   finishes.
5. In **Start in**, enter the folder containing the script.

In `/auto` mode the console output is appended to `vendor_watch.log` next to
the script (roughly 3 KB per run, about 1 MB a year — delete it any time).
If the dashboard ever shows an "out of date" banner, that log is the first
place to look.

## How the news filtering works

- Each vendor and competitor gets one targeted news search pre-filtered for
  structural terms.
- Headlines are classified by keyword — anything matching no structural
  category is discarded, which keeps product launches and routine news out.
- Keywords match whole words, and context matters: "strikes a deal" is not a
  labor strike, "closes acquisition" is not a closure, and "expands" only
  counts as an opening when a plant, warehouse, or other site is involved
  (so "expands product line" stays out).
- Stock commentary, shareholder-lawsuit notices, news roundups, SEO junk
  pages, and any outlets in `blocked_sources` are filtered out.
- Multiple outlets covering the same event within a week collapse to one entry.
- Industry-wide items must mention a relevant category (packaging, janitorial,
  safety, etc.) to make the list.

Dates are when the outlet published. Occasionally an older story is
re-published and shows up with a recent date — for example, coverage of the
Imperial Dade/BradyPLUS merger (closed March 2026) resurfaced in late
September. Check the article date before acting on anything time-sensitive.

Keyword filtering is dumber than a human reader: expect the occasional
borderline item (hide it with the × — hidden items are remembered per person,
per browser) and know it can occasionally miss an oddly-worded headline. The
keyword lists are all near the top of `vendor_watch.py` if you want to tune
them.

## Notes on the data sources

- The BLS public API allows 25 unregistered requests per day; the script makes
  exactly one per run. PPI data is monthly and publishes with roughly a
  one-month lag, so "Aug" showing in mid-September is normal.
- On the Commodity Signals strip, red means the cost went up, green means it
  came down.
- If BLS or the Federal Register can't be reached, the script keeps the
  previous values and says so in the console — a bad network day never blanks
  the dashboard.

## Troubleshooting

- **Upgrading from an earlier version**: replace `vendor_watch.py` and
  `run_watch.bat` and keep your `watch_data.json` — saved findings carry over.
  Your existing `config.json` also keeps working; new settings use their
  defaults until you add them. Remove "BradyPLUS" from `competitors` if it's
  in yours.
- **"config.json has a formatting error"**: the script stops rather than
  silently ignoring your edits. The usual cause is a missing comma or quote
  near the last thing you changed.
- **Feeds skipped with errors**: usually a network blip or a corporate proxy;
  skipped sources are retried automatically next run.
  The script honors system proxy settings automatically; if your network needs
  a manual proxy, set the `HTTPS_PROXY` environment variable before running.
- **Nothing found**: normal on quiet weeks — the console will say so and the
  dashboard's existing list stays in place.
