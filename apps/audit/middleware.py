"""Set the audit actor from the authenticated request user."""

from __future__ import annotations

from apps.audit.context import clear_audit_actor, set_audit_actor


class AuditActorMiddleware:
    """Propagates ``request.user`` into audit context for signal-based logging."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = getattr(request, 'user', None)
        if user is not None and getattr(user, 'is_authenticated', False):
            set_audit_actor(user)
        else:
            clear_audit_actor()
        try:
            return self.get_response(request)
        finally:
            clear_audit_actor()
