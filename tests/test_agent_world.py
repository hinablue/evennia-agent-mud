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
sys.modules["typeclasses.objects"] = ModuleType("typeclasses.objects")
sys.modules["typeclasses.objects"].Object = MagicMock()
sys.modules["typeclasses.rooms"] = ModuleType("typeclasses.rooms")
sys.modules["typeclasses.rooms"].Room = MagicMock()

from world.agent_world import ROOM_DEFS, LIMBO_ROOM_KEY


class TestAgentWorld(unittest.TestCase):
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


if __name__ == "__main__":
    unittest.main()
