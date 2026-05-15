"""CV upload, parsing, and job matching endpoint."""
from __future__ import annotations

import os
import secrets
from pathlib import Path

from flask import Blueprint, current_app, jsonify, request
from werkzeug.utils import secure_filename

from ..auth import current_user, login_required
from ..cv_parser import match_jobs_for_cv, parse_cv, suggest_skills_to_improve
from ..database import execute, query_all


bp = Blueprint("api_cv", __name__, url_prefix="/api/cv")


@bp.post("/upload")
@login_required
def upload_cv():
    user = current_user()
    if not user or user.get("role") not in ("user", "company"):
        return jsonify({"error": "Login sebagai user untuk mengunggah CV"}), 403
    f = request.files.get("cv")
    if not f or not f.filename:
        return jsonify({"error": "File CV wajib diunggah"}), 400
    name = secure_filename(f.filename)
    if not name.lower().endswith(".pdf"):
        return jsonify({"error": "Hanya format PDF yang diterima"}), 400

    dest_dir = Path(current_app.config["CV_UPLOAD_DIR"])
    os.makedirs(dest_dir, exist_ok=True)
    fname = f"{secrets.token_hex(8)}_{name}"
    save_path = dest_dir / fname
    f.save(save_path)

    try:
        cv = parse_cv(save_path)
    except Exception as exc:
        current_app.logger.exception("CV parse failed: %s", exc)
        return jsonify({"error": "Gagal membaca PDF, pastikan file valid"}), 400

    if not cv.raw_text.strip():
        return jsonify({
            "error": "CV tidak terbaca. Pastikan PDF berisi teks (bukan hasil scan).",
        }), 400

    execute(
        "INSERT INTO cv_uploads(user_id, file_path, parsed_skills, parsed_age, "
        "parsed_experience_years, raw_text) VALUES(?,?,?,?,?,?)",
        (
            user["id"], f"uploads/cv/{fname}", ",".join(cv.skills),
            cv.age, cv.experience_years, cv.raw_text[:50_000],
        ),
    )

    # Pull all active jobs for matching
    rows = query_all(
        "SELECT j.id, j.title, j.skills, j.min_experience, j.min_age, j.max_age, "
        "c.id AS company_id, c.name AS company_name "
        "FROM jobs j JOIN companies c ON c.id=j.company_id "
        "WHERE j.is_active=1 AND c.is_approved=1"
    )
    jobs = [dict(r) for r in rows]
    matches = match_jobs_for_cv(cv, jobs)

    # If no decent match (best below 50), return suggestions
    has_good_match = matches and matches[0].score >= 50
    suggestions = [] if has_good_match else suggest_skills_to_improve(matches)

    return jsonify({
        "ok": True,
        "parsed": {
            "skills": cv.skills,
            "age": cv.age,
            "experience_years": cv.experience_years,
        },
        "matches": [m.__dict__ for m in matches],
        "suggestions": suggestions,
        "has_good_match": has_good_match,
    })
