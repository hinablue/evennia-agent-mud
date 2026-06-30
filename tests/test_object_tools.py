"""Unit tests for world/object_tools.py — object CRUD helpers."""

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

    def create_object(typeclass, key, **kw):
        obj = SimpleNamespace(key=key, typeclass_path="typeclasses.objects.Object",
                              db=SimpleNamespace(desc=""), location=kw.get("location"),
                              save=MagicMock(), delete=MagicMock(),
                              aliases=SimpleNamespace(add=MagicMock(), all=lambda: []))
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

    typeclasses_objects = types.ModuleType("typeclasses.objects")
    typeclasses_objects.Object = type("Object", (), {})
    sys.modules["typeclasses.objects"] = typeclasses_objects

    typeclasses_rooms = types.ModuleType("typeclasses.rooms")
    typeclasses_rooms.Room = type("Room", (), {})
    sys.modules["typeclasses.rooms"] = typeclasses_rooms


_install_stubs()
obj_tools = importlib.import_module("world.object_tools")
ObjectSpecError = obj_tools.ObjectSpecError


class TestObjectTools(unittest.TestCase):
    def setUp(self):
        _FAKE_OBJS.clear()

    def test_create_object_admin(self):
        room = SimpleNamespace(key="Tavern", typeclass_path="typeclasses.rooms.Room", db=SimpleNamespace(desc=""))
        _FAKE_OBJS["Tavern"] = room
        result = obj_tools.create_object_admin("Chest", "Tavern")
        self.assertIn("Chest", _FAKE_OBJS)

    def test_summarize_object(self):
        obj = SimpleNamespace(key="Chest", typeclass_path="typeclasses.objects.Object",
                              db=SimpleNamespace(desc="A wooden chest."),
                              location=SimpleNamespace(key="Tavern"),
                              aliases=SimpleNamespace(all=lambda: []))
        _FAKE_OBJS["Chest"] = obj
        result = obj_tools.summarize_object("Chest")
        self.assertIn("Chest", result)

    def test_move_object(self):
        dest = SimpleNamespace(key="Dungeon", typeclass_path="typeclasses.rooms.Room")
        obj = SimpleNamespace(key="Chest", typeclass_path="typeclasses.objects.Object",
                              db=SimpleNamespace(), location=None, save=MagicMock())
        _FAKE_OBJS["Chest"] = obj
        _FAKE_OBJS["Dungeon"] = dest
        obj_tools.move_object("Chest", "Dungeon")
        self.assertEqual(obj.location, dest)

    def test_set_object_desc(self):
        obj = SimpleNamespace(key="Chest", typeclass_path="typeclasses.objects.Object",
                              db=SimpleNamespace(desc="old"), save=MagicMock())
        _FAKE_OBJS["Chest"] = obj
        obj_tools.set_object_desc("Chest", "A golden chest.")
        self.assertEqual(obj.db.desc, "A golden chest.")

    def test_delete_object(self):
        obj = SimpleNamespace(key="Chest", typeclass_path="typeclasses.objects.Object",
                              db=SimpleNamespace(), delete=MagicMock())
        _FAKE_OBJS["Chest"] = obj
        obj_tools.delete_object("Chest")
        obj.delete.assert_called_once()

    def test_missing_object_raises(self):
        with self.assertRaises(ObjectSpecError):
            obj_tools.summarize_object("NonExistent")


if __name__ == "__main__":
    unittest.main()
