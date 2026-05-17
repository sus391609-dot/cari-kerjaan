"""Scrape Lever public job postings for well-known companies.

Lever exposes a free public REST API per company. Pattern::

    GET https://api.lever.co/v0/postings/{company}?mode=json

The response is a JSON array. All currently-open postings are returned
in one response; we don't need to paginate.

Output: ``scrapers/data/lever_jobs.json``.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path


BASE = "https://api.lever.co/v0/postings"
OUT_PATH = Path(__file__).parent / "data" / "lever_jobs.json"


COMPANIES: list[tuple[str, str, str | None]] = [
    # (lever_slug, display_name, industry hint)
    ("spotify", "Spotify", "Streaming"),
    ("netflix", "Netflix", "Streaming"),
    ("github", "GitHub", "DevTools"),
    ("figma", "Figma", "Design SaaS"),
    ("notion", "Notion", "Productivity"),
    ("airtable", "Airtable", "SaaS"),
    ("box", "Box", "Cloud Storage"),
    ("yelp", "Yelp", "Local Search"),
    ("eventbrite", "Eventbrite", "Events"),
    ("kickstarter", "Kickstarter", "Crowdfunding"),
    ("medium", "Medium", "Publishing"),
    ("turo", "Turo", "Travel"),
    ("zola", "Zola", "Consumer"),
    ("kraken", "Kraken", "Crypto"),
    ("toast", "Toast", "Restaurant Tech"),
    ("clio", "Clio", "Legal Tech"),
    ("samsara", "Samsara", "IoT"),
    ("highspot", "Highspot", "Sales Tech"),
    ("airwallex", "Airwallex", "Fintech"),
    ("monzo", "Monzo", "Fintech"),
    ("revolut", "Revolut", "Fintech"),
    ("hopin", "Hopin", "Events"),
    ("attentive", "Attentive", "Marketing"),
    ("vroom", "Vroom", "Automotive"),
    ("zip", "Zip", "Fintech"),
    ("envoy", "Envoy", "Workplace SaaS"),
    ("matterport", "Matterport", "3D Tech"),
    ("blueprintsystems", "Blueprint Systems", "Cloud"),
    ("trumid", "Trumid", "Fintech"),
    ("policygenius", "Policygenius", "InsurTech"),
    ("upstart", "Upstart", "Fintech"),
    ("klue", "Klue", "Sales Tech"),
    ("podium", "Podium", "Customer Comms"),
    ("loop-returns", "Loop Returns", "E-commerce SaaS"),
    ("eaglestratbio", "EagleStratBio", "Biotech"),
    ("color", "Color Health", "HealthTech"),
    ("medely", "Medely", "HealthTech"),
    ("modernhealth", "Modern Health", "HealthTech"),
    ("upgrade", "Upgrade", "Fintech"),
    ("paystack", "Paystack", "Fintech"),
    ("flutterwave", "Flutterwave", "Fintech"),
    ("kueski", "Kueski", "Fintech"),
    ("clipboardhealth", "Clipboard Health", "Health Staffing"),
    ("workrise", "Workrise", "Staffing"),
    ("ankorstore", "Ankorstore", "B2B Marketplace"),
    ("typeform", "Typeform", "SaaS"),
    ("contentful", "Contentful", "Headless CMS"),
    ("getyourguide", "GetYourGuide", "Travel"),
    ("hotjar", "Hotjar", "Analytics"),
    ("zwift", "Zwift", "Gaming / Fitness"),
    ("mistral", "Mistral AI", "Machine Learning"),
    ("anyscale", "Anyscale", "Machine Learning"),
    ("weightsandbiases", "Weights & Biases", "Machine Learning"),
]


def fetch(slug: str) -> list[dict]:
    url = f"{BASE}/{slug}?mode=json"
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "Mozilla/5.0 (compatible; RUMAH-KARIR-scraper/1.0)"},
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            data = json.loads(resp.read())
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            return []
        print(f"  lever: HTTP {exc.code} for '{slug}'", file=sys.stderr)
        return []
    except Exception as exc:
        print(f"  lever: fetch failed for '{slug}': {exc}", file=sys.stderr)
        return []
    if not isinstance(data, list):
        return []
    return data


def normalize(job: dict, *, company_name: str, industry: str | None) -> dict:
    cats = job.get("categories") or {}
    return {
        "external_id": str(job.get("id") or ""),
        "title": (job.get("text") or "").strip(),
        "company_name": company_name,
        "industry": industry,
        "location": (cats.get("location") or "").strip() or "Remote",
        "team": cats.get("team"),
        "commitment": cats.get("commitment"),
        "department": cats.get("department"),
        "level": cats.get("allLocations") if isinstance(cats.get("allLocations"), str) else None,
        "description_html": (job.get("descriptionPlain") or job.get("description") or "").strip(),
        "url": job.get("hostedUrl"),
        "created_at": job.get("createdAt"),
        "source": "lever",
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--sleep", type=float, default=0.4,
                    help="Sleep seconds between company fetches")
    ap.add_argument("--max-per-company", type=int, default=500,
                    help="Cap how many jobs to keep per board")
    args = ap.parse_args(argv)

    seen: dict[str, dict] = {}
    for slug, display, industry in COMPANIES:
        rows = fetch(slug)
        if not rows:
            print(f"lever: {slug:<22} no jobs (skipped)")
            time.sleep(args.sleep)
            continue
        rows = rows[: args.max_per_company]
        added = 0
        for r in rows:
            nj = normalize(r, company_name=display, industry=industry)
            key = nj["external_id"] or (nj["title"] + "|" + display)
            if not key or key in seen:
                continue
            if not nj["title"]:
                continue
            seen[key] = nj
            added += 1
        print(f"lever: {slug:<22} fetched={len(rows):>4} new={added:>4} total={len(seen)}")
        time.sleep(args.sleep)

    out = list(seen.values())
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps(out, indent=2, ensure_ascii=False))
    print(f"lever: wrote {len(out)} unique jobs to {OUT_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
