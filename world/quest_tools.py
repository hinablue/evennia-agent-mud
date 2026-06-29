"""Admin helpers for managing Game Quests."""
from __future__ import annotations
from evennia import search_object
from dataclasses import dataclass

@dataclass
class QuestSpecError(ValueError):
    message: str
    def __str__(self):
        return self.message

def _clean_text(value):
    return (value or "").strip()

def _get_player_or_error(char_key):
    char_key = _clean_text(char_key)
    if not char_key:
        raise QuestSpecError("請提供角色名稱。")
    matches = search_object(char_key, exact=True)
    if not matches:
        raise QuestSpecError(f"找不到角色：{char_key}")
    return matches[0]

def give_quest(char_key, quest_key):
    char = _get_player_or_error(char_key)
    active = getattr(char.db, "active_quests", [])
    if not isinstance(active, list):
        active = []
    
    if quest_key in active:
        raise QuestSpecError(f"角色 `{char.key}` 已經擁有任務 `{quest_key}`。")
    
    active.append(quest_key)
    char.db.active_quests = active
    char.save()
    return {"message": f"已將任務 `{quest_key}` 強制發放給 `{char.key}`。"}

def complete_quest(char_key, quest_key):
    char = _get_player_or_error(char_key)
    active = getattr(char.db, "active_quests", [])
    if not isinstance(active, list):
        active = []
        
    if quest_key not in active:
        raise QuestSpecError(f"角色 `{char.key}` 目前沒有進行中的任務 `{quest_key}`。")
    
    active.remove(quest_key)
    char.db.active_quests = active
    
    completed = getattr(char.db, "completed_quests", [])
    if not isinstance(completed, list):
        completed = []
    completed.append(quest_key)
    char.db.completed_quests = completed
    
    char.save()
    return {"message": f"已將任務 `{quest_key}` 標記為 `{char.key}` 已完成。"}

def summarize_quests(char_key):
    char = _get_player_or_error(char_key)
    active = getattr(char.db, "active_quests", []) or "無"
    completed = getattr(char.db, "completed_quests", []) or "無"
    
    lines = [f"Quest 狀態：{char.key}"]
    lines.append(f"- 進行中：{', '.join(active) if isinstance(active, list) else active}")
    lines.append(f"- 已完成：{', '.join(completed) if isinstance(completed, list) else completed}")
    return "\n".join(lines)
