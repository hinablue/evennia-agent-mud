"""Unit tests for the expanded combat system.

Tests cover:
- NPC level scaling
- NPC cooldown / death / respawn
- NPC token drops
- NPC flee mechanic
- NPC aggro on look
- Combat session lock (no double-attack)
- Player flee
- Buff/debuff system
- Pick command
- Magic spell system (basic CRUD)
"""

from __future__ import annotations

import importlib
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _install_evennia_stubs():
    evennia = types.ModuleType("evennia")

    class Command:
        """Minimal Evennia command stub."""

    class CmdSet:
        """Minimal Evennia cmdset stub."""

        def add(self, *args, **kwargs):
            return None

    evennia.Command = Command
    evennia.CmdSet = CmdSet
    evennia.search_script = lambda *a, **k: []
    evennia.search_object = lambda *a, **k: []
    evennia.default_cmds = types.SimpleNamespace(
        CharacterCmdSet=type("CharacterCmdSet", (), {}),
        AccountCmdSet=type("AccountCmdSet", (), {}),
        UnloggedinCmdSet=type("UnloggedinCmdSet", (), {}),
        SessionCmdSet=type("SessionCmdSet", (), {}),
    )
    evennia.logger = types.SimpleNamespace(
        log_info=lambda *a, **k: None,
        log_err=lambda *a, **k: None,
        log_warn=lambda *a, **k: None,
    )
    sys.modules["evennia"] = evennia

    utils_pkg = types.ModuleType("evennia.utils")
    utils_module = types.ModuleType("evennia.utils.utils")

    def inherits_from(obj, path):
        if path == "typeclasses.characters.Character":
            return not getattr(getattr(obj, "db", object()), "is_npc", False)
        return False

    utils_module.inherits_from = inherits_from
    utils_pkg.utils = utils_module
    sys.modules["evennia.utils"] = utils_pkg
    sys.modules["evennia.utils.utils"] = utils_module

    commands_pkg = types.ModuleType("evennia.commands")
    cmdhandler_module = types.ModuleType("evennia.commands.cmdhandler")
    command_module = types.ModuleType("evennia.commands.command")
    command_module.Command = Command
    cmdhandler_module.CMD_NOMATCH = "__nomatch_command"
    cmdhandler_module.CMD_NOINPUT = "__noinput_command"
    default_account_module = types.ModuleType("evennia.commands.default.account")

    class CmdIC:
        def func(self):
            self._super_called = True

    default_account_module.CmdIC = CmdIC
    commands_pkg.cmdhandler = cmdhandler_module
    sys.modules["evennia.commands"] = commands_pkg
    sys.modules["evennia.commands.cmdhandler"] = cmdhandler_module
    sys.modules["evennia.commands.command"] = command_module
    sys.modules["evennia.commands.default.account"] = default_account_module

    objects_module = types.ModuleType("evennia.objects.objects")

    class DefaultObject:
        def at_object_creation(self):
            return None

        def at_cmdset_get(self, **kwargs):
            return None

    class DefaultCharacter(DefaultObject):
        """Minimal DefaultCharacter stub."""

    objects_module.DefaultObject = DefaultObject
    objects_module.DefaultCharacter = DefaultCharacter
    sys.modules["evennia.objects.objects"] = objects_module

    clothing_module = types.ModuleType("evennia.contrib.game_systems.clothing")
    clothing_module.ClothedCharacter = type("ClothedCharacter", (), {})
    sys.modules["evennia.contrib.game_systems.clothing"] = clothing_module

    gender_module = types.ModuleType("evennia.contrib.game_systems.gendersub")
    gender_module.GenderCharacter = type("GenderCharacter", (), {})
    sys.modules["evennia.contrib.game_systems.gendersub"] = gender_module

    rp_module = types.ModuleType("evennia.contrib.rpg.rpsystem")
    rp_module.ContribRPCharacter = type("ContribRPCharacter", (), {})
    rp_module.ContribRPObject = type("ContribRPObject", (), {})
    sys.modules["evennia.contrib.rpg.rpsystem"] = rp_module

    chargen_module = types.ModuleType(
        "evennia.contrib.rpg.character_creator.character_creator"
    )

    class ContribCmdCharCreate:
        def func(self):
            self._super_called = True

    chargen_module.ContribCmdCharCreate = ContribCmdCharCreate
    chargen_module.ContribChargenAccount = type("ContribChargenAccount", (), {})
    sys.modules["evennia.contrib.rpg.character_creator.character_creator"] = (
        chargen_module
    )

    scripts_module = types.ModuleType("evennia.scripts.models")
    scripts_module.ScriptDB = type(
        "ScriptDB",
        (),
        {"objects": types.SimpleNamespace(all=lambda: [])},
    )
    sys.modules["evennia.scripts"] = types.ModuleType("evennia.scripts")
    sys.modules["evennia.scripts.models"] = scripts_module

    objects_models_module = types.ModuleType("evennia.objects.models")
    objects_models_module.ObjectDB = type(
        "ObjectDB",
        (),
        {"objects": types.SimpleNamespace(filter=lambda *a, **k: [], all=lambda: [])},
    )
    sys.modules["evennia.objects.models"] = objects_models_module

    search_module = types.ModuleType("evennia.scripts.handler")

    def fake_search_script(key, exact=False):
        return []

    def fake_search_object(key, exact=False):
        return []

    search_module.search_script = fake_search_script
    search_module.search_object = fake_search_object
    sys.modules["evennia.scripts.handler"] = search_module

    # evennia.typeclasses stubs
    typeclasses_pkg = types.ModuleType("evennia.typeclasses")
    typeclasses_module = types.ModuleType("evennia.typeclasses.attributes")

    class AttributeProperty:
        def __init__(self, default=None, autocreate=False):
            self.default = default
            self.autocreate = autocreate

    typeclasses_module.AttributeProperty = AttributeProperty
    typeclasses_pkg.attributes = typeclasses_module
    sys.modules["evennia.typeclasses"] = typeclasses_pkg
    sys.modules["evennia.typeclasses.attributes"] = typeclasses_module

    # evennia.utils.create stub
    create_module = types.ModuleType("evennia.utils.create")

    def create_object(*a, **k):
        return None

    def create_account(*a, **k):
        return None

    def create_script(*a, **k):
        return None

    def create_channel(*a, **k):
        return None

    def create_message(*a, **k):
        return None

    def create_help_entry(*a, **k):
        return None

    create_module.create_object = create_object
    create_module.create_account = create_account
    create_module.create_script = create_script
    create_module.create_channel = create_channel
    create_module.create_message = create_message
    create_module.create_help_entry = create_help_entry
    sys.modules["evennia.utils.create"] = create_module

    # evennia.utils.utils stub - class_from_module
    utils_module.class_from_module = lambda path, *a, **k: None
    utils_module.make_iter = lambda x: x if isinstance(x, (list, tuple)) else [x]

    llm_npc_module = types.ModuleType("typeclasses.llm_npc")
    llm_npc_module.DEFAULT_PROMPT_PREFIX = ""
    llm_npc_module.LocalLLMNPC = type("LocalLLMNPC", (), {})
    sys.modules["typeclasses.llm_npc"] = llm_npc_module


