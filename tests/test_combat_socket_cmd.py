"""Unit tests for commands/combat_socket.py — CmdSocketGem."""

from __future__ import annotations

import importlib
import sys
import types
import unittest
from types import SimpleNamespace


def _install_stubs():
    evennia = types.ModuleType("evennia")

    class Command:
        pass

    evennia.Command = Command
    sys.modules["evennia"] = evennia


_install_stubs()
combat_socket = importlib.import_module("commands.combat_socket")
CmdSocketGem = combat_socket.CmdSocketGem


class FakeCaller:
    def __init__(self, max_sockets=3, sockets=None):
        self.messages = []
        self.db = SimpleNamespace(
            max_sockets=max_sockets,
            sockets=dict(sockets) if sockets else None,
        )

    def msg(self, text):
        self.messages.append(text)


def _make_cmd(caller, args_str):
    cmd = object.__new__(CmdSocketGem)
    cmd.caller = caller
    cmd.args = args_str
    return cmd


class TestCmdSocketGem(unittest.TestCase):
    def test_socket_ruby_slot1(self):
        caller = FakeCaller()
        cmd = _make_cmd(caller, "ruby 1")
        cmd.func()
        self.assertEqual(caller.db.sockets["slot1"]["name"], "紅寶石")
        self.assertTrue(any("紅寶石" in m for m in caller.messages))

    def test_socket_sapphire_slot2(self):
        caller = FakeCaller()
        cmd = _make_cmd(caller, "sapphire 2")
        cmd.func()
        self.assertEqual(caller.db.sockets["slot2"]["name"], "藍寶石")

    def test_socket_emerald_slot3(self):
        caller = FakeCaller()
        cmd = _make_cmd(caller, "emerald 3")
        cmd.func()
        self.assertEqual(caller.db.sockets["slot3"]["name"], "綠寶石")

    def test_invalid_gem_rejected(self):
        caller = FakeCaller()
        cmd = _make_cmd(caller, "diamond 1")
        cmd.func()
        self.assertTrue(any("找不到" in m for m in caller.messages))

    def test_out_of_range_slot_rejected(self):
        caller = FakeCaller()
        cmd = _make_cmd(caller, "ruby 5")
        cmd.func()
        self.assertTrue(any("範圍" in m for m in caller.messages))

    def test_non_numeric_slot_rejected(self):
        caller = FakeCaller()
        cmd = _make_cmd(caller, "ruby abc")
        cmd.func()
        self.assertTrue(any("數字" in m for m in caller.messages))

    def test_missing_args_shows_usage(self):
        caller = FakeCaller()
        cmd = _make_cmd(caller, "ruby")
        cmd.func()
        self.assertTrue(any("用法" in m for m in caller.messages))


if __name__ == "__main__":
    unittest.main()
