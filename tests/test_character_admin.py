"""Tests for @agentchar account-character admin helpers and routing."""

from __future__ import annotations

import importlib
import sys
import unittest
from pathlib import Path
from types import ModuleType, SimpleNamespace
from unittest.mock import MagicMock, patch

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


class _RelationList:
    """Minimal relation wrapper mimicking Evennia's character handler."""

    def __init__(self, items=None):
        """Store mutable items for ``all/add/remove`` access."""
        self._items = list(items or [])

    def all(self):
        """Return the current related objects."""
        return list(self._items)

    def add(self, obj):
        """Append a related object."""
        self._items.append(obj)

    def remove(self, obj):
        """Remove a related object if present."""
        self._items.remove(obj)

    def count(self):
        """Return relation size."""
        return len(self._items)


class _AliasHandler:
    """Minimal alias handler used by fake Character objects."""

    def __init__(self, aliases=None):
        """Store aliases for ``all`` access."""
        self._aliases = list(aliases or [])

    def all(self):
        """Return aliases as strings."""
        return list(self._aliases)


class _NdbProxy:
    """Simple namespace-like container for ``obj.ndb`` values."""

    pass


def _fake_character(key, char_id, desc="", aliases=None, location=None, home=None):
    """Build a fake Evennia-like character object for helper tests."""

    return SimpleNamespace(
        key=key,
        id=char_id,
        db=SimpleNamespace(desc=desc),
        aliases=_AliasHandler(aliases=aliases),
        location=location,
        home=home,
        delete=MagicMock(return_value=True),
    )


def _install_evennia_stubs():
    """Install minimal Evennia stubs needed by character admin tests."""

    evennia = ModuleType("evennia")
    evennia.search_account = MagicMock(return_value=[])
    sys.modules["evennia"] = evennia

    utils_utils = ModuleType("evennia.utils.utils")
    utils_utils.make_iter = lambda value: (
        value if isinstance(value, (list, tuple, set)) else [value]
    )
    sys.modules["evennia.utils.utils"] = utils_utils

    commands_command = ModuleType("commands.command")

    class MuxCommand:
        """Minimal MuxCommand base stub."""

    commands_command.MuxCommand = MuxCommand
    sys.modules["commands.command"] = commands_command


_install_evennia_stubs()

sys.modules.pop("commands.character_admin", None)
sys.modules.pop("world.character_tools", None)

character_tools = importlib.import_module("world.character_tools")
character_admin = importlib.import_module("commands.character_admin")

CharacterAdminError = character_tools.CharacterAdminError
CmdAgentChar = character_admin.CmdAgentChar


class FakeCaller:
    """Collect command output for assertions."""

    def __init__(self):
        """Initialize an empty message log and fake session."""
        self.messages = []
        self.sessions = SimpleNamespace(all=lambda: [SimpleNamespace(address="127.0.0.1")])

    def msg(self, text):
        """Capture text sent by the command."""
        self.messages.append(text)


