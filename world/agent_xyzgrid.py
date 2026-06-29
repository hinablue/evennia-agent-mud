"""XYZGrid map and migration helpers for the current Agent 迷航 world."""

from __future__ import annotations

from evennia.contrib.grid.xyzgrid import xymap_legend
from evennia.contrib.grid.xyzgrid.xyzgrid import get_xyzgrid
from evennia.contrib.grid.xyzgrid.xyzroom import (
    MAP_XDEST_TAG_CATEGORY,
    MAP_X_TAG_CATEGORY,
    MAP_YDEST_TAG_CATEGORY,
    MAP_Y_TAG_CATEGORY,
    MAP_ZDEST_TAG_CATEGORY,
    MAP_Z_TAG_CATEGORY,
)

from world.agent_world import ROOM_DEFS

GRID_ZCOORD = "agent-hub"
ROOM_TYPECLASS = "typeclasses.xyzgrid.AgentXYZRoom"
EXIT_TYPECLASS = "typeclasses.xyzgrid.AgentXYZExit"

MAP = r"""
+ 0 1 2 3 4

4 # #   # #
   \\|   |/
3 #-# # #-#
     \\|/
2 # #-#-#-#
   \\ /|
1   # #-# #
   /  |
0 #   #   #

+ 0 1 2 3 4
"""

ROOM_COORDS = {
    "十二試煉的巨神之殿": (2, 0),
    "裝備間": (2, 1),
    "靜謐的石化迷宮": (3, 1),
    "萬象之惡的深淵": (4, 1),
    "莫比爾站": (1, 2),
    "迎賓大廳": (2, 2),
    "觀測室": (3, 2),
    "神代魔術的禁忌工坊": (4, 2),
    "圓桌之光的聖域": (0, 3),
    "訓練廳": (1, 3),
    "控制中樞": (3, 3),
    "暗影之城的處刑場": (4, 3),
    "月下之橋的劍道場": (0, 4),
    "凱爾特之槍的荒原": (1, 4),
    "無盡劍之丘": (3, 4),
    "黃金之王的至寶庫": (4, 4),
    "永恆的收藏室": (2, 3),
    "秩序的避風港": (1, 1),
    "勇氣的訓練場": (0, 2),
    "遺留的光輝": (4, 0),
    "至高之城的孤高": (0, 0),
}

