"""Unit tests for commands/combat_socket.py — CmdSocketGem."""

from __future__ import annotations

import importlib
import sys
import types
import unittest
from types import SimpleNamespace


class FakeGemSpecError(ValueError):
    """Stub GemSpecError."""


class FakeGem:
    """Stub persistent Gem object."""

    def __init__(self, gem_id, name, stats, enabled=True):
        self.key = gem_id
        self.db = SimpleNamespace(
            gem_id=gem_id,
            display_name=name,
            stats=dict(stats),
            enabled=enabled,
        )


FAKE_GEMS = {
    "ruby": FakeGem("ruby", "紅寶石", {"str": 3, "stamina": 1}),
    "sapphire": FakeGem("sapphire", "藍寶石", {"intel": 3, "spirit": 1}),
    "emerald": FakeGem("emerald", "綠寶石", {"agility": 3, "spd": 1}),
}


def _install_stubs():
    evennia = types.ModuleType("evennia")

    class Command:
        pass

    evennia.Command = Command
    sys.modules["evennia"] = evennia

    gem_tools = types.ModuleType("world.gem_tools")
    setattr(gem_tools, "GemSpecError", FakeGemSpecError)

    def get_gem_by_id(gem_id, require_enabled=False):
        gem = FAKE_GEMS.get(gem_id)
        if not gem or (require_enabled and not gem.db.enabled):
            raise FakeGemSpecError(gem_id)
        return gem

    def gem_ids(enabled_only=False):
        return sorted(
            gem_id
            for gem_id, gem in FAKE_GEMS.items()
            if not enabled_only or gem.db.enabled
        )

    setattr(gem_tools, "get_gem_by_id", get_gem_by_id)
    setattr(gem_tools, "gem_ids", gem_ids)
    sys.modules["world.gem_tools"] = gem_tools


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
    def test_socket_ruby_slot1_stores_gem_reference(self):
        caller = FakeCaller()
        cmd = _make_cmd(caller, "ruby 1")
        cmd.func()
        self.assertIs(caller.db.sockets["slot1"], FAKE_GEMS["ruby"])
        self.assertTrue(any("紅寶石" in m for m in caller.messages))

    def test_socket_sapphire_slot2(self):
        caller = FakeCaller()
        cmd = _make_cmd(caller, "sapphire 2")
        cmd.func()
        self.assertIs(caller.db.sockets["slot2"], FAKE_GEMS["sapphire"])

    def test_socket_emerald_slot3(self):
        caller = FakeCaller()
        cmd = _make_cmd(caller, "emerald 3")
        cmd.func()
        self.assertIs(caller.db.sockets["slot3"], FAKE_GEMS["emerald"])

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
