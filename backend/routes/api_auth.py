"""Authentication-related RESTful endpoints (JSON)."""
from __future__ import annotations

import os
import re
from pathlib import Path

from flask import Blueprint, current_app, jsonify, request
from werkzeug.utils import secure_filename

from ..auth import (
    current_user,
    hash_password,
    login_user,
    logout_user,
    verify_password,
)
from ..database import execute, query_one
from ..mailer import create_and_send_otp, verify_otp


bp = Blueprint("api_auth", __name__, url_prefix="/api/auth")


EMAIL_RE = re.compile(r"^[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}$")
ALLOWED_PHOTO_EXT = {".png", ".jpg", ".jpeg", ".webp"}


def _is_email(s: str) -> bool:
    return bool(EMAIL_RE.match((s or "").strip()))


def _save_photo(file_storage) -> str | None:
    if not file_storage or not file_storage.filename:
        return None
    name = secure_filename(file_storage.filename)
    ext = Path(name).suffix.lower()
    if ext not in ALLOWED_PHOTO_EXT:
        return None
    dest_dir = current_app.config["PHOTO_UPLOAD_DIR"]
    os.makedirs(dest_dir, exist_ok=True)
    import secrets
    fname = f"{secrets.token_hex(8)}{ext}"
    path = Path(dest_dir) / fname
    file_storage.save(path)
    return f"uploads/photos/{fname}"


@bp.post("/register")
def register():
    """Register a normal user or a company.

    For ``role=user`` the form requires: full_name, birth_date, email, password,
    and photo (file). For ``role=company`` the form requires: company_name,
    industry, address, province, city, email, password (and optional website,
    description, logo image). Companies are created with ``is_approved=0`` and
    must be approved by an admin before they can log in.
    """
    role = (request.form.get("role") or "user").lower()
    email = (request.form.get("email") or "").strip().lower()
    password = request.form.get("password") or ""
    if not _is_email(email):
        return jsonify({"error": "Email tidak valid"}), 400
    if len(password) < 6:
        return jsonify({"error": "Password minimal 6 karakter"}), 400
    if query_one("SELECT id FROM users WHERE email=?", (email,)):
        return jsonify({"error": "Email sudah terdaftar"}), 400

    if role == "company":
        company_name = (request.form.get("company_name") or "").strip()
        industry = (request.form.get("industry") or "").strip()
        address = (request.form.get("address") or "").strip()
        province = (request.form.get("province") or "").strip()
        city = (request.form.get("city") or "").strip()
        website = (request.form.get("website") or "").strip()
        description = (request.form.get("description") or "").strip()
        if not company_name or not industry or not city:
            return jsonify({"error": "Nama perusahaan, industri, dan kota wajib diisi"}), 400
        logo_rel = _save_photo(request.files.get("logo"))
        # create user (role=company) - not approved yet
        user_id = execute(
            "INSERT INTO users(role, email, password_hash, full_name, is_verified, is_approved) "
            "VALUES(?,?,?,?,?,?)",
            ("company", email, hash_password(password), company_name, 0, 0),
        )
        execute(
            "INSERT INTO companies(owner_user_id, name, industry, website, address, "
            "province, city, country, description, logo_path, is_approved) "
            "VALUES(?,?,?,?,?,?,?,?,?,?,?)",
            (
                user_id, company_name, industry, website, address,
                province, city, "Indonesia", description, logo_rel, 0,
            ),
        )
        _, sent = create_and_send_otp(email, purpose="register")
        return jsonify({
            "ok": True,
            "message": "Pendaftaran perusahaan diterima. Verifikasi email dengan OTP "
                       "yang dikirim ke gmail Anda, lalu menunggu persetujuan admin.",
            "email": email,
            "otp_sent_via_smtp": sent,
            "role": "company",
        })

    # Normal user
    full_name = (request.form.get("full_name") or "").strip()
    birth_date = (request.form.get("birth_date") or "").strip()
    username = (request.form.get("username") or "").strip() or email.split("@")[0]
    if not full_name or not birth_date:
        return jsonify({"error": "Nama lengkap dan tanggal lahir wajib diisi"}), 400
    photo_rel = _save_photo(request.files.get("photo"))
    if not photo_rel:
        return jsonify({"error": "Foto profil wajib diunggah (png/jpg/webp)"}), 400
    user_id = execute(
        "INSERT INTO users(role,email,password_hash,full_name,username,birth_date,"
        "photo_path,is_verified,is_approved) VALUES(?,?,?,?,?,?,?,?,?)",
        ("user", email, hash_password(password), full_name, username, birth_date,
         photo_rel, 0, 1),
    )
    _, sent = create_and_send_otp(email, purpose="register")
    return jsonify({
        "ok": True,
        "message": "Akun dibuat. Cek email Anda untuk kode OTP.",
        "email": email,
        "user_id": user_id,
        "otp_sent_via_smtp": sent,
        "role": "user",
    })


@bp.post("/verify-otp")
def verify_otp_route():
    data = request.get_json(silent=True) or request.form
    email = (data.get("email") or "").strip().lower()
    code = (data.get("code") or "").strip()
    if not email or not code:
        return jsonify({"error": "Email dan kode wajib diisi"}), 400
    if not verify_otp(email, code, purpose="register"):
        return jsonify({"error": "Kode OTP salah atau kedaluwarsa"}), 400
    execute("UPDATE users SET is_verified=1 WHERE email=?", (email,))
    return jsonify({"ok": True, "message": "Verifikasi berhasil. Silakan login."})


@bp.post("/resend-otp")
def resend_otp():
    data = request.get_json(silent=True) or request.form
    email = (data.get("email") or "").strip().lower()
    if not email:
        return jsonify({"error": "Email wajib diisi"}), 400
    _, sent = create_and_send_otp(email, purpose="register")
    return jsonify({"ok": True, "otp_sent_via_smtp": sent})


@bp.post("/login")
def login():
    data = request.get_json(silent=True) or request.form
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""
    # Admin login (hard-coded credentials)
    if email == current_app.config["ADMIN_EMAIL"].lower() \
            and password == current_app.config["ADMIN_PASSWORD"]:
        login_user(0, "admin")
        return jsonify({"ok": True, "role": "admin", "redirect": "/admin"})

    row = query_one("SELECT * FROM users WHERE email=?", (email,))
    if not row or not verify_password(password, row["password_hash"]):
        return jsonify({"error": "Email atau password salah"}), 400
    if not row["is_verified"]:
        return jsonify({"error": "Email belum diverifikasi. Cek OTP di gmail Anda."}), 403
    if row["role"] == "company" and not row["is_approved"]:
        return jsonify({"error": "Akun perusahaan menunggu persetujuan admin"}), 403
    login_user(row["id"], row["role"])
    redirect = "/company" if row["role"] == "company" else "/"
    return jsonify({"ok": True, "role": row["role"], "redirect": redirect})


@bp.post("/logout")
def logout():
    logout_user()
    return jsonify({"ok": True})


@bp.get("/me")
def me():
    u = current_user()
    if not u:
        return jsonify({"user": None})
    return jsonify({"user": u})
