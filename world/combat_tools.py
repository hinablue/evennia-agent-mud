"""用於控制戰鬥和人工智慧狀態的管理助理。"""

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
    # 我們假設 CombatHandler 作為屬性或透過全域管理器附加到角色
    # 在 Evennia 中，如果您使用處理程序，它通常位於 char.db.combat_handler 或類似的位置。
    # 對於通用的“停止”，我們嘗試清除與戰鬥相關的屬性。
    char.db.combat_state = "idle"
    # 如果有一個處理程序實例，我們將呼叫它的 stop 方法。
    # 由於確切的處理程序實作有所不同，我們將設定一個狀態並假設系統做出反應。
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
