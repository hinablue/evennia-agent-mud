"""Unit tests for world/combat_tools.py — GM combat control helpers."""

from __future__ import annotations

import importlib
import sys
import types
import unittest
from unittest.mock import MagicMock
from types import SimpleNamespace


_FAKE_OBJS = {}


def _install_stubs():
    evennia = types.ModuleType("evennia")

    def search_object(key, exact=True):
        return [_FAKE_OBJS[key]] if key in _FAKE_OBJS else []

    evennia.search_object = search_object
    sys.modules["evennia"] = evennia


_install_stubs()
ct = importlib.import_module("world.combat_tools")
CombatSpecError = ct.CombatSpecError


def _make_obj(key="Goblin", **db_kw):
    obj = SimpleNamespace(key=key, db=SimpleNamespace(**db_kw), save=MagicMock())
    _FAKE_OBJS[key] = obj
    return obj


class TestCombatTools(unittest.TestCase):
    def setUp(self):
        _FAKE_OBJS.clear()

    def test_stop_combat_sets_idle(self):
        obj = _make_obj("Goblin", combat_state="fighting")
        result = ct.stop_combat("Goblin")
        self.assertEqual(obj.db.combat_state, "idle")
        self.assertIn("已強行終止", result["message"])

    def test_force_win_sets_victory(self):
        obj = _make_obj("Goblin", combat_result="pending")
        result = ct.force_win("Goblin")
        self.assertEqual(obj.db.combat_result, "victory")
        self.assertIn("獲勝", result["message"])

    def test_set_npc_state(self):
        obj = _make_obj("Goblin", ai_state="idle")
        result = ct.set_npc_state("Goblin", "patrol")
        self.assertEqual(obj.db.ai_state, "patrol")
        self.assertIn("AI 狀態", result["message"])

    def test_stop_combat_missing_raises(self):
        with self.assertRaises(CombatSpecError):
            ct.stop_combat("NonExistent")

    def test_set_npc_state_missing_raises(self):
        with self.assertRaises(CombatSpecError):
            ct.set_npc_state("NonExistent", "idle")


if __name__ == "__main__":
    unittest.main()