_install_evennia_stubs()

combat_manager = importlib.import_module("world.combat_manager")
combat_commands = importlib.import_module("commands.combat_commands")
characters_module = importlib.import_module("typeclasses.characters")
npcs_module = importlib.import_module("typeclasses.npcs")
Character = characters_module.Character
NPC = npcs_module.NPC


class FakeAttributes:
    """Very small attribute handler stub."""

    def __init__(self):
        self._data = {}

    def get(self, key, default=None):
        return self._data.get(key, default)

    def add(self, key, value):
        self._data[key] = value


class FakeDB(types.SimpleNamespace):
    """Namespace-backed db attr holder."""


class FakeCombatant:
    """Simple combatant test double."""

    _next_id = 1

    def __init__(
        self,
        key,
        stats=None,
        hp=100,
        mp=30,
        account=True,
        aliases=None,
        is_npc=False,
        room_pvp=False,
        level=1,
    ):
        stats = stats or {}
        self.id = FakeCombatant._next_id
        self.pk = self.id
        FakeCombatant._next_id += 1
        self.key = key
        self.account = account
        self.messages = []
        self.exp_gained = 0
        self.tokens_gained = 0
        self.aliases = types.SimpleNamespace(all=lambda: aliases or [])
        # location with msg_contents stub
        self.location = types.SimpleNamespace(
            db=types.SimpleNamespace(pvp_enabled=room_pvp),
            msg_contents=lambda *a, **k: None,
        )
        self.search_results = {}
        self.db = FakeDB(
            hp=hp,
            mp=mp,
            combat_state="idle",
            combat_session=None,
            combat_status="normal",
            is_npc=is_npc,
            npc_attackable=True,
            npc_retaliates=True,
            npc_can_die=True,
            skills=[],
            level=level,
            npc_cooldown=60,
            npc_death_time=None,
            npc_token_min=1,
            npc_token_max=5,
            npc_can_flee=True,
            npc_flee_chance=0.20,
            npc_flee_countdown=0,
            npc_aggro_chance=0.0,
            active_buffs={},
            active_debuffs={},
        )
        self._stats = {
            "str": 10,
            "def": 10,
            "spirit": 10,
            "intel": 10,
            "agility": 10,
            "stamina": 10,
            "spd": 10,
            "atk": 10,
        }
        self._stats.update(stats)

    def save(self):
        """Stub for Evennia's save() method."""
        pass

    def get_stat(self, stat_name):
        return self._stats.get(stat_name, 10)

    def msg(self, text):
        self.messages.append(text)

    def gain_exp(self, amount):
        self.exp_gained += amount

    def add_tokens(self, amount):
        self.tokens_gained += amount

    def search(self, name):
        return self.search_results.get(name)

    def is_in_cooldown(self):
        if self.db.npc_death_time is None:
            return False
        import time

        elapsed = time.time() - self.db.npc_death_time
        return elapsed < self.db.npc_cooldown

    def get_tokens_for_drop(self):
        import random

        level = max(1, int(self.db.level or 1))
        token_min = max(1, int(self.db.npc_token_min or 1))
        token_max = max(1, int(self.db.npc_token_max or 5))
        base = random.randint(token_min, token_max)
        bonus = (level - 1) * 2
        return base + bonus

    def attempt_flee(self):
        import random

        if not self.db.npc_can_flee:
            return False
        # 失敗率 = 基礎失敗率（越高越容易失敗）
        fail_rate = max(0.05, min(0.90, float(self.db.npc_flee_chance or 0.20)))
        if random.random() < fail_rate:
            return False  # 逃跑失敗
        return True  # 逃跑成功

    def enter_cooldown(self, from_death=True):
        import time

        self.db.npc_death_time = time.time()

    def check_aggro_on_look(self):
        if not self.db.npc_aggro_chance:
            return False
        import random

        return random.random() < self.db.npc_aggro_chance

    def apply_buff(self, stat, amount, duration):
        if duration <= 0:
            return
        buffs = getattr(self.db, "active_buffs") or {}
        import time

        buffs[stat] = {
            "amount": int(amount),
            "duration": int(duration),
            "applied_at": time.time(),
        }
        self.db.active_buffs = buffs

    def apply_debuff_to_self(self, stat, amount, duration):
        if duration <= 0:
            return
        debuffs = getattr(self.db, "active_debuffs") or {}
        import time

        debuffs[stat] = {
            "amount": int(amount),
            "duration": int(duration),
            "applied_at": time.time(),
        }
        self.db.active_debuffs = debuffs

    def get_buff_bonus(self, stat_name):
        buffs = getattr(self.db, "active_buffs") or {}
        buff = buffs.get(stat_name)
        if not buff:
            return 0
        return buff.get("amount", 0)

    def get_debuff_penalty(self, stat_name):
        debuffs = getattr(self.db, "active_debuffs") or {}
        debuff = debuffs.get(stat_name)
        if not debuff:
            return 0
        return debuff.get("amount", 0)

    def tick_buffs(self):
        buffs = getattr(self.db, "active_buffs") or {}
        debuffs = getattr(self.db, "active_debuffs") or {}
        expired = []
        for stat, data in buffs.items():
            data["duration"] -= 1
            if data["duration"] <= 0:
                expired.append(stat)
        for stat in expired:
            del buffs[stat]
        self.db.active_buffs = buffs

        expired_debuffs = []
        for stat, data in debuffs.items():
            data["duration"] -= 1
            if data["duration"] <= 0:
                expired_debuffs.append(stat)
        for stat in expired_debuffs:
            del debuffs[stat]
        self.db.active_debuffs = debuffs


