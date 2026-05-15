"""Admin RESTful endpoints. All routes require ``role=admin``."""
from __future__ import annotations

import os
import secrets
from pathlib import Path

from flask import Blueprint, current_app, jsonify, request
from werkzeug.security import generate_password_hash
from werkzeug.utils import secure_filename

from ..auth import admin_required
from ..database import execute, get_setting, query_all, query_one, set_setting


bp = Blueprint("api_admin", __name__, url_prefix="/api/admin")


# ----------------------------- Maintenance ----------------------------- #


@bp.get("/maintenance")
@admin_required
def get_maintenance():
    return jsonify({"enabled": get_setting("maintenance_mode", "0") == "1"})


@bp.post("/maintenance")
@admin_required
def set_maintenance():
    data = request.get_json(silent=True) or request.form
    enabled = str(data.get("enabled")).lower() in ("1", "true", "yes", "on")
    set_setting("maintenance_mode", "1" if enabled else "0")
    return jsonify({"ok": True, "enabled": enabled})


# ----------------------------- Users ----------------------------- #


@bp.get("/users")
@admin_required
def list_users():
    q = (request.args.get("q") or "").strip()
    sql = (
        "SELECT id, role, email, full_name, username, birth_date, photo_path, "
        "is_verified, is_approved, created_at FROM users WHERE 1=1"
    )
    params: list = []
    if q:
        sql += " AND (email LIKE ? OR full_name LIKE ? OR username LIKE ?)"
        like = f"%{q}%"
        params.extend([like, like, like])
    sql += " ORDER BY created_at DESC LIMIT 500"
    rows = query_all(sql, params)
    return jsonify({"items": [dict(r) for r in rows]})


@bp.put("/users/<int:user_id>")
@admin_required
def update_user(user_id: int):
    data = request.get_json(silent=True) or request.form
    fields: dict[str, object] = {}
    for k in ("full_name", "username", "birth_date", "email"):
        if k in data and data[k] is not None:
            fields[k] = (data[k] or "").strip() or None
    if data.get("password"):
        fields["password_hash"] = generate_password_hash(data["password"])
    if "is_verified" in data:
        fields["is_verified"] = 1 if str(data["is_verified"]).lower() in (
            "1", "true", "yes", "on"
        ) else 0
    if "is_approved" in data:
        fields["is_approved"] = 1 if str(data["is_approved"]).lower() in (
            "1", "true", "yes", "on"
        ) else 0
    if not fields:
        return jsonify({"error": "Tidak ada perubahan"}), 400
    sets = ", ".join(f"{k}=?" for k in fields.keys())
    execute(
        f"UPDATE users SET {sets} WHERE id=?", list(fields.values()) + [user_id]
    )
    return jsonify({"ok": True})


@bp.delete("/users/<int:user_id>")
@admin_required
def delete_user(user_id: int):
    execute("DELETE FROM users WHERE id=?", (user_id,))
    return jsonify({"ok": True})


@bp.post("/users/<int:user_id>/approve")
@admin_required
def approve_user(user_id: int):
    execute(
        "UPDATE users SET is_approved=1, is_verified=1 WHERE id=?", (user_id,)
    )
    # Also approve the company they own, if any
    execute(
        "UPDATE companies SET is_approved=1 WHERE owner_user_id=?", (user_id,)
    )
    return jsonify({"ok": True})


@bp.get("/pending-companies")
@admin_required
def pending_companies():
    rows = query_all(
        "SELECT u.id AS user_id, u.email, u.full_name AS company_owner, "
        "c.id AS company_id, c.name, c.industry, c.city, c.province, c.address, "
        "c.website, c.description, c.logo_path, c.created_at "
        "FROM users u LEFT JOIN companies c ON c.owner_user_id=u.id "
        "WHERE u.role='company' AND u.is_approved=0 "
        "ORDER BY c.created_at DESC"
    )
    return jsonify({"items": [dict(r) for r in rows]})


# ----------------------------- Companies ----------------------------- #


