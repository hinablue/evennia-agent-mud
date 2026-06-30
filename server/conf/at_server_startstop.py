"""伺服器啟動停止鉤子

此模組包含 Evennia 在各種場合呼叫的函數
其啟動、重新載入和關閉序列期間的點。它
允許根據需要自訂伺服器操作。

此模組必須至少包含以下全域函數：

at_server_init()
at_server_start()
at_server_stop()
at_server_reload_start()
at_server_reload_stop()
at_server_cold_start()
at_server_cold_stop()"""

from __future__ import annotations

import time
from pathlib import Path

from evennia import logger


_PATCHED = False


def _current_rss_mb() -> float | None:
    """使用 /proc 傳回目前駐留記憶體（以 MB 為單位），如果不可用則傳回 None。"""
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
        """Evennia 的 conditional_flush 的容器安全變體。

        Evennia 上游向 `ps -p <pid> -o rss` 發動攻擊，但我們的容器鏡像
        不運送 `ps`。我們改為讀取 VmRSS 的 `/proc/self/status`。
        如果無法確定目前的 RSS，我們會跳過自動刷新檢查，而不是
        每 5 分鐘伺服器維護就會崩潰一次。"""
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
    """無論如何啟動，這都會在伺服器啟動時首先被呼叫。"""
    _patch_idmapper_conditional_flush()


def at_server_start():
    """每次伺服器啟動時都會呼叫此函數，無論
    它是如何被關閉的。"""
    _patch_idmapper_conditional_flush()


def at_server_stop():
    """無論如何，這都會在伺服器關閉之前調用
    其中用於重新載入、重置或關閉。"""
    pass


def at_server_reload_start():
    """僅當伺服器在重新載入後重新啟動時才會呼叫此函數。"""
    pass


def at_server_reload_stop():
    """僅當伺服器在重新載入之前停止時才會呼叫此函數。"""
    pass


def at_server_cold_start():
    """僅當伺服器「冷」啟動時（即經過一段時間後）才會呼叫此方法
    關機或重置。"""
    pass


def at_server_cold_stop():
    """僅當伺服器因關閉或關閉而關閉時才會呼叫此函數
    重置。"""
    pass
