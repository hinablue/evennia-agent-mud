import unittest
from unittest.mock import MagicMock
import sys
from types import ModuleType

# 1. Mock Django settings
mock_settings = ModuleType("settings")
mock_settings.CHANNEL_LOG_NUM_TAIL_LINES = 100
sys.modules["django.conf.settings"] = mock_settings

# 2. Mock Evennia core
evennia = ModuleType("evennia")
evennia.create_object = MagicMock()
evennia.search_object = MagicMock()
sys.modules["evennia"] = evennia

# 3. Mock hierarchy
modules_to_mock = [
    "evennia.objects.models",
    "evennia.contrib.grid.xyzgrid",
    "evennia.contrib.grid.xyzgrid.xyzgrid",
    "evennia.contrib.grid.xyzgrid.xyzroom",
    "evennia.contrib.grid.xyzgrid.xymap_legend",
    "evennia.prototypes",
    "evennia.prototypes.spawner",
    "evennia.commands",
    "evennia.commands.cmdset",
    "evennia.commands.command",
    "evennia.utils",
    "evennia.utils.utils",
    "evennia.utils.logger",
    "evennia.locks",
    "evennia.locks.lockhandler",
]

for mod_name in modules_to_mock:
    mod = ModuleType(mod_name)
    sys.modules[mod_name] = mod

sys.modules["evennia.contrib.grid.xyzgrid.xyzroom"].MAP_XDEST_TAG_CATEGORY = "xdest"
sys.modules["evennia.contrib.grid.xyzgrid.xyzroom"].MAP_X_TAG_CATEGORY = "x"
sys.modules["evennia.contrib.grid.xyzgrid.xyzroom"].MAP_YDEST_TAG_CATEGORY = "ydest"
sys.modules["evennia.contrib.grid.xyzgrid.xyzroom"].MAP_Y_TAG_CATEGORY = "y"
sys.modules["evennia.contrib.grid.xyzgrid.xyzroom"].MAP_ZDEST_TAG_CATEGORY = "zdest"
sys.modules["evennia.contrib.grid.xyzgrid.xyzroom"].MAP_Z_TAG_CATEGORY = "z"
sys.modules["evennia.contrib.grid.xyzgrid.xymap_legend"].MapNode = MagicMock()
sys.modules["evennia.contrib.grid.xyzgrid.xyzgrid"].get_xyzgrid = MagicMock()
sys.modules["evennia.objects.models"].ObjectDB = MagicMock()
sys.modules["evennia.commands.command"].Command = MagicMock()

# 4. Mock typeclasses
sys.modules["typeclasses.exits"] = ModuleType("typeclasses.exits")
sys.modules["typeclasses.exits"].Exit = MagicMock()
sys.modules["typeclasses.npcs"] = ModuleType("typeclasses.npcs")
setattr(sys.modules["typeclasses.npcs"], "NPC", MagicMock())
sys.modules["typeclasses.objects"] = ModuleType("typeclasses.objects")
sys.modules["typeclasses.objects"].Object = MagicMock()
sys.modules["typeclasses.rooms"] = ModuleType("typeclasses.rooms")
sys.modules["typeclasses.rooms"].Room = MagicMock()

from world import agent_world
from world.agent_world import ROOM_DEFS, LIMBO_ROOM_KEY, ROSIE_HOME, ROSIE_KEY


class _FakeQuerySet(list):
    def order_by(self, *_args, **_kwargs):
        return self


class TestAgentWorld(unittest.TestCase):
    def setUp(self):
        evennia.create_object.reset_mock()
        evennia.search_object.reset_mock()
        agent_world.ObjectDB.objects.filter.reset_mock()

    def test_room_defs_structure(self):
        self.assertIn(LIMBO_ROOM_KEY, ROOM_DEFS)
        room = ROOM_DEFS[LIMBO_ROOM_KEY]
        self.assertIn("desc", room)
        self.assertIn("details", room)
        self.assertIn("objects", room)

    def test_room_desc_not_empty(self):
        for room_key, data in ROOM_DEFS.items():
            self.assertTrue(len(data["desc"]) > 0)

    def test_room_objects_structure(self):
        for room_key, data in ROOM_DEFS.items():
            for obj in data["objects"]:
                self.assertIn("key", obj)
                self.assertIn("desc", obj)
                self.assertIn("aliases", obj)

    def test_find_by_key_prefers_objectdb_over_search_cache(self):
        fresh_room = object()
        agent_world.ObjectDB.objects.filter.return_value = _FakeQuerySet([fresh_room])
        evennia.search_object.return_value = [object()]

        result = agent_world._find_by_key("莫比爾站")

        self.assertIs(result, fresh_room)
        agent_world.ObjectDB.objects.filter.assert_called_with(db_key="莫比爾站")
        evennia.search_object.assert_not_called()

    def test_find_by_key_falls_back_to_search_object_when_db_empty(self):
        cached_room = object()
        agent_world.ObjectDB.objects.filter.return_value = _FakeQuerySet()
        evennia.search_object.return_value = [cached_room]

        result = agent_world._find_by_key("迎賓大廳")

        self.assertIs(result, cached_room)
        evennia.search_object.assert_called_with("迎賓大廳", exact=True)

    def test_rosie_is_promoted_to_npc_defs(self):
        self.assertIn(ROSIE_KEY, agent_world.NPC_DEFS)
        spec = agent_world.NPC_DEFS[ROSIE_KEY]
        self.assertEqual(spec["room"], ROSIE_HOME)
        self.assertIn("蘿西", spec["aliases"])
        self.assertFalse(spec["attributes"]["npc_attackable"])

    def test_npc_defs_are_filtered_by_scope(self):
        self.assertEqual(agent_world._npc_defs_for_scope(["訓練廳"]), {})
        self.assertIn(ROSIE_KEY, agent_world._npc_defs_for_scope([ROSIE_HOME]))

    def test_ensure_npc_creates_missing_rosie(self):
        room = MagicMock()
        npc = MagicMock()
        evennia.create_object.return_value = npc
        agent_world.ObjectDB.objects.filter.return_value = _FakeQuerySet()
        evennia.search_object.return_value = []

        result, created, moved, updated = agent_world._ensure_npc(
            ROSIE_KEY, agent_world.NPC_DEFS[ROSIE_KEY], {ROSIE_HOME: room}
        )

        self.assertIs(result, npc)
        self.assertTrue(created)
        self.assertFalse(moved)
        self.assertFalse(updated)
        evennia.create_object.assert_called_once()
        kwargs = evennia.create_object.call_args.kwargs
        self.assertEqual(kwargs["key"], ROSIE_KEY)
        self.assertIs(kwargs["location"], room)
        self.assertIs(kwargs["home"], room)
        self.assertIn("蘿西", kwargs["aliases"])
        self.assertIn(("is_npc", True), kwargs["attributes"])


if __name__ == "__main__":
    unittest.main()
