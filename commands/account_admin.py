"""Account management command."""

from commands.command import MuxCommand
from world.account_tools import (
    AccountSpecError,
    add_account_permission,
    appoint_king,
    create_account,
    delete_account,
    list_accounts,
    remove_account_permission,
    set_account_nationality,
    set_account_puppet,
    summarize_account,
    _find_exact_account,
)


class CmdAgentAccount(MuxCommand):
    """
    管理 Account 帳號。

    使用方式:
      @agentaccount
      @agentaccount/list
      @agentaccount/create <帳號>=<密碼>
      @agentaccount/create <帳號>=<密碼>|<email>
      @agentaccount/status <帳號>
      @agentaccount/setpuppet <帳號>=<角色>
      @agentaccount/addperm <帳號>=<King|Player>
      @agentaccount/delperm <帳號>=<King|Player>
      @agentaccount/appoint <帳號>=<角色>  (GM 指定該帳號角色為 King)
      @agentaccount/nationality <帳號>=<國名>  (King/GM 設定帳號下所有角色國籍)
      @agentaccount/delete <帳號>  (僅 GM/Developer/Admin)

    King 使用限制：僅能查看/操作同國籍帳號（含自己）。
    設定國籍需 King 或以上權限。
    delete 僅限 GM/Developer/Admin。
    """

    key = "@agentaccount"
    aliases = ["@account"]
    locks = "cmd:perm(Admin) or perm(Developer) or perm(King)"
    help_category = "Admin"
    switch_options = (
        "list",
        "create",
        "status",
        "setpuppet",
        "addperm",
        "delperm",
        "appoint",
        "nationality",
        "delete",
        "help",
    )

    def _msg(self, text):
        self.caller.msg(text)

    def _caller_permissions(self):
        """Return the caller account's permission strings."""

        account = getattr(self.caller, "account", None)
        if not account:
            return set()
        return set(account.permissions.all())

    def _has_account_delete_access(self):
        """Check whether caller can use @agentaccount/delete."""

        return bool(self._caller_permissions() & {"GM", "Developer", "Admin"})

    def _get_caller_kingdom(self):
        """取得 caller 的 Kingdom（King 才有）"""
        caller = self.caller
        if getattr(caller.db, "is_king", False):
            from world.kingdom import get_kingdom_by_king
            return get_kingdom_by_king(caller)
        return None

    def _is_same_nation_account(self, account):
        """檢查帳號是否屬於同國籍（King 檢查用）"""
        kingdom = self._get_caller_kingdom()
        if not kingdom:
            return True  # GM/Developer 不限制
        nat = kingdom.key
        # 檢查帳號下是否有同國籍角色
        for char in account.characters.all():
            if getattr(char.db, "nationality", "") == nat:
                return True
        # 若帳號無角色，但 caller 自己就是這個帳號，允許
        if account == self.caller.account:
            return True
        return False

    def _filter_by_nation(self, accounts):
        """依國籍過濾帳號清單"""
        kingdom = self._get_caller_kingdom()
        if not kingdom:
            return accounts
        nat = kingdom.key
        return [
            a for a in accounts
            if any(getattr(c.db, "nationality", "") == nat for c in a.characters.all())
            or a == self.caller.account
        ]

    def _show_help(self):
        self._msg(
            "|w@agentaccount|n\n"
            "  |w@agentaccount/list|n：列出所有帳號。\n"
            "  |w@agentaccount/create <帳號>=<密碼>|n：建立新 Account。\n"
            "  |w@agentaccount/create <帳號>=<密碼>|<email>|n：建立新 Account 並設定 email。\n"
            "  |w@agentaccount/status <帳號>|n：查看帳號詳情與角色。\n"
            "  |w@agentaccount/setpuppet <帳號>=<角色>|n：強制切換最後使用角色。\n"
            "  |w@agentaccount/addperm <帳號>=<King|Player>|n：追加層級權限。\n"
            "  |w@agentaccount/delperm <帳號>=<King|Player>|n：移除層級權限。\n"
            "  |w@agentaccount/appoint <帳號>=<角色>|n：GM 指定該帳號角色為 King（單一國家只能有一個 King）。\n"
            "  |w@agentaccount/nationality <帳號>=<國名>|n：設定帳號下所有角色國籍（需 King/GM/Developer/Admin）。\n"
            "  |w註：GM 請改用 @agentworld/role <帳號>=GM|n。\n"
            "  |w@agentaccount/delete <帳號>|n：刪除 Account（僅 GM/Developer/Admin）。\n"
        )

    def _handle_list(self):
        accounts = list_accounts()
        if isinstance(accounts, str):
            self._msg(accounts)
            return
        filtered = self._filter_by_nation(accounts)
        if not filtered:
            self._msg("找不到符合條件的帳號。")
            return
        lines = ["帳號清單："]
        for a in filtered:
            lines.append(f"- {a.key} (角色數: {a.characters.count()})")
        self._msg("\n".join(lines))

    def _handle_create(self):
        usage = "create 格式需要 `帳號=密碼`，若要設定 email 可再追加 `|email`。"
        acc_key = (self.lhs or "").strip()
        rhs = (self.rhs or "").strip()
        if not acc_key or not rhs:
            raise AccountSpecError(usage)

        parts = [part.strip() for part in rhs.split("|", 1)]
        password = parts[0]
        email = parts[1] if len(parts) > 1 and parts[1] else None
        if not password:
            raise AccountSpecError(usage)

        result = create_account(acc_key, password, email=email)
        self._msg(result["message"])

    def _handle_status(self):
        acc_key = (self.args or self.lhs or "").strip()
        if not acc_key:
            raise AccountSpecError("status 格式需要 `帳號`。")
        from evennia import search_account
        account = _find_exact_account(acc_key)
        if not account:
            raise AccountSpecError(f"找不到帳號：{acc_key}")
        if not self._is_same_nation_account(account):
            raise AccountSpecError("King 只能查看同國籍帳號。")
        self._msg(summarize_account(acc_key))

    def _handle_setpuppet(self):
        if not self.lhs or not self.rhs:
            raise AccountSpecError("setpuppet 格式需要 `帳號=角色`。")
        acc_key = self.lhs.strip()
        char_key = self.rhs.strip()
        account = _find_exact_account(acc_key)
        if not account:
            raise AccountSpecError(f"找不到帳號：{acc_key}")
        if not self._is_same_nation_account(account):
            raise AccountSpecError("King 只能操作同國籍帳號。")
        result = set_account_puppet(acc_key, char_key)
        self._msg(result["message"])

    def _handle_addperm(self):
        if not self.lhs or not self.rhs:
            raise AccountSpecError("addperm 格式需要 `帳號=權限`。")
        acc_key = self.lhs.strip()
        perm_name = self.rhs.strip()
        account = _find_exact_account(acc_key)
        if not account:
            raise AccountSpecError(f"找不到帳號：{acc_key}")
        if not self._is_same_nation_account(account):
            raise AccountSpecError("King 只能操作同國籍帳號。")
        result = add_account_permission(acc_key, perm_name)
        self._msg(result["message"])

    def _handle_delperm(self):
        if not self.lhs or not self.rhs:
            raise AccountSpecError("delperm 格式需要 `帳號=權限`。")
        acc_key = self.lhs.strip()
        perm_name = self.rhs.strip()
        account = _find_exact_account(acc_key)
        if not account:
            raise AccountSpecError(f"找不到帳號：{acc_key}")
        if not self._is_same_nation_account(account):
            raise AccountSpecError("King 只能操作同國籍帳號。")
        result = remove_account_permission(acc_key, perm_name)
        self._msg(result["message"])

    def _handle_appoint(self):
        # appoint 是 GM 專用，King 不可用
        kingdom = self._get_caller_kingdom()
        if kingdom:
            raise AccountSpecError("King 不能使用 appoint；請使用 @king/appoint 移交王位。")
        if not self.lhs or not self.rhs:
            raise AccountSpecError("appoint 格式需要 `帳號=角色`。")
        acc_key = self.lhs.strip()
        char_key = self.rhs.strip()
        result = appoint_king(acc_key, char_key)
        self._msg(result["message"])

    def _handle_delete(self):
        if not self._has_account_delete_access():
            raise AccountSpecError("delete 僅限 GM/Developer/Admin 使用。")
        acc_key = (self.args or self.lhs or "").strip()
        if not acc_key:
            raise AccountSpecError("delete 格式需要 `帳號`。")
        account = _find_exact_account(acc_key)
        if not account:
            raise AccountSpecError(f"找不到帳號：{acc_key}")
        result = delete_account(acc_key)
        self._msg(result["message"])

    def _handle_nationality(self):
        if not self.lhs or not self.rhs:
            raise AccountSpecError("nationality 格式需要 `帳號=國名`。")
        acc_key = self.lhs.strip()
        nationality = self.rhs.strip()
        result = set_account_nationality(acc_key, nationality, caller=self.caller)
        self._msg(result["message"])

    def func(self):
        try:
            if "help" in self.switches:
                self._show_help()
                return
            if "list" in self.switches:
                self._handle_list()
                return
            if "create" in self.switches:
                self._handle_create()
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
            if "appoint" in self.switches:
                self._handle_appoint()
                return
            if "nationality" in self.switches:
                self._handle_nationality()
                return
            if "delete" in self.switches:
                self._handle_delete()
                return
            self._handle_list()
        except AccountSpecError as err:
            self._msg(f"|r{err}|n")
