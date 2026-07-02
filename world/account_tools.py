"""用於管理 Evennia 帳戶的管理員助手。"""

from __future__ import annotations

from dataclasses import dataclass

from django.conf import settings

from evennia import search_account
from evennia.utils.search import search_object
from evennia.accounts.models import AccountDB
from evennia.utils.utils import class_from_module, make_iter
from evennia.utils import logger
from world.kingdom import get_kingdom_by_name

HIERARCHY_ROLE_PERMISSIONS = {
    "GM": ("Admin", "GM"),
    "King": ("King",),
    "Player": ("Player",),
}
HIERARCHY_PERMISSION_POOL = ("Admin", "Developer", "GM", "King", "Player")
ACCOUNT_COMMAND_ALLOWED_PERMISSIONS = ("King", "Player")


@dataclass
class AccountSpecError(ValueError):
    message: str

    def __str__(self):
        return self.message


def _clean_text(value):
    return (value or "").strip()


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
    account = _find_exact_account(account_name)
    if not account:
        raise AccountSpecError(f"找不到帳號：{account_name}")
    return account


def summarize_account(account_name):
    account = _get_account_or_error(account_name)
    chars = list(account.characters.all())
    char_list = ", ".join([c.key for c in chars]) if chars else "無"
    puppet = (
        account.db._last_puppet.key
        if getattr(account.db, "_last_puppet", None)
        else "無"
    )
    perms = (
        ", ".join([p for p in account.permissions.all()])
        if account.permissions.all()
        else "無"
    )

    lines = [f"帳號：{account.key}"]
    lines.append(f"- 擁有角色：{char_list}")
    lines.append(f"- 目前控制角色：{puppet}")
    lines.append(f"- 權限：{perms}")
    return "\n".join(lines)


def list_accounts(filter_perm=None, nation=None):
    accounts = AccountDB.objects.all()
    if filter_perm:
        accounts = [
            a
            for a in accounts
            if filter_perm in a.permissions.all()
        ]

    if nation:
        accounts = [
            a for a in accounts
            if any(getattr(c.db, "nationality", "") == nation for c in a.characters.all())
        ]

    lines = ["帳號清單："]
    for a in accounts:
        lines.append(f"- {a.key} (角色數: {a.characters.count()})")
    return "\n".join(lines) if len(lines) > 1 else "目前沒有找到符合條件的帳號。"


def create_account(account_name, password, email=None):
    """建立一個即時 Evennia 帳戶。

    參數：
        account_name (str)：請求的帳號名稱。
        密碼 (str)：明文密碼。
        email (str, 可選): 可選的電子郵件地址。

    返回：
        dict：帶有人類可讀狀態訊息的結果有效負載。

    加薪：
        AccountSpecError：如果輸入遺失或 Evennia 拒絕建立。"""

    account_name = _clean_text(account_name)
    password = _clean_text(password)
    email = _clean_text(email) or None
    if not account_name:
        raise AccountSpecError("create 需要帳號名稱。")
    if not password:
        raise AccountSpecError("create 需要密碼。")

    account_typeclass = class_from_module(settings.BASE_ACCOUNT_TYPECLASS)
    account, errors = account_typeclass.create(
        username=account_name,
        password=password,
        email=email or "",
    )
    if not account:
        error_text = "; ".join(errors or ["未知錯誤"])
        raise AccountSpecError(f"建立帳號失敗：{error_text}")

    email_note = f"，email：{email}" if email else ""
    return {
        "account": account,
        "message": (
            f"已建立帳號 `{account.key}`{email_note}。"
            "這是 live 世界變更。"
        ),
    }


def set_account_puppet(account_name, char_key):
    account = _get_account_or_error(account_name)
    from evennia import search_object

    matches = search_object(char_key, exact=True)
    if not matches:
        raise AccountSpecError(f"找不到角色：{char_key}")
    char = matches[0]
    if char not in account.characters.all():
        raise AccountSpecError(f"角色 `{char.key}` 不屬於帳號 `{account.key}`。")

    account.db._last_puppet = char
    account.save()
    return {"message": f"已將帳號 `{account.key}` 的控制角色強制切換為 `{char.key}`。"}


def normalize_hierarchy_role_name(role_name):
    """標準化層次結構角色名稱並驗證它。"""

    role_name = _clean_text(role_name)
    lookup = {name.lower(): name for name in HIERARCHY_ROLE_PERMISSIONS}
    normalized = lookup.get(role_name.lower())
    if not normalized:
        allowed = "/".join(HIERARCHY_ROLE_PERMISSIONS)
        raise AccountSpecError(f"角色層級只接受 {allowed}。")
    return normalized


