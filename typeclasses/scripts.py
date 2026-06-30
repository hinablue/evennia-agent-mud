"""腳本

腳本是強大的萬事通。他們沒有遊戲內
存在並且可以用來表示某些持久性博弈系統
情況。腳本還可以有一個時間組件，允許它們
定期或有限次數地「開火」。

通常不存在相互繼承的腳本“樹”。
相反，每個腳本都傾向於從 Script 基底類別繼承，並且
只是重載它的鉤子讓它執行它的功能。"""

from evennia.scripts.scripts import DefaultScript


class Script(DefaultScript):
    """這是所有腳本的基本類型類別。腳本描述
    遊戲世界中沒有物理存在的所有實體/系統
    需要資料庫儲存（如經濟系統或
    戰鬥追蹤器）。他們
    還可以有計時器/自動收報機組件。

    腳本類型是透過重新定義其部分或全部鉤子來自訂的
    方法和變數。

    * 可用屬性（查看文件以取得完整列表，這可能是
      已過時）。

     key（字串）- 物件名稱
     名稱（字串）- 與鍵相同
     別名（字串列表）- 物件的別名。將會被拯救
              作為 AliasDB 條目發送到資料庫，但作為字串傳回。
     dbref（int，唯讀）- 唯一的#id 號。也可以使用“id”。
     date_created (string) - 物件建立的時間戳
     權限（字串列表）- 權限字串列表

     desc (字串) - 腳本的可選描述，顯示在清單中
     obj (Object) - 此腳本連接到的可選對象
                          並作用於（由 obj.scripts.add() 自動設定）
     Interval (int) - 腳本運行的頻率（以秒為單位）。 <0 turns
                          off ticker
     start_delay (bool) - if the script should start repeating right away or
                          wait self.interval seconds
     repeats (int)      - how many times the script should repeat before
                          stopping. 0 means infinite repeats
     persistent (bool)  - if script should survive a server shutdown or not
     is_active (bool)   - if script is currently running

    * Handlers

     locks - lock-handler: use locks.add() to add new lock strings
     db - attribute-handler: store/retrieve database attributes on this
                        self.db.myattr=val, val=self.db.myattr
     ndb - non-persistent attribute handler: same as db but does not
                        create a database entry when storing data

    * Helper methods

     create(key, **kwargs)
     start() - start script (this usually happens automatically at creation
               and at obj.script.add() etc)
     stop()  - stop script, and delete it
     pause() - put the script on hold, until unpause() is called. If script
               is persistent, the pause state will survive a shutdown.
     unpause() - restart a previously paused script. The script will continue
                 from the paused timer (but at_start() will be called).
     time_until_next_repeat() - if a timed script (interval>0)，返回時間
                 直到下一個刻度

    * Hook 方法（也應該包含 self 作為第一個參數）：

     at_script_creation() - 只呼叫一次，當 this 的對象
                            類別首先被創建。
     is_valid() - 呼叫以檢查腳本是否有效執行
                  目前。如果 is_valid() 傳回 False，則執行
                  腳本被停止並從遊戲中刪除。你可以用這個
                  檢查狀態變化（即追蹤某些戰鬥的腳本
                  定期統計數據僅在存在時才有效
                  實戰正在進行中）。
      at_start() - 每次啟動腳本時調用，這用於持久
                  腳本至少在每個伺服器啟動一次。請注意，這是
                  不受 self.delay_start 影響，只延遲第一個
                  呼叫 at_repeat()。
      at_repeat() - 每 self.interval 秒呼叫一次。它將被稱為
                  啟動後立即啟動，除非 self.delay_start 為 True，即
                  將延遲此方法的第一次呼叫 self.interval
                  秒。如果 self.interval==0，這個方法永遠不會
                  被召喚。
      at_pause()
      at_stop() - 在腳本物件停止並即將停止時調用
                  從遊戲中刪除，例如因為 is_valid() 回傳 False。
      at_script_delete()
      at_server_reload() - 伺服器重新載入時呼叫。可以用來
                  保存您想要的臨時變數應該在重新載入後仍然存在。
      at_server_shutdown() - 在伺服器完全關閉時呼叫。
      at_server_start()"""

    pass


