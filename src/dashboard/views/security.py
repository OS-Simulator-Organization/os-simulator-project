"""Security tab (spec 4.4 and 5.1): session selection with demo credentials,
authorization checks, admin grant/revoke, and the required security imagery:
permission matrix, severity distribution, audit-event timeline and a
filterable audit log.

The Security manager isn't registered with the controller yet, so this tab uses
the controller's one if it exists and otherwise keeps its own for the session.
Security events from each action are added to the shared event log.
"""

from typing import Any, Dict, List

import altair as alt
import pandas as pd
import streamlit as st

from src.core.controller_api import Snapshot
from src.dashboard.manager_view import ManagerView
from src.managers.SecurityManager import SecurityManager

MANAGER = "security-manager"
SESSION = "security-session"
PERMISSIONS = ["r", "w", "x", "admin", "network"]
# Demonstration-only credentials built into the Security manager (not real passwords).
DEMO_SECRETS = {"u_admin": "demo_admin_pass", "u_guest": "demo_guest_pass"}
SEVERITY_ORDER = ["LOW", "MEDIUM", "HIGH"]
SEVERITY_COLORS = ["#eda100", "#eb6834", "#d03b3b"]
OUTCOME_COLORS = {"ALLOWED": "#1baf7a", "DENIED": "#d03b3b", "LOW": "#eda100", "MEDIUM": "#eb6834", "HIGH": "#d03b3b"}


def get_security_manager() -> SecurityManager:
    controller = st.session_state.get("controller")
    registered = controller.engine.get_manager("Security") if controller and hasattr(controller, "engine") else None
    if registered:
        return registered
    if MANAGER not in st.session_state:
        st.session_state[MANAGER] = SecurityManager()
    return st.session_state[MANAGER]


def permission_matrix(manager: SecurityManager) -> List[Dict[str, str]]:
    """One row per user, one column per permission, marked with words so it doesn't rely on color."""
    return [
        {"user": user.user_id, "role": user.role,
         **{perm: "✓ yes" if perm in user.permissions or "admin" in user.permissions else "✗ no" for perm in PERMISSIONS}}
        for user in manager.users.values()
    ]


def severity_counts(manager: SecurityManager) -> List[Dict[str, Any]]:
    counts = {level: 0 for level in SEVERITY_ORDER}
    for alert in manager.alerts:
        counts[alert["severity"]] = counts.get(alert["severity"], 0) + 1
    return [{"severity": level, "alerts": count} for level, count in counts.items()]


def audit_rows(manager: SecurityManager) -> List[Dict[str, Any]]:
    return [{"entry": number, **entry} for number, entry in enumerate(manager.audit_log, start=1)]


def severity_chart(counts: List[Dict[str, Any]]) -> alt.Chart:
    return alt.Chart(pd.DataFrame(counts)).mark_bar().encode(
        x=alt.X("severity:N", title="Severity", sort=SEVERITY_ORDER),
        y=alt.Y("alerts:Q", title="Alerts (count)", axis=alt.Axis(tickMinStep=1)),
        color=alt.Color("severity:N", title="Severity",
                        scale=alt.Scale(domain=SEVERITY_ORDER, range=SEVERITY_COLORS)),
        tooltip=["severity", "alerts"],
    ).properties(title="Security alerts by severity", height=220)


def audit_timeline_chart(rows: List[Dict[str, Any]]) -> alt.Chart:
    outcomes = list(dict.fromkeys(r["outcome"] for r in rows))
    return alt.Chart(pd.DataFrame(rows)).mark_point(size=90, filled=True).encode(
        x=alt.X("entry:Q", title="Audit entry (in order)", axis=alt.Axis(tickMinStep=1)),
        y=alt.Y("action:N", title="Action"),
        color=alt.Color("outcome:N", title="Outcome",
                        scale=alt.Scale(domain=outcomes, range=[OUTCOME_COLORS.get(o, "#888780") for o in outcomes])),
        shape=alt.Shape("outcome:N", title="Outcome"),
        tooltip=["entry", "timestamp", "user_id", "action", "outcome", "message"],
    ).properties(title="Audit events over time", height=240)


def _record(manager: SecurityManager, tick: int) -> None:
    """Moves the manager's new security events into the shared event log."""
    st.session_state.events = [*st.session_state.get("events", []), *manager.step(tick)]


