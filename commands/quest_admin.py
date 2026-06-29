"""Quest management command."""

from commands.command import MuxCommand
from world.quest_tools import (
    QuestSpecError,
    complete_quest,
    give_quest,
    summarize_quests,
)

class CmdAgentQuest(MuxCommand):
    """
    管理遊戲任務 (Quest)。

    使用方式:
      @agentquest
      @agentquest/status <角色>
      @agentquest/give <角色>=<任務>
      @agentquest/complete <角色>=<任務>
    """

    key = "@agentquest"
    aliases = ["@quest"]
    locks = "cmd:perm(Admin) or perm(Developer)"
    help_category = "Admin"
    switch_options = ("status", "give", "complete", "help")

    def _msg(self, text):
        self.caller.msg(text)

    def _show_help(self):
        self._msg(
            "|w@agentquest|n\n"
            "  |w@agentquest/status <角色>|n：查看玩家任務進度。\n"
            "  |w@agentquest/give <角色>=<任務>|n：強制發放任務。\n"
            "  |w@agentquest/complete <角色>=<任務>|n：強制完成任務。\n"
        )

    def _handle_status(self):
        char_key = (self.args or self.lhs or "").strip()
        if not char_key:
            raise QuestSpecError("status 格式需要 `角色`。")
        self._msg(summarize_quests(char_key))

    def _handle_give(self):
        if not self.lhs or not self.rhs:
            raise QuestSpecError("give 格式需要 `角色=任務`。")
        char_key = self.lhs.strip()
        quest_key = self.rhs.strip()
        result = give_quest(char_key, quest_key)
        self._msg(result["message"])

    def _handle_complete(self):
        if not self.lhs or not self.rhs:
            raise QuestSpecError("complete 格式需要 `角色=任務`。")
        char_key = self.lhs.strip()
        quest_key = self.rhs.strip()
        result = complete_quest(char_key, quest_key)
        self._msg(result["message"])

    def func(self):
        try:
            if "help" in self.switches:
                self._show_help()
                return
            if "status" in self.switches:
                self._handle_status()
                return
            if "give" in self.switches:
                self._handle_give()
                return
            if "complete" in self.switches:
                self._handle_complete()
                return
            self._show_help()
        except QuestSpecError as err:
            self._msg(f"|r{err}|n")
