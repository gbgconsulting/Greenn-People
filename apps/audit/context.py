"""Context for attributing audit log rows to the acting user."""

from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar
from typing import TYPE_CHECKING, Iterator

if TYPE_CHECKING:
    from apps.accounts.models import CustomUser

_audit_actor: ContextVar[CustomUser | None] = ContextVar('audit_actor', default=None)


def get_audit_actor() -> CustomUser | None:
    """Return the current request/service actor, if any (nullable for Celery)."""
    return _audit_actor.get()


def set_audit_actor(user: CustomUser | None) -> None:
    _audit_actor.set(user)


def clear_audit_actor() -> None:
    _audit_actor.set(None)


@contextmanager
def audit_actor(user: CustomUser | None) -> Iterator[None]:
    """Temporarily set the audit actor (e.g. stage transitions outside a request)."""
    token = _audit_actor.set(user)
    try:
        yield
    finally:
        _audit_actor.reset(token)
