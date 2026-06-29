"""Player / Character management command."""

from commands.command import MuxCommand
from world.player_tools import (
    PlayerSpecError,
    add_player_aliases,
    bind_player,
    create_player,
    delete_player,
    move_player,
    remove_player_aliases,
    rename_player,
    send_player_home,
    set_player_aliases,
    set_player_desc,
    set_player_home,
    summarize_player,
    summarize_players,
    summon_player,
    unbind_player,
)


class CmdAgentPlayer(MuxCommand):
    """
    管理 Player / Character。

    使用方式:
      @agentplayer
      @agentplayer/list
      @agentplayer/list 迎賓大廳
      @agentplayer/status Hina
      @agentplayer/create Hina=迎賓大廳|她看起來像剛結束一場長夢。|旅人,小藍
      @agentplayer/create Hina=迎賓大廳|她看起來像剛結束一場長夢。|旅人,小藍|hinablue
      @agentplayer/move Hina=觀測室
      @agentplayer/home Hina=旅館房間
      @agentplayer/sendhome Hina
      @agentplayer/summon Hina=控制中樞
      @agentplayer/rename Hina=HinaBlue
      @agentplayer/desc Hina=她的視線總像慢半拍才落下來。
      @agentplayer/aliases Hina=旅人,小藍,觀測者
      @agentplayer/addaliases Hina=夜行者,旅客
      @agentplayer/delaliases Hina=小藍
      @agentplayer/bind Hina=hinablue
      @agentplayer/unbind Hina
      @agentplayer/unbind Hina=hinablue
      @agentplayer/delete Hina

    不帶 switch 時，等同於 list。
    這顆工具是 live 世界管理工具，不會自動回寫任何 world spec。
    """

    key = "@agentplayer"
    aliases = ["@agentchar", "@playerworld", "@player"]
    locks = "cmd:perm(Admin) or perm(Developer)"
    help_category = "Admin"
    switch_options = ("list", "status", "create", "move", "home", "sendhome", "summon", "rename", "desc", "aliases", "addaliases", "delaliases", "bind", "unbind", "delete", "help")

    def _msg(self, text):
        self.caller.msg(text)

    def _show_help(self):
        self._msg(
            "|w@agentplayer|n\n"
            "  |w@agentplayer|n 或 |w@agentplayer/list [房間]|n：列出所有玩家角色。\n"
            "  |w@agentplayer/status 名稱|n：看單一角色狀態。\n"
            "  |w@agentplayer/create 名稱=房間|描述|alias1,alias2|n：建立未綁帳號的 Character。\n"
            "  |w@agentplayer/create 名稱=房間|描述|alias1,alias2|帳號|n：建立並綁到指定帳號。\n"
            "  |w@agentplayer/move 名稱=房間|n：移動角色到新房間。\n"
            "  |w@agentplayer/home 名稱=房間|n：設定角色 home。\n"
            "  |w@agentplayer/sendhome 名稱|n：把角色送回 home。\n"
            "  |w@agentplayer/summon 名稱=房間|n：傳送角色但不改 home。\n"
            "  |w@agentplayer/rename 名稱=新名稱|n：重新命名角色。\n"
            "  |w@agentplayer/desc 名稱=描述|n：更新描述。\n"
            "  |w@agentplayer/aliases 名稱=alias1,alias2|n：覆寫 aliases。\n"
            "  |w@agentplayer/addaliases 名稱=alias1,alias2|n：追加 aliases。\n"
            "  |w@agentplayer/delaliases 名稱=alias1,alias2|n：移除指定 aliases。\n"
            "  |w@agentplayer/bind 名稱=帳號|n：把現有角色綁到帳號。\n"
            "  |w@agentplayer/unbind 名稱[=帳號]|n：解綁單一或全部帳號。\n"
            "  |w@agentplayer/delete 名稱|n：刪除角色。\n\n"
            "註：這顆工具直接修改 live DB；如果角色已綁帳號，建立流程會套用 Evennia 的 character slot 檢查。"
        )

    def _handle_list(self):
        room_name = (self.args or self.lhs or "").strip()
        self._msg(summarize_players(room_name or None))

    def _handle_status(self):
        char_key = (self.args or self.lhs or "").strip()
        self._msg(summarize_player(char_key))

    def _handle_create(self):
        usage = "create 格式需要 `名稱=房間|描述|alias1,alias2`，若要直接綁帳號可再追加 `|帳號`。"
        if not self.lhs or not self.rhs:
            raise PlayerSpecError(usage)
        char_key = self.lhs.strip()
        parts = [part.strip() for part in self.rhs.split("|")]
        if len(parts) < 3:
            raise PlayerSpecError(usage)
        room_name, desc, alias_part = parts[:3]
        aliases = [alias.strip() for alias in alias_part.split(",") if alias.strip()]
        account_name = parts[3] if len(parts) > 3 and parts[3] else None
        result = create_player(char_key, room_name=room_name, desc=desc, aliases=aliases, account_name=account_name)
        self._msg(result["message"])

    def _handle_move(self):
        char_key = (self.lhs or "").strip()
        room_name = (self.rhs or "").strip()
        if not char_key or not room_name:
            raise PlayerSpecError("move 格式需要 `名稱=房間`。")
        result = move_player(char_key, room_name)
        self._msg(result["message"])

    def _handle_home(self):
        char_key = (self.lhs or "").strip()
        room_name = (self.rhs or "").strip()
        if not char_key or not room_name:
            raise PlayerSpecError("home 格式需要 `名稱=房間`。")
        result = set_player_home(char_key, room_name)
        self._msg(result["message"])

    def _handle_summon(self):
        char_key = (self.lhs or "").strip()
        room_name = (self.rhs or "").strip()
        if not char_key or not room_name:
            raise PlayerSpecError("summon 格式需要 `名稱=房間`。")
        result = summon_player(char_key, room_name)
        self._msg(result["message"])

    def _handle_sendhome(self):
        char_key = (self.args or self.lhs or "").strip()
        if not char_key:
            raise PlayerSpecError("sendhome 格式需要 `名稱`。")
        result = send_player_home(char_key)
        self._msg(result["message"])

    def _handle_rename(self):
        char_key = (self.lhs or "").strip()
        new_name = (self.rhs or "").strip()
        if not char_key or not new_name:
            raise PlayerSpecError("rename 格式需要 `名稱=新名稱`。")
        result = rename_player(char_key, new_name)
        self._msg(result["message"])

    def _handle_desc(self):
        char_key = (self.lhs or "").strip()
        desc = (self.rhs or "").strip()
        if not char_key or not desc:
            raise PlayerSpecError("desc 格式需要 `名稱=描述`。")
        result = set_player_desc(char_key, desc)
        self._msg(result["message"])

    def _handle_aliases(self):
        char_key = (self.lhs or "").strip()
        aliases = [alias.strip() for alias in (self.rhs or "").split(",") if alias.strip()]
        if not char_key or not aliases:
            raise PlayerSpecError("aliases 格式需要 `名稱=alias1,alias2`。")
        result = set_player_aliases(char_key, aliases)
        self._msg(result["message"])

    def _handle_addaliases(self):
        char_key = (self.lhs or "").strip()
        aliases = [alias.strip() for alias in (self.rhs or "").split(",") if alias.strip()]
        if not char_key or not aliases:
            raise PlayerSpecError("addaliases 格式需要 `名稱=alias1,alias2`。")
        result = add_player_aliases(char_key, aliases)
        self._msg(result["message"])

    def _handle_delaliases(self):
        char_key = (self.lhs or "").strip()
        aliases = [alias.strip() for alias in (self.rhs or "").split(",") if alias.strip()]
        if not char_key or not aliases:
            raise PlayerSpecError("delaliases 格式需要 `名稱=alias1,alias2`。")
        result = remove_player_aliases(char_key, aliases)
        self._msg(result["message"])

    def _handle_bind(self):
        char_key = (self.lhs or "").strip()
        account_name = (self.rhs or "").strip()
        if not char_key or not account_name:
            raise PlayerSpecError("bind 格式需要 `名稱=帳號`。")
        result = bind_player(char_key, account_name)
        self._msg(result["message"])

    def _handle_unbind(self):
        char_key = (self.lhs or self.args or "").strip()
        account_name = (self.rhs or "").strip() or None
        if not char_key:
            raise PlayerSpecError("unbind 格式需要 `名稱` 或 `名稱=帳號`。")
        result = unbind_player(char_key, account_name)
        self._msg(result["message"])

    def _handle_delete(self):
        char_key = (self.args or self.lhs or "").strip()
        result = delete_player(char_key)
        self._msg(result["message"])

    def func(self):
        try:
            if "help" in self.switches:
                self._show_help()
                return
            if "status" in self.switches:
                self._handle_status()
                return
            if "create" in self.switches:
                self._handle_create()
                return
            if "move" in self.switches:
                self._handle_move()
                return
            if "home" in self.switches:
                self._handle_home()
                return
            if "sendhome" in self.switches:
                self._handle_sendhome()
                return
            if "summon" in self.switches:
                self._handle_summon()
                return
            if "rename" in self.switches:
                self._handle_rename()
                return
            if "desc" in self.switches:
                self._handle_desc()
                return
            if "aliases" in self.switches:
                self._handle_aliases()
                return
            if "addaliases" in self.switches:
                self._handle_addaliases()
                return
            if "delaliases" in self.switches:
                self._handle_delaliases()
                return
            if "bind" in self.switches:
                self._handle_bind()
                return
            if "unbind" in self.switches:
                self._handle_unbind()
                return
            if "delete" in self.switches:
                self._handle_delete()
                return
            self._handle_list()
        except PlayerSpecError as err:
            self._msg(f"|r{err}|n")
