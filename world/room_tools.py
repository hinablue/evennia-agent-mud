"""直播間管理好幫手。"""

from __future__ import annotations

from evennia import create_object, search_object
from evennia.utils.utils import inherits_from

from typeclasses.doors import DoorObject
from typeclasses.rooms import Room


class RoomTools:
    @staticmethod
    def _clean(value):
        return (value or "").strip()

    @staticmethod
    def _find_room(room_name):
        room_name = RoomTools._clean(room_name)
        if not room_name:
            return None
        matches = search_object(room_name, exact=True)
        room = matches[0] if matches else None
        if room and inherits_from(room, "typeclasses.rooms.Room"):
            return room
        return None

    @staticmethod
    def _find_object(obj_name):
        obj_name = RoomTools._clean(obj_name)
        if not obj_name:
            return None
        matches = search_object(obj_name, exact=True)
        return matches[0] if matches else None

    @staticmethod
    def _room_pvp_enabled(room):
        return bool(getattr(room.db, "pvp_enabled", False))

    @staticmethod
    def list_rooms(query=None):
        rooms = [
            obj
            for obj in Room.objects.all()
            if inherits_from(obj, "typeclasses.rooms.Room")
        ]
        query = RoomTools._clean(query).lower()
        if query:
            rooms = [room for room in rooms if query in room.key.lower()]
        lines = ["Rooms found:"]
        for room in sorted(rooms, key=lambda item: item.key):
            pvp = "ON" if RoomTools._room_pvp_enabled(room) else "OFF"
            lines.append(f"- {room.key} (ID: {room.id}, PVP: {pvp})")
        return "\n".join(lines) if len(lines) > 1 else "沒有找到房間。"

    @staticmethod
    def create_room(name, desc):
        name = RoomTools._clean(name)
        if not name:
            return "需要房間名稱。"
        if RoomTools._find_object(name):
            return f"物件已存在：{name}。"
        room = create_object(Room, key=name)
        room.db.desc = RoomTools._clean(desc) or Room.fallback_desc
        room.db.pvp_enabled = False
        room.save()
        return f"房間 '{name}' 建立成功。"

    @staticmethod
    def update_desc(room_name, new_desc):
        room = RoomTools._find_room(room_name)
        if not room:
            return "房間不存在。"
        room.db.desc = RoomTools._clean(new_desc) or Room.fallback_desc
        room.save()
        return f"房間 {room.key} 描述更新。"

    @staticmethod
    def move_object(obj_name, room_name):
        obj = RoomTools._find_object(obj_name)
        room = RoomTools._find_room(room_name)
        if not obj or not room:
            return "物件或房間不存在。"
        obj.location = room
        obj.save()
        return f"移動 {obj.key} 到 {room.key}。"

    @staticmethod
    def delete_room(room_name):
        room = RoomTools._find_room(room_name)
        if not room:
            return "房間不存在。"
        key = room.key
        room.delete()
        return f"房間 {key} 刪除。"

    @staticmethod
    def set_door_state(room_name, direction, state):
        room = RoomTools._find_room(room_name)
        direction = RoomTools._clean(direction)
        state = RoomTools._clean(state)
        if not room:
            return "房間不存在。"
        if not direction or not state:
            return "需要方向和狀態。"

        door = None
        for obj in room.contents:
            if (
                inherits_from(obj, "typeclasses.doors.DoorObject")
                and getattr(obj.db, "direction", None) == direction
            ):
                door = obj
                break

        if not door:
            door = create_object(
                DoorObject, key=f"Door-{direction}", location=room, home=room
            )
            door.db.direction = direction
        door.db.state = state
        door.save()
        return (
            f"門 {direction} 在 {room.key} 現在 {state} (DoorObject ID: {door.id})。"
        )

    @staticmethod
    def set_pvp_state(room_name, enabled):
        room = RoomTools._find_room(room_name)
        if not room:
            return "房間不存在。"
        room.db.pvp_enabled = bool(enabled)
        room.save()
        state = "ON" if room.db.pvp_enabled else "OFF"
        return f"房間 {room.key} PVP 現在 {state}。"

    @staticmethod
    def summarize_room(room_name):
        room = RoomTools._find_room(room_name)
        if not room:
            return "房間不存在。"
        pvp = "ON" if RoomTools._room_pvp_enabled(room) else "OFF"
        desc = getattr(room.db, "desc", Room.fallback_desc) or Room.fallback_desc
        return f"房間：{room.key}\n- ID：{room.id}\n- PVP：{pvp}\n- 描述：{desc}"
