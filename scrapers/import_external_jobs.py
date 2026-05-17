"""Import jobs scraped from RemoteOK, arbeitnow, and Adzuna into the
RUMAH KARIR database.

Reads:
  - ``scrapers/data/remoteok_jobs.json``
  - ``scrapers/data/arbeitnow_jobs.json``
  - ``scrapers/data/adzuna_jobs.json``

Inserts companies + jobs idempotently (same dedup strategy as
``import_kalibrr.py``: company by case-insensitive name, job by
``(company_id, title)``).

Currency conversion:
  - RemoteOK salary is in USD per year. Convert to monthly IDR using
    ``USD_TO_IDR`` (default 16000) and divide by 12.
  - arbeitnow doesn't expose salary fields; we leave NULL.
  - Adzuna ID returns salary in IDR (annual or monthly depending on
    posting). We assume annual when the value is > 50,000,000.

The script supports a ``--dry-run`` flag for preview.
"""
from __future__ import annotations

import argparse
import html
import json
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app import create_app  # noqa: E402
from backend.database import execute, query_one  # noqa: E402


USD_TO_IDR = int(os.environ.get("USD_TO_IDR_RATE", "16000"))

# Province parsing for Adzuna ID. Adzuna's location.area looks like
# ["Indonesia", "DKI Jakarta", "Jakarta"] or ["Indonesia", "West Java", "Bandung"].
# We map the second element through this dict (English → Indonesian standard).
ADZUNA_PROVINCE_MAP: dict[str, str] = {
    "DKI Jakarta": "DKI Jakarta",
    "Jakarta": "DKI Jakarta",
    "West Java": "Jawa Barat",
    "East Java": "Jawa Timur",
    "Central Java": "Jawa Tengah",
    "Banten": "Banten",
    "Yogyakarta": "DI Yogyakarta",
    "Special Region of Yogyakarta": "DI Yogyakarta",
    "Bali": "Bali",
    "North Sumatra": "Sumatera Utara",
    "South Sumatra": "Sumatera Selatan",
    "West Sumatra": "Sumatera Barat",
    "South Sulawesi": "Sulawesi Selatan",
    "North Sulawesi": "Sulawesi Utara",
    "Central Sulawesi": "Sulawesi Tengah",
    "Riau": "Riau",
    "Lampung": "Lampung",
    "Aceh": "Aceh",
    "Papua": "Papua",
    "West Nusa Tenggara": "Nusa Tenggara Barat",
    "East Nusa Tenggara": "Nusa Tenggara Timur",
}

# Map a city in DKI Jakarta back to province.
JAKARTA_CITIES = {
    "Jakarta Pusat", "Jakarta Barat", "Jakarta Selatan",
    "Jakarta Timur", "Jakarta Utara", "Jakarta",
    "Central Jakarta", "West Jakarta", "South Jakarta",
    "East Jakarta", "North Jakarta",
}

JAKARTA_CITY_MAP = {
    "Central Jakarta": "Jakarta Pusat",
    "West Jakarta": "Jakarta Barat",
    "South Jakarta": "Jakarta Selatan",
    "East Jakarta": "Jakarta Timur",
    "North Jakarta": "Jakarta Utara",
    "Jakarta": "Jakarta",
}

# Map arbeitnow job_types -> our employment_type vocabulary.
ARBEITNOW_TYPE_MAP = {
    "full-time": "Full-time",
    "part-time": "Part-time",
    "contract": "Contract",
    "freelance": "Freelance",
    "internship": "Internship",
    "permanent": "Full-time",
}


TAG_RE = re.compile(r"<[^>]+>")


def strip_html(s: str) -> str:
    if not s:
        return ""
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


def find_or_create_company(name: str, *, industry: str | None = None,
                           description: str | None = None,
                           country: str | None = None) -> int:
    name = (name or "").strip()
    if not name:
        return 0
    row = query_one(
        "SELECT id FROM companies WHERE LOWER(name) = LOWER(?) LIMIT 1",
        (name,),
    )
    if row:
        return int(row["id"])
    slug_base = slugify(name)
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
            (industry or "").strip() or None,
            strip_html(description or "") or None,
            (country or "").strip() or None,
            1,
            0,
        ),
    )
    return int(cid)


