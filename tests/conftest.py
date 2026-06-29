from __future__ import annotations

import uuid

import pytest


_SHARED_LIVE_SMOKE_KEYS = (
    "alpha",
    "beta",
    "gamma",
    "smoke_alpha",
    "smoke_beta",
)


def _cancel_session_timers(manager) -> None:
    """Best-effort cancellation of pending combat timers."""
    sessions = getattr(manager, "sessions", {}) or {}
    for session in list(sessions.values()):
        try:
            session._cancel_turn_timer()
        except Exception:
            pass


def _reset_combat_manager() -> None:
    """Clear the global combat singleton between tests."""
    try:
        from world.combat_manager import manager
    except Exception:
        return

    _cancel_session_timers(manager)
    try:
        manager.sessions.clear()
    except Exception:
        pass


def _delete_shared_objects() -> None:
    """Delete commonly re-used live-smoke objects, if Evennia ORM is available."""
    try:
        from evennia.objects.models import ObjectDB
    except Exception:
        return

    for key in _SHARED_LIVE_SMOKE_KEYS:
        try:
            matches = ObjectDB.objects.filter(db_key__iexact=key)
        except Exception:
            continue

        for obj in list(matches):
            try:
                if hasattr(obj, "scripts"):
                    obj.scripts.stop()
            except Exception:
                pass
            try:
                obj.delete()
            except Exception:
                pass


@pytest.fixture(autouse=True)
def isolate_combat_state():
    """Reset shared combat state before and after every test."""
    _reset_combat_manager()
    _delete_shared_objects()
    yield
    _delete_shared_objects()
    _reset_combat_manager()


@pytest.fixture
def live_smoke_namespace(monkeypatch):
    """Optional namespace for smoke helpers that want unique object keys."""
    namespace = f"smoke-{uuid.uuid4().hex[:8]}"
    monkeypatch.setenv("LIVE_SMOKE_NAMESPACE", namespace)
    return namespace
