"""Admin helpers for creating and managing NPC / LLMNPC objects."""

from __future__ import annotations

from dataclasses import dataclass

from evennia import create_object, search_object
from evennia.objects.models import ObjectDB
from evennia.utils.utils import inherits_from, make_iter

from typeclasses.llm_npc import DEFAULT_PROMPT_PREFIX
from typeclasses.npcs import LLMNPC, NPC


DEFAULT_NPC_DESC = "這是一名 NPC。"
DEFAULT_LLMNPC_DESC = "這是一名會回話的 NPC。"
NPC_COMBAT_DEFAULTS = {
    "npc_attackable": True,
    "npc_retaliates": True,
    "npc_can_die": True,
}
NPC_STAT_FIELDS = {
    "str": "base_str",
    "def": "base_def",
    "spirit": "base_spirit",
    "intel": "base_intel",
    "agility": "base_agility",
    "stamina": "base_stamina",
    "spd": "base_spd",
    "hp": "hp",
    "max_hp": "max_hp",
    "mp": "mp",
    "max_mp": "max_mp",
}


@dataclass
class NPCSpecError(ValueError):
    message: str

    def __str__(self):
        return self.message


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------


def _clean_text(value):
    return (value or "").strip()



def _normalize_aliases(aliases):
    seen = set()
    ordered = []
    for alias in make_iter(aliases or []):
        alias = _clean_text(alias)
        if alias and alias not in seen:
            ordered.append(alias)
            seen.add(alias)
    return ordered



def _format_list(items):
    items = [str(item) for item in items if item]
    return "、".join(items) if items else "無"



def _find_exact(key):
    key = _clean_text(key)
    if not key:
        return None
    matches = search_object(key, exact=True)
    return matches[0] if matches else None



def _get_room_or_error(room_name):
    room_name = _clean_text(room_name)
    if not room_name:
        raise NPCSpecError("請提供房間名稱。")
    room = _find_exact(room_name)
    if not room:
        raise NPCSpecError(f"房間不存在：{room_name}")
    if not inherits_from(room, "typeclasses.rooms.Room"):
        raise NPCSpecError(f"`{room_name}` 不是房間。")
    return room



def _get_npc_or_error(npc_key):
    npc_key = _clean_text(npc_key)
    if not npc_key:
        raise NPCSpecError("請提供 NPC 名稱。")
    obj = _find_exact(npc_key)
    if not obj:
        raise NPCSpecError(f"找不到 NPC：{npc_key}")
    if not _is_npc(obj):
        raise NPCSpecError(f"`{npc_key}` 不是受這顆工具管理的 NPC/LLMNPC。")
    return obj



def _current_aliases(obj):
    return list(obj.aliases.all()) if obj else []



def _find_room_name_for_obj(obj):
    location = getattr(obj, "location", None)
    return getattr(location, "key", "無") if location else "無"



def _is_llm_npc(obj):
    return bool(obj) and (
        getattr(obj.db, "npc_kind", None) == "llm"
        or inherits_from(obj, "typeclasses.npcs.LLMNPC")
        or inherits_from(obj, "typeclasses.llm_npc.LocalLLMNPC")
    )



def _is_npc(obj):
    return bool(obj) and (
        getattr(obj.db, "is_npc", False)
        or inherits_from(obj, "typeclasses.npcs.NPC")
        or _is_llm_npc(obj)
    )



def _npc_kind(obj):
    if _is_llm_npc(obj):
        return "llm"
    return "npc"



def _set_aliases(obj, aliases):
    aliases = _normalize_aliases(aliases)
    obj.aliases.clear()
    for alias in aliases:
        obj.aliases.add(alias)
    return aliases



def _truncate(text, limit=140):
    text = _clean_text(text)
    if len(text) <= limit:
        return text or "無"
    return text[: limit - 1] + "…"


def _format_combat_flags(obj):
    return (
        f"可被攻擊：{'是' if getattr(obj.db, 'npc_attackable', True) else '否'}｜"
        f"會反擊：{'是' if getattr(obj.db, 'npc_retaliates', True) else '否'}｜"
        f"可死亡：{'是' if getattr(obj.db, 'npc_can_die', True) else '否'}"
    )