def upsert_job(*, company_id: int, title: str, description: str | None,
               requirements: str | None, employment_type: str | None,
               country: str | None, province: str | None, city: str | None,
               salary_min: int | None, salary_max: int | None,
               min_experience: int = 0, skills: str | None = None,
               dry_run: bool = False) -> str:
    title = (title or "").strip()
    if not title or not company_id:
        return "skipped"
    row = query_one(
        "SELECT id FROM jobs WHERE company_id = ? AND LOWER(title) = LOWER(?) LIMIT 1",
        (company_id, title),
    )
    if row:
        return "skipped"
    if dry_run:
        return "inserted"
    execute(
        "INSERT INTO jobs(company_id, title, description, requirements, skills, "
        "employment_type, country, province, city, salary_min, salary_max, "
        "min_experience, is_active) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (
            company_id, title,
            description or None,
            requirements or None,
            skills or None,
            employment_type,
            country or None,
            province or None,
            city or None,
            salary_min,
            salary_max,
            int(min_experience or 0),
            1,
        ),
    )
    return "inserted"


# ----------------------------------------------------------------------
# RemoteOK
# ----------------------------------------------------------------------

def import_remoteok(path: Path, dry_run: bool) -> tuple[int, int]:
    if not path.exists():
        return 0, 0
    jobs = json.loads(path.read_text(encoding="utf-8"))
    ins = skip = 0
    for j in jobs:
        company_id = find_or_create_company(
            j.get("company_name") or "",
            industry=", ".join((j.get("tags") or [])[:3]) or None,
            country="Worldwide",
        )
        if not company_id:
            skip += 1
            continue
        # Salary: RemoteOK is USD/year. Convert to monthly IDR.
        smin = j.get("salary_min")
        smax = j.get("salary_max")
        salary_min = (
            int(smin) * USD_TO_IDR // 12 if smin else None
        )
        salary_max = (
            int(smax) * USD_TO_IDR // 12 if smax else None
        )
        descr = strip_html(j.get("description_html") or "")
        url = j.get("url") or ""
        if url:
            req = f"Tags: {', '.join((j.get('tags') or [])[:8])}\n\nSumber: {url}"
        else:
            req = None
        loc = (j.get("location") or "").strip() or "Remote"
        country = "Worldwide"
        # If location mentions Indonesia
        if "indonesia" in loc.lower():
            country = "Indonesia"
        elif "singapore" in loc.lower():
            country = "Singapore"
        elif "australia" in loc.lower():
            country = "Australia"
        status = upsert_job(
            company_id=company_id,
            title=j.get("title") or "",
            description=descr,
            requirements=req,
            employment_type="Remote",
            country=country,
            province=None,
            city=loc,
            salary_min=salary_min,
            salary_max=salary_max,
            min_experience=0,
            skills=", ".join((j.get("tags") or [])[:10]) or None,
            dry_run=dry_run,
        )
        if status == "inserted":
            ins += 1
        else:
            skip += 1
    return ins, skip


# ----------------------------------------------------------------------
# arbeitnow
# ----------------------------------------------------------------------

def import_arbeitnow(path: Path, dry_run: bool) -> tuple[int, int]:
    if not path.exists():
        return 0, 0
    jobs = json.loads(path.read_text(encoding="utf-8"))
    ins = skip = 0
    for j in jobs:
        company_id = find_or_create_company(
            j.get("company_name") or "",
            industry=", ".join((j.get("tags") or [])[:3]) or None,
            country="Worldwide",
        )
        if not company_id:
            skip += 1
            continue
        descr = strip_html(j.get("description_html") or "")
        url = j.get("url") or ""
        req = f"Sumber: {url}" if url else None
        loc = (j.get("location") or "").strip() or ""
        country = "Worldwide"
        if "indonesia" in loc.lower():
            country = "Indonesia"
        emp_type = None
        for t in (j.get("job_types") or []):
            if t in ARBEITNOW_TYPE_MAP:
                emp_type = ARBEITNOW_TYPE_MAP[t]
                break
        if not emp_type and j.get("is_remote"):
            emp_type = "Remote"
        status = upsert_job(
            company_id=company_id,
            title=j.get("title") or "",
            description=descr,
            requirements=req,
            employment_type=emp_type or "Full-time",
            country=country,
            province=None,
            city=loc,
            salary_min=None,
            salary_max=None,
            min_experience=0,
            skills=", ".join((j.get("tags") or [])[:10]) or None,
            dry_run=dry_run,
        )
        if status == "inserted":
            ins += 1
        else:
            skip += 1
    return ins, skip


