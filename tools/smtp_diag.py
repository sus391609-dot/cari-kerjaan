"""SMTP diagnosis script — run this on YOUR laptop to figure out why
OTP emails are not being delivered.

Usage:
    python smtp_diag.py
    # or specify recipient
    python smtp_diag.py recipient@example.com

What it does:
    1. Checks DNS resolution of smtp.gmail.com
    2. Tests TCP connectivity to ports 587 + 465 (some ISPs block 587!)
    3. Tries SMTP STARTTLS login with verbose logging
    4. Tries SMTP-over-SSL on 465 (fallback if 587 is blocked)
    5. Sends a test email to yourself and prints the server response
    6. Prints clear pass/fail for each step

No need to run a Flask app — this is standalone.
"""
from __future__ import annotations

import os
import smtplib
import socket
import ssl
import sys
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path


def load_env_from_dotenv() -> None:
    """Best-effort load of a .env file if it exists in CWD or alongside this file."""
    candidates = [
        Path.cwd() / ".env",
        Path(__file__).resolve().parent / ".env",
        Path.cwd() / "cari-kerjaan" / ".env",
    ]
    for path in candidates:
        if not path.exists():
            continue
        print(f"[env] reading {path}")
        for raw in path.read_text(encoding="utf-8").splitlines():
            line = raw.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, _, v = line.partition("=")
            k = k.strip()
            v = v.strip().strip('"').strip("'")
            os.environ.setdefault(k, v)
        break
    else:
        print("[env] no .env found, will rely on shell env vars only")


def banner(s: str) -> None:
    print()
    print("=" * 60)
    print(s)
    print("=" * 60)


def main() -> int:
    load_env_from_dotenv()

    host = os.environ.get("SMTP_HOST", "smtp.gmail.com")
    port = int(os.environ.get("SMTP_PORT", "587"))
    user = os.environ.get("SMTP_USER", "")
    pwd = os.environ.get("SMTP_PASS", "")
    sender = os.environ.get("SMTP_FROM", user)
    recipient = sys.argv[1] if len(sys.argv) > 1 else user

    banner("Step 0 — env vars")
    print(f"SMTP_HOST = {host!r}")
    print(f"SMTP_PORT = {port}")
    print(f"SMTP_USER = {user!r}")
    print(f"SMTP_PASS = {'*' * len(pwd)} ({len(pwd)} chars)")
    print(f"SMTP_FROM = {sender!r}")
    print(f"recipient = {recipient!r}")
    if not (host and user and pwd):
        print("FATAL: SMTP_HOST/USER/PASS belum lengkap di env atau .env")
        return 2
    if " " in pwd:
        print("WARNING: SMTP_PASS has spaces — Gmail App Password should be 16 chars no spaces")

    banner("Step 1 — DNS")
    try:
        addrs = socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)
        for a in addrs[:4]:
            print(f"  -> {a[4]}")
        print("PASS: DNS resolved")
    except Exception as e:
        print(f"FAIL: DNS — {e!r}")
        return 1

    banner(f"Step 2 — TCP connect to {host}:{port}")
    try:
        with socket.create_connection((host, port), timeout=10) as s:
            print(f"PASS: connected, local addr {s.getsockname()}")
    except Exception as e:
        print(f"FAIL: TCP — {e!r}")
        print(
            "  >> ISP / firewall kamu mungkin block port 587 outbound.\n"
            "  >> Coba dari hotspot HP (tethering) untuk ngecek apakah ISP yang blokir."
        )
        # try 465 as fallback
        print()
        print(f"Step 2b — trying fallback port 465 (SSL)…")
        try:
            with socket.create_connection((host, 465), timeout=10) as s:
                print(f"  PASS via 465: {s.getsockname()}")
                port = 465
        except Exception as e2:
            print(f"  FAIL via 465 too: {e2!r}")
            print("  >> Semua SMTP port outbound diblok dari laptopmu. Ganti jaringan atau pakai mail relay HTTPS.")
            return 1

    banner(f"Step 3 — SMTP {'SSL' if port == 465 else 'STARTTLS'} login")
    try:
        ctx = ssl.create_default_context()
        if port == 465:
            smtp = smtplib.SMTP_SSL(host, port, context=ctx, timeout=20)
        else:
            smtp = smtplib.SMTP(host, port, timeout=20)
            smtp.set_debuglevel(1)
            smtp.ehlo()
            smtp.starttls(context=ctx)
            smtp.ehlo()
        if port == 465:
            smtp.set_debuglevel(1)
        smtp.login(user, pwd)
        print("PASS: SMTP authenticated")
    except smtplib.SMTPAuthenticationError as e:
        print(f"FAIL auth: {e!r}")
        print(
            "  >> App Password salah / dicabut / Gmail account belum aktifkan 2FA.\n"
            "  >> Generate ulang di https://myaccount.google.com/apppasswords\n"
            "  >> Pastikan 2FA aktif: https://myaccount.google.com/security"
        )
        return 1
    except Exception as e:
        print(f"FAIL: {type(e).__name__} — {e!r}")
        return 1

    banner(f"Step 4 — send test email to {recipient}")
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = "RUMAH KARIR — SMTP diagnosis"
        msg["From"] = sender
        msg["To"] = recipient
        body_text = "Kalau email ini masuk inbox kamu, berarti SMTP RUMAH KARIR sudah berfungsi."
        body_html = f"<p>{body_text}</p><p>Sent via {host}:{port} as {user}.</p>"
        msg.attach(MIMEText(body_text, "plain"))
        msg.attach(MIMEText(body_html, "html"))
        refused = smtp.sendmail(sender, [recipient], msg.as_string())
        smtp.quit()
        if refused:
            print(f"PARTIAL: server menerima tapi refused: {refused}")
        else:
            print("PASS: server menerima email — cek inbox + folder spam dari", recipient)
    except Exception as e:
        print(f"FAIL: sendmail — {type(e).__name__} — {e!r}")
        return 1

    banner("Summary")
    print("Semua step PASS. Kalau OTP signup masih nggak nyampe:")
    print("  1. Cek Spam / Tab 'Promotions' di Gmail.")
    print("  2. Pastikan Flask kamu memang load .env (taruh .env di folder yang sama dengan app.py).")
    print("  3. Cek log Flask saat register — kalau 'otp_sent_via_smtp: false' artinya .env nggak ke-load.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
