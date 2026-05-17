"""Scrape Remotive.com's public remote-jobs API.

Endpoint: ``GET https://remotive.com/api/remote-jobs``
Returns ``{"job-count": N, "jobs": [...]}`` — Remotive returns the
whole active corpus in one response (currently ~1500 active listings),
so no pagination is needed. We can also filter by ``category`` and
``search`` but the unfiltered list already covers everything.

Output: ``scrapers/data/remotive_jobs.json``.
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


API_URL = "https://remotive.com/api/remote-jobs"
OUT_PATH = Path(__file__).parent / "data" / "remotive_jobs.json"


# Remotive lets us filter by category which lifts the per-category cap.
# We sweep every public category to make sure we never miss listings.
CATEGORIES = [
    "",  # also fetch unfiltered to catch anything new
    "software-dev", "customer-support", "design", "marketing", "sales",
    "product", "business", "data", "devops", "finance-legal", "hr",
    "qa", "writing", "all-others",
]


def fetch(category: str = "") -> list[dict]:
    params: dict[str, object] = {}
    if category:
        params["category"] = category
    url = API_URL
    if params:
        url = f"{API_URL}?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "Mozilla/5.0 (compatible; RUMAH-KARIR-scraper/1.0)"},
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            payload = json.loads(resp.read())
    except urllib.error.HTTPError as exc:
        print(f"  remotive: HTTP {exc.code} for category='{category}'", file=sys.stderr)
        return []
    except Exception as exc:
        print(f"  remotive: fetch failed for '{category}': {exc}", file=sys.stderr)
        return []
    return list(payload.get("jobs") or [])


def normalize(job: dict) -> dict:
    tags = [str(t).lower() for t in (job.get("tags") or []) if t]
    return {
        "external_id": str(job.get("id") or ""),
        "slug": (job.get("url") or "").rstrip("/").rsplit("/", 1)[-1] or None,
        "title": (job.get("title") or "").strip(),
        "company_name": (job.get("company_name") or "").strip(),
        "company_logo": job.get("company_logo") or job.get("company_logo_url"),
        "category": job.get("category"),
        "job_type": job.get("job_type"),
        "tags": tags,
        "location": (job.get("candidate_required_location") or "").strip() or "Remote",
        "is_remote": True,
        "description_html": (job.get("description") or "").strip(),
        "salary": job.get("salary"),
        "publication_date": job.get("publication_date"),
        "url": job.get("url"),
        "source": "remotive",
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--sleep", type=float, default=0.5,
                    help="Sleep seconds between category fetches")
    args = ap.parse_args(argv)

    seen: dict[str, dict] = {}
    for cat in CATEGORIES:
        rows = fetch(cat)
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
        print(f"remotive: cat='{cat or 'all':<18}' fetched={len(rows):>4} new={added:>4} total={len(seen)}")
        time.sleep(args.sleep)

    out = list(seen.values())
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps(out, indent=2, ensure_ascii=False))
    print(f"remotive: wrote {len(out)} unique jobs to {OUT_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
