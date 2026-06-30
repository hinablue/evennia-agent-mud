"""帳戶

Account代表遊戲“帳號”，每次登入只有一個
帳戶對象。帳戶是在預設頻道上聊天但沒有權限的帳戶
其他遊戲世界中的存在。相反，帳號傀儡物件（例如
作為角色）以便真正參與遊戲世界。"""

from evennia.accounts.accounts import DefaultGuest
from evennia.contrib.rpg.character_creator.character_creator import (
    ContribChargenAccount,
)


class Account(ContribChargenAccount):
    """主要角色被鎖定的遊戲帳號。"""

    def at_account_creation(self):
        super().at_account_creation()
        character, errors = self.create_character(
            key=self.key,
            typeclass="typeclasses.characters.Character",
            permissions=list(self.permissions.all()),
        )
        if character:
            self.db.primary_character = character
            self.db._last_puppet = character
        else:
            self.db.primary_character = None
            self.msg("\n".join(errors or ["系統未能自動建立預設角色。請通知管理員。"]))

    def at_post_create_character(self, character, **kwargs):
        super().at_post_create_character(character, **kwargs)
        primary = getattr(self.db, "primary_character", None)
        if not primary:
            self.db.primary_character = character
            primary = character
        if character == primary:
            self.db._last_puppet = character

    def get_primary_character(self):
        primary = getattr(self.db, "primary_character", None)
        if primary:
            return primary
        try:
            characters = list(self.characters.all())
        except Exception:
            characters = list(self.characters or [])
        return characters[0] if characters else None


class Guest(DefaultGuest):
    """斷開連線後，訪客帳戶將被刪除。"""

    pass