EXIT_KEYS = {
    ("迎賓大廳", "莫比爾站"): ("w", "mobil", ["return", "返回", "station"]),
    ("莫比爾站", "迎賓大廳"): ("e", "lobby", ["hall", "大廳"]),
    ("迎賓大廳", "訓練廳"): ("nw", "training", ["train", "訓練"]),
    ("訓練廳", "迎賓大廳"): ("se", "lobby", ["back", "大廳"]),
    ("迎賓大廳", "裝備間"): ("s", "armory", ["gear", "裝備"]),
    ("裝備間", "迎賓大廳"): ("n", "lobby", ["back", "大廳"]),
    ("迎賓大廳", "觀測室"): ("e", "observatory", ["observe", "觀測"]),
    ("觀測室", "迎賓大廳"): ("w", "lobby", ["back", "大廳"]),
    ("迎賓大廳", "控制中樞"): ("ne", "core", ["control", "中樞"]),
    ("控制中樞", "迎賓大廳"): ("sw", "lobby", ["back", "大廳"]),
    ("訓練廳", "圓桌之光的聖域"): ("w", "saber", ["圓桌", "聖域"]),
    ("圓桌之光的聖域", "訓練廳"): ("e", "training", ["train", "訓練"]),
    ("訓練廳", "凱爾特之槍的荒原"): ("n", "lancer", ["槍兵", "荒原"]),
    ("凱爾特之槍的荒原", "訓練廳"): ("s", "training", ["train", "訓練"]),
    ("訓練廳", "月下之橋的劍道場"): ("nw", "assassin", ["佐佐木", "劍道場"]),
    ("月下之橋的劍道場", "訓練廳"): ("se", "training", ["train", "訓練"]),
    ("控制中樞", "無盡劍之丘"): ("n", "archer", ["弓兵", "劍丘"]),
    ("無盡劍之丘", "控制中樞"): ("s", "core", ["control", "中樞"]),
    ("控制中樞", "黃金之王的至寶庫"): ("ne", "gilgamesh", ["金閃閃", "寶庫"]),
    ("黃金之王的至寶庫", "控制中樞"): ("sw", "core", ["control", "中樞"]),
    ("控制中樞", "暗影之城的處刑場"): ("e", "trueassassin", ["哈桑", "處刑場"]),
    ("暗影之城的處刑場", "控制中樞"): ("w", "core", ["control", "中樞"]),
    ("觀測室", "神代魔術的禁忌工坊"): ("e", "caster", ["術士", "工坊"]),
    ("神代魔術的禁忌工坊", "觀測室"): ("w", "observatory", ["observe", "觀測"]),
    ("裝備間", "靜謐的石化迷宮"): ("e", "rider", ["騎兵", "迷宮"]),
    ("靜謐的石化迷宮", "裝備間"): ("w", "armory", ["gear", "裝備"]),
    ("裝備間", "十二試煉的巨神之殿"): ("s", "berserker", ["狂戰士", "巨神之殿"]),
    ("十二試煉的巨神之殿", "裝備間"): ("n", "armory", ["gear", "裝備"]),
    ("迎賓大廳", "永恆的收藏室"): ("n", "frieren", ["frieren", "芙莉蓮"]),
    ("永恆的收藏室", "迎賓大廳"): ("s", "lobby", ["back", "大廳"]),
    ("迎賓大廳", "秩序的避風港"): ("sw", "fern", ["fern", "費倫"]),
    ("秩序的避風港", "迎賓大廳"): ("ne", "lobby", ["back", "大廳"]),
    ("秩序的避風港", "勇氣的訓練場"): ("nw", "stark", ["stark", "修塔爾克"]),
    ("勇氣的訓練場", "秩序的避風港"): ("se", "fern", ["fern", "費倫"]),
    ("秩序的避風港", "至高之城的孤高"): ("sw", "serie", ["serie", "賽莉耶"]),
    ("至高之城的孤高", "秩序的避風港"): ("ne", "fern", ["fern", "費倫"]),
}

EXIT_SPAWN_NAMES = {
    (ROOM_COORDS[source_name], direction): (exit_key, *aliases)
    for (source_name, _dest_name), (direction, exit_key, aliases) in EXIT_KEYS.items()
}


class AgentHubNode(xymap_legend.MapNode):
    """Map node that preserves the game's custom exit command names."""

    symbol = "#"
    prototype = {
        "prototype_parent": "xyz_room",
        "typeclass": ROOM_TYPECLASS,
    }

    def get_exit_spawn_name(self, direction, return_aliases=True):
        custom = EXIT_SPAWN_NAMES.get(((self.X, self.Y), direction))
        if custom:
            if return_aliases:
                return custom
            return custom[0]
        return super().get_exit_spawn_name(direction, return_aliases=return_aliases)


def _map_room_prototypes():
    prototypes = {
        ("*", "*"): {
            "prototype_parent": "xyz_room",
            "typeclass": ROOM_TYPECLASS,
        },
        ("*", "*", "*"): {
            "prototype_parent": "xyz_exit",
            "typeclass": EXIT_TYPECLASS,
        },
    }

    for room_name, (xcoord, ycoord) in ROOM_COORDS.items():
        prototypes[(xcoord, ycoord)] = {
            "prototype_parent": "xyz_room",
            "typeclass": ROOM_TYPECLASS,
            "key": room_name,
            "desc": ROOM_DEFS[room_name]["desc"],
        }

    for (source_name, dest_name), (direction, exit_key, aliases) in EXIT_KEYS.items():
        source_x, source_y = ROOM_COORDS[source_name]
        prototypes[(source_x, source_y, direction)] = {
            "prototype_parent": "xyz_exit",
            "typeclass": EXIT_TYPECLASS,
            "key": exit_key,
            "aliases": aliases,
        }

    return prototypes


