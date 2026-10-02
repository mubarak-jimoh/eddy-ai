def test_staff_cannot_open_the_admin_dashboard(sam):
    assert sam.get("/admin/").status_code == 403


def test_staff_cannot_change_a_report_status(sam):
    report_id = sam.create_report()
    response = sam.post(f"/admin/reports/{report_id}/status", {"status": "reviewed"})
    assert response.status_code == 403


def test_admin_sees_every_report(sam, tara, admin):
    sam.create_report("JS-07")
    tara.create_report("AK-12")
    page = admin.get("/admin/").get_data(as_text=True)
    assert "JS-07" in page and "AK-12" in page
    assert "Sam Staff" in page and "Tara Teacher" in page


def test_admin_can_open_any_report(sam, admin):
    report_id = sam.create_report()
    assert admin.get(f"/reports/{report_id}").status_code == 200


def test_admin_can_mark_a_report_reviewed_and_filter(sam, admin):
    first = sam.create_report("JS-07")
    sam.create_report("AK-12")

    admin.post(f"/admin/reports/{first}/status", {"status": "reviewed"})

    reviewed = admin.get("/admin/?status=reviewed").get_data(as_text=True)
    assert "JS-07" in reviewed and "AK-12" not in reviewed
    waiting = admin.get("/admin/?status=new").get_data(as_text=True)
    assert "AK-12" in waiting and "JS-07" not in waiting


def test_unknown_status_is_ignored(sam, admin):
    report_id = sam.create_report()
    response = admin.post(
        f"/admin/reports/{report_id}/status", {"status": "hacked"}, follow_redirects=True
    )
    assert "Unknown status." in response.get_data(as_text=True)


def test_status_filter_is_not_open_to_sql_injection(sam, admin):
    sam.create_report("JS-07")
    response = admin.get("/admin/?status=new' OR '1'='1")
    assert response.status_code == 200
    assert "JS-07" in response.get_data(as_text=True)  # treated as "no filter"


def test_admin_can_delete_any_report(sam, admin):
    report_id = sam.create_report()
    response = admin.post(f"/reports/{report_id}/delete")
    assert response.headers["Location"] == "/admin/"
    assert sam.get(f"/reports/{report_id}").status_code == 404


def test_create_admin_command(app):
    runner = app.test_cli_runner()
    result = runner.invoke(
        args=["create-admin", "--name", "Root", "--email", "root@example.com"],
        input="a-long-password\na-long-password\n",
    )
    assert "Admin account created" in result.output

    again = runner.invoke(
        args=["create-admin", "--name", "Root", "--email", "root@example.com"],
        input="a-long-password\na-long-password\n",
    )
    assert "already exists" in again.output
