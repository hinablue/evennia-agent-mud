"""Helpers for admin-managed Account Character rosters."""

from __future__ import annotations

from evennia import search_account
from evennia.utils.utils import make_iter


DEFAULT_CHARACTER_DESC = "This is a character."


class CharacterAdminError(ValueError):
    """Raised when an ``@agentchar`` request cannot be completed."""


def _clean_text(value):
    """Normalize command input into a stripped string."""

    return (value or "").strip()


def _find_exact_account(account_name):
    """Return an exact account match, ignoring case."""

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
    """Resolve an account or raise a user-facing error."""

    account_name = _clean_text(account_name)
    if not account_name:
        raise CharacterAdminError("請提供帳號名稱。")
    account = _find_exact_account(account_name)
    if not account:
        raise CharacterAdminError(f"找不到帳號：{account_name}")
    return account


def _account_characters(account):
    """Return a stable list of playable characters for an account."""

    try:
        characters = list(account.characters.all())
    except Exception:
        characters = list(make_iter(account.characters or []))
    return characters


def _find_account_character(account, char_key):
    """Find a character on an account roster by key or ``#dbref``."""

    char_key = _clean_text(char_key)
    if not char_key:
        return None
    needle = char_key.lower()
    for char in _account_characters(account):
        if char.key.lower() == needle:
            return char
        if needle == str(getattr(char, "id", "")).lower():
            return char
        if needle == f"#{getattr(char, 'id', '')}".lower():
            return char
    return None


def _character_desc(character):
    """Safely extract a character description."""

    return _clean_text(getattr(getattr(character, "db", None), "desc", "")) or "無"


def _character_aliases(character):
    """Return aliases as a printable list."""

    aliases = []
    try:
        aliases = [str(alias) for alias in character.aliases.all()]
    except Exception:
        aliases = []
    return "、".join(aliases) if aliases else "無"


def _character_room_name(character):
    """Return a safe location name for display."""

    location = getattr(character, "location", None)
    return getattr(location, "key", "無") if location else "無"


def _character_home_name(character):
    """Return a safe home name for display."""

    home = getattr(character, "home", None)
    return getattr(home, "key", "無") if home else "無"


def summarize_account_characters(account_name):
    """Return an admin summary similar to Evennia's ``characters`` roster."""

    account = _get_account_or_error(account_name)
    characters = _account_characters(account)
    primary = getattr(getattr(account, "db", None), "primary_character", None)
    last_puppet = getattr(getattr(account, "db", None), "_last_puppet", None)

    lines = [f"Account：{account.key}"]
    if not characters:
        lines.append("- 目前沒有任何 Character。")
        return "\n".join(lines)

    lines.append(f"- 角色數：{len(characters)}")
    for char in characters:
        flags = []
        if char == primary:
            flags.append("主角色")
        if char == last_puppet:
            flags.append("最後操控")
        flag_text = f"｜{'、'.join(flags)}" if flags else ""
        lines.append(
            f"- {char.key}｜#{getattr(char, 'id', '?')}｜目前位置：{_character_room_name(char)}"
            f"｜home：{_character_home_name(char)}｜aliases：{_character_aliases(char)}{flag_text}"
        )
        lines.append(f"  描述：{_character_desc(char)}")
    return "\n".join(lines)


def _caller_ip(caller):
    """Best-effort lookup of the caller's active session IP."""

    if not caller:
        return None
    try:
        sessions = list(caller.sessions.all())
    except Exception:
        sessions = []
    if not sessions:
        return None
    return getattr(sessions[0], "address", None)


def create_account_character(account_name, char_key, desc=None, caller=None):
    """Create a new Character on an existing Account using Evennia's factory."""

    account = _get_account_or_error(account_name)
    char_key = _clean_text(char_key)
    if not char_key:
        raise CharacterAdminError("請提供角色名稱。")
    if _find_account_character(account, char_key):
        raise CharacterAdminError(f"`{account.key}` 底下已經有角色 `{char_key}`。")

    description = _clean_text(desc) or DEFAULT_CHARACTER_DESC
    character, errors = account.create_character(
        key=char_key,
        description=description,
        ip=_caller_ip(caller),
    )
    if errors:
        error_text = "; ".join(str(err) for err in errors)
        raise CharacterAdminError(f"建立角色失敗：{error_text}")
    if not character:
        raise CharacterAdminError("建立角色失敗：未知錯誤。")

    if not getattr(account.db, "primary_character", None):
        account.db.primary_character = character
    account.db._last_puppet = character
    if hasattr(account, "save"):
        account.save()

    return {
        "character": character,
        "message": (
            f"已為 Account `{account.key}` 建立 Character `{character.key}`。"
            "這是 live 世界變更。"
        ),
    }


def delete_account_character(account_name, char_key):
    """Delete a Character from an Account roster, mirroring ``chardelete``."""

    account = _get_account_or_error(account_name)
    character = _find_account_character(account, char_key)
    if not character:
        raise CharacterAdminError(f"找不到角色：{char_key}")

    account.characters.remove(character)
    if hasattr(character, "delete"):
        character.delete()

    remaining = _account_characters(account)
    primary = getattr(account.db, "primary_character", None)
    last_puppet = getattr(account.db, "_last_puppet", None)
    replacement = remaining[0] if remaining else None
    note_parts = []

    if character == primary:
        account.db.primary_character = replacement
        if replacement:
            note_parts.append(f"新的主角色：`{replacement.key}`")
        else:
            note_parts.append("帳號目前沒有主角色")
    if character == last_puppet or not getattr(account.db, "_last_puppet", None):
        account.db._last_puppet = replacement

    if hasattr(account, "save"):
        account.save()

    extra = f" {'；'.join(note_parts)}。" if note_parts else ""
    return {
        "message": (
            f"已從 Account `{account.key}` 刪除 Character `{character.key}`。"
            f"這是 live 世界變更。{extra}"
        ).strip(),
    }
