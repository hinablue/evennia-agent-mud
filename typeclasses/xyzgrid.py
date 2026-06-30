"""XYZGrid-aware room and exit typeclasses for Agent 迷航。"""

from evennia.contrib.grid.xyzgrid.xyzroom import XYZExit, XYZRoom

from .exits import Exit
from .rooms import Room


class AgentXYZRoom(XYZRoom, Room):
    """遊戲主要房間類型的 XYZ 感知版本。"""

    map_mode = "nodes"
    map_visual_range = 2
    map_fill_all = True
    map_separator_char = "|x─|n"
    fallback_desc = Room.fallback_desc


class AgentXYZExit(XYZExit, Exit):
    """遊戲主要退出類型類別的 XYZ 感知版本。"""

    default_description = Exit.default_description