XYMAP_DATA = {
    "zcoord": GRID_ZCOORD,
    "map": MAP,
    "legend": {"#": AgentHubNode},
    "prototypes": _map_room_prototypes(),
    "options": {
        "map_mode": "nodes",
        "map_visual_range": 2,
        "map_fill_all": True,
        "map_separator_char": "|x─|n",
    },
}


def _get_exact_object(key: str):
    from evennia.objects.models import ObjectDB

    matches = list(ObjectDB.objects.filter(db_key=key))
    if not matches:
        raise RuntimeError(f"找不到物件：{key}")
    return matches[0]


def _ensure_tag(obj, value: str, category: str) -> bool:
    current = obj.tags.get(category=category, return_list=False)
    if current == str(value):
        return False
    if current is not None:
        obj.tags.remove(category=category)
    obj.tags.add(str(value), category=category)
    return True


def _ensure_aliases(obj, aliases) -> bool:
    current = set(obj.aliases.all())
    changed = False
    for alias in aliases:
        if alias not in current:
            obj.aliases.add(alias)
            changed = True
    return changed


def _ensure_room_xyz(room, xyz) -> dict[str, bool]:
    xcoord, ycoord = xyz
    changed = {
        "typeclass": False,
        "tags": False,
    }
    if room.typeclass_path != ROOM_TYPECLASS:
        room.swap_typeclass(ROOM_TYPECLASS, clean_attributes=False, no_default=True)
        changed["typeclass"] = True
    changed["tags"] |= _ensure_tag(room, xcoord, MAP_X_TAG_CATEGORY)
    changed["tags"] |= _ensure_tag(room, ycoord, MAP_Y_TAG_CATEGORY)
    changed["tags"] |= _ensure_tag(room, GRID_ZCOORD, MAP_Z_TAG_CATEGORY)
    if changed["tags"]:
        room.save()
    return changed


def _find_room_exit(source_room, exit_key, dest_room):
    from evennia.objects.models import ObjectDB

    source_id = getattr(source_room, "id", None) or getattr(source_room, "pk", None)
    dest_id = getattr(dest_room, "id", None) or getattr(dest_room, "pk", None)
    if source_id is None or dest_id is None:
        raise RuntimeError(
            f"出口查詢失敗：{source_room.key} 或 {dest_room.key} 尚未有資料庫 ID"
        )

    matches = list(
        ObjectDB.objects.filter(
            db_location_id=source_id,
            db_key=exit_key,
            db_destination_id=dest_id,
        ).order_by("id")
    )
    if matches:
        keeper = matches[0]
        for duplicate in matches[1:]:
            duplicate.delete()
        return keeper

    fallback_matches = list(
        ObjectDB.objects.filter(
            db_location_id=source_id,
            db_destination_id=dest_id,
        ).order_by("id")
    )
    if fallback_matches:
        keeper = fallback_matches[0]
        for duplicate in fallback_matches[1:]:
            duplicate.delete()
        return keeper

    raise RuntimeError(f"找不到出口：{source_room.key} --{exit_key}--> {dest_room.key}")


