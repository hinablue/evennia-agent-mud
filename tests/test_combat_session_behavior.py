"""CombatSession behavior tests — locks the refactoring invariants.

Phase 2 status: Bug-A (next_turn index-0 skip) and Bug-B (HP=0 player still
gets exp) are FIXED. All tests assert CORRECT behavior.

Invariant contracts (must survive CombatSession→CombatScript refactor):
  - turn_order sorted by agility+spd descending
  - has_ended() = len(living) <= 1
  - next_turn() always checks turn_order[current] before advancing
  - stun / no_retaliates always skip and broadcast
  - round_count increments when index wraps to 0
  - is_npc_locked_by_session: NPC in active session is locked
  - _calc_exp_for_session: player must be alive (HP>0) to earn exp
"""

from __future__ import annotations

import importlib
import os
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


# ---------------------------------------------------------------------------
# Evennia stubs
# ---------------------------------------------------------------------------
def _stub_evennia():
    if "evennia" in sys.modules:
        return
    evennia = types.ModuleType("evennia")
    evennia.Command = type("Command", (), {})
    evennia.CmdSet = type("CmdSet", (), {"add": lambda s, *a, **k: None})
    evennia.default_cmds = types.SimpleNamespace(
        CharacterCmdSet=type("CS", (), {}), AccountCmdSet=type("AS", (), {}))
    evennia.logger = types.SimpleNamespace(
        log_info=lambda *a, **k: None, log_err=lambda *a, **k: None,
        log_warn=lambda *a, **k: None)
    sys.modules["evennia"] = evennia
    utils_pkg = types.ModuleType("evennia.utils")
    utils_mod = types.ModuleType("evennia.utils.utils")
    utils_mod.inherits_from = lambda obj, path: not getattr(
        getattr(obj, "db", object()), "is_npc", False)
    utils_mod.class_from_module = lambda *a, **k: None
    utils_mod.make_iter = lambda x: x if isinstance(x, (list, tuple)) else [x]
    utils_pkg.utils = utils_mod
    sys.modules["evennia.utils"] = utils_pkg
    sys.modules["evennia.utils.utils"] = utils_mod
    cmd_pkg = types.ModuleType("evennia.commands")
    cmd_mod = types.ModuleType("evennia.commands.command")
    cmd_mod.Command = evennia.Command
    cmd_pkg.command = cmd_mod
    sys.modules["evennia.commands"] = cmd_pkg
    sys.modules["evennia.commands.command"] = cmd_mod
    ch_mod = types.ModuleType("evennia.commands.cmdhandler")
    ch_mod.CMD_NOMATCH = "__nm__"
    ch_mod.CMD_NOINPUT = "__ni__"
    ch_mod.cmdhandler = types.SimpleNamespace()
    sys.modules["evennia.commands.cmdhandler"] = ch_mod
    search_mod = types.ModuleType("evennia.scripts.handler")
    search_mod.search_script = lambda *a, **k: []
    search_mod.search_object = lambda *a, **k: []
    sys.modules["evennia.scripts.handler"] = search_mod
    create_mod = types.ModuleType("evennia.utils.create")
    create_mod.create_script = lambda *a, **k: None
    create_mod.create_object = lambda *a, **k: None
    sys.modules["evennia.utils.create"] = create_mod
    scr_mod = types.ModuleType("evennia.scripts.models")
    scr_mod.ScriptDB = type("SDB", (), {})
    sys.modules["evennia.scripts"] = types.ModuleType("evennia.scripts")
    sys.modules["evennia.scripts.models"] = scr_mod

_stub_evennia()


# ---------------------------------------------------------------------------
# Imports
# ---------------------------------------------------------------------------
combat_manager = importlib.import_module("world.combat_manager")
importlib.reload(combat_manager)
manager = combat_manager.manager
CombatSession = combat_manager.CombatSession


# ---------------------------------------------------------------------------
# Test-double combatants
# ---------------------------------------------------------------------------

class FakeDB:
    def __init__(self, **kw):
        for k, v in kw.items():
            setattr(self, k, v)