def _format_npc_stats(obj):
    parts = []
    for public_key, attr_name in NPC_STAT_FIELDS.items():
        value = getattr(obj.db, attr_name, None)
        if value is None and hasattr(obj, 'get_stat') and public_key in {"str", "def", "spirit", "intel", "agility", "stamina", "spd"}:
            value = obj.get_stat(public_key)
        parts.append(f"{public_key}={value}")
    return "｜".join(parts)


# ---------------------------------------------------------------------------
# Summaries
# ---------------------------------------------------------------------------


def summarize_npc(npc_key):
    obj = _get_npc_or_error(npc_key)
    lines = [f"NPC：{obj.key}"]
    lines.append(f"- 類型：{_npc_kind(obj)}")
    lines.append(f"- 房間：{_find_room_name_for_obj(obj)}")
    lines.append(f"- aliases：{_format_list(_current_aliases(obj))}")
    lines.append(f"- 描述：{_clean_text(getattr(obj.db, 'desc', '')) or '無'}")
    lines.append(f"- 等級/重生：{_format_npc_level(obj)}")
    lines.append(f"- 戰鬥旗標：{_format_combat_flags(obj)}")
    lines.append(f"- 戰鬥數值：{_format_npc_stats(obj)}")
    lines.append(f"- 技能：{_format_list(getattr(obj.db, 'skills', []) or [])}")
    lines.append(f"- typeclass：{obj.typeclass_path}")
    if _is_llm_npc(obj):
        lines.append(f"- prompt：{_truncate(obj.attributes.get('prompt_prefix', default=DEFAULT_PROMPT_PREFIX), 180)}")
        lines.append(f"- LLM：{_format_llm_config(obj)}")
        memory_size = getattr(obj.db, "max_chat_memory_size", None)
        if memory_size in (None, ""):
            memory_size = getattr(obj, "max_chat_memory_size", 25)
        thinking_timeout = getattr(obj.db, "thinking_timeout", None)
        if thinking_timeout in (None, ""):
            thinking_timeout = getattr(obj, "thinking_timeout", 2)
        lines.append(f"- memory：{memory_size}")
        lines.append(f"- thinking_timeout：{thinking_timeout}")
        thinking_messages = obj.attributes.get("thinking_messages", default=getattr(obj, "thinking_messages", []))
        lines.append(f"- thinking_messages：{_format_list(thinking_messages)}")
    return "\n".join(lines)



def summarize_npcs(room_name=None):
    room = _get_room_or_error(room_name) if room_name else None
    matches = []
    for obj in ObjectDB.objects.all():
        if not _is_npc(obj):
            continue
        if room and obj.location != room:
            continue
        matches.append(obj)

    title = f"NPC 清單：{room.key}" if room else "NPC 清單：全世界"
    lines = [title]
    if not matches:
        lines.append("- 目前沒有找到受管理的 NPC。")
        return "\n".join(lines)

    def _sort_key(item):
        return (_find_room_name_for_obj(item), _npc_kind(item), item.key)

    for obj in sorted(matches, key=_sort_key):
        lines.append(
            f"- {obj.key}｜類型：{_npc_kind(obj)}｜房間：{_find_room_name_for_obj(obj)}｜aliases：{_format_list(_current_aliases(obj))}"
        )
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Mutations
# ---------------------------------------------------------------------------


def create_npc(kind, npc_key, room_name, desc=None, aliases=None, prompt_prefix=None):
    kind = _clean_text(kind).lower()
    npc_key = _clean_text(npc_key)
    if kind not in {"npc", "llm"}:
        raise NPCSpecError("create 只接受 `npc` 或 `llm`。")
    if not npc_key:
        raise NPCSpecError("create 需要 NPC 名稱。")
    if _find_exact(npc_key):
        raise NPCSpecError(f"同名物件已存在：{npc_key}")

    room = _get_room_or_error(room_name)
    aliases = _normalize_aliases(aliases)
    desc = _clean_text(desc) or (DEFAULT_LLMNPC_DESC if kind == "llm" else DEFAULT_NPC_DESC)
    typeclass = LLMNPC if kind == "llm" else NPC

    attributes = [("desc", desc), ("is_npc", True), ("npc_kind", kind)]
    for attr_name, value in NPC_COMBAT_DEFAULTS.items():
        attributes.append((attr_name, value))
    if kind == "llm":
        attributes.append(("prompt_prefix", _clean_text(prompt_prefix) or DEFAULT_PROMPT_PREFIX))

    obj = create_object(
        typeclass,
        key=npc_key,
        location=room,
        home=room,
        aliases=aliases,
        attributes=attributes,
    )
    return {
        "npc": obj,
        "message": f"已建立 {kind.upper()} `{npc_key}`，目前位於 `{room.key}`。這是 live 世界變更。",
    }



