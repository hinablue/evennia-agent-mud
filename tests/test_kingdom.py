"""Unit tests for world/kingdom.py — Kingdom class and module-level tools."""

from __future__ import annotations

import importlib
import sys
import types
import unittest
from unittest.mock import MagicMock, patch

from types import SimpleNamespace


# ---------------------------------------------------------------------------
# Evennia stubs
# ---------------------------------------------------------------------------

def _install_stubs():
    evennia = types.ModuleType("evennia")
    evennia.search_object = MagicMock(return_value=[])
    evennia.create_object = MagicMock()
    sys.modules["evennia"] = evennia

    utils_utils = types.ModuleType("evennia.utils.utils")
    utils_utils.inherits_from = lambda obj, path: True
    sys.modules["evennia.utils.utils"] = utils_utils

    utils_pkg = types.ModuleType("evennia.utils")
    sys.modules["evennia.utils"] = utils_pkg
    utils_pkg.utils = utils_utils

    objects_models = types.ModuleType("evennia.objects.models")
    objects_models.ObjectDB = SimpleNamespace(objects=SimpleNamespace(all=lambda: []))
    sys.modules["evennia.objects.models"] = objects_models

    scripts_mod = types.ModuleType("evennia.scripts.scripts")
    scripts_mod.DefaultScript = type("DefaultScript", (), {"delete": lambda self: None, "save": lambda self: None})
    sys.modules["evennia.scripts.scripts"] = scripts_mod

    evennia.DefaultScript = scripts_mod.DefaultScript

    commands_command = types.ModuleType("commands.command")
    commands_command.MuxCommand = type("MuxCommand", (), {})
    sys.modules["commands.command"] = commands_command

    typeclasses_rooms = types.ModuleType("typeclasses.rooms")
    typeclasses_rooms.Room = type("Room", (), {})
    sys.modules["typeclasses.rooms"] = typeclasses_rooms

    typeclasses_exits = types.ModuleType("typeclasses.exits")
    typeclasses_exits.Exit = type("Exit", (), {})
    sys.modules["typeclasses.exits"] = typeclasses_exits

    typeclasses_characters = types.ModuleType("typeclasses.characters")
    typeclasses_characters.Character = type("Character", (), {"objects": SimpleNamespace(filter=lambda **k: [])})
    sys.modules["typeclasses.characters"] = typeclasses_characters


_install_stubs()
kingdom_mod = importlib.import_module("world.kingdom")
Kingdom = kingdom_mod.Kingdom


# ---------------------------------------------------------------------------
# Fake helpers
# ---------------------------------------------------------------------------

class FakeDB:
    """Dict-backed .db replacement."""
    def __init__(self, **kw):
        object.__setattr__(self, "_store", dict(kw))

    def __getattr__(self, key):
        return object.__getattribute__(self, "_store").get(key)

    def __setattr__(self, key, value):
        object.__getattribute__(self, "_store")[key] = value


class FakeTags:
    """Minimal tag handler."""
    def __init__(self):
        self._tags = set()

    def add(self, key, category=None):
        self._tags.add((key, category))

    def has(self, key, category=None):
        return (key, category) in self._tags

    def all(self, category=None):
        if category:
            return [k for k, c in self._tags if c == category]
        return list(self._tags)


def _make_kingdom(key="Astra", room_quota=10, rooms_created=0):
    """Build a fake Kingdom instance for unit tests."""
    k = object.__new__(Kingdom)
    k.key = key
    k.db = FakeDB(
        king=None,
        gm_continent_rooms=[],
        entrance_room=None,
        room_quota=room_quota,
        rooms_created=rooms_created,
        nationality_tag=key,
    )
    return k


def _make_char(key="KingArthur", is_king=False):
    """Build a fake King character."""
    char = SimpleNamespace(
        key=key,
        db=FakeDB(is_king=is_king, kingdom=None, nationality=""),
        save=MagicMock(),
        home=None,
    )
    return char


