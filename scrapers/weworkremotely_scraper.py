"""Scrape WeWorkRemotely.com RSS feeds.

WWR publishes per-category RSS feeds plus a master feed. We pull from
each feed and merge results. The data is XML; we parse with the
stdlib ``xml.etree`` module.

Output: ``scrapers/data/wwr_jobs.json``.
"""
from __future__ import annotations

import json
import re
import sys
import time
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path


FEEDS = [
    "https://weworkremotely.com/remote-jobs.rss",
    "https://weworkremotely.com/categories/remote-programming-jobs.rss",
    "https://weworkremotely.com/categories/remote-design-jobs.rss",
    "https://weworkremotely.com/categories/remote-customer-support-jobs.rss",
    "https://weworkremotely.com/categories/remote-sales-and-marketing-jobs.rss",
    "https://weworkremotely.com/categories/remote-management-and-finance-jobs.rss",
    "https://weworkremotely.com/categories/remote-product-jobs.rss",
    "https://weworkremotely.com/categories/all-other-remote-jobs.rss",
]
OUT_PATH = Path(__file__).parent / "data" / "wwr_jobs.json"


def fetch_feed(url: str) -> list[dict]:
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "Mozilla/5.0 (compatible; RUMAH-KARIR-scraper/1.0)"},
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            xml_bytes = resp.read()
    except Exception as exc:
        print(f"  wwr fetch failed {url}: {exc}", file=sys.stderr)
        return []
    try:
        root = ET.fromstring(xml_bytes)
    except ET.ParseError as exc:
        print(f"  wwr parse failed {url}: {exc}", file=sys.stderr)
        return []
    items = []
    for item in root.iter("item"):
        title = (item.findtext("title") or "").strip()
        link = (item.findtext("link") or "").strip()
        desc = (item.findtext("description") or "").strip()
        pub = (item.findtext("pubDate") or "").strip()
        region = (item.findtext("region") or "").strip()
        # Title is typically "Company Name: Job Title"
        company = ""
        job_title = title
        if ":" in title:
            company, _, job_title = title.partition(":")
            company = company.strip()
            job_title = job_title.strip()
        items.append({
            "title": job_title,
            "company": company,
            "description_html": desc,
            "url": link,
            "region": region,
            "pub_date": pub,
        })
    return items


def main() -> int:
    all_jobs: dict[str, dict] = {}
    for feed in FEEDS:
        rows = fetch_feed(feed)
        new = 0
        for r in rows:
            if not r["title"] or not r["company"]:
                continue
            key = r["url"] or (r["title"] + "|" + r["company"])
            if key in all_jobs:
                continue
            r["source"] = "wwr"
            all_jobs[key] = r
            new += 1
        print(f"wwr: {feed.split('/')[-1]:<45} +{new:>3} (total {len(all_jobs)})")
        time.sleep(0.4)
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps(list(all_jobs.values()), indent=2, ensure_ascii=False))
    print(f"wwr: wrote {len(all_jobs)} unique jobs to {OUT_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
