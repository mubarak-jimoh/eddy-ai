"""Admin dashboard: review and manage every saved report."""

from __future__ import annotations

from flask import Blueprint, flash, redirect, render_template, request, url_for

from eddy.db import get_db
from eddy.reports import get_report
from eddy.security import admin_required

bp = Blueprint("admin", __name__, url_prefix="/admin")

STATUSES = ("new", "reviewed")


@bp.route("/")
@admin_required
def dashboard():
    status = request.args.get("status", "")
    database = get_db()

    query = (
        "SELECT reports.id, student_name, problem, status, source, reports.created_at, "
        "users.name AS author FROM reports JOIN users ON users.id = reports.user_id"
    )
    # The status comes from the URL, so it is passed as a parameter (the ?),
    # never pasted into the SQL. That is what stops SQL injection.
    parameters: tuple = ()
    if status in STATUSES:
        query += " WHERE status = ?"
        parameters = (status,)
    reports = database.execute(query + " ORDER BY reports.id DESC", parameters).fetchall()

    totals = database.execute(
        "SELECT COUNT(*) AS total, "
        "COALESCE(SUM(status = 'new'), 0) AS new, "
        "COALESCE(SUM(status = 'reviewed'), 0) AS reviewed FROM reports"
    ).fetchone()
    staff = database.execute(
        "SELECT users.name, users.email, users.role, COUNT(reports.id) AS report_count "
        "FROM users LEFT JOIN reports ON reports.user_id = users.id "
        "GROUP BY users.id ORDER BY users.name"
    ).fetchall()

    return render_template(
        "admin/dashboard.html", reports=reports, totals=totals, staff=staff, status=status
    )


@bp.post("/reports/<int:report_id>/status")
@admin_required
def set_status(report_id: int):
    report = get_report(report_id)
    status = request.form.get("status", "")
    if status not in STATUSES:
        flash("Unknown status.", "error")
    else:
        database = get_db()
        database.execute("UPDATE reports SET status = ? WHERE id = ?", (status, report["id"]))
        database.commit()
        flash(f"Report marked as {status}.")
    # Go back to wherever the button was pressed. The destination is chosen
    # here, not taken from the form, so it cannot be pointed at another site.
    if request.form.get("from") == "report":
        return redirect(url_for("reports.view", report_id=report["id"]))
    return redirect(url_for("admin.dashboard"))
