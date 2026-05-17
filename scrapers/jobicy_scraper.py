"""Scrape Jobicy's free public REST API for remote jobs.

Endpoint: ``GET https://jobicy.com/api/v2/remote-jobs?count=100[&industry=...][&geo=...]``

Jobicy caps a single call at 100 results, but supports many filters.
We sweep across a broad set of industries to maximise coverage.

Output: ``scrapers/data/jobicy_jobs.json``.
"""
from __future__ import annotations

import json
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path


API_URL = "https://jobicy.com/api/v2/remote-jobs"
OUT_PATH = Path(__file__).parent / "data" / "jobicy_jobs.json"


# Industries supported by Jobicy (subset that have ≥10 jobs each).
INDUSTRIES = [
    "all", "marketing", "design", "sales", "data-science",
    "human-resources", "copywriting", "supporting", "business",
    "management", "finance-and-legal", "qa-testing", "devops-and-sysadmin",
    "engineering-and-tech", "product",
]


def fetch(industry: str, count: int = 100) -> list[dict]:
    params = {"count": count}
    if industry and industry != "all":
        params["industry"] = industry
    url = f"{API_URL}?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "Mozilla/5.0 (compatible; RUMAH-KARIR-scraper/1.0)"},
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            data = json.loads(resp.read())
    except Exception as exc:
        print(f"  jobicy fetch failed for {industry}: {exc}", file=sys.stderr)
        return []
    return list(data.get("jobs") or [])


def normalize(job: dict) -> dict:
    return {
        "external_id": str(job.get("id") or ""),
        "slug": job.get("jobSlug"),
        "title": (job.get("jobTitle") or "").strip(),
        "company_name": (job.get("companyName") or "").strip(),
        "company_logo": job.get("companyLogo"),
        "industry": job.get("jobIndustry"),
        "job_type": job.get("jobType"),
        "location": job.get("jobGeo"),
        "level": job.get("jobLevel"),
        "excerpt": (job.get("jobExcerpt") or "").strip(),
        "description_html": (job.get("jobDescription") or "").strip(),
        "salary_min": job.get("salaryMin"),
        "salary_max": job.get("salaryMax"),
        "salary_currency": job.get("salaryCurrency"),
        "salary_period": job.get("salaryPeriod"),
        "pub_date": job.get("pubDate"),
        "url": job.get("url"),
        "source": "jobicy",
    }


def main() -> int:
    all_jobs: dict[str, dict] = {}  # by external_id
    for ind in INDUSTRIES:
        rows = fetch(ind, 100)
        added = 0
        for r in rows:
            nj = normalize(r)
            key = nj["external_id"] or nj["slug"]
            if not key or key in all_jobs:
                continue
            if not nj["title"] or not nj["company_name"]:
                continue
            all_jobs[key] = nj
            added += 1
        print(f"jobicy: industry={ind:>22}  fetched={len(rows):>3}  new={added:>3}  total={len(all_jobs)}")
        time.sleep(0.4)
    out = list(all_jobs.values())
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps(out, indent=2, ensure_ascii=False))
    print(f"jobicy: wrote {len(out)} unique jobs to {OUT_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