class FakeCombatant:
    _id = 0

    def __init__(self, key="C", account=True, is_npc=False, hp=100, mp=30,
                 str_=10, def_=10, intel=10, agility=10, stamina=10,
                 spd=10, spirit=10, **extra_db):
        FakeCombatant._id += 1
        self.id = FakeCombatant._id
        self.key = key
        self.account = account
        self.messages = []
        self.exp_gained = 0
        self.tokens_gained = 0
        self._stats = {
            "str": str_, "def": def_, "intel": intel, "agility": agility,
            "stamina": stamina, "spd": spd, "spirit": spirit,
        }
        defaults = dict(
            hp=hp, mp=mp, combat_state="idle", combat_session=None,
            combat_status="normal", is_npc=is_npc, npc_attackable=True,
            npc_retaliates=True, npc_can_die=True, skills=[],
            npc_cooldown=60, npc_death_time=None,
            npc_token_min=1, npc_token_max=5,
            npc_can_flee=True, npc_flee_chance=0.20, npc_flee_countdown=0,
            npc_aggro_chance=0.0, active_buffs={}, active_debuffs={},
        )
        defaults.update(extra_db)
        self.db = FakeDB(**defaults)
        self.cmdset = MagicMock()  # so hasattr(cmdset, ...) in trigger_ai_turn works

    def get_stat(self, name):
        return self._stats.get(name, 10)

    def msg(self, text):
        self.messages.append(str(text))

    def gain_exp(self, amount):
        self.exp_gained += amount

    def add_tokens(self, amount):
        self.tokens_gained += amount

    def save(self):
        pass

    def is_in_cooldown(self):
        if self.db.npc_death_time is None:
            return False
        import time
        return time.time() - self.db.npc_death_time < self.db.npc_cooldown

    def get_tokens_for_drop(self):
        import random
        lvl = max(1, getattr(self.db, "level", 1) or 1)
        tmin = max(1, int(getattr(self.db, "npc_token_min", 1) or 1))
        tmax = max(1, int(getattr(self.db, "npc_token_max", 5) or 5))
        return random.randint(tmin, tmax) + (lvl - 1) * 2

    def attempt_flee(self):
        import random
        if not getattr(self.db, "npc_can_flee", False):
            return False
        fail = float(getattr(self.db, "npc_flee_chance", 0.20) or 0.20)
        return random.random() >= fail

    def enter_cooldown(self, from_death=True):
        import time
        self.db.npc_death_time = time.time()

    def add_to_inventory(self, item):
        """Mock add_to_inventory for testing."""
        if not hasattr(self, "inventory"):
            self.inventory = []
        if len(self.inventory) >= 10:
            return False
        self.inventory.append(item)
        # Send message like real implementation
        key = getattr(item, "key", "物品") if hasattr(item, "key") else item.get("key", "物品")
        self.msg(f"💎 你撿到了 {key}！")
        return True

    def drop_loot(self, player):
        """Mock drop_loot for testing - just records the call."""
        self.loot_dropped = True
        # Simulate giving item to player
        if player and hasattr(player, "add_to_inventory"):
            player.add_to_inventory({"key": "鐵劍", "stats": {"atk": 5}})

    def tick_buffs(self):
        buffs = dict(getattr(self.db, "active_buffs", {}))
        expired = [k for k, v in buffs.items() if v.get("duration", 0) - 1 <= 0]
        for k in expired:
            del buffs[k]
        for v in buffs.values():
            v["duration"] = max(0, v.get("duration", 0) - 1)
        self.db.active_buffs = buffs

    def apply_buff(self, stat, amount, duration):
        if duration <= 0:
            return
        import time
        buffs = dict(getattr(self.db, "active_buffs", {}))
        buffs[stat] = {"amount": int(amount), "duration": int(duration),
                       "applied_at": time.time()}
        self.db.active_buffs = buffs

    def get_buff_bonus(self, stat_name):
        buffs = getattr(self.db, "active_buffs", {}) or {}
        b = buffs.get(stat_name)
        return b.get("amount", 0) if b else 0


# ---------------------------------------------------------------------------
# Tests: CombatSession — turn ordering
# ---------------------------------------------------------------------------

