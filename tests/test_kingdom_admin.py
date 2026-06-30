"""Tests for the @agentkingdom admin command."""

from __future__ import annotations

import sys
import unittest
from types import ModuleType
from unittest.mock import patch

if "commands.command" not in sys.modules:
    commands_command = ModuleType("commands.command")

    class MuxCommand:
        """Minimal MuxCommand base stub."""

    commands_command.MuxCommand = MuxCommand
    sys.modules["commands.command"] = commands_command

if "world.kingdom" not in sys.modules:
    kingdom_tools = ModuleType("world.kingdom")
    kingdom_tools.create_kingdom = lambda *args, **kwargs: None
    kingdom_tools.delete_kingdom = lambda *args, **kwargs: None
    kingdom_tools.get_kingdom_by_name = lambda *args, **kwargs: None
    kingdom_tools.get_kingdom_status = lambda *args, **kwargs: None
    kingdom_tools.list_kingdoms = lambda *args, **kwargs: []
    kingdom_tools.rename_kingdom = lambda *args, **kwargs: None
    kingdom_tools.resolve_caller_kingdom = lambda *args, **kwargs: None
    kingdom_tools.set_kingdom_entrance = lambda *args, **kwargs: None
    kingdom_tools.set_kingdom_quota = lambda *args, **kwargs: None
    sys.modules["world.kingdom"] = kingdom_tools

if "evennia" not in sys.modules:
    evennia = ModuleType("evennia")
    evennia.search_object = lambda *args, **kwargs: []
    sys.modules["evennia"] = evennia

from commands.kingdom_admin import CmdKingdomAdmin


class FakeCaller:
    """Collects command output for assertions."""

    def __init__(self, permissions=None):
        self.messages = []
        self.account = type(
            "FakeAccount",
            (),
            {
                "permissions": type(
                    "FakePerms",
                    (),
                    {"all": lambda self: list(permissions or [])},
                )()
            },
        )()

    def msg(self, text):
        self.messages.append(text)


class CmdKingdomAdminTests(unittest.TestCase):
    """Command routing and permission tests for @agentkingdom."""

    def _make_cmd(self, permissions=None):
        cmd = object.__new__(CmdKingdomAdmin)
        cmd.caller = FakeCaller(permissions=permissions)
        cmd.switches = []
        cmd.args = ""
        cmd.lhs = ""
        cmd.rhs = None
        return cmd

    def test_command_key_and_aliases(self):
        self.assertEqual(CmdKingdomAdmin.key, "@agentkingdom")
        self.assertIn("@kingdom", CmdKingdomAdmin.aliases)

    def test_help_without_switches(self):
        cmd = self._make_cmd(permissions=["King"])

        cmd.func()

        self.assertIn("@agentkingdom", cmd.caller.messages[-1])
        self.assertIn("/countryrename", cmd.caller.messages[-1])

    def test_king_can_use_countries_switch(self):
        cmd = self._make_cmd(permissions=["King"])
        cmd.switches = ["countries"]
        fake_kingdom = type("FakeKingdom", (), {"key": "Astra"})()

        with patch(
            "commands.kingdom_admin.resolve_caller_kingdom", return_value=fake_kingdom
        ), patch(
            "commands.kingdom_admin.get_kingdom_status",
            return_value={
                "name": "Astra",
                "king": "Arthur",
                "entrance_room": "Gate",
                "quota": 10,
                "used": 3,
                "remaining": 7,
                "nationality_tag": "Astra",
            },
        ):
            cmd.func()

        self.assertIn("Astra", cmd.caller.messages[-1])
        self.assertIn("Arthur", cmd.caller.messages[-1])

    def test_king_can_use_countryrename_switch(self):
        cmd = self._make_cmd(permissions=["King"])
        cmd.switches = ["countryrename"]
        cmd.args = "新亞斯特拉"
        fake_kingdom = type("FakeKingdom", (), {"key": "Astra"})()

        with patch(
            "commands.kingdom_admin.resolve_caller_kingdom", return_value=fake_kingdom
        ), patch(
            "commands.kingdom_admin.rename_kingdom",
            return_value={"message": "已將國名從 `Astra` 改為 `新亞斯特拉`。"},
        ) as renamer:
            cmd.func()

        renamer.assert_called_once_with(fake_kingdom, "新亞斯特拉")
        self.assertEqual(
            cmd.caller.messages[-1], "已將國名從 `Astra` 改為 `新亞斯特拉`。"
        )

    def test_king_cannot_use_countrycreate_switch(self):
        cmd = self._make_cmd(permissions=["King"])
        cmd.switches = ["countrycreate"]
        cmd.args = "Arthur=Astra,Gate,10"

        cmd.func()

        self.assertIn("King 只能使用", cmd.caller.messages[-1])
        self.assertIn("@agentkingdom/countries", cmd.caller.messages[-1])

    def test_admin_countryquota_routes_to_helper(self):
        cmd = self._make_cmd(permissions=["Admin"])
        cmd.switches = ["countryquota"]
        cmd.lhs = "Astra"
        cmd.rhs = "20"
        fake_kingdom = type("FakeKingdom", (), {"key": "Astra"})()

        with patch(
            "commands.kingdom_admin.get_kingdom_by_name", return_value=fake_kingdom
        ), patch(
            "commands.kingdom_admin.set_kingdom_quota",
            return_value={"message": "已更新額度"},
        ) as setter:
            cmd.func()

        setter.assert_called_once_with(fake_kingdom, "20")
        self.assertEqual(cmd.caller.messages[-1], "已更新額度")

    def test_admin_countrycreate_routes_to_helper(self):
        cmd = self._make_cmd(permissions=["Admin"])
        cmd.switches = ["countrycreate"]
        cmd.args = "Arthur=Astra,Gate,10"
        fake_king = type("FakeKing", (), {"key": "Arthur"})()
        fake_room = type("FakeRoom", (), {"key": "Gate"})()
        fake_kingdom = type("FakeKingdom", (), {"key": "Astra"})()

        with patch(
            "evennia.search_object", side_effect=[[fake_king], [fake_room]]
        ), patch(
            "commands.kingdom_admin.create_kingdom", return_value=fake_kingdom
        ) as creator:
            cmd.func()

        creator.assert_called_once_with(fake_king, "Astra", fake_room, 10)
        self.assertEqual(cmd.caller.messages[-1], "已建立國家：Astra")


if __name__ == "__main__":
    unittest.main()