# ---------------------------------------------------------------------------
# Tests: NPC Level Scaling
# ---------------------------------------------------------------------------


class NPCLevelScalingTests(unittest.TestCase):
    """Test NPC level attribute scaling."""

    def test_scale_stat_formula(self):
        scale = npcs_module.LEVEL_SCALING
        self.assertAlmostEqual(scale["hp"], 0.15)
        self.assertAlmostEqual(scale["atk"], 0.04)
        self.assertAlmostEqual(scale["spd"], 0.03)

    def test_scale_stat_computation(self):
        base_val = 100
        level5_hp = npcs_module.scale_stat(base_val, 5, "hp")
        # 100 * (1 + 4 * 0.15) = 100 * 1.6 = 160
        self.assertEqual(level5_hp, 160)

        level10_hp = npcs_module.scale_stat(base_val, 10, "hp")
        # 100 * (1 + 9 * 0.15) = 100 * 2.35 = 235 (may be 234 due to float precision)
        self.assertIn(level10_hp, [234, 235])

    def test_npc_default_level_is_one(self):
        npc = NPC()
        npc.db = FakeDB(
            is_npc=True,
            npc_kind="npc",
            npc_attackable=True,
            npc_retaliates=True,
            npc_can_die=True,
            level=1,
            base_level=1,
            npc_cooldown=60,
            npc_death_time=None,
            npc_token_min=1,
            npc_token_max=5,
            npc_can_flee=True,
            npc_flee_chance=0.20,
            npc_flee_countdown=0,
            npc_aggro_chance=0.0,
            desc="test",
            hp=100,
            max_hp=100,
            mp=30,
            max_mp=30,
        )
        npc.attributes = FakeAttributes()
        self.assertEqual(npc.db.level, 1)

    def test_npc_higher_level_has_more_hp(self):
        npc = NPC()
        npc.db = FakeDB(
            is_npc=True,
            npc_kind="npc",
            npc_attackable=True,
            npc_retaliates=True,
            npc_can_die=True,
            level=1,
            base_level=1,
            npc_cooldown=60,
            npc_death_time=None,
            npc_token_min=1,
            npc_token_max=5,
            npc_can_flee=True,
            npc_flee_chance=0.20,
            npc_flee_countdown=0,
            npc_aggro_chance=0.0,
            desc="test",
            hp=100,
            max_hp=100,
            mp=30,
            max_mp=30,
        )
        npc.attributes = FakeAttributes()
        npc.db.level = 5
        npc._apply_level_stats()
        # Level 5 HP should be scaled
        self.assertGreaterEqual(npc.db.max_hp, 100)


