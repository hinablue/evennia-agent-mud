"""Account management command."""

from commands.command import MuxCommand
from world.account_tools import (
    AccountSpecError,
    add_account_permission,
    delete_account,
    list_accounts,
    remove_account_permission,
    set_account_puppet,
    summarize_account,
)

class CmdAgentAccount(MuxCommand):
    """
    管理 Account 帳號。

    使用方式:
      @agentaccount
      @agentaccount/list
      @agentaccount/status <帳號>
      @agentaccount/setpuppet <帳號>=<角色>
      @agentaccount/addperm <帳號>=<權限>
      @agentaccount/delperm <帳號>=<權限>
      @agentaccount/delete <帳號>
    """

    key = "@agentaccount"
    aliases = ["@account"]
    locks = "cmd:perm(Admin) or perm(Developer)"
    help_category = "Admin"
    switch_options = ("list", "status", "setpuppet", "addperm", "delperm", "delete", "help")

    def _msg(self, text):
        self.caller.msg(text)

    def _show_help(self):
        self._msg(
            "|w@agentaccount|n\n"
            "  |w@agentaccount/list|n：列出所有帳號。\n"
            "  |w@agentaccount/status <帳號>|n：查看帳號詳情與角色。\n"
            "  |w@agentaccount/setpuppet <帳號>=<角色>|n：強制切換最後使用角色。\n"
            "  |w@agentaccount/addperm <帳號>=<權限>|n：追加權限。\n"
            "  |w@agentaccount/delperm <帳號>=<權限>|n：移除權限。\n"
            "  |w@agentaccount/delete <帳號>|n：刪除 Account。\n"
        )

    def _handle_list(self):
        self._msg(list_accounts())

    def _handle_status(self):
        acc_key = (self.args or self.lhs or "").strip()
        if not acc_key:
            raise AccountSpecError("status 格式需要 `帳號`。")
        self._msg(summarize_account(acc_key))

    def _handle_setpuppet(self):
        if not self.lhs or not self.rhs:
            raise AccountSpecError("setpuppet 格式需要 `帳號=角色`。")
        acc_key = self.lhs.strip()
        char_key = self.rhs.strip()
        result = set_account_puppet(acc_key, char_key)
        self._msg(result["message"])

    def _handle_addperm(self):
        if not self.lhs or not self.rhs:
            raise AccountSpecError("addperm 格式需要 `帳號=權限`。")
        acc_key = self.lhs.strip()
        perm_name = self.rhs.strip()
        result = add_account_permission(acc_key, perm_name)
        self._msg(result["message"])

    def _handle_delperm(self):
        if not self.lhs or not self.rhs:
            raise AccountSpecError("delperm 格式需要 `帳號=權限`。")
        acc_key = self.lhs.strip()
        perm_name = self.rhs.strip()
        result = remove_account_permission(acc_key, perm_name)
        self._msg(result["message"])

    def _handle_delete(self):
        acc_key = (self.args or self.lhs or "").strip()
        if not acc_key:
            raise AccountSpecError("delete 格式需要 `帳號`。")
        result = delete_account(acc_key)
        self._msg(result["message"])

    def func(self):
        try:
            if "help" in self.switches:
                self._show_help()
                return
            if "list" in self.switches:
                self._handle_list()
                return
            if "status" in self.switches:
                self._handle_status()
                return
            if "setpuppet" in self.switches:
                self._handle_setpuppet()
                return
            if "addperm" in self.switches:
                self._handle_addperm()
                return
            if "delperm" in self.switches:
                self._handle_delperm()
                return
            if "delete" in self.switches:
                self._handle_delete()
                return
            self._handle_list()
        except AccountSpecError as err:
            self._msg(f"|r{err}|n")
