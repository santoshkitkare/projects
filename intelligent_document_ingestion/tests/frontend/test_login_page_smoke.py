# tests/test_login_page_smoke.py
from streamlit.testing.v1 import AppTest


def test_login_page_renders(monkeypatch):
    # fake backend response
    import requests

    class FakeResponse:
        status_code = 200

        def json(self):
            return {
                "accessToken": "dummy",
                "userId": "u1",
                "role": "admin",
            }

    monkeypatch.setattr(requests, "post", lambda *a, **k: FakeResponse())

    at = AppTest.from_file("frontend/pages/Login.py")
    at.run()
    # fill username/password and click login
    at.text_input[0].input("admin")
    at.text_input[1].input("admin@123")
    at.button[0].click().run()
    # just assert it didn't crash
    assert at.session_state["access_token"] == "dummy"