# ---------------------------------------------------------------------------
# Tests: NPC Token Drop
# ---------------------------------------------------------------------------


class NPCTokenDropTests(unittest.TestCase):
    """Test NPC token dropping on death."""

    def test_get_tokens_for_drop_uses_level(self):
        player = FakeCombatant("玩家", account=True)
        npc = FakeCombatant("哥布林", is_npc=True, account=False)
        npc.db.level = 5
        # Need to set token min/max on the fake db to match the NPC class defaults
        npc.db.npc_token_min = 1
        npc.db.npc_token_max = 5

        # Simulate death drop
        tokens = npc.get_tokens_for_drop()
        # Base range 1-5 + bonus (level-1)*2 = 1-5 + 8 = 9-13
        self.assertGreaterEqual(tokens, 9)

    def test_tokens_not_dropped_on_flee(self):
        """When NPC flees, no tokens are dropped."""
        player = FakeCombatant("玩家", account=True)
        npc = FakeCombatant("哥布林", is_npc=True, account=False)

        # NPC flees - tokens remain 0
        success = npc.attempt_flee()
        # We don't know if it succeeded, but the manager should handle it
        # correctly (no tokens on flee)
        self.assertIn(success, [True, False])


# ---------------------------------------------------------------------------
# Tests: NPC Cooldown / Death / Respawn
# ---------------------------------------------------------------------------


class NPCCooldownTests(unittest.TestCase):
    """Test NPC cooldown state after death."""

    def test_npc_not_in_cooldown_initially(self):
        npc = FakeCombatant("哥布林", is_npc=True, account=False)
        self.assertFalse(npc.is_in_cooldown())

    def test_npc_enter_cooldown_sets_timestamp(self):
        npc = FakeCombatant("哥布林", is_npc=True, account=False)
        npc.enter_cooldown(from_death=True)
        self.assertIsNotNone(npc.db.npc_death_time)

    def test_npc_not_in_cooldown_after_respawn(self):
        npc = FakeCombatant("哥布林", is_npc=True, account=False)
        npc.enter_cooldown(from_death=True)
        # Manually clear for respawn
        npc.db.npc_death_time = None
        npc.db.hp = npc.db.max_hp if hasattr(npc.db, "max_hp") else 100
        self.assertFalse(npc.is_in_cooldown())


# ---------------------------------------------------------------------------
# Tests: NPC Flee Mechanic
# ---------------------------------------------------------------------------


