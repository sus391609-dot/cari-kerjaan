"""Public partners + experience listing endpoints."""
from __future__ import annotations

from flask import Blueprint, jsonify, request

from ..auth import current_user, login_required
from ..database import execute, query_all


bp = Blueprint("api_partners", __name__, url_prefix="/api")


@bp.get("/partners")
def list_partners():
    rows = query_all(
        "SELECT id, name, image_path, link FROM partners ORDER BY created_at DESC"
    )
    return jsonify({"items": [dict(r) for r in rows]})


@bp.get("/experiences")
def list_experiences():
    rows = query_all(
        "SELECT e.id, e.title, e.body, e.rating, e.created_at, "
        "u.full_name, u.photo_path "
        "FROM experiences e JOIN users u ON u.id=e.user_id "
        "WHERE e.is_visible=1 ORDER BY e.created_at DESC LIMIT 50"
    )
    return jsonify({"items": [dict(r) for r in rows]})


@bp.post("/experiences")
@login_required
def create_experience():
    u = current_user()
    if not u or u["role"] not in ("user", "company"):
        return jsonify({"error": "Hanya user yang sudah login dapat berbagi pengalaman"}), 403
    data = request.get_json(silent=True) or request.form
    body = (data.get("body") or "").strip()
    title = (data.get("title") or "").strip()[:120]
    try:
        rating = int(data.get("rating") or 5)
    except (TypeError, ValueError):
        rating = 5
    rating = max(1, min(5, rating))
    if len(body) < 10:
        return jsonify({"error": "Pengalaman terlalu pendek (min 10 karakter)"}), 400
    new_id = execute(
        "INSERT INTO experiences(user_id, rating, title, body) VALUES(?,?,?,?)",
        (u["id"], rating, title or None, body),
    )
    return jsonify({"ok": True, "id": new_id})
