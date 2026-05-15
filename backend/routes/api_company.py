"""RESTful endpoints used by approved company accounts."""
from __future__ import annotations

from flask import Blueprint, jsonify, request

from ..auth import company_required, current_user
from ..database import execute, query_all, query_one


bp = Blueprint("api_company", __name__, url_prefix="/api/company")


def _company_for_user(user_id: int):
    return query_one(
        "SELECT * FROM companies WHERE owner_user_id=? LIMIT 1", (user_id,)
    )


@bp.get("/me")
@company_required
def me():
    u = current_user()
    assert u is not None
    c = _company_for_user(u["id"])
    return jsonify({"company": dict(c) if c else None})


@bp.get("/jobs")
@company_required
def my_jobs():
    u = current_user()
    assert u is not None
    c = _company_for_user(u["id"])
    if not c:
        return jsonify({"items": []})
    rows = query_all(
        "SELECT * FROM jobs WHERE company_id=? ORDER BY created_at DESC",
        (c["id"],),
    )
    return jsonify({"items": [dict(r) for r in rows]})


@bp.post("/jobs")
@company_required
def create_my_job():
    u = current_user()
    assert u is not None
    c = _company_for_user(u["id"])
    if not c:
        return jsonify({"error": "Profil perusahaan tidak ditemukan"}), 400
    if not c["is_approved"]:
        return jsonify({"error": "Akun perusahaan belum disetujui admin"}), 403
    data = request.get_json(silent=True) or request.form
    title = (data.get("title") or "").strip()
    if not title:
        return jsonify({"error": "Judul lowongan wajib"}), 400
    new_id = execute(
        "INSERT INTO jobs(company_id, title, description, requirements, skills, "
        "employment_type, country, province, city, salary_min, salary_max, "
        "min_experience, min_age, max_age, is_active) "
        "VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,1)",
        (
            c["id"], title,
            (data.get("description") or "").strip(),
            (data.get("requirements") or "").strip(),
            (data.get("skills") or "").strip().lower(),
            (data.get("employment_type") or "Full-time").strip(),
            (data.get("country") or "Indonesia").strip(),
            (data.get("province") or "").strip(),
            (data.get("city") or "").strip(),
            int(data.get("salary_min") or 0) or None,
            int(data.get("salary_max") or 0) or None,
            int(data.get("min_experience") or 0) or 0,
            int(data.get("min_age") or 0) or None,
            int(data.get("max_age") or 0) or None,
        ),
    )
    return jsonify({"ok": True, "id": new_id})


@bp.delete("/jobs/<int:job_id>")
@company_required
def delete_my_job(job_id: int):
    u = current_user()
    assert u is not None
    c = _company_for_user(u["id"])
    if not c:
        return jsonify({"error": "Profil perusahaan tidak ditemukan"}), 400
    execute(
        "DELETE FROM jobs WHERE id=? AND company_id=?", (job_id, c["id"])
    )
    return jsonify({"ok": True})