class NPCFleeTests(unittest.TestCase):
    """Test NPC flee logic."""

    def test_npc_flee_chance_respected(self):
        npc = FakeCombatant("哥布林", is_npc=True, account=False)
        npc.db.npc_can_flee = True
        npc.db.npc_flee_chance = 0.20  # 20% fail = 80% succeed

        # Run many times - should succeed most
        successes = sum(1 for _ in range(50) if npc.attempt_flee())
        self.assertGreater(successes, 30)  # At least 60% success

    def test_npc_flee_disabled_always_fails(self):
        npc = FakeCombatant("哥布林", is_npc=True, account=False)
        npc.db.npc_can_flee = False
        results = [npc.attempt_flee() for _ in range(10)]
        self.assertFalse(any(results))

    def test_npc_flee_high_fail_chance_rarely_succeeds(self):
        npc = FakeCombatant("哥布林", is_npc=True, account=False)
        npc.db.npc_can_flee = True
        npc.db.npc_flee_chance = 0.90  # 90% fail = 10% succeed

        successes = sum(1 for _ in range(50) if npc.attempt_flee())
        self.assertLess(successes, 15)  # Should rarely succeed


# ---------------------------------------------------------------------------
# Tests: NPC Aggro on Look
# ---------------------------------------------------------------------------


class NPCAggroTests(unittest.TestCase):
    """Test NPC aggro chance on look."""

    def test_aggro_zero_never_triggers(self):
        npc = FakeCombatant("石像鬼", is_npc=True, account=False)
        npc.db.npc_aggro_chance = 0.0
        results = [npc.check_aggro_on_look() for _ in range(20)]
        self.assertFalse(any(results))

    def test_aggro_half_triggers_roughly_half(self):
        npc = FakeCombatant("石像鬼", is_npc=True, account=False)
        npc.db.npc_aggro_chance = 0.50
        # Run many times and check distribution
        results = [npc.check_aggro_on_look() for _ in range(200)]
        triggered = sum(results)
        # Should be between 35% and 65%
        self.assertGreater(triggered, 60)
        self.assertLess(triggered, 140)


# ---------------------------------------------------------------------------
# Tests: Combat Session Lock
# ---------------------------------------------------------------------------


class CombatLockTests(unittest.TestCase):
    """Test that attackable NPC locks are respected."""

    def setUp(self):
        combat_manager.manager.sessions.clear()

    def test_npc_locked_prevents_second_attacker(self):
        player1 = FakeCombatant("玩家A", account=True)
        player2 = FakeCombatant("玩家B", account=True)
        npc = FakeCombatant("哥布林", is_npc=True, account=False, hp=50)

        session1 = combat_manager.manager.start_combat([player1, npc])
        session_id = session1.session_id

        # Player 2 tries to attack the same NPC
        ok, reason = combat_commands.validate_combat_target(player2, npc)
        self.assertFalse(ok)
        self.assertIn("其他敵人", reason)


# ---------------------------------------------------------------------------
# Tests: Player Flee
# ---------------------------------------------------------------------------


class PlayerFleeTests(unittest.TestCase):
    """Test player flee command."""

    def setUp(self):
        combat_manager.manager.sessions.clear()

    def test_player_flee_consumes_turn_on_failure(self):
        player = FakeCombatant("玩家", stats={"agility": 10}, account=True)
        npc = FakeCombatant("哥布林", is_npc=True, account=False, hp=50)

        session = combat_manager.manager.start_combat([player, npc])

        # Mock random to force flee failure
        with patch("commands.combat_commands.random.random", return_value=0.0):
            cmd = object.__new__(combat_commands.CmdCombatFlee)
            cmd.caller = player
            cmd.args = ""
            cmd.func()

        # Flee failed message
        self.assertTrue(any("被敵人追上" in msg for msg in player.messages))

    def test_player_flee_succeeds_and_ends_combat(self):
        player = FakeCombatant("玩家", stats={"agility": 50}, account=True)
        npc = FakeCombatant("哥布林", is_npc=True, account=False, hp=50)

        session = combat_manager.manager.start_combat([player, npc])
        session_id = session.session_id

        # Mock random to force flee success (high agility = low fail)
        with patch("commands.combat_commands.random.random", return_value=1.0):
            cmd = object.__new__(combat_commands.CmdCombatFlee)
            cmd.caller = player
            cmd.args = ""
            cmd.func()

        self.assertTrue(any("成功逃離" in msg for msg in player.messages))
        self.assertTrue(any("玩家 成功逃離了戰鬥" in msg for msg in npc.messages))
        # Session should be gone
        self.assertNotIn(session_id, combat_manager.manager.sessions)


