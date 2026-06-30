"""Admin helpers for creating and managing player Character objects."""

from __future__ import annotations

from dataclasses import dataclass

from evennia import create_object, search_account, search_object
from evennia.accounts.models import AccountDB
from evennia.objects.models import ObjectDB
from evennia.utils.utils import inherits_from, make_iter

from typeclasses.characters import Character
from world.account_tools import ensure_first_player_account_is_gm


DEFAULT_PLAYER_DESC = "這是一名旅人。"


@dataclass
class PlayerSpecError(ValueError):
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


def _find_exact_object(key):
    key = _clean_text(key)
    if not key:
        return None
    matches = search_object(key, exact=True)
    return matches[0] if matches else None


def _get_room_or_error(room_name):
    room_name = _clean_text(room_name)
    if not room_name:
        raise PlayerSpecError("請提供房間名稱。")
    room = _find_exact_object(room_name)
    if not room:
        raise PlayerSpecError(f"房間不存在：{room_name}")
    if not inherits_from(room, "typeclasses.rooms.Room"):
        raise PlayerSpecError(f"`{room_name}` 不是房間。")
    return room


def _find_exact_account(account_name):
    account_name = _clean_text(account_name)
    if not account_name:
        return None
    matches = [
        account
        for account in search_account(account_name)
        if account.key.lower() == account_name.lower()
    ]
    return matches[0] if matches else None


def _get_account_or_error(account_name):
    account_name = _clean_text(account_name)
    if not account_name:
        raise PlayerSpecError("請提供帳號名稱。")
    account = _find_exact_account(account_name)
    if not account:
        raise PlayerSpecError(f"找不到帳號：{account_name}")
    return account


def _player_accounts(obj):
    owners = []
    for account in AccountDB.objects.all():
        try:
            playable = list(account.characters.all())
        except Exception:
            playable = list(account.db._playable_characters or [])
        if obj in playable:
            owners.append(account)
    return owners


def _is_player_character(obj):
    return (
        bool(obj)
        and inherits_from(obj, "typeclasses.characters.Character")
        and not getattr(obj.db, "is_npc", False)
    )


def _get_player_or_error(char_key):
    char_key = _clean_text(char_key)
    if not char_key:
        raise PlayerSpecError("請提供角色名稱。")
    obj = _find_exact_object(char_key)
    if not obj:
        raise PlayerSpecError(f"找不到角色：{char_key}")
    if not _is_player_character(obj):
        raise PlayerSpecError(f"`{char_key}` 不是玩家角色 Character。")
    return obj


def _current_aliases(obj):
    return list(obj.aliases.all()) if obj else []


def _find_room_name_for_obj(obj):
    location = getattr(obj, "location", None)
    return getattr(location, "key", "無") if location else "無"


def _set_aliases(obj, aliases):
    aliases = _normalize_aliases(aliases)
    obj.aliases.clear()
    for alias in aliases:
        obj.aliases.add(alias)
    return aliases


def _add_aliases(obj, aliases):
    current = _current_aliases(obj)
    merged = _normalize_aliases(list(current) + list(aliases or []))
    obj.aliases.clear()
    for alias in merged:
        obj.aliases.add(alias)
    return merged


def _remove_aliases(obj, aliases):
    current = _current_aliases(obj)
    remove_set = {alias for alias in _normalize_aliases(aliases)}
    kept = [alias for alias in current if alias not in remove_set]
    obj.aliases.clear()
    for alias in kept:
        obj.aliases.add(alias)
    return kept


def _truncate(text, limit=160):
    text = _clean_text(text)
    if len(text) <= limit:
        return text or "無"
    return text[: limit - 1] + "…"


def _apply_character_owner_locks(character, owners):
    owners = list(dict.fromkeys(owner for owner in owners if owner))
    puppet_parts = (
        [f"id({character.id})"]
        + [f"pid({owner.id})" for owner in owners]
        + ["perm(Developer)", "pperm(Developer)"]
    )
    delete_parts = [f"id({owner.id})" for owner in owners] + ["perm(Admin)"]
    character.locks.add(
        f"puppet:{' or '.join(puppet_parts)};delete:{' or '.join(delete_parts)}"
    )


# ---------------------------------------------------------------------------
# Summaries
# ---------------------------------------------------------------------------


def summarize_player(char_key):
    obj = _get_player_or_error(char_key)
    owners = _player_accounts(obj)
    lines = [f"Player：{obj.key}"]
    lines.append(f"- 房間：{_find_room_name_for_obj(obj)}")
    lines.append(
        f"- home：{getattr(getattr(obj, 'home', None), 'key', '無') if getattr(obj, 'home', None) else '無'}"
    )
    lines.append(f"- aliases：{_format_list(_current_aliases(obj))}")
    lines.append(f"- 描述：{_clean_text(getattr(obj.db, 'desc', '')) or '無'}")
    lines.append(f"- 擁有帳號：{_format_list(account.key for account in owners)}")
    lines.append(f"- typeclass：{obj.typeclass_path}")
    return "\n".join(lines)


