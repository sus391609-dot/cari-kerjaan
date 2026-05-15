"""Authentication helpers: session, decorators, password hashing."""
from __future__ import annotations

from functools import wraps
from typing import Callable

from flask import current_app, jsonify, redirect, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

from .database import query_one


def hash_password(raw: str) -> str:
    return generate_password_hash(raw)


def verify_password(raw: str, hashed: str) -> bool:
    try:
        return check_password_hash(hashed, raw)
    except Exception:
        return False


def current_user() -> dict | None:
    uid = session.get("user_id")
    role = session.get("role")
    if role == "admin":
        return {
            "id": 0,
            "role": "admin",
            "email": current_app.config["ADMIN_EMAIL"],
            "full_name": "Administrator",
        }
    if not uid:
        return None
    row = query_one(
        "SELECT id, role, email, full_name, username, birth_date, photo_path, "
        "is_verified, is_approved FROM users WHERE id=?",
        (uid,),
    )
    if row is None:
        return None
    return dict(row)


def login_user(user_id: int, role: str) -> None:
    session.clear()
    session["user_id"] = int(user_id) if user_id else 0
    session["role"] = role


def logout_user() -> None:
    session.clear()


def _wants_json() -> bool:
    return request.is_json or request.path.startswith("/api/") or \
        request.accept_mimetypes.best == "application/json"


def login_required(fn: Callable) -> Callable:
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not current_user():
            if _wants_json():
                return jsonify({"error": "unauthorized"}), 401
            return redirect(url_for("pages.login", next=request.path))
        return fn(*args, **kwargs)

    return wrapper


def role_required(*roles: str) -> Callable:
    def deco(fn: Callable) -> Callable:
        @wraps(fn)
        def wrapper(*args, **kwargs):
            u = current_user()
            if not u:
                if _wants_json():
                    return jsonify({"error": "unauthorized"}), 401
                return redirect(url_for("pages.login", next=request.path))
            if u["role"] not in roles:
                if _wants_json():
                    return jsonify({"error": "forbidden"}), 403
                return redirect(url_for("pages.index"))
            return fn(*args, **kwargs)

        return wrapper

    return deco


admin_required = role_required("admin")
company_required = role_required("company")
