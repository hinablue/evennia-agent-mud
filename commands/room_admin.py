"""Admin command to manage rooms and room-level PVP."""

from commands.command import MuxCommand
from world.room_tools import RoomTools


class CmdAgentRoom(MuxCommand):
    """
    管理房間與房間屬性。

    使用方式:
      @agentroom
      @agentroom/list [關鍵字]
      @agentroom/status 房間
      @agentroom/create 房間=描述
      @agentroom/move 物件=房間
      @agentroom/desc 房間=描述
      @agentroom/door 房間=方向=狀態
      @agentroom/pvp 房間=on|off
      @agentroom/delete 房間
    """

    key = "@agentroom"
    aliases = ["@room"]
    locks = "cmd:perm(Admin) or perm(Developer)"
    help_category = "Admin"
    switch_options = (
        "list",
        "status",
        "create",
        "move",
        "desc",
        "door",
        "pvp",
        "delete",
        "help",
    )

    def _msg(self, text):
        self.caller.msg(text)

    def _show_help(self):
        self._msg(
            "|w@agentroom|n\n"
            "  |w@agentroom|n 或 |w@agentroom/list [關鍵字]|n：列出房間。\n"
            "  |w@agentroom/status 房間|n：顯示房間狀態。\n"
            "  |w@agentroom/create 房間=描述|n：建立房間。\n"
            "  |w@agentroom/move 物件=房間|n：移動物件。\n"
            "  |w@agentroom/desc 房間=描述|n：更新房間描述。\n"
            "  |w@agentroom/door 房間=方向=狀態|n：設定門狀態。\n"
            "  |w@agentroom/pvp 房間=on|off|n：切換房間 PVP。\n"
            "  |w@agentroom/delete 房間|n：刪除房間。"
        )

    def _handle_list(self):
        self._msg(RoomTools.list_rooms(self.args or self.lhs or None))

    def _handle_status(self):
        room_name = (self.args or self.lhs or "").strip()
        if not room_name:
            self._msg("status 格式需要 `房間名`。")
            return
        self._msg(RoomTools.summarize_room(room_name))

    def _handle_create(self):
        if not self.lhs or not self.rhs:
            self._msg("create 格式需要 `房間=描述`。")
            return
        self._msg(RoomTools.create_room(self.lhs, self.rhs))

    def _handle_move(self):
        if not self.lhs or not self.rhs:
            self._msg("move 格式需要 `物件=房間`。")
            return
        self._msg(RoomTools.move_object(self.lhs, self.rhs))

    def _handle_desc(self):
        if not self.lhs or not self.rhs:
            self._msg("desc 格式需要 `房間=描述`。")
            return
        self._msg(RoomTools.update_desc(self.lhs, self.rhs))

    def _handle_door(self):
        parts = [part.strip() for part in (self.args or "").split("=")]
        if len(parts) != 3:
            self._msg("door 格式需要 `房間=方向=狀態`。")
            return
        self._msg(RoomTools.set_door_state(parts[0], parts[1], parts[2]))

    def _handle_pvp(self):
        if not self.lhs or not self.rhs:
            self._msg("pvp 格式需要 `房間=on|off`。")
            return
        value = self.rhs.strip().lower()
        if value not in {"on", "off", "true", "false", "1", "0"}:
            self._msg("pvp 狀態只接受 on/off。")
            return
        enabled = value in {"on", "true", "1"}
        self._msg(RoomTools.set_pvp_state(self.lhs, enabled))

    def _handle_delete(self):
        room_name = (self.args or self.lhs or "").strip()
        if not room_name:
            self._msg("delete 格式需要 `房間`。")
            return
        self._msg(RoomTools.delete_room(room_name))

    def func(self):
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
        if "desc" in self.switches:
            self._handle_desc()
            return
        if "door" in self.switches:
            self._handle_door()
            return
        if "pvp" in self.switches:
            self._handle_pvp()
            return
        if "delete" in self.switches:
            self._handle_delete()
            return
        self._handle_list()
