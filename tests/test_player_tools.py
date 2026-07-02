"""Unit tests for world/player_tools.py — player CRUD helpers."""

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
        obj = SimpleNamespace(key=key, typeclass_path="typeclasses.characters.Character",
                              db=SimpleNamespace(desc="", nationality=""),
                              location=kw.get("location"), home=kw.get("home"),
                              save=MagicMock(), delete=MagicMock(),
                              aliases=SimpleNamespace(add=MagicMock(), all=lambda: []))
        _FAKE_OBJS[key] = obj
        return obj

    def search_object(key, exact=True):
        return [_FAKE_OBJS[key]] if key in _FAKE_OBJS else []

    def search_account(key):
        return []

    evennia.create_object = create_object
    evennia.search_object = search_object
    evennia.search_account = search_account
    sys.modules["evennia"] = evennia

    accounts_mod = types.ModuleType("evennia.accounts")
    sys.modules["evennia.accounts"] = accounts_mod

    accounts_models = types.ModuleType("evennia.accounts.models")
    accounts_models.AccountDB = SimpleNamespace(objects=SimpleNamespace(all=lambda: []))
    sys.modules["evennia.accounts.models"] = accounts_models
    accounts_mod.models = accounts_models

    accounts_accounts = types.ModuleType("evennia.accounts.accounts")
    accounts_accounts.DefaultAccount = type("DefaultAccount", (), {"create": MagicMock(return_value=(None, []))})
    sys.modules["evennia.accounts.accounts"] = accounts_accounts
    accounts_mod.accounts = accounts_accounts

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

    typeclasses_chars = types.ModuleType("typeclasses.characters")
    typeclasses_chars.Character = type("Character", (), {})
    sys.modules["typeclasses.characters"] = typeclasses_chars

    typeclasses_rooms = types.ModuleType("typeclasses.rooms")
    typeclasses_rooms.Room = type("Room", (), {})
    sys.modules["typeclasses.rooms"] = typeclasses_rooms

    # Stub world.kingdom which player_tools may import
    kingdom_mod = types.ModuleType("world.kingdom")
    kingdom_mod.get_kingdom_by_king = lambda c: None
    kingdom_mod.get_kingdom_by_name = lambda n: None
    sys.modules["world.kingdom"] = kingdom_mod

    account_tools_mod = types.ModuleType("world.account_tools")
    setattr(
        account_tools_mod,
        "ensure_first_player_account_is_gm",
        MagicMock(return_value={"promoted": False, "message": ""}),
    )
    sys.modules["world.account_tools"] = account_tools_mod


_install_stubs()
player = importlib.import_module("world.player_tools")
PlayerSpecError = player.PlayerSpecError


class TestPlayerTools(unittest.TestCase):
    def setUp(self):
        _FAKE_OBJS.clear()

    def test_create_player(self):
        room = SimpleNamespace(key="StartRoom", typeclass_path="typeclasses.rooms.Room")
        _FAKE_OBJS["StartRoom"] = room
        # create_player needs more args; test via summarize instead
        obj = SimpleNamespace(key="Hero", id=1, typeclass_path="typeclasses.characters.Character",
                              db=SimpleNamespace(desc="A hero.", nationality="", active_quests=[], completed_quests=[]),
                              location=room, home=room,
                              save=MagicMock(), delete=MagicMock(),
                              aliases=SimpleNamespace(add=MagicMock(), all=lambda: []),
                              locks=SimpleNamespace(add=MagicMock()), account=None)
        _FAKE_OBJS["Hero"] = obj
        result = player.summarize_player("Hero")
        self.assertIn("Hero", result)

    def test_summarize_player(self):
        obj = SimpleNamespace(key="Hero", typeclass_path="typeclasses.characters.Character",
                              db=SimpleNamespace(desc="A hero.", nationality=""),
                              sdesc=SimpleNamespace(get=MagicMock(return_value="A quiet hero")),
                              location=SimpleNamespace(key="Town"), home=SimpleNamespace(key="Start"),
                              aliases=SimpleNamespace(all=lambda: []), account=None)
        _FAKE_OBJS["Hero"] = obj
        result = player.summarize_player("Hero")
        self.assertIn("Hero", result)
        self.assertIn("A quiet hero", result)

    def test_move_player(self):
        dest = SimpleNamespace(key="Dungeon")
        obj = SimpleNamespace(key="Hero", typeclass_path="typeclasses.characters.Character",
                              db=SimpleNamespace(), location=None, save=MagicMock())
        _FAKE_OBJS["Hero"] = obj
        _FAKE_OBJS["Dungeon"] = dest
        player.move_player("Hero", "Dungeon")
        self.assertEqual(obj.location, dest)

    def test_set_player_sdesc_updates_rpsystem_handler(self):
        sdesc_handler = SimpleNamespace(add=MagicMock(return_value="A masked traveler"))
        obj = SimpleNamespace(
            key="Hero",
            typeclass_path="typeclasses.characters.Character",
            db=SimpleNamespace(),
            sdesc=sdesc_handler,
            save=MagicMock(),
        )
        _FAKE_OBJS["Hero"] = obj
        result = player.set_player_sdesc("Hero", "A masked traveler")
        sdesc_handler.add.assert_called_once_with("A masked traveler")
        obj.save.assert_called_once()
        self.assertIn("A masked traveler", result["message"])

    def test_set_player_home(self):
        room = SimpleNamespace(key="HomeRoom")
        obj = SimpleNamespace(key="Hero", typeclass_path="typeclasses.characters.Character",
                              db=SimpleNamespace(), home=None, save=MagicMock())
        _FAKE_OBJS["Hero"] = obj
        _FAKE_OBJS["HomeRoom"] = room
        player.set_player_home("Hero", "HomeRoom")
        self.assertEqual(obj.home, room)

    def test_delete_player(self):
        obj = SimpleNamespace(key="Hero", typeclass_path="typeclasses.characters.Character",
                              db=SimpleNamespace(), delete=MagicMock())
        _FAKE_OBJS["Hero"] = obj
        player.delete_player("Hero")
        obj.delete.assert_called_once()

    def test_missing_player_raises(self):
        with self.assertRaises(PlayerSpecError):
            player.summarize_player("NonExistent")


if __name__ == "__main__":
    unittest.main()
