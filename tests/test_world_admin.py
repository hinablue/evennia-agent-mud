"""Tests for the @agentworld admin command."""

from __future__ import annotations

import unittest
from types import ModuleType
from unittest.mock import patch

import sys

if "commands.command" not in sys.modules:
    commands_command = ModuleType("commands.command")

    class MuxCommand:
        """Minimal MuxCommand base stub."""

    commands_command.MuxCommand = MuxCommand
    sys.modules["commands.command"] = commands_command

if "world.agent_world" not in sys.modules:
    agent_world = ModuleType("world.agent_world")

    class WorldSpecError(ValueError):
        """Minimal world error stub."""

    agent_world.WorldSpecError = WorldSpecError
    agent_world.add_live_exit = lambda *args, **kwargs: None
    agent_world.add_live_room_detail = lambda *args, **kwargs: None
    agent_world.add_live_scenery = lambda *args, **kwargs: None
    agent_world.analyze_agent_world = lambda *args, **kwargs: None
    agent_world.build_agent_world = lambda *args, **kwargs: None
    agent_world.create_live_room = lambda *args, **kwargs: None
    agent_world.force_rebuild_agent_world = lambda *args, **kwargs: None
    agent_world.is_spec_room = lambda room_name: True
    agent_world.move_live_entity = lambda *args, **kwargs: None
    agent_world.render_analysis = lambda *args, **kwargs: None
    agent_world.summarize_agent_world = lambda *args, **kwargs: None
    sys.modules["world.agent_world"] = agent_world

if "world.account_tools" not in sys.modules:
    account_tools = ModuleType("world.account_tools")

    class AccountSpecError(ValueError):
        """Minimal account error stub."""

    account_tools.AccountSpecError = AccountSpecError
    account_tools.set_account_role = lambda *args, **kwargs: None
    sys.modules["world.account_tools"] = account_tools

from commands.world_admin import CmdAgentWorld


class FakeCaller:
    """Collects command output for assertions."""

    def __init__(self):
        self.messages = []

    def msg(self, text):
        self.messages.append(text)


class CmdAgentWorldTests(unittest.TestCase):
    """Command routing and reporting tests."""

    def _make_cmd(self):
        cmd = object.__new__(CmdAgentWorld)
        cmd.caller = FakeCaller()
        cmd.switches = []
        cmd.args = ""
        cmd.lhs = ""
        cmd.rhs = None
        cmd.lhslist = []
        cmd.rhslist = []
        cmd.arglist = []
        return cmd

    def test_handle_force_rebuild_reports_summary(self):
        """The forcerebuild report should include both builder and XYZGrid stats."""

        cmd = self._make_cmd()
        fake_result = {
            "rooms_deleted": 21,
            "exits_deleted": 25,
            "objects_deleted": 63,
            "objects_preserved": 1,
            "objects_relocated_after_rebuild": 0,
            "fallback_room": "迎賓大廳",
            "build": {"rooms_total": 21, "rooms_created": 21, "exits_created": 50},
            "xyzgrid": {
                "rooms": 21,
                "exits": 36,
                "zcoord": "agent-hub",
                "spawned": True,
            },
        }

        with patch(
            "commands.world_admin.force_rebuild_agent_world", return_value=fake_result
        ):
            cmd._handle_force_rebuild()

        output = cmd.caller.messages[-1]
        self.assertIn("世界強制重建完成", output)
        self.assertIn("刪除房間：21", output)
        self.assertIn("Builder 新增出口：50", output)
        self.assertIn("XYZGrid zcoord：agent-hub", output)

    def test_func_routes_forcerebuild_switch(self):
        """The public command entrypoint should dispatch /forcerebuild correctly."""

        cmd = self._make_cmd()
        cmd.switches = ["forcerebuild"]

        with patch.object(cmd, "_handle_force_rebuild") as handler:
            cmd.func()

        handler.assert_called_once_with()

    def test_func_routes_role_switch(self):
        """The role switch should delegate to hierarchy role assignment."""

        cmd = self._make_cmd()
        cmd.switches = ["role"]
        cmd.lhs = "hinablue"
        cmd.rhs = "GM"

        with patch("commands.world_admin.set_account_role", return_value={"message": "已設為 GM"}) as setter:
            cmd.func()

        setter.assert_called_once_with("hinablue", "GM")
        self.assertEqual(cmd.caller.messages[-1], "已設為 GM")


if __name__ == "__main__":
    unittest.main()
