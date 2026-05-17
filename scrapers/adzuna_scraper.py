"""Scrape Adzuna's free public Search API for Indonesia jobs.

Endpoint::

  GET https://api.adzuna.com/v1/api/jobs/id/search/{page}
       ?app_id=...&app_key=...&results_per_page=50&what=...&where=Indonesia

Requires ``ADZUNA_APP_ID`` and ``ADZUNA_APP_KEY`` in the environment
(free tier — sign up at https://developer.adzuna.com/signup).

We sweep over a list of broad keyword queries to maximize coverage.
Adzuna caps free tier at 1000 calls/month and 50 results per page —
we paginate up to 20 pages per keyword = 1000 jobs per keyword (less
in practice; Adzuna ID has a smaller corpus).

Output: ``scrapers/data/adzuna_jobs.json``.
"""
from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

import urllib.request
import urllib.parse


COUNTRY = "id"
BASE = f"https://api.adzuna.com/v1/api/jobs/{COUNTRY}/search"
OUT_PATH = Path(__file__).parent / "data" / "adzuna_jobs.json"

# Broad keywords designed to maximize coverage of the Adzuna ID corpus.
# Each keyword is searched independently and the union is deduplicated.
KEYWORDS = [
    "developer", "engineer", "manager", "marketing", "sales",
    "design", "data", "finance", "hr", "operasional",
    "admin", "guru", "teacher", "perawat", "akuntan",
    "customer service", "supervisor", "staff", "produksi", "teknisi",
]


def fetch_page(app_id: str, app_key: str, query: str, page: int) -> list[dict]:
    params = {
        "app_id": app_id,
        "app_key": app_key,
        "results_per_page": 50,
        "what": query,
        "content-type": "application/json",
    }
    url = f"{BASE}/{page}?{urllib.parse.urlencode(params)}"
    try:
        with urllib.request.urlopen(url, timeout=20) as resp:
            data = json.loads(resp.read())
    except urllib.error.HTTPError as exc:
        if exc.code == 429:
            print("  429 rate-limited, sleeping 30s…", file=sys.stderr)
            time.sleep(30)
            return []
        print(f"  HTTP {exc.code} for {query} page {page}", file=sys.stderr)
        return []
    except Exception as exc:
        print(f"  fetch failed for {query} page {page}: {exc}", file=sys.stderr)
        return []
    return list(data.get("results") or [])


def normalize(job: dict) -> dict:
    company = job.get("company") or {}
    location = job.get("location") or {}
    cat = job.get("category") or {}
    return {
        "external_id": str(job.get("id") or ""),
        "title": (job.get("title") or "").strip(),
        "company_name": (company.get("display_name") or "").strip(),
        "location_display": (location.get("display_name") or "").strip(),
        "location_areas": list(location.get("area") or []),
        "description_html": (job.get("description") or "").strip(),
        "category": cat.get("label"),
        "contract_type": job.get("contract_type"),
        "contract_time": job.get("contract_time"),
        "salary_min": job.get("salary_min"),
        "salary_max": job.get("salary_max"),
        "salary_currency": "IDR",
        "salary_is_predicted": job.get("salary_is_predicted"),
        "created": job.get("created"),
        "url": job.get("redirect_url"),
        "latitude": job.get("latitude"),
        "longitude": job.get("longitude"),
        "source": "adzuna",
    }


def main(argv: list[str] | None = None) -> int:
    argv = argv or sys.argv[1:]
    max_pages = int(argv[0]) if argv else 6  # per keyword

    app_id = os.environ.get("ADZUNA_APP_ID")
    app_key = os.environ.get("ADZUNA_APP_KEY")
    if not app_id or not app_key:
        print(
            "ERROR: ADZUNA_APP_ID / ADZUNA_APP_KEY not set in environment. "
            "Sign up at https://developer.adzuna.com/signup for a free key.",
            file=sys.stderr,
        )
        return 1

    all_results: list[dict] = []
    for kw in KEYWORDS:
        for page in range(1, max_pages + 1):
            rows = fetch_page(app_id, app_key, kw, page)
            if not rows:
                break
            all_results.extend(rows)
            print(f"adzuna: '{kw}' p{page} -> {len(rows)} (running total {len(all_results)})")
            time.sleep(0.4)

    out = [normalize(j) for j in all_results]
    out = [j for j in out if j["title"] and j["company_name"]]
    # Dedup by external id
    seen: set[str] = set()
    deduped = []
    for j in out:
        key = j["external_id"] or j["title"] + "|" + j["company_name"]
        if key in seen:
            continue
        seen.add(key)
        deduped.append(j)
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps(deduped, indent=2, ensure_ascii=False))
    print(f"adzuna: wrote {len(deduped)} unique jobs to {OUT_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
