"""Create, list, view and delete support plans."""

from __future__ import annotations

import json

from flask import Blueprint, abort, flash, g, redirect, render_template, request, url_for

from eddy import pcar
from eddy.db import get_db
from eddy.security import login_required

bp = Blueprint("reports", __name__)

MAX_NAME_LENGTH = 80
MAX_TEXT_LENGTH = 4000


def validate(student_name: str, needs: str, problem: str) -> str | None:
    if not student_name:
        return "Enter the student's name."
    if len(student_name) > MAX_NAME_LENGTH:
        return f"Keep the student's name under {MAX_NAME_LENGTH} characters."
    if not needs:
        return "Describe the student's needs."
    if not problem:
        return "Describe the problem the student is facing."
    if len(needs) > MAX_TEXT_LENGTH or len(problem) > MAX_TEXT_LENGTH:
        return f"Keep each description under {MAX_TEXT_LENGTH} characters."
    return None


def get_report(report_id: int):
    """Fetch a report the current user is allowed to see, or stop with 404.

    Staff see only their own reports. A report that belongs to someone else
    gives the same 404 as one that does not exist, so ids cannot be probed.
    """
    report = (
        get_db()
        .execute(
            "SELECT reports.*, users.name AS author FROM reports "
            "JOIN users ON users.id = reports.user_id WHERE reports.id = ?",
            (report_id,),
        )
        .fetchone()
    )
    if report is None:
        abort(404)
    if report["user_id"] != g.user["id"] and g.user["role"] != "admin":
        abort(404)
    return report


@bp.route("/")
@login_required
def index():
    reports = (
        get_db()
        .execute(
            "SELECT id, student_name, problem, status, source, created_at FROM reports "
            "WHERE user_id = ? ORDER BY id DESC",
            (g.user["id"],),
        )
        .fetchall()
    )
    return render_template("index.html", reports=reports)


@bp.route("/new", methods=("GET", "POST"))
@login_required
def new():
    form = {"student_name": "", "needs": "", "problem": ""}

    if request.method == "POST":
        form = {field: request.form.get(field, "").strip() for field in form}
        error = validate(**form)

        if error is None:
            try:
                # Only the needs and the problem go to the AI. The student's name
                # stays in this app's database and is never sent anywhere.
                plan, source = pcar.generate_plan(form["needs"], form["problem"])
            except pcar.PlanError as plan_error:
                error = str(plan_error)
            else:
                database = get_db()
                cursor = database.execute(
                    "INSERT INTO reports "
                    "(user_id, student_name, needs, problem, plan_json, source) "
                    "VALUES (?, ?, ?, ?, ?, ?)",
                    (
                        g.user["id"],
                        form["student_name"],
                        form["needs"],
                        form["problem"],
                        plan.model_dump_json(),
                        source,
                    ),
                )
                database.commit()
                return redirect(url_for("reports.view", report_id=cursor.lastrowid))

        flash(error, "error")

    return render_template("new.html", form=form, ai_available=pcar.ai_available())


@bp.route("/reports/<int:report_id>")
@login_required
def view(report_id: int):
    report = get_report(report_id)
    return render_template("report.html", report=report, plan=json.loads(report["plan_json"]))


@bp.post("/reports/<int:report_id>/delete")
@login_required
def delete(report_id: int):
    report = get_report(report_id)
    database = get_db()
    database.execute("DELETE FROM reports WHERE id = ?", (report["id"],))
    database.commit()
    flash("Report deleted.")
    if g.user["role"] == "admin" and report["user_id"] != g.user["id"]:
        return redirect(url_for("admin.dashboard"))
    return redirect(url_for("reports.index"))
