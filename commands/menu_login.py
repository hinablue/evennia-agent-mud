"""繁體中文化的登入選單。"""

from django.conf import settings

from evennia import CmdSet, Command, syscmdkeys
from evennia.utils.evmenu import EvMenu
from evennia.utils.utils import (
    callables_from_module,
    class_from_module,
    random_string_from_module,
)

_CONNECTION_SCREEN_MODULE = settings.CONNECTION_SCREEN_MODULE
_GUEST_ENABLED = settings.GUEST_ENABLED
_ACCOUNT = class_from_module(settings.BASE_ACCOUNT_TYPECLASS)
_GUEST = class_from_module(settings.BASE_GUEST_TYPECLASS)

_ACCOUNT_HELP = "輸入新的或既有的登入名稱。"
_PASSWORD_HELP = (
    "密碼至少需要 8 個字元，建議更長，並可包含英文字母、空白、數字與 @ . + - _ ' /。"
)

_ERROR_TRANSLATIONS = {
    "Username and/or password is incorrect.": "帳號或密碼不正確。",
    "Too many authentication failures.": "驗證失敗次數過多。",
    "Too many login failures; please try again in a few minutes.": "登入失敗次數過多，請幾分鐘後再試。",
    "You are creating too many accounts. Please log into an existing account.": "你建立帳號的次數過多，請先登入既有帳號。",
    "Registration is currently disabled.": "目前暫停註冊新帳號。",
    "There was an error creating the Account. If this problem persists, contact an admin.": "建立帳號時發生錯誤；若問題持續，請聯絡管理員。",
    "An error occurred. Please e-mail an admin if the problem persists.": "發生錯誤；若問題持續，請聯絡管理員。",
    "Guest accounts are not enabled on this server.": "這個伺服器目前未啟用訪客帳號。",
    "All guest accounts are in use. Please try again later.": "所有訪客帳號目前都在使用中，請稍後再試。",
    "The Character does not exist.": "該角色不存在。",
    "Account being deleted.": "帳號正在刪除中。",
}


def _translate_error(text):
    text = text or ""
    for source, target in _ERROR_TRANSLATIONS.items():
        text = text.replace(source, target)
    return text


def _translate_errors(errors):
    return "\n".join(_translate_error(error) for error in errors)


def _show_help(caller, raw_string, **kwargs):
    """顯示說明文字，然後重新進入原節點。"""
    help_entry = kwargs["help_entry"]
    caller.msg(help_entry)
    return None


def node_enter_username(caller, raw_text, **kwargs):
    """顯示連線畫面並要求輸入帳號名稱。"""

    def _check_input(caller, username, **kwargs):
        username = username.replace("\x00", "").strip()

        if username == "guest" and _GUEST_ENABLED:
            session = caller
            address = session.address
            account, errors = _GUEST.authenticate(ip=address)
            if account:
                return "node_quit_or_login", {"login": True, "account": account}
            session.msg(f"|R{_translate_errors(errors)}|n")
            return None

        try:
            _ACCOUNT.objects.get(username__iexact=username)
        except _ACCOUNT.DoesNotExist:
            new_user = True
        else:
            new_user = False

        if new_user and not settings.NEW_ACCOUNT_REGISTRATION_ENABLED:
            caller.msg("目前暫停註冊新帳號。")
            return None

        return "node_enter_password", {"new_user": new_user, "username": username}

    callables = callables_from_module(_CONNECTION_SCREEN_MODULE)
    if "connection_screen" in callables:
        connection_screen = callables["connection_screen"]()
    else:
        connection_screen = random_string_from_module(_CONNECTION_SCREEN_MODULE)

    if _GUEST_ENABLED:
        text = "請輸入新的或既有的帳號名稱以登入（輸入 guest 可使用訪客登入）："
    else:
        text = "請輸入新的或既有的帳號名稱以登入："
    text = f"{connection_screen}\n\n{text}"

    options = (
        {"key": "", "goto": "node_enter_username"},
        {"key": ("quit", "q"), "goto": "node_quit_or_login"},
        {
            "key": ("help", "h"),
            "goto": (_show_help, {"help_entry": _ACCOUNT_HELP, **kwargs}),
        },
        {"key": "_default", "goto": _check_input},
    )
    return text, options


def node_enter_password(caller, raw_string, **kwargs):
    """處理密碼輸入。"""

    def _check_input(caller, password, **kwargs):
        username = kwargs["username"]
        new_user = kwargs["new_user"]
        password = password.replace("\x00", "").rstrip("\r\n")

        session = caller
        address = session.address
        if new_user:
            account, errors = _ACCOUNT.create(
                username=username, password=password, ip=address, session=session
            )
        else:
            account, errors = _ACCOUNT.authenticate(
                username=username, password=password, ip=address, session=session
            )

        if account:
            if new_user:
                session.msg(f"|g已建立新帳號 |c{username}|g，歡迎加入。|n")
            return "node_quit_or_login", {"login": True, "account": account}

        session.msg(f"|R{_translate_errors(errors)}|n")
        kwargs["retry_password"] = True
        return "node_enter_password", kwargs

    def _restart_login(caller, *args, **kwargs):
        caller.msg("|y已取消登入。|n")
        return "node_enter_username"

    username = kwargs["username"]
    if kwargs["new_user"]:
        if kwargs.get("retry_password"):
            text = "請重新輸入新密碼："
        else:
            text = f"正在建立新帳號 |c{username}|n。請輸入密碼（留空可取消）："
    else:
        text = f"請輸入帳號 |c{username}|n 的密碼（留空可取消）："
    options = (
        {"key": "", "goto": _restart_login},
        {"key": ("quit", "q"), "goto": "node_quit_or_login"},
        {
            "key": ("help", "h"),
            "goto": (_show_help, {"help_entry": _PASSWORD_HELP, **kwargs}),
        },
        {"key": "_default", "goto": (_check_input, kwargs)},
    )
    return text, options


def node_quit_or_login(caller, raw_text, **kwargs):
    """離開選單：登入或斷線。"""
    session = caller
    if kwargs.get("login"):
        account = kwargs.get("account")
        session.msg("|g登入中……|n")
        session.sessionhandler.login(session, account)
    else:
        session.sessionhandler.disconnect(session, "再會，已登出。")
    return "", {}


class MenuLoginEvMenu(EvMenu):
    """不顯示選項列表的登入選單版本。"""

    def node_formatter(self, nodetext, optionstext):
        return nodetext

    def options_formatter(self, optionlist):
        return ""


class UnloggedinCmdSet(CmdSet):
    """未登入狀態使用的指令集。"""

    key = "DefaultUnloggedin"
    priority = 0

    def at_cmdset_creation(self):
        self.add(CmdUnloggedinLook())


class CmdUnloggedinLook(Command):
    """未登入狀態下的 look 指令，會啟動登入選單。"""

    key = syscmdkeys.CMD_LOGINSTART
    locks = "cmd:all()"
    arg_regex = r"^$"

    def func(self):
        menu_nodes = {
            "node_enter_username": node_enter_username,
            "node_enter_password": node_enter_password,
            "node_quit_or_login": node_quit_or_login,
        }

        MenuLoginEvMenu(
            self.caller,
            menu_nodes,
            startnode="node_enter_username",
            auto_look=False,
            auto_quit=False,
            cmd_on_exit=None,
        )
