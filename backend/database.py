"""SQLite helpers for the RUMAH KARIR app.

Uses the built-in ``sqlite3`` module per the user's stack requirement
(SQLite + Python). All queries in route modules go through ``get_db()``
or the helpers below.
"""
from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from typing import Any, Iterable

from flask import current_app, g


SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    role TEXT NOT NULL CHECK(role IN ('user','company','admin')),
    email TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    full_name TEXT,
    username TEXT,
    birth_date TEXT,
    photo_path TEXT,
    is_verified INTEGER NOT NULL DEFAULT 0,
    is_approved INTEGER NOT NULL DEFAULT 1, -- 1 default for normal users, 0 for companies until admin approves
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS companies (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    owner_user_id INTEGER, -- NULL for companies created by admin
    name TEXT NOT NULL,
    slug TEXT UNIQUE,
    industry TEXT,
    website TEXT,
    address TEXT,
    province TEXT,
    city TEXT,
    country TEXT DEFAULT 'Indonesia',
    description TEXT,
    logo_path TEXT,
    employees TEXT,
    founded_year INTEGER,
    is_approved INTEGER NOT NULL DEFAULT 1,
    search_count INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(owner_user_id) REFERENCES users(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS jobs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id INTEGER NOT NULL,
    title TEXT NOT NULL,
    description TEXT,
    requirements TEXT,
    skills TEXT, -- comma-separated lowercase skills
    employment_type TEXT, -- full-time / part-time / contract / internship
    country TEXT DEFAULT 'Indonesia',
    province TEXT,
    city TEXT,
    salary_min INTEGER,
    salary_max INTEGER,
    min_experience INTEGER DEFAULT 0,
    min_age INTEGER,
    max_age INTEGER,
    is_active INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(company_id) REFERENCES companies(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS otps (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email TEXT NOT NULL,
    code TEXT NOT NULL,
    purpose TEXT NOT NULL DEFAULT 'register',
    expires_at INTEGER NOT NULL,
    used INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS partners (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT,
    image_path TEXT NOT NULL,
    link TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS experiences (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    rating INTEGER NOT NULL DEFAULT 5,
    title TEXT,
    body TEXT NOT NULL,
    is_visible INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS cv_uploads (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    file_path TEXT NOT NULL,
    parsed_skills TEXT,    -- comma-separated lowercase
    parsed_age INTEGER,
    parsed_experience_years INTEGER,
    raw_text TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS company_search_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id INTEGER NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(company_id) REFERENCES companies(id) ON DELETE CASCADE
);
"""


def get_db() -> sqlite3.Connection:
    """Return a request-scoped SQLite connection."""
    if "db" not in g:
        conn = sqlite3.connect(current_app.config["DATABASE_PATH"])
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON;")
        g.db = conn
    return g.db


def close_db(_exc: BaseException | None = None) -> None:
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db(app) -> None:
    """Create tables if missing and seed default settings."""
    with app.app_context():
        db = get_db()
        db.executescript(SCHEMA)
        # Default settings
        db.execute(
            "INSERT OR IGNORE INTO settings(key, value) VALUES('maintenance_mode', '0')"
        )
        db.commit()


@contextmanager
def db_cursor() -> Any:
    conn = get_db()
    cur = conn.cursor()
    try:
        yield cur
        conn.commit()
    finally:
        cur.close()


def query_all(sql: str, params: Iterable[Any] = ()) -> list[sqlite3.Row]:
    cur = get_db().execute(sql, tuple(params))
    rows = cur.fetchall()
    cur.close()
    return rows


def query_one(sql: str, params: Iterable[Any] = ()) -> sqlite3.Row | None:
    cur = get_db().execute(sql, tuple(params))
    row = cur.fetchone()
    cur.close()
    return row


def execute(sql: str, params: Iterable[Any] = ()) -> int:
    conn = get_db()
    cur = conn.execute(sql, tuple(params))
    conn.commit()
    last_id = cur.lastrowid
    cur.close()
    return last_id or 0


def get_setting(key: str, default: str = "") -> str:
    row = query_one("SELECT value FROM settings WHERE key=?", (key,))
    return row["value"] if row else default


def set_setting(key: str, value: str) -> None:
    execute(
        "INSERT INTO settings(key,value) VALUES(?,?) "
        "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
        (key, value),
    )
