"""EddyAI: structured student support plans using the PCAR framework."""

from __future__ import annotations

import os
import secrets

from flask import Flask, render_template

from eddy import admin, auth, db, reports, security


def create_app(config: dict | None = None) -> Flask:
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_mapping(
        # Set SECRET_KEY in production. The random fallback is fine for local
        # use, but it changes on restart, which signs everyone out.
        SECRET_KEY=os.environ.get("SECRET_KEY") or secrets.token_hex(32),
        DATABASE=os.path.join(app.instance_path, "eddy.sqlite3"),
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        SESSION_COOKIE_SECURE=os.environ.get("FLASK_ENV") == "production",
        MAX_CONTENT_LENGTH=64 * 1024,  # a support request is text; 64 KB is plenty
    )
    if config:
        app.config.update(config)

    os.makedirs(app.instance_path, exist_ok=True)

    db.init_app(app)
    security.init_app(app)
    app.register_blueprint(auth.bp)
    app.register_blueprint(reports.bp)
    app.register_blueprint(admin.bp)

    @app.errorhandler(403)
    def forbidden(_error):
        return render_template(
            "error.html", code=403, message="You do not have access to this page."
        ), 403

    @app.errorhandler(404)
    def not_found(_error):
        return render_template("error.html", code=404, message="That page does not exist."), 404

    return app
