import re

import pytest
from werkzeug.security import generate_password_hash

from eddy import create_app
from eddy.db import get_db

PASSWORD = "correct-horse-battery"


@pytest.fixture
def app(tmp_path, monkeypatch):
    # No key means demo mode, so tests never call the real AI service.
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    app = create_app({"TESTING": True, "DATABASE": str(tmp_path / "test.sqlite3")})
    with app.app_context():
        database = get_db()
        for name, email, role in (
            ("Sam Staff", "sam@example.com", "staff"),
            ("Tara Teacher", "tara@example.com", "staff"),
            ("Ada Admin", "ada@example.com", "admin"),
        ):
            database.execute(
                "INSERT INTO users (name, email, password_hash, role) VALUES (?, ?, ?, ?)",
                (name, email, generate_password_hash(PASSWORD), role),
            )
        database.commit()
    return app


class Browser:
    """A test client that fills in the CSRF token the way a real browser would."""

    def __init__(self, app):
        self.client = app.test_client()

    def token(self) -> str:
        page = self.client.get("/login", follow_redirects=True).get_data(as_text=True)
        return re.search(r'name="csrf_token" value="([^"]+)"', page).group(1)

    def get(self, path, **kwargs):
        return self.client.get(path, **kwargs)

    def post(self, path, data=None, **kwargs):
        data = {"csrf_token": self.token(), **(data or {})}
        return self.client.post(path, data=data, **kwargs)

    def login(self, email, password=PASSWORD):
        return self.post("/login", {"email": email, "password": password})

    def create_report(self, student_name="Jordan Smith"):
        response = self.post(
            "/new",
            {
                "student_name": student_name,
                "needs": "Dyslexia. Works well with printed notes.",
                "problem": "Falling behind on written coursework. Has missed two deadlines.",
            },
        )
        assert response.status_code == 302
        return int(response.headers["Location"].rsplit("/", 1)[1])


@pytest.fixture
def browser(app):
    return Browser(app)


@pytest.fixture
def sam(app):
    browser = Browser(app)
    browser.login("sam@example.com")
    return browser


@pytest.fixture
def tara(app):
    browser = Browser(app)
    browser.login("tara@example.com")
    return browser


@pytest.fixture
def admin(app):
    browser = Browser(app)
    browser.login("ada@example.com")
    return browser