def render_session_controls(manager: SecurityManager, tick: int) -> None:
    st.markdown("**Session**")
    st.caption("Demonstration credentials only, not real passwords: "
               + ", ".join(f"{user} / {secret}" for user, secret in DEMO_SECRETS.items()))
    session = st.session_state.get(SESSION)
    if session and session in manager.active_contexts:
        user = manager.active_contexts[session].user_id
        st.markdown(f":material/person: Logged in as **{user}**")
        if st.button("Log out", key="security-logout"):
            manager.logout(session, timestamp=tick)
            st.session_state.pop(SESSION, None)
            _record(manager, tick)
            st.rerun()
        return

    user_col, secret_col = st.columns(2)
    user = user_col.selectbox("User", list(manager.users), key="security-user")
    secret = secret_col.text_input("Demo credential", type="password", key="security-secret")
    if st.button("Log in", key="security-login"):
        ok, result = manager.login(user, secret, timestamp=tick)
        _record(manager, tick)
        if ok:
            st.session_state[SESSION] = result.context_id
            st.rerun()
        st.error(result)


def render_actions(manager: SecurityManager, tick: int) -> None:
    session = st.session_state.get(SESSION)
    if not session or session not in manager.active_contexts:
        st.caption("Log in to try authorization checks and permission changes.")
        return

    st.markdown("**Authorization check**")
    resource_col, perm_col = st.columns(2)
    resource = resource_col.text_input("Resource", value="/docs/notes.txt", key="security-resource")
    permission = perm_col.selectbox("Permission needed", PERMISSIONS, key="security-permission")
    if st.button("Check access", key="security-check"):
        allowed = manager.authorize(session, permission, resource, timestamp=tick)
        _record(manager, tick)
        if allowed:
            st.success(f"Allowed: '{permission}' on {resource}")
        else:
            st.error(f"Denied: '{permission}' on {resource}")

    st.markdown("**Grant or revoke a permission** (administrator only)")
    target_col, grant_perm_col = st.columns(2)
    target = target_col.selectbox("User", list(manager.users), key="security-target")
    grant_perm = grant_perm_col.selectbox("Permission", PERMISSIONS, key="security-grant-perm")
    grant_col, revoke_col = st.columns(2)
    for column, label, change in ((grant_col, "Grant", manager.grant_permission),
                                  (revoke_col, "Revoke", manager.revoke_permission)):
        if column.button(label, key=f"security-{label.lower()}"):
            ok, message = change(session, target, grant_perm, timestamp=tick)
            _record(manager, tick)
            if ok:
                st.success(message)
            else:
                st.error(message)


def render_security_content(snapshot: Snapshot) -> None:
    manager = get_security_manager()
    tick = snapshot.tick
    metrics = manager.metrics()

    counts = st.columns(4)
    counts[0].metric("Successful logins", metrics["successful_logins"])
    counts[1].metric("Failed logins", metrics["failed_logins"])
    counts[2].metric("Allowed / denied", f"{metrics['allowed_accesses']} / {metrics['denied_accesses']}")
    counts[3].metric("Alerts", metrics["alerts_total"])

    with st.container(border=True):
        render_session_controls(manager, tick)
        render_actions(manager, tick)

    with st.container(border=True):
        st.markdown("**Permission matrix**")
        st.dataframe(permission_matrix(manager), hide_index=True)
        st.caption("Administrators have every permission.")

    with st.container(border=True):
        st.markdown("**Severity distribution**")
        severity = severity_counts(manager)
        st.altair_chart(severity_chart(severity), width="stretch")
        with st.expander("Data table: alerts by severity"):
            st.dataframe(severity, hide_index=True)

    with st.container(border=True):
        st.markdown("**Audit-event timeline**")
        rows = audit_rows(manager)
        if not rows:
            st.caption("No audit entries yet. Log in to start.")
            return
        st.altair_chart(audit_timeline_chart(rows), width="stretch")
        st.markdown("##### Audit log")
        user_col, outcome_col = st.columns(2)
        user_filter = user_col.selectbox("Filter by user", ["All", *sorted({r["user_id"] for r in rows})],
                                         key="security-audit-user")
        outcome_filter = outcome_col.selectbox("Filter by outcome", ["All", *sorted({r["outcome"] for r in rows})],
                                               key="security-audit-outcome")
        filtered = manager.filter_audit_log(user_id=None if user_filter == "All" else user_filter,
                                            outcome=None if outcome_filter == "All" else outcome_filter)
        st.dataframe(filtered, hide_index=True)


VIEW = ManagerView(
    name="Security",
    manager="Security",
    render_content=render_security_content,
    test_files=("tests/test_security_manager.py",),
)