def _make_room(key="Throne_Room", room_id=1):
    """Build a fake room."""
    room = SimpleNamespace(
        key=key,
        id=room_id,
        tags=FakeTags(),
        save=MagicMock(),
    )
    return room


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestKingdomClass(unittest.TestCase):
    """Test Kingdom (DefaultScript) instance methods."""

    def test_at_script_creation_sets_defaults(self):
        k = _make_kingdom("")
        # Simulate at_script_creation
        k.key = ""
        k.db.king = None
        k.db.gm_continent_rooms = []
        k.db.entrance_room = None
        k.db.room_quota = 0
        k.db.rooms_created = 0
        k.db.nationality_tag = ""

        self.assertIsNone(k.db.king)
        self.assertEqual(k.db.room_quota, 0)

    def test_get_quota_remaining(self):
        k = _make_kingdom(room_quota=10, rooms_created=3)
        self.assertEqual(k.get_quota_remaining(), 7)

    def test_get_quota_remaining_floor_zero(self):
        k = _make_kingdom(room_quota=5, rooms_created=8)
        self.assertEqual(k.get_quota_remaining(), 0)

    def test_can_create_room_true(self):
        k = _make_kingdom(room_quota=5, rooms_created=2)
        self.assertTrue(k.can_create_room())

    def test_can_create_room_false(self):
        k = _make_kingdom(room_quota=5, rooms_created=5)
        self.assertFalse(k.can_create_room())

    def test_increment_rooms_created(self):
        k = _make_kingdom(rooms_created=3)
        k.increment_rooms_created()
        self.assertEqual(k.db.rooms_created, 4)

    def test_decrement_rooms_created(self):
        k = _make_kingdom(rooms_created=3)
        k.decrement_rooms_created()
        self.assertEqual(k.db.rooms_created, 2)

    def test_decrement_rooms_created_floor_zero(self):
        k = _make_kingdom(rooms_created=0)
        k.decrement_rooms_created()
        self.assertEqual(k.db.rooms_created, 0)

    def test_set_king(self):
        k = _make_kingdom()
        king = _make_char()
        k.set_king(king)
        self.assertEqual(k.db.king, king)
        self.assertTrue(king.db.is_king)
        self.assertEqual(king.db.kingdom, k)

    def test_set_entrance_room(self):
        k = _make_kingdom("Astra")
        room = _make_room()
        k.set_entrance_room(room)
        self.assertEqual(k.db.entrance_room, room)
        self.assertTrue(room.tags.has("king_entrance", category="ownership"))
        self.assertTrue(room.tags.has("kingdom:Astra", category="ownership"))

    def test_add_gm_continent_room(self):
        k = _make_kingdom()
        room = _make_room(room_id=42)
        k.add_gm_continent_room(room)
        self.assertIn(42, k.db.gm_continent_rooms)

    def test_add_gm_continent_room_no_duplicate(self):
        k = _make_kingdom()
        room = _make_room(room_id=42)
        k.add_gm_continent_room(room)
        k.add_gm_continent_room(room)
        self.assertEqual(k.db.gm_continent_rooms.count(42), 1)

    def test_delete_clears_king(self):
        k = _make_kingdom()
        king = _make_char(is_king=True)
        king.db.kingdom = k
        k.db.king = king
        k.delete()
        self.assertFalse(king.db.is_king)
        self.assertIsNone(king.db.kingdom)


class TestKingdomTools(unittest.TestCase):
    """Test module-level kingdom_* functions."""

    def test_get_kingdom_by_king_returns_kingdom(self):
        king = _make_char()
        kingdom = _make_kingdom()
        king.db.kingdom = kingdom
        result = kingdom_mod.get_kingdom_by_king(king)
        self.assertEqual(result, kingdom)

    def test_get_kingdom_by_king_returns_none(self):
        king = _make_char()
        result = kingdom_mod.get_kingdom_by_king(king)
        self.assertIsNone(result)

    def test_add_room_quota(self):
        k = _make_kingdom(room_quota=10)
        result = kingdom_mod.add_room_quota(k, 5)
        self.assertEqual(k.db.room_quota, 15)
        self.assertEqual(result, 15)

    def test_get_kingdom_status(self):
        k = _make_kingdom(key="Astra", room_quota=10, rooms_created=3)
        king = _make_char(key="Arthur")
        k.db.king = king
        room = _make_room(key="Throne")
        k.db.entrance_room = room

        status = kingdom_mod.get_kingdom_status(k)
        self.assertEqual(status["name"], "Astra")
        self.assertEqual(status["king"], "Arthur")
        self.assertEqual(status["entrance_room"], "Throne")
        self.assertEqual(status["quota"], 10)
        self.assertEqual(status["used"], 3)
        self.assertEqual(status["remaining"], 7)

    def test_get_kingdom_status_no_king(self):
        k = _make_kingdom(key="Empty")
        status = kingdom_mod.get_kingdom_status(k)
        self.assertEqual(status["king"], "無")
        self.assertEqual(status["entrance_room"], "未設定")

    def test_create_kingdom_validates_character(self):
        """create_kingdom should reject non-Character king_char."""
        bad_char = SimpleNamespace(key="NotAChar")
        # inherits_from returns False for this test
        with patch.object(kingdom_mod, "inherits_from", return_value=False):
            with self.assertRaises(ValueError) as err:
                kingdom_mod.create_kingdom(bad_char, "Test", _make_room(), 5)
        self.assertIn("必須是 Character", str(err.exception))

    def test_get_kingdom_by_name_returns_none_when_empty(self):
        with patch.object(kingdom_mod, "search_object", return_value=[]):
            result = kingdom_mod.get_kingdom_by_name("NonExistent")
        self.assertIsNone(result)


if __name__ == "__main__":
    unittest.main()
