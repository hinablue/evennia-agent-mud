"""Isolated end-to-end combat smoke tests.

These tests replace the old live-shell smoke runner. They run under Evennia's
Django test harness and therefore use a temporary test database instead of the
live game database.
"""

from __future__ import annotations

from types import MethodType
from unittest.mock import patch

from evennia import create_object, search_script
from evennia.utils.test_resources import EvenniaTest

from commands.combat_commands import CombatCmdSet
from world.combat_manager import CombatSession, manager
from world.npc_tools import set_npc_combat_flags, set_npc_skills, set_npc_stats
from world.room_tools import RoomTools


class CombatLiveSmokeTests(EvenniaTest):
    """Exercise combat flows against an isolated Evennia test database."""

    def setUp(self):
        """Create a fresh combat sandbox for each test case."""
        super().setUp()
        self.turn_timer_patcher = patch.object(
            CombatSession, "_start_turn_timer", autospec=True, return_value=None
        )
        self.turn_timer_patcher.start()
        self.room = self.room1
        self.room.key = "訓練廳"
        self.logs = {}
        self.alpha = None
        self.beta = None
        self.gamma = None
        self.create_temp_characters()

    def tearDown(self):
        """Clean up transient combat objects and sessions."""
        self.cleanup()
        self.turn_timer_patcher.stop()
        super().tearDown()

    def _bind_logger(self, obj):
        """Capture object messages for later assertions."""
        self.logs[obj.key] = []

        def _msg(this, text=None, **kwargs):
            msg_str = str(text)
            if kwargs:
                msg_str += f" {kwargs}"
            self.logs[this.key].append(msg_str)

        obj.msg = MethodType(_msg, obj)

    def _set_player_binding(self, obj, account):
        """Bind an Evennia account onto a character in both common slots."""
        obj.account = account
        obj.db_account = account
        if account is not None:
            account.db._last_puppet = obj

    def _set_npc_binding(self, obj):
        """Mark an object as an NPC for combat logic."""
        obj.account = None
        obj.db_account = None
        obj.db.is_npc = True
        obj.save()

    def create_temp_characters(self):
        """Create the alpha/beta/gamma combatants for one isolated test."""
        self.alpha = create_object(
            "typeclasses.characters.Character",
            key="SmokeCaseAlphaTmp",
            location=self.room,
            home=self.room,
        )
        self.beta = create_object(
            "typeclasses.npcs.NPC",
            key="SmokeCaseBetaTmp",
            location=self.room,
            home=self.room,
        )
        self.gamma = create_object(
            "typeclasses.npcs.NPC",
            key="SmokeCaseGammaTmp",
            location=self.room,
            home=self.room,
        )

        for obj in (self.alpha, self.beta, self.gamma):
            self._bind_logger(obj)

        self._set_player_binding(self.alpha, self.account)
        self.alpha.db.is_npc = False
        self.alpha.aliases.add("阿法")
        self.alpha.save()

        self._set_npc_binding(self.beta)
        self.beta.aliases.add("小鬼")

        self._set_npc_binding(self.gamma)
        self.gamma.aliases.add("影子")

        self._apply_common_stats()

    def cleanup(self):
        """End all active sessions and delete temporary combatants."""
        seen = set()
        for obj in (self.alpha, self.beta, self.gamma):
            if not obj or not getattr(obj, "pk", None):
                continue
            session_id = getattr(obj.db, "combat_session", None)
            if session_id and session_id in manager.sessions and session_id not in seen:
                seen.add(session_id)
                manager.end_combat(session_id)

        manager.sessions.clear()

        for obj in (self.gamma, self.beta, self.alpha):
            if obj and getattr(obj, "pk", None):
                obj.delete()

        self.alpha = None
        self.beta = None
        self.gamma = None

    def _replace_beta_with_player(self):
        """Recreate beta as a player character for PVP-only tests."""
        if self.beta and getattr(self.beta, "pk", None):
            self.beta.delete()
        self.beta = create_object(
            "typeclasses.characters.Character",
            key="SmokeCaseBetaTmp",
            location=self.room,
            home=self.room,
        )
        self._bind_logger(self.beta)
        self._set_player_binding(self.beta, self.account2)
        self.beta.db.is_npc = False
        self.beta.aliases.add("小鬼")
        self.beta.save()
        self._apply_common_stats()
        return self.beta

    def _apply_common_stats(self):
        """Apply baseline stats and clear transient combat state."""
        for obj in (self.alpha, self.beta, self.gamma):
            if not obj or not getattr(obj, "pk", None):
                continue
            obj.location = self.room
            obj.home = self.room
            obj.db.sockets = {}
            obj.db.equipped_items = []
            obj.db.skills = []
            obj.db.npc_attackable = True
            obj.db.npc_retaliates = True
            obj.db.npc_can_die = True
            obj.db.combat_state = "idle"
            obj.db.combat_session = None
            obj.db.combat_status = "normal"
            self.logs[obj.key] = []
            try:
                obj.cmdset.remove_default(CombatCmdSet)
            except Exception:
                pass
            try:
                obj.cmdset.remove(CombatCmdSet)
            except Exception:
                pass

        self.alpha.db.base_str = 18
        self.alpha.db.base_def = 8
        self.alpha.db.base_intel = 40
        self.alpha.db.base_agility = 20
        self.alpha.db.base_spirit = 10
        self.alpha.db.base_stamina = 12
        self.alpha.db.base_spd = 12
        self.alpha.db.hp = 100
        self.alpha.db.max_hp = 100
        self.alpha.db.mp = 30
        self.alpha.db.max_mp = 30
        self.alpha.db.exp = 0
        self.alpha.db.tokens = 0

        self.beta.db.base_str = 8
        self.beta.db.base_def = 4
        self.beta.db.base_intel = 12
        self.beta.db.base_agility = 10
        self.beta.db.base_spirit = 0
        self.beta.db.base_stamina = 4
        self.beta.db.base_spd = 10
        self.beta.db.hp = 30
        self.beta.db.max_hp = 30
        self.beta.db.mp = 30
        self.beta.db.max_mp = 30

        self.gamma.db.base_str = 14
        self.gamma.db.base_def = 8
        self.gamma.db.base_intel = 12
        self.gamma.db.base_agility = 15
        self.gamma.db.base_spirit = 12
        self.gamma.db.base_stamina = 8
        self.gamma.db.base_spd = 11
        self.gamma.db.hp = 40
        self.gamma.db.max_hp = 40
        self.gamma.db.mp = 20
        self.gamma.db.max_mp = 20

        for obj in (self.alpha, self.beta, self.gamma):
            if obj and getattr(obj, "pk", None):
                obj.save()

        RoomTools.set_pvp_state(self.room.key, False)

    def tail(self, obj, count=12):
        """Return the last few captured messages for an object."""
        return self.logs.get(obj.key, [])[-count:]

    def test_socket_command(self):
        """socket command should write the selected gem into slot1."""
        self.alpha.execute_cmd("socket ruby 1")
        slot = self.alpha.db.sockets.get("slot1")
        self.assertTrue(slot and slot["name"] == "紅寶石")

    def test_combat_lock_and_basic_kill(self):
        """Basic lethal combat should end the session and restore idle state."""
        self.beta.db.hp = 12
        session = manager.start_combat([self.alpha, self.beta])
        self.alpha.execute_cmd("look")
        with patch("commands.combat_commands.random.random", return_value=0.0):
            self.alpha.execute_cmd("attack SmokeCaseBetaTmp")
        alpha_tail = self.tail(self.alpha)
        self.assertTrue(
            any(
                "只能使用 attack、skill 或 flee" in line
                or "只能使用 attack 或 skill" in line
                for line in alpha_tail
            )
        )
        self.assertEqual(self.beta.db.hp, 0)
        self.assertNotIn(session.session_id, manager.sessions)
        self.assertEqual(self.alpha.db.combat_state, "idle")

    def test_stun_flow(self):
        """Stunned targets should lose a turn and recover afterwards."""
        self.beta.db.hp = 50
        session = manager.start_combat([self.alpha, self.beta])
        with patch("commands.combat_commands.random.random", side_effect=[0.0, 0.5]):
            self.alpha.execute_cmd("skill stun_bash SmokeCaseBetaTmp")
        self.assertEqual(self.beta.db.combat_status, "normal")
        self.assertIn(session.session_id, manager.sessions)
        self.assertEqual(session.get_current_actor(), self.alpha)

    def test_poison_round_tick_kill(self):
        """Poison damage should tick across rounds and can kill the target."""
        RoomTools.set_pvp_state(self.room.key, True)
        self.alpha.db.base_str = 4
        self.beta.db.base_def = 1
        self.beta.db.hp = 12
        self.beta.db.max_hp = 12
        self.alpha.db.hp = 100
        self.alpha.db.max_hp = 100
        self.alpha.save()
        self.beta.save()
        manager.start_combat([self.alpha, self.beta])
        random_values = [0.0, 1.0, 0.0, 0.0, 0.0]
        with patch("commands.combat_commands.random.random", side_effect=random_values):
            self.alpha.execute_cmd("skill poison_dart SmokeCaseBetaTmp")
        self.assertLess(self.beta.db.hp, 12)
        with patch("commands.combat_commands.random.random", return_value=0.0):
            self.alpha.execute_cmd("attack SmokeCaseBetaTmp")
        self.assertEqual(self.beta.db.hp, 0)
        self.assertEqual(self.beta.db.combat_status, "normal")
        self.assertTrue(any("中毒" in line for line in self.tail(self.alpha)))

    def test_alias_target_resolution(self):
        """Alias-based target lookup should resolve correctly in combat."""
        self.beta.db.hp = 12
        manager.start_combat([self.alpha, self.beta])
        with patch("commands.combat_commands.random.random", return_value=0.0):
            self.alpha.execute_cmd("attack 小鬼")
        self.assertEqual(self.beta.db.hp, 0)

    def test_self_target_guards(self):
        """Combat skills should guard against invalid self-target usage."""
        self.beta.db.hp = 12
        manager.start_combat([self.alpha, self.beta])
        self.alpha.execute_cmd("skill heavy_strike 阿法")
        alpha_tail = self.tail(self.alpha)
        self.assertTrue(
            any(
                "自己" in line or "自身" in line or "不認識" in line
                for line in alpha_tail
            )
        )

    def test_insufficient_mp(self):
        """Using a skill without MP should report a helpful error."""
        self.beta.db.hp = 12
        self.alpha.db.mp = 0
        self.alpha.save()
        manager.start_combat([self.alpha, self.beta])
        self.alpha.execute_cmd("skill heavy_strike SmokeCaseBetaTmp")
        self.assertTrue(any("法力不足" in line for line in self.tail(self.alpha)))

    def test_player_pvp_room_gate(self):
        """Player-vs-player combat should be blocked outside PVP rooms only."""
        self._replace_beta_with_player()
        self.alpha.db.hp = 100
        self.alpha.db.max_hp = 100
        self.beta.db.hp = 30
        self.beta.db.max_hp = 30
        self.alpha.save()
        self.beta.save()

        RoomTools.set_pvp_state(self.room.key, False)
        self.alpha.execute_cmd("attack SmokeCaseBetaTmp")
        alpha_tail = self.tail(self.alpha)
        self.assertTrue(any("不是 PVP 房" in line for line in alpha_tail))
        self.assertEqual(self.alpha.db.combat_state, "idle")

        RoomTools.set_pvp_state(self.room.key, True)
        with patch("commands.combat_commands.random.random", return_value=0.0):
            self.alpha.execute_cmd("attack SmokeCaseBetaTmp")
        self.assertEqual(self.alpha.db.combat_state, "fighting")
        self.assertLess(self.beta.db.hp, 30)

    def test_npc_flags_and_admin_stats(self):
        """NPC admin helpers should alter combat behavior immediately."""
        set_npc_combat_flags(self.beta.key, attackable=False)
        self.alpha.execute_cmd("attack SmokeCaseBetaTmp")
        self.assertTrue(any("不能被攻擊" in line for line in self.tail(self.alpha)))

        set_npc_combat_flags(
            self.beta.key, attackable=True, retaliates=False, can_die=False
        )
        set_npc_stats(
            self.beta.key,
            {"str": 22, "hp": 15, "max_hp": 15, "mp": 9, "max_mp": 9, "spd": 7},
        )
        set_npc_skills(self.beta.key, ["heavy_strike"])
        self.assertEqual(self.beta.db.base_str, 22)
        self.assertEqual(self.beta.db.max_hp, 15)
        self.assertEqual(self.beta.db.skills, ["heavy_strike"])

        session = manager.start_combat([self.alpha, self.beta])
        with patch("commands.combat_commands.random.random", return_value=0.0):
            self.alpha.execute_cmd("attack SmokeCaseBetaTmp")
        self.assertEqual(self.beta.db.hp, 1)
        self.assertIn(session.session_id, manager.sessions)
        alpha_tail = self.tail(self.alpha, 18)
        self.assertTrue(any("不會死亡" in line for line in alpha_tail))
        self.assertTrue(any("沒有反擊" in line for line in alpha_tail))

    def test_reload_restores_hp_mp(self):
        """CombatScript reload should restore saved combat session state."""
        self.alpha.db.hp = 33
        self.alpha.db.mp = 7
        self.beta.db.hp = 14
        session = manager.start_combat([self.alpha, self.beta])
        script_key = f"combat_{session.session_id}"
        scripts = [
            row
            for row in search_script(script_key)
            if getattr(row, "key", None) == script_key
        ]
        self.assertTrue(bool(scripts))
        script = scripts[0]
        script._session = session
        script.save_state()

        del manager.sessions[session.session_id]
        self.assertNotIn(session.session_id, manager.sessions)
        script.at_start()
        recovered = manager.sessions.get(session.session_id)
        self.assertIsNotNone(recovered)
        self.assertEqual(self.alpha.db.hp, 33)
        self.assertEqual(self.alpha.db.mp, 7)
        self.assertEqual(self.beta.db.hp, 14)
        self.assertEqual(script.get_current_actor(), recovered.get_current_actor())

    def test_npc_loot_drop(self):
        """NPC death should award tokens and emit a loot message."""
        self.beta.db.npc_loot_table = [
            {
                "typeclass": "typeclasses.equipment.Equipment",
                "key": "生鏽鐵劍",
                "chance": 1.0,
                "stats": {"atk": 3},
            }
        ]
        self.beta.save()
        self.alpha.db.base_str = 100
        self.alpha.db.base_def = 100
        self.alpha.db.hp = 100
        self.alpha.db.max_hp = 100
        self.alpha.save()
        manager.start_combat([self.alpha, self.beta])
        with patch("commands.combat_commands.random.random", return_value=0.0):
            self.alpha.execute_cmd("attack SmokeCaseBetaTmp")
        alpha_tail = self.tail(self.alpha, 20)
        self.assertEqual(self.beta.db.hp, 0)
        self.assertTrue(
            any(
                "撿到" in s or "拾取" in s or "掉落" in s for s in map(str, alpha_tail)
            ),
            alpha_tail,
        )
        self.assertGreater(self.alpha.db.tokens, 0)

    def test_exp_broadcast_on_combat_end(self):
        """Combat end should broadcast exp rewards to the player."""
        self.beta.db.hp = 10
        self.beta.db.max_hp = 10
        self.beta.db.npc_retaliates = False
        self.beta.save()
        self.alpha.db.base_str = 100
        self.alpha.db.base_def = 100
        self.alpha.db.hp = 100
        self.alpha.db.max_hp = 100
        self.alpha.save()
        manager.start_combat([self.alpha, self.beta])
        with patch("commands.combat_commands.random.random", return_value=0.0):
            self.alpha.execute_cmd("attack SmokeCaseBetaTmp")
        alpha_tail = self.tail(self.alpha, 16)
        self.assertEqual(self.beta.db.hp, 0)
        self.assertTrue(any("經驗值" in line for line in alpha_tail))
        self.assertGreater(self.alpha.db.exp, 0)

    def test_emerald_affects_turn_order(self):
        """Socket stat bonuses should affect combat initiative ordering."""
        self.alpha.db.base_agility = 12
        self.alpha.db.base_spd = 10
        self.alpha.save()
        self.beta.db.hp = 30
        self.beta.db.max_hp = 30
        session = manager.start_combat([self.alpha, self.beta])
        order = [obj.key for obj in session.turn_order]
        self.assertEqual(order[0], self.alpha.key, order)

        self.beta.db.sockets = {
            "slot1": {"name": "綠寶石", "stats": {"agility": 3, "spd": 1}}
        }
        self.beta.save()
        manager.end_combat(session.session_id)
        manager.sessions.clear()
        session = manager.start_combat([self.alpha, self.beta])
        order = [obj.key for obj in session.turn_order]
        self.assertEqual(order[0], self.beta.key, order)
        self.assertEqual(self.beta.get_stat("spd"), 11)
        self.assertEqual(self.beta.get_stat("agility"), 13)

    def test_dbref_and_dead_skip_in_multi_combat(self):
        """dbref targeting should work while dead combatants are skipped."""
        self.beta.db.hp = 10
        self.gamma.save()
        session = manager.start_combat([self.alpha, self.beta, self.gamma])
        with patch("commands.combat_commands.random.random", return_value=0.0):
            self.alpha.execute_cmd(f"attack #{self.beta.id}")
        self.assertEqual(self.beta.db.hp, 0)
        self.assertIn(session.session_id, manager.sessions)
        session.next_turn()
        self.assertEqual(session.get_current_actor(), self.alpha)
        alpha_tail = self.tail(self.alpha, 18)
        self.assertTrue(
            any("SmokeCaseGammaTmp 使用 普通攻擊" in line for line in alpha_tail),
            alpha_tail,
        )
