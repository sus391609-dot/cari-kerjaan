"""Scrape RemoteOK's free public API.

Endpoint: ``GET https://remoteok.com/api`` returns a JSON array. The
first element is a meta/legal disclaimer; the rest are job records.

Output: ``scrapers/data/remoteok_jobs.json`` (newline-pretty JSON list).
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import urllib.request


API_URL = "https://remoteok.com/api"
OUT_PATH = Path(__file__).parent / "data" / "remoteok_jobs.json"


def fetch() -> list[dict]:
    req = urllib.request.Request(
        API_URL,
        headers={"User-Agent": "Mozilla/5.0 (compatible; RUMAH-KARIR-scraper/1.0)"},
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = json.loads(resp.read())
    # Skip the meta entry (no 'position' key)
    return [j for j in data if isinstance(j, dict) and j.get("position")]


def normalize(job: dict) -> dict:
    return {
        "external_id": str(job.get("id") or job.get("slug") or ""),
        "slug": job.get("slug"),
        "title": (job.get("position") or "").strip(),
        "company_name": (job.get("company") or "").strip(),
        "company_logo": job.get("company_logo") or job.get("logo"),
        "location": (job.get("location") or "").strip(),
        "is_remote": True,
        "tags": [str(t).lower() for t in (job.get("tags") or []) if t],
        "description_html": (job.get("description") or "").strip(),
        "salary_min": job.get("salary_min") or None,
        "salary_max": job.get("salary_max") or None,
        "salary_currency": "USD" if job.get("salary_min") else None,
        "epoch": job.get("epoch"),
        "date": job.get("date"),
        "url": job.get("url") or job.get("apply_url"),
        "source": "remoteok",
    }


def main(argv: list[str] | None = None) -> int:
    argv = argv or sys.argv[1:]
    raw = fetch()
    out = [normalize(j) for j in raw]
    out = [j for j in out if j["title"] and j["company_name"]]
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps(out, indent=2, ensure_ascii=False))
    print(f"RemoteOK: wrote {len(out)} jobs to {OUT_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
