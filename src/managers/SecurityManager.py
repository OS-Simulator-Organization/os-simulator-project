from typing import Dict, List, Any, Optional
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
        self.active_contexts: Dict[str, SecurityContext] = {}
        self.audit_log: List[Dict[str, Any]] = []
        self.denied_count: int = 0
        self.allowed_count: int = 0

    def configure(self, config: Dict[str, Any]) -> None:
        self.is_configured = True

    def load(self, input_data: List[User]) -> None:
        for user in input_data:
            self.users[user.user_id] = user

    def reset(self) -> None:
        self.active_contexts.clear()
        self.audit_log.clear()
        self.denied_count = 0
        self.allowed_count = 0

    def authenticate(self, user_id: str, timestamp: float) -> Optional[SecurityContext]:
        """Creates an active security context for a registered user."""
        user = self.users.get(user_id)
        if not user:
            self._log_audit(timestamp, user_id, "AUTH_FAIL", "DENIED", "Invalid user ID")
            return None

        ctx = SecurityContext(
            context_id=f"ctx_{user_id}_{int(timestamp)}",
            user_id=user_id,
            token=f"tok_{user_id}_secret",
            effective_permissions=user.permissions.copy()
        )
        self.active_contexts[ctx.context_id] = ctx
        self._log_audit(timestamp, user_id, "LOGIN", "ALLOWED", f"Session started: {ctx.context_id}")
        return ctx

    def authorize(self, context_id: str, required_perm: str, resource_id: str, timestamp: float) -> bool:
        """Verifies if an active context possesses the necessary access permissions."""
        ctx = self.active_contexts.get(context_id)
        if not ctx or required_perm not in ctx.effective_permissions:
            self.denied_count += 1
            self._log_audit(timestamp, ctx.user_id if ctx else "UNKNOWN", "ACCESS_REQUEST", "DENIED", 
                            f"Missing '{required_perm}' for {resource_id}")
            return False

        self.allowed_count += 1
        self._log_audit(timestamp, ctx.user_id, "ACCESS_REQUEST", "ALLOWED", 
                        f"Granted '{required_perm}' for {resource_id}")
        return True

    def _log_audit(self, timestamp: float, user_id: str, action: str, outcome: str, msg: str):
        self.audit_log.append({
            "timestamp": timestamp,
            "user_id": user_id,
            "action": action,
            "outcome": outcome,
            "message": msg
        })

    def step(self, current_time: float) -> List[EventRecord]:
        # Emits newly generated security events from audit log if necessary
        return []

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
            "recent_audit_log": self.audit_log[-10:]
        }

    def metrics(self) -> Dict[str, Any]:
        """UI metrics format for security pie charts and warning banners."""
        return {
            "total_users": len(self.users),
            "active_sessions": len(self.active_contexts),
            "allowed_accesses": self.allowed_count,
            "denied_accesses": self.denied_count,
            "audit_entries": len(self.audit_log)
        }

    def validate(self) -> List[str]:
        return []

    def export(self, export_format: str = "json") -> Any:
        return {
            "metrics": self.metrics(),
            "users": [u.__dict__ for u in self.users.values()],
            "audit_log": self.audit_log
        }