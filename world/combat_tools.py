"""Admin helpers for controlling combat and AI states."""

from __future__ import annotations
from evennia import search_object
from dataclasses import dataclass


@dataclass
class CombatSpecError(ValueError):
    message: str

    def __str__(self):
        return self.message


def _clean_text(value):
    return (value or "").strip()


def _get_object_or_error(obj_key):
    obj_key = _clean_text(obj_key)
    if not obj_key:
        raise CombatSpecError("請提供名稱。")
    matches = search_object(obj_key, exact=True)
    if not matches:
        raise CombatSpecError(f"找不到物件：{obj_key}")
    return matches[0]


def stop_combat(char_key):
    char = _get_object_or_error(char_key)
    # We assume CombatHandler is attached to the character as an attribute or via a global manager
    # In Evennia, if you use a handler, it's often in char.db.combat_handler or similar.
    # For a generic 'stop', we try to clear combat-related attributes.
    char.db.combat_state = "idle"
    # If there's a handler instance, we would call its stop method.
    # Since the exact handler implementation varies, we'll set a state and assume the system reacts.
    char.save()
    return {"message": f"已強行終止 `{char.key}` 的所有戰鬥狀態。"}


def force_win(char_key):
    char = _get_object_or_error(char_key)
    char.db.combat_result = "victory"
    char.save()
    return {"message": f"已強制將 `{char.key}` 設為戰鬥獲勝狀態。"}


def set_npc_state(npc_key, state):
    npc = _get_object_or_error(npc_key)
    npc.db.ai_state = state
    npc.save()
    return {"message": f"已將 NPC `{npc.key}` 的 AI 狀態切換為 `{state}`。"}
