"""國家管理指令：@agentkingdom。"""

from commands.command import MuxCommand
from world.kingdom import (create_kingdom, delete_kingdom, get_kingdom_by_name,
                           get_kingdom_status, list_kingdoms, rename_kingdom,
                           resolve_caller_kingdom, set_kingdom_entrance,
                           set_kingdom_quota)


class CmdKingdomAdmin(MuxCommand):
    """GM/King 共用的國家管理主入口。"""

    key = "@agentkingdom"
    aliases = ["@kingdom", "@kingdom_admin"]
    locks = "cmd:perm(Admin) or perm(Developer) or perm(King)"
    help_category = "管理"
    switch_options = (
        "countrycreate",
        "countries",
        "countrystatus",
        "countryrename",
        "countryquota",
        "countryentrance",
        "countrydelete",
        "help",
    )

    KING_ALLOWED_SWITCHES = {"countries", "countrystatus", "countryrename"}

    def _msg(self, text):
        self.caller.msg(text)

    def _caller_permissions(self):
        account = getattr(self.caller, "account", None)
        if not account:
            return set()
        return set(account.permissions.all())

    def _has_staff_access(self):
        perms = {perm.lower() for perm in (self._caller_permissions() or [])}
        return bool(perms & {"gm", "developer", "admin"})

    def _has_king_access(self):
        return self._has_staff_access() or "King" in self._caller_permissions()

    def _ensure_switch_access(self):
        active_switches = set(self.switches)
        king_help = (
            "King 只能使用 @agentkingdom/countries、/countrystatus、/countryrename。"
        )

        if not active_switches:
            raise ValueError("請指定 switch；可用 /help 查看說明。")

        if active_switches <= self.KING_ALLOWED_SWITCHES:
            if not self._has_king_access():
                raise ValueError(
                    "@agentkingdom/countries、/countrystatus、/countryrename 僅限 King 或 GM/Developer/Admin。"
                )
            return

        if not self._has_staff_access():
            raise ValueError(king_help)

    def _format_country_status(self, status):
        return (
            f"|w{status['name']} 國狀態：|n\n"
            f"- 國王：{status['king']}\n"
            f"- 入口房間：{status['entrance_room']}\n"
            f"- 房間額度：{status['used']}/{status['quota']} (剩餘 {status['remaining']})\n"
            f"- 國籍標籤：{status['nationality_tag']}"
        )

    def _require_staff_country(self, name):
        kingdom = get_kingdom_by_name(name)
        if not kingdom:
            raise ValueError(f"找不到國家：{name}")
        return kingdom

    def _require_king_actor_country(self):
        kingdom = resolve_caller_kingdom(self.caller)
        if not kingdom:
            raise ValueError("找不到你的國家資料。")
        return kingdom

    def _resolve_country_for_read(self):
        if self._has_staff_access():
            name = (self.args or self.lhs or "").strip()
            if not name:
                raise ValueError("countrystatus 格式需要 `國名`。")
            return self._require_staff_country(name)

        kingdom = self._require_king_actor_country()
        requested = (self.args or self.lhs or "").strip()
        if requested and requested != kingdom.key:
            raise ValueError("King 只能查看自己的國家。")
        return kingdom

    def _parse_countrycreate_args(self):
        if not self.args or "=" not in self.args:
            raise ValueError("countrycreate 格式需要 `King名稱=國名,入口房間,額度`。")
        king_name, rest = self.args.split("=", 1)
        parts = [part.strip() for part in rest.split(",")]
        if len(parts) != 3:
            raise ValueError("countrycreate 格式需要 `King名稱=國名,入口房間,額度`。")
        return king_name.strip(), parts[0], parts[1], parts[2]

    def _handle_countrycreate(self):
        from evennia import search_object

        king_name, country_name, entrance_name, quota = self._parse_countrycreate_args()
        king_matches = search_object(king_name, exact=True)
        if not king_matches:
            raise ValueError(f"找不到 King 角色：{king_name}")
        entrance_matches = search_object(entrance_name, exact=True)
        if not entrance_matches:
            raise ValueError(f"找不到入口房間：{entrance_name}")
        try:
            result = create_kingdom(
                king_matches[0], country_name, entrance_matches[0], int(quota)
            )
        except ValueError as err:
            raise ValueError(str(err)) from err
        self._msg(f"已建立國家：{result.key}")

    def _handle_countries(self):
        if self._has_staff_access():
            kingdoms = list_kingdoms()
            if not kingdoms:
                self._msg("目前沒有任何國家。")
                return
            lines = ["|w國家列表：|n"]
            for kingdom in kingdoms:
                status = get_kingdom_status(kingdom)
                lines.append(
                    f"- {status['name']} (King: {status['king']}, 額度: {status['used']}/{status['quota']}, 入口: {status['entrance_room']})"
                )
            self._msg("\n".join(lines))
            return

        kingdom = self._require_king_actor_country()
        self._msg(self._format_country_status(get_kingdom_status(kingdom)))

    def _handle_countrystatus(self):
        kingdom = self._resolve_country_for_read()
        self._msg(self._format_country_status(get_kingdom_status(kingdom)))

    def _handle_countryrename(self):
        if self._has_staff_access():
            country_name = (self.lhs or "").strip()
            new_name = (self.rhs or "").strip()
            if not country_name or not new_name:
                raise ValueError(
                    "countryrename 格式需要 `國名=新國名`；King 可用 `@agentkingdom/countryrename 新國名`。"
                )
            kingdom = self._require_staff_country(country_name)
        else:
            new_name = (self.args or self.rhs or self.lhs or "").strip()
            if not new_name:
                raise ValueError("countryrename 格式需要 `新國名`。")
            kingdom = self._require_king_actor_country()
        try:
            result = rename_kingdom(kingdom, new_name)
        except ValueError as err:
            raise ValueError(str(err)) from err
        self._msg(result["message"])

    def _handle_countryquota(self):
        country_name = (self.lhs or "").strip()
        new_total = (self.rhs or "").strip()
        if not country_name or not new_total:
            raise ValueError("countryquota 格式需要 `國名=新總額度`。")
        kingdom = self._require_staff_country(country_name)
        try:
            result = set_kingdom_quota(kingdom, new_total)
        except ValueError as err:
            raise ValueError(str(err)) from err
        self._msg(result["message"])

    def _handle_countryentrance(self):
        from evennia import search_object

        country_name = (self.lhs or "").strip()
        entrance_name = (self.rhs or "").strip()
        if not country_name or not entrance_name:
            raise ValueError("countryentrance 格式需要 `國名=入口房間`。")
        kingdom = self._require_staff_country(country_name)
        entrance_matches = search_object(entrance_name, exact=True)
        if not entrance_matches:
            raise ValueError(f"找不到入口房間：{entrance_name}")
        result = set_kingdom_entrance(kingdom, entrance_matches[0])
        self._msg(result["message"])

    def _handle_countrydelete(self):
        country_name = (self.args or self.lhs or "").strip()
        if not country_name:
            raise ValueError("countrydelete 格式需要 `國名`。")
        kingdom = self._require_staff_country(country_name)
        try:
            result = delete_kingdom(kingdom)
        except ValueError as err:
            raise ValueError(str(err)) from err
        self._msg(result["message"])

    def _handle_help(self):
        self._msg(
            "|w@agentkingdom|n\n"
            "  |w@agentkingdom/countrycreate|n King名稱=國名,入口房間,額度：建立國家（GM 專用）。\n"
            "  |w@agentkingdom/countries|n：列出國家；King 只會看到自己的國家。\n"
            "  |w@agentkingdom/countrystatus|n [國名]：查看國家狀態；King 只可看自己。\n"
            "  |w@agentkingdom/countryrename|n 國名=新國名：GM 改任一國；King 可直接用 `@agentkingdom/countryrename 新國名` 改自己的國名。\n"
            "  |w@agentkingdom/countryquota|n 國名=新總額度：調整房間總額度（GM 專用）。\n"
            "  |w@agentkingdom/countryentrance|n 國名=入口房間：調整國家入口房（GM 專用）。\n"
            "  |w@agentkingdom/countrydelete|n 國名：刪除國家（GM 專用）。\n\n"
            "註：King 僅開放 /countries、/countrystatus、/countryrename。\n"
            "註：`@kingdom` 保留為 `@agentkingdom` 的相容 alias。"
        )

    def func(self):
        try:
            if "help" in self.switches or not self.switches:
                self._handle_help()
                return

            self._ensure_switch_access()

            if "countrycreate" in self.switches:
                self._handle_countrycreate()
                return
            if "countries" in self.switches:
                self._handle_countries()
                return
            if "countrystatus" in self.switches:
                self._handle_countrystatus()
                return
            if "countryrename" in self.switches:
                self._handle_countryrename()
                return
            if "countryquota" in self.switches:
                self._handle_countryquota()
                return
            if "countryentrance" in self.switches:
                self._handle_countryentrance()
                return
            if "countrydelete" in self.switches:
                self._handle_countrydelete()
                return

            self._msg(f"未知 switch: {self.switches[0]}")
        except ValueError as err:
            self._msg(f"|r{err}|n")
