"""戰鬥和AI管理指揮。"""

from commands.command import MuxCommand
from world.combat_tools import (
    CombatSpecError,
    force_win,
    set_npc_state,
    stop_combat,
)


class CmdAgentCombat(MuxCommand):
    """
    管理戰鬥狀態與 AI 行為。

    使用方式:
      @agentcombat
      @agentcombat/stop <名稱>
      @agentcombat/forcewin <名稱>
      @agentcombat/setstate <NPC>=<狀態>
    """

    key = "@agentcombat"
    aliases = ["@combat"]
    locks = "cmd:perm(Admin) or perm(Developer)"
    help_category = "管理"
    switch_options = ("stop", "forcewin", "setstate", "help")

    def _msg(self, text):
        self.caller.msg(text)

    def _show_help(self):
        self._msg(
            "|w@agentcombat|n\n"
            "  |w@agentcombat/stop <名稱>|n：強行終止戰鬥。\n"
            "  |w@agentcombat/forcewin <名稱>|n：強制設定獲勝。\n"
            "  |w@agentcombat/setstate <NPC>=狀態|n：切換 AI 狀態 (e.g. Aggressive)。\n"
        )

    def _handle_stop(self):
        char_key = (self.args or self.lhs or "").strip()
        if not char_key:
            raise CombatSpecError("stop 格式需要 `名稱`。")
        result = stop_combat(char_key)
        self._msg(result["message"])

    def _handle_forcewin(self):
        char_key = (self.args or self.lhs or "").strip()
        if not char_key:
            raise CombatSpecError("forcewin 格式需要 `名稱`。")
        result = force_win(char_key)
        self._msg(result["message"])

    def _handle_setstate(self):
        if not self.lhs or not self.rhs:
            raise CombatSpecError("setstate 格式需要 `NPC=狀態`。")
        npc_key = self.lhs.strip()
        state = self.rhs.strip()
        result = set_npc_state(npc_key, state)
        self._msg(result["message"])

    def func(self):
        try:
            if "help" in self.switches:
                self._show_help()
                return
            if "stop" in self.switches:
                self._handle_stop()
                return
            if "forcewin" in self.switches:
                self._handle_forcewin()
                return
            if "setstate" in self.switches:
                self._handle_setstate()
                return
            self._show_help()
        except CombatSpecError as err:
            self._msg(f"|r{err}|n")
