"""
Lockfuncs for GM/King/Player permission hierarchy.

Lock functions are called with (accessing_obj, accessed_obj, *args, **kwargs).
All functions return True (access granted) or False (denied).
"""

from evennia.accounts.models import AccountDB


def is_gm(accessing_obj, accessed_obj, *args, **kwargs):
    """GM (Admin/Developer) permission check."""
    if not hasattr(accessing_obj, "account"):
        return False
    account = accessing_obj.account
    return account and (
        account.check_permstring("Admin")
        or account.check_permstring("Developer")
        or account.check_permstring("GM")
    )


def is_king(accessing_obj, accessed_obj, *args, **kwargs):
    """King permission check (needs King perm + is_king=True)."""
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
    """
    Check if accessing_obj is the King of accessed_obj's kingdom.
    Usage: control:is_king_of(), edit:is_king_of()
    accessed_obj needs tag category="ownership" with kingdom:xxx
    """
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
    """Check if both belong to same kingdom (Player <-> Player, King <-> own objects)."""
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
    """Check if target belongs to GM continent (King cannot touch)."""
    if not hasattr(accessed_obj, "tags"):
        return False
    return accessed_obj.tags.has("gm_continent", category="ownership")


def is_king_entrance(accessing_obj, accessed_obj, *args, **kwargs):
    """Check if target is King's entrance room (structure immutable)."""
    if not hasattr(accessed_obj, "tags"):
        return False
    return accessed_obj.tags.has("king_entrance", category="ownership")


def is_gm_link_exit(accessing_obj, accessed_obj, *args, **kwargs):
    """Check if target exit links to GM continent (King cannot touch)."""
    if not hasattr(accessed_obj, "tags"):
        return False
    return accessed_obj.tags.has("gm_link_exit", category="ownership")
