"""Unit tests for world/magic_tools.py — spell CRUD and helpers."""

from __future__ import annotations

import importlib
import sys
import types
import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch


# ---------------------------------------------------------------------------
# Stubs
# ---------------------------------------------------------------------------

_SPELL_REGISTRY = []


class FakeScriptDB:
    """In-memory script registry."""

    def __init__(self):
        self._scripts = list(_SPELL_REGISTRY)

    class objects:
        @staticmethod
        def all():
            return list(_SPELL_REGISTRY)


def _install_stubs():
    evennia = types.ModuleType("evennia")

    def search_script(key):
        return []

    evennia.search_script = search_script
    evennia.create_script = MagicMock()
    sys.modules["evennia"] = evennia

    scripts_models = types.ModuleType("evennia.scripts.models")
    scripts_models.ScriptDB = FakeScriptDB
    sys.modules["evennia.scripts.models"] = scripts_models

    utils_utils = types.ModuleType("evennia.utils.utils")
    utils_utils.make_iter = (
        lambda v: list(v) if isinstance(v, (list, tuple, set)) else [v] if v else []
    )
    sys.modules["evennia.utils.utils"] = utils_utils

    utils_pkg = types.ModuleType("evennia.utils")
    sys.modules["evennia.utils"] = utils_pkg
    utils_pkg.utils = utils_utils

    scripts_s = types.ModuleType("evennia.scripts.scripts")
    scripts_s.MuxScript = type(
        "MuxScript", (), {"save": lambda self: None, "delete": lambda self: None}
    )
    sys.modules["evennia.scripts.scripts"] = scripts_s
    evennia.create_script = MagicMock(
        return_value=SimpleNamespace(
            db=SimpleNamespace(), save=MagicMock(), delete=MagicMock(), key="spell"
        )
    )

    typeclasses_scripts = types.ModuleType("typeclasses.scripts")
    typeclasses_scripts.Script = scripts_s.MuxScript
    sys.modules["typeclasses.scripts"] = typeclasses_scripts


_install_stubs()
magic = importlib.import_module("world.magic_tools")
MagicSpecError = magic.MagicSpecError


# ---------------------------------------------------------------------------
# Tests — helpers
# ---------------------------------------------------------------------------


class TestMagicHelpers(unittest.TestCase):
    def test_clean_text_strips(self):
        self.assertEqual(magic._clean_text("  hello  "), "hello")

    def test_clean_text_none(self):
        self.assertEqual(magic._clean_text(None), "")

    def test_normalize_aliases_deduplicates(self):
        result = magic._normalize_aliases(["fire", "fire", "ice"])
        self.assertEqual(result, ["fire", "ice"])

    def test_normalize_aliases_strips_and_filters_empty(self):
        result = magic._normalize_aliases(["  fire  ", "", None, "ice"])
        self.assertEqual(result, ["fire", "ice"])

    def test_format_aliases_joins(self):
        self.assertEqual(magic._format_aliases(["火球", "冰刺"]), "火球、冰刺")

    def test_format_aliases_empty(self):
        self.assertEqual(magic._format_aliases([]), "無")

    def test_is_spell_script_by_flag(self):
        scr = SimpleNamespace(db=SimpleNamespace(is_spell=True), key="test")
        self.assertTrue(magic._is_spell_script(scr))

    def test_is_spell_script_by_spell_id(self):
        scr = SimpleNamespace(db=SimpleNamespace(is_spell=False, spell_id="fireball"), key="test")
        self.assertTrue(magic._is_spell_script(scr))

    def test_is_spell_script_false(self):
        scr = SimpleNamespace(db=SimpleNamespace(is_spell=False, spell_id=""), key="other")
        self.assertFalse(magic._is_spell_script(scr))

    def test_get_spell_identifier_prefers_spell_id(self):
        scr = SimpleNamespace(db=SimpleNamespace(spell_id="real_id", name="display"), key="k")
        self.assertEqual(magic._get_spell_identifier(scr), "real_id")

    def test_get_spell_identifier_falls_to_key(self):
        scr = SimpleNamespace(db=SimpleNamespace(spell_id="", name="display"), key="mykey")
        self.assertEqual(magic._get_spell_identifier(scr), "mykey")

    def test_get_spell_identifier_falls_to_name(self):
        scr = SimpleNamespace(db=SimpleNamespace(spell_id="", name="display_name"), key="spell")
        self.assertEqual(magic._get_spell_identifier(scr), "display_name")

    def test_resolve_spell_types_from_legacy_damage_type(self):
        damage_type, effect_type = magic._resolve_spell_types({"magic_type": "fire"})
        self.assertEqual(damage_type, "fire")
        self.assertEqual(effect_type, "damage")

    def test_resolve_spell_types_from_legacy_effect_type(self):
        damage_type, effect_type = magic._resolve_spell_types({"magic_type": "heal"})
        self.assertEqual(damage_type, "holy")
        self.assertEqual(effect_type, "heal")


