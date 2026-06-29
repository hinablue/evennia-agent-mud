"""Admin helpers for managing Evennia Accounts."""
from __future__ import annotations

from evennia import search_account
from evennia.accounts.models import AccountDB
from evennia.utils.utils import make_iter
from dataclasses import dataclass

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
    matches = [account for account in search_account(account_name) if account.key.lower() == account_name.lower()]
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
    puppet = account.db._last_puppet.key if getattr(account.db, "_last_puppet", None) else "無"
    perms = ", ".join([p.name for p in account.permissions.all()]) if account.permissions.all() else "無"
    
    lines = [f"Account：{account.key}"]
    lines.append(f"- 擁有角色：{char_list}")
    lines.append(f"- 目前 Puppet：{puppet}")
    lines.append(f"- 權限：{perms}")
    return "\n".join(lines)

def list_accounts(filter_perm=None):
    accounts = AccountDB.objects.all()
    if filter_perm:
        accounts = [a for a in accounts if any(p.name == filter_perm in p.name for p in a.permissions.all())]
    
    lines = ["帳號清單："]
    for a in accounts:
        lines.append(f"- {a.key} (角色數: {a.characters.count()})")
    return "\n".join(lines) if len(lines) > 1 else "目前沒有找到符合條件的帳號。"

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

def add_account_permission(account_name, perm_name):
    account = _get_account_or_error(account_name)
    from evennia.accounts.models import Permission
    try:
        perm = Permission.objects.get(name=perm_name)
    except Permission.DoesNotExist:
        raise AccountSpecError(f"權限 `{perm_name}` 不存在。")
    
    account.permissions.add(perm)
    account.save()
    return {"message": f"已為帳號 `{account.key}` 追加權限 `{perm_name}`。"}

def remove_account_permission(account_name, perm_name):
    account = _get_account_or_error(account_name)
    from evennia.accounts.models import Permission
    try:
        perm = Permission.objects.get(name=perm_name)
    except Permission.DoesNotExist:
        raise AccountSpecError(f"權限 `{perm_name}` 不存在。")
    
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