# ----------------------------------------------------------------------
# Jobicy
# ----------------------------------------------------------------------

JOBICY_TYPE_MAP = {
    "Full-Time": "Full-time",
    "Part-Time": "Part-time",
    "Contract": "Contract",
    "Freelance": "Freelance",
    "Internship": "Internship",
}


def _jobicy_emp_type(types: list[str] | None) -> str:
    if not types:
        return "Remote"
    for t in types:
        if t in JOBICY_TYPE_MAP:
            return JOBICY_TYPE_MAP[t]
    return "Remote"


def import_jobicy(path: Path, dry_run: bool) -> tuple[int, int]:
    if not path.exists():
        return 0, 0
    jobs = json.loads(path.read_text(encoding="utf-8"))
    ins = skip = 0
    for j in jobs:
        industry = j.get("industry")
        if isinstance(industry, list):
            industry = ", ".join(industry[:3])
        company_id = find_or_create_company(
            j.get("company_name") or "",
            industry=industry,
            country="Worldwide",
        )
        if not company_id:
            skip += 1
            continue
        descr = strip_html(j.get("description_html") or j.get("excerpt") or "")
        url = j.get("url") or ""
        req = f"Sumber: {url}" if url else None
        loc = (j.get("location") or "").strip() or "Remote"
        country = "Worldwide"
        if "indonesia" in loc.lower():
            country = "Indonesia"
        elif "singapore" in loc.lower():
            country = "Singapore"
        elif "australia" in loc.lower():
            country = "Australia"
        status = upsert_job(
            company_id=company_id,
            title=j.get("title") or "",
            description=descr,
            requirements=req,
            employment_type=_jobicy_emp_type(j.get("job_type")),
            country=country,
            province=None,
            city=loc,
            salary_min=None,
            salary_max=None,
            min_experience=0,
            dry_run=dry_run,
        )
        if status == "inserted":
            ins += 1
        else:
            skip += 1
    return ins, skip


# ----------------------------------------------------------------------
# WeWorkRemotely (RSS)
# ----------------------------------------------------------------------

def import_wwr(path: Path, dry_run: bool) -> tuple[int, int]:
    if not path.exists():
        return 0, 0
    jobs = json.loads(path.read_text(encoding="utf-8"))
    ins = skip = 0
    for j in jobs:
        company_id = find_or_create_company(
            j.get("company") or "",
            industry=None,
            country="Worldwide",
        )
        if not company_id:
            skip += 1
            continue
        descr = strip_html(j.get("description_html") or "")
        url = j.get("url") or ""
        req = f"Sumber: {url}" if url else None
        region = (j.get("region") or "Remote").strip()
        country = "Worldwide"
        if "indonesia" in region.lower():
            country = "Indonesia"
        status = upsert_job(
            company_id=company_id,
            title=j.get("title") or "",
            description=descr,
            requirements=req,
            employment_type="Remote",
            country=country,
            province=None,
            city=region,
            salary_min=None,
            salary_max=None,
            min_experience=0,
            dry_run=dry_run,
        )
        if status == "inserted":
            ins += 1
        else:
            skip += 1
    return ins, skip


# ----------------------------------------------------------------------
# Adzuna ID
# ----------------------------------------------------------------------

def _parse_adzuna_location(j: dict) -> tuple[str | None, str | None]:
    """Return (province, city) from Adzuna location areas / display."""
    areas = j.get("location_areas") or []
    province = None
    city = None
    # area: [country, province, city, ...]
    if len(areas) >= 2 and areas[0].lower().startswith("indonesia"):
        prov_raw = areas[1]
        province = ADZUNA_PROVINCE_MAP.get(prov_raw, prov_raw)
    if len(areas) >= 3:
        city = areas[2]
    if not city and j.get("location_display"):
        city = j["location_display"].split(",")[0].strip()
    if not province and city in JAKARTA_CITIES:
        province = "DKI Jakarta"
        city = JAKARTA_CITY_MAP.get(city, city)
    return province, city