def summarize_players(room_name=None):
    room = _get_room_or_error(room_name) if room_name else None
    matches = []
    for obj in ObjectDB.objects.all():
        if not _is_player_character(obj):
            continue
        if room and obj.location != room:
            continue
        matches.append(obj)

    title = f"Player 清單：{room.key}" if room else "Player 清單：全世界"
    lines = [title]
    if not matches:
        lines.append("- 目前沒有找到玩家角色。")
        return "\n".join(lines)

    def _sort_key(item):
        return (_find_room_name_for_obj(item), item.key)

    for obj in sorted(matches, key=_sort_key):
        owners = _player_accounts(obj)
        lines.append(
            f"- {obj.key}｜房間：{_find_room_name_for_obj(obj)}｜home：{getattr(getattr(obj, 'home', None), 'key', '無') if getattr(obj, 'home', None) else '無'}｜擁有帳號：{_format_list(account.key for account in owners)}｜aliases：{_format_list(_current_aliases(obj))}"
        )
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Mutations
# ---------------------------------------------------------------------------


def create_player(
    char_key, room_name, desc=None, aliases=None, account_name=None, caller=None
):
    char_key = _clean_text(char_key)
    if not char_key:
        raise PlayerSpecError("create 需要角色名稱。")
    if _find_exact_object(char_key):
        raise PlayerSpecError(f"同名物件已存在：{char_key}")

    room = _get_room_or_error(room_name)
    aliases = _normalize_aliases(aliases)
    desc = _clean_text(desc) or DEFAULT_PLAYER_DESC
    account = _get_account_or_error(account_name) if account_name else None

    # --- Kingdom/King logic ---
    king_char = None
    nationality = ""
    if caller and hasattr(caller, "db") and getattr(caller.db, "is_king", False):
        king_char = caller
        # 驗證 home_room 是否屬於自國
        kingdom = getattr(king_char.db, "kingdom", None)
        if kingdom and not room.tags.has(
            f"kingdom:{kingdom.key}", category="ownership"
        ):
            raise PlayerSpecError("King 只能在自國範圍內建立角色。")
        nationality = kingdom.key if kingdom else ""

    if account:
        character, errs = account.create_character(
            key=char_key,
            location=room,
            home=room,
            permissions=list(account.permissions.all()),
            typeclass="typeclasses.characters.Character",
        )
        if not character:
            error_text = "; ".join(errs or ["未知錯誤"])
            raise PlayerSpecError(f"建立角色失敗：{error_text}")
    else:
        character = create_object(
            Character,
            key=char_key,
            location=room,
            home=room,
            aliases=aliases,
            attributes=[("desc", desc), ("is_player_character", True)],
        )

    character.db.is_player_character = True
    character.db.desc = desc
    if aliases:
        _set_aliases(character, aliases)
    # 設定國籍與 King 參照
    character.db.nationality = nationality
    if king_char:
        character.db.king = king_char
    owners = _player_accounts(character)
    _apply_character_owner_locks(character, owners)
    character.save()
    bootstrap_result = ensure_first_player_account_is_gm()

    owner_note = f"，已綁定帳號 `{account.key}`" if account else "，目前未綁帳號"
    king_note = f"（{nationality} 國籍）" if nationality else ""
    bootstrap_note = (
        f" {bootstrap_result['message']}" if bootstrap_result.get("promoted") else ""
    )
    return {
        "player": character,
        "message": (
            f"已建立 Player `{char_key}`，目前位於 `{room.key}`{owner_note}{king_note}。"
            f"這是 live 世界變更。{bootstrap_note}"
        ),
    }


def move_player(char_key, room_name):
    obj = _get_player_or_error(char_key)
    room = _get_room_or_error(room_name)
    obj.location = room
    obj.save()
    return {
        "player": obj,
        "message": f"已將 `{obj.key}` 移到 `{room.key}`。這是 live 世界變更。",
    }


def set_player_home(char_key, room_name):
    obj = _get_player_or_error(char_key)
    room = _get_room_or_error(room_name)
    obj.home = room
    obj.save()
    return {
        "player": obj,
        "message": f"已將 `{obj.key}` 的 home 設為 `{room.key}`。",
    }


