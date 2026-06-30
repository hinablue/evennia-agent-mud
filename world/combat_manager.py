from __future__ import annotations

import random
import uuid
from typing import List, Optional

# 玩家操作的預設逾時（秒）
COMBAT_TURN_TIMEOUT = 60


class CombatSession:
    """代表一個活躍的回合製戰鬥會話。"""

    def __init__(self, combatants: List, timer_factory: Optional[Callable] = None):
        self.session_id = str(uuid.uuid4())
        self.combatants = combatants
        self.turn_order = []
        self.current_turn_index = 0
        self.round_count = 1
        self.is_active = True
        self._turn_timer = None  # Evennia delay() 處理逾時取消
        self.timer_factory = timer_factory
        self.sort_turns()

    def sort_turns(self):
        """根據最終的敏捷性和速度對轉彎順序進行排序。"""
        self.turn_order = sorted(
            self.combatants,
            key=lambda c: c.get_stat("agility") + c.get_stat("spd"),
            reverse=True,
        )

    def get_current_actor(self):
        """如果戰鬥仍處於活動狀態，則返回當前演員。"""
        if not self.is_active or not self.turn_order:
            return None
        return self.turn_order[self.current_turn_index]

    def living_combatants(self):
        """返回本次會議中所有活著的戰鬥人員。"""
        return [c for c in self.combatants if getattr(c.db, "hp", 0) > 0]

    def has_ended(self):
        """檢查戰鬥是否已達到結束狀態。"""
        return len(self.living_combatants()) <= 1

    # ------------------------------------------------------------------
    # P0-1：開啟逾時機制
    # ------------------------------------------------------------------
    def _cancel_turn_timer(self):
        """取消任何待處理的輪次逾時回呼。"""
        if self._turn_timer is not None:
            try:
                self._turn_timer.delete()
            except Exception:
                pass
            self._turn_timer = None

    def _on_turn_timeout(self):
        """當玩家採取行動的時間過長時調用。

        P0-1：強制跳過演員的回合並向所有人廣播。"""
        if not self.is_active:
            return
        actor = self.get_current_actor()
        if actor is None:
            return
        # 僅對玩家控制的角色應用超時
        if not getattr(actor, "account", None):
            return

        self._cancel_turn_timer()
        self._broadcast(f"⏰ {actor.key} 思考太久，自動跳過了這個回合。")
        self._advance_past_actor()

    def _start_turn_timer(self):
        """啟動 Evennia 延遲（）倒數計時，以實現玩家回合逾時。"""
        self._cancel_turn_timer()
        if hasattr(self, "timer_factory") and self.timer_factory:
            try:
                self._turn_timer = self.timer_factory(
                    COMBAT_TURN_TIMEOUT,
                    self._on_turn_timeout,
                )
            except Exception:
                self._turn_timer = None
        else:
            try:
                from evennia import delay

                self._turn_timer = delay(
                    COMBAT_TURN_TIMEOUT,
                    self._on_turn_timeout,
                )
            except Exception:
                self._turn_timer = None

    def _broadcast(self, msg: str):
        """向所有戰鬥人員發送訊息。"""
        for c in self.combatants:
            c.msg(msg)

    def _consume_control_status(self, actor, status_name, release_message):
        """消耗一回合控制狀態，耗儘後清除。"""
        duration = max(1, int(getattr(actor.db, "combat_status_duration", 1) or 1))
        duration -= 1
        actor.db.combat_status_duration = duration
        if duration <= 0:
            actor.db.combat_status = "normal"
            actor.db.combat_status_duration = 0
        self._broadcast(release_message)

    def _advance_past_actor(self):
        """跳過當前演員並前進到下一個回合。

        由逾時和正常的 next_turn() 成功路徑使用。"""
        while self.is_active:
            self.current_turn_index = (self.current_turn_index + 1) % len(
                self.turn_order
            )
            if self.current_turn_index == 0:
                self.round_count += 1
                self.process_status_effects()
                if self.has_ended():
                    return
            next_actor = self.get_current_actor()
            if not next_actor:
                return

            # 在觸發 AI 之前檢查下一個演員的控制狀態（眩暈/凍結）
            if getattr(next_actor.db, "combat_status", "normal") == "stunned":
                self._consume_control_status(
                    next_actor,
                    "stunned",
                    f"😵 {next_actor.key} 精神不振，被眩暈了，跳過回合！",
                )
                continue
            if getattr(next_actor.db, "combat_status", "normal") == "frozen":
                self._consume_control_status(
                    next_actor,
                    "frozen",
                    f"🧊 {next_actor.key} 仍被冰封，這回合無法行動！",
                )
                continue

            self._broadcast(f"\n➡️ 現在輪到 {next_actor.key} 行動。")
            # 如果下一個演員是NPC，在觸發AI之前檢查報復標誌
            if not getattr(next_actor, "account", None):
                if not getattr(next_actor.db, "npc_retaliates", True):
                    self._broadcast(f"🕊️ {next_actor.key} 沒有反擊，回合略過。")
                    # 越過這個不報復的 NPC 並繼續循環
                    self.current_turn_index = (self.current_turn_index + 1) % len(
                        self.turn_order
                    )
                    if self.current_turn_index == 0:
                        self.round_count += 1
                        self.process_status_effects()
                        if self.has_ended():
                            return
                    # 檢查我們是否已經循環了所有戰鬥人員以避免無限循環
                    valid_count = sum(
                        1 for c in self.turn_order if getattr(c.db, "hp", 0) > 0
                    )
                    if valid_count <= 1:
                        return
                    continue  # 讓 while 迴圈找到下一個有效的 actor
                self.trigger_ai_turn(next_actor)
            return

    # ------------------------------------------------------------------
    # 結束 P0-1
    # ------------------------------------------------------------------

    def next_turn(self):
        """前進到下一個有效的演員並在需要時觸發人工智慧。

        Bug-A 修復：索引在成功路徑的末尾遞增
        （不是在每次迭代開始時），所以turn_order[0]總是
        在第一次通話時進行了檢查。"""
        if not self.turn_order or self.has_ended():
            return None

        max_attempts = len(self.turn_order) * 2
        attempts = 0

        while self.is_active and attempts < max_attempts:
            actor = self.turn_order[self.current_turn_index]
            if getattr(actor.db, "hp", 0) <= 0:
                attempts += 1
                self.current_turn_index = (self.current_turn_index + 1) % len(
                    self.turn_order
                )
                if self.current_turn_index == 0:
                    self.round_count += 1
                    self.process_status_effects()
                    if self.has_ended():
                        return None
                continue

            if getattr(actor.db, "combat_status", "normal") == "stunned":
                self._consume_control_status(
                    actor,
                    "stunned",
                    f"😵 {actor.key} 精神不振，被眩暈了，跳過回合！",
                )
                attempts += 1
                self.current_turn_index = (self.current_turn_index + 1) % len(
                    self.turn_order
                )
                if self.current_turn_index == 0:
                    self.round_count += 1
                    self.process_status_effects()
                    if self.has_ended():
                        return None
                continue

            if getattr(actor.db, "combat_status", "normal") == "frozen":
                self._consume_control_status(
                    actor,
                    "frozen",
                    f"🧊 {actor.key} 仍被冰封，這回合無法行動！",
                )
                attempts += 1
                self.current_turn_index = (self.current_turn_index + 1) % len(
                    self.turn_order
                )
                if self.current_turn_index == 0:
                    self.round_count += 1
                    self.process_status_effects()
                    if self.has_ended():
                        return None
                continue

            if not actor.account:
                if not getattr(actor.db, "npc_retaliates", True):
                    self._broadcast(f"🕊️ {actor.key} 沒有反擊，回合略過。")
                    attempts += 1
                    self.current_turn_index = (self.current_turn_index + 1) % len(
                        self.turn_order
                    )
                    if self.current_turn_index == 0:
                        self.round_count += 1
                        self.process_status_effects()
                        if self.has_ended():
                            return None
                    continue
                self.trigger_ai_turn(actor)
                if self.has_ended():
                    return None
                current_actor = self.get_current_actor()
                if current_actor is not actor:
                    if current_actor and getattr(current_actor, "account", None):
                        self._start_turn_timer()
                    return current_actor

            # P0-1：輪到玩家了－啟動超時計時器
            self._start_turn_timer()

            # 下一次調用的高級索引 - 僅在成功時達到
            self.current_turn_index = (self.current_turn_index + 1) % len(
                self.turn_order
            )
            if self.current_turn_index == 0:
                self.round_count += 1
                self.process_status_effects()
                if self.has_ended():
                    return None
            return actor

        return None

    def process_status_effects(self):
        """對戰鬥人員施加回合結束狀態效果。"""
        for combatant in self.combatants:
            if getattr(combatant.db, "hp", 0) <= 0:
                continue

            before_buffs = set((getattr(combatant.db, "active_buffs", {}) or {}).keys())
            before_debuffs = set(
                (getattr(combatant.db, "active_debuffs", {}) or {}).keys()
            )

            if hasattr(combatant, "tick_buffs"):
                combatant.tick_buffs()

            after_buffs = set((getattr(combatant.db, "active_buffs", {}) or {}).keys())
            after_debuffs = set(
                (getattr(combatant.db, "active_debuffs", {}) or {}).keys()
            )

            for stat in sorted(before_buffs - after_buffs):
                self._broadcast(f"⏳ {combatant.key} 的 {stat} 增益效果消失了。")
            for stat in sorted(before_debuffs - after_debuffs):
                self._broadcast(f"⏳ {combatant.key} 的 {stat} 減益效果消失了。")

            if getattr(combatant.db, "combat_status", "normal") == "poisoned":
                stamina = combatant.get_stat("stamina")
                damage = max(1, 10 - (stamina // 2))
                combatant.db.hp = max(0, getattr(combatant.db, "hp", 0) - damage)
                for viewer in self.combatants:
                    viewer.msg(
                        f"🤢 {combatant.key} 受到毒素侵蝕，失去了 {damage} 點 HP。"
                    )
                if combatant.db.hp <= 0:
                    combatant.db.combat_status = "normal"
                    combatant.db.combat_status_duration = 0
                    for viewer in self.combatants:
                        viewer.msg(f"💀 {combatant.key} 因中毒倒下了！")

    def trigger_ai_turn(self, actor):
        """讓 NPC 執行自動轉彎。"""
        from commands.combat_commands import execute_combat_action

        targets = [
            c for c in self.combatants if c != actor and getattr(c.db, "hp", 0) > 0
        ]
        if not targets:
            return

        target = random.choice(targets)

        # P0-2：從 magic_tools 中提取法術而不是硬編碼的 SKILL_TABLE
        usable_skills = self._get_usable_spells(actor)
        if usable_skills and random.random() > 0.4:
            execute_combat_action(
                actor, "skill", target, skill_key=random.choice(usable_skills)
            )
            return
        execute_combat_action(actor, "attack", target)

    def _get_usable_spells(self, actor):
        """P0-2：傳回演員目前可以施放的spell_keys清單。

        從 magic_tools.py 拼字註冊表（ScriptDB）讀取而不是
        Battle_commands.py 中的靜態 SKILL_TABLE。
        傳回 NPC AI 可以選擇的拼字鍵（字串）。"""
        try:
            from world.magic_tools import _list_all_spells
        except Exception:
            return []

        usable = []
        for spell in _list_all_spells():
            mp_cost = getattr(spell.db, "mp_cost", 0)
            spell_level = getattr(spell.db, "spell_level", 1)
            spell_id = getattr(spell.db, "spell_id", None) or getattr(
                spell, "key", None
            )
            if (
                getattr(actor.db, "mp", 0) >= mp_cost
                and getattr(actor.db, "level", 1) >= spell_level
                and spell_id
            ):
                usable.append(spell_id)
        return usable

    def get_npc_target(self, npc_obj):
        """傳回該 NPC 正在戰鬥的玩家目標（如果有）。"""
        for c in self.combatants:
            if c.db and getattr(c.db, "is_npc", False) and c is npc_obj:
                # 返回第一個非 NPC 戰鬥人員
                players = [
                    x for x in self.combatants if not getattr(x.db, "is_npc", False)
                ]
                return players[0] if players else None
        return None


class CombatManager:
    """所有戰鬥會話的全域單例管理器。"""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(CombatManager, cls).__new__(cls)
            cls._instance.sessions = {}
        return cls._instance

    def start_combat(self, combatants: List, timer_factory: Optional[Callable] = None):
        """建立並初始化一個新的戰鬥會話。

        始終在 manager.sessions 中建立記憶體中 CombatSession。
        當 Evennia 可用時，也會在 ScriptDB 中建立 CombatScript
        所以會話在伺服器重新載入後仍然存在。"""
        session = CombatSession(combatants, timer_factory=timer_factory)
        self.sessions[session.session_id] = session
        for combatant in combatants:
            combatant.db.combat_state = "fighting"
            combatant.db.combat_session = session.session_id
            combatant.db.combat_status = "normal"

        # 嘗試建立持久性 Evennia ScriptDB 條目
        self._create_combat_script(session, combatants)

        first_actor = session.get_current_actor()
        if first_actor:
            msg = f"⚔️ 戰鬥開始！目前輪到：{first_actor.key}"
            for combatant in combatants:
                combatant.msg(msg)
            if not first_actor.account:
                session.trigger_ai_turn(first_actor)
        return session

    def _create_combat_script(self, session, combatants):
        """在 ScriptDB 中建立 Evennia CombatScript。如果 Evennia 不可用，則靜默無操作。"""
        try:
            from evennia import create_script
            from typeclasses.scripts import CombatScript

            script = create_script(
                "typeclasses.scripts.CombatScript",
                key=f"combat_{session.session_id}",
                persistent=True,
            )
            # 儲存委派的會話參考
            script._session = session
            script.db.combatant_ids = [
                getattr(c, "dbref", None) or getattr(c, "id", None) for c in combatants
            ]
            # 保存初始狀態
            script.save_state()
        except Exception:
            # 沒有 Evennia — 測試或獨立模式，通過
            pass

    def end_combat(self, session_id: str, reason: str = "normal"):
        """結束戰鬥並清除所有戰鬥人員的狀態。

        參數：
            session_id：要結束的會話。
            原因：「normal」=正常結束，「flee」=NPC逃脫，「death」=NPC死亡。"""
        if session_id not in self.sessions:
            return

        session = self.sessions[session_id]

        # P0-1：取消任何掛起的逾時定時器
        session._cancel_turn_timer()

        session.is_active = False

        winner = next(
            (c for c in session.combatants if getattr(c.db, "hp", 0) > 0), None
        )

        # 計算經驗獎勵
        exp_per_player = self._calc_exp_for_session(session, winner, reason)

        for combatant in session.combatants:
            # 跳過已從資料庫中刪除的戰鬥人員
            if not getattr(combatant, "pk", None):
                continue
            combatant.db.combat_state = "idle"
            combatant.db.combat_session = None
            combatant.db.combat_status = "normal"
            combatant.db.combat_status_duration = 0
            combatant.msg("戰鬥已結束。")

            # 獎勵經驗給玩家
            if winner and not getattr(combatant.db, "is_npc", False):
                exp_amount = exp_per_player.get(id(combatant), 0)
                if exp_amount > 0 and hasattr(combatant, "gain_exp"):
                    combatant.gain_exp(exp_amount)
                    combatant.msg(f"✨ 你獲得了 {exp_amount} 點經驗值！")

        # 停止 Evennia CombatScript（如果存在）
        self._stop_combat_script(session_id)

        del self.sessions[session_id]

    def _stop_combat_script(self, session_id):
        """停止並刪除此會話的 Evennia CombatScript。"""
        try:
            from evennia import search_script

            results = search_script(f"combat_{session_id}", exact=True)
            if results:
                results[0].stop()
        except Exception:
            pass

    def is_combatant_locked_by_session(self, combatant, exclude_session_id=None):
        """檢查戰鬥員是否被另一個活動的戰鬥會話鎖定。

        參數：
            戰鬥員：要檢查的角色或 NPC 物件。
            except_session_id：要忽略的會話 ID，通常是攻擊者自己的。

        返回：
            bool：如果戰鬥者已經在另一個活動會話中，則為 true。"""
        for sid, session in self.sessions.items():
            if sid == exclude_session_id:
                continue
            if not session.is_active:
                continue
            for existing in session.combatants:
                if existing is combatant and getattr(existing.db, "hp", 0) > 0:
                    return True
        return False

    def is_npc_locked_by_session(self, npc_obj, exclude_session_id=None):
        """用於 NPC 戰鬥鎖定檢查的向後相容包裝器。"""
        return self.is_combatant_locked_by_session(
            npc_obj, exclude_session_id=exclude_session_id
        )

    def _calc_exp_for_session(self, session, winner, reason):
        """根據會話結果計算每位玩家的經驗。

        Bug-B 修復：也要求玩家還活著（HP > 0）。"""
        exp_per_player = {}
        players = [c for c in session.combatants if not getattr(c.db, "is_npc", False)]

        def _get_hp(char):
            """從角色資料庫安全取得HP，如果不設定則預設為0。"""
            hp = getattr(char.db, "hp", None)
            return hp if hp is not None else 0

        if reason == "flee":
            # NPC 逃跑：玩家只獲得部分經驗（25%），但玩家必須活著
            base_exp = 12
            for p in players:
                if _get_hp(p) > 0:
                    exp_per_player[id(p)] = base_exp
        elif winner and not getattr(winner.db, "is_npc", False):
            # 玩家獲勝：玩家必須活著（HP > 0）
            if _get_hp(winner) > 0:
                base_exp = 50
                for p in players:
                    if _get_hp(p) > 0:
                        exp_per_player[id(p)] = base_exp
        # NPC 獲勝：無經驗
        return exp_per_player

    def npc_death(self, npc_obj, session_id):
        """處理 NPC 死亡：掉落代幣、掉落戰利品、進入冷卻時間，並且僅在一側剩餘時結束戰鬥。"""
        session = self.sessions.get(session_id)
        token_drop = 0
        if hasattr(npc_obj, "get_tokens_for_drop"):
            token_drop = npc_obj.get_tokens_for_drop()
        else:
            token_drop = max(5, int(getattr(npc_obj.db, "level", 1) or 1) * 10)

        if session:
            player = next((c for c in session.combatants if c.account), None)
            if player and hasattr(player, "add_tokens"):
                player.add_tokens(token_drop)
            # 發放 loot
            if hasattr(npc_obj, "drop_loot"):
                npc_obj.drop_loot(player)
            if hasattr(npc_obj, "enter_cooldown"):
                npc_obj.enter_cooldown(from_death=True)
            else:
                npc_obj.db.npc_in_combat = False
            npc_obj.db.combat_state = "idle"
            npc_obj.db.combat_session = None
            npc_obj.db.combat_status = "normal"
            npc_obj.location = None
            if session.has_ended():
                self.end_combat(session_id, reason="death")
        else:
            try:
                npc_obj.db.npc_in_combat = False
                npc_obj.db.combat_state = "idle"
                npc_obj.db.combat_session = None
                npc_obj.db.combat_status = "normal"
                if hasattr(npc_obj, "enter_cooldown"):
                    npc_obj.enter_cooldown(from_death=True)
            except Exception:
                pass

    def npc_flee(self, npc_obj, session_id):
        """處理NPC逃跑：進入冷卻並結束戰鬥。"""
        session = self.sessions.get(session_id)
        if session:
            if hasattr(npc_obj, "enter_cooldown"):
                npc_obj.enter_cooldown(from_death=False)
            else:
                npc_obj.db.npc_in_combat = False
            npc_obj.location = None
            self.end_combat(session_id, reason="flee")
        else:
            try:
                npc_obj.db.npc_in_combat = False
                if hasattr(npc_obj, "enter_cooldown"):
                    npc_obj.enter_cooldown(from_death=False)
            except Exception:
                pass


# 模組級單例
manager = CombatManager()
