"""Unit tests for world/room_tools.py — RoomTools class."""

from __future__ import annotations

import importlib
import sys
import types
import unittest
from unittest.mock import MagicMock, patch
from types import SimpleNamespace


_FAKE_OBJS = {}


def _install_stubs():
    evennia = types.ModuleType("evennia")

    def create_object(typeclass, key, **kw):
        obj = SimpleNamespace(key=key, typeclass_path="typeclasses.rooms.Room",
                              db=SimpleNamespace(desc="", pvp_enabled=False),
                              save=MagicMock(), delete=MagicMock(), location=None)
        _FAKE_OBJS[key] = obj
        return obj

    def search_object(key, exact=True):
        return [_FAKE_OBJS[key]] if key in _FAKE_OBJS else []

    evennia.create_object = create_object
    evennia.search_object = search_object
    sys.modules["evennia"] = evennia

    objects_mod = types.ModuleType("evennia.objects")
    sys.modules["evennia.objects"] = objects_mod

    objects_models = types.ModuleType("evennia.objects.models")
    objects_models.ObjectDB = SimpleNamespace(objects=SimpleNamespace(all=lambda: list(_FAKE_OBJS.values())))
    sys.modules["evennia.objects.models"] = objects_models
    objects_mod.models = objects_models

    utils_utils = types.ModuleType("evennia.utils.utils")
    utils_utils.inherits_from = lambda o, p: True
    utils_utils.make_iter = lambda v: list(v) if isinstance(v, (list, tuple, set)) else [v] if v else []
    utils_utils.class_from_module = lambda p, *a, **k: None
    sys.modules["evennia.utils.utils"] = utils_utils

    utils_pkg = types.ModuleType("evennia.utils")
    sys.modules["evennia.utils"] = utils_pkg
    utils_pkg.utils = utils_utils

    # Stub typeclasses chain to avoid deep imports
    typeclasses_rooms = types.ModuleType("typeclasses.rooms")

    class _FakeRoom:
        fallback_desc = "你甚麼也沒看到。"
        objects = SimpleNamespace(all=lambda: list(_FAKE_OBJS.values()))

    typeclasses_rooms.Room = _FakeRoom
    sys.modules["typeclasses.rooms"] = typeclasses_rooms

    typeclasses_exits = types.ModuleType("typeclasses.exits")
    typeclasses_exits.Exit = type("Exit", (), {})
    sys.modules["typeclasses.exits"] = typeclasses_exits

    typeclasses_objects = types.ModuleType("typeclasses.objects")
    typeclasses_objects.Object = type("Object", (), {})
    sys.modules["typeclasses.objects"] = typeclasses_objects

    typeclasses_doors = types.ModuleType("typeclasses.doors")
    typeclasses_doors.DoorObject = type("DoorObject", (), {})
    sys.modules["typeclasses.doors"] = typeclasses_doors

    typeclasses_chars = types.ModuleType("typeclasses.characters")
    typeclasses_chars.Character = type("Character", (), {})
    sys.modules["typeclasses.characters"] = typeclasses_chars

    # Stub evennia.objects.objects for DefaultObject
    objects_objects = types.ModuleType("evennia.objects.objects")
    objects_objects.DefaultObject = type("DefaultObject", (), {})
    sys.modules["evennia.objects.objects"] = objects_objects
    objects_mod.objects = objects_objects


_install_stubs()
room_tools = importlib.import_module("world.room_tools")
RoomTools = room_tools.RoomTools


class TestRoomTools(unittest.TestCase):
    def setUp(self):
        _FAKE_OBJS.clear()

    def test_create_room(self):
        rt = RoomTools()
        result = rt.create_room("Castle", "A grand castle.")
        self.assertIn("Castle", _FAKE_OBJS)

    def test_list_rooms(self):
        _FAKE_OBJS["Tavern"] = SimpleNamespace(key="Tavern", id=1, typeclass_path="typeclasses.rooms.Room",
                                                db=SimpleNamespace(desc="", pvp_enabled=False))
        rt = RoomTools()
        result = rt.list_rooms()
        self.assertIsInstance(result, str)

    def test_update_desc(self):
        room = SimpleNamespace(key="Tavern", typeclass_path="typeclasses.rooms.Room",
                               db=SimpleNamespace(desc="old"), save=MagicMock())
        _FAKE_OBJS["Tavern"] = room
        rt = RoomTools()
        rt.update_desc("Tavern", "A cozy tavern.")
        self.assertEqual(room.db.desc, "A cozy tavern.")

    def test_set_pvp_state(self):
        room = SimpleNamespace(key="Arena", typeclass_path="typeclasses.rooms.Room",
                               db=SimpleNamespace(pvp_enabled=False), save=MagicMock())
        _FAKE_OBJS["Arena"] = room
        rt = RoomTools()
        rt.set_pvp_state("Arena", True)
        self.assertTrue(room.db.pvp_enabled)

    def test_delete_room(self):
        room = SimpleNamespace(key="OldRoom", typeclass_path="typeclasses.rooms.Room",
                               db=SimpleNamespace(), delete=MagicMock())
        _FAKE_OBJS["OldRoom"] = room
        rt = RoomTools()
        rt.delete_room("OldRoom")
        room.delete.assert_called_once()

    def test_summarize_room(self):
        room = SimpleNamespace(key="Tavern", id=1, typeclass_path="typeclasses.rooms.Room",
                               db=SimpleNamespace(desc="A cozy place.", pvp_enabled=False, shop_stock=[]),
                               location=None, contents=[])
        _FAKE_OBJS["Tavern"] = room
        rt = RoomTools()
        result = rt.summarize_room("Tavern")
        self.assertIn("Tavern", result)


if __name__ == "__main__":
    unittest.main()
