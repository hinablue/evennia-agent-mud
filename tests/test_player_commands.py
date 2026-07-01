"""Tests for player-facing status, inventory, equipment, and shop commands."""

from __future__ import annotations

import importlib
import sys
import types
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


class _StubBaseCommand:
    """Minimal Evennia Command stub for importing game commands."""

    def has_perm(self, srcobj):
        """Always allow command execution in tests."""
        return True


class _StubBaseCmdSet:
    """Minimal Evennia CmdSet stub that records added commands."""

    def __init__(self):
        """Initialize an empty command registry."""
        self.commands = []

    def at_cmdset_creation(self):
        """No-op parent hook for compatibility with super()."""
        return None

    def add(self, cmd):
        """Record added command instances or instantiate command classes."""
        if isinstance(cmd, type):
            cmd = cmd()
        self.commands.append(cmd)
        return cmd

    def remove(self, cmdname):
        """No-op remove for command names stripped from the live cmdset."""
        return None


class FakeDB:
    """Dict-backed proxy that mimics Evennia's ``obj.db`` access pattern."""

    def __init__(self, **values):
        """Store arbitrary DB attributes for test doubles."""
        object.__setattr__(self, "_values", dict(values))

    def __getattr__(self, key):
        """Return stored values or ``None`` for missing attributes."""
        return object.__getattribute__(self, "_values").get(key)

    def __setattr__(self, key, value):
        """Persist attribute writes into the backing store."""
        object.__getattribute__(self, "_values")[key] = value


class FakeItem:
    """Simple inventory/equipment item used by command rendering tests."""

    def __init__(self, item_id, key, **db_values):
        """Create a fake item with id, name, and DB attributes."""
        self.id = item_id
        self.key = key
        self.db = FakeDB(**db_values)

    def get_display_name(self, looker=None):
        """Return the display name used by the commands."""
        return self.key


class FakeCaller:
    """Character-like test double for command execution."""

    def __init__(
        self,
        key="Hina",
        db_values=None,
        computed_stats=None,
        inventory=None,
        capacity=10,
        equipped=None,
        location=None,
    ):
        """Create a fake caller with messages, stats, inventory, equipment, and location."""
        self.key = key
        self.db = FakeDB(**(db_values or {}))
        self._computed_stats = computed_stats or {}
        self._inventory = list(inventory or [])
        self._capacity = capacity
        self._equipped = dict(equipped or {})
        self.location = location
        self.contents = []
        self.messages = []
        self.equip_calls = []
        self.unequip_calls = []

    def equip_item(self, item, wear_style=None, quiet=False):
        """Record equip calls and mutate fake inventory/equipment enough for command tests."""
        self.equip_calls.append((item, wear_style, quiet))
        if item in self._inventory:
            self._inventory.remove(item)
        slot = getattr(item.db, "equip_slot", None) or "hat"
        self._equipped[slot] = item
        item.db.worn = wear_style or True
        item.db.wear_style = wear_style or ""
        return True

    def unequip_item(self, slot_or_item, quiet=False):
        """Record unequip calls."""
        self.unequip_calls.append((slot_or_item, quiet))
        return True

    def get_stat(self, name):
        """Return a computed stat value for the requested key."""
        return self._computed_stats.get(name, 0)

    def get_inventory(self):
        """Return the fake inventory list."""
        return list(self._inventory)

    def get_inventory_capacity(self):
        """Return the fake inventory capacity."""
        return self._capacity

    def get_all_equipped(self):
        """Return the fake equipment mapping."""
        return dict(self._equipped)

    def msg(self, text):
        """Capture command output sent to the caller."""
        self.messages.append(text)