@bp.get("/companies")
@admin_required
def list_companies():
    q = (request.args.get("q") or "").strip()
    sql = "SELECT * FROM companies WHERE 1=1"
    params: list = []
    if q:
        sql += " AND (name LIKE ? OR industry LIKE ? OR city LIKE ?)"
        like = f"%{q}%"
        params.extend([like, like, like])
    sql += " ORDER BY created_at DESC LIMIT 500"
    rows = query_all(sql, params)
    return jsonify({"items": [dict(r) for r in rows]})


@bp.post("/companies")
@admin_required
def create_company():
    data = request.form if request.form else (request.get_json(silent=True) or {})
    name = (data.get("name") or "").strip()
    if not name:
        return jsonify({"error": "Nama perusahaan wajib"}), 400
    logo_rel = None
    if "logo" in request.files:
        logo_rel = _save_partner_image(request.files["logo"], subdir="photos")
    company_id = execute(
        "INSERT INTO companies(name, industry, website, address, province, city, "
        "country, description, logo_path, employees, founded_year, is_approved) "
        "VALUES(?,?,?,?,?,?,?,?,?,?,?,1)",
        (
            name,
            (data.get("industry") or "").strip(),
            (data.get("website") or "").strip(),
            (data.get("address") or "").strip(),
            (data.get("province") or "").strip(),
            (data.get("city") or "").strip(),
            (data.get("country") or "Indonesia").strip(),
            (data.get("description") or "").strip(),
            logo_rel,
            (data.get("employees") or "").strip() or None,
            int(data.get("founded_year")) if (data.get("founded_year") or "").isdigit() else None,
        ),
    )
    return jsonify({"ok": True, "id": company_id})


@bp.put("/companies/<int:company_id>")
@admin_required
def update_company(company_id: int):
    data = request.form if request.form else (request.get_json(silent=True) or {})
    fields: dict[str, object] = {}
    for k in (
        "name", "industry", "website", "address", "province", "city",
        "country", "description", "employees",
    ):
        if k in data and data[k] is not None:
            fields[k] = (data[k] or "").strip() or None
    if data.get("founded_year") and str(data["founded_year"]).isdigit():
        fields["founded_year"] = int(data["founded_year"])
    if "is_approved" in data:
        fields["is_approved"] = 1 if str(data["is_approved"]).lower() in (
            "1", "true", "yes", "on"
        ) else 0
    if "logo" in request.files:
        rel = _save_partner_image(request.files["logo"], subdir="photos")
        if rel:
            fields["logo_path"] = rel
    if not fields:
        return jsonify({"error": "Tidak ada perubahan"}), 400
    sets = ", ".join(f"{k}=?" for k in fields.keys())
    execute(
        f"UPDATE companies SET {sets} WHERE id=?",
        list(fields.values()) + [company_id],
    )
    return jsonify({"ok": True})


@bp.delete("/companies/<int:company_id>")
@admin_required
def delete_company(company_id: int):
    execute("DELETE FROM companies WHERE id=?", (company_id,))
    return jsonify({"ok": True})


# ----------------------------- Jobs ----------------------------- #


@bp.get("/jobs")
@admin_required
def list_jobs():
    q = (request.args.get("q") or "").strip()
    sql = (
        "SELECT j.*, c.name AS company_name FROM jobs j "
        "JOIN companies c ON c.id=j.company_id WHERE 1=1"
    )
    params: list = []
    if q:
        sql += " AND (j.title LIKE ? OR c.name LIKE ? OR j.skills LIKE ?)"
        like = f"%{q}%"
        params.extend([like, like, like])
    sql += " ORDER BY j.created_at DESC LIMIT 500"
    rows = query_all(sql, params)
    return jsonify({"items": [dict(r) for r in rows]})


