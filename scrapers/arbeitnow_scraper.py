"""Scrape arbeitnow.com's public Job Board API.

Endpoint: ``GET https://www.arbeitnow.com/api/job-board-api?page=N``
Returns ``{"data": [...], "meta": {"current_page": N, "per_page": 100, ...}}``.
Pagination is by ``?page=``; empty ``data`` indicates we've reached the
end (typically ~14 pages = ~1400 jobs).

Output: ``scrapers/data/arbeitnow_jobs.json``.
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import urllib.request


API_URL = "https://www.arbeitnow.com/api/job-board-api"
OUT_PATH = Path(__file__).parent / "data" / "arbeitnow_jobs.json"


def fetch_page(page: int) -> list[dict]:
    url = f"{API_URL}?page={page}"
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "Mozilla/5.0 (compatible; RUMAH-KARIR-scraper/1.0)"},
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            payload = json.loads(resp.read())
    except Exception as exc:
        print(f"  page {page}: failed: {exc}", file=sys.stderr)
        return []
    return list(payload.get("data") or [])


def normalize(job: dict) -> dict:
    return {
        "external_id": str(job.get("slug") or ""),
        "slug": job.get("slug"),
        "title": (job.get("title") or "").strip(),
        "company_name": (job.get("company_name") or "").strip(),
        "location": (job.get("location") or "").strip(),
        "is_remote": bool(job.get("remote")),
        "tags": [str(t).lower() for t in (job.get("tags") or []) if t],
        "job_types": [str(t).lower() for t in (job.get("job_types") or []) if t],
        "description_html": (job.get("description") or "").strip(),
        "created_at": job.get("created_at"),
        "url": job.get("url"),
        "source": "arbeitnow",
    }


def main(argv: list[str] | None = None) -> int:
    argv = argv or sys.argv[1:]
    max_pages = int(argv[0]) if argv else 16
    all_jobs: list[dict] = []
    for page in range(1, max_pages + 1):
        rows = fetch_page(page)
        if not rows:
            print(f"arbeitnow: page {page} empty, stopping.")
            break
        all_jobs.extend(rows)
        print(f"arbeitnow: page {page} -> {len(rows)} jobs (total {len(all_jobs)})")
        time.sleep(0.5)
    out = [normalize(j) for j in all_jobs]
    out = [j for j in out if j["title"] and j["company_name"]]
    # Deduplicate by slug
    seen: set[str] = set()
    deduped = []
    for j in out:
        key = j["slug"] or j["title"] + "|" + j["company_name"]
        if key in seen:
            continue
        seen.add(key)
        deduped.append(j)
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps(deduped, indent=2, ensure_ascii=False))
    print(f"arbeitnow: wrote {len(deduped)} jobs to {OUT_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
