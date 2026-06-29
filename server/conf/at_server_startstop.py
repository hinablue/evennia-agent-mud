"""
Server startstop hooks

This module contains functions called by Evennia at various
points during its startup, reload and shutdown sequence. It
allows for customizing the server operation as desired.

This module must contain at least these global functions:

at_server_init()
at_server_start()
at_server_stop()
at_server_reload_start()
at_server_reload_stop()
at_server_cold_start()
at_server_cold_stop()

"""

from __future__ import annotations

import time
from pathlib import Path

from evennia import logger


_PATCHED = False


def _current_rss_mb() -> float | None:
    """Return current resident memory in MB using /proc, or None if unavailable."""
    status_path = Path("/proc/self/status")
    try:
        for line in status_path.read_text().splitlines():
            if line.startswith("VmRSS:"):
                parts = line.split()
                if len(parts) >= 2:
                    return float(parts[1]) / 1000.0
    except Exception as err:
        logger.log_warn(
            f"Idmapper RSS check skipped; could not read /proc/self/status: {err}"
        )
    return None


def _patch_idmapper_conditional_flush():
    global _PATCHED
    if _PATCHED:
        return

    from evennia.utils.idmapper import models as idmapper_models

    def safe_conditional_flush(max_rmem, force=False):
        """Container-safe variant of Evennia's conditional_flush.

        Evennia upstream shells out to `ps -p <pid> -o rss`, but our container image
        does not ship `ps`. We instead read `/proc/self/status` for VmRSS.
        If current RSS can't be determined, we skip the auto-flush check rather than
        crashing server_maintenance every 5 minutes.
        """
        global _PATCHED

        if not max_rmem:
            return

        now = time.time()
        if not idmapper_models.LAST_FLUSH:
            idmapper_models.LAST_FLUSH = now
            return

        if (
            (now - idmapper_models.LAST_FLUSH) < idmapper_models.AUTO_FLUSH_MIN_INTERVAL
        ) and not force:
            logger.log_warn(
                "Warning: Idmapper flush called more than once in %s min interval. Check memory usage."
                % (idmapper_models.AUTO_FLUSH_MIN_INTERVAL / 60.0)
            )
            return

        rss_mb = _current_rss_mb()
        if rss_mb is None:
            return

        def mem2cachesize(desired_rmem):
            desired_rmem = max(50, desired_rmem)
            return max(1000, int(35.0 * desired_rmem - 250.0))

        ncache_max = mem2cachesize(max_rmem)
        ncache, _ = idmapper_models.cache_size()

        if ncache >= ncache_max and rss_mb > max_rmem * 0.9:
            idmapper_models.flush_cache()
            idmapper_models.LAST_FLUSH = now

    idmapper_models.conditional_flush = safe_conditional_flush

    try:
        import evennia

        service = getattr(evennia, "EVENNIA_SERVER_SERVICE", None)
        if service:
            service._flush_cache = safe_conditional_flush
    except Exception:
        pass

    _PATCHED = True
    logger.log_info("Applied container-safe idmapper conditional_flush patch.")


def at_server_init():
    """
    This is called first as the server is starting up, regardless of how.
    """
    _patch_idmapper_conditional_flush()


def at_server_start():
    """
    This is called every time the server starts up, regardless of
    how it was shut down.
    """
    _patch_idmapper_conditional_flush()


def at_server_stop():
    """
    This is called just before the server is shut down, regardless
    of it is for a reload, reset or shutdown.
    """
    pass


def at_server_reload_start():
    """
    This is called only when server starts back up after a reload.
    """
    pass


def at_server_reload_stop():
    """
    This is called only time the server stops before a reload.
    """
    pass


def at_server_cold_start():
    """
    This is called only when the server starts "cold", i.e. after a
    shutdown or a reset.
    """
    pass


def at_server_cold_stop():
    """
    This is called only when the server goes down due to a shutdown or
    reset.
    """
    pass