# ---------------------------------------------------------------------------
# CombatScript — Evennia 持續戰鬥會話
#
# 透過將 CombatSession 狀態儲存在 ScriptDB 中，在 `evennia reload` 上保持不變。
# 每次伺服器啟動時，at_start() 都會將活動會話還原到 manager.sessions 中。
# ---------------------------------------------------------------------------

import random
import uuid
from typing import List, Optional


class CombatScript(DefaultScript):
    """由 Evennia 的 ScriptDB 支援的回合製戰鬥會話，以實現持久性。

    這包裝了 CombatSession（普通 Python 類別）。創建時會話是
    儲存在 Evennia ScriptDB（持久）和 manager.sessions 中
    （用於快速進程內存取）。  重新載入後，at_start() 恢復所有
    來自資料庫的 CombatScript 並重建記憶體中會話。

    戰鬥的進展取決於玩家的行動（而不是計時器），因此：
      - 間隔 = 0（無 at_repeat）
      - is_valid() 檢查 has_end() — 過期會話會自動刪除
      - at_stop() 清理 manager.sessions 條目"""

    # ScriptDB 儲存的屬性 - 這些屬性在伺服器重新載入後仍然存在
    # 透過 self.db.<name> 儲存在 ScriptDB 中

    def at_script_creation(self):
        """首次建立腳本時呼叫一次。"""
        self.db.combatant_ids = []  # 物件 dbref 列表
        self.db.session_id = None
        self.db.session_state = {}  # 序列化的 CombatSession 狀態（字典）
        self.db.round_count = 1
        self.db.current_turn_index = 0
        self.interval = 0  # 沒有計時器
        self.repeats = 0  # 無限（以 is_valid() 結束）
        self.persistent = True

    def is_valid(self) -> bool:
        """戰鬥結束時傳回 False → Evennia 會自動刪除此腳本。"""
        if not self.db.session_state:
            return False
        # 至少重構以呼叫 has_end()
        from world.combat_manager import CombatSession

        state = self.db.session_state
        # 檢查是否有戰鬥者的hp > 0
        living = [
            cid for cid in state.get("combatants_ids", []) if self._get_hp(cid) > 0
        ]
        return len(living) > 1  # 當 2 名以上戰鬥人員活著時有效

    def _get_hp(self, combatant_id):
        """從 ScriptDB 儲存的快照中取得 hp。"""
        snapshot = self.db.session_state.get("combatant_snapshots", {})
        data = snapshot.get(combatant_id, {})
        return data.get("hp", 0)

    def at_start(self):
        """在每個伺服器啟動/重新載入時調用。恢復到管理器的會話。"""
        state = self.db.session_state
        if not state:
            return

        from world.combat_manager import CombatSession, manager

        # 從 ScriptDB 快照中還原戰鬥人員（dbrefs + 屬性）
        combatants = self._reconstruct_combatants()
        if not combatants:
            return

        # 從恢復狀態建構 CombatSession
        session = CombatSession.__new__(CombatSession)
        session.session_id = self.db.session_id or str(self.dbref)
        session.combatants = combatants
        session.turn_order = sorted(
            combatants,
            key=lambda c: c.get_stat("agility") + c.get_stat("spd"),
            reverse=True,
        )
        session.current_turn_index = self.db.current_turn_index
        session.round_count = self.db.round_count
        session.is_active = True
        session._turn_timer = None
        session.timer_factory = None

        # 儲存在manager.sessions中
        manager.sessions[session.session_id] = session

        # 從快照恢復戰鬥狀態
        snapshot = self.db.session_state.get("combatant_snapshots", {})
        for combatant in combatants:
            snap = snapshot.get(combatant.dbref, {})
            if snap:
                for k, v in snap.items():
                    setattr(combatant.db, k, v)
            combatant.db.combat_session = session.session_id

    def _reconstruct_combatants(self):
        """使用儲存的 dbrefs 從 Evennia 資料庫載入戰鬥人員。"""
        from evennia.utils.utils import make_iter

        combatant_ids = self.db.combatant_ids or []
        combatants = []
        for cid in combatant_ids:
            # cid 可能是字串 dbref，如「#12」或一個 int
            cid_str = str(cid).lstrip("#")
            try:
                from evennia.objects.models import ObjectDB

                obj = ObjectDB.objects.get(id=int(cid_str))
                # 從實際資料庫重新取得以取得當前狀態
                combatants.append(obj)
            except Exception:
                pass
        return combatants

    def save_state(self):
        """將目前會話狀態快照到 ScriptDB 中。"""
        if not hasattr(self, "_session"):
            return
        session = self._session
        self.db.session_id = getattr(session, "session_id", None)
        self.db.combatant_ids = [
            getattr(c, "dbref", None) or getattr(c, "id", None)
            for c in session.combatants
        ]
        self.db.current_turn_index = session.current_turn_index
        self.db.round_count = session.round_count

        # 關鍵戰鬥屬性快照
        snapshot = {}
        for c in session.combatants:
            cid = getattr(c, "dbref", None) or getattr(c, "id", None)
            if cid:
                snapshot[cid] = {
                    "hp": getattr(c.db, "hp", 0),
                    "mp": getattr(c.db, "mp", 0),
                    "combat_status": getattr(c.db, "combat_status", "normal"),
                    "combat_state": getattr(c.db, "combat_state", "idle"),
                    "active_buffs": dict((getattr(c.db, "active_buffs", {}) or {})),
                }
        self.db.session_state = {
            "combatants_ids": self.db.combatant_ids,
            "combatant_snapshots": snapshot,
        }

    def at_stop(self):
        """當腳本停止/刪除時呼叫。從 manager.sessions 中刪除。"""
        from world.combat_manager import manager

        sid = self.db.session_id or getattr(self, "dbref", None)
        if sid and sid in manager.sessions:
            del manager.sessions[sid]

    def at_server_reload(self):
        """在伺服器重新載入之前儲存狀態（與 save_state 相同）。"""
        self.save_state()

    def at_server_shutdown(self):
        """儲存伺服器關閉前的狀態。"""
        self.save_state()

    # --- 委託給記憶體中 CombatSession 的方法 ---
    # 由 Battle_commands.py 透過 manager.sessions[session_id].method() 調用

    def next_turn(self):
        from world.combat_manager import manager

        sid = self.db.session_id or getattr(self, "dbref", None)
        session = manager.sessions.get(sid)
        if not session:
            return None
        self._session = session  # 儲存狀態標記
        result = session.next_turn()
        self._auto_save()
        return result

    def process_status_effects(self):
        from world.combat_manager import manager

        sid = self.db.session_id or getattr(self, "dbref", None)
        session = manager.sessions.get(sid)
        if session:
            self._session = session
            session.process_status_effects()
            self._auto_save()

    def has_ended(self):
        from world.combat_manager import manager

        sid = self.db.session_id or getattr(self, "dbref", None)
        session = manager.sessions.get(sid)
        return session.has_ended() if session else True

    def living_combatants(self):
        from world.combat_manager import manager

        sid = self.db.session_id or getattr(self, "dbref", None)
        session = manager.sessions.get(sid)
        return session.living_combatants() if session else []

    def get_current_actor(self):
        from world.combat_manager import manager

        sid = self.db.session_id or getattr(self, "dbref", None)
        session = manager.sessions.get(sid)
        return session.get_current_actor() if session else None

    def trigger_ai_turn(self, actor):
        from world.combat_manager import manager

        sid = self.db.session_id or getattr(self, "dbref", None)
        session = manager.sessions.get(sid)
        if session:
            self._session = session
            session.trigger_ai_turn(actor)
            self._auto_save()

    def _auto_save(self):
        """每次突變後保存狀態。"""
        try:
            self.save_state()
        except Exception:
            pass