class CombatSessionSortOrder(unittest.TestCase):
    def test_higher_agility_spd_first(self):
        fast = FakeCombatant("Fast", agility=20, spd=20)
        slow = FakeCombatant("Slow", agility=5, spd=5)
        session = CombatSession([slow, fast])
        self.assertEqual(session.turn_order[0].key, "Fast")
        self.assertEqual(session.turn_order[1].key, "Slow")

    def test_turn_order_stable_on_tie(self):
        a = FakeCombatant("A", agility=10, spd=10)
        b = FakeCombatant("B", agility=10, spd=10)
        session = CombatSession([a, b])
        self.assertEqual({c.key for c in session.turn_order}, {"A", "B"})


# ---------------------------------------------------------------------------
# Tests: CombatSession — has_ended / living_combatants
# ---------------------------------------------------------------------------

class CombatSessionHasEnded(unittest.TestCase):
    def test_not_ended_two_living(self):
        a = FakeCombatant("A", hp=10)
        b = FakeCombatant("B", hp=10)
        session = CombatSession([a, b])
        self.assertFalse(session.has_ended())

    def test_ended_one_living(self):
        # has_ended = len(living) <= 1
        a = FakeCombatant("A", hp=10)
        b = FakeCombatant("B", hp=0)
        session = CombatSession([a, b])
        self.assertTrue(session.has_ended())

    def test_ended_zero_living(self):
        a = FakeCombatant("A", hp=0)
        b = FakeCombatant("B", hp=0)
        session = CombatSession([a, b])
        self.assertTrue(session.has_ended())


# ---------------------------------------------------------------------------
# Tests: CombatSession — next_turn behavior
#
# IMPORTANT BUG (Bug A): next_turn() increments index BEFORE checking actor.
# turn_order[0] is NEVER evaluated on the first next_turn() call.
# The FIRST actor returned is always turn_order[1] (if it exists).
# This is a bug that the Phase 2 refactor must fix.
# ---------------------------------------------------------------------------

class CombatSessionNextTurn(unittest.TestCase):
    def test_next_turn_checks_first_actor_first(self):
        """FIXED: With Bug-A fixed, first call returns turn_order[0] (not [1])."""
        npc    = FakeCombatant("N", account=None, hp=100, spd=20, agility=20)
        player = FakeCombatant("P", account=True,  hp=100, spd=5,  agility=5)
        session = CombatSession([npc, player])
        # turn_order = [N, P] (N is first, higher spd+agi)
        # With fix: next_turn checks index 0 first → returns N
        actor = session.next_turn()
        self.assertEqual(actor.key, "N")  # Fixed: checks [0] first, not [1]

    def test_dead_actor_skipped_returns_none_when_one_living(self):
        """When only one living remains, has_ended=True → next_turn returns None."""
        npc    = FakeCombatant("N", account=None, hp=0,  spd=20, agility=20)
        player = FakeCombatant("P", account=True,  hp=100, spd=5,  agility=5)
        session = CombatSession([npc, player])
        # living = [player], has_ended=True → None
        self.assertIsNone(session.next_turn())

    def test_stunned_actor_skipped_immediately(self):
        """FIXED: With Bug-A fixed, stunned turn_order[0] is skipped on first call."""
        npc    = FakeCombatant("N", account=None, hp=100, spd=20, agility=20,
                               combat_status="stunned")
        player = FakeCombatant("P", account=True,  hp=100, spd=5,  agility=5)
        session = CombatSession([npc, player])
        # first next_turn: N is index 0, stunned → skip → player (index 1) returns
        actor = session.next_turn()
        self.assertEqual(actor.key, "P")
        self.assertEqual(npc.db.combat_status, "normal")  # stun cleared
        self.assertTrue(any("眩暈" in m for m in npc.messages))  # skip message

    def test_npc_retaliates_false_skipped_immediately(self):
        """FIXED: With Bug-A fixed, npc_retaliates=False at index 0 skipped on first call."""
        npc    = FakeCombatant("N", account=None, hp=100, spd=20, agility=20,
                               npc_retaliates=False)
        player = FakeCombatant("P", account=True,  hp=100, spd=5,  agility=5)
        session = CombatSession([npc, player])
        # first call: N (index 0) has no_retaliates → skip → player (index 1) returns
        actor = session.next_turn()
        self.assertEqual(actor.key, "P")
        self.assertTrue(any("沒有反擊" in m for m in npc.messages))

    def test_round_count_increments_on_wrap(self):
        """Round count increments when index wraps back to 0 after all living have acted.

        With Bug-A fixed, turn order is checked from index 0 on first call:
          - Call 1: N (index 0, npc_retaliates=False) skipped → player (index 1) acts
                   → advance: index=0, round_count=2, process_status_effects
          - Call 2: N (index 0, npc_retaliates=False) skipped → player (index 1) acts
                   → advance: index=0, round_count=3, process_status_effects
        So round_count=3 on the second next_turn() return.
        """
        npc    = FakeCombatant("N", account=None, hp=100, spd=20, agility=20,
                               npc_retaliates=False)
        player = FakeCombatant("P", account=True,  hp=100, spd=5,  agility=5)
        session = CombatSession([npc, player])
        self.assertEqual(session.round_count, 1)
        # Turn 1: N skipped → P acts → advance: round_count=2
        actor1 = session.next_turn()
        self.assertEqual(actor1.key, "P")
        self.assertEqual(session.round_count, 2)
        # Turn 2: N skipped → P acts → advance: round_count=3
        actor2 = session.next_turn()
        self.assertEqual(session.round_count, 3)


