"""XYZGrid-aware room and exit typeclasses for Agent 迷航。"""

from evennia.contrib.grid.xyzgrid.xyzroom import XYZExit, XYZRoom

from .exits import Exit
from .rooms import Room


class AgentXYZRoom(XYZRoom, Room):
    """XYZ-aware version of the game's main room typeclass."""

    map_mode = "nodes"
    map_visual_range = 2
    map_fill_all = True
    map_separator_char = "|x─|n"
    fallback_desc = Room.fallback_desc


class AgentXYZExit(XYZExit, Exit):
    """XYZ-aware version of the game's main exit typeclass."""

    default_description = Exit.default_description