def move_npc(npc_key, room_name):
    obj = _get_npc_or_error(npc_key)
    room = _get_room_or_error(room_name)
    obj.location = room
    obj.home = room
    obj.save()
    return {
        "npc": obj,
        "message": f"已將 `{obj.key}` 移到 `{room.key}`。這是 live 世界變更。",
    }



def set_npc_desc(npc_key, desc):
    obj = _get_npc_or_error(npc_key)
    desc = _clean_text(desc)
    if not desc:
        raise NPCSpecError("desc 需要新的描述。")
    obj.db.desc = desc
    obj.save()
    return {
        "npc": obj,
        "message": f"已更新 `{obj.key}` 的描述。",
    }



def set_npc_aliases(npc_key, aliases):
    obj = _get_npc_or_error(npc_key)
    aliases = _normalize_aliases(aliases)
    if not aliases:
        raise NPCSpecError("aliases 需要至少一個 alias。")
    aliases = _set_aliases(obj, aliases)
    obj.save()
    return {
        "npc": obj,
        "message": f"已更新 `{obj.key}` 的 aliases：{_format_list(aliases)}。",
    }



def set_llm_prompt(npc_key, prompt_prefix):
    obj = _get_npc_or_error(npc_key)
    if not _is_llm_npc(obj):
        raise NPCSpecError(f"`{obj.key}` 不是 LLMNPC，不能設定 prompt。")
    prompt_prefix = _clean_text(prompt_prefix)
    if not prompt_prefix:
        raise NPCSpecError("prompt 需要新的 prompt prefix。")
    obj.attributes.add("prompt_prefix", prompt_prefix)
    obj.save()
    return {
        "npc": obj,
        "message": f"已更新 `{obj.key}` 的 LLM prompt。",
    }



def set_llm_thinking(npc_key, timeout, messages=None):
    obj = _get_npc_or_error(npc_key)
    if not _is_llm_npc(obj):
        raise NPCSpecError(f"`{obj.key}` 不是 LLMNPC，不能設定 thinking。")
    try:
        timeout_value = float(timeout)
    except (TypeError, ValueError) as exc:
        raise NPCSpecError("thinking 的第一段需要是秒數，例如 `2.5`。") from exc
    if timeout_value < 0:
        raise NPCSpecError("thinking timeout 不能小於 0。")
    obj.attributes.add("thinking_timeout", timeout_value)
    clean_messages = [msg for msg in (_clean_text(item) for item in (messages or [])) if msg]
    if clean_messages:
        obj.attributes.add("thinking_messages", clean_messages)
    obj.save()
    return {
        "npc": obj,
        "message": (
            f"已更新 `{obj.key}` 的 thinking 設定：timeout={timeout_value} 秒"
            + (f"，messages={_format_list(clean_messages)}。" if clean_messages else "。")
        ),
    }


def set_npc_combat_flags(npc_key, attackable=None, retaliates=None, can_die=None):
    obj = _get_npc_or_error(npc_key)
    updates = {}
    if attackable is not None:
        updates["npc_attackable"] = bool(attackable)
    if retaliates is not None:
        updates["npc_retaliates"] = bool(retaliates)
    if can_die is not None:
        updates["npc_can_die"] = bool(can_die)
    if not updates:
        raise NPCSpecError("flags 至少要提供一個設定。")
    for key, value in updates.items():
        setattr(obj.db, key, value)
    obj.save()
    return {"npc": obj, "message": f"已更新 `{obj.key}` 的戰鬥旗標：{_format_combat_flags(obj)}。"}


def set_npc_stats(npc_key, stat_updates):
    obj = _get_npc_or_error(npc_key)
    if not stat_updates:
        raise NPCSpecError("stats 至少要提供一個數值，例如 `str=20,mp=40`。")
    applied = []
    for public_key, raw_value in stat_updates.items():
        attr_name = NPC_STAT_FIELDS.get(public_key)
        if not attr_name:
            raise NPCSpecError(f"不支援的屬性：{public_key}")
        try:
            value = int(raw_value)
        except (TypeError, ValueError) as exc:
            raise NPCSpecError(f"{public_key} 需要整數。") from exc
        setattr(obj.db, attr_name, value)
        applied.append(f"{public_key}={value}")
    obj.save()
    return {"npc": obj, "message": f"已更新 `{obj.key}` 的戰鬥數值：{'、'.join(applied)}。"}