# ---------------------------------------------------------------------------
# Tests: CombatSession — status effects
# ---------------------------------------------------------------------------

class CombatSessionStatusEffects(unittest.TestCase):
    def test_poison_ticks_damage(self):
        npc    = FakeCombatant("N", account=None, hp=100, stamina=10,
                               combat_status="poisoned")
        player = FakeCombatant("P", hp=20)
        session = CombatSession([npc, player])
        session.process_status_effects()
        self.assertEqual(npc.db.hp, 95)
        self.assertEqual(npc.db.combat_status, "poisoned")

    def test_poison_floor_at_zero(self):
        npc    = FakeCombatant("N", account=None, hp=3, stamina=10,
                               combat_status="poisoned")
        session = CombatSession([npc])
        session.process_status_effects()
        self.assertEqual(npc.db.hp, 0)
        self.assertEqual(npc.db.combat_status, "normal")

    def test_dead_poison_ignored(self):
        npc    = FakeCombatant("N", account=None, hp=0, combat_status="poisoned")
        session = CombatSession([npc])
        session.process_status_effects()  # must not raise
        self.assertEqual(npc.db.hp, 0)

    def test_expired_buff_removed(self):
        import time
        player = FakeCombatant("P", hp=100)
        player.db.active_buffs = {"str": {"amount": 5, "duration": 1,
                                          "applied_at": time.time()}}
        session = CombatSession([player])
        session.process_status_effects()
        self.assertEqual(player.get_buff_bonus("str"), 0)
        self.assertTrue(any("增益效果消失" in m for m in player.messages))

    def test_active_buff_preserved(self):
        import time
        player = FakeCombatant("P", hp=100)
        player.db.active_buffs = {"str": {"amount": 5, "duration": 3,
                                          "applied_at": time.time()}}
        session = CombatSession([player])
        session.process_status_effects()
        self.assertEqual(player.get_buff_bonus("str"), 5)


# ---------------------------------------------------------------------------
# Tests: CombatManager — start_combat
# ---------------------------------------------------------------------------

class CombatManagerStartCombat(unittest.TestCase):
    def setUp(self):
        FakeCombatant._id = 0
        manager.sessions.clear()

    def test_start_combat_stores_session(self):
        player = FakeCombatant("P", account=True)
        npc    = FakeCombatant("N", account=None)
        session = manager.start_combat([player, npc])
        self.assertIn(session.session_id, manager.sessions)

    def test_combatants_set_to_fighting(self):
        player = FakeCombatant("P", account=True)
        npc    = FakeCombatant("N", account=None)
        session = manager.start_combat([player, npc])
        self.assertEqual(player.db.combat_state, "fighting")
        self.assertEqual(npc.db.combat_state, "fighting")
        self.assertEqual(player.db.combat_session, session.session_id)

    def test_start_combat_announces(self):
        player = FakeCombatant("P", account=True)
        npc    = FakeCombatant("N", account=None)
        manager.start_combat([player, npc])
        all_msgs = player.messages + npc.messages
        self.assertTrue(any("戰鬥開始" in m for m in all_msgs))