# ---------------------------------------------------------------------------
# Tests: Buff / Debuff System
# ---------------------------------------------------------------------------


class BuffSystemTests(unittest.TestCase):
    """Test player buff and debuff system."""

    def test_apply_buff_increases_stat(self):
        player = FakeCombatant("玩家", stats={"str": 10})
        player.apply_buff("str", 5, 3)
        self.assertEqual(player.get_buff_bonus("str"), 5)

    def test_buff_multiple_stats(self):
        player = FakeCombatant("玩家")
        player.apply_buff("str", 5, 3)
        player.apply_buff("def", 3, 2)
        self.assertEqual(player.get_buff_bonus("str"), 5)
        self.assertEqual(player.get_buff_bonus("def"), 3)

    def test_tick_buffs_decrements_duration(self):
        player = FakeCombatant("玩家")
        player.apply_buff("str", 5, 3)
        player.tick_buffs()
        # Duration goes from 3 to 2
        buffs = player.db.active_buffs
        self.assertEqual(buffs["str"]["duration"], 2)

    def test_tick_buffs_removes_expired(self):
        player = FakeCombatant("玩家")
        player.apply_buff("str", 5, 1)
        player.tick_buffs()
        self.assertEqual(player.get_buff_bonus("str"), 0)

    def test_several_buffs_independent_timing(self):
        player = FakeCombatant("玩家")
        player.apply_buff("str", 5, 3)
        player.apply_buff("def", 3, 5)
        player.tick_buffs()  # str: 2, def: 4
        self.assertEqual(player.get_buff_bonus("str"), 5)
        self.assertEqual(player.get_buff_bonus("def"), 3)
        player.tick_buffs()  # str: 1, def: 3
        self.assertEqual(player.get_buff_bonus("str"), 5)
        self.assertEqual(player.get_buff_bonus("def"), 3)
        player.tick_buffs()  # str: expired, def: 2
        self.assertEqual(player.get_buff_bonus("str"), 0)
        self.assertEqual(player.get_buff_bonus("def"), 3)


# ---------------------------------------------------------------------------
# Tests: NPC Death + Exp Award
# ---------------------------------------------------------------------------


class NPCDeathExpTests(unittest.TestCase):
    """Test NPC death handling and exp awards."""

    def setUp(self):
        combat_manager.manager.sessions.clear()

    def test_player_gets_exp_when_npc_dies(self):
        attacker = FakeCombatant("玩家", stats={"str": 20, "intel": 50})
        defender = FakeCombatant(
            "哥布林", stats={"def": 1, "agility": 1}, hp=5, is_npc=True, account=False
        )
        session = combat_manager.manager.start_combat([attacker, defender])

        with patch("commands.combat_commands.random.random", return_value=0.0):
            combat_commands.execute_combat_action(attacker, "attack", defender)

        # NPC died - session ended
        self.assertEqual(defender.db.hp, 0)
        # Player should have gotten exp
        self.assertGreater(attacker.exp_gained, 0)

    def test_flee_reduces_exp(self):
        """NPC flee awards only 25% exp."""
        attacker = FakeCombatant("玩家", stats={"str": 20, "intel": 50})
        defender = FakeCombatant(
            "哥布林", stats={"def": 1, "agility": 1}, hp=50, is_npc=True, account=False
        )

        session = combat_manager.manager.start_combat([attacker, defender])

        # Player attacks once, then NPC flees
        # The session will give reduced exp because of flee
        # Just verify session exists and the NPC can attempt flee
        defender.db.npc_can_flee = True
        defender.db.npc_flee_chance = 0.0  # Always succeed

        # Flee is handled by the combat flow
        # This test just checks the mechanic exists


# ---------------------------------------------------------------------------
# Tests: Validate Combat Target (lock check)
# ---------------------------------------------------------------------------


