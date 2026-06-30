"""將玩家鎖定到單一託管角色的帳戶級命令。"""

from evennia.commands.default.account import CmdIC, CmdOOC, CmdOOCLook
from evennia.contrib.rpg.character_creator.character_creator import ContribCmdCharCreate

from commands.command import MuxCommand


class CmdChineseOOCLook(CmdOOCLook):
    """中文化的 OOC look。"""

    help_category = "一般"

    def func(self):
        if self.session.puppet:
            self.msg("你目前無法查看周遭。")
            return

        if self.playable and not self.args:
            self.msg(self.account.at_look(target=self.playable, session=self.session))
            return

        return super().func()


class CmdChineseOOC(CmdOOC):
    """中文化的 ooc 指令。"""

    help_category = "一般"

    def func(self):
        account = self.account
        session = self.session
        old_char = account.get_puppet(session)
        if not old_char:
            self.msg("你已經在 OOC 狀態。")
            return

        account.db._last_puppet = old_char
        try:
            account.unpuppet_object(session)
            self.msg("\n|G你已回到 OOC 狀態。|n\n")
            self.msg(account.at_look(target=self.playable, session=session))
        except RuntimeError as exc:
            self.msg(f"|r無法從 |c{old_char}|n 解除控制：{exc}|n")


class CmdLockedIC(CmdIC):
    """只允許非管理員玩家操縱他們的主要角色。"""

    help_category = "一般"

    def func(self):
        account = self.account
        if account.check_permstring("Developer") or account.check_permstring("Admin"):
            return super().func()

        primary = None
        if hasattr(account, "get_primary_character"):
            primary = account.get_primary_character()
        primary = (
            primary
            or getattr(account.db, "primary_character", None)
            or getattr(account.db, "_last_puppet", None)
        )
        if not primary:
            self.msg("你目前沒有可進入的角色，請通知管理員。")
            return

        if self.args:
            query = self.args.strip().lower()
            aliases = []
            try:
                aliases = [str(alias).lower() for alias in primary.aliases.all()]
            except Exception:
                aliases = []
            allowed = {primary.key.lower(), str(primary.id), f"#{primary.id}", *aliases}
            if query not in allowed:
                self.msg("你的帳號已綁定固定角色，不能切換到其他角色。")
                return

        self.args = primary.key
        return super().func()


class CmdLockedCharCreate(ContribCmdCharCreate):
    """停用普通玩家的自助角色創建。"""

    def func(self):
        account = self.account
        if account.check_permstring("Developer") or account.check_permstring("Admin"):
            return super().func()
        self.msg("一般玩家不能自行新增角色。")


class CmdCharacterRoster(MuxCommand):
    """
    查看自己的預設角色。

    用法:
      characters
      charstatus
    """

    key = "characters"
    aliases = ["charstatus"]
    locks = "cmd:pperm(Player)"
    help_category = "一般"
    account_caller = True

    def func(self):
        account = self.caller
        primary = None
        if hasattr(account, "get_primary_character"):
            primary = account.get_primary_character()
        primary = primary or getattr(account.db, "primary_character", None)
        if not primary:
            self.msg("你目前沒有綁定角色。")
            return
        self.msg(
            f"你的預設角色是：{primary.key}。此帳號不能自行新增、刪除或切換角色。"
        )