def _adzuna_salary_monthly(v: float | None) -> int | None:
    if v is None:
        return None
    try:
        v = float(v)
    except (TypeError, ValueError):
        return None
    if v <= 0:
        return None
    # Heuristic: if > 50,000,000 it's likely annual IDR.
    if v > 50_000_000:
        return int(v / 12)
    return int(v)


def import_adzuna(path: Path, dry_run: bool) -> tuple[int, int]:
    if not path.exists():
        return 0, 0
    jobs = json.loads(path.read_text(encoding="utf-8"))
    ins = skip = 0
    for j in jobs:
        company_id = find_or_create_company(
            j.get("company_name") or "",
            industry=j.get("category"),
            country="Indonesia",
        )
        if not company_id:
            skip += 1
            continue
        province, city = _parse_adzuna_location(j)
        descr = strip_html(j.get("description_html") or "")
        url = j.get("url") or ""
        req = f"Sumber: {url}" if url else None
        emp_type = None
        ct = (j.get("contract_time") or "").lower()
        if ct == "full_time":
            emp_type = "Full-time"
        elif ct == "part_time":
            emp_type = "Part-time"
        if (j.get("contract_type") or "").lower() == "contract":
            emp_type = "Contract"
        smin = _adzuna_salary_monthly(j.get("salary_min"))
        smax = _adzuna_salary_monthly(j.get("salary_max"))
        status = upsert_job(
            company_id=company_id,
            title=j.get("title") or "",
            description=descr,
            requirements=req,
            employment_type=emp_type or "Full-time",
            country="Indonesia",
            province=province,
            city=city,
            salary_min=smin,
            salary_max=smax,
            min_experience=0,
            dry_run=dry_run,
        )
        if status == "inserted":
            ins += 1
        else:
            skip += 1
    return ins, skip


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-dir", type=Path,
                    default=Path(__file__).parent / "data")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--skip-remoteok", action="store_true")
    ap.add_argument("--skip-arbeitnow", action="store_true")
    ap.add_argument("--skip-jobicy", action="store_true")
    ap.add_argument("--skip-wwr", action="store_true")
    ap.add_argument("--skip-adzuna", action="store_true")
    args = ap.parse_args()

    app = create_app()
    with app.app_context():
        before_companies = query_one("SELECT COUNT(*) AS n FROM companies")["n"]
        before_jobs = query_one("SELECT COUNT(*) AS n FROM jobs")["n"]
        total_ins = total_skip = 0
        if not args.skip_remoteok:
            ins, skip = import_remoteok(args.data_dir / "remoteok_jobs.json", args.dry_run)
            total_ins += ins
            total_skip += skip
            print(f"RemoteOK: inserted={ins} skipped={skip}")
        if not args.skip_arbeitnow:
            ins, skip = import_arbeitnow(args.data_dir / "arbeitnow_jobs.json", args.dry_run)
            total_ins += ins
            total_skip += skip
            print(f"arbeitnow: inserted={ins} skipped={skip}")
        if not args.skip_jobicy:
            ins, skip = import_jobicy(args.data_dir / "jobicy_jobs.json", args.dry_run)
            total_ins += ins
            total_skip += skip
            print(f"jobicy:    inserted={ins} skipped={skip}")
        if not args.skip_wwr:
            ins, skip = import_wwr(args.data_dir / "wwr_jobs.json", args.dry_run)
            total_ins += ins
            total_skip += skip
            print(f"wwr:       inserted={ins} skipped={skip}")
        if not args.skip_adzuna:
            ins, skip = import_adzuna(args.data_dir / "adzuna_jobs.json", args.dry_run)
            total_ins += ins
            total_skip += skip
            print(f"adzuna:   inserted={ins} skipped={skip}")
        after_companies = query_one("SELECT COUNT(*) AS n FROM companies")["n"]
        after_jobs = query_one("SELECT COUNT(*) AS n FROM jobs")["n"]
        print(
            f"\nSummary: total inserted={total_ins} skipped={total_skip}\n"
            f"Companies: {before_companies} -> {after_companies} (+{after_companies-before_companies})\n"
            f"Jobs:      {before_jobs} -> {after_jobs} (+{after_jobs-before_jobs})"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
