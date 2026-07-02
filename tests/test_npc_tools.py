"""Unit tests for world/npc_tools.py — NPC CRUD helpers."""

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
    _next = [1000]

    def create_object(typeclass, key, **kw):
        obj = SimpleNamespace(
            id=_next[0],
            key=key,
            typeclass_path="typeclasses.npcs.NPC",
            db=SimpleNamespace(desc="", aliases=[]),
            save=MagicMock(),
            delete=MagicMock(),
            location=kw.get("location"),
            home=kw.get("home"),
        )
        _next[0] += 1
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
    objects_models.ObjectDB = SimpleNamespace(
        objects=SimpleNamespace(all=lambda: list(_FAKE_OBJS.values()))
    )
    sys.modules["evennia.objects.models"] = objects_models
    objects_mod.models = objects_models

    utils_utils = types.ModuleType("evennia.utils.utils")
    utils_utils.inherits_from = lambda o, p: True
    utils_utils.make_iter = lambda v: (
        list(v) if isinstance(v, (list, tuple, set)) else [v] if v else []
    )
    utils_utils.class_from_module = lambda p, *a, **k: None
    sys.modules["evennia.utils.utils"] = utils_utils

    utils_pkg = types.ModuleType("evennia.utils")
    sys.modules["evennia.utils"] = utils_pkg
    utils_pkg.utils = utils_utils

    typeclasses_npcs = types.ModuleType("typeclasses.npcs")
    typeclasses_npcs.NPC = type("NPC", (), {})
    typeclasses_npcs.LLMNPC = type("LLMNPC", (), {})
    sys.modules["typeclasses.npcs"] = typeclasses_npcs

    typeclasses_llm = types.ModuleType("typeclasses.llm_npc")
    typeclasses_llm.DEFAULT_PROMPT_PREFIX = "You are an NPC."
    sys.modules["typeclasses.llm_npc"] = typeclasses_llm

    typeclasses_chars = types.ModuleType("typeclasses.characters")
    typeclasses_chars.Character = type("Character", (), {})
    sys.modules["typeclasses.characters"] = typeclasses_chars


_install_stubs()
npc = importlib.import_module("world.npc_tools")
NPCSpecError = npc.NPCSpecError


class TestNPCTools(unittest.TestCase):
    def setUp(self):
        _FAKE_OBJS.clear()

    def test_create_npc_adds_to_registry(self):
        room = SimpleNamespace(key="Tavern")
        _FAKE_OBJS["Tavern"] = room
        result = npc.create_npc("npc", "Guard", "Tavern")
        self.assertIn("Guard", _FAKE_OBJS)

    def test_summarize_npc_returns_text(self):
        obj = SimpleNamespace(
            key="Guard",
            typeclass_path="typeclasses.npcs.NPC",
            db=SimpleNamespace(desc="A guard.", ai_state="idle"),
            sdesc=SimpleNamespace(get=MagicMock(return_value="A watchful guard")),
            location=SimpleNamespace(key="Tavern"),
            attributes=SimpleNamespace(get=lambda k, default=None: default),
            aliases=SimpleNamespace(all=lambda: []),
        )
        _FAKE_OBJS["Guard"] = obj
        result = npc.summarize_npc("Guard")
        self.assertIn("Guard", result)
        self.assertIn("A watchful guard", result)

    def test_move_npc_updates_location(self):
        target_room = SimpleNamespace(key="Dungeon")
        obj = SimpleNamespace(
            key="Guard",
            typeclass_path="typeclasses.npcs.NPC",
            db=SimpleNamespace(),
            location=SimpleNamespace(key="Tavern"),
            save=MagicMock(),
        )
        _FAKE_OBJS["Guard"] = obj
        _FAKE_OBJS["Dungeon"] = target_room
        result = npc.move_npc("Guard", "Dungeon")
        self.assertEqual(obj.location, target_room)

    def test_set_npc_desc(self):
        obj = SimpleNamespace(
            key="Guard",
            typeclass_path="typeclasses.npcs.NPC",
            db=SimpleNamespace(desc="old"),
            save=MagicMock(),
        )
        _FAKE_OBJS["Guard"] = obj
        result = npc.set_npc_desc("Guard", "A fierce guard.")
        self.assertEqual(obj.db.desc, "A fierce guard.")

    def test_set_npc_sdesc_updates_rpsystem_handler(self):
        sdesc_handler = SimpleNamespace(add=MagicMock(return_value="A masked guard"))
        obj = SimpleNamespace(
            key="Guard",
            typeclass_path="typeclasses.npcs.NPC",
            db=SimpleNamespace(),
            sdesc=sdesc_handler,
            save=MagicMock(),
        )
        _FAKE_OBJS["Guard"] = obj
        result = npc.set_npc_sdesc("Guard", "A masked guard")
        sdesc_handler.add.assert_called_once_with("A masked guard")
        obj.save.assert_called_once()
        self.assertIn("A masked guard", result["message"])

    def test_delete_npc(self):
        obj = SimpleNamespace(
            key="Guard",
            typeclass_path="typeclasses.npcs.NPC",
            db=SimpleNamespace(),
            delete=MagicMock(),
        )
        _FAKE_OBJS["Guard"] = obj
        result = npc.delete_npc("Guard")
        obj.delete.assert_called_once()

    def test_missing_npc_raises(self):
        with self.assertRaises(NPCSpecError):
            npc.summarize_npc("NonExistent")

    def test_copy_equipment_to_loot_entry_keeps_clothing_metadata(self):
        item = SimpleNamespace(
            key="Cloak",
            typeclass_path="typeclasses.equipment.Equipment",
            db=SimpleNamespace(
                desc="A cloak.",
                stats={"def": 2},
                equip_slot="cloak",
                clothing_type="cloak",
                max_durability=80,
                two_handed=False,
                magic_buffs=[],
                wear_style="披在肩上",
            ),
            aliases=SimpleNamespace(all=lambda: ["mantle"]),
        )
        entry = npc._copy_equipment_to_loot_entry(item, chance=0.5)
        self.assertEqual(entry["clothing_type"], "cloak")
        self.assertFalse(entry["worn"])
        self.assertIsNone(entry["covered_by"])
        self.assertEqual(entry["wear_style"], "披在肩上")

    def test_place_equipment_on_npc_uses_local_equip_quietly(self):
        item = SimpleNamespace(
            key="Hat",
            location=None,
            home=None,
            save=MagicMock(),
        )
        npc_obj = SimpleNamespace(
            key="Guard",
            location=SimpleNamespace(key="Tavern"),
            home=None,
            find_in_inventory=MagicMock(return_value=None),
            add_to_inventory=MagicMock(return_value=True),
            equip_item=MagicMock(return_value=True),
        )
        result = npc._place_equipment_on_npc(npc_obj, item, "hat")
        self.assertIs(result, item)
        self.assertEqual(item.location, npc_obj)
        npc_obj.add_to_inventory.assert_called_once_with(item)
        npc_obj.equip_item.assert_called_once_with(item, "hat", quiet=True)


if __name__ == "__main__":
    unittest.main()
