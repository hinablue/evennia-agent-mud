"""帳戶

Account代表遊戲“帳號”，每次登入只有一個
帳戶對象。帳戶是在預設頻道上聊天但沒有權限的帳戶
其他遊戲世界中的存在。相反，帳號傀儡物件（例如
作為角色）以便真正參與遊戲世界。"""

from evennia.accounts.accounts import DefaultGuest
from evennia.contrib.rpg.character_creator.character_creator import (
    ContribChargenAccount,
)
from evennia.utils.utils import is_iter


def _zh_permissions(obj):
    try:
        perms = list(obj.permissions.all())
    except Exception:
        perms = []
    return ", ".join(perms) if perms else "無"


class Account(ContribChargenAccount):
    """主要角色被鎖定的遊戲帳號。"""

    ooc_appearance_template = (
        "--------------------------------------------------------------------\n"
        "{header}\n\n"
        "{sessions}\n\n"
        "  |whelp|n - 顯示更多指令\n"
        "  |wcharcreate|n - 建立新角色\n"
        "  |wchardelete <名稱>|n - 刪除角色\n"
        "  |wic <名稱>|n - 以角色進入遊戲（|wooc|n 回到這裡）\n"
        "  |wic|n - 直接進入上次操控的角色\n\n"
        "{characters}\n"
        "{footer}\n"
        "--------------------------------------------------------------------"
    )

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

    def at_look(self, target=None, session=None, **kwargs):
        if target and not is_iter(target):
            if hasattr(target, "return_appearance"):
                return target.return_appearance(self)
            return f"{target} 沒有可顯示的遊戲內外觀。"

        characters = list(tar for tar in target if tar) if target else []
        char_count = len(characters)
        sessions = self.sessions.all()
        if not sessions:
            return ""

        header = f"帳號 |g{self.name}|n（你目前在 OOC 狀態）"

        session_lines = []
        for index, sess in enumerate(sessions, start=1):
            ip_addr = sess.address[0] if isinstance(sess.address, tuple) else sess.address
            addr = f"{sess.protocol_key} ({ip_addr})"
            prefix = f"|w* {index}|n" if session and session.sessid == sess.sessid else f"  {index}"
            session_lines.append(f"{prefix} {addr}")
        session_block = "|w已連線的 session：|n\n" + "\n".join(session_lines)

        if not characters:
            character_block = "你目前還沒有角色。可用 |wcharcreate|n 建立角色。"
        else:
            max_nr_characters = getattr(self, "max_nr_characters", None)
            max_chars = (
                "不限"
                if self.is_superuser or max_nr_characters is None
                else max_nr_characters
            )
            char_lines = []
            for char in characters:
                perms = _zh_permissions(char)
                csessions = char.sessions.all()
                if csessions:
                    for sess in csessions:
                        sid = sessions.index(sess) + 1 if sess in sessions else None
                        if sid:
                            char_lines.append(
                                f" - |G{char.name}|n [{perms}]（正由你在 session {sid} 操作）"
                            )
                        else:
                            char_lines.append(
                                f" - |R{char.name}|n [{perms}]（正由其他人操作）"
                            )
                else:
                    char_lines.append(f" - {char.name} [{perms}]")
            character_block = (
                f"可用角色 ({char_count}/{max_chars}，輸入 |wic <名稱>|n 進入)：|n\n"
                + "\n".join(char_lines)
            )

        return self.ooc_appearance_template.format(
            header=header,
            sessions=session_block,
            characters=character_block,
            footer="",
        )


class Guest(DefaultGuest):
    """斷開連線後，訪客帳戶將被刪除。"""

    pass
