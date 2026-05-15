"""SMTP-based OTP delivery.

Uses the stdlib ``smtplib``. If SMTP is not configured, the OTP is
logged to the application logger so development without real SMTP
credentials still works (the OTP is then surfaced in the API response
when ``debug`` is enabled).
"""
from __future__ import annotations

import logging
import smtplib
import ssl
import time
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from secrets import randbelow

from flask import current_app

from .database import execute, query_one


logger = logging.getLogger(__name__)


def generate_otp() -> str:
    return f"{randbelow(1_000_000):06d}"


def _build_message(to_email: str, code: str) -> MIMEMultipart:
    cfg = current_app.config
    msg = MIMEMultipart("alternative")
    msg["Subject"] = "Kode OTP RUMAH KARIR"
    msg["From"] = cfg["SMTP_FROM"]
    msg["To"] = to_email
    text = (
        f"Halo,\n\nKode OTP RUMAH KARIR Anda adalah: {code}\n"
        "Kode ini berlaku selama 10 menit.\n\n"
        "Jika Anda tidak meminta kode ini, abaikan email ini."
    )
    html = f"""
    <div style=\"font-family: Arial, sans-serif; max-width: 480px; margin:auto;\">
      <h2 style=\"color:#111\">RUMAH KARIR</h2>
      <p>Halo,</p>
      <p>Berikut kode OTP untuk verifikasi akun Anda:</p>
      <p style=\"font-size:28px;font-weight:700;letter-spacing:6px;background:#f3f4f6;
                padding:12px 16px;display:inline-block;border-radius:8px;color:#111;\">{code}</p>
      <p style=\"color:#555\">Kode ini berlaku selama 10 menit.</p>
      <p style=\"color:#888;font-size:12px\">Abaikan email ini jika Anda tidak meminta kode.</p>
    </div>
    """
    msg.attach(MIMEText(text, "plain"))
    msg.attach(MIMEText(html, "html"))
    return msg


def send_otp_email(to_email: str, code: str) -> bool:
    cfg = current_app.config
    host = cfg.get("SMTP_HOST")
    user = cfg.get("SMTP_USER")
    pwd = cfg.get("SMTP_PASS")
    port = int(cfg.get("SMTP_PORT", 587))
    msg = _build_message(to_email, code)
    if not (host and user and pwd):
        logger.warning(
            "SMTP not configured; OTP for %s = %s (dev fallback)", to_email, code
        )
        return False
    try:
        ctx = ssl.create_default_context()
        if port == 465:
            with smtplib.SMTP_SSL(host, port, context=ctx, timeout=15) as s:
                s.login(user, pwd)
                s.sendmail(cfg["SMTP_FROM"], [to_email], msg.as_string())
        else:
            with smtplib.SMTP(host, port, timeout=15) as s:
                s.ehlo()
                s.starttls(context=ctx)
                s.ehlo()
                s.login(user, pwd)
                s.sendmail(cfg["SMTP_FROM"], [to_email], msg.as_string())
        return True
    except Exception as exc:  # pragma: no cover - SMTP runtime failure
        logger.exception("Failed to send OTP via SMTP to %s: %s", to_email, exc)
        return False


def create_and_send_otp(email: str, purpose: str = "register") -> tuple[str, bool]:
    """Generate, persist and email an OTP. Returns ``(code, smtp_sent)``."""
    code = generate_otp()
    expires_at = int(time.time()) + int(current_app.config.get("OTP_EXP_SECONDS", 600))
    execute(
        "INSERT INTO otps(email, code, purpose, expires_at) VALUES(?,?,?,?)",
        (email.lower(), code, purpose, expires_at),
    )
    sent = send_otp_email(email, code)
    return code, sent


def verify_otp(email: str, code: str, purpose: str = "register") -> bool:
    row = query_one(
        "SELECT id, expires_at, used FROM otps "
        "WHERE email=? AND code=? AND purpose=? "
        "ORDER BY id DESC LIMIT 1",
        (email.lower(), code, purpose),
    )
    if row is None:
        return False
    if row["used"]:
        return False
    if int(row["expires_at"]) < int(time.time()):
        return False
    execute("UPDATE otps SET used=1 WHERE id=?", (row["id"],))
    return True
