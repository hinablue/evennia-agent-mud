"""Live room management helpers."""

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
        rooms = [obj for obj in Room.objects.all() if inherits_from(obj, "typeclasses.rooms.Room")]
        query = RoomTools._clean(query).lower()
        if query:
            rooms = [room for room in rooms if query in room.key.lower()]
        lines = ["Rooms found:"]
        for room in sorted(rooms, key=lambda item: item.key):
            pvp = "ON" if RoomTools._room_pvp_enabled(room) else "OFF"
            lines.append(f"- {room.key} (ID: {room.id}, PVP: {pvp})")
        return "\n".join(lines) if len(lines) > 1 else "No rooms found."

    @staticmethod
    def create_room(name, desc):
        name = RoomTools._clean(name)
        if not name:
            return "Room name is required."
        if RoomTools._find_object(name):
            return f"Object already exists: {name}."
        room = create_object(Room, key=name)
        room.db.desc = RoomTools._clean(desc) or Room.fallback_desc
        room.db.pvp_enabled = False
        room.save()
        return f"Room '{name}' created successfully."

    @staticmethod
    def update_desc(room_name, new_desc):
        room = RoomTools._find_room(room_name)
        if not room:
            return "Room not found."
        room.db.desc = RoomTools._clean(new_desc) or Room.fallback_desc
        room.save()
        return f"Description for {room.key} updated."

    @staticmethod
    def move_object(obj_name, room_name):
        obj = RoomTools._find_object(obj_name)
        room = RoomTools._find_room(room_name)
        if not obj or not room:
            return "Object or Room not found."
        obj.location = room
        obj.save()
        return f"Moved {obj.key} to {room.key}."

    @staticmethod
    def delete_room(room_name):
        room = RoomTools._find_room(room_name)
        if not room:
            return "Room not found."
        key = room.key
        room.delete()
        return f"Room {key} deleted."

    @staticmethod
    def set_door_state(room_name, direction, state):
        room = RoomTools._find_room(room_name)
        direction = RoomTools._clean(direction)
        state = RoomTools._clean(state)
        if not room:
            return "Room not found."
        if not direction or not state:
            return "Direction and state are required."

        door = None
        for obj in room.contents:
            if inherits_from(obj, "typeclasses.doors.DoorObject") and getattr(obj.db, "direction", None) == direction:
                door = obj
                break

        if not door:
            door = create_object(DoorObject, key=f"Door-{direction}", location=room, home=room)
            door.db.direction = direction
        door.db.state = state
        door.save()
        return f"Door {direction} in {room.key} is now {state} (DoorObject ID: {door.id})."

    @staticmethod
    def set_pvp_state(room_name, enabled):
        room = RoomTools._find_room(room_name)
        if not room:
            return "Room not found."
        room.db.pvp_enabled = bool(enabled)
        room.save()
        state = "ON" if room.db.pvp_enabled else "OFF"
        return f"Room {room.key} PVP is now {state}."

    @staticmethod
    def summarize_room(room_name):
        room = RoomTools._find_room(room_name)
        if not room:
            return "Room not found."
        pvp = "ON" if RoomTools._room_pvp_enabled(room) else "OFF"
        desc = getattr(room.db, "desc", Room.fallback_desc) or Room.fallback_desc
        return f"Room：{room.key}\n- ID：{room.id}\n- PVP：{pvp}\n- 描述：{desc}"
