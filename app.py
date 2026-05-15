"""RUMAH KARIR — Flask application entrypoint.

Run with:
    python app.py
Or in production:
    gunicorn -w 2 -b 0.0.0.0:5000 app:app
"""
from __future__ import annotations

import logging
import os

from flask import Flask

from backend.database import close_db, init_db
from backend.middleware import install as install_middleware
from backend.routes.api_admin import bp as bp_api_admin
from backend.routes.api_auth import bp as bp_api_auth
from backend.routes.api_company import bp as bp_api_company
from backend.routes.api_cv import bp as bp_api_cv
from backend.routes.api_jobs import bp as bp_api_jobs
from backend.routes.api_partners import bp as bp_api_partners
from backend.routes.pages import bp as bp_pages
from config import Config


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)


def create_app() -> Flask:
    app = Flask(__name__, static_folder="static", template_folder="templates")
    app.config.from_object(Config)

    app.teardown_appcontext(close_db)

    # Blueprints
    app.register_blueprint(bp_pages)
    app.register_blueprint(bp_api_auth)
    app.register_blueprint(bp_api_jobs)
    app.register_blueprint(bp_api_cv)
    app.register_blueprint(bp_api_partners)
    app.register_blueprint(bp_api_company)
    app.register_blueprint(bp_api_admin)

    # DB init
    init_db(app)

    # Middleware (maintenance mode)
    install_middleware(app)

    @app.context_processor
    def inject_globals():
        return {"site_name": "RUMAH KARIR"}

    return app


app = create_app()


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "5000"))
    app.run(host="0.0.0.0", port=port, debug=bool(int(os.environ.get("FLASK_DEBUG", "1"))))
