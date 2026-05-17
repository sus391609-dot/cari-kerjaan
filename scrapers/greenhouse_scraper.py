"""Scrape Greenhouse public Job Boards for well-known companies.

Greenhouse exposes a free public REST API for every company that uses
their job board. Pattern::

    GET https://boards-api.greenhouse.io/v1/boards/{board_slug}/jobs?content=true

The response is ``{"jobs": [...], "meta": {"total": N}}`` and is not
paginated — all currently-open requisitions are returned in a single
response (typical sizes range from 50 to 800 per company).

This script sweeps a curated list of companies that publish on
Greenhouse. The board slugs are stable; companies that have closed
their board return an empty list and we skip them gracefully.

Output: ``scrapers/data/greenhouse_jobs.json``.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path


BASE = "https://boards-api.greenhouse.io/v1/boards"
OUT_PATH = Path(__file__).parent / "data" / "greenhouse_jobs.json"


# Curated list of board slugs that we know are live (verified Nov 2025).
# These cover a broad set of industries: e-commerce, fintech, cloud,
# devtools, dev platforms, design, B2B SaaS, biotech, etc.
COMPANIES: list[tuple[str, str, str | None]] = [
    # (board_slug, display_name, industry hint)
    ("airbnb", "Airbnb", "Travel & Hospitality"),
    ("stripe", "Stripe", "Fintech"),
    ("robinhood", "Robinhood", "Fintech"),
    ("instacart", "Instacart", "E-commerce"),
    ("lyft", "Lyft", "Transportation"),
    ("gitlab", "GitLab", "DevOps"),
    ("asana", "Asana", "SaaS"),
    ("intercom", "Intercom", "SaaS"),
    ("databricks", "Databricks", "Data Platform"),
    ("cloudflare", "Cloudflare", "Cloud"),
    ("reddit", "Reddit", "Social Media"),
    ("pinterest", "Pinterest", "Social Media"),
    ("datadog", "Datadog", "Cloud / Observability"),
    ("mongodb", "MongoDB", "Data Platform"),
    ("dropbox", "Dropbox", "Cloud"),
    ("twilio", "Twilio", "Cloud / Communications"),
    ("hubspot", "HubSpot", "SaaS / Marketing"),
    ("squareup", "Block (Square)", "Fintech"),
    ("plaid", "Plaid", "Fintech"),
    ("affirm", "Affirm", "Fintech"),
    ("snyk", "Snyk", "Cybersecurity"),
    ("samsara", "Samsara", "IoT"),
    ("anduril", "Anduril", "Defense Tech"),
    ("scaleai", "Scale AI", "Machine Learning"),
    ("openai", "OpenAI", "Machine Learning"),
    ("anthropic", "Anthropic", "Machine Learning"),
    ("brex", "Brex", "Fintech"),
    ("chime", "Chime", "Fintech"),
    ("ramp", "Ramp", "Fintech"),
    ("benchling", "Benchling", "Biotech SaaS"),
    ("retool", "Retool", "DevTools"),
    ("vercel", "Vercel", "DevTools"),
    ("supabase", "Supabase", "DevTools"),
    ("hashicorp", "HashiCorp", "DevOps"),
    ("circleci", "CircleCI", "DevOps"),
    ("buildkite", "Buildkite", "DevOps"),
    ("fastly", "Fastly", "Cloud"),
    ("digitalocean", "DigitalOcean", "Cloud"),
    ("paloalto", "Palo Alto Networks", "Cybersecurity"),
    ("zscaler", "Zscaler", "Cybersecurity"),
    ("crowdstrike", "CrowdStrike", "Cybersecurity"),
    ("okta", "Okta", "Identity"),
    ("auth0", "Auth0", "Identity"),
    ("amplitude", "Amplitude", "Analytics"),
    ("segment", "Segment", "Analytics"),
    ("mixpanel", "Mixpanel", "Analytics"),
    ("zapier", "Zapier", "Automation"),
    ("monzo", "Monzo", "Fintech"),
    ("revolut", "Revolut", "Fintech"),
    ("wise", "Wise", "Fintech"),
    ("klarna", "Klarna", "Fintech"),
    ("bumble", "Bumble", "Social"),
    ("rippling", "Rippling", "HR Tech"),
    ("gusto", "Gusto", "HR Tech"),
    ("toast", "Toast", "Restaurant Tech"),
    ("squarespace", "Squarespace", "Web Tools"),
    ("wayfair", "Wayfair", "E-commerce"),
    ("etsy", "Etsy", "E-commerce"),
    ("ebay", "eBay", "E-commerce"),
    ("walmart", "Walmart Global Tech", "Retail"),
    ("warbyparker", "Warby Parker", "Retail"),
    ("peloton", "Peloton", "Connected Fitness"),
    ("ginkgobioworks", "Ginkgo Bioworks", "Biotech"),
    ("oscar", "Oscar Health", "HealthTech"),
    ("flexport", "Flexport", "Logistics"),
    ("convoy", "Convoy", "Logistics"),
    ("rivian", "Rivian", "Automotive"),
    ("lucid", "Lucid Motors", "Automotive"),
    ("spacex", "SpaceX", "Aerospace"),
    ("relativity", "Relativity Space", "Aerospace"),
    ("opensea", "OpenSea", "Web3"),
    ("alchemy", "Alchemy", "Web3"),
    ("blockchain", "Blockchain.com", "Web3"),
    ("circle", "Circle", "Fintech / Web3"),
    ("kraken", "Kraken Digital Asset Exchange", "Crypto"),
    ("gemini", "Gemini", "Crypto"),
    ("paxos", "Paxos", "Fintech"),
    ("plenty", "Plenty", "AgriTech"),
    ("nuro", "Nuro", "Robotics"),
    ("scaleai", "Scale AI", "Machine Learning"),
    ("airwallex", "Airwallex", "Fintech"),
    ("traveloka", "Traveloka", "Travel"),
    ("gojek", "Gojek", "Super App"),
    ("kredivocorp", "Kredivo", "Fintech"),
    ("flip", "Flip", "Fintech"),
    ("paper", "Paper", "EdTech"),
    ("classdojo", "ClassDojo", "EdTech"),
    ("course-hero", "Course Hero", "EdTech"),
    ("masterclass", "MasterClass", "EdTech"),
    ("quizlet", "Quizlet", "EdTech"),
    ("calm", "Calm", "Wellness"),
    ("headspace", "Headspace", "Wellness"),
    ("livongo", "Livongo", "HealthTech"),
    ("forhims", "Hims & Hers", "HealthTech"),
    ("rocheinternal", "Roche", "Pharma"),
    ("epicgames", "Epic Games", "Gaming"),
    ("riotgames", "Riot Games", "Gaming"),
    ("unity3d", "Unity", "Gaming"),
    ("zynga", "Zynga", "Gaming"),
    ("twitch", "Twitch", "Streaming"),
    ("spotify", "Spotify", "Streaming"),
    ("hellofresh", "HelloFresh", "Food Tech"),
    ("doordashessentials", "DoorDash", "Food Delivery"),
    ("ubereats", "Uber Eats", "Food Delivery"),
    ("openaiapplied", "OpenAI", "Machine Learning"),
    ("character", "Character.AI", "Machine Learning"),
    ("perplexity", "Perplexity", "Machine Learning"),
    ("huggingface", "Hugging Face", "Machine Learning"),
    ("cohere", "Cohere", "Machine Learning"),
    ("runway", "Runway ML", "Machine Learning"),
    ("midjourney", "Midjourney", "Creative AI"),
    ("eleutherai", "EleutherAI", "Machine Learning"),
    ("groq", "Groq", "AI Hardware"),
    ("cerebrastechnology", "Cerebras", "AI Hardware"),
    ("samsung", "Samsung NEXT", "Conglomerate"),
    ("instabase", "Instabase", "Enterprise AI"),
    ("verily", "Verily", "Health Tech"),
    ("alphasights", "AlphaSights", "Research"),
    ("twosigma", "Two Sigma", "Quant Trading"),
    ("citadel", "Citadel", "Hedge Fund"),
    ("hudsonriverlab", "Hudson River Trading", "Quant Trading"),
    ("janestreet", "Jane Street", "Quant Trading"),
    ("optiver", "Optiver", "Quant Trading"),
    ("imc", "IMC Trading", "Quant Trading"),
    ("akunaholdings", "Akuna Capital", "Quant Trading"),
    ("flowtraders", "Flow Traders", "Quant Trading"),
    ("alibaba", "Alibaba", "E-commerce"),
    ("bytedance", "ByteDance", "Social Media"),
    ("tiktok", "TikTok", "Social Media"),
]


def fetch(board_slug: str, *, with_content: bool = True) -> list[dict]:
    url = f"{BASE}/{board_slug}/jobs"
    if with_content:
        url += "?content=true"
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "Mozilla/5.0 (compatible; RUMAH-KARIR-scraper/1.0)"},
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            payload = json.loads(resp.read())
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            return []
        print(f"  greenhouse: HTTP {exc.code} for '{board_slug}'", file=sys.stderr)
        return []
    except Exception as exc:
        print(f"  greenhouse: fetch failed for '{board_slug}': {exc}", file=sys.stderr)
        return []
    return list(payload.get("jobs") or [])


def normalize(job: dict, *, company_name: str, industry: str | None) -> dict:
    offices = job.get("offices") or []
    departments = job.get("departments") or []
    loc = (job.get("location") or {}).get("name") if isinstance(job.get("location"), dict) else None
    return {
        "external_id": str(job.get("id") or ""),
        "title": (job.get("title") or "").strip(),
        "company_name": company_name,
        "industry": industry,
        "location": (loc or "").strip() or "Remote",
        "offices": [o.get("name") for o in offices if isinstance(o, dict) and o.get("name")],
        "departments": [d.get("name") for d in departments if isinstance(d, dict) and d.get("name")],
        "description_html": (job.get("content") or "").strip(),
        "url": job.get("absolute_url"),
        "updated_at": job.get("updated_at"),
        "first_published": job.get("first_published"),
        "source": "greenhouse",
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--sleep", type=float, default=0.4,
                    help="Sleep seconds between company fetches")
    ap.add_argument("--max-per-company", type=int, default=600,
                    help="Cap how many jobs to keep per board (avoid imbalance)")
    args = ap.parse_args(argv)

    seen: dict[str, dict] = {}
    seen_companies: set[str] = set()
    for slug, display, industry in COMPANIES:
        if slug in seen_companies:
            continue
        seen_companies.add(slug)
        rows = fetch(slug)
        if not rows:
            print(f"greenhouse: {slug:<30} no jobs (skipped)")
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
        print(f"greenhouse: {slug:<30} fetched={len(rows):>4} new={added:>4} total={len(seen)}")
        time.sleep(args.sleep)

    out = list(seen.values())
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps(out, indent=2, ensure_ascii=False))
    print(f"greenhouse: wrote {len(out)} unique jobs to {OUT_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
