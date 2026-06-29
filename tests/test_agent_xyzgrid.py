import unittest
from unittest.mock import MagicMock
import sys
from types import ModuleType

mock_settings = ModuleType("settings")
mock_settings.CHANNEL_LOG_NUM_TAIL_LINES = 100
sys.modules["django.conf.settings"] = mock_settings

evennia = ModuleType("evennia")
evennia.create_object = MagicMock()
evennia.search_object = MagicMock()
sys.modules["evennia"] = evennia

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

sys.modules["typeclasses.exits"] = ModuleType("typeclasses.exits")
sys.modules["typeclasses.exits"].Exit = MagicMock()
sys.modules["typeclasses.objects"] = ModuleType("typeclasses.objects")
sys.modules["typeclasses.objects"].Object = MagicMock()
sys.modules["typeclasses.rooms"] = ModuleType("typeclasses.rooms")
sys.modules["typeclasses.rooms"].Room = MagicMock()

from world.agent_xyzgrid import ROOM_COORDS, EXIT_KEYS, GRID_ZCOORD


class TestAgentXYZGrid(unittest.TestCase):
    def test_room_coords_consistency(self):
        for room_name, coord in ROOM_COORDS.items():
            self.assertIsInstance(coord, tuple)
            self.assertEqual(len(coord), 2)

    def test_exit_keys_endpoints(self):
        for source, dest in EXIT_KEYS.keys():
            self.assertIn(source, ROOM_COORDS)
            self.assertIn(dest, ROOM_COORDS)

    def test_exit_definition_structure(self):
        for (source, dest), data in EXIT_KEYS.items():
            self.assertEqual(len(data), 3)
            self.assertIsInstance(data[0], str)
            self.assertIsInstance(data[1], str)
            self.assertIsInstance(data[2], list)

    def test_grid_zcoord_value(self):
        self.assertEqual(GRID_ZCOORD, "agent-hub")


if __name__ == "__main__":
    unittest.main()
