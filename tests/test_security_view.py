from pathlib import Path

from streamlit.testing.v1 import AppTest

from src.dashboard.views.security import audit_rows, permission_matrix, severity_counts
from src.managers.SecurityManager import SecurityManager

ENTRYPOINT = Path(__file__).parent.parent / "streamlit_app.py"


def test_permission_matrix_marks_each_permission_in_words():
    rows = {r["user"]: r for r in permission_matrix(SecurityManager())}
    assert rows["u_guest"]["r"] == "✓ yes"
    assert rows["u_guest"]["w"] == "✗ no"
    assert all(rows["u_admin"][p] == "✓ yes" for p in ("r", "w", "x", "admin", "network"))


def test_three_failed_logins_raise_one_high_alert():
    manager = SecurityManager()
    for time in range(3):
        manager.login("u_guest", "wrong", timestamp=time)
    counts = {row["severity"]: row["alerts"] for row in severity_counts(manager)}
    assert sum(counts.values()) == 1
    assert len(audit_rows(manager)) >= 3


def security_app() -> AppTest:
    app = AppTest.from_file(str(ENTRYPOINT), default_timeout=30).run()
    app.selectbox(key="security-user").set_value("u_guest").run()
    app.text_input(key="security-secret").input("demo_guest_pass").run()
    return app.button(key="security-login").click().run()


def test_login_then_denied_write_is_audited_and_logged():
    app = security_app()
    assert not app.exception
    assert app.session_state["security-session"]
    app.selectbox(key="security-permission").set_value("w").run()
    app.button(key="security-check").click().run()
    assert any("Denied" in e.value for e in app.error)
    security_events = [e for e in app.session_state.events if e.manager == "Security"]
    assert {e.event_type for e in security_events} >= {"LOGIN_SUCCESS", "ACCESS_DENIED", "SECURITY_ALERT"}


def test_wrong_credential_is_rejected():
    app = AppTest.from_file(str(ENTRYPOINT), default_timeout=30).run()
    app.text_input(key="security-secret").input("nope").run()
    app.button(key="security-login").click().run()
    assert any("invalid demo credentials" in e.value for e in app.error)
