from src.managers.SecurityManager import SecurityManager
from src.core.controller import RealController
from src.core.controller_api import RunConfig


def test_controller_registers_and_authorizes_actions():
    ctrl = RealController()
    sec_mgr = ctrl.engine.get_manager("Security")
    assert sec_mgr is not None

    _, guest_ctx = sec_mgr.login("u_guest", "demo_guest_pass", timestamp=0.0)
    _, admin_ctx = sec_mgr.login("u_admin", "demo_admin_pass", timestamp=0.0)

    # Guest allowed read, denied device/network actions before state changes
    assert ctrl.engine.authorize_action(guest_ctx.context_id, "r", "/system.log") is True
    assert ctrl.engine.authorize_action(guest_ctx.context_id, "device", "DISK_1") is False
    assert ctrl.engine.authorize_action(guest_ctx.context_id, "network", "ETH_0") is False

    # Admin allowed device and network actions
    assert ctrl.engine.authorize_action(admin_ctx.context_id, "device", "DISK_1") is True
    assert ctrl.engine.authorize_action(admin_ctx.context_id, "network", "ETH_0") is True


def test_controller_snapshot_includes_security_metrics():
    ctrl = RealController()
    snap = ctrl.load(RunConfig(scenario_id="baseline"))
    assert "Security" in snap.metrics
    assert snap.metrics["Security"]["total_users"].value == 2.0
    assert snap.metrics["Security"]["alerts_total"].value == 0.0

def test_login_and_logout():
    sm = SecurityManager()
    ok, ctx = sm.login("u_guest", "demo_guest_pass", timestamp=1.0)
    assert ok is True
    assert ctx.user_id == "u_guest"
    assert ctx.context_id in sm.active_contexts

    out_ok, msg = sm.logout(ctx.context_id, timestamp=2.0)
    assert out_ok is True
    assert ctx.context_id not in sm.active_contexts


def test_repeated_failed_logins_trigger_alert():
    sm = SecurityManager()
    sm.login("u_guest", "wrong_pass", timestamp=1.0)
    sm.login("u_guest", "wrong_pass", timestamp=2.0)
    ok, msg = sm.login("u_guest", "wrong_pass", timestamp=3.0)

    assert ok is False
    assert sm.failed_logins == 3
    assert len(sm.alerts) == 1
    assert sm.alerts[0]["rule"] == "REPEATED_FAILED_LOGINS"
    assert sm.alerts[0]["severity"] == "HIGH"


def test_authorize_and_forbidden_access_alert():
    sm = SecurityManager()
    _, guest_ctx = sm.login("u_guest", "demo_guest_pass", timestamp=1.0)

    assert sm.authorize(guest_ctx.context_id, "r", "/docs/readme.txt", timestamp=2.0) is True
    assert sm.authorize(guest_ctx.context_id, "w", "/docs/readme.txt", timestamp=3.0) is False
    assert sm.denied_count == 1
    assert len(sm.alerts) == 1
    assert sm.alerts[0]["rule"] == "FORBIDDEN_RESOURCE_ACCESS"


def test_admin_grant_and_revoke_permissions():
    sm = SecurityManager()
    _, admin_ctx = sm.login("u_admin", "demo_admin_pass", timestamp=1.0)
    _, guest_ctx = sm.login("u_guest", "demo_guest_pass", timestamp=1.0)

    assert sm.authorize(guest_ctx.context_id, "w", "/file.txt", timestamp=2.0) is False

    grant_ok, _ = sm.grant_permission(admin_ctx.context_id, "u_guest", "w", timestamp=3.0)
    assert grant_ok is True
    assert sm.authorize(guest_ctx.context_id, "w", "/file.txt", timestamp=4.0) is True

    revoke_ok, _ = sm.revoke_permission(admin_ctx.context_id, "u_guest", "w", timestamp=5.0)
    assert revoke_ok is True
    assert sm.authorize(guest_ctx.context_id, "w", "/file.txt", timestamp=6.0) is False
    assert sm.policy_changes == 2


def test_non_admin_cannot_grant_permissions():
    sm = SecurityManager()
    _, guest_ctx = sm.login("u_guest", "demo_guest_pass", timestamp=1.0)

    ok, msg = sm.grant_permission(guest_ctx.context_id, "u_guest", "admin", timestamp=2.0)
    assert ok is False
    assert "administrator role required" in msg.lower()
    assert len(sm.alerts) == 1
    assert sm.alerts[0]["rule"] == "UNAUTHORIZED_POLICY_CHANGE"


def test_rwx_permissions_and_metrics():
    sm = SecurityManager()
    sm.create_user("u_student", "student", role="USER", permissions=["r", "w"], demo_secret="demo_student_pass", timestamp=1.0)
    _, user_ctx = sm.login("u_student", "demo_student_pass", timestamp=2.0)

    allowed, _ = sm.check_rwx(user_ctx.context_id, "w", owner_id="u_student", permissions_str="rwx------", timestamp=3.0)
    denied, _ = sm.check_rwx(user_ctx.context_id, "r", owner_id="u_admin", permissions_str="rwx------", timestamp=4.0)

    assert allowed is True
    assert denied is False

    m = sm.metrics()
    assert m["successful_logins"] == 1
    assert m["allowed_accesses"] == 1
    assert m["denied_accesses"] == 1
    assert m["alerts_total"] == 1
    assert m["alerts_medium"] == 1