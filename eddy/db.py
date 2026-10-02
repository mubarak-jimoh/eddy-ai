"""SQLite access. One connection per request, closed automatically."""

from __future__ import annotations

import sqlite3

import click
from flask import Flask, current_app, g
from flask.cli import with_appcontext
from werkzeug.security import generate_password_hash

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    name          TEXT NOT NULL,
    email         TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    role          TEXT NOT NULL DEFAULT 'staff' CHECK (role IN ('staff', 'admin')),
    created_at    TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS reports (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id     INTEGER NOT NULL REFERENCES users (id) ON DELETE CASCADE,
    student_ref TEXT NOT NULL,
    needs       TEXT NOT NULL,
    problem     TEXT NOT NULL,
    plan_json   TEXT NOT NULL,
    source      TEXT NOT NULL CHECK (source IN ('ai', 'demo')),
    status      TEXT NOT NULL DEFAULT 'new' CHECK (status IN ('new', 'reviewed')),
    created_at  TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS reports_user ON reports (user_id);
"""


def get_db() -> sqlite3.Connection:
    if "db" not in g:
        g.db = sqlite3.connect(current_app.config["DATABASE"])
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


def close_db(_error=None) -> None:
    connection = g.pop("db", None)
    if connection is not None:
        connection.close()


def init_db() -> None:
    get_db().executescript(SCHEMA)


@click.command("create-admin")
@click.option("--name", prompt=True)
@click.option("--email", prompt=True)
@click.password_option()
@with_appcontext
def create_admin(name: str, email: str, password: str) -> None:
    """Create an admin account. Admins cannot be made from the sign-up page."""
    from eddy.auth import validate_password

    problem = validate_password(password)
    if problem:
        raise click.ClickException(problem)

    database = get_db()
    try:
        database.execute(
            "INSERT INTO users (name, email, password_hash, role) VALUES (?, ?, ?, 'admin')",
            (name.strip(), email.strip().lower(), generate_password_hash(password)),
        )
        database.commit()
    except sqlite3.IntegrityError as error:
        raise click.ClickException("An account with that email already exists.") from error
    click.echo(f"Admin account created for {email}.")


def init_app(app: Flask) -> None:
    app.teardown_appcontext(close_db)
    app.cli.add_command(create_admin)
    with app.app_context():
        init_db()
