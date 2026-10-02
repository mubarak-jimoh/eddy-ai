import json

from eddy.db import get_db


def test_creating_a_report_saves_a_pcar_plan(app, sam):
    report_id = sam.create_report()

    with app.app_context():
        report = get_db().execute("SELECT * FROM reports WHERE id = ?", (report_id,)).fetchone()
    plan = json.loads(report["plan_json"])
    assert set(plan) == {"problem", "causes", "actions", "result"}
    assert report["source"] == "demo"
    assert report["status"] == "new"

    page = sam.get(f"/reports/{report_id}").get_data(as_text=True)
    for heading in ("Problem", "Possible causes", "Actions", "Intended result"):
        assert heading in page
    assert "Example plan." in page  # demo plans are labelled, never passed off as AI


def test_report_appears_in_my_reports(sam):
    sam.create_report("JS-07")
    assert "JS-07" in sam.get("/").get_data(as_text=True)


def test_missing_fields_are_rejected_and_keep_what_was_typed(sam):
    response = sam.post("/new", {"student_ref": "JS-07", "needs": "Some needs", "problem": "  "})
    page = response.get_data(as_text=True)
    assert "Describe the problem" in page
    assert "Some needs" in page


def test_over_long_text_is_rejected(sam):
    response = sam.post("/new", {"student_ref": "JS-07", "needs": "x" * 4001, "problem": "p"})
    assert "under 4000 characters" in response.get_data(as_text=True)


def test_staff_cannot_see_each_others_reports(sam, tara):
    report_id = sam.create_report()
    assert tara.get(f"/reports/{report_id}").status_code == 404
    assert "JS-07" not in tara.get("/").get_data(as_text=True)


def test_staff_cannot_delete_each_others_reports(app, sam, tara):
    report_id = sam.create_report()
    assert tara.post(f"/reports/{report_id}/delete").status_code == 404
    assert sam.get(f"/reports/{report_id}").status_code == 200


def test_owner_can_delete_a_report(sam):
    report_id = sam.create_report()
    assert sam.post(f"/reports/{report_id}/delete").status_code == 302
    assert sam.get(f"/reports/{report_id}").status_code == 404


def test_html_typed_by_staff_is_shown_as_text(sam):
    sam.post(
        "/new",
        {"student_ref": "<script>alert(1)</script>", "needs": "<b>bold</b>", "problem": "p"},
    )
    page = sam.get("/").get_data(as_text=True)
    assert "<script>alert(1)</script>" not in page
    assert "&lt;script&gt;" in page
