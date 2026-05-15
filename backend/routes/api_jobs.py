"""Job / company search RESTful endpoints."""
from __future__ import annotations

from flask import Blueprint, jsonify, request

from ..auth import current_user
from ..database import execute, query_all, query_one


bp = Blueprint("api_jobs", __name__, url_prefix="/api")


def _row_to_dict(row) -> dict:
    return {k: row[k] for k in row.keys()}


@bp.get("/jobs")
def list_jobs():
    """Search jobs by keyword, country, province, city.

    Returns a JSON list of jobs with the joined company name and city. The
    full job description is only returned for authenticated users (the
    "lihat selengkapnya" gate from the spec).
    """
    q = (request.args.get("q") or "").strip()
    country = (request.args.get("country") or "").strip()
    province = (request.args.get("province") or "").strip()
    city = (request.args.get("city") or "").strip()
    page = max(1, int(request.args.get("page", "1") or 1))
    per_page = min(50, max(1, int(request.args.get("per_page", "12") or 12)))

    sql = (
        "SELECT j.id, j.title, j.skills, j.employment_type, j.country, j.province, "
        "j.city, j.salary_min, j.salary_max, j.min_experience, j.created_at, "
        "c.id AS company_id, c.name AS company_name, c.logo_path, c.industry "
        "FROM jobs j JOIN companies c ON c.id=j.company_id "
        "WHERE j.is_active=1 AND c.is_approved=1"
    )
    params: list = []
    if q:
        sql += " AND (j.title LIKE ? OR j.skills LIKE ? OR c.name LIKE ?)"
        like = f"%{q}%"
        params.extend([like, like, like])
    if country:
        sql += " AND j.country LIKE ?"
        params.append(f"%{country}%")
    if province:
        sql += " AND j.province LIKE ?"
        params.append(f"%{province}%")
    if city:
        sql += " AND j.city LIKE ?"
        params.append(f"%{city}%")
    sql += " ORDER BY j.created_at DESC LIMIT ? OFFSET ?"
    params.extend([per_page, (page - 1) * per_page])

    rows = query_all(sql, params)
    items = []
    is_auth = bool(current_user())
    for r in rows:
        d = _row_to_dict(r)
        if not is_auth:
            # Keep listing visible but blur "see more" detail in UI.
            d["_locked"] = True
        items.append(d)
    return jsonify({"items": items, "page": page, "per_page": per_page})


@bp.get("/jobs/<int:job_id>")
def job_detail(job_id: int):
    """Detailed job view. Requires authentication for full company info."""
    row = query_one(
        "SELECT j.*, c.name AS company_name, c.description AS company_description, "
        "c.industry, c.website, c.employees, c.founded_year, c.address, "
        "c.logo_path FROM jobs j JOIN companies c ON c.id=j.company_id "
        "WHERE j.id=? AND j.is_active=1 AND c.is_approved=1",
        (job_id,),
    )
    if not row:
        return jsonify({"error": "Job tidak ditemukan"}), 404
    d = _row_to_dict(row)
    if not current_user():
        return jsonify({"item": {
            "id": d["id"], "title": d["title"], "company_name": d["company_name"],
            "city": d["city"], "province": d["province"], "country": d["country"],
            "skills": d["skills"], "employment_type": d["employment_type"],
            "_locked": True,
        }})
    # increment company search/view counter
    execute(
        "UPDATE companies SET search_count = search_count + 1 WHERE id=?",
        (d["company_id"],),
    )
    execute("INSERT INTO company_search_log(company_id) VALUES(?)", (d["company_id"],))
    return jsonify({"item": d})


@bp.get("/companies/top-searched")
def top_searched_companies():
    rows = query_all(
        "SELECT id, name, logo_path, industry, search_count "
        "FROM companies WHERE is_approved=1 ORDER BY search_count DESC LIMIT 10"
    )
    return jsonify({"items": [_row_to_dict(r) for r in rows]})


@bp.get("/companies/top-openings")
def top_openings_companies():
    rows = query_all(
        "SELECT c.id, c.name, c.logo_path, c.industry, COUNT(j.id) AS open_jobs "
        "FROM companies c LEFT JOIN jobs j ON j.company_id=c.id AND j.is_active=1 "
        "WHERE c.is_approved=1 GROUP BY c.id ORDER BY open_jobs DESC, c.name ASC LIMIT 10"
    )
    return jsonify({"items": [_row_to_dict(r) for r in rows]})


@bp.get("/companies/<int:company_id>")
def company_detail(company_id: int):
    row = query_one(
        "SELECT * FROM companies WHERE id=? AND is_approved=1", (company_id,)
    )
    if not row:
        return jsonify({"error": "Perusahaan tidak ditemukan"}), 404
    d = _row_to_dict(row)
    jobs = query_all(
        "SELECT id, title, city, province, country, employment_type, skills, "
        "salary_min, salary_max, created_at FROM jobs "
        "WHERE company_id=? AND is_active=1 ORDER BY created_at DESC",
        (company_id,),
    )
    d["jobs"] = [_row_to_dict(j) for j in jobs]
    return jsonify({"item": d})


@bp.get("/stats")
def public_stats():
    users = query_one(
        "SELECT COUNT(*) AS n FROM users WHERE role='user' AND is_verified=1"
    )["n"]
    companies = query_one(
        "SELECT COUNT(*) AS n FROM companies WHERE is_approved=1"
    )["n"]
    jobs = query_one(
        "SELECT COUNT(*) AS n FROM jobs WHERE is_active=1"
    )["n"]
    return jsonify({"users": users, "companies": companies, "jobs": jobs})


@bp.get("/locations/provinces")
def provinces():
    """Return distinct provinces from current jobs + a baseline list."""
    rows = query_all(
        "SELECT DISTINCT province FROM jobs WHERE province IS NOT NULL AND province <> ''"
    )
    base = [
        "DKI Jakarta", "Jawa Barat", "Jawa Tengah", "Jawa Timur", "DI Yogyakarta",
        "Banten", "Bali", "Sumatera Utara", "Sumatera Selatan", "Sumatera Barat",
        "Riau", "Lampung", "Kalimantan Timur", "Kalimantan Selatan", "Kalimantan Barat",
        "Sulawesi Selatan", "Sulawesi Utara", "Papua", "Nusa Tenggara Barat",
        "Nusa Tenggara Timur", "Aceh", "Maluku",
    ]
    have = {r["province"] for r in rows}
    return jsonify({"items": sorted(set(base) | have)})
