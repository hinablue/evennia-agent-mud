"""對像管理命令。"""

from commands.command import MuxCommand
from world.object_tools import (
    ObjectSpecError,
    create_object_admin,
    delete_object,
    equip_object,
    list_objects,
    move_object,
    set_object_desc,
    set_object_stat,
    set_object_takeable,
    set_object_equippable,
    summarize_object,
)


class CmdAgentObject(MuxCommand):
    """
    管理世界物件 (Object)。

    使用方式:
      @agentobject
      @agentobject/list [房間]
      @agentobject/status <名稱>
      @agentobject/create <名稱>=<房間>|<描述>
      @agentobject/move <名稱>=<房間>
      @agentobject/desc <名稱>=<描述>
      @agentobject/takeable <名稱>=1(可拿)/0(不可拿)
      @agentobject/equippable <名稱>=1(可穿)/0(不可穿)
      @agentobject/setstat <名稱>=<屬性:值>
      @agentobject/equip <角色>=<物品>|<槽位>
      @agentobject/delete <名稱>
    """

    key = "@agentobject"
    aliases = ["@obj"]
    locks = "cmd:perm(Admin) or perm(Developer)"
    help_category = "管理"
    switch_options = (
        "list",
        "status",
        "create",
        "move",
        "desc",
        "takeable",
        "equippable",
        "setstat",
        "equip",
        "delete",
        "help",
    )

    def _msg(self, text):
        self.caller.msg(text)

    def _show_help(self):
        self._msg(
            "|w@agentobject|n\n"
            "  |w@agentobject/list [房間]|n：列出所有物件。\n"
            "  |w@agentobject/status <名稱>|n：查看物件詳情。\n"
            "  |w@agentobject/create <名稱>=<房間>|<描述>|n：建立物件。\n"
            "  |w@agentobject/move <名稱>=<房間>|n：移動物件。\n"
            "  |w@agentobject/desc <名稱>=<描述>|n：更新描述。\n"
            "  |w@agentobject/takeable <名稱>=1/0|n：設定可拿取屬性。\n"
            "  |w@agentobject/equippable <名稱>=1/0|n：設定可裝備屬性。\n"
            "  |w@agentobject/setstat <名稱>=屬性:值|n：修改 RPG 屬性 (e.g. attack:5)。\n"
            "  |w@agentobject/equip <角色>=<物品>|<槽位>|n：強制裝備物品。\n"
            "  |w@agentobject/delete <名稱>|n：刪除物件。\n"
        )

    def _handle_list(self):
        room_name = (self.args or self.lhs or "").strip()
        self._msg(list_objects(room_name or None))

    def _handle_status(self):
        obj_key = (self.args or self.lhs or "").strip()
        if not obj_key:
            raise ObjectSpecError("status 格式需要 `名稱`。")
        self._msg(summarize_object(obj_key))

    def _handle_create(self):
        if not self.lhs or not self.rhs:
            raise ObjectSpecError("create 格式需要 `名稱=房間|描述`。")
        obj_key = self.lhs.strip()
        parts = [p.strip() for p in self.rhs.split("|")]
        room_name = parts[0]
        desc = parts[1] if len(parts) > 1 else None
        result = create_object_admin(obj_key, room_name, desc)
        self._msg(result["message"])

    def _handle_move(self):
        if not self.lhs or not self.rhs:
            raise ObjectSpecError("move 格式需要 `名稱=房間`。")
        obj_key = self.lhs.strip()
        room_name = self.rhs.strip()
        result = move_object(obj_key, room_name)
        self._msg(result["message"])

    def _handle_desc(self):
        if not self.lhs or not self.rhs:
            raise ObjectSpecError("desc 格式需要 `名稱=描述`。")
        obj_key = self.lhs.strip()
        desc = self.rhs.strip()
        result = set_object_desc(obj_key, desc)
        self._msg(result["message"])

    def _handle_takeable(self):
        if not self.lhs or not self.rhs:
            raise ObjectSpecError("takeable 格式需要 `名稱=1(可拿)/0(不可拿)`。")
        obj_key = self.lhs.strip()
        val = self.rhs.strip() == "1"
        result = set_object_takeable(obj_key, val)
        self._msg(result["message"])

    def _handle_equippable(self):
        if not self.lhs or not self.rhs:
            raise ObjectSpecError("equippable 格式需要 `名稱=1(可穿)/0(不可穿)`。")
        obj_key = self.lhs.strip()
        val = self.rhs.strip() == "1"
        result = set_object_equippable(obj_key, val)
        self._msg(result["message"])

    def _handle_setstat(self):
        if not self.lhs or not self.rhs:
            raise ObjectSpecError("setstat 格式需要 `名稱=屬性:值`。")
        obj_key = self.lhs.strip()
        stat_pair = self.rhs.strip()
        result = set_object_stat(obj_key, stat_pair)
        self._msg(result["message"])

    def _handle_equip(self):
        if not self.lhs or not self.rhs:
            raise ObjectSpecError("equip 格式需要 `角色=物品|槽位`。")
        char_key = self.lhs.strip()
        parts = [p.strip() for p in self.rhs.split("|")]
        obj_key = parts[0]
        slot = parts[1] if len(parts) > 1 else "main"
        result = equip_object(char_key, obj_key, slot)
        self._msg(result["message"])

    def _handle_delete(self):
        obj_key = (self.args or self.lhs or "").strip()
        if not obj_key:
            raise ObjectSpecError("delete 格式需要 `名稱`。")
        result = delete_object(obj_key)
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
            if "create" in self.switches:
                self._handle_create()
                return
            if "move" in self.switches:
                self._handle_move()
                return
            if "desc" in self.switches:
                self._handle_desc()
                return
            if "takeable" in self.switches:
                self._handle_takeable()
                return
            if "equippable" in self.switches:
                self._handle_equippable()
                return
            if "setstat" in self.switches:
                self._handle_setstat()
                return
            if "equip" in self.switches:
                self._handle_equip()
                return
            if "delete" in self.switches:
                self._handle_delete()
                return
            self._handle_list()
        except ObjectSpecError as err:
            self._msg(f"|r{err}|n")
