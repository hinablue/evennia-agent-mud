"""GM/King/Player 權限層級結構的 Lockfuncs。

鎖定函數透過 (accessing_obj、accessed_obj、*args、**kwargs) 呼叫。
所有函數都傳回 True（授予存取權限）或 False（拒絕存取）。"""

from evennia.accounts.models import AccountDB


def is_gm(accessing_obj, accessed_obj, *args, **kwargs):
    """GM（管理員/開發人員）權限檢查。"""
    if not hasattr(accessing_obj, "account"):
        return False
    account = accessing_obj.account
    return account and (
        account.check_permstring("Admin")
        or account.check_permstring("Developer")
        or account.check_permstring("GM")
    )


def is_king(accessing_obj, accessed_obj, *args, **kwargs):
    """King 權限檢查（需要 King perm + is_king=True）。"""
    if not hasattr(accessing_obj, "account"):
        return False
    account = accessing_obj.account
    char = accessing_obj
    return (
        account
        and account.check_permstring("King")
        and getattr(char.db, "is_king", False)
    )


def is_king_of(accessing_obj, accessed_obj, *args, **kwargs):
    """檢查accessing_obj是否是accessed_obj王國的國王。
    用法：控制：is_king_of()，編者：is_king_of()
    accessed_obj 需要標籤category="ownership" 和 Kingdom:xxx"""
    if not (hasattr(accessing_obj, "account") and hasattr(accessed_obj, "tags")):
        return False
    char = accessing_obj
    if not (
        char.account.check_permstring("King") and getattr(char.db, "is_king", False)
    ):
        return False
    kingdom_tag = accessed_obj.tags.get(
        category="ownership", key__startswith="kingdom:"
    )
    if not kingdom_tag:
        return False
    kingdom_key = kingdom_tag.split(":", 1)[1]
    return getattr(char.db, "kingdom", None) and char.db.kingdom.key == kingdom_key


def is_same_kingdom(accessing_obj, accessed_obj, *args, **kwargs):
    """檢查兩者是否屬於同一個王國（玩家 <-> 玩家，國王 <-> 自己的對象）。"""
    if not (hasattr(accessing_obj, "db") and hasattr(accessed_obj, "tags")):
        return False
    nat = getattr(accessing_obj.db, "nationality", "")
    if not nat:
        return False
    kingdom_tag = accessed_obj.tags.get(
        category="ownership", key__startswith="kingdom:"
    )
    if not kingdom_tag:
        return False
    return kingdom_tag.split(":", 1)[1] == nat


def is_gm_continent(accessing_obj, accessed_obj, *args, **kwargs):
    """檢查目標是否屬於GM大陸（國王無法觸及）。"""
    if not hasattr(accessed_obj, "tags"):
        return False
    return accessed_obj.tags.has("gm_continent", category="ownership")


def is_king_entrance(accessing_obj, accessed_obj, *args, **kwargs):
    """檢查目標是否為國王的入口房間（結構不可變）。"""
    if not hasattr(accessed_obj, "tags"):
        return False
    return accessed_obj.tags.has("king_entrance", category="ownership")


def is_gm_link_exit(accessing_obj, accessed_obj, *args, **kwargs):
    """檢查目標出口是否連結到GM大陸（國王無法觸摸）。"""
    if not hasattr(accessed_obj, "tags"):
        return False
    return accessed_obj.tags.has("gm_link_exit", category="ownership")