def _install_evennia_stubs():
    """Install minimal Evennia/module stubs required by these imports."""

    importlib.import_module("commands")
    importlib.import_module("typeclasses")

    def register_module(module_name, **attrs):
        """Create a module, register it, and attach it to its parent package."""
        module = types.ModuleType(module_name)
        for attr_name, value in attrs.items():
            setattr(module, attr_name, value)
        sys.modules[module_name] = module

        if "." in module_name:
            parent_name, child_name = module_name.rsplit(".", 1)
            parent = sys.modules.get(parent_name)
            if parent is None:
                parent = importlib.import_module(parent_name)
            setattr(parent, child_name, module)
        return module

    register_module(
        "evennia",
        default_cmds=types.SimpleNamespace(
            CharacterCmdSet=_StubBaseCmdSet,
            AccountCmdSet=_StubBaseCmdSet,
            UnloggedinCmdSet=_StubBaseCmdSet,
            SessionCmdSet=_StubBaseCmdSet,
        ),
    )
    register_module("evennia.contrib")
    register_module("evennia.contrib.grid")
    register_module("evennia.contrib.grid.xyzgrid")
    register_module("evennia.contrib.base_systems")
    register_module("evennia.contrib.game_systems")
    register_module("evennia.contrib.game_systems.achievements")
    register_module("evennia.contrib.rpg")
    register_module("evennia.utils")
    register_module("evennia.utils.utils")
    register_module("evennia.commands")
    register_module("evennia.commands.command", Command=_StubBaseCommand)

    module_attrs = {
        "evennia.contrib.grid.extended_room": {
            "ExtendedRoomCmdSet": type("ExtendedRoomCmdSet", (), {})
        },
        "evennia.contrib.grid.mapbuilder": {
            "CmdMapBuilder": type("CmdMapBuilder", (), {})
        },
        "evennia.contrib.grid.simpledoor": {
            "SimpleDoorCmdSet": type("SimpleDoorCmdSet", (), {})
        },
        "evennia.contrib.grid.slow_exit": {
            "SlowExitCmdSet": type("SlowExitCmdSet", (), {})
        },
        "evennia.contrib.grid.ingame_map_display": {
            "MapDisplayCmdSet": type("MapDisplayCmdSet", (), {})
        },
        "evennia.contrib.grid.xyzgrid.commands": {
            "XYZGridCmdSet": type("XYZGridCmdSet", (), {})
        },
        "typeclasses.llm_npc": {"CmdLocalLLMTalk": type("CmdLocalLLMTalk", (), {})},
        "evennia.contrib.base_systems.building_menu": {
            "GenericBuildingCmd": type("GenericBuildingCmd", (), {})
        },
        "evennia.contrib.base_systems.ingame_reports": {
            "ReportsCmdSet": type("ReportsCmdSet", (), {})
        },
        "evennia.contrib.game_systems.achievements.achievements": {
            "CmdAchieve": type("CmdAchieve", (), {})
        },
        "evennia.contrib.game_systems.barter": {
            "CmdsetTrade": type("CmdsetTrade", (), {})
        },
        "evennia.contrib.game_systems.clothing": {
            "ClothedCharacterCmdSet": type("ClothedCharacterCmdSet", (), {})
        },
        "evennia.contrib.game_systems.containers": {
            "ContainerCmdSet": type("ContainerCmdSet", (), {})
        },
        "evennia.contrib.game_systems.gendersub": {
            "SetGender": type("SetGender", (), {})
        },
        "evennia.contrib.game_systems.storage": {
            "StorageCmdSet": type("StorageCmdSet", (), {})
        },
        "evennia.contrib.rpg.rpsystem": {
            "RPSystemCmdSet": type("RPSystemCmdSet", (), {})
        },
        "commands.account_character_commands": {
            "CmdCharacterRoster": type("CmdCharacterRoster", (), {}),
            "CmdChineseOOC": type("CmdChineseOOC", (), {}),
            "CmdChineseOOCLook": type("CmdChineseOOCLook", (), {}),
            "CmdLockedCharCreate": type("CmdLockedCharCreate", (), {}),
            "CmdLockedIC": type("CmdLockedIC", (), {}),
        },
        "commands.combat_admin": {"CmdAgentCombat": type("CmdAgentCombat", (), {})},
        "commands.combat_commands": {
            "CmdCombatAttack": type("CmdCombatAttack", (), {}),
            "CmdCombatSkill": type("CmdCombatSkill", (), {}),
            "CmdCombatFlee": type("CmdCombatFlee", (), {}),
            "CmdPick": type("CmdPick", (), {}),
            "CmdCast": type("CmdCast", (), {}),
        },
        "commands.combat_socket": {"CmdSocketGem": type("CmdSocketGem", (), {})},
        "commands.equipment_admin": {"CmdAgentWeapon": type("CmdAgentWeapon", (), {})},
        "commands.kingdom_admin": {"CmdKingdomAdmin": type("CmdKingdomAdmin", (), {})},
        "commands.npc_admin": {"CmdAgentNPC": type("CmdAgentNPC", (), {})},
        "commands.object_admin": {"CmdAgentObject": type("CmdAgentObject", (), {})},
        "commands.player_admin": {"CmdAgentPlayer": type("CmdAgentPlayer", (), {})},
        "commands.account_admin": {"CmdAgentAccount": type("CmdAgentAccount", (), {})},
        "commands.quest_admin": {"CmdAgentQuest": type("CmdAgentQuest", (), {})},
        "commands.room_admin": {"CmdAgentRoom": type("CmdAgentRoom", (), {})},
        "commands.world_admin": {"CmdAgentWorld": type("CmdAgentWorld", (), {})},
        "commands.magic_admin": {"CmdAgentMagic": type("CmdAgentMagic", (), {})},
    }

    for module_name, attrs in module_attrs.items():
        register_module(module_name, **attrs)


