# Kalibrr Job Scraper

Two-step pipeline that pulls real Indonesian job listings from
[Kalibrr.id](https://www.kalibrr.id) and seeds them into the
`rumahkarir.db` SQLite database used by the Flask app.

## Why this exists

The original `seed.py` ships a small set of hand-curated demo
companies + jobs. To make search results, the map dashboard and the
admin views feel realistic, we want real Indonesian listings.

Glints.com is fronted by Cloudflare with bot fingerprinting that
returns HTTP 403 to most cloud/server IPs, so it cannot be scraped
from a clean VM. Kalibrr does not block automated access and exposes
each category page as a Next.js SSR document containing the full job
record inside a `<script id="__NEXT_DATA__">` payload — perfect for
deterministic scraping.

## Files

| File | Purpose |
| ---- | ------- |
| `kalibrr_scraper.py` | Playwright-over-CDP scraper. Writes `data/kalibrr_jobs.json`. |
| `import_kalibrr.py`  | Reads the JSON and upserts companies + jobs into the DB. Idempotent. |
| `data/kalibrr_jobs.json` | Last successful scrape (258 listings, 91 companies). Committed so a fresh checkout can re-seed the DB without scraping. |

## Usage

```bash
# 1. Activate the project venv
source .venv/bin/activate

# 2. (Optional) Re-scrape from Kalibrr
#    Requires a running Chrome with --remote-debugging-port=29229.
#    On Devin VMs this is already the case.
python scrapers/kalibrr_scraper.py --max-jobs 250

# 3. Import into the DB. Safe to re-run; duplicates are skipped.
python scrapers/import_kalibrr.py
```

The importer:

* deduplicates companies by lower-case name (so re-imports don't fork
  identities, and Kalibrr "PT. Cosmax Indonesia" maps onto an existing
  hand-seeded "PT. Cosmax Indonesia" if present),
* deduplicates jobs by `(company_id, lower(title))`,
* normalises bilingual province names (`"West Java (Jawa Barat)"` →
  `"Jawa Barat"`) so the province dropdown and map don't fragment,
* maps Kalibrr's `workExperience` buckets (`100/200/300/400`) onto
  `min_experience` years (`0/1/3/5`),
* maps `tenure` (`Full time` / `Contractual` / …) onto the app's
  `employment_type` vocabulary,
* only stores salary values when the listing's currency is IDR.

Pass `--include-other-countries` to also import Kalibrr's
Philippines / Singapore listings (default is Indonesia-only).

## Data shape

Each entry in `data/kalibrr_jobs.json` looks like:

```json
{
  "kalibrr_id": 265990,
  "slug": "mandarin-translator",
  "title": "Mandarin Translator",
  "description_html": "<ul>…</ul>",
  "qualifications_html": "<ul>…</ul>",
  "function": "Administration and Coordination",
  "tenure": "Full time",
  "work_experience_months": 300,
  "is_wfh": false,
  "is_hybrid": false,
  "salary_min": null,
  "salary_max": null,
  "salary_currency": null,
  "salary_interval": null,
  "country": "Indonesia",
  "region": "DKI Jakarta",
  "city": "Central Jakarta",
  "company": {
    "code": "pt-metro-timur-indonusa",
    "name": "PT Metro Timur Indonusa",
    "industry": "Investment Banking / Venture",
    "description": "…",
    "logo_small": "https://…"
  },
  "url": "https://www.kalibrr.id/id-ID/c/…/jobs/265990/…"
}
```
