import hashlib
from typing import Dict, List, Any, Optional, Tuple
from src.core.base_manager import BaseManager
from src.core.events import EventRecord
from src.core.models import User, SecurityContext


class SecurityManager(BaseManager):
    """
    Manages users, authentication, active security contexts (sessions), RBAC permissions,
    authorization queries, and append-only audit logging.
    """

    def __init__(self):
        super().__init__("Security")
        self.users: Dict[str, User] = {
            "u_admin": User(user_id="u_admin", username="admin", role="ADMIN", permissions=["r", "w", "x", "admin"]),
            "u_guest": User(user_id="u_guest", username="guest", role="GUEST", permissions=["r"])
        }
        self.demo_credentials: Dict[str, str] = {
            "u_admin": self._hash_demo_secret("demo_admin_pass"),
            "u_guest": self._hash_demo_secret("demo_guest_pass"),
        }
        self.active_contexts: Dict[str, SecurityContext] = {}
        self.audit_log: List[Dict[str, Any]] = []
        self.alerts: List[Dict[str, Any]] = []
        self.pending_events: List[EventRecord] = []

        self.denied_count: int = 0
        self.allowed_count: int = 0
        self.successful_logins: int = 0
        self.failed_logins: int = 0
        self.failed_login_streak: Dict[str, int] = {}
        self.policy_changes: int = 0
        self.failed_login_threshold: int = 3

    def _hash_demo_secret(self, demo_secret: str) -> str:
        return hashlib.sha256(demo_secret.encode("utf-8")).hexdigest()

    def configure(self, config: Dict[str, Any]) -> None:
        if "failed_login_threshold" in config:
            self.failed_login_threshold = int(config["failed_login_threshold"])
        self.is_configured = True

    def load(self, input_data: List[User]) -> None:
        for user in input_data:
            self.users[user.user_id] = user
            if user.user_id not in self.demo_credentials:
                self.demo_credentials[user.user_id] = self._hash_demo_secret("demo_default_pass")

    def reset(self) -> None:
        self.active_contexts.clear()
        self.audit_log.clear()
        self.alerts.clear()
        self.pending_events.clear()
        self.denied_count = 0
        self.allowed_count = 0
        self.successful_logins = 0
        self.failed_logins = 0
        self.failed_login_streak.clear()
        self.policy_changes = 0

    def create_user(
        self,
        user_id: str,
        username: str,
        role: str = "USER",
        permissions: Optional[List[str]] = None,
        demo_secret: str = "demo_pass",
        timestamp: float = 0.0,
    ) -> Tuple[bool, str]:
        if user_id in self.users:
            return False, f"User '{user_id}' already exists"

        perms = permissions if permissions is not None else ["r"]
        self.users[user_id] = User(
            user_id=user_id,
            username=username,
            role=role.upper(),
            permissions=perms,
        )
        self.demo_credentials[user_id] = self._hash_demo_secret(demo_secret)
        self.policy_changes += 1
        self._log_audit(timestamp, user_id, "USER_CREATED", "ALLOWED", f"Created user '{username}' ({role.upper()})")
        return True, f"User '{username}' created"

    def login(self, user_id: str, demo_secret: str, timestamp: float = 0.0) -> Tuple[bool, Any]:
        user = self.users.get(user_id)
        if not user:
            self.failed_logins += 1
            self._record_failed_login(user_id, timestamp, "Invalid user ID")
            return False, "Authentication failed: unknown user"

        expected_hash = self.demo_credentials.get(user_id)
        if expected_hash != self._hash_demo_secret(demo_secret):
            self.failed_logins += 1
            self._record_failed_login(user_id, timestamp, "Invalid demo credentials")
            return False, "Authentication failed: invalid demo credentials"

        self.failed_login_streak[user_id] = 0
        self.successful_logins += 1

        ctx = SecurityContext(
            context_id=f"ctx_{user_id}_{int(timestamp)}",
            user_id=user_id,
            token=f"tok_{user_id}_secret",
            effective_permissions=user.permissions.copy()
        )
        self.active_contexts[ctx.context_id] = ctx
        self._log_audit(timestamp, user_id, "LOGIN", "ALLOWED", f"Session started: {ctx.context_id}")
        self._emit_event(timestamp, "LOGIN_SUCCESS", user_id, "LOGIN", "ALLOWED", f"Session started: {ctx.context_id}", "LOGGED_OUT", "ACTIVE")
        return True, ctx

    def authenticate(self, user_id: str, timestamp: float) -> Optional[SecurityContext]:
        """Creates an active security context for a registered user."""
        user = self.users.get(user_id)
        if not user:
            self.failed_logins += 1
            self._record_failed_login(user_id, timestamp, "Invalid user ID")
            return None

        self.failed_login_streak[user_id] = 0
        self.successful_logins += 1

        ctx = SecurityContext(
            context_id=f"ctx_{user_id}_{int(timestamp)}",
            user_id=user_id,
            token=f"tok_{user_id}_secret",
            effective_permissions=user.permissions.copy()
        )
        self.active_contexts[ctx.context_id] = ctx
        self._log_audit(timestamp, user_id, "LOGIN", "ALLOWED", f"Session started: {ctx.context_id}")
        self._emit_event(timestamp, "LOGIN_SUCCESS", user_id, "LOGIN", "ALLOWED", f"Session started: {ctx.context_id}", "LOGGED_OUT", "ACTIVE")
        return ctx

    def logout(self, context_id: str, timestamp: float = 0.0) -> Tuple[bool, str]:
        ctx = self.active_contexts.pop(context_id, None)
        if not ctx:
            return False, f"Session '{context_id}' not found"

        self._log_audit(timestamp, ctx.user_id, "LOGOUT", "ALLOWED", f"Session ended: {context_id}")
        self._emit_event(timestamp, "LOGOUT", ctx.user_id, "LOGOUT", "ALLOWED", f"Session ended: {context_id}", "ACTIVE", "LOGGED_OUT")
        return True, f"Logged out session '{context_id}'"

    def check_rwx(
        self,
        context_id: str,
        action: str,
        owner_id: str,
        permissions_str: str = "rwxr-x---",
        group_ids: Optional[List[str]] = None,
        resource_id: str = "resource",
        timestamp: float = 0.0,
    ) -> Tuple[bool, str]:
        ctx = self.active_contexts.get(context_id)
        if not ctx:
            self.denied_count += 1
            self._log_audit(timestamp, "UNKNOWN", "RWX_CHECK", "DENIED", f"Invalid session for {resource_id}")
            return False, "Access denied: invalid session"

        if "admin" in ctx.effective_permissions:
            self.allowed_count += 1
            self._log_audit(timestamp, ctx.user_id, "RWX_CHECK", "ALLOWED", f"Admin override '{action}' on {resource_id}")
            return True, "Allowed (admin privilege)"

        clean_perms = permissions_str.replace(" ", "")
        if len(clean_perms) != 9:
            self.denied_count += 1
            return False, "Invalid permission string format"

        if ctx.user_id == owner_id:
            triplet = clean_perms[0:3]
        elif group_ids and ctx.user_id in group_ids:
            triplet = clean_perms[3:6]
        else:
            triplet = clean_perms[6:9]

        if action in triplet and action in ctx.effective_permissions:
            self.allowed_count += 1
            self._log_audit(timestamp, ctx.user_id, "RWX_CHECK", "ALLOWED", f"Granted '{action}' on {resource_id}")
            return True, f"Access granted for '{action}' on {resource_id}"

        self.denied_count += 1
        self._log_audit(timestamp, ctx.user_id, "RWX_CHECK", "DENIED", f"Forbidden '{action}' on {resource_id}")
        self._trigger_alert(
            timestamp,
            "FORBIDDEN_ACCESS",
            "MEDIUM",
            ctx.user_id,
            f"User '{ctx.user_id}' attempted unauthorized '{action}' on '{resource_id}'",
        )
        return False, f"Access denied: missing '{action}' permission on {resource_id}"

    def authorize(self, context_id: str, required_perm: str, resource_id: str, timestamp: float) -> bool:
        """Verifies if an active context possesses the necessary access permissions."""
        ctx = self.active_contexts.get(context_id)
        if not ctx or ("admin" not in ctx.effective_permissions and required_perm not in ctx.effective_permissions):
            self.denied_count += 1
            actor = ctx.user_id if ctx else "UNKNOWN"
            self._log_audit(timestamp, actor, "ACCESS_REQUEST", "DENIED",
                            f"Missing '{required_perm}' for {resource_id}")
            self._emit_event(timestamp, "ACCESS_DENIED", ctx.user_id, "ACCESS_REQUEST", "DENIED", f"Missing '{required_perm}' for {resource_id}")
            severity = "HIGH" if required_perm in ("admin", "network") else "MEDIUM"
            self._trigger_alert(
                timestamp,
                "FORBIDDEN_RESOURCE_ACCESS",
                severity,
                actor,
                f"Denied '{required_perm}' access to '{resource_id}' for '{actor}'",
            )
            return False

        self.allowed_count += 1
        self._log_audit(timestamp, ctx.user_id, "ACCESS_REQUEST", "ALLOWED",
                        f"Granted '{required_perm}' for {resource_id}")
        return True

    def grant_permission(
        self, admin_context_id: str, target_user_id: str, permission: str, timestamp: float = 0.0
    ) -> Tuple[bool, str]:
        admin_ctx = self.active_contexts.get(admin_context_id)
        if not admin_ctx or "admin" not in admin_ctx.effective_permissions:
            self.denied_count += 1
            actor = admin_ctx.user_id if admin_ctx else "UNKNOWN"
            self._log_audit(timestamp, actor, "GRANT_PERM", "DENIED", f"Unauthorized grant attempt on {target_user_id}")
            self._trigger_alert(
                timestamp,
                "UNAUTHORIZED_POLICY_CHANGE",
                "HIGH",
                actor,
                f"Non-admin '{actor}' tried to grant '{permission}' to '{target_user_id}'",
            )
            return False, "Permission denied: administrator role required"

        target_user = self.users.get(target_user_id)
        if not target_user:
            return False, f"Target user '{target_user_id}' not found"

        if permission not in target_user.permissions:
            target_user.permissions.append(permission)

        for ctx in self.active_contexts.values():
            if ctx.user_id == target_user_id and permission not in ctx.effective_permissions:
                ctx.effective_permissions.append(permission)

        self.policy_changes += 1
        self._log_audit(timestamp, admin_ctx.user_id, "GRANT_PERM", "ALLOWED", f"Granted '{permission}' to {target_user_id}")
        self._emit_event(timestamp, "POLICY_CHANGED", admin_ctx.user_id, "GRANT_PERM", "ALLOWED", f"Granted '{permission}' to {target_user_id}")
        return True, f"Granted '{permission}' to '{target_user_id}'"

    def revoke_permission(
        self, admin_context_id: str, target_user_id: str, permission: str, timestamp: float = 0.0
    ) -> Tuple[bool, str]:
        admin_ctx = self.active_contexts.get(admin_context_id)
        if not admin_ctx or "admin" not in admin_ctx.effective_permissions:
            self.denied_count += 1
            actor = admin_ctx.user_id if admin_ctx else "UNKNOWN"
            self._log_audit(timestamp, actor, "REVOKE_PERM", "DENIED", f"Unauthorized revoke attempt on {target_user_id}")
            self._trigger_alert(
                timestamp,
                "UNAUTHORIZED_POLICY_CHANGE",
                "HIGH",
                actor,
                f"Non-admin '{actor}' tried to revoke '{permission}' from '{target_user_id}'",
            )
            return False, "Permission denied: administrator role required"

        target_user = self.users.get(target_user_id)
        if not target_user:
            return False, f"Target user '{target_user_id}' not found"

        if permission in target_user.permissions:
            target_user.permissions.remove(permission)

        for ctx in self.active_contexts.values():
            if ctx.user_id == target_user_id and permission in ctx.effective_permissions:
                ctx.effective_permissions.remove(permission)

        self.policy_changes += 1
        self._log_audit(timestamp, admin_ctx.user_id, "REVOKE_PERM", "ALLOWED", f"Revoked '{permission}' from {target_user_id}")
        self._emit_event(timestamp, "POLICY_CHANGED", admin_ctx.user_id, "REVOKE_PERM", "ALLOWED", f"Revoked '{permission}' from {target_user_id}")
        return True, f"Revoked '{permission}' from '{target_user_id}'"

    def _record_failed_login(self, user_id: str, timestamp: float, reason: str) -> None:
        self._log_audit(timestamp, user_id, "AUTH_FAIL", "DENIED", reason)
        self._emit_event(timestamp, "LOGIN_FAILED", user_id, "AUTH_FAIL", "DENIED", reason)

        streak = self.failed_login_streak.get(user_id, 0) + 1
        self.failed_login_streak[user_id] = streak

        if streak >= self.failed_login_threshold:
            self._trigger_alert(
                timestamp,
                "REPEATED_FAILED_LOGINS",
                "HIGH",
                user_id,
                f"{streak} consecutive failed login attempts for '{user_id}'",
            )

    def _trigger_alert(self, timestamp: float, rule: str, severity: str, user_id: str, details: str) -> None:
        alert = {
            "alert_id": f"alert_{len(self.alerts) + 1}",
            "timestamp": timestamp,
            "rule": rule,
            "severity": severity.upper(),
            "user_id": user_id,
            "details": details,
        }
        self.alerts.append(alert)
        self._log_audit(timestamp, user_id, f"ALERT:{rule}", severity.upper(), details)
        self._emit_event(timestamp, "SECURITY_ALERT", user_id, f"ALERT:{rule}", severity.upper(), details)

    def _log_audit(self, timestamp: float, user_id: str, action: str, outcome: str, msg: str):
        self.audit_log.append({
            "timestamp": timestamp,
            "user_id": user_id,
            "action": action,
            "outcome": outcome,
            "message": msg
        })

    def _emit_event(
        self,
        timestamp: float,
        event_type: str,
        entity_id: str,
        action: str,
        outcome: str,
        message: str,
        previous_state: str = "",
        new_state: str = "",
    ) -> None:
        self.pending_events.append(
            EventRecord(
                timestamp=timestamp,
                manager="Security",
                event_type=event_type,
                entity_id=entity_id,
                action=action,
                previous_state=previous_state,
                new_state=new_state,
                outcome=outcome,
                explanatory_message=message,
            )
        )

    def filter_audit_log(
        self, user_id: Optional[str] = None, outcome: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        results = self.audit_log
        if user_id:
            results = [e for e in results if e["user_id"] == user_id]
        if outcome:
            results = [e for e in results if e["outcome"] == outcome.upper()]
        return list(results)

    def step(self, current_time: float) -> List[EventRecord]:
        events = self.pending_events.copy()
        self.pending_events.clear()
        return events

    def run(self, stop_condition: Any = None) -> List[EventRecord]:
        return []

    def snapshot(self) -> Dict[str, Any]:
        """UI Snapshot for security tables, active sessions, and permission matrices."""
        return {
            "active_sessions": [
                {"ctx_id": c.context_id, "user_id": c.user_id, "perms": c.effective_permissions}
                for c in self.active_contexts.values()
            ],
            "permission_matrix": {
                u.username: {"role": u.role, "permissions": u.permissions}
                for u in self.users.values()
            },
            "alerts": list(self.alerts),
            "recent_audit_log": self.audit_log[-10:]
        }

    def metrics(self) -> Dict[str, Any]:
        """UI metrics format for security pie charts and warning banners."""
        severity_counts = {"LOW": 0, "MEDIUM": 0, "HIGH": 0}
        for alert in self.alerts:
            sev = alert.get("severity", "LOW")
            severity_counts[sev] = severity_counts.get(sev, 0) + 1

        return {
            "total_users": len(self.users),
            "active_sessions": len(self.active_contexts),
            "successful_logins": self.successful_logins,
            "failed_logins": self.failed_logins,
            "allowed_accesses": self.allowed_count,
            "denied_accesses": self.denied_count,
            "policy_changes": self.policy_changes,
            "alerts_total": len(self.alerts),
            "alerts_low": severity_counts["LOW"],
            "alerts_medium": severity_counts["MEDIUM"],
            "alerts_high": severity_counts["HIGH"],
            "audit_entries": len(self.audit_log)
        }

    def validate(self) -> List[str]:
        return []

    def export(self, export_format: str = "json") -> Any:
        return {
            "metrics": self.metrics(),
            "users": [u.__dict__ for u in self.users.values()],
            "alerts": self.alerts,
            "audit_log": self.audit_log
        }