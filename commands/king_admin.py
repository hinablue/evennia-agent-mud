"""King 管理指令：@king (@kingdom for King).

King 管理自己的國家：建房、建出口、放物件、改國名、刪房、看狀態。
"""

from evennia import search_object
from evennia.utils.utils import inherits_from

from commands.command import MuxCommand
from world.kingdom import (get_kingdom_by_king, get_kingdom_status,
                           rename_kingdom)


class CmdKingAdmin(MuxCommand):
    """
    King 管理自己的國家（需 King 權限）。

    用法:
      @king/status           - 看自己國家狀態
      @king/buildroom <房間名>=<描述> [父房間]  - 在額度內建房
      @king/buildexit <來源房間>=<出口名>,<目標房間> [,alias1,alias2] - 建出口
      @king/buildobj <房間>=<物件名> [,alias1,alias2] [,描述] - 放物件/場景物
      @king/deleteroom <房間名> - 刪除自建房間 (Player 遷回入口房，物品消滅)
      @king/name <新國名>    - 更改國名 (同步 tag 與 Player 國籍)
      @king/help             - 說明

    範例:
      @king/buildroom 花園=滿是玫瑰的庭院
      @king/buildexit 入口大廳=北門,花園,北,往北
      @king/buildobj 花園=石凳,長椅,石頭做的長椅
      @king/deleteroom 廢棄倉庫
      @king/name 新亞斯特拉
    """

    key = "@king"
    aliases = ["@kingdom"]  # 同名不同 lock，King 用這個
    locks = "cmd:perm(King)"
    help_category = "King"
    switch_options = (
        "status",
        "buildroom",
        "buildexit",
        "buildobj",
        "deleteroom",
        "name",
        "help",
    )

    def _msg(self, text):
        self.caller.msg(text)

    def _get_kingdom(self):
        """取得 caller 的 Kingdom"""
        caller = self.caller
        if not getattr(caller.db, "is_king", False):
            self._msg("你不是國王。")
            return None
        kingdom = get_kingdom_by_king(caller)
        if not kingdom:
            self._msg("找不到你的國家資料。")
            return None
        return kingdom

    def _find_room_in_kingdom(self, kingdom, room_name):
        """在自國範圍內找房間"""
        matches = search_object(room_name, exact=True)
        if not matches:
            return None
        room = matches[0]
        if not inherits_from(room, "typeclasses.rooms.Room"):
            return None
        # 檢查是否屬於自國
        if not room.tags.has(f"kingdom:{kingdom.key}", category="ownership"):
            return None
        return room

    def _handle_status(self):
        kingdom = self._get_kingdom()
        if not kingdom:
            return
        status = get_kingdom_status(kingdom)
        self._msg(
            f"|w你的國家：{status['name']}|n\n"
            f"- 國王：{status['king']}\n"
            f"- 入口房間：{status['entrance_room']}\n"
            f"- 房間額度：{status['used']}/{status['quota']} (剩餘 {status['remaining']})\n"
            f"- 國籍標籤：{status['nationality_tag']}"
        )

    def _handle_buildroom(self):
        kingdom = self._get_kingdom()
        if not kingdom:
            return

        if not self.args or "=" not in self.args:
            self._msg("用法：@king/buildroom <房間名>=<描述> [父房間]")
            return

        # 解析參數
        room_part, rest = self.args.split("=", 1)
        room_name = room_name = room_part.strip()

        # rest 可能包含描述和可選的父房間（用 | 分隔）
        parts = [p.strip() for p in rest.split("|")]
        desc = parts[0] if parts else ""
        parent_room_name = parts[1] if len(parts) > 1 else None

        if not room_name:
            self._msg("房間名不可為空。")
            return

        # 檢查額度
        if not kingdom.can_create_room():
            self._msg(
                f"房間額度已滿 ({kingdom.db.rooms_created}/{kingdom.db.room_quota})，請向 GM 申請追加。"
            )
            return

        # 找父房間（預設為入口房間）
        if parent_room_name:
            parent_room = self._find_room_in_kingdom(kingdom, parent_room_name)
            if not parent_room:
                self._msg(f"找不到父房間：{parent_room_name}（或不屬於你的國家）。")
                return
        else:
            parent_room = kingdom.db.entrance_room
            if not parent_room:
                self._msg("入口房間未設定，請聯繫 GM。")
                return

        # 建立房間
        from evennia import create_object

        from typeclasses.rooms import Room

        new_room = create_object(Room, key=room_name, location=parent_room)
        new_room.db.desc = desc or Room.fallback_desc
        new_room.save()

        # 打標
        new_room.tags.add(f"kingdom:{kingdom.key}", category="ownership")
        new_room.tags.add("king_created", category="ownership")
        new_room.save()

        # 更新計數
        kingdom.increment_rooms_created()

        self._msg(
            f"|w建房成功！|n\n"
            f"- 房間：{new_room.key}\n"
            f"- 描述：{new_room.db.desc}\n"
            f"- 位置：{parent_room.key}\n"
            f"- 額度剩餘：{kingdom.get_quota_remaining()}"
        )

    def _handle_buildexit(self):
        kingdom = self._get_kingdom()
        if not kingdom:
            return

        if not self.args or "=" not in self.args:
            self._msg(
                "用法：@king/buildexit <來源房間>=<出口名>,<目標房間> [,alias1,alias2...]"
            )
            return

        source_name, rest = self.args.split("=", 1)
        source_name = source_name.strip()

        parts = [p.strip() for p in rest.split(",")]
        if len(parts) < 2:
            self._msg("至少需要出口名和目標房間。")
            return

        exit_name = parts[0]
        dest_name = parts[1]
        aliases = parts[2:] if len(parts) > 2 else []

        # 找來源房間
        source_room = self._find_room_in_kingdom(kingdom, source_name)
        if not source_room:
            self._msg(f"來源房間不存在或不屬於你的國家：{source_name}")
            return

        # 找目標房間
        dest_room = self._find_room_in_kingdom(kingdom, dest_name)
        if not dest_room:
            self._msg(f"目標房間不存在或不屬於你的國家：{dest_name}")
            return

        # 建立出口（雙向）
        from evennia import create_object

        from typeclasses.exits import Exit

        # 出口：source -> dest
        exit1 = create_object(
            Exit, key=exit_name, location=source_room, destination=dest_room
        )
        if aliases:
            exit1.aliases.add(*aliases)
        exit1.tags.add(f"kingdom:{kingdom.key}", category="ownership")
        exit1.tags.add("king_created", category="ownership")
        exit1.save()

        # 反向出口（預設用目標房間名做 key）
        back_name = source_room.key
        exit2 = create_object(
            Exit, key=back_name, location=dest_room, destination=source_room
        )
        exit2.tags.add(f"kingdom:{kingdom.key}", category="ownership")
        exit2.tags.add("king_created", category="ownership")
        exit2.save()

        self._msg(
            f"|w建出口成功！|n\n"
            f"- {source_room.key} -> {exit_name} -> {dest_room.key}\n"
            f"- 反向：{dest_room.key} -> {back_name} -> {source_room.key}"
        )

    def _handle_buildobj(self):
        kingdom = self._get_kingdom()
        if not kingdom:
            return

        if not self.args or "=" not in self.args:
            self._msg("用法：@king/buildobj <房間>=<物件名> [,alias1,alias2] [,描述]")
            return

        room_name, rest = self.args.split("=", 1)
        room_name = room_name.strip()

        parts = [p.strip() for p in rest.split(",")]
        obj_name = parts[0] if parts else ""
        aliases = parts[1:-1] if len(parts) > 2 else []
        desc = parts[-1] if len(parts) > 1 else ""

        if not obj_name:
            self._msg("物件名不可為空。")
            return

        # 找房間
        room = self._find_room_in_kingdom(kingdom, room_name)
        if not room:
            self._msg(f"房間不存在或不屬於你的國家：{room_name}")
            return

        # 建立物件
        from evennia import create_object

        from typeclasses.objects import Object

        new_obj = create_object(Object, key=obj_name, location=room)
        if aliases:
            new_obj.aliases.add(*aliases)
        new_obj.db.desc = desc or Object.default_description
        new_obj.tags.add(f"kingdom:{kingdom.key}", category="ownership")
        new_obj.tags.add("king_created", category="ownership")
        new_obj.save()

        self._msg(
            f"|w放置物件成功！|n\n"
            f"- 物件：{new_obj.key}\n"
            f"- 位置：{room.key}\n"
            f"- 描述：{new_obj.db.desc}"
        )

    def _handle_deleteroom(self):
        kingdom = self._get_kingdom()
        if not kingdom:
            return

        if not self.args:
            self._msg("用法：@king/deleteroom <房間名>")
            return

        room_name = self.args.strip()
        room = self._find_room_in_kingdom(kingdom, room_name)
        if not room:
            self._msg(f"房間不存在或不屬於你的國家：{room_name}")
            return

        # 防呆：不可刪入口房
        if room.tags.has("king_entrance", category="ownership"):
            self._msg("不可刪除入口房間。")
            return

        # 遷移房內 Player 到入口房
        entrance = kingdom.db.entrance_room
        moved = 0
        for char in room.contents_get(content_type="character"):
            if char.has_account:  # Player
                char.move_to(entrance, quiet=False)
                char.msg(f"你所在的房間已被國王拆除，你被傳送回 {kingdom.key} 的入口。")
                moved += 1

        # 刪除房內所有物件（NPC、物品、出口）
        deleted_count = 0
        for obj in list(room.contents):
            obj.delete()
            deleted_count += 1

        # 刪除房間本身
        room.delete()

        # 更新額度
        kingdom.decrement_rooms_created()

        self._msg(
            f"|w刪除房間完成。|n\n"
            f"- 房間：{room_name}\n"
            f"- 遷移 Player：{moved} 人\n"
            f"- 刪除物件/出口：{deleted_count} 個\n"
            f"- 額度剩餘：{kingdom.get_quota_remaining()}"
        )

    def _handle_name(self):
        kingdom = self._get_kingdom()
        if not kingdom:
            return

        if not self.args:
            self._msg("用法：@king/name <新國名>")
            return

        new_name = self.args.strip()
        if not new_name:
            self._msg("國名不可為空。")
            return

        try:
            result = rename_kingdom(kingdom, new_name)
        except ValueError as e:
            self._msg(f"改名失敗：{e}")
            return

        self._msg(
            f"|w改名成功！|n\n"
            f"- 舊國名：{result['old_name']}\n"
            f"- 新國名：{result['new_name']}\n"
            f"- 已同步更新所有自國物件 tag、Player nationality、頻道"
        )

    def _handle_help(self):
        self._msg(
            "|w@king (King 管理自己國家) |n\n"
            "  @king/status - 看自己國家狀態\n"
            "  @king/buildroom <房間名>=<描述> [父房間] - 建房\n"
            "  @king/buildexit <來源房間>=<出口名>,<目標房間> [,alias...] - 建出口\n"
            "  @king/buildobj <房間>=<物件名> [,alias...] [,描述] - 放物件\n"
            "  @king/deleteroom <房間名> - 刪房 (Player 遷回入口)\n"
            "  @king/name <新國名> - 改國名\n"
            "  @king/help - 此說明"
        )

    def func(self):
        switch = self.switches[0] if self.switches else "help"
        handlers = {
            "status": self._handle_status,
            "buildroom": self._handle_buildroom,
            "buildexit": self._handle_buildexit,
            "buildobj": self._handle_buildobj,
            "deleteroom": self._handle_deleteroom,
            "name": self._handle_name,
            "help": self._handle_help,
        }
        handler = handlers.get(switch)
        if handler:
            handler()
        else:
            self._msg(f"未知 switch: {switch}")
