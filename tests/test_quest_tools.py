"""Unit tests for world/quest_tools.py — quest management."""

from __future__ import annotations

import importlib
import sys
import types
import unittest
from unittest.mock import MagicMock, patch
from types import SimpleNamespace


_FAKE_CHARS = {}


def _install_stubs():
    evennia = types.ModuleType("evennia")

    def search_object(key, exact=True):
        return [_FAKE_CHARS[key]] if key in _FAKE_CHARS else []

    evennia.search_object = search_object
    sys.modules["evennia"] = evennia


_install_stubs()
quest = importlib.import_module("world.quest_tools")
QuestSpecError = quest.QuestSpecError


def _make_char(key="Hero", active_quests=None, completed_quests=None):
    char = SimpleNamespace(
        key=key,
        db=SimpleNamespace(
            active_quests=list(active_quests or []),
            completed_quests=list(completed_quests or []),
        ),
        save=MagicMock(),
    )
    _FAKE_CHARS[key] = char
    return char


class TestQuestTools(unittest.TestCase):
    def setUp(self):
        _FAKE_CHARS.clear()

    def test_give_quest_assigns_quest(self):
        char = _make_char("Hero")
        result = quest.give_quest("Hero", "slay_dragon")
        self.assertIn("slay_dragon", char.db.active_quests)
        self.assertIn("已將任務", result["message"])

    def test_give_quest_rejects_duplicate(self):
        char = _make_char("Hero", active_quests=["slay_dragon"])
        with self.assertRaises(QuestSpecError) as err:
            quest.give_quest("Hero", "slay_dragon")
        self.assertIn("已經擁有", str(err.exception))

    def test_complete_quest_moves_to_completed(self):
        char = _make_char("Hero", active_quests=["slay_dragon"])
        result = quest.complete_quest("Hero", "slay_dragon")
        self.assertNotIn("slay_dragon", char.db.active_quests)
        self.assertIn("slay_dragon", char.db.completed_quests)
        self.assertIn("已完成", result["message"])

    def test_complete_quest_rejects_if_not_active(self):
        char = _make_char("Hero")
        with self.assertRaises(QuestSpecError) as err:
            quest.complete_quest("Hero", "unknown_quest")
        self.assertIn("沒有進行中", str(err.exception))

    def test_summarize_quests(self):
        char = _make_char("Hero", active_quests=["q1"], completed_quests=["q2"])
        result = quest.summarize_quests("Hero")
        self.assertIn("Hero", result)
        self.assertIn("q1", result)
        self.assertIn("q2", result)

    def test_give_quest_invalid_char_raises(self):
        with self.assertRaises(QuestSpecError):
            quest.give_quest("NonExistent", "quest1")


if __name__ == "__main__":
    unittest.main()
