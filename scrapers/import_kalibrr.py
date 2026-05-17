"""Import scraped Kalibrr jobs into the cari-kerjaan SQLite database.

Reads ``scrapers/data/kalibrr_jobs.json`` (produced by
``scrapers/kalibrr_scraper.py``) and upserts companies + jobs into the
schema defined by ``backend/database.py``.

Idempotent: re-running this script will not duplicate companies or
jobs. Companies are matched case-insensitively by name; jobs are
matched by ``(company_id, title)``.

Usage::

    python scrapers/import_kalibrr.py
    python scrapers/import_kalibrr.py --reset-kalibrr   # delete jobs/companies previously imported by this script

Note: this only inserts Indonesia-based jobs by default; pass
``--include-other-countries`` to also import Philippines / international
postings that Kalibrr exposes.
"""
from __future__ import annotations

import argparse
import html
import json
import re
import sys
from pathlib import Path
from typing import Any

# Make sure we can import the Flask app + DB helpers no matter where the script
# is run from.
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app import create_app  # noqa: E402
from backend.database import execute, query_all, query_one  # noqa: E402


# Map Kalibrr workExperience bucket (100/200/300/400) -> min years experience.
EXPERIENCE_BUCKETS: dict[int, int] = {100: 0, 200: 1, 300: 3, 400: 5}

# Map Kalibrr tenure -> our employment_type vocabulary.
TENURE_MAP: dict[str, str] = {
    "Full time": "Full-time",
    "Part time": "Part-time",
    "Contractual": "Contract",
    "Freelance": "Freelance",
    "Internship": "Internship",
}

# Province name normalisation. Kalibrr is regionally inconsistent: some
# entries are pure English ("West Java"), others Indonesian ("Jawa Barat"),
# others bilingual with parens ("West Java (Jawa Barat)"). The app's UI
# (province dropdown, Indonesia map) uses the standard Indonesian names.
PROVINCE_MAP: dict[str, str] = {
    # Bilingual variants Kalibrr returns most often.
    "West Java (Jawa Barat)": "Jawa Barat",
    "Central Java (Jawa Tengah)": "Jawa Tengah",
    "East Java (Jawa Timur)": "Jawa Timur",
    "West Nusa Tenggara (Nusa Tenggara Barat)": "Nusa Tenggara Barat",
    "East Nusa Tenggara (Nusa Tenggara Timur)": "Nusa Tenggara Timur",
    "South Sumatra (Sumatra Selatan)": "Sumatera Selatan",
    "West Sumatra (Sumatra Barat)": "Sumatera Barat",
    "North Sumatra (Sumatra Utara)": "Sumatera Utara",
    "South Sulawesi (Sulawesi Selatan)": "Sulawesi Selatan",
    "North Sulawesi (Sulawesi Utara)": "Sulawesi Utara",
    "Central Sulawesi (Sulawesi Tengah)": "Sulawesi Tengah",
    "Central Kalimantan (Kalimantan Tengah)": "Kalimantan Tengah",
    "Southwest Papua (Papua Barat Daya)": "Papua Barat Daya",
    # English-only variants.
    "West Java": "Jawa Barat",
    "East Java": "Jawa Timur",
    "Central Java": "Jawa Tengah",
    "Special Region of Yogyakarta": "DI Yogyakarta",
    "Yogyakarta": "DI Yogyakarta",
    "North Sumatra": "Sumatera Utara",
    "South Sumatra": "Sumatera Selatan",
    "West Sumatra": "Sumatera Barat",
    "South Sulawesi": "Sulawesi Selatan",
    "North Sulawesi": "Sulawesi Utara",
    # Indonesian variants that already match.
    "Daerah Khusus Ibukota Jakarta": "DKI Jakarta",
    "Daerah Istimewa Yogyakarta": "DI Yogyakarta",
    "Jakarta": "DKI Jakarta",
    "Riau": "Riau",
    "Bali": "Bali",
    "Banten": "Banten",
    "DKI Jakarta": "DKI Jakarta",
}

# Map a city in DKI Jakarta back to the province if Kalibrr didn't set one.
JAKARTA_CITIES = {
    "Jakarta Pusat", "Jakarta Barat", "Jakarta Selatan",
    "Jakarta Timur", "Jakarta Utara", "Jakarta",
}

# City normalisation: Kalibrr returns "West Jakarta", "Central Jakarta",
# the app uses "Jakarta Barat", "Jakarta Pusat" etc.
CITY_MAP: dict[str, str] = {
    "West Jakarta": "Jakarta Barat",
    "Central Jakarta": "Jakarta Pusat",
    "South Jakarta": "Jakarta Selatan",
    "East Jakarta": "Jakarta Timur",
    "North Jakarta": "Jakarta Utara",
}


TAG_RE = re.compile(r"<[^>]+>")
WS_RE = re.compile(r"\s+\n|\n\s+")


def strip_html(s: str) -> str:
    """Convert simple HTML lists / paragraphs into readable plain text."""
    if not s:
        return ""
    # Treat </li> and </p> and <br> as line breaks
    s = re.sub(r"</(li|p|div|h[1-6])>", "\n", s, flags=re.I)
    s = re.sub(r"<br\s*/?>", "\n", s, flags=re.I)
    s = re.sub(r"<li[^>]*>", "• ", s, flags=re.I)
    s = TAG_RE.sub("", s)
    s = html.unescape(s)
    s = re.sub(r"\n{3,}", "\n\n", s)
    s = re.sub(r"[ \t]+\n", "\n", s)
    return s.strip()


