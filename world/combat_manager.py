from __future__ import annotations

import random
import uuid
from typing import List, Optional

# Default timeout for player action (seconds)
COMBAT_TURN_TIMEOUT = 60


class CombatSession:
    """Represents one active turn-based combat session."""

    def __init__(self, combatants: List, timer_factory: Optional[Callable] = None):
        self.session_id = str(uuid.uuid4())
        self.combatants = combatants
        self.turn_order = []
        self.current_turn_index = 0
        self.round_count = 1
        self.is_active = True
        self._turn_timer = None  # Evennia delay() handle for timeout cancellation
        self.timer_factory = timer_factory
        self.sort_turns()

    def sort_turns(self):
        """Sort turn order based on final agility and speed."""
        self.turn_order = sorted(
            self.combatants,
            key=lambda c: c.get_stat("agility") + c.get_stat("spd"),
            reverse=True,
        )

    def get_current_actor(self):
        """Return the current actor, if combat is still active."""
        if not self.is_active or not self.turn_order:
            return None
        return self.turn_order[self.current_turn_index]

    def living_combatants(self):
        """Return all living combatants in this session."""
        return [c for c in self.combatants if getattr(c.db, "hp", 0) > 0]

    def has_ended(self):
        """Check if combat has reached its end state."""
        return len(self.living_combatants()) <= 1

    # ------------------------------------------------------------------
    # P0-1: Turn timeout mechanism
    # ------------------------------------------------------------------
    def _cancel_turn_timer(self):
        """Cancel any pending turn-timeout callback."""
        if self._turn_timer is not None:
            try:
                self._turn_timer.delete()
            except Exception:
                pass
            self._turn_timer = None

    def _on_turn_timeout(self):
        """Called when the player takes too long to act.

        P0-1: Force-skip the actor's turn and broadcast to all.
        """
        if not self.is_active:
            return
        actor = self.get_current_actor()
        if actor is None:
            return
        # Only apply timeout to player-controlled characters
        if not getattr(actor, "account", None):
            return

        self._cancel_turn_timer()
        self._broadcast(f"⏰ {actor.key} 思考太久，自動跳過了這個回合。")
        self._advance_past_actor()

    def _start_turn_timer(self):
        """Start the Evennia delay() countdown for player turn timeout."""
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
        """Send a message to all combatants."""
        for c in self.combatants:
            c.msg(msg)

    def _consume_control_status(self, actor, status_name, release_message):
        """Consume one turn of a control status and clear it when exhausted."""
        duration = max(1, int(getattr(actor.db, "combat_status_duration", 1) or 1))
        duration -= 1
        actor.db.combat_status_duration = duration
        if duration <= 0:
            actor.db.combat_status = "normal"
            actor.db.combat_status_duration = 0
        self._broadcast(release_message)

    def _advance_past_actor(self):
        """Skip the current actor and advance to the next turn.

        Used by both timeout and normal next_turn() success path.
        """
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

            # Check for control status (stunned/frozen) on the next actor BEFORE triggering AI
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
            # If the next actor is NPC, check retaliates flag before triggering AI
            if not getattr(next_actor, "account", None):
                if not getattr(next_actor.db, "npc_retaliates", True):
                    self._broadcast(f"🕊️ {next_actor.key} 沒有反擊，回合略過。")
                    # Advance past this non-retaliating NPC and continue the loop
                    self.current_turn_index = (self.current_turn_index + 1) % len(
                        self.turn_order
                    )
                    if self.current_turn_index == 0:
                        self.round_count += 1
                        self.process_status_effects()
                        if self.has_ended():
                            return
                    # Check if we've looped through all combatants to avoid infinite loop
                    valid_count = sum(
                        1 for c in self.turn_order if getattr(c.db, "hp", 0) > 0
                    )
                    if valid_count <= 1:
                        return
                    continue  # Let the while loop find the next valid actor
                self.trigger_ai_turn(next_actor)
            return

    # ------------------------------------------------------------------
    # end P0-1
    # ------------------------------------------------------------------

    def next_turn(self):
        """Advance to the next valid actor and trigger AI if needed.

        Bug-A fix: index is incremented at the END of the successful path
        (not at the start of every iteration), so turn_order[0] is always
        checked on the very first call.
        """
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

            # P0-1: Player's turn — start the timeout timer
            self._start_turn_timer()

            # Advance index for next call — only reached on success
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
        """Apply round-end status effects to combatants."""
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
        """Let an NPC perform an automatic turn."""
        from commands.combat_commands import execute_combat_action

        targets = [
            c for c in self.combatants if c != actor and getattr(c.db, "hp", 0) > 0
        ]
        if not targets:
            return

        target = random.choice(targets)

        # P0-2: Pull spells from magic_tools instead of hardcoded SKILL_TABLE
        usable_skills = self._get_usable_spells(actor)
        if usable_skills and random.random() > 0.4:
            execute_combat_action(
                actor, "skill", target, skill_key=random.choice(usable_skills)
            )
            return
        execute_combat_action(actor, "attack", target)

    def _get_usable_spells(self, actor):
        """P0-2: Return list of spell_keys the actor can currently cast.

        Reads from magic_tools.py spell registry (ScriptDB) instead of
        the static SKILL_TABLE in combat_commands.py.
        Returns spell keys (strings) the NPC AI can choose from.
        """
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
        """Return the player target that this NPC is fighting, if any."""
        for c in self.combatants:
            if c.db and getattr(c.db, "is_npc", False) and c is npc_obj:
                # Return the first non-NPC combatant
                players = [
                    x for x in self.combatants if not getattr(x.db, "is_npc", False)
                ]
                return players[0] if players else None
        return None