# ---------------------------------------------------------------------------
# Tests: CombatManager — is_npc_locked_by_session
# ---------------------------------------------------------------------------

class CombatManagerNPCCheck(unittest.TestCase):
    def setUp(self):
        FakeCombatant._id = 0
        manager.sessions.clear()

    def test_npc_locked_while_in_active_session(self):
        """NPC in active session is locked. Session stays active while NPC is alive."""
        player = FakeCombatant("P", account=True, hp=100)   # high HP so NPC can't kill
        npc    = FakeCombatant("N", account=None, hp=100, str_=1, def_=1)  # weak NPC
        manager.start_combat([player, npc])
        # Session should still be active (NPC alive, player not dead)
        self.assertTrue(manager.is_npc_locked_by_session(npc))

    def test_free_npc_not_locked(self):
        npc = FakeCombatant("N", account=None)
        self.assertFalse(manager.is_npc_locked_by_session(npc))

    def test_ended_session_does_not_lock(self):
        player = FakeCombatant("P", account=True)
        npc    = FakeCombatant("N", account=None)
        session = manager.start_combat([player, npc])
        manager.end_combat(session.session_id)
        self.assertFalse(manager.is_npc_locked_by_session(npc))


# ---------------------------------------------------------------------------
# Tests: CombatManager — end_combat
# ---------------------------------------------------------------------------

class CombatManagerEndCombat(unittest.TestCase):
    def setUp(self):
        FakeCombatant._id = 0
        manager.sessions.clear()

    def tearDown(self):
        manager.sessions.clear()

    def test_end_combat_clears_state(self):
        player = FakeCombatant("P", account=True)
        npc    = FakeCombatant("N", account=None)
        session = manager.start_combat([player, npc])
        manager.end_combat(session.session_id)
        self.assertEqual(player.db.combat_state, "idle")
        self.assertEqual(npc.db.combat_state, "idle")
        self.assertIsNone(player.db.combat_session)
        self.assertEqual(player.db.combat_status, "normal")

    def test_end_combat_removes_session(self):
        player = FakeCombatant("P", account=True)
        npc    = FakeCombatant("N", account=None)
        session = manager.start_combat([player, npc])
        sid = session.session_id
        manager.end_combat(sid)
        self.assertNotIn(sid, manager.sessions)

    def test_death_awards_50_exp(self):
        player = FakeCombatant("P", account=True)
        npc    = FakeCombatant("N", account=None)
        session = manager.start_combat([player, npc])
        manager.end_combat(session.session_id, reason="death")
        self.assertEqual(player.exp_gained, 50)

    def test_flee_awards_partial_exp(self):
        player = FakeCombatant("P", account=True)
        npc    = FakeCombatant("N", account=None)
        session = manager.start_combat([player, npc])
        manager.end_combat(session.session_id, reason="flee")
        self.assertEqual(player.exp_gained, 12)

    def test_player_dead_no_exp(self):
        """FIXED: player HP=0 → no exp even if 'winner' would be player."""
        player = FakeCombatant("P", account=True)
        npc    = FakeCombatant("N", account=None, hp=100)
        player.db.hp = 0  # player dead
        session = manager.start_combat([player, npc])
        manager.end_combat(session.session_id, reason="normal")
        # Bug-B fixed: winner is player but HP=0 → 0 exp
        self.assertEqual(player.exp_gained, 0)


# ---------------------------------------------------------------------------
# Tests: CombatManager — npc_death / npc_flee
# ---------------------------------------------------------------------------

