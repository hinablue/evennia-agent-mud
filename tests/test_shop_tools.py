"""Unit tests for limited room-shop stock and purchases."""

from __future__ import annotations

import importlib
import sys
import types
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


class FakeDB:
    """Dict-backed ``obj.db`` replacement."""

    def __init__(self, **values):
        object.__setattr__(self, "_values", dict(values))

    def __getattr__(self, key):
        return object.__getattribute__(self, "_values").get(key)

    def __setattr__(self, key, value):
        object.__getattribute__(self, "_values")[key] = value


class FakeAliases:
    """Minimal alias handler supporting ``all()``."""

    def __init__(self, values=None):
        self._values = list(values or [])

    def all(self):
        return list(self._values)


class FakeObject:
    """Base fake Evennia object."""

    def __init__(self, object_id, key, typeclass_path, **db_values):
        self.id = object_id
        self.key = key
        self.typeclass_path = typeclass_path
        self.db = FakeDB(**db_values)
        self.aliases = FakeAliases(db_values.pop("aliases", []))
        self.location = db_values.pop("location", None)
        self.home = db_values.pop("home", None)
        self.attributes = types.SimpleNamespace(get=lambda key, default=None: getattr(self.db, key, default))
        self.deleted = False

    def save(self):
        return None

    def delete(self):
        self.deleted = True

    def get_display_name(self, looker=None):
        return self.key


class FakeRoom(FakeObject):
    """Fake room object."""

    def __init__(self, object_id, key):
        super().__init__(object_id, key, "typeclasses.rooms.Room", shop_stock=[])


class FakeEquipment(FakeObject):
    """Fake equipment object used as shop template or purchase clone."""

    def __init__(self, object_id, key, **db_values):
        defaults = {
            "desc": "一件裝備。",
            "stats": {},
            "equip_slot": "main_hand",
            "max_durability": 100,
            "durability": 100,
            "two_handed": False,
            "magic_buffs": [],
            "wear_style": "",
            "is_equipment": True,
        }
        defaults.update(db_values)
        aliases = defaults.pop("aliases", [])
        location = defaults.pop("location", None)
        home = defaults.pop("home", None)
        super().__init__(
            object_id,
            key,
            "typeclasses.equipment.Equipment",
            aliases=aliases,
            location=location,
            home=home,
            **defaults,
        )


class FakeObjectManager:
    """In-memory ``ObjectDB.objects`` replacement."""

    def __init__(self, registry):
        self.registry = registry

    def all(self):
        return list(self.registry)

    def get(self, id):
        for obj in self.registry:
            if obj.id == id:
                return obj
        raise KeyError(id)


class FakeCaller:
    """Character-like fake for purchase tests."""

    def __init__(self, room, tokens=100, capacity=10):
        self.location = room
        self.db = FakeDB(tokens=tokens)
        self._capacity = capacity
        self.inventory = []
        self.messages = []

    def get_tokens(self):
        return self.db.tokens

    def add_to_inventory(self, item):
        if len(self.inventory) >= self._capacity:
            return False
        self.inventory.append(item)
        return True

    def remove_from_inventory(self, item):
        if item in self.inventory:
            self.inventory.remove(item)
            return True
        return False

    def spend_tokens(self, amount):
        if self.db.tokens < amount:
            return False
        self.db.tokens -= amount
        return True

    def msg(self, text):
        self.messages.append(text)