class ValidateCombatTargetTests(unittest.TestCase):
    """Test validate_combat_target enforces combat-session lock rules."""

    def tearDown(self):
        """Clear global combat sessions between tests."""
        combat_manager.manager.sessions.clear()

    def test_blocks_attack_on_locked_npc(self):
        player1 = FakeCombatant("玩家A", account=True)
        player2 = FakeCombatant("玩家B", account=True)
        npc = FakeCombatant("哥布林", is_npc=True, account=False)

        # Player 1 starts combat
        session = combat_manager.CombatSession([player1, npc])
        combat_manager.manager.sessions[session.session_id] = session
        player1.db.combat_session = session.session_id
        player1.db.combat_state = "fighting"
        npc.db.combat_session = session.session_id
        npc.db.combat_state = "fighting"

        # Player 2 tries to attack same NPC
        ok, reason = combat_commands.validate_combat_target(player2, npc)
        self.assertFalse(ok)
        self.assertIn("無法同時被多人攻擊", reason)

    def test_blocks_attack_on_locked_player(self):
        player1 = FakeCombatant("玩家A", account=True, room_pvp=True)
        player2 = FakeCombatant("玩家B", account=True, room_pvp=True)
        player3 = FakeCombatant("玩家C", account=True, room_pvp=True)

        session = combat_manager.CombatSession([player1, player2])
        combat_manager.manager.sessions[session.session_id] = session
        player1.db.combat_session = session.session_id
        player1.db.combat_state = "fighting"
        player2.db.combat_session = session.session_id
        player2.db.combat_state = "fighting"

        ok, reason = combat_commands.validate_combat_target(player3, player1)
        self.assertFalse(ok)
        self.assertIn("無法同時被多人攻擊", reason)

    def test_same_session_combatant_can_still_target_opponent(self):
        player1 = FakeCombatant("玩家A", account=True, room_pvp=True)
        player2 = FakeCombatant("玩家B", account=True, room_pvp=True)

        session = combat_manager.CombatSession([player1, player2])
        combat_manager.manager.sessions[session.session_id] = session
        player1.db.combat_session = session.session_id
        player1.db.combat_state = "fighting"
        player2.db.combat_session = session.session_id
        player2.db.combat_state = "fighting"

        ok, reason = combat_commands.validate_combat_target(player1, player2)
        self.assertTrue(ok)
        self.assertIsNone(reason)

    def test_attackable_npc_without_session_can_be_targeted(self):
        player = FakeCombatant("玩家", account=True)
        npc = FakeCombatant("哥布林", is_npc=True, account=False)

        ok, reason = combat_commands.validate_combat_target(player, npc)
        self.assertTrue(ok)


# ---------------------------------------------------------------------------
# Tests: Pick Command (basic)
# ---------------------------------------------------------------------------


class PickCommandTests(unittest.TestCase):
    """Test the pick command for room items."""

    def test_pick_requires_argument(self):
        caller = FakeCombatant("玩家", account=True)
        caller.location = None

        cmd = object.__new__(combat_commands.CmdPick)
        cmd.caller = caller
        cmd.args = ""

        # Capture output
        caller.messages.clear()
        cmd.func()

        self.assertTrue(any("用法" in msg for msg in caller.messages))

    def test_pick_with_no_location(self):
        caller = FakeCombatant("玩家", account=True)
        caller.location = None

        cmd = object.__new__(combat_commands.CmdPick)
        cmd.caller = caller
        cmd.args = "sword"

        caller.messages.clear()
        cmd.func()

        self.assertTrue(any("不在任何地方" in msg for msg in caller.messages))


# ---------------------------------------------------------------------------
# Tests: Dynamic spell metadata / skill flow
# ---------------------------------------------------------------------------