_install_evennia_stubs()
player_commands = importlib.import_module("commands.player_commands")
default_cmdsets = importlib.import_module("commands.default_cmdsets")

CmdStatus = player_commands.CmdStatus
CmdInventory = player_commands.CmdInventory
CmdEquipment = player_commands.CmdEquipment
CmdShop = player_commands.CmdShop
CmdBuy = player_commands.CmdBuy
CmdWearEquipment = player_commands.CmdWearEquipment
CmdRemoveEquipment = player_commands.CmdRemoveEquipment
CmdCoverEquipment = player_commands.CmdCoverEquipment
CmdUncoverEquipment = player_commands.CmdUncoverEquipment
CharacterCmdSet = default_cmdsets.CharacterCmdSet


class TestPlayerCommands(unittest.TestCase):
    """Exercise the player-facing command output and metadata."""

    def test_status_command_renders_core_panels(self):
        """Status should render vitals, token count, and computed stats."""
        caller = FakeCaller(
            db_values={
                "hp": 87,
                "max_hp": 100,
                "mp": 12,
                "max_mp": 30,
                "stamina": 55,
                "max_stamina": 80,
                "level": 3,
                "exp": 45,
                "max_exp": 100,
                "tokens": 9,
                "combat_state": "idle",
                "combat_status": "normal",
            },
            computed_stats={
                "str": 14,
                "def": 11,
                "spirit": 8,
                "intel": 13,
                "agility": 12,
                "stamina": 15,
                "spd": 16,
                "atk": 18,
            },
        )
        cmd = CmdStatus()
        cmd.caller = caller

        cmd.func()

        output = caller.messages[-1]
        self.assertIn("Hina 的狀態", output)
        self.assertIn("HP：87/100", output)
        self.assertIn("MP：12/30", output)
        self.assertIn("體力：55/80", output)
        self.assertIn("代幣：9", output)
        self.assertIn("力量：14", output)
        self.assertIn("攻擊：18", output)

    def test_inventory_command_lists_backpack_only(self):
        """Inventory should list backpack contents without treating equipped state as source of truth."""
        sword = FakeItem(101, "鋼鐵長劍")
        armor = FakeItem(102, "皮甲上衣")
        caller = FakeCaller(
            inventory=[sword, armor],
            equipped={"main_hand": sword},
            capacity=10,
        )
        cmd = CmdInventory()
        cmd.caller = caller

        cmd.func()

        output = caller.messages[-1]
        self.assertIn("Hina 的背包 (2/10)", output)
        self.assertIn("鋼鐵長劍", output)
        self.assertNotIn("已裝備", output)
        self.assertIn("皮甲上衣", output)

    def test_equipment_command_lists_equipped_and_empty_slots(self):
        """Equipment should show equipped items and explicit empty slots."""
        sword = FakeItem(201, "鋼鐵長劍", wear_style="發著冷光")
        caller = FakeCaller(
            equipped={"main_hand": sword, "hat": None, "top": None},
        )
        cmd = CmdEquipment()
        cmd.caller = caller

        cmd.func()

        output = caller.messages[-1]
        self.assertIn("Hina 的裝備", output)
        self.assertIn("主手武器", output)
        self.assertIn("鋼鐵長劍 (發著冷光)", output)
        self.assertIn("帽子", output)
        self.assertIn("|x空|n", output)

    def test_wear_command_equips_inventory_item_with_style(self):
        """Wear should find a backpack item and pass the style to equip_item."""
        hat = FakeItem(301, "皮帽", is_equipment=True, equip_slot="hat")
        caller = FakeCaller(inventory=[hat])
        cmd = CmdWearEquipment()
        cmd.caller = caller
        cmd.args = "皮帽 = 歪歪地戴著"
        cmd.lhs = "皮帽"
        cmd.rhs = "歪歪地戴著"

        cmd.func()

        self.assertEqual(caller.equip_calls[-1], (hat, "歪歪地戴著", False))

    def test_remove_command_delegates_equipped_item(self):
        """Remove should resolve equipped item names before delegating."""
        hat = FakeItem(302, "皮帽", is_equipment=True, equip_slot="hat")
        caller = FakeCaller(equipped={"hat": hat})
        cmd = CmdRemoveEquipment()
        cmd.caller = caller
        cmd.args = "皮帽"

        cmd.func()

        self.assertEqual(caller.unequip_calls[-1], (hat, False))

    def test_cover_and_uncover_commands_update_covered_by(self):
        """Cover/uncover should mutate local clothing metadata."""
        shirt = FakeItem(303, "襯衫", is_equipment=True, equip_slot="top")
        cloak = FakeItem(304, "披風", is_equipment=True, equip_slot="cloak")
        caller = FakeCaller(equipped={"top": shirt, "cloak": cloak})

        cover = CmdCoverEquipment()
        cover.caller = caller
        cover.args = "襯衫 with 披風"
        cover.lhs = "襯衫 with 披風"
        cover.rhs = None
        cover.func()
        self.assertEqual(shirt.db.covered_by, cloak)

        uncover = CmdUncoverEquipment()
        uncover.caller = caller
        uncover.args = "襯衫"
        uncover.func()
        self.assertIsNone(shirt.db.covered_by)

    def test_shop_command_uses_room_summary(self):
        """Shop should render the room stock summary returned by shop_tools."""
        shop_module = types.ModuleType("world.shop_tools")
        setattr(shop_module, "ShopSpecError", type("ShopSpecError", (Exception,), {}))
        setattr(
            shop_module,
            "summarize_room_shop_for_player",
            lambda room: f"{room.key} 商店清單\n1. 鐵劍 - 30 Token（剩餘：2）",
        )
        setattr(
            shop_module,
            "buy_from_room_shop",
            lambda caller, selection: {"message": f"你購買了 {selection}。"},
        )
        sys.modules["world.shop_tools"] = shop_module

        room = types.SimpleNamespace(key="迎賓大廳")
        caller = FakeCaller(location=room)
        cmd = CmdShop()
        cmd.caller = caller

        cmd.func()

        output = caller.messages[-1]
        self.assertIn("迎賓大廳 商店清單", output)
        self.assertIn("鐵劍 - 30 Token", output)

    def test_buy_command_reports_purchase_result(self):
        """Buy should surface the purchase result message from shop_tools."""
        shop_module = types.ModuleType("world.shop_tools")
        setattr(shop_module, "ShopSpecError", type("ShopSpecError", (Exception,), {}))
        setattr(shop_module, "summarize_room_shop_for_player", lambda room: "unused")
        setattr(
            shop_module,
            "buy_from_room_shop",
            lambda caller, selection: {"message": f"你購買了 {selection}。"},
        )
        sys.modules["world.shop_tools"] = shop_module

        caller = FakeCaller(location=types.SimpleNamespace(key="迎賓大廳"))
        cmd = CmdBuy()
        cmd.caller = caller
        cmd.args = "鐵劍"

        cmd.func()

        self.assertEqual(caller.messages[-1], "你購買了 鐵劍。")

    def test_command_metadata_exposes_expected_aliases(self):
        """Commands should keep the expected bilingual aliases."""
        self.assertEqual(CmdStatus.key, "status")
        self.assertIn("stat", CmdStatus.aliases)
        self.assertIn("狀態", CmdStatus.aliases)
        self.assertEqual(CmdInventory.key, "inventory")
        self.assertIn("背包", CmdInventory.aliases)
        self.assertEqual(CmdEquipment.key, "equipment")
        self.assertIn("裝備", CmdEquipment.aliases)
        self.assertEqual(CmdShop.key, "shop")
        self.assertIn("商店", CmdShop.aliases)
        self.assertEqual(CmdBuy.key, "buy")
        self.assertIn("購買", CmdBuy.aliases)
        self.assertEqual(CmdWearEquipment.key, "wear")
        self.assertIn("穿戴", CmdWearEquipment.aliases)
        self.assertEqual(CmdRemoveEquipment.key, "remove")
        self.assertIn("卸下", CmdRemoveEquipment.aliases)
        self.assertEqual(CmdCoverEquipment.key, "cover")
        self.assertIn("覆蓋", CmdCoverEquipment.aliases)
        self.assertEqual(CmdUncoverEquipment.key, "uncover")
        self.assertIn("揭開", CmdUncoverEquipment.aliases)


class TestPlayerCommandRegistration(unittest.TestCase):
    """Verify that player-facing commands are actually registered live."""

    def test_character_cmdset_registers_player_commands(self):
        """CharacterCmdSet should include all player-facing commands."""
        cmdset = CharacterCmdSet()
        cmdset.at_cmdset_creation()

        keys = sorted(
            cmd.key
            for cmd in cmdset.commands
            if hasattr(cmd, "key")
            and cmd.key
            in {
                "status",
                "inventory",
                "equipment",
                "wear",
                "remove",
                "cover",
                "uncover",
                "shop",
                "buy",
            }
        )
        self.assertEqual(
            keys,
            [
                "buy",
                "cover",
                "equipment",
                "inventory",
                "remove",
                "shop",
                "status",
                "uncover",
                "wear",
            ],
        )


if __name__ == "__main__":
    unittest.main()