class TestShopTools(unittest.TestCase):
    """Exercise room stock configuration and limited purchases."""

    def setUp(self):
        self.registry = []
        self._next_id = 100
        self.room = FakeRoom(1, "迎賓大廳")
        self.template = FakeEquipment(
            2,
            "鐵劍",
            desc="普通的鐵劍。",
            stats={"atk": 5},
            equip_slot="main_hand",
            aliases=["iron_sword"],
            location=self.room,
            home=self.room,
        )
        self.registry.extend([self.room, self.template])
        self._install_stubs()
        sys.modules.pop("world.equipment_tools", None)
        sys.modules.pop("world.shop_tools", None)
        self.shop_tools = importlib.import_module("world.shop_tools")

    def _install_stubs(self):
        """Install fake Evennia modules required by shop/equipment tools."""

        def create_object(typeclass, key, location=None, home=None, aliases=None, attributes=None):
            obj = FakeEquipment(self._next_id, key, location=location, home=home)
            self._next_id += 1
            if aliases:
                obj.aliases = FakeAliases(aliases)
            for attr_key, attr_value in attributes or []:
                setattr(obj.db, attr_key, attr_value)
            self.registry.append(obj)
            return obj

        def search_object(key, exact=True):
            matches = [obj for obj in self.registry if obj.key == key]
            return matches[:1] if exact else matches

        def inherits_from(obj, path):
            return getattr(obj, "typeclass_path", None) == path

        def class_from_module(path, *args, **kwargs):
            return FakeEquipment

        def make_iter(value):
            if value is None:
                return []
            if isinstance(value, (list, tuple, set)):
                return list(value)
            return [value]

        evennia = types.ModuleType("evennia")
        setattr(evennia, "create_object", create_object)
        setattr(evennia, "search_object", search_object)
        sys.modules["evennia"] = evennia

        objects_module = types.ModuleType("evennia.objects")
        sys.modules["evennia.objects"] = objects_module
        models_module = types.ModuleType("evennia.objects.models")
        setattr(models_module, "ObjectDB", types.SimpleNamespace(objects=FakeObjectManager(self.registry)))
        sys.modules["evennia.objects.models"] = models_module
        setattr(objects_module, "models", models_module)

        utils_pkg = types.ModuleType("evennia.utils")
        sys.modules["evennia.utils"] = utils_pkg
        utils_module = types.ModuleType("evennia.utils.utils")
        setattr(utils_module, "inherits_from", inherits_from)
        setattr(utils_module, "class_from_module", class_from_module)
        setattr(utils_module, "make_iter", make_iter)
        sys.modules["evennia.utils.utils"] = utils_module
        setattr(utils_pkg, "utils", utils_module)

        typeclasses_pkg = types.ModuleType("typeclasses")
        sys.modules["typeclasses"] = typeclasses_pkg
        typeclasses_equipment = types.ModuleType("typeclasses.equipment")
        setattr(typeclasses_equipment, "Equipment", FakeEquipment)
        sys.modules["typeclasses.equipment"] = typeclasses_equipment
        setattr(typeclasses_pkg, "equipment", typeclasses_equipment)

    def test_set_room_shop_stock_adds_entry(self):
        """Stock configuration should persist template id, price, and quantity."""
        result = self.shop_tools.set_room_shop_stock("鐵劍", "迎賓大廳", 30, 2)

        self.assertIn("價格 30 Token，數量 2", result["message"])
        self.assertEqual(len(self.room.db.shop_stock), 1)
        self.assertEqual(self.room.db.shop_stock[0]["template_key"], "鐵劍")
        self.assertEqual(self.room.db.shop_stock[0]["quantity"], 2)

    def test_buy_from_room_shop_decrements_limited_stock(self):
        """Buying a limited item should clone it, deduct tokens, and reduce quantity."""
        self.shop_tools.set_room_shop_stock("鐵劍", "迎賓大廳", 30, 2)
        caller = FakeCaller(self.room, tokens=100)

        result = self.shop_tools.buy_from_room_shop(caller, "1")

        self.assertEqual(caller.db.tokens, 70)
        self.assertEqual(len(caller.inventory), 1)
        self.assertEqual(caller.inventory[0].key, "鐵劍")
        self.assertIn("剩餘數量：1", result["message"])
        self.assertEqual(self.room.db.shop_stock[0]["quantity"], 1)

    def test_buy_from_room_shop_keeps_infinite_stock(self):
        """Buying an infinite item should leave quantity at ``-1``."""
        self.shop_tools.set_room_shop_stock("鐵劍", "迎賓大廳", 30, -1)
        caller = FakeCaller(self.room, tokens=100)

        result = self.shop_tools.buy_from_room_shop(caller, "鐵劍")

        self.assertEqual(caller.db.tokens, 70)
        self.assertIn("剩餘數量：∞", result["message"])
        self.assertEqual(self.room.db.shop_stock[0]["quantity"], -1)

    def test_buy_from_room_shop_rejects_sold_out_item(self):
        """Sold-out entries should block purchases."""
        self.shop_tools.set_room_shop_stock("鐵劍", "迎賓大廳", 30, 0)
        caller = FakeCaller(self.room, tokens=100)

        with self.assertRaises(self.shop_tools.ShopSpecError):
            self.shop_tools.buy_from_room_shop(caller, "1")


if __name__ == "__main__":
    unittest.main()