def rename_player(char_key, new_name):
    obj = _get_player_or_error(char_key)
    new_name = _clean_text(new_name)
    if not new_name:
        raise PlayerSpecError("rename 需要新的角色名稱。")
    if new_name.lower() == obj.key.lower():
        raise PlayerSpecError("新名稱和目前名稱相同。")
    existing = _find_exact_object(new_name)
    if existing and existing.id != obj.id:
        raise PlayerSpecError(f"同名物件已存在：{new_name}")
    old_name = obj.key
    obj.key = new_name
    obj.save()
    return {
        "player": obj,
        "message": f"已將角色 `{old_name}` 重新命名為 `{new_name}`。",
    }


def summon_player(char_key, room_name):
    obj = _get_player_or_error(char_key)
    room = _get_room_or_error(room_name)
    obj.location = room
    obj.save()
    return {
        "player": obj,
        "message": f"已將 `{obj.key}` 傳送到 `{room.key}`，home 保持不變。",
    }


def set_player_desc(char_key, desc):
    obj = _get_player_or_error(char_key)
    desc = _clean_text(desc)
    if not desc:
        raise PlayerSpecError("desc 需要新的描述。")
    obj.db.desc = desc
    obj.save()
    return {
        "player": obj,
        "message": f"已更新 `{obj.key}` 的描述。",
    }


def set_player_aliases(char_key, aliases):
    obj = _get_player_or_error(char_key)
    aliases = _normalize_aliases(aliases)
    if not aliases:
        raise PlayerSpecError("aliases 需要至少一個 alias。")
    aliases = _set_aliases(obj, aliases)
    obj.save()
    return {
        "player": obj,
        "message": f"已更新 `{obj.key}` 的 aliases：{_format_list(aliases)}。",
    }


def add_player_aliases(char_key, aliases):
    obj = _get_player_or_error(char_key)
    aliases = _normalize_aliases(aliases)
    if not aliases:
        raise PlayerSpecError("addaliases 需要至少一個 alias。")
    merged = _add_aliases(obj, aliases)
    obj.save()
    return {
        "player": obj,
        "message": f"已追加 `{obj.key}` 的 aliases，目前為：{_format_list(merged)}。",
    }


def remove_player_aliases(char_key, aliases):
    obj = _get_player_or_error(char_key)
    aliases = _normalize_aliases(aliases)
    if not aliases:
        raise PlayerSpecError("delaliases 需要至少一個 alias。")
    kept = _remove_aliases(obj, aliases)
    obj.save()
    return {
        "player": obj,
        "message": f"已移除指定 aliases；`{obj.key}` 目前 aliases：{_format_list(kept)}。",
    }


def send_player_home(char_key):
    obj = _get_player_or_error(char_key)
    home = getattr(obj, "home", None)
    if not home:
        raise PlayerSpecError(f"`{obj.key}` 目前沒有 home。")
    obj.location = home
    obj.save()
    return {
        "player": obj,
        "message": f"已將 `{obj.key}` 送回 home `{home.key}`。",
    }


def bind_player(char_key, account_name):
    obj = _get_player_or_error(char_key)
    account = _get_account_or_error(account_name)
    owners = _player_accounts(obj)
    if account in owners:
        raise PlayerSpecError(f"`{obj.key}` 已經綁在 `{account.key}` 底下。")
    account.characters.add(obj)
    owners = _player_accounts(obj)
    if len(account.characters.all()) == 1:
        account.db._last_puppet = obj
    _apply_character_owner_locks(obj, owners)
    obj.db.is_player_character = True
    obj.save()
    bootstrap_result = ensure_first_player_account_is_gm()
    bootstrap_note = (
        f" {bootstrap_result['message']}" if bootstrap_result.get("promoted") else ""
    )
    return {
        "player": obj,
        "message": f"已將 `{obj.key}` 綁到帳號 `{account.key}`。{bootstrap_note}",
    }


def unbind_player(char_key, account_name=None):
    obj = _get_player_or_error(char_key)
    owners = _player_accounts(obj)
    if not owners:
        raise PlayerSpecError(f"`{obj.key}` 目前沒有綁定任何帳號。")

    if account_name:
        target = _get_account_or_error(account_name)
        if target not in owners:
            raise PlayerSpecError(f"`{obj.key}` 沒有綁在 `{target.key}` 底下。")
        target.characters.remove(obj)
        message = f"已將 `{obj.key}` 從帳號 `{target.key}` 解綁。"
    else:
        for owner in owners:
            owner.characters.remove(obj)
        message = f"已將 `{obj.key}` 從所有帳號解綁。"

    owners = _player_accounts(obj)
    _apply_character_owner_locks(obj, owners)
    obj.save()
    return {
        "player": obj,
        "message": message,
    }


def delete_player(char_key):
    obj = _get_player_or_error(char_key)
    owners = _player_accounts(obj)
    for owner in owners:
        owner.characters.remove(obj)
    key = obj.key
    obj.delete()
    return {
        "message": f"已刪除 Player `{key}`。這是 live 世界變更。",
    }
