"""Admin helpers for managing Evennia Accounts."""

from __future__ import annotations

from dataclasses import dataclass

from evennia import search_account
from evennia.utils.search import search_object
from evennia.accounts.models import AccountDB
from django.contrib.auth.models import Permission
from evennia.utils.utils import make_iter
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
        ", ".join([p.name for p in account.permissions.all()])
        if account.permissions.all()
        else "無"
    )

    lines = [f"Account：{account.key}"]
    lines.append(f"- 擁有角色：{char_list}")
    lines.append(f"- 目前 Puppet：{puppet}")
    lines.append(f"- 權限：{perms}")
    return "\n".join(lines)


def list_accounts(filter_perm=None):
    accounts = AccountDB.objects.all()
    if filter_perm:
        accounts = [
            a
            for a in accounts
            if any(p.name == filter_perm in p.name for p in a.permissions.all())
        ]

    lines = ["帳號清單："]
    for a in accounts:
        lines.append(f"- {a.key} (角色數: {a.characters.count()})")
    return "\n".join(lines) if len(lines) > 1 else "目前沒有找到符合條件的帳號。"


def create_account(account_name, password, email=None):
    """Create a live Evennia account.

    Args:
        account_name (str): Requested account name.
        password (str): Cleartext password.
        email (str, optional): Optional email address.

    Returns:
        dict: Result payload with a human-readable status message.

    Raises:
        AccountSpecError: If the inputs are missing or Evennia rejects creation.
    """

    account_name = _clean_text(account_name)
    password = _clean_text(password)
    email = _clean_text(email) or None
    if not account_name:
        raise AccountSpecError("create 需要帳號名稱。")
    if not password:
        raise AccountSpecError("create 需要密碼。")

    from evennia.accounts.accounts import DefaultAccount

    account, errors = DefaultAccount.create(
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
            f"已建立 Account `{account.key}`{email_note}。"
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
    return {"message": f"已將帳號 `{account.key}` 的 puppet 強制切換為 `{char.key}`。"}


def normalize_hierarchy_role_name(role_name):
    """Normalize a hierarchy role name and validate it."""

    role_name = _clean_text(role_name)
    lookup = {name.lower(): name for name in HIERARCHY_ROLE_PERMISSIONS}
    normalized = lookup.get(role_name.lower())
    if not normalized:
        allowed = "/".join(HIERARCHY_ROLE_PERMISSIONS)
        raise AccountSpecError(f"角色層級只接受 {allowed}。")
    return normalized


def normalize_account_command_permission(perm_name):
    """Normalize a permission name allowed by @agentaccount."""

    perm_name = _clean_text(perm_name)
    lookup = {name.lower(): name for name in ACCOUNT_COMMAND_ALLOWED_PERMISSIONS}
    normalized = lookup.get(perm_name.lower())
    if not normalized:
        allowed = "/".join(ACCOUNT_COMMAND_ALLOWED_PERMISSIONS)
        raise AccountSpecError(
            f"@agentaccount 只能管理 {allowed} 權限；GM 請改用 @agentworld/role。"
        )
    return normalized


def _get_permission_or_error(name):
    """Resolve a permission row by exact name."""

    from django.contrib.auth.models import Permission

    try:
        return Permission.objects.get(name=name)
    except Permission.DoesNotExist:
        raise AccountSpecError(f"權限 `{name}` 不存在。")


def set_account_role(account_name, role_name):
    """Set one hierarchy role on an account, replacing existing hierarchy perms."""

    account = _get_account_or_error(account_name)
    normalized = normalize_hierarchy_role_name(role_name)
    current = {perm.name for perm in account.permissions.all()}

    removed = []
    for perm_name in HIERARCHY_PERMISSION_POOL:
        if perm_name in current:
            account.permissions.remove(_get_permission_or_error(perm_name))
            removed.append(perm_name)

    added = []
    for perm_name in HIERARCHY_ROLE_PERMISSIONS[normalized]:
        if perm_name not in current:
            account.permissions.add(_get_permission_or_error(perm_name))
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


def add_account_permission(account_name, perm_name):
    perm_name = normalize_account_command_permission(perm_name)
    account = _get_account_or_error(account_name)
    perm = _get_permission_or_error(perm_name)

    account.permissions.add(perm)
    account.save()
    return {"message": f"已為帳號 `{account.key}` 追加權限 `{perm_name}`。"}


def remove_account_permission(account_name, perm_name):
    perm_name = normalize_account_command_permission(perm_name)
    account = _get_account_or_error(account_name)
    perm = _get_permission_or_error(perm_name)

    account.permissions.remove(perm)
    account.save()
    return {"message": f"已從帳號 `{account.key}` 移除權限 `{perm_name}`。"}


def delete_account(account_name):
    """Delete a live Evennia account.

    Args:
        account_name (str): Exact account name to delete.

    Returns:
        dict: Result payload with a human-readable status message.

    Raises:
        AccountSpecError: If the account does not exist or is protected.
    """

    account = _get_account_or_error(account_name)
    if getattr(account, "is_superuser", False):
        raise AccountSpecError(f"不能刪除 superuser 帳號：{account.key}")

    char_count = account.characters.count()
    key = account.key
    if not account.delete():
        raise AccountSpecError(f"刪除帳號失敗：{key}")

    return {
        "message": (
            f"已刪除 Account `{key}`。原本綁定 {char_count} 個角色；"
            "若該帳號仍在線上，session 已一併斷線。這是 live 世界變更。"
        )
    }


# --- King Appoint Tool (GM only) ---

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
                king_perm = Permission.objects.get(name="King")
                old_account.permissions.remove(king_perm)
            except Exception as e:
                logger.log_warn(f"移除舊 King 權限失敗: {e}")
        old_king.db.is_king = False
        old_king.db.kingdom = None
        old_king.db.king = target_char
        old_king.save()
    
    # 賦予新 King 權限
    try:
        king_perm = Permission.objects.get(name="King")
        account.permissions.add(king_perm)
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
