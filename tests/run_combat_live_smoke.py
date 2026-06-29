"""Compatibility wrapper for the old live combat smoke runner.

The smoke suite now lives in ``tests.test_combat_live_smoke`` and must be run
through Evennia's test runner so it uses an isolated test database:

    evennia test tests.test_combat_live_smoke

Running combat smoke via ``evennia shell`` against the live game database is no
longer supported.
"""

from __future__ import annotations


def main():
    """Abort old live-shell usage and point callers to the isolated suite."""
    raise RuntimeError(
        "Combat smoke tests were moved to tests.test_combat_live_smoke. "
        "Run `evennia test tests.test_combat_live_smoke` instead of evennia shell."
    )


if __name__ == "__main__":
    main()
