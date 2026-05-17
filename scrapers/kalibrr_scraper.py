"""Kalibrr.id job scraper.

Why this exists
---------------
The original seed data was hand-curated. To ship the app with *real*
Indonesian job listings, this script scrapes Kalibrr.id — a major
Indonesian job board that exposes Server-Side-Rendered (Next.js)
``__NEXT_DATA__`` JSON on each job-board category page.

Why Playwright (not plain requests)
-----------------------------------
Kalibrr fronts requests through Cloudflare. Plain ``requests`` /
``curl`` from many cloud IPs (including Devin's VM egress) get the
"Just a moment…" challenge page and never reach the real HTML. A real
browser (attached over CDP to a running Chrome) sails through.

Usage
-----
1. Make sure a Chrome instance is running with ``--remote-debugging-port=29229``.
   On Devin VMs this is the default. Outside Devin, start Chrome with::

       google-chrome --remote-debugging-port=29229 --user-data-dir=/tmp/cdp

2. Install Playwright (no need to install browser binaries, we attach
   to the existing Chrome)::

       pip install playwright

3. Run::

       python scrapers/kalibrr_scraper.py --max-jobs 250

Output
------
Writes a JSON file at ``scrapers/data/kalibrr_jobs.json`` containing a
list of unique jobs with the fields the importer needs.  Each entry
also keeps the original Kalibrr ``slug``/``id`` so the importer can
upsert idempotently.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import sys
import time
from pathlib import Path

try:
    from playwright.async_api import async_playwright
except ImportError:  # pragma: no cover - dependency missing
    print("ERROR: playwright not installed. Run: pip install playwright", file=sys.stderr)
    raise


# 21 job-board categories Kalibrr exposes for Indonesia. Each category
# page returns up to 15 jobs via __NEXT_DATA__. Pagination query params
# are ignored server-side (verified empirically), so we crawl categories
# in two variants (general + work-from-home) to maximise unique IDs.
CATEGORIES: list[str] = [
    "accounting-and-finance",
    "administration-and-coordination",
    "architecture-and-engineering",
    "arts-and-sports",
    "customer-service",
    "education-and-training",
    "general-services",
    "health-and-medical",
    "hospitality-and-tourism",
    "human-resources",
    "it-and-software",
    "legal",
    "management-and-consultancy",
    "manufacturing-and-production",
    "media-and-creatives",
    "public-service-and-ngos",
    "safety-and-security",
    "sales-and-marketing",
    "sciences",
    "supply-chain",
    "writing-and-content",
]


# Listing URLs that have produced unique jobs in probing.
def category_urls() -> list[str]:
    base = "https://www.kalibrr.id"
    urls: list[str] = [
        f"{base}/id-ID/job-board",  # main board (15 trending in ID)
        f"{base}/job-board/1",
    ]
    for c in CATEGORIES:
        urls.append(f"{base}/job-board/i/{c}/1")
    # work-from-home variants
    for c in CATEGORIES:
        urls.append(f"{base}/job-board/work_from_home/y/i/{c}/1")
    return urls


def normalize_job(j: dict) -> dict:
    """Pluck only the fields we need so the JSON dump is compact."""
    company = j.get("company") or {}
    gloc = (j.get("googleLocation") or {}).get("addressComponents") or {}
    return {
        "kalibrr_id": j.get("id"),
        "slug": j.get("slug"),
        "title": (j.get("name") or "").strip(),
        "description_html": j.get("description") or "",
        "qualifications_html": j.get("qualifications") or "",
        "function": j.get("function") or "",
        "tenure": j.get("tenure") or "",
        "work_experience_months": j.get("workExperience"),
        "is_wfh": bool(j.get("isWorkFromHome")),
        "is_hybrid": bool(j.get("isHybrid")),
        "is_open_to_fresh_grads": bool(j.get("isOpenToFreshGrads")),
        "number_of_openings": j.get("numberOfOpenings"),
        "salary_min": j.get("baseSalary"),
        "salary_max": j.get("maximumSalary"),
        "salary_currency": j.get("salaryCurrency"),
        "salary_interval": j.get("salaryInterval"),
        "salary_shown": bool(j.get("salaryShown")),
        "country": gloc.get("country"),
        "region": gloc.get("region"),
        "city": gloc.get("city"),
        "address": gloc.get("addressLine_1"),
        "activation_date": j.get("activationDate"),
        "application_end_date": j.get("applicationEndDate"),
        "company": {
            "code": company.get("code"),
            "name": company.get("name"),
            "industry": company.get("industry"),
            "description": company.get("description") or "",
            "logo_small": company.get("logoSmall"),
        },
        "url": (
            f"https://www.kalibrr.id/id-ID/c/{company.get('code')}"
            f"/jobs/{j.get('id')}/{j.get('slug') or ''}".rstrip("/")
        ),
    }


async def scrape(max_jobs: int = 250, per_url_wait_s: float = 2.0,
                 cdp_url: str = "http://localhost:29229") -> list[dict]:
    seen: dict[int, dict] = {}

    async with async_playwright() as p:
        browser = await p.chromium.connect_over_cdp(cdp_url)
        ctx = browser.contexts[0] if browser.contexts else await browser.new_context()
        page = await ctx.new_page()
        try:
            urls = category_urls()
            for idx, url in enumerate(urls):
                if len(seen) >= max_jobs:
                    print(f"[scrape] reached cap {max_jobs}, stopping early")
                    break
                t0 = time.time()
                try:
                    await page.goto(url, wait_until="domcontentloaded", timeout=45_000)
                except Exception as e:
                    print(f"[scrape] {url} — goto failed: {e!r}")
                    continue
                # Small wait for Cloudflare auto-pass / hydration.
                await asyncio.sleep(per_url_wait_s)
                try:
                    raw = await page.evaluate(
                        "() => document.querySelector('script#__NEXT_DATA__')?.textContent"
                        " || null"
                    )
                except Exception as e:
                    print(f"[scrape] {url} — eval failed: {e!r}")
                    continue
                if not raw:
                    print(f"[scrape] {url} — no NEXT_DATA")
                    continue
                try:
                    data = json.loads(raw)
                except Exception as e:
                    print(f"[scrape] {url} — bad JSON: {e!r}")
                    continue
                jobs = (data.get("props") or {}).get("pageProps", {}).get("jobs") or []
                new = 0
                for j in jobs:
                    jid = j.get("id")
                    if not jid or jid in seen:
                        continue
                    seen[jid] = normalize_job(j)
                    new += 1
                print(f"[{idx + 1:>2}/{len(urls)}] {url}  +{new} (total {len(seen)})"
                      f"  {time.time() - t0:.1f}s")
        finally:
            try:
                await page.close()
            except Exception:
                pass

    return list(seen.values())


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--max-jobs", type=int, default=250)
    ap.add_argument("--wait", type=float, default=2.0,
                    help="Seconds to wait per URL after load")
    ap.add_argument("--cdp", type=str, default="http://localhost:29229",
                    help="Chrome CDP endpoint")
    ap.add_argument("--out", type=Path,
                    default=Path(__file__).parent / "data" / "kalibrr_jobs.json")
    args = ap.parse_args()

    rows = asyncio.run(scrape(max_jobs=args.max_jobs,
                              per_url_wait_s=args.wait,
                              cdp_url=args.cdp))
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nWrote {len(rows)} jobs to {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
