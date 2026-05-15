"""Application configuration loaded from environment variables."""
from __future__ import annotations

import os
from pathlib import Path

try:
    from dotenv import load_dotenv  # type: ignore
    load_dotenv()
except Exception:  # pragma: no cover - python-dotenv is optional
    pass


BASE_DIR = Path(__file__).resolve().parent
INSTANCE_DIR = BASE_DIR / "instance"
INSTANCE_DIR.mkdir(parents=True, exist_ok=True)

UPLOAD_DIR = BASE_DIR / "static" / "uploads"
CV_UPLOAD_DIR = UPLOAD_DIR / "cv"
PHOTO_UPLOAD_DIR = UPLOAD_DIR / "photos"
PARTNER_UPLOAD_DIR = UPLOAD_DIR / "partners"
for _d in (CV_UPLOAD_DIR, PHOTO_UPLOAD_DIR, PARTNER_UPLOAD_DIR):
    _d.mkdir(parents=True, exist_ok=True)


class Config:
    SECRET_KEY = os.environ.get("FLASK_SECRET_KEY", "rumah-karir-dev-secret-change-me")
    DATABASE_PATH = str(INSTANCE_DIR / "rumahkarir.db")

    # SMTP / OTP
    SMTP_HOST = os.environ.get("SMTP_HOST", "smtp.gmail.com")
    SMTP_PORT = int(os.environ.get("SMTP_PORT", "587"))
    SMTP_USER = os.environ.get("SMTP_USER", "")
    SMTP_PASS = os.environ.get("SMTP_PASS", "")
    SMTP_FROM = os.environ.get("SMTP_FROM", "RUMAH KARIR <no-reply@rumahkarir.local>")

    # Admin (hard-coded credentials per spec)
    ADMIN_EMAIL = os.environ.get("ADMIN_EMAIL", "admin@admin.com")
    ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "admin123")

    # Uploads
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16 MB
    CV_UPLOAD_DIR = str(CV_UPLOAD_DIR)
    PHOTO_UPLOAD_DIR = str(PHOTO_UPLOAD_DIR)
    PARTNER_UPLOAD_DIR = str(PARTNER_UPLOAD_DIR)

    # OTP
    OTP_EXP_SECONDS = 10 * 60  # 10 minutes