def normalize_account_command_permission(perm_name):
    """規範化 @agentaccount 允許的權限名稱。"""

    perm_name = _clean_text(perm_name)
    lookup = {name.lower(): name for name in ACCOUNT_COMMAND_ALLOWED_PERMISSIONS}
    normalized = lookup.get(perm_name.lower())
    if not normalized:
        allowed = "/".join(ACCOUNT_COMMAND_ALLOWED_PERMISSIONS)
        raise AccountSpecError(
            f"@agentaccount 只能管理 {allowed} 權限；GM 請改用 @agentworld/role。"
        )
    return normalized


def set_account_role(account_name, role_name):
    """在帳號上​​設定一個層次結構角色，取代現有的層次結構權限。"""

    account = _get_account_or_error(account_name)
    normalized = normalize_hierarchy_role_name(role_name)
    current = set(account.permissions.all())

    removed = []
    for perm_name in HIERARCHY_PERMISSION_POOL:
        if perm_name in current:
            account.permissions.remove(perm_name)
            removed.append(perm_name)

    added = []
    for perm_name in HIERARCHY_ROLE_PERMISSIONS[normalized]:
        if perm_name not in current:
            account.permissions.add(perm_name)
            added.append(perm_name)

    account.save()
    removed_note = f"；移除：{', '.join(removed)}" if removed else ""
    added_note = f"；加入：{', '.join(added)}" if added else ""
    return {
        "account": account,
        "role": normalized,
        "message": (
            f"已將帳號 `{account.key}` 設為 `{normalized}` 層級"
            f"{added_note}{removed_note}。"
        ),
    }


def _iter_account_characters(account):
    """傳回帳戶擁有的穩定角色清單。"""

    try:
        return list(account.characters.all())
    except Exception:
        return []


def _has_staff_role(account):
    """帳戶是否已經擁有員工級世界權限。"""

    perms = set(account.permissions.all())

    perms = {perm.lower() for perm in (account.permissions.all() or [])}
    return bool(perms & {"gm", "developer", "admin"})


def _apply_role_to_holder(holder, normalized):
    """將一個層級角色應用於帳戶或類似角色的持有者。"""

    permissions = getattr(holder, "permissions", None)
    if not permissions:
        return False

    current = set(permissions.all())
    changed = False
    for perm_name in HIERARCHY_PERMISSION_POOL:
        if perm_name in current:
            permissions.remove(perm_name)
            changed = True

    for perm_name in HIERARCHY_ROLE_PERMISSIONS[normalized]:
        if perm_name not in current:
            permissions.add(perm_name)
            changed = True

    if changed and hasattr(holder, "save"):
        holder.save()
    return changed


def ensure_first_player_account_is_gm():
    """如果不存在員工帳戶，則將第一個可玩的帳戶/角色提升為 GM。"""

    accounts = list(AccountDB.objects.all())
    if any(_has_staff_role(account) for account in accounts):
        return {
            "promoted": False,
            "account": None,
            "character": None,
            "message": "已存在 GM/Admin/Developer 帳號，略過首位玩家自動升權。",
        }

    for account in accounts:
        characters = _iter_account_characters(account)
        if not characters:
            continue

        first_character = characters[0]
        _apply_role_to_holder(account, "GM")
        _apply_role_to_holder(first_character, "GM")
        return {
            "promoted": True,
            "account": account,
            "character": first_character,
            "message": (
                f"已將首位使用者角色 `{first_character.key}` 與帳號 `{account.key}`"
                " 自動設為 GM/Admin。"
            ),
        }

    return {
        "promoted": False,
        "account": None,
        "character": None,
        "message": "目前尚未找到已綁定帳號的使用者角色，略過首位玩家自動升權。",
    }


def add_account_permission(account_name, perm_name):
    perm_name = normalize_account_command_permission(perm_name)
    account = _get_account_or_error(account_name)

    account.permissions.add(perm_name)
    account.save()
    return {"message": f"已為帳號 `{account.key}` 追加權限 `{perm_name}`。"}


def remove_account_permission(account_name, perm_name):
    perm_name = normalize_account_command_permission(perm_name)
    account = _get_account_or_error(account_name)

    account.permissions.remove(perm_name)
    account.save()
    return {"message": f"已從帳號 `{account.key}` 移除權限 `{perm_name}`。"}


def delete_account(account_name):
    """刪除真實的 Evennia 帳戶。

    參數：
        account_name (str)：要刪除的確切帳號名稱。

    返回：
        dict：帶有人類可讀狀態訊息的結果有效負載。

    加薪：
        AccountSpecError：如果帳戶不存在或受保護。"""

    account = _get_account_or_error(account_name)
    if getattr(account, "is_superuser", False):
        raise AccountSpecError(f"不能刪除 superuser 帳號：{account.key}")

    char_count = account.characters.count()
    key = account.key
    if not account.delete():
        raise AccountSpecError(f"刪除帳號失敗：{key}")

    return {
        "message": (
            f"已刪除帳號 `{key}`。原本綁定 {char_count} 個角色；"
            "若該帳號仍在線上，會話已一併斷線。這是 live 世界變更。"
        )
    }


