"""GM 管理指令：@kingdom

建國、列表、刪國、追加額度、狀態查看。
"""

from commands.command import MuxCommand
from world.kingdom import (
    create_kingdom,
    get_kingdom_by_name,
    get_kingdom_by_king,
    add_room_quota,
    get_kingdom_status,
)


class CmdKingdomAdmin(MuxCommand):
    """
    GM 管理國家。

    用法:
      @kingdom/create <King名稱>=<國名>,<入口房間>,<房間額度>
      @kingdom/list
      @kingdom/status <國名>
      @kingdom/quota <國名>=<新總額度>
      @kingdom/delete <國名>

    範例:
      @kingdom/create 阿爾泰=阿斯特拉,迎賓大廳,10
      @kingdom/status 阿斯特拉
      @kingdom/quota 阿斯特拉=20
    """

    key = "@kingdom"
    aliases = ["@kingdom_admin"]
    locks = "cmd:perm(Admin) or perm(Developer)"
    help_category = "Admin"
    switch_options = ("create", "list", "status", "quota", "delete", "help")

    def _msg(self, text):
        self.caller.msg(text)

    def _parse_create_args(self):
        """解析 create 參數: King名稱=國名,入口房間,額度"""
        if not self.args or "=" not in self.args:
            raise ValueError(
                "格式：@kingdom/create <King名稱>=<國名>,<入口房間>,<額度>"
            )

        king_name, rest = self.args.split("=", 1)
        king_name = king_name.strip()

        parts = [p.strip() for p in rest.split(",")]
        if len(parts) != 3:
            raise ValueError("需要 3 個參數：國名,入口房間,額度")

        kingdom_name, entrance_room_name, quota_str = parts
        try:
            quota = int(quota_str)
        except ValueError:
            raise ValueError("額度必須是整數")

        return king_name, kingdom_name, entrance_room_name, quota

    def _handle_create(self):
        from evennia import search_object
        from evennia.accounts.models import AccountDB
        from evennia.utils.utils import inherits_from
        from typeclasses.characters import Character

        king_name, kingdom_name, entrance_room_name, quota = self._parse_create_args()

        # 找 King character（或建立新的）
        king_matches = search_object(king_name, exact=True)
        if king_matches:
            king_char = king_matches[0]
            if not inherits_from(king_char, "typeclasses.characters.Character"):
                self._msg(f"`{king_name}` 不是 Character 類別。")
                return
        else:
            # 建立新 King character（無帳號綁定，GM 後續綁定）
            from evennia import create_object

            entrance_room = search_object(entrance_room_name, exact=True)
            if not entrance_room:
                self._msg(f"入口房間不存在：{entrance_room_name}")
                return
            entrance_room = entrance_room[0]

            king_char = create_object(
                Character,
                key=king_name,
                location=entrance_room,
                home=entrance_room,
                attributes=[
                    ("desc", f"{kingdom_name} 的國王。"),
                    ("is_player_character", False),
                ],
            )
            self._msg(f"已建立新 King character：{king_name}")

        # 找入口房間
        entrance_matches = search_object(entrance_room_name, exact=True)
        if not entrance_matches:
            self._msg(f"入口房間不存在：{entrance_room_name}")
            return
        entrance_room = entrance_matches[0]
        if not inherits_from(entrance_room, "typeclasses.rooms.Room"):
            self._msg(f"`{entrance_room_name}` 不是房間。")
            return

        # 給 King 權限
        king_account = getattr(king_char, "account", None)
        if king_account:
            king_account.permissions.add("King")
        else:
            self._msg(
                f"⚠️ King `{king_name}` 沒有綁定帳號，請後續用 @agentaccount/bind 綁定帳號並給予 King 權限。"
            )

        # 建國
        try:
            kingdom = create_kingdom(king_char, kingdom_name, entrance_room, quota)
        except ValueError as e:
            self._msg(f"建國失敗：{e}")
            return

        # 打標：入口房間的 GM 連結出口（如果有的話，GM 手動處理）
        self._msg(
            f"|w建國完成！|n\n"
            f"- 國王：{king_char.key}\n"
            f"- 國名：{kingdom.key}\n"
            f"- 入口房間：{entrance_room.key}\n"
            f"- 房間額度：{quota}\n"
            f"- King 權限：已加入 King permission\n\n"
            f"後續：\n"
            f"1. 若 King 需登入遊戲，請用 @agentaccount/bind {king_name}=<帳號>\n"
            f"2. 入口房間內連往 GM 大陸的出口，請手動打上 gm_link_exit tag"
        )

    def _handle_list(self):
        from world.kingdom import Kingdom

        kingdoms = Kingdom.objects.all()
        if not kingdoms:
            self._msg("目前沒有任何國家。")
            return

        lines = ["|w國家列表：|n"]
        for k in kingdoms:
            status = get_kingdom_status(k)
            lines.append(
                f"- {k.key} (King: {status['king']}, 額度: {status['used']}/{status['quota']}, 入口: {status['entrance_room']})"
            )
        self._msg("\n".join(lines))

    def _handle_status(self):
        if not self.args:
            self._msg("用法：@kingdom/status <國名>")
            return
        kingdom = get_kingdom_by_name(self.args.strip())
        if not kingdom:
            self._msg(f"找不到國家：{self.args.strip()}")
            return
        status = get_kingdom_status(kingdom)
        self._msg(
            f"|w{status['name']} 國狀態：|n\n"
            f"- 國王：{status['king']}\n"
            f"- 入口房間：{status['entrance_room']}\n"
            f"- 房間額度：{status['used']}/{status['quota']} (剩餘 {status['remaining']})\n"
            f"- 國籍標籤：{status['nationality_tag']}"
        )

    def _handle_quota(self):
        if not self.args or "=" not in self.args:
            self._msg("用法：@kingdom/quota <國名>=<新總額度>")
            return
        name, quota_str = self.args.split("=", 1)
        name = name.strip()
        try:
            new_quota = int(quota_str.strip())
        except ValueError:
            self._msg("額度必須是整數。")
            return
        kingdom = get_kingdom_by_name(name)
        if not kingdom:
            self._msg(f"找不到國家：{name}")
            return
        total = add_room_quota(kingdom, new_quota - kingdom.db.room_quota)
        self._msg(f"已更新 {name} 總額度為 {total}（原 {kingdom.db.room_quota}）。")

    def _handle_delete(self):
        if not self.args:
            self._msg("用法：@kingdom/delete <國名>")
            return
        kingdom = get_kingdom_by_name(self.args.strip())
        if not kingdom:
            self._msg(f"找不到國家：{self.args.strip()}")
            return
        name = kingdom.key
        kingdom.delete()
        self._msg(f"已刪除國家：{name}")

    def _handle_help(self):
        self._msg(
            "|w@kingdom (GM 管理) |n\n"
            "  @kingdom/create <King名稱>=<國名>,<入口房間>,<額度> - 建國\n"
            "  @kingdom/list - 列出所有國家\n"
            "  @kingdom/status <國名> - 查看國狀態\n"
            "  @kingdom/quota <國名>=<新總額度> - 調整額度\n"
            "  @kingdom/delete <國名> - 刪除國家"
        )

    def func(self):
        switch = self.switches[0] if self.switches else "help"
        handlers = {
            "create": self._handle_create,
            "list": self._handle_list,
            "status": self._handle_status,
            "quota": self._handle_quota,
            "delete": self._handle_delete,
            "help": self._handle_help,
        }
        handler = handlers.get(switch)
        if handler:
            handler()
        else:
            self._msg(f"未知 switch: {switch}")