class CharacterToolsTests(unittest.TestCase):
    """Unit tests for ``world.character_tools``."""

    def test_summarize_account_characters_marks_primary(self):
        """Summaries should highlight the primary character in the roster."""

        room = SimpleNamespace(key="迎賓大廳")
        hero = _fake_character("Hero", 101, desc="主角", aliases=["旅人"], location=room, home=room)
        mage = _fake_character("Mage", 102, desc="法師", aliases=["術士"], location=None, home=room)
        account = SimpleNamespace(
            key="hinablue",
            characters=_RelationList([hero, mage]),
            db=SimpleNamespace(primary_character=hero, _last_puppet=hero),
        )

        with patch.object(character_tools, "_get_account_or_error", return_value=account):
            summary = character_tools.summarize_account_characters("hinablue")

        self.assertIn("Account：hinablue", summary)
        self.assertIn("- Hero｜#101｜目前位置：迎賓大廳｜home：迎賓大廳｜aliases：旅人｜主角色", summary)
        self.assertIn("- Mage｜#102｜目前位置：無｜home：迎賓大廳｜aliases：術士", summary)

    def test_create_account_character_delegates_to_evennia_factory(self):
        """Character creation should use ``account.create_character`` directly."""

        account = SimpleNamespace(
            key="hinablue",
            characters=_RelationList(),
            db=SimpleNamespace(primary_character=None, _last_puppet=None),
            create_character=MagicMock(),
            save=MagicMock(),
        )
        created = _fake_character("Nova", 201, desc="新角色")
        account.create_character.return_value = (created, [])

        with patch.object(character_tools, "_get_account_or_error", return_value=account):
            result = character_tools.create_account_character(
                "hinablue",
                "Nova",
                desc="新角色",
                caller=FakeCaller(),
            )

        account.create_character.assert_called_once_with(
            key="Nova",
            description="新角色",
            ip="127.0.0.1",
        )
        self.assertIs(account.db.primary_character, created)
        self.assertIs(account.db._last_puppet, created)
        account.save.assert_called_once_with()
        self.assertIn("已為 Account `hinablue` 建立 Character `Nova`", result["message"])

    def test_delete_account_character_repoints_primary_when_needed(self):
        """Deleting the primary character should advance primary pointers."""

        hero = _fake_character("Hero", 101)
        mage = _fake_character("Mage", 102)
        relation = _RelationList([hero, mage])
        account = SimpleNamespace(
            key="hinablue",
            characters=relation,
            db=SimpleNamespace(primary_character=hero, _last_puppet=hero),
            save=MagicMock(),
        )

        with patch.object(character_tools, "_get_account_or_error", return_value=account):
            result = character_tools.delete_account_character("hinablue", "Hero")

        hero.delete.assert_called_once_with()
        self.assertEqual(relation.all(), [mage])
        self.assertIs(account.db.primary_character, mage)
        self.assertIs(account.db._last_puppet, mage)
        account.save.assert_called_once_with()
        self.assertIn("已從 Account `hinablue` 刪除 Character `Hero`", result["message"])
        self.assertIn("新的主角色：`Mage`", result["message"])

    def test_delete_account_character_rejects_missing_match(self):
        """Deleting an unknown roster entry should raise a clear error."""

        hero = _fake_character("Hero", 101)
        account = SimpleNamespace(
            key="hinablue",
            characters=_RelationList([hero]),
            db=SimpleNamespace(primary_character=hero, _last_puppet=hero),
        )

        with patch.object(character_tools, "_get_account_or_error", return_value=account):
            with self.assertRaises(CharacterAdminError) as err:
                character_tools.delete_account_character("hinablue", "Mage")

        self.assertIn("找不到角色：Mage", str(err.exception))


class CmdAgentCharTests(unittest.TestCase):
    """Command routing tests for ``@agentchar``."""

    def _make_cmd(self):
        """Construct a minimally initialized command instance."""
        cmd = object.__new__(CmdAgentChar)
        cmd.caller = FakeCaller()
        cmd.switches = []
        cmd.args = ""
        cmd.lhs = ""
        cmd.rhs = None
        return cmd

    def test_func_defaults_to_list(self):
        """Bare ``@agentchar`` should dispatch to the roster summary."""

        cmd = self._make_cmd()
        cmd.args = "hinablue"

        with patch.object(
            character_admin,
            "summarize_account_characters",
            return_value="角色清單",
        ) as summary:
            cmd.func()

        summary.assert_called_once_with("hinablue")
        self.assertEqual(cmd.caller.messages[-1], "角色清單")

    def test_func_routes_create_switch(self):
        """The public command entrypoint should dispatch /create correctly."""

        cmd = self._make_cmd()
        cmd.switches = ["create"]
        cmd.lhs = "hinablue"
        cmd.rhs = "Nova|新角色描述"

        with patch.object(
            character_admin,
            "create_account_character",
            return_value={"message": "建立完成"},
        ) as creator:
            cmd.func()

        creator.assert_called_once()
        self.assertEqual(creator.call_args.args[:2], ("hinablue", "Nova"))
        self.assertEqual(creator.call_args.kwargs["desc"], "新角色描述")
        self.assertEqual(cmd.caller.messages[-1], "建立完成")

    def test_func_routes_delete_switch(self):
        """The public command entrypoint should dispatch /delete correctly."""

        cmd = self._make_cmd()
        cmd.switches = ["delete"]
        cmd.lhs = "hinablue"
        cmd.rhs = "Hero"

        with patch.object(
            character_admin,
            "delete_account_character",
            return_value={"message": "刪除完成"},
        ) as deleter:
            cmd.func()

        deleter.assert_called_once_with("hinablue", "Hero")
        self.assertEqual(cmd.caller.messages[-1], "刪除完成")


if __name__ == "__main__":
    unittest.main()