def set_account_nationality(account_name, nationality, caller=None):
    """
    為帳號下的所有角色設定國籍（nationality）。

    Args:
        account_name (str): 目標帳號名稱
        nationality (str): 國籍字串（通常為 Kingdom key）
        caller (Object, optional): 呼叫者，用於權限檢查。需具 King/GM/Developer 權限。

    Returns:
        dict: Result payload with message

    Raises:
        AccountSpecError: 如果權限不足、帳號不存在、或國籍無效
    """
    from world.kingdom import get_kingdom_by_name

    # 權限檢查：只有 King、GM、Developer 可用
    if caller:
        perms = {perm.lower() for perm in caller.account.permissions.all()} if caller.account else set()
        is_king = bool(getattr(caller.db, "is_king", False))

        if not (is_king or perms & {"gm", "developer", "admin"}):
            raise AccountSpecError(f"只有 King 或以上權限才能設定國籍。{perms}")

    account = _get_account_or_error(account_name)

    # 驗證國家是否存在
    kingdom = get_kingdom_by_name(nationality)
    if not kingdom:
        raise AccountSpecError(f"找不到國家：{nationality}")

    # 為該帳號下所有角色設定國籍
    updated = 0
    for char in account.characters.all():
        char.db.nationality = nationality
        # 若是 King 設定，同步更新 king 參照
        if caller and getattr(caller.db, "is_king", False):
            char.db.king = caller
        char.save()
        updated += 1

    if updated == 0:
        return {"message": f"帳號 `{account.key}` 下無角色，無需設定國籍。"}

    return {
        "message": f"已將帳號 `{account.key}` 的 {updated} 個角色國籍設為 `{nationality}`。"
    }


# --- King 任命工具（僅限 GM）---
def appoint_king(account_name, target_char_key):
    """
    GM 強制指定/移交 King：將指定角色設為某國的 King。
    單一國家同一時間只有一個 King。
    這是 GM 級工具，不受 King 自身 @king/appoint 限制。

    Args:
        account_name (str): 目標 Player 的 Account 名稱
        target_char_key (str): 要升為 King 的 Character 名稱

    Returns:
        dict: Result payload
    """
    account = _get_account_or_error(account_name)

    # 找目標角色
    matches = search_object(target_char_key, exact=True)
    if not matches:
        raise AccountSpecError(f"找不到角色：{target_char_key}")
    target_char = matches[0]

    # 驗證角色屬於該帳號
    if target_char not in account.characters.all():
        raise AccountSpecError(f"角色 `{target_char.key}` 不屬於帳號 `{account.key}`。")

    # 找該角色目前的 Kingdom（透過 nationality 或 king 參照）
    kingdom = None
    nat = getattr(target_char.db, "nationality", "")
    if nat:
        from world.kingdom import get_kingdom_by_name
        kingdom = get_kingdom_by_name(nat)

    if not kingdom:
        raise AccountSpecError(f"角色 `{target_char.key}` 無國籍或找不到對應國家。")

    # 如果該國已有 King，先降級舊 King
    old_king = kingdom.db.king
    if old_king and old_king != target_char:
        old_account = old_king.account
        if old_account:
            try:
                old_account.permissions.remove("King")
            except Exception as e:
                logger.log_warn(f"移除舊 King 權限失敗: {e}")
        old_king.db.is_king = False
        old_king.db.kingdom = None
        old_king.db.king = target_char
        old_king.save()

    # 賦予新 King 權限
    try:
        account.permissions.add("King")
    except Exception as e:
        raise AccountSpecError(f"賦予 King 權限失敗：{e}")

    target_char.db.is_king = True
    target_char.db.kingdom = kingdom
    target_char.db.king = target_char  # 自己是自己的 King
    target_char.db.nationality = kingdom.key

    # 設定 home = 入口房
    if kingdom.db.entrance_room:
        target_char.home = kingdom.db.entrance_room

    target_char.save()

    # 更新 Kingdom script
    kingdom.db.king = target_char
    kingdom.save()

    logger.log_info(f"GM appoint King: {account.key} -> {target_char.key} (kingdom: {kingdom.key})")

    return {
        "message": (
            f"已指定 `{target_char.key}` (帳號: {account.key}) 為 `{kingdom.key}` 國王。"
            f"{'（原 King 已降為國民）' if old_king and old_king != target_char else ''}"
        )
    }