@bp.post("/jobs")
@admin_required
def create_job():
    data = request.get_json(silent=True) or request.form
    try:
        company_id = int(data.get("company_id"))
    except (TypeError, ValueError):
        return jsonify({"error": "company_id wajib"}), 400
    title = (data.get("title") or "").strip()
    if not title:
        return jsonify({"error": "Judul lowongan wajib"}), 400
    new_id = execute(
        "INSERT INTO jobs(company_id, title, description, requirements, skills, "
        "employment_type, country, province, city, salary_min, salary_max, "
        "min_experience, min_age, max_age, is_active) "
        "VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,1)",
        (
            company_id, title,
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
@admin_required
def delete_job(job_id: int):
    execute("DELETE FROM jobs WHERE id=?", (job_id,))
    return jsonify({"ok": True})


# ----------------------------- Partners ----------------------------- #


ALLOWED_IMG_EXT = {".png", ".jpg", ".jpeg", ".webp", ".gif"}


def _save_partner_image(file_storage, subdir: str = "partners") -> str | None:
    if not file_storage or not file_storage.filename:
        return None
    name = secure_filename(file_storage.filename)
    ext = Path(name).suffix.lower()
    if ext not in ALLOWED_IMG_EXT:
        return None
    base = current_app.config["PARTNER_UPLOAD_DIR"] if subdir == "partners" \
        else current_app.config["PHOTO_UPLOAD_DIR"]
    os.makedirs(base, exist_ok=True)
    fname = f"{secrets.token_hex(8)}{ext}"
    path = Path(base) / fname
    file_storage.save(path)
    return f"uploads/{subdir}/{fname}"


@bp.post("/partners")
@admin_required
def create_partner():
    img = request.files.get("image")
    if not img:
        return jsonify({"error": "Gambar wajib diunggah"}), 400
    rel = _save_partner_image(img)
    if not rel:
        return jsonify({"error": "Format tidak didukung (png/jpg/webp/gif)"}), 400
    name = (request.form.get("name") or "").strip()
    link = (request.form.get("link") or "").strip()
    new_id = execute(
        "INSERT INTO partners(name, image_path, link) VALUES(?,?,?)",
        (name or None, rel, link or None),
    )
    return jsonify({"ok": True, "id": new_id})


@bp.delete("/partners/<int:pid>")
@admin_required
def delete_partner(pid: int):
    execute("DELETE FROM partners WHERE id=?", (pid,))
    return jsonify({"ok": True})


# ----------------------------- Experiences ----------------------------- #


@bp.get("/experiences")
@admin_required
def admin_experiences():
    rows = query_all(
        "SELECT e.*, u.email, u.full_name FROM experiences e "
        "JOIN users u ON u.id=e.user_id ORDER BY e.created_at DESC LIMIT 500"
    )
    return jsonify({"items": [dict(r) for r in rows]})


@bp.delete("/experiences/<int:eid>")
@admin_required
def delete_experience(eid: int):
    execute("DELETE FROM experiences WHERE id=?", (eid,))
    return jsonify({"ok": True})


# ----------------------------- Stats ----------------------------- #


@bp.get("/stats")
@admin_required
def admin_stats():
    users = query_one("SELECT COUNT(*) AS n FROM users WHERE role='user'")["n"]
    verified = query_one(
        "SELECT COUNT(*) AS n FROM users WHERE role='user' AND is_verified=1"
    )["n"]
    companies = query_one(
        "SELECT COUNT(*) AS n FROM companies WHERE is_approved=1"
    )["n"]
    pending = query_one(
        "SELECT COUNT(*) AS n FROM users WHERE role='company' AND is_approved=0"
    )["n"]
    jobs = query_one("SELECT COUNT(*) AS n FROM jobs WHERE is_active=1")["n"]
    partners = query_one("SELECT COUNT(*) AS n FROM partners")["n"]
    exps = query_one("SELECT COUNT(*) AS n FROM experiences")["n"]
    return jsonify({
        "users": users,
        "verified_users": verified,
        "companies": companies,
        "pending_companies": pending,
        "jobs": jobs,
        "partners": partners,
        "experiences": exps,
        "maintenance": get_setting("maintenance_mode", "0") == "1",
    })