class CombatManager:
    """Global singleton manager for all combat sessions."""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(CombatManager, cls).__new__(cls)
            cls._instance.sessions = {}
        return cls._instance

    def start_combat(self, combatants: List, timer_factory: Optional[Callable] = None):
        """Create and initialize a new combat session.

        Always creates an in-memory CombatSession in manager.sessions.
        When Evennia is available, also creates a CombatScript in ScriptDB
        so the session survives server reload.
        """
        session = CombatSession(combatants, timer_factory=timer_factory)
        self.sessions[session.session_id] = session
        for combatant in combatants:
            combatant.db.combat_state = "fighting"
            combatant.db.combat_session = session.session_id
            combatant.db.combat_status = "normal"

        # Try to create a persistent Evennia ScriptDB entry
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
        """Create an Evennia CombatScript in ScriptDB. Silently no-ops if Evennia is unavailable."""
        try:
            from evennia import create_script
            from typeclasses.scripts import CombatScript

            script = create_script(
                "typeclasses.scripts.CombatScript",
                key=f"combat_{session.session_id}",
                persistent=True,
            )
            # Store session reference for delegation
            script._session = session
            script.db.combatant_ids = [
                getattr(c, "dbref", None) or getattr(c, "id", None) for c in combatants
            ]
            # Save initial state
            script.save_state()
        except Exception:
            # No Evennia — testing or standalone mode, pass
            pass

    def end_combat(self, session_id: str, reason: str = "normal"):
        """End a combat session and clear state on all combatants.

        Args:
            session_id: The session to end.
            reason: "normal"=normal end, "flee"=NPC escaped, "death"=NPC died.
        """
        if session_id not in self.sessions:
            return

        session = self.sessions[session_id]

        # P0-1: Cancel any pending timeout timer
        session._cancel_turn_timer()

        session.is_active = False

        winner = next(
            (c for c in session.combatants if getattr(c.db, "hp", 0) > 0), None
        )

        # Calculate exp awards
        exp_per_player = self._calc_exp_for_session(session, winner, reason)

        for combatant in session.combatants:
            # Skip combatants that have been deleted from DB
            if not getattr(combatant, "pk", None):
                continue
            combatant.db.combat_state = "idle"
            combatant.db.combat_session = None
            combatant.db.combat_status = "normal"
            combatant.db.combat_status_duration = 0
            combatant.msg("戰鬥已結束。")

            # Award exp to players
            if winner and not getattr(combatant.db, "is_npc", False):
                exp_amount = exp_per_player.get(id(combatant), 0)
                if exp_amount > 0 and hasattr(combatant, "gain_exp"):
                    combatant.gain_exp(exp_amount)
                    combatant.msg(f"✨ 你獲得了 {exp_amount} 點經驗值！")

        # Stop the Evennia CombatScript if it exists
        self._stop_combat_script(session_id)

        del self.sessions[session_id]

    def _stop_combat_script(self, session_id):
        """Stop and delete the Evennia CombatScript for this session."""
        try:
            from evennia import search_script

            results = search_script(f"combat_{session_id}", exact=True)
            if results:
                results[0].stop()
        except Exception:
            pass

    def is_combatant_locked_by_session(self, combatant, exclude_session_id=None):
        """Check whether a combatant is locked by another active combat session.

        Args:
            combatant: Character or NPC object to inspect.
            exclude_session_id: Session id to ignore, typically the attacker's own.

        Returns:
            bool: True if the combatant is already in another active session.
        """
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
        """Backward-compatible wrapper for NPC combat lock checks."""
        return self.is_combatant_locked_by_session(
            npc_obj, exclude_session_id=exclude_session_id
        )

    def _calc_exp_for_session(self, session, winner, reason):
        """Calculate exp per player based on session outcome.

        Bug-B fix: also require player to be alive (HP > 0).
        """
        exp_per_player = {}
        players = [c for c in session.combatants if not getattr(c.db, "is_npc", False)]

        def _get_hp(char):
            """Safely get HP from character db, defaulting to 0 if not set."""
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
        """Handle NPC death: drop tokens, drop loot, enter cooldown, and only end combat if one side remains."""
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
        """Handle NPC fleeing: enter cooldown and end combat."""
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


# Module-level singleton
manager = CombatManager()