class CombatManagerNPCDeathFlee(unittest.TestCase):
    def setUp(self):
        FakeCombatant._id = 0
        manager.sessions.clear()

    def tearDown(self):
        manager.sessions.clear()

    def test_npc_death_drops_tokens(self):
        player = FakeCombatant("P", account=True)
        npc    = FakeCombatant("N", account=None, hp=0, level=5,
                               npc_token_min=2, npc_token_max=4)
        session = manager.start_combat([player, npc])
        manager.npc_death(npc, session.session_id)
        # rand(2,4) + (5-1)*2 = 2-4+8 = min 10
        self.assertGreaterEqual(player.tokens_gained, 10)

    def test_npc_death_sets_cooldown(self):
        player = FakeCombatant("P", account=True)
        npc    = FakeCombatant("N", account=None, hp=0)
        session = manager.start_combat([player, npc])
        manager.npc_death(npc, session.session_id)
        self.assertIsNotNone(npc.db.npc_death_time)

    def test_npc_death_removes_from_room(self):
        player = FakeCombatant("P", account=True)
        npc    = FakeCombatant("N", account=None, hp=0)
        npc.location = types.SimpleNamespace(msg_contents=lambda *a, **k: None)
        session = manager.start_combat([player, npc])
        manager.npc_death(npc, session.session_id)
        self.assertIsNone(npc.location)

    def test_npc_flee_no_tokens(self):
        player = FakeCombatant("P", account=True)
        npc    = FakeCombatant("N", account=None)
        session = manager.start_combat([player, npc])
        manager.npc_flee(npc, session.session_id)
        self.assertEqual(player.tokens_gained, 0)

    def test_npc_flee_sets_cooldown(self):
        player = FakeCombatant("P", account=True)
        npc    = FakeCombatant("N", account=None)
        session = manager.start_combat([player, npc])
        manager.npc_flee(npc, session.session_id)
        self.assertIsNotNone(npc.db.npc_death_time)

    def test_npc_death_drops_loot(self):
        player = FakeCombatant("P", account=True, hp=100)
        npc = FakeCombatant("N", account=None, hp=0, level=3)
        npc.db.npc_loot_table = [
            {"typeclass": "typeclasses.equipment.Equipment", "key": "鐵劍", "chance": 1.0, "stats": {"atk": 5}}
        ]
        session = manager.start_combat([player, npc])
        manager.npc_death(npc, session.session_id)
        # 物品應該被嘗試放入背包
        self.assertTrue(any("撿到" in str(m) or "拾取" in str(m) for m in player.messages))

    def test_end_combat_broadcasts_exp(self):
        player = FakeCombatant("P", account=True, hp=100)
        npc = FakeCombatant("N", account=None, hp=0)
        session = manager.start_combat([player, npc])
        sid = session.session_id
        manager.end_combat(sid, reason="death")
        # 玩家應收到 exp 通知
        self.assertTrue(any("經驗值" in str(m) for m in player.messages))
        self.assertEqual(player.exp_gained, 50)


# ---------------------------------------------------------------------------
# Smoke: full 1v1 → player attacks → NPC dies → session ends → exp awarded
# ---------------------------------------------------------------------------

class CombatFullSmoke(unittest.TestCase):
    def setUp(self):
        FakeCombatant._id = 0
        manager.sessions.clear()

    def tearDown(self):
        manager.sessions.clear()

    def test_player_kills_npc_exp_awarded(self):
        import commands.combat_commands as cc

        player = FakeCombatant("P", account=True, hp=100, str_=100,
                               def_=0, intel=50, agility=50)
        npc    = FakeCombatant("N", account=None, hp=5, npc_retaliates=False)
        session = manager.start_combat([player, npc])
        sid = session.session_id

        with patch("commands.combat_commands.random.random", return_value=0.0):
            cc.execute_combat_action(player, "attack", npc)

        self.assertEqual(npc.db.hp, 0)
        self.assertNotIn(sid, manager.sessions)
        self.assertEqual(player.exp_gained, 50)
        self.assertEqual(player.db.combat_state, "idle")
        self.assertIsNone(player.db.combat_session)
        self.assertEqual(player.db.combat_status, "normal")


if __name__ == "__main__":
    unittest.main()
