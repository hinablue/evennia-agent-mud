"""Game-local RP command set wrappers."""

from evennia.commands.cmdset import CmdSet
from evennia.contrib.rpg.rpsystem import (
    CmdEmote,
    CmdMask,
    CmdPose,
    CmdRecog,
    CmdSay,
    CmdSdesc,
)


class CmdGameEmote(CmdEmote):
    """Describe an action in the room."""

    aliases = [":", "動作", "表情"]

    def get_help(self, caller, cmdset):
        """Return Traditional Chinese help for the local RP emote command."""
        return """描述角色動作。

用法：
  emote <動作文字>
  動作 <動作文字>
  表情 <動作文字>
  : <動作文字>

範例：
  動作 /me 微微點頭。
  表情 /me 看向 /高個子男人。

可使用 RPSystem 的 /ref 標記指向同房間角色或物件，實際顯示會依觀看者的短描與認出設定替換。"""


class CmdGameSay(CmdSay):
    """Speak as your character."""

    aliases = ['"', "'", "說", "講", "說話"]

    def get_help(self, caller, cmdset):
        """Return Traditional Chinese help for the local RP say command."""
        return """以角色身分說話。

用法：
  say <訊息>
  說 <訊息>
  講 <訊息>

訊息會送給目前所在地點中的所有人，並走 RPSystem 的發話流程。"""


class CmdGameSdesc(CmdSdesc):
    """Set or view a short description."""

    aliases = ["短描", "外貌", "描述"]

    def get_help(self, caller, cmdset):
        """Return Traditional Chinese help for the local RP sdesc command."""
        return """設定或查看自己的短描。

用法：
  sdesc <短描>
  短描 <短描>
  sdesc
  sdesc clear

短描是其他人在 RPSystem 描述、動作與辨認流程中看到你的簡短外觀。"""


class CmdGamePose(CmdPose):
    """Set a static pose."""

    aliases = ["姿態", "姿勢"]

    def get_help(self, caller, cmdset):
        """Return Traditional Chinese help for the local RP pose command."""
        return """設定靜態姿態。

用法：
  pose <姿態文字>
  姿態 <姿態文字>
  pose default <預設姿態>
  pose reset
  pose <物件> = <姿態文字>

姿態會接在短描後方顯示。未加標點時，系統會自動補上句點。"""

    def parse(self):
        """Normalize Chinese mode words before delegating to upstream parsing."""
        original_args = self.args
        stripped = self.args.strip()
        if stripped.startswith("預設"):
            self.args = "default" + stripped[len("預設") :]
        elif stripped.startswith("重置") or stripped.startswith("清除"):
            self.args = "reset" + stripped[2:]
        try:
            super().parse()
        finally:
            if self.args == original_args:
                self.args = original_args.strip()


class CmdGameRecog(CmdRecog):
    """Recognize or forget another character."""

    aliases = ["recognize", "forget", "認出", "記住", "忘記"]

    def get_help(self, caller, cmdset):
        """Return Traditional Chinese help for the local RP recog command."""
        return """辨認或忘記同房間中的角色。

用法：
  recog
  recog <短描> as <稱呼>
  認出 <短描> as <稱呼>
  記住 <短描> as <稱呼>
  forget <稱呼>
  忘記 <稱呼>

不帶參數時會列出目前記住的稱呼。"""

    def parse(self):
        """Support Chinese separators before delegating to upstream parsing."""
        self.args = self.args.replace(" 作為 ", " as ").replace(" 叫做 ", " as ")
        super().parse()

    @staticmethod
    def normalize_cmdstring(cmdstring):
        """Return the upstream command string for local recog aliases."""
        return "forget" if cmdstring == "忘記" else cmdstring

    def func(self):
        """Normalize Chinese forget alias so upstream takes the forget branch."""
        original_cmdstring = self.cmdstring
        self.cmdstring = self.normalize_cmdstring(original_cmdstring)
        try:
            return super().func()
        finally:
            self.cmdstring = original_cmdstring


class CmdGameMask(CmdMask):
    """Wear or remove an RP mask."""

    aliases = ["unmask", "面具", "偽裝", "卸下面具", "脫下面具", "解除偽裝"]

    def get_help(self, caller, cmdset):
        """Return Traditional Chinese help for the local RP mask command."""
        return """戴上或取下面具，暫時隱藏原本短描。

用法：
  mask <新的短描>
  面具 <新的短描>
  偽裝 <新的短描>
  unmask
  卸下面具
  脫下面具

戴上面具後，其他人的辨認會被暫時停用；取下面具後會恢復原本短描。"""

    @staticmethod
    def normalize_cmdstring(cmdstring):
        """Return the upstream command string for local mask aliases."""
        if cmdstring in {"面具", "偽裝"}:
            return "mask"
        if cmdstring in {"卸下面具", "脫下面具", "解除偽裝"}:
            return "unmask"
        return cmdstring

    def func(self):
        """Normalize Chinese mask aliases so upstream takes the correct branch."""
        original_cmdstring = self.cmdstring
        self.cmdstring = self.normalize_cmdstring(original_cmdstring)
        try:
            return super().func()
        finally:
            self.cmdstring = original_cmdstring


class GameRPSystemCmdSet(CmdSet):
    """Game-local RP command set.

    This mirrors Evennia's contrib RPSystemCmdSet first, then gives agent-mud
    a stable place to localize aliases, help text, and player-facing messages.
    """

    key = "agent_mud_rpsystem_cmdset"

    def at_cmdset_creation(self):
        """Populate RP commands used by the game world."""
        self.add(CmdGameEmote())
        self.add(CmdGameSay())
        self.add(CmdGameSdesc())
        self.add(CmdGamePose())
        self.add(CmdGameRecog())
        self.add(CmdGameMask())
