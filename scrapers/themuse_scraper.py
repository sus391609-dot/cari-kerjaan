"""Scrape The Muse public Jobs API.

Endpoint: ``GET https://www.themuse.com/api/public/jobs?page=N``
The free public API exposes thousands of global listings (~25k at any
given time). Each page returns 20 results; pagination is by ``?page=``.
No API key is required for the public endpoint.

Output: ``scrapers/data/themuse_jobs.json``.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path


API_URL = "https://www.themuse.com/api/public/jobs"
OUT_PATH = Path(__file__).parent / "data" / "themuse_jobs.json"


def fetch_page(page: int, *, category: str | None = None,
               level: str | None = None) -> tuple[list[dict], int]:
    """Return (results, page_count) for the requested page."""
    params: dict[str, object] = {"page": page}
    if category:
        params["category"] = category
    if level:
        params["level"] = level
    url = f"{API_URL}?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "Mozilla/5.0 (compatible; RUMAH-KARIR-scraper/1.0)"},
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            data = json.loads(resp.read())
    except urllib.error.HTTPError as exc:
        if exc.code == 429:
            print("  themuse: 429 rate-limited, sleeping 30s…", file=sys.stderr)
            time.sleep(30)
            return [], 0
        print(f"  themuse: HTTP {exc.code} on page {page}", file=sys.stderr)
        return [], 0
    except Exception as exc:
        print(f"  themuse: page {page} failed: {exc}", file=sys.stderr)
        return [], 0
    return list(data.get("results") or []), int(data.get("page_count") or 0)


def normalize(job: dict) -> dict:
    company = job.get("company") or {}
    locations = job.get("locations") or []
    categories = job.get("categories") or []
    levels = job.get("levels") or []
    refs = job.get("refs") or {}
    return {
        "external_id": str(job.get("id") or ""),
        "slug": job.get("short_name"),
        "title": (job.get("name") or "").strip(),
        "company_name": (company.get("short_name") or company.get("name") or "").strip()
        if isinstance(company, dict) else "",
        "location": ", ".join(
            (loc.get("name") or "").strip() for loc in locations if isinstance(loc, dict)
        ),
        "category": (categories[0].get("name") if categories and isinstance(categories[0], dict) else None),
        "level": (levels[0].get("name") if levels and isinstance(levels[0], dict) else None),
        "type": job.get("type"),
        "tags": [str(t.get("short_name") or t.get("name") or "").lower()
                 for t in (job.get("tags") or []) if isinstance(t, dict)],
        "description_html": (job.get("contents") or "").strip(),
        "publication_date": job.get("publication_date"),
        "url": refs.get("landing_page") if isinstance(refs, dict) else None,
        "source": "themuse",
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--max-pages", type=int, default=120,
                    help="Maximum number of pages to fetch (20 jobs/page)")
    ap.add_argument("--sleep", type=float, default=0.3,
                    help="Sleep seconds between page fetches")
    args = ap.parse_args(argv)

    seen: dict[str, dict] = {}
    page = 1
    last_total_pages = 0
    while page <= args.max_pages:
        rows, total_pages = fetch_page(page)
        if total_pages:
            last_total_pages = total_pages
        if not rows:
            print(f"themuse: page {page} returned no rows, stopping.")
            break
        added = 0
        for r in rows:
            nj = normalize(r)
            key = nj["external_id"] or (nj["title"] + "|" + nj["company_name"])
            if not key or key in seen:
                continue
            if not nj["title"] or not nj["company_name"]:
                continue
            seen[key] = nj
            added += 1
        print(f"themuse: page {page:>3}/{last_total_pages or '?'} +{added:>2} (total {len(seen)})")
        page += 1
        if page > (last_total_pages or args.max_pages):
            break
        time.sleep(args.sleep)
    out = list(seen.values())
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps(out, indent=2, ensure_ascii=False))
    print(f"themuse: wrote {len(out)} unique jobs to {OUT_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
