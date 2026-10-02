"""Login checks, role checks and CSRF protection."""

from __future__ import annotations

import functools
import hmac
import secrets

from flask import Flask, abort, g, redirect, request, session, url_for

from eddy.db import get_db


def init_app(app: Flask) -> None:
    @app.before_request
    def load_user() -> None:
        """Look the signed-in user up fresh on every request.

        Reading the role from the database, not from the session cookie, means
        a deleted or demoted account loses access straight away.
        """
        user_id = session.get("user_id")
        g.user = None
        if user_id is not None:
            g.user = (
                get_db()
                .execute("SELECT id, name, email, role FROM users WHERE id = ?", (user_id,))
                .fetchone()
            )
            if g.user is None:
                session.clear()

    @app.before_request
    def check_csrf() -> None:
        """Reject any form post that does not carry this session's token.

        Without this, another website could submit a form to EddyAI using a
        signed-in user's cookies (cross-site request forgery).
        """
        if request.method == "POST":
            expected = session.get("csrf_token", "")
            sent = request.form.get("csrf_token", "")
            # compare_digest takes the same time whether or not the tokens
            # match, so the token cannot be guessed one character at a time.
            if not expected or not hmac.compare_digest(expected, sent):
                abort(400, "This form has expired. Go back, refresh the page and try again.")

    @app.context_processor
    def inject_csrf_token() -> dict:
        return {"csrf_token": csrf_token}

    @app.after_request
    def security_headers(response):
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "same-origin")
        response.headers.setdefault(
            "Content-Security-Policy", "default-src 'self'; frame-ancestors 'none'"
        )
        # Reports are about students. Do not let a shared computer cache them.
        if g.get("user") is not None:
            response.headers["Cache-Control"] = "no-store"
        return response


def csrf_token() -> str:
    if "csrf_token" not in session:
        session["csrf_token"] = secrets.token_urlsafe(32)
    return session["csrf_token"]


def login_required(view):
    @functools.wraps(view)
    def wrapped(*args, **kwargs):
        if g.user is None:
            return redirect(url_for("auth.login"))
        return view(*args, **kwargs)

    return wrapped


def admin_required(view):
    @functools.wraps(view)
    def wrapped(*args, **kwargs):
        if g.user is None:
            return redirect(url_for("auth.login"))
        if g.user["role"] != "admin":
            abort(403)
        return view(*args, **kwargs)

    return wrapped
