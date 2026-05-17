"""Deeper Kalibrr scrape — adds per-city URLs to expand coverage.

This complements ``kalibrr_scraper.py`` (which sweeps the 21 job-board
categories) by also sweeping Kalibrr's per-city pages for ~25 Indonesian
cities. Each city page returns up to 15 jobs via ``__NEXT_DATA__``.

Output is appended to the same data file produced by the main scraper
so the importer can pick everything up in one run.
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
except ImportError:  # pragma: no cover
    print("ERROR: playwright not installed. Run: pip install playwright", file=sys.stderr)
    raise

# Reuse the normaliser from the main scraper for consistency.
sys.path.insert(0, str(Path(__file__).parent))
from kalibrr_scraper import normalize_job, CATEGORIES  # type: ignore  # noqa: E402


# Major Indonesian cities (Kalibrr URL slugs). Cities are matched against
# Kalibrr's location index — if a slug doesn't resolve, the page simply
# returns no jobs and we move on.
CITIES: list[str] = [
    "jakarta", "surabaya", "bandung", "medan", "semarang", "palembang",
    "makassar", "tangerang", "depok", "bekasi", "batam", "bogor",
    "pekanbaru", "malang", "denpasar", "yogyakarta", "manado",
    "balikpapan", "samarinda", "banjarmasin", "pontianak", "padang",
    "jambi", "bandar-lampung", "solo",
]


def build_urls() -> list[str]:
    base = "https://www.kalibrr.id"
    urls: list[str] = []
    # Per-city home pages
    for city in CITIES:
        urls.append(f"{base}/id-ID/home/jobs/{city}")
    # Per-category + per-city (only top cities to keep run time tractable)
    top_cities = CITIES[:6]
    for c in CATEGORIES:
        for city in top_cities:
            urls.append(f"{base}/id-ID/home/jobs/{city}?industry={c}")
    return urls


async def scrape(max_jobs: int, per_url_wait_s: float, cdp_url: str,
                 existing_ids: set[int]) -> list[dict]:
    new_jobs: dict[int, dict] = {}

    async with async_playwright() as p:
        browser = await p.chromium.connect_over_cdp(cdp_url)
        ctx = browser.contexts[0] if browser.contexts else await browser.new_context()
        page = await ctx.new_page()
        urls = build_urls()
        try:
            for idx, url in enumerate(urls):
                if len(new_jobs) >= max_jobs:
                    print(f"[deep] reached cap {max_jobs}")
                    break
                t0 = time.time()
                try:
                    await page.goto(url, wait_until="domcontentloaded", timeout=45_000)
                except Exception as e:
                    print(f"[deep] {url} — goto failed: {e!r}")
                    continue
                await asyncio.sleep(per_url_wait_s)
                try:
                    raw = await page.evaluate(
                        "() => document.querySelector('script#__NEXT_DATA__')?.textContent"
                        " || null"
                    )
                except Exception as e:
                    print(f"[deep] {url} — eval failed: {e!r}")
                    continue
                if not raw:
                    continue
                try:
                    data = json.loads(raw)
                except Exception:
                    continue
                # Per-city pages put the jobs under different keys; try a few.
                page_props = (data.get("props") or {}).get("pageProps") or {}
                jobs = (
                    page_props.get("jobs")
                    or page_props.get("initialJobs")
                    or page_props.get("homePageJobs")
                    or []
                )
                if isinstance(jobs, dict):
                    jobs = jobs.get("results") or []
                new_here = 0
                for j in jobs:
                    jid = j.get("id")
                    if not jid or jid in existing_ids or jid in new_jobs:
                        continue
                    new_jobs[jid] = normalize_job(j)
                    new_here += 1
                print(f"[{idx + 1:>3}/{len(urls)}] {url}  +{new_here} "
                      f"(deep total {len(new_jobs)})  {time.time() - t0:.1f}s")
        finally:
            try:
                await page.close()
            except Exception:
                pass

    return list(new_jobs.values())


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--max-jobs", type=int, default=400)
    ap.add_argument("--wait", type=float, default=1.6)
    ap.add_argument("--cdp", type=str, default="http://localhost:29229")
    ap.add_argument(
        "--data-file",
        type=Path,
        default=Path(__file__).parent / "data" / "kalibrr_jobs.json",
        help="Existing Kalibrr data file; new jobs are merged in.",
    )
    args = ap.parse_args()

    existing: list[dict] = []
    existing_ids: set[int] = set()
    if args.data_file.exists():
        existing = json.loads(args.data_file.read_text(encoding="utf-8"))
        existing_ids = {j["kalibrr_id"] for j in existing if j.get("kalibrr_id")}
        print(f"[deep] loaded {len(existing)} existing jobs (skip ids)")

    new_jobs = asyncio.run(
        scrape(args.max_jobs, args.wait, args.cdp, existing_ids)
    )
    merged = existing + new_jobs
    args.data_file.parent.mkdir(parents=True, exist_ok=True)
    args.data_file.write_text(
        json.dumps(merged, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(
        f"\n[deep] +{len(new_jobs)} new jobs -> {args.data_file} "
        f"(now {len(merged)} total)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