def slugify(name: str) -> str:
    s = (name or "").lower()
    s = re.sub(r"[^a-z0-9]+", "-", s).strip("-")
    return s or "company"


def to_monthly_idr(amount: float | int | None, interval: str | None,
                   currency: str | None) -> int | None:
    if amount is None or currency != "IDR":
        return None
    try:
        amount = float(amount)
    except (TypeError, ValueError):
        return None
    iv = (interval or "month").lower()
    if iv in ("month", "monthly"):
        return int(round(amount))
    if iv in ("year", "annual", "annually"):
        return int(round(amount / 12))
    if iv in ("week", "weekly"):
        return int(round(amount * 4.33))
    if iv in ("day", "daily"):
        return int(round(amount * 22))
    if iv in ("hour", "hourly"):
        return int(round(amount * 22 * 8))
    return int(round(amount))


def find_or_create_company(c: dict[str, Any]) -> int:
    name = (c.get("name") or "").strip()
    if not name:
        return 0
    # Match case-insensitively by name to dedupe against hand-seeded entries.
    row = query_one(
        "SELECT id FROM companies WHERE LOWER(name) = LOWER(?) LIMIT 1",
        (name,),
    )
    if row:
        return int(row["id"])
    slug_base = (c.get("code") or "").strip() or slugify(name)
    # Ensure slug uniqueness.
    slug = slug_base
    suffix = 2
    while query_one("SELECT id FROM companies WHERE slug = ?", (slug,)):
        slug = f"{slug_base}-{suffix}"
        suffix += 1
    cid = execute(
        "INSERT INTO companies(name, slug, industry, description, country, "
        "is_approved, search_count) VALUES(?,?,?,?,?,?,?)",
        (
            name,
            slug,
            (c.get("industry") or "").strip() or None,
            strip_html(c.get("description") or "") or None,
            "Indonesia",
            1,
            0,
        ),
    )
    return int(cid)


def import_job(j: dict[str, Any], dry_run: bool = False) -> tuple[str, int | None]:
    """Return ('inserted'|'skipped'|'company_skip', job_id_or_None)."""
    company_id = find_or_create_company(j.get("company") or {})
    if not company_id:
        return "company_skip", None
    title = (j.get("title") or "").strip()
    if not title:
        return "skipped", None
    # Idempotency: skip if a job with same (company_id, title) exists.
    row = query_one(
        "SELECT id FROM jobs WHERE company_id = ? AND LOWER(title) = LOWER(?) LIMIT 1",
        (company_id, title),
    )
    if row:
        return "skipped", int(row["id"])

    employment_type = TENURE_MAP.get(j.get("tenure") or "", j.get("tenure") or None)
    region = PROVINCE_MAP.get(j.get("region") or "", j.get("region") or None)
    city = CITY_MAP.get(j.get("city") or "", j.get("city") or None)
    if not region and city in JAKARTA_CITIES:
        region = "DKI Jakarta"
    salary_min = to_monthly_idr(j.get("salary_min"), j.get("salary_interval"),
                                j.get("salary_currency"))
    salary_max = to_monthly_idr(j.get("salary_max"), j.get("salary_interval"),
                                j.get("salary_currency"))
    min_exp = EXPERIENCE_BUCKETS.get(j.get("work_experience_months") or 0, 0)
    description = strip_html(j.get("description_html") or "")
    requirements = strip_html(j.get("qualifications_html") or "")
    if j.get("url"):
        requirements = (requirements + "\n\nSumber: " + j["url"]).strip()
    if dry_run:
        return "inserted", None
    jid = execute(
        "INSERT INTO jobs(company_id, title, description, requirements, skills, "
        "employment_type, country, province, city, salary_min, salary_max, "
        "min_experience, is_active) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (
            company_id,
            title,
            description or None,
            requirements or None,
            None,
            employment_type,
            (j.get("country") or "Indonesia").strip(),
            region,
            city,
            salary_min,
            salary_max,
            min_exp,
            1,
        ),
    )
    return "inserted", int(jid)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", type=Path,
                    default=Path(__file__).parent / "data" / "kalibrr_jobs.json")
    ap.add_argument("--include-other-countries", action="store_true",
                    help="Also import non-Indonesia jobs (Kalibrr is regional)")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    if not args.data.exists():
        print(f"ERROR: dataset not found at {args.data}\n"
              f"Run scrapers/kalibrr_scraper.py first.", file=sys.stderr)
        return 1
    jobs = json.loads(args.data.read_text(encoding="utf-8"))
    print(f"Loaded {len(jobs)} jobs from {args.data}")
    if not args.include_other_countries:
        jobs = [j for j in jobs if (j.get("country") or "") == "Indonesia"]
        print(f"After country=Indonesia filter: {len(jobs)} jobs")

    app = create_app()
    with app.app_context():
        before_companies = query_one("SELECT COUNT(*) AS n FROM companies")["n"]
        before_jobs = query_one("SELECT COUNT(*) AS n FROM jobs")["n"]
        inserted = skipped = 0
        for j in jobs:
            status, _ = import_job(j, dry_run=args.dry_run)
            if status == "inserted":
                inserted += 1
            else:
                skipped += 1
        after_companies = query_one("SELECT COUNT(*) AS n FROM companies")["n"]
        after_jobs = query_one("SELECT COUNT(*) AS n FROM jobs")["n"]
    print(f"\nResult:")
    print(f"  jobs inserted: {inserted}, skipped (duplicate): {skipped}")
    print(f"  companies: {before_companies} -> {after_companies}")
    print(f"  jobs:      {before_jobs} -> {after_jobs}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
