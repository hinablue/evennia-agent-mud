"""Admin wrapper for Evennia's account Character roster commands."""

from commands.command import MuxCommand
from world.character_tools import (
    CharacterAdminError,
    create_account_character,
    delete_account_character,
    summarize_account_characters,
)


class CmdAgentChar(MuxCommand):
    """
    管理 Account 旗下的 Character roster。

    這顆命令對應 Evennia 內建的 `characters`、`charcreate`、`chardelete`
    三個概念，但改成 Admin 可用的 `@agentchar` 介面。

    使用方式:
      @agentchar <帳號>
      @agentchar/list <帳號>
      @agentchar/create <帳號>=<角色名>
      @agentchar/create <帳號>=<角色名>|<描述>
      @agentchar/delete <帳號>=<角色名>

    不帶 switch 時，等同於查看該帳號的 characters roster。
    """

    key = "@agentchar"
    aliases = ["@charadmin"]
    locks = "cmd:perm(Admin) or perm(Developer) or perm(King)"
    help_category = "Admin"
    switch_options = ("list", "create", "delete", "help")

    def _msg(self, text):
        """Send feedback to the caller."""

        self.caller.msg(text)

    def _show_help(self):
        """Render a compact usage summary."""

        self._msg(
            "|w@agentchar|n\n"
            "  |w@agentchar <帳號>|n：查看該帳號目前有哪些 Character（對應 characters）。\n"
            "  |w@agentchar/list <帳號>|n：同上。\n"
            "  |w@agentchar/create <帳號>=<角色名>|n：在該帳號下建立新 Character（對應 charcreate）。\n"
            "  |w@agentchar/create <帳號>=<角色名>|<描述>|n：建立新 Character 並指定描述。\n"
            "  |w@agentchar/delete <帳號>=<角色名>|n：從該帳號刪除 Character（對應 chardelete）。\n\n"
            "註：這顆工具直接修改 live DB。"
        )

    def _handle_list(self):
        """Show the target account's roster."""

        account_name = (self.args or self.lhs or "").strip()
        if not account_name:
            raise CharacterAdminError("list 格式需要 `帳號`。")
        self._msg(summarize_account_characters(account_name))

    def _handle_create(self):
        """Create a new character on an existing account."""

        usage = "create 格式需要 `帳號=角色名`，若要給描述可再追加 `|描述`。"
        account_name = (self.lhs or "").strip()
        rhs = (self.rhs or "").strip()
        if not account_name or not rhs:
            raise CharacterAdminError(usage)

        parts = [part.strip() for part in rhs.split("|", 1)]
        char_key = parts[0]
        desc = parts[1] if len(parts) > 1 and parts[1] else None
        if not char_key:
            raise CharacterAdminError(usage)

        result = create_account_character(account_name, char_key, desc=desc, caller=self.caller)
        self._msg(result["message"])

    def _handle_delete(self):
        """Delete a character from an account roster."""

        account_name = (self.lhs or "").strip()
        char_key = (self.rhs or self.args or "").strip()
        if not account_name or not char_key:
            raise CharacterAdminError("delete 格式需要 `帳號=角色名`。")
        result = delete_account_character(account_name, char_key)
        self._msg(result["message"])

    def func(self):
        """Dispatch the selected ``@agentchar`` action."""

        try:
            if "help" in self.switches:
                self._show_help()
                return
            if "create" in self.switches:
                self._handle_create()
                return
            if "delete" in self.switches:
                self._handle_delete()
                return
            self._handle_list()
        except CharacterAdminError as err:
            self._msg(f"|r{err}|n")
