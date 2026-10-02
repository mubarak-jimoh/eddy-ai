"""Sign up, sign in and sign out."""

from __future__ import annotations

import sqlite3

from flask import Blueprint, flash, g, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

from eddy.db import get_db

bp = Blueprint("auth", __name__)

MIN_PASSWORD_LENGTH = 10

# Checked when the email does not exist, so a wrong email takes as long to
# reject as a wrong password. Otherwise response time reveals who has an account.
_DUMMY_HASH = generate_password_hash("not-a-real-password")


def validate_password(password: str) -> str | None:
    if len(password) < MIN_PASSWORD_LENGTH:
        return f"Password must be at least {MIN_PASSWORD_LENGTH} characters."
    return None


@bp.route("/register", methods=("GET", "POST"))
def register():
    if g.user:
        return redirect(url_for("reports.index"))

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        error = None
        if not name or len(name) > 80:
            error = "Enter your name."
        elif "@" not in email or len(email) > 254:
            error = "Enter a valid email address."
        else:
            error = validate_password(password)

        if error is None:
            database = get_db()
            try:
                # New accounts are always staff. Admins are created from the
                # command line, so nobody can sign themselves up as one.
                database.execute(
                    "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
                    (name, email, generate_password_hash(password)),
                )
                database.commit()
            except sqlite3.IntegrityError:
                error = "An account with that email already exists."
            else:
                flash("Account created. You can sign in now.")
                return redirect(url_for("auth.login"))

        flash(error, "error")

    return render_template("register.html")


@bp.route("/login", methods=("GET", "POST"))
def login():
    if g.user:
        return redirect(url_for("reports.index"))

    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        user = get_db().execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
        password_ok = check_password_hash(user["password_hash"] if user else _DUMMY_HASH, password)

        if user and password_ok:
            # Start a fresh session so a cookie planted before login is useless.
            session.clear()
            session["user_id"] = user["id"]
            return redirect(url_for("reports.index"))

        # One message for both cases, so it does not confirm which emails exist.
        flash("Incorrect email or password.", "error")

    return render_template("login.html")


@bp.post("/logout")
def logout():
    session.clear()
    return redirect(url_for("auth.login"))