# ---------------------------------------------------------------------------
# Tests — CRUD
# ---------------------------------------------------------------------------


class TestMagicCRUD(unittest.TestCase):
    def _make_spell(self):
        return SimpleNamespace(
            db=SimpleNamespace(
                is_spell=True,
                spell_id="fireball",
                name="火球",
                aliases=[],
                mp_cost=20,
                damage_type="fire",
                effect_type="damage",
                magic_type="fire",
                dmg_min=10,
                dmg_max=20,
                buff_stat="",
                buff_min=0,
                buff_max=0,
                debuff_stat="",
                debuff_min=0,
                debuff_max=0,
                buff_duration=0,
                is_heal=False,
                heal_min=0,
                heal_max=0,
                chance=0.8,
                status_effect=None,
                spell_level=1,
                target_self=False,
                target_enemy=True,
            ),
            key="fireball",
            save=MagicMock(),
            delete=MagicMock(),
        )

    def test_create_spell_empty_key_raises(self):
        with self.assertRaises(MagicSpecError) as err:
            magic.create_spell("")
        self.assertIn("ID", str(err.exception))

    def test_create_spell_stores_new_types(self):
        fake_obj = SimpleNamespace(
            db=SimpleNamespace(), save=MagicMock(), delete=MagicMock(), key="ember"
        )
        with patch("evennia.create_script", return_value=fake_obj, create=True):
            result = magic.create_spell(
                "ember",
                name="餘燼",
                damage_type="fire",
                effect_type="burn",
            )
        spell = result["spell"]
        self.assertEqual(spell.db.damage_type, "fire")
        self.assertEqual(spell.db.effect_type, "burn")
        self.assertEqual(spell.db.magic_type, "burn")

    def test_update_spell_no_fields_raises(self):
        spell = self._make_spell()
        with patch.object(magic, "_get_spell_or_error", return_value=spell):
            with self.assertRaises(MagicSpecError) as err:
                magic.update_spell("fireball")
        self.assertIn("至少", str(err.exception))

    def test_update_spell_name_field(self):
        spell = self._make_spell()
        with patch.object(magic, "_get_spell_or_error", return_value=spell):
            result = magic.update_spell("fireball", name="大火球")
        self.assertIn("name=", result["message"])
        self.assertEqual(spell.db.name, "大火球")

    def test_update_spell_damage_and_effect_type_fields(self):
        spell = self._make_spell()
        with patch.object(magic, "_get_spell_or_error", return_value=spell):
            result = magic.update_spell(
                "fireball", damage_type="arcane", effect_type="illusion"
            )
        self.assertIn("damage_type=arcane", result["message"])
        self.assertIn("effect_type=illusion", result["message"])
        self.assertEqual(spell.db.damage_type, "arcane")
        self.assertEqual(spell.db.effect_type, "illusion")
        self.assertEqual(spell.db.magic_type, "illusion")

    def test_update_spell_legacy_magic_type_routes_to_effect_type(self):
        spell = self._make_spell()
        with patch.object(magic, "_get_spell_or_error", return_value=spell):
            result = magic.update_spell("fireball", magic_type="heal")
        self.assertIn("effect_type=heal", result["message"])
        self.assertEqual(spell.db.effect_type, "heal")
        self.assertEqual(spell.db.damage_type, "fire")

    def test_delete_spell_calls_delete(self):
        spell = self._make_spell()
        with patch.object(magic, "_get_spell_or_error", return_value=spell):
            result = magic.delete_spell("fireball")
        spell.delete.assert_called_once()
        self.assertIn("已刪除", result["message"])

    def test_get_spell_or_error_empty_key_raises(self):
        with self.assertRaises(MagicSpecError):
            magic._get_spell_or_error("")

    def test_list_spells_returns_text_when_empty(self):
        with patch.object(magic, "_list_all_spells", return_value=[]):
            result = magic.list_spells()
        self.assertIn("沒有任何法術", result)

    def test_get_spell_or_error_not_found_raises(self):
        with patch.object(magic, "search_script", return_value=[]):
            with patch.object(
                magic,
                "ScriptDB",
                SimpleNamespace(objects=SimpleNamespace(all=lambda: [])),
            ):
                with self.assertRaises(MagicSpecError):
                    magic._get_spell_or_error("nonexistent_spell_xyz")


if __name__ == "__main__":
    unittest.main()
