"""
Account

The Account represents the game "account" and each login has only one
Account object. An Account is what chats on default channels but has no
other in-game-world existence. Rather the Account puppets Objects (such
as Characters) in order to actually participate in the game world.
"""

from evennia.accounts.accounts import DefaultGuest
from evennia.contrib.rpg.character_creator.character_creator import (
    ContribChargenAccount,
)


class Account(ContribChargenAccount):
    """Game account with a locked primary character."""

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
    """Guest accounts are deleted after disconnection."""

    pass