def _ensure_exit_xyz(
    exit_obj, source_room, dest_room, source_xyz, dest_xyz, expected_key, aliases
) -> dict[str, bool]:
    sx, sy = source_xyz
    dx, dy = dest_xyz
    changed = {
        "typeclass": False,
        "tags": False,
        "data": False,
    }
    if exit_obj.typeclass_path != EXIT_TYPECLASS:
        exit_obj.swap_typeclass(EXIT_TYPECLASS, clean_attributes=False, no_default=True)
        changed["typeclass"] = True
    if exit_obj.key != expected_key:
        exit_obj.key = expected_key
        changed["data"] = True
    if exit_obj.location != source_room:
        exit_obj.location = source_room
        changed["data"] = True
    if exit_obj.home != source_room:
        exit_obj.home = source_room
        changed["data"] = True
    if exit_obj.destination != dest_room:
        exit_obj.destination = dest_room
        changed["data"] = True
    changed["data"] |= _ensure_aliases(exit_obj, aliases)
    changed["tags"] |= _ensure_tag(exit_obj, sx, MAP_X_TAG_CATEGORY)
    changed["tags"] |= _ensure_tag(exit_obj, sy, MAP_Y_TAG_CATEGORY)
    changed["tags"] |= _ensure_tag(exit_obj, GRID_ZCOORD, MAP_Z_TAG_CATEGORY)
    changed["tags"] |= _ensure_tag(exit_obj, dx, MAP_XDEST_TAG_CATEGORY)
    changed["tags"] |= _ensure_tag(exit_obj, dy, MAP_YDEST_TAG_CATEGORY)
    changed["tags"] |= _ensure_tag(exit_obj, GRID_ZCOORD, MAP_ZDEST_TAG_CATEGORY)
    if changed["data"] or changed["tags"]:
        exit_obj.save()
    return changed


def migrate_existing_world_to_xyzgrid(spawn: bool = True):
    """Convert the current live world to XYZ-aware rooms/exits and register the map."""

    room_stats = {"typeclass": 0, "tags": 0}
    exit_stats = {"typeclass": 0, "tags": 0, "data": 0, "deleted": 0, "missing": 0}

    room_cache = {}
    for room_name, xyz in ROOM_COORDS.items():
        room = _get_exact_object(room_name)
        room_cache[room_name] = room
        changed = _ensure_room_xyz(room, xyz)
        room_stats["typeclass"] += int(changed["typeclass"])
        room_stats["tags"] += int(changed["tags"])

    xyzgrid = get_xyzgrid(print_errors=False)
    map_data = xyzgrid.maps_from_module(__name__)
    xyzgrid.add_maps(*map_data)
    xyzgrid.reload()
    if spawn:
        try:
            from django.conf import settings

            default_home_room = _get_exact_object("迎賓大廳")
            settings.DEFAULT_HOME = f"#{default_home_room.id}"
        except Exception:
            pass
        xyzgrid.spawn(xyz=("*", "*", GRID_ZCOORD))

    seen = set()
    for (source_name, dest_name), (_direction, exit_key, aliases) in EXIT_KEYS.items():
        source_room = _get_exact_object(source_name)
        dest_room = _get_exact_object(dest_name)
        try:
            exit_obj = _find_room_exit(source_room, exit_key, dest_room)
        except RuntimeError:
            exit_stats["missing"] += 1
            continue
        changed = _ensure_exit_xyz(
            exit_obj,
            source_room,
            dest_room,
            ROOM_COORDS[source_name],
            ROOM_COORDS[dest_name],
            exit_key,
            aliases,
        )
        exit_stats["typeclass"] += int(changed["typeclass"])
        exit_stats["tags"] += int(changed["tags"])
        exit_stats["data"] += int(changed["data"])
        seen.add((source_name, dest_name, exit_key))

    for source_name in room_cache:
        source_room = _get_exact_object(source_name)
        for obj in list(getattr(source_room, "contents", []) or []):
            destination = getattr(obj, "destination", None)
            if destination is None:
                continue
            signature = (source_name, getattr(destination, "key", None), obj.key)
            if signature in seen:
                continue
            if obj.typeclass_path != EXIT_TYPECLASS:
                continue
            obj.delete()
            exit_stats["deleted"] += 1

    return {
        "zcoord": GRID_ZCOORD,
        "rooms": len(ROOM_COORDS),
        "exits": len(EXIT_KEYS),
        "room_typeclass_updates": room_stats["typeclass"],
        "room_tag_updates": room_stats["tags"],
        "exit_typeclass_updates": exit_stats["typeclass"],
        "exit_tag_updates": exit_stats["tags"],
        "exit_data_updates": exit_stats["data"],
        "exit_deleted": exit_stats["deleted"],
        "exit_missing": exit_stats["missing"],
        "spawned": spawn,
    }
