"""命令

命令描述了帳戶可以對遊戲執行的輸入。"""

from evennia.commands.command import Command as BaseCommand

# 從 Evennia 導入 default_cmds


class Command(BaseCommand):
    """基本命令（如果子命令沒有定義幫助文本，您可能會看到此命令）

    請注意，Evennia 使用該類別的 `__doc__` 字串來建立
    命令的自動幫助條目，因此請確保記錄一致
    在這裡。如果不設定一個，父級的文件字串將顯示（就像現在一樣）。"""

    # 每個 Command 類別實作以下方法，並按此順序調用
    # （實際上只需要 func() ）：
    #
    # - at_pre_cmd()：如果傳回任何真實值，則執行將中止。
    # - parse()：應該對 self.args 執行任何所需的額外解析
    # 並將結果儲存在 self 上。
    # - func()：執行實際工作。
    # - at_post_cmd()：額外的操作，通常是之後完成的事情
    # 每個命令，如提示。
    #
    pass


# -------------------------------------------------------------
#
# 預設指令繼承自
#
# Evennia.commands.default.muxcommand.MuxCommand。
#
# 如果您想對預設命令進行徹底更改，您可以
# 取消註解 MuxCommand 父級的此副本並新增
#
#   COMMAND_DEFAULT_CLASS = "commands.command.MuxCommand"
#
# 到您的設定檔。請注意，預設命令需要
# parse() 方法中實現的功能，因此
# 小心你所做的改變。
#
# -------------------------------------------------------------

from evennia.utils import utils


class MuxCommand(Command):
    """這為 MUX 指令奠定了基礎。這個想法
    大多數其他與 Mux 相關的命令應該只是
    繼承於此並且不必實現太多
    除非他們做了特別的事情，否則他們自己解析
    先進的。

    請注意，該類別的 __doc__ 字串（此文字）是
    Evennia 使用它來建立自動說明條目
    命令，因此請確保此處的記錄一致。"""

    def has_perm(self, srcobj):
        """這由 cmdhandler 呼叫來決定
        如果允許 srcobj 執行該指令。
        我們只是為了完整性而在這裡展示 - 我們
        使用命令中的預設檢查感到滿意。"""
        return super().has_perm(srcobj)

    def at_pre_cmd(self):
        """該鉤子在所有命令的 self.parse() 之前調用"""
        pass

    def at_post_cmd(self):
        """該鉤子在命令執行完成後被調用
        （在 self.func() 之後）。"""
        pass

    def parse(self):
        """一旦命令名稱出現，cmdhandler 就會呼叫此方法
        已被識別。它會創建一組新的成員變數
        稍後可以從 self.func() 訪問（見下文）

        輸入此內容時，以下變數可供我們使用
        方法（來自命令定義，並由
        命令處理程序）：
           self.key - 該指令的名稱（'look'）
           self.aliases - 此 cmd 的別名 ('l')
           self.permissions - 此指令的權限字串
           self.help_category - 指令的總體類別

           self.caller - 呼叫此指令的對象
           self.cmdstring - 用於呼叫此命令的實際命令名稱
                            （這可以讓您知道使用了哪個別名，
                             例如）
           self.args - 原始輸入； self.cmdstring 之後的所有內容。
           self.cmdset - 從中選擇此命令的 cmdset。不
                         經常使用（對於“help”等命令很有用或
                         列出所有可用的命令等）
           self.obj - 定義此指令的物件。常常是
                         與 self.caller 相同。

        MUX 指令有以下可能的語法：

          名稱[包含多個單字][/switch[/switch..]] arg1[,arg2,...] [[=|,] arg[,..]]

        '名稱[有幾個單字]'部分已經由
        此時cmdhandler，並儲存在self.cmdname中（我們不使用
        就在這裡）。命令的其餘部分存儲在 self.args 中，可以
        從開關指示器 / 開始。

        該解析器將 self.args 分解為其組成部分並將它們儲存在
        以下變數：
          self.switches = [/開關清單（不含 /）]
          self.raw = 這是原始參數輸入，包括開關
          self.args = 這被重新定義為*除了*開關之外的所有內容
          self.lhs = = (lhs:'左側') 左側的所有內容。如果
                     沒有找到 =，這與 self.args 相同。
          self.rhs： = (rhs:'右側') 右側的所有內容。
                    如果沒有找到“=”，則為“無”。
          self.lhslist - [self.lhs 用逗號分割成列表]
          self.rhslist - [self.rhs 清單用逗號分割成列表]
          self.arglist = [以空格分隔的參數清單（已刪除，包括“=”（如果存在））]

          所有參數和列表成員都被去除了周圍多餘的空格
          字串，但大小寫被保留。"""
        raw = self.args
        args = raw.strip()

        # 分離開關
        switches = []
        if args and len(args) > 1 and args[0] == "/":
            # 我們有一個開關，或一組開關。它們以空格結尾。
            switches = args[1:].split(None, 1)
            if len(switches) > 1:
                switches, args = switches
                switches = switches.split("/")
            else:
                args = ""
                switches = switches[0].split("/")
        arglist = [arg.strip() for arg in args.split()]

        # 檢查 arg1、arg2、... = argA、argB、... 構造
        lhs, rhs = args, None
        lhslist, rhslist = [arg.strip() for arg in args.split(",")], []
        if args and "=" in args:
            lhs, rhs = [arg.strip() for arg in args.split("=", 1)]
            lhslist = [arg.strip() for arg in lhs.split(",")]
            rhslist = [arg.strip() for arg in rhs.split(",")]

        # 儲存到物件屬性：
        self.raw = raw
        self.switches = switches
        self.args = args.strip()
        self.arglist = arglist
        self.lhs = lhs
        self.lhslist = lhslist
        self.rhs = rhs
        self.rhslist = rhslist

        # 如果該類別本身設定了 account_caller 屬性，我們將
        # 如果可能的话，请确保 self.caller 始终是该帐户。我們還創造
        # 傀儡物件的特殊屬性「字元」（如果有）。這
        # 僅適用於在帳戶上定義的命令。
        if hasattr(self, "account_caller") and self.account_caller:
            if utils.inherits_from(
                self.caller, "evennia.objects.objects.DefaultObject"
            ):
                # 呼叫者是一個物件/角色
                self.character = self.caller
                self.caller = self.caller.account
            elif utils.inherits_from(
                self.caller, "evennia.accounts.accounts.DefaultAccount"
            ):
                # 來電者已經是個帳戶
                self.character = self.caller.get_puppet(self.session)
            else:
                self.character = None