def set_npc_skills(npc_key, skills):
    obj = _get_npc_or_error(npc_key)
    clean_skills = [skill for skill in (_clean_text(item) for item in (skills or [])) if skill]
    obj.db.skills = clean_skills
    obj.save()
    return {"npc": obj, "message": f"已更新 `{obj.key}` 的技能：{_format_list(clean_skills)}。"}


def _format_llm_config(obj):
    """Format LLM configuration for display."""
    parts = []
    llm_host = getattr(obj.db, "llm_host", None)
    llm_api_key = getattr(obj.db, "llm_api_key", None)
    llm_model = getattr(obj.db, "llm_model", None)
    if llm_host:
        parts.append(f"host={llm_host}")
    if llm_api_key:
        # Mask API key for display
        masked = llm_api_key[:4] + "***" + llm_api_key[-4:] if len(llm_api_key) > 8 else "***"
        parts.append(f"api_key={masked}")
    if llm_model:
        parts.append(f"model={llm_model}")
    return "｜".join(parts) if parts else "使用預設設定"


def set_llm_config(npc_key, base_url=None, model=None, api_key=None):
    """Set LLM configuration for an LLMNPC."""
    obj = _get_npc_or_error(npc_key)
    if not _is_llm_npc(obj):
        raise NPCSpecError(f"`{npc_key}` 不是 LLMNPC，不能設定 LLM 參數。")
    updates = []
    if base_url is not None:
        obj.db.llm_host = base_url
        updates.append(f"host={base_url}")
    if model is not None:
        obj.db.llm_model = model
        updates.append(f"model={model}")
    if api_key is not None:
        obj.db.llm_api_key = api_key
        updates.append("api_key=***(已設定)")
    if not updates:
        raise NPCSpecError("llm 至少要提供一個設定：base_url、model 或 api_key。")
    # Clear cached client so it picks up new settings
    if hasattr(obj, "ndb") and getattr(obj.ndb, "llm_client", None):
        obj.ndb.llm_client = None
    obj.save()
    return {
        "npc": obj,
        "message": f"已更新 `{obj.key}` 的 LLM 設定：{'、'.join(updates)}。",
    }


def get_llm_config(npc_key):
    """Get LLM configuration for an LLMNPC."""
    obj = _get_npc_or_error(npc_key)
    if not _is_llm_npc(obj):
        raise NPCSpecError(f"`{npc_key}` 不是 LLMNPC。")
    lines = [f"LLM 設定：{obj.key}"]
    lines.append(f"- host：{getattr(obj.db, 'llm_host', '（預設）')}")
    lines.append(f"- model：{getattr(obj.db, 'llm_model', '（預設）')}")
    api_key = getattr(obj.db, "llm_api_key", None)
    if api_key:
        lines.append(f"- api_key：{api_key[:4]}***{api_key[-4:]}")
    else:
        lines.append("- api_key：（未設定）")
    return "\n".join(lines)


def delete_npc(npc_key):
    obj = _get_npc_or_error(npc_key)
    key = obj.key
    obj.delete()
    return {
        "message": f"已刪除 `{key}`。",
    }


def set_npc_level(npc_key, level_str):
    """設定 NPC 等級，會套用屬性倍率並重算 HP/MP。"""
    obj = _get_npc_or_error(npc_key)
    try:
        level = int(level_str)
    except (TypeError, ValueError) as exc:
        raise NPCSpecError("level 需要一個整數，例如 `5`。") from exc
    if level < 1:
        raise NPCSpecError("level 不能小於 1。")
    obj.db.level = level
    if hasattr(obj, "_apply_level_stats"):
        obj._apply_level_stats()
    else:
        obj.save()
    return {
        "npc": obj,
        "message": f"已設定 `{obj.key}` 等級為 {level}，屬性已套用倍率。",
    }


