"""Tests for the @agentworld admin command."""

from __future__ import annotations

import unittest
from unittest.mock import patch

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
            "xyzgrid": {"rooms": 21, "exits": 36, "zcoord": "agent-hub", "spawned": True},
        }

        with patch("commands.world_admin.force_rebuild_agent_world", return_value=fake_result):
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


if __name__ == "__main__":
    unittest.main()
