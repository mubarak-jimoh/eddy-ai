from eddy.db import get_db


def test_pages_need_a_login(browser):
    for path in ("/", "/new", "/reports/1", "/admin/"):
        response = browser.get(path)
        assert response.status_code == 302
        assert response.headers["Location"] == "/login"


def test_sign_in_and_out(browser):
    assert browser.login("sam@example.com").headers["Location"] == "/"
    assert "Sam Staff" in browser.get("/").get_data(as_text=True)

    browser.post("/logout")
    assert browser.get("/").status_code == 302


def test_wrong_password_and_unknown_email_give_the_same_message(browser):
    wrong_password = browser.login("sam@example.com", "nope-nope-nope").get_data(as_text=True)
    unknown_email = browser.login("nobody@example.com").get_data(as_text=True)
    assert "Incorrect email or password." in wrong_password
    assert "Incorrect email or password." in unknown_email


def test_register_creates_a_staff_account(app, browser):
    response = browser.post(
        "/register",
        {"name": "New Person", "email": "New@Example.com", "password": "a-long-password"},
    )
    assert response.status_code == 302

    with app.app_context():
        user = get_db().execute("SELECT * FROM users WHERE email = 'new@example.com'").fetchone()
    assert user["role"] == "staff"
    assert user["password_hash"] != "a-long-password"  # stored hashed, never as typed
    assert browser.login("new@example.com", "a-long-password").status_code == 302


def test_register_cannot_choose_a_role(app, browser):
    browser.post(
        "/register",
        {
            "name": "Sneaky",
            "email": "sneaky@example.com",
            "password": "a-long-password",
            "role": "admin",
        },
    )
    with app.app_context():
        user = (
            get_db().execute("SELECT role FROM users WHERE email = 'sneaky@example.com'").fetchone()
        )
    assert user["role"] == "staff"


def test_register_rejects_short_passwords_and_duplicate_emails(browser):
    short = browser.post("/register", {"name": "A", "email": "a@example.com", "password": "short"})
    assert "at least 10 characters" in short.get_data(as_text=True)

    duplicate = browser.post(
        "/register", {"name": "Sam", "email": "sam@example.com", "password": "a-long-password"}
    )
    assert "already exists" in duplicate.get_data(as_text=True)


def test_post_without_csrf_token_is_rejected(app):
    client = app.test_client()
    client.get("/login")
    response = client.post("/login", data={"email": "sam@example.com", "password": "x"})
    assert response.status_code == 400


def test_post_with_wrong_csrf_token_is_rejected(sam):
    response = sam.client.post("/logout", data={"csrf_token": "made-up"})
    assert response.status_code == 400
    assert sam.get("/").status_code == 200  # still signed in


def test_deleted_account_loses_access_immediately(app, sam):
    with app.app_context():
        database = get_db()
        database.execute("DELETE FROM users WHERE email = 'sam@example.com'")
        database.commit()
    assert sam.get("/").status_code == 302


def test_security_headers_are_set(sam):
    headers = sam.get("/").headers
    assert headers["X-Frame-Options"] == "DENY"
    assert headers["X-Content-Type-Options"] == "nosniff"
    assert headers["Cache-Control"] == "no-store"
    assert "default-src 'self'" in headers["Content-Security-Policy"]