def set_npc_cooldown(npc_key, cooldown_str):
    """設定 NPC 死亡/逃跑後的冷卻重生秒數。"""
    obj = _get_npc_or_error(npc_key)
    try:
        cooldown = int(cooldown_str)
    except (TypeError, ValueError) as exc:
        raise NPCSpecError("cooldown 需要一個整數（秒），例如 `120`。") from exc
    if cooldown < 0:
        raise NPCSpecError("cooldown 不能為負數。")
    obj.db.npc_cooldown = cooldown
    obj.save()
    return {
        "npc": obj,
        "message": f"已設定 `{obj.key}` 的重生冷卻為 {cooldown} 秒。",
    }


def set_npc_tokens(npc_key, min_str, max_str):
    """設定 NPC Token 掉落範圍。"""
    obj = _get_npc_or_error(npc_key)
    try:
        tmin = int(min_str)
        tmax = int(max_str)
    except (TypeError, ValueError) as exc:
        raise NPCSpecError("tokens 需要兩個整數：`最小,最大`，例如 `3,15`。") from exc
    if tmin < 0 or tmax < 0:
        raise NPCSpecError("Token 數量不能為負數。")
    if tmin > tmax:
        raise NPCSpecError("最小值不能大於最大值。")
    obj.db.npc_token_min = tmin
    obj.db.npc_token_max = tmax
    obj.save()
    return {
        "npc": obj,
        "message": f"已設定 `{obj.key}` 的 Token 掉落範圍為 {tmin}~{tmax}。",
    }


def set_npc_flee(npc_key, enable_str, fail_chance_str=None):
    """設定 NPC 逃跑功能與失敗率。"""
    obj = _get_npc_or_error(npc_key)
    enable = enable_str.lower() in ("on", "true", "1", "yes")
    fail_chance = None
    if fail_chance_str is not None:
        try:
            fail_chance = float(fail_chance_str)
            if not (0.0 <= fail_chance <= 1.0):
                raise NPCSpecError("fail_chance 必須在 0~1 之間，例如 `0.3`。")
        except (TypeError, ValueError) as exc:
            raise NPCSpecError("fail_chance 需要一個 0~1 的小數。") from exc
    obj.db.npc_can_flee = enable
    if fail_chance is not None:
        obj.db.npc_flee_chance = fail_chance
    obj.save()
    parts = [f"逃跑功能：{'開' if enable else '關'}"]
    if fail_chance is not None:
        parts.append(f"失敗率：{fail_chance:.0%}")
    return {
        "npc": obj,
        "message": f"已更新 `{obj.key}` 的逃跑設定：{'、'.join(parts)}。",
    }


def set_npc_aggro(npc_key, chance_str):
    """設定 NPC 被 look 時主動攻擊的機率。"""
    obj = _get_npc_or_error(npc_key)
    try:
        chance = float(chance_str)
        if not (0.0 <= chance <= 1.0):
            raise NPCSpecError("aggro 機率必須在 0~1 之間，例如 `0.15` 代表 15% 機率。")
    except (TypeError, ValueError) as exc:
        raise NPCSpecError("aggro 需要一個 0~1 的小數，例如 `0.15`。") from exc
    obj.db.npc_aggro_chance = chance
    obj.save()
    return {
        "npc": obj,
        "message": f"已設定 `{obj.key}` 的被 look 主動攻擊機率為 {chance:.0%}。",
    }


def _format_npc_level(obj):
    """Format NPC level and cooldown for display."""
    level = getattr(obj.db, "level", 1)
    cooldown = getattr(obj.db, "npc_cooldown", 60)
    in_cooldown = False
    remaining = 0
    if hasattr(obj, "is_in_cooldown"):
        in_cooldown = obj.is_in_cooldown()
        remaining = obj.get_cooldown_remaining()
    token_min = getattr(obj.db, "npc_token_min", 1)
    token_max = getattr(obj.db, "npc_token_max", 5)
    can_flee = getattr(obj.db, "npc_can_flee", True)
    flee_chance = getattr(obj.db, "npc_flee_chance", 0.20)
    aggro = getattr(obj.db, "npc_aggro_chance", 0.0)
    parts = [
        f"等級：{level}",
        f"冷卻：{cooldown}秒{'（重生中，剩餘 %d 秒）' % remaining if in_cooldown else '（不在冷卻）'}",
        f"Token：{token_min}~{token_max}",
        f"逃跑：{'是' if can_flee else '否'}（失敗率 {flee_chance:.0%}）",
        f"主動攻擊：{aggro:.0%}",
    ]
    return "｜".join(parts)