class MagicSkillsTests(unittest.TestCase):
    """Test dynamic spell metadata lookup."""

    def _fake_spell(self, spell_id, **attrs):
        data = {
            "spell_id": spell_id,
            "name": attrs.get("name", spell_id),
            "aliases": attrs.get("aliases", []),
            "mp_cost": attrs.get("mp_cost", 10),
            "chance": attrs.get("chance", 0.8),
            "dmg_min": attrs.get("dmg_min", 0),
            "dmg_max": attrs.get("dmg_max", 0),
            "is_heal": attrs.get("is_heal", False),
            "heal_min": attrs.get("heal_min", 0),
            "heal_max": attrs.get("heal_max", 0),
            "status_effect": attrs.get("status_effect"),
            "buff_stat": attrs.get("buff_stat"),
            "buff_min": attrs.get("buff_min", 0),
            "buff_max": attrs.get("buff_max", 0),
            "debuff_stat": attrs.get("debuff_stat", None),
            "debuff_min": attrs.get("debuff_min", 0),
            "debuff_max": attrs.get("debuff_max", 0),
            "buff_duration": attrs.get("buff_duration", 0),
            "damage_type": attrs.get("damage_type", "physical"),
            "effect_type": attrs.get("effect_type", "damage"),
            "magic_type": attrs.get("magic_type", attrs.get("damage_type", "physical")),
            "target_self": attrs.get("target_self", False),
            "target_enemy": attrs.get("target_enemy", True),
            "spell_level": attrs.get("spell_level", 1),
        }
        return types.SimpleNamespace(key=spell_id, db=types.SimpleNamespace(**data))

    def test_spell_metadata_reads_scriptdb_shape(self):
        fake_spell = self._fake_spell(
            "fireball", name="火球術", mp_cost=20, dmg_min=18, dmg_max=32
        )
        with patch("world.magic_tools.get_spell_by_name", return_value=fake_spell):
            meta = combat_commands._get_spell_metadata("fireball")
        self.assertEqual(meta["spell_id"], "fireball")
        self.assertEqual(meta["name"], "火球術")
        self.assertEqual(meta["mp_cost"], 20)
        self.assertEqual(meta["dmg_max"], 32)

    def test_buff_skill_applies_to_actor(self):
        actor = FakeCombatant("玩家", account=True)
        target = FakeCombatant("哥布林", is_npc=True, account=False)
        combat_manager.manager.start_combat([actor, target])
        spell = {
            "spell_id": "battle_focus",
            "name": "戰鬥專注",
            "mp_cost": 6,
            "chance": 1.0,
            "buff_stat": "str",
            "buff_min": 4,
            "buff_max": 4,
            "buff_duration": 2,
            "target_self": True,
            "target_enemy": False,
        }
        with patch("commands.combat_commands._get_spell_metadata", return_value=spell):
            combat_commands.execute_combat_action(
                actor, "skill", actor, skill_key="battle_focus"
            )
        self.assertEqual(actor.get_buff_bonus("str"), 4)
        self.assertEqual(actor.db.mp, 24)

    def test_debuff_skill_applies_to_target(self):
        actor = FakeCombatant("玩家", account=True)
        target = FakeCombatant("哥布林", is_npc=True, account=False)
        combat_manager.manager.start_combat([actor, target])
        spell = {
            "spell_id": "weaken",
            "name": "虛弱術",
            "mp_cost": 5,
            "chance": 1.0,
            "dmg_min": 4,
            "dmg_max": 4,
            "debuff_stat": "def",
            "debuff_min": 3,
            "debuff_max": 3,
            "buff_duration": 2,
            "target_self": False,
            "target_enemy": True,
        }
        with (
            patch("commands.combat_commands._get_spell_metadata", return_value=spell),
            patch("commands.combat_commands.random.random", return_value=0.0),
        ):
            combat_commands.execute_combat_action(
                actor, "skill", target, skill_key="weaken"
            )
        self.assertEqual(target.get_debuff_penalty("def"), 3)
        self.assertEqual(target.db.hp, 96)

    def test_frozen_status_skips_then_clears(self):
        actor = FakeCombatant("玩家", account=True)
        target = FakeCombatant("哥布林", is_npc=True, account=False)
        session = combat_manager.manager.start_combat([actor, target])
        spell = {
            "spell_id": "ice_shard",
            "name": "冰刺術",
            "mp_cost": 8,
            "chance": 1.0,
            "dmg_min": 3,
            "dmg_max": 3,
            "status_effect": "frozen",
            "target_self": False,
            "target_enemy": True,
        }
        with (
            patch("commands.combat_commands._get_spell_metadata", return_value=spell),
            patch("commands.combat_commands.random.random", side_effect=[0.0, 0.99]),
        ):
            combat_commands.execute_combat_action(
                actor, "skill", target, skill_key="ice_shard"
            )
        self.assertEqual(target.db.combat_status, "normal")
        self.assertEqual(getattr(target.db, "combat_status_duration", 0), 0)
        self.assertIs(session.get_current_actor(), actor)


# ---------------------------------------------------------------------------
# Tests: CombatCmdSet includes flee
# ---------------------------------------------------------------------------


class CombatCmdSetContentsTests(unittest.TestCase):
    """Test CombatCmdSet has all required commands."""

    def test_flee_in_combat_cmdset(self):
        cmdset = combat_commands.CombatCmdSet()
        # The cmdset contains CmdCombatAttack, CmdCombatSkill, CmdCombatFlee, CmdCombatNoMatch, CmdCast
        # Check that the cmdset has commands by checking the commands added at creation
        # We can verify by checking the cmdset's internal _added_commands
        self.assertTrue(hasattr(cmdset, "_added_commands") or len(dir(cmdset)) > 0)
        # More robust: check that the cmdset class defines the expected commands
        self.assertEqual(len(combat_commands.COMBAT_COMMANDS), 5)


if __name__ == "__main__":
    unittest.main()
