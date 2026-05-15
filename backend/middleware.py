"""Middleware: maintenance mode."""
from __future__ import annotations

from flask import jsonify, render_template, request, session

from .database import get_setting


# Endpoints accessible while the site is in maintenance mode.
ALLOWED_WHEN_MAINTENANCE = {
    "static",
    "pages.login",
    "pages.logout",
    "pages.maintenance",
    "api_auth.login",
    "api_auth.logout",
}


def install(app) -> None:
    @app.before_request
    def _check_maintenance():
        if request.endpoint and request.endpoint in ALLOWED_WHEN_MAINTENANCE:
            return None
        if session.get("role") == "admin":
            return None
        try:
            mode = get_setting("maintenance_mode", "0")
        except Exception:
            mode = "0"
        if mode == "1":
            wants_json = request.path.startswith("/api/") or request.is_json
            if wants_json:
                return jsonify({"error": "maintenance"}), 503
            return render_template("maintenance.html"), 503
        return None
