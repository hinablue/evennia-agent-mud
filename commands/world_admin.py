"""世界管理用的管理員指令。"""

from commands.command import MuxCommand
from world.account_tools import AccountSpecError, set_account_role
from world.agent_world import (WorldSpecError, add_live_exit,
                               add_live_room_detail, add_live_scenery,
                               analyze_agent_world, build_agent_world,
                               create_live_room, force_rebuild_agent_world,
                               is_spec_room, move_live_entity, render_analysis,
                               summarize_agent_world)
from world.kingdom import (create_kingdom, delete_kingdom, get_kingdom_by_name,
                           get_kingdom_status, list_kingdoms, rename_kingdom,
                           resolve_caller_kingdom, set_kingdom_entrance,
                           set_kingdom_quota)


class CmdAgentWorld(MuxCommand):
    """
    管理 Agent 迷航的世界內容。

    使用方式:
      @agentworld
      @agentworld/build
      @agentworld/build 迎賓大廳
      @agentworld/status
      @agentworld/status 迎賓大廳
      @agentworld/check
      @agentworld/dryrun
      @agentworld/forcerebuild
      @agentworld/exits 觀測室
      @agentworld/details 迎賓大廳
      @agentworld/addroom 新房間=這裡的描述
      @agentworld/adddetail 迎賓大廳=窗景,落地窗:遠方的光像海一樣慢慢流動。
      @agentworld/addscenery 迎賓大廳=茶几|桌几,矮桌|深色木紋桌面被擦得很乾淨。
      @agentworld/addexit 迎賓大廳=archive|資料室|file,檔案室
      @agentworld/move rosie=觀測室
      @agentworld/role hinablue=GM

    不帶 switch 時，等同於全域 build。
    Phase 4 的 add/move 類動作只改 live DB，不會自動回寫 world/agent_world.py。
    """

    key = "@agentworld"
    aliases = ["@worldbuild", "@world"]
    locks = "cmd:perm(Admin) or perm(Developer) or perm(King)"
    help_category = "Admin"
    switch_options = (
        "build",
        "status",
        "help",
        "check",
        "dryrun",
        "forcerebuild",
        "rooms",
        "objects",
        "exits",
        "details",
        "npcs",
        "room",
        "addroom",
        "adddetail",
        "addscenery",
        "addexit",
        "move",
        "role",
        "countrycreate",
        "countries",
        "countrystatus",
        "countryrename",
        "countryquota",
        "countryentrance",
        "countrydelete",
    )

    GRANULAR_SWITCHES = {"rooms", "objects", "exits", "details", "npcs"}
    KING_WORLD_ALLOWED_SWITCHES = {"addroom", "adddetail", "addscenery", "addexit"}
    KING_COUNTRY_ALLOWED_SWITCHES = {"countries", "countrystatus", "countryrename"}
    KING_ALLOWED_SWITCHES = KING_WORLD_ALLOWED_SWITCHES | KING_COUNTRY_ALLOWED_SWITCHES
    ACTION_SWITCHES = {
        "status",
        "check",
        "dryrun",
        "room",
        "addroom",
        "adddetail",
        "addscenery",
        "addexit",
        "move",
        "role",
        "countrycreate",
        "countries",
        "countrystatus",
        "countryrename",
        "countryquota",
        "countryentrance",
        "countrydelete",
    }

    def _msg(self, text):
        self.caller.msg(text)

    def _caller_permissions(self):
        """Return the caller account's permission strings."""

        account = getattr(self.caller, "account", None)
        if not account:
            return set()
        return set(account.permissions.all())

    def _has_staff_world_access(self):
        """Check whether caller can use staff-only @agentworld switches."""

        perms = {perm.lower() for perm in (self._caller_permissions() or [])}
        return bool(perms & {"gm", "developer", "admin"})

    def _has_king_world_access(self):
        """Check whether caller can use King-allowed @agentworld switches."""

        return self._has_staff_world_access() or "King" in self._caller_permissions()

    def _ensure_switch_access(self):
        """Validate per-switch access for @agentworld."""

        king_help = (
            "King 只能使用 @agentworld/addroom、/adddetail、/addscenery、/addexit、"
            "/countries、/countrystatus、/countryrename。"
        )
        active_switches = set(self.switches)
        if not active_switches:
            if not self._has_staff_world_access():
                raise WorldSpecError(king_help)
            return

        if active_switches <= self.KING_ALLOWED_SWITCHES:
            if not self._has_king_world_access():
                raise WorldSpecError(
                    "@agentworld/addroom、/adddetail、/addscenery、/addexit、/countries、"
                    "/countrystatus、/countryrename 僅限 King 或 GM/Developer/Admin。"
                )
            return

        if not self._has_staff_world_access():
            raise WorldSpecError(king_help)

    def _room_arg(self):
        return (self.args or self.lhs or "").strip()

    def _selected_components(self):
        components = [
            switch for switch in self.switches if switch in self.GRANULAR_SWITCHES
        ]
        return components or None

    def _resolve_scope_for_report(self):
        room_name = self._room_arg()
        if room_name and not is_spec_room(room_name):
            raise WorldSpecError(
                f"`{room_name}` 不是 builder 規格房間。規格外房間可用 `/status` 看現況，但 `/build`、`/check`、`/dryrun` 只接受 world/agent_world.py 內定義的房間。"
            )
        return room_name or None

    def _render_build_result(self, result):
        scope = result["scope"]
        scope_label = scope[0] if len(scope) == 1 else "全世界"
        components = "、".join(result["components"])
        bootstrap = result.get("bootstrap") or {}
        bootstrap_line = (
            f"- 首位使用者升權：{bootstrap.get('message')}\n"
            if bootstrap.get("promoted")
            else ""
        )
        return (
            "|w世界整理完成。|n\n"
            f"- 範圍：{scope_label}\n"
            f"- 元件：{components}\n"
            f"- 新增房間：{result['rooms_created']}\n"
            f"- 更新房間：{result['rooms_updated']}\n"
            f"- 更新 details：{result['details_updated']}\n"
            f"- 新增物件：{result['objects_created']}\n"
            f"- 更新物件：{result['objects_updated']}\n"
            f"- 新增出口：{result['exits_created']}\n"
            f"- 更新出口：{result['exits_updated']}\n"
            f"- NPC 移動：{result['npcs_moved']}\n"
            f"- NPC 更新：{result['npcs_updated']}\n"
            f"- 玩家描述修正：{result['player_descs_updated']}\n"
            f"{bootstrap_line}\n"
            f"{summarize_agent_world(scope[0] if len(scope) == 1 else None)}"
        )

    def _format_country_status(self, status):
        """Render a compact country status block."""

        return (
            f"|w{status['name']} 國狀態：|n\n"
            f"- 國王：{status['king']}\n"
            f"- 入口房間：{status['entrance_room']}\n"
            f"- 房間額度：{status['used']}/{status['quota']} (剩餘 {status['remaining']})\n"
            f"- 國籍標籤：{status['nationality_tag']}"
        )

    def _require_staff_country(self, name):
        """Resolve a kingdom by name for staff-only country actions."""

        kingdom = get_kingdom_by_name(name)
        if not kingdom:
            raise WorldSpecError(f"找不到國家：{name}")
        return kingdom

    def _require_king_actor_country(self):
        """Resolve the caller's own kingdom for King-scoped country actions."""

        kingdom = resolve_caller_kingdom(self.caller)
        if not kingdom:
            raise WorldSpecError("找不到你的國家資料。")
        return kingdom

    def _resolve_country_for_read(self):
        """Resolve the visible country based on caller role and args."""

        if self._has_staff_world_access():
            name = (self.args or self.lhs or "").strip()
            if not name:
                raise WorldSpecError("countrystatus 格式需要 `國名`。")
            return self._require_staff_country(name)

        kingdom = self._require_king_actor_country()
        requested = (self.args or self.lhs or "").strip()
        if requested and requested != kingdom.key:
            raise WorldSpecError("King 只能查看自己的國家。")
        return kingdom

    def _show_help(self):
        self._msg(
            "|w@agentworld|n\n"
            "  |w@agentworld|n 或 |w@agentworld/build [房間]|n：補齊世界。\n"
            "  |w@agentworld/rooms|n、|w/objects|n、|w/exits|n、|w/details|n、|w/npcs|n：只補指定元件，可加房間名。\n"
            "  |w@agentworld/status [房間]|n：看目前世界或單房間現況。\n"
            "  |w@agentworld/check [房間]|n：列出與 builder 規格的差異。\n"
            "  |w@agentworld/dryrun [房間]|n：預估 build 會補哪些項目。\n"
            "  |w@agentworld/forcerebuild|n：清掉規格世界後，依 world/agent_world.py 與 XYZGrid 重新建一遍。\n"
            "  |w@agentworld/room 房間名|n：等同該房間的 status。\n"
            "  |w@agentworld/addroom 房間名=描述|n：新增 live 房間（King 可用）。\n"
            "  |w@agentworld/adddetail 房間=alias1,alias2:描述|n：新增 live detail（King 可用）。\n"
            "  |w@agentworld/addscenery 房間=物件名|alias1,alias2|描述|n：新增 live 場景物（King 可用）。\n"
            "  |w@agentworld/addexit 來源房間=出口名|目標房間|alias1,alias2|n：新增 live 出口（King 可用）。\n"
            "  |w@agentworld/move 物件或角色=房間|n：移動 live 物件或角色。\n"
            "  |w@agentworld/role 帳號=GM|King|Player|n：指定帳號的三層角色。\n"
            "  |w@agentworld/countrycreate King名稱=國名,入口房間,額度|n：建立國家（GM 專用）。\n"
            "  |w@agentworld/countries|n：列出國家；King 只會看到自己的國家。\n"
            "  |w@agentworld/countrystatus [國名]|n：查看國家狀態；King 只可看自己。\n"
            "  |w@agentworld/countryrename 國名=新國名|n：GM 改任一國；King 可直接用 `@agentworld/countryrename 新國名` 改自己的國名。\n"
            "  |w@agentworld/countryquota 國名=新總額度|n：調整房間總額度（GM 專用）。\n"
            "  |w@agentworld/countryentrance 國名=入口房間|n：調整國家入口房（GM 專用）。\n"
            "  |w@agentworld/countrydelete 國名|n：刪除國家（GM 專用）。\n\n"
            "註：King 僅開放 /addroom、/adddetail、/addscenery、/addexit、/countries、/countrystatus、/countryrename；其餘 switch 仍限 GM/Developer/Admin。\n"
            "註：add/move 系列只修改 live DB，不會自動回寫 world/agent_world.py。"
        )

    def _handle_status(self):
        room_name = self._room_arg()
        self._msg(summarize_agent_world(room_name or None))

    def _handle_checklike(self, mode):
        room_name = self._resolve_scope_for_report()
        analysis = analyze_agent_world(
            room_name=room_name, components=self._selected_components()
        )
        self._msg(render_analysis(analysis, mode=mode))

    def _handle_build(self):
        room_name = self._resolve_scope_for_report()
        result = build_agent_world(
            room_name=room_name, components=self._selected_components()
        )
        self._msg(self._render_build_result(result))

    def _handle_force_rebuild(self):
        result = force_rebuild_agent_world()
        build = result["build"]
        xyzgrid = result["xyzgrid"]
        bootstrap = build.get("bootstrap") or {}
        bootstrap_line = (
            f"- 首位使用者升權：{bootstrap.get('message')}\n"
            if bootstrap.get("promoted")
            else ""
        )
        self._msg(
            "|w世界強制重建完成。|n\n"
            f"- 刪除房間：{result['rooms_deleted']}\n"
            f"- 刪除出口：{result['exits_deleted']}\n"
            f"- 刪除場景物：{result['objects_deleted']}\n"
            f"- 暫存保留物件：{result['objects_preserved']}\n"
            f"- 重建後移回物件：{result['objects_relocated_after_rebuild']}\n"
            f"- 安置房間：{result['fallback_room']}\n"
            f"- Builder 房間總數：{build['rooms_total']}\n"
            f"- Builder 新增房間：{build['rooms_created']}\n"
            f"- Builder 新增出口：{build['exits_created']}\n"
            f"{bootstrap_line}"
            f"- XYZGrid 房間：{xyzgrid['rooms']}\n"
            f"- XYZGrid 出口：{xyzgrid['exits']}\n"
            f"- XYZGrid zcoord：{xyzgrid['zcoord']}\n"
            f"- XYZGrid 已重刷：{xyzgrid['spawned']}"
        )

    def _parse_detail_rhs(self):
        if not self.rhs or ":" not in self.rhs:
            raise WorldSpecError("adddetail 格式需要 `房間=alias1,alias2:描述`。")
        alias_part, desc = self.rhs.split(":", 1)
        aliases = [alias.strip() for alias in alias_part.split(",") if alias.strip()]
        return aliases, desc.strip()

    def _parse_pipe_rhs(self, expected_segments, usage, required_indexes=None):
        parts = [part.strip() for part in (self.rhs or "").split("|")]
        required_indexes = required_indexes or []
        if len(parts) < expected_segments:
            raise WorldSpecError(usage)
        for index in required_indexes:
            if index >= len(parts) or not parts[index]:
                raise WorldSpecError(usage)
        return parts

    def _handle_addroom(self):
        room_name = (self.lhs or self.args or "").strip()
        desc = (self.rhs or "").strip()
        result = create_live_room(room_name, desc=desc)
        self._msg(result["message"])

    def _handle_adddetail(self):
        room_name = (self.lhs or "").strip()
        aliases, desc = self._parse_detail_rhs()
        result = add_live_room_detail(room_name, aliases=aliases, desc=desc)
        self._msg(result["message"])

    def _handle_addscenery(self):
        room_name = (self.lhs or "").strip()
        parts = self._parse_pipe_rhs(
            3,
            "addscenery 格式需要 `房間=物件名|alias1,alias2|描述`。alias 可留空字串，但分隔符仍要保留。",
            required_indexes=[0, 2],
        )
        object_key = parts[0]
        aliases = [alias.strip() for alias in parts[1].split(",") if alias.strip()]
        desc = "|".join(parts[2:]).strip()
        result = add_live_scenery(
            room_name, object_key=object_key, aliases=aliases, desc=desc
        )
        self._msg(result["message"])

    def _handle_addexit(self):
        source_name = (self.lhs or "").strip()
        parts = self._parse_pipe_rhs(
            2, "addexit 格式需要 `來源房間=出口名|目標房間|alias1,alias2`。"
        )
        exit_key = parts[0]
        dest_name = parts[1]
        aliases = [
            alias.strip()
            for alias in (parts[2] if len(parts) > 2 else "").split(",")
            if alias.strip()
        ]
        result = add_live_exit(
            source_name, exit_key=exit_key, dest_name=dest_name, aliases=aliases
        )
        self._msg(result["message"])

    def _handle_move(self):
        entity_key = (self.lhs or "").strip()
        dest_name = (self.rhs or "").strip()
        if not entity_key or not dest_name:
            raise WorldSpecError("move 格式需要 `物件或角色=房間`。")
        result = move_live_entity(entity_key, dest_name=dest_name)
        self._msg(result["message"])

    def _handle_role(self):
        account_name = (self.lhs or "").strip()
        role_name = (self.rhs or "").strip()
        if not account_name or not role_name:
            raise WorldSpecError("role 格式需要 `帳號=GM|King|Player`。")
        try:
            result = set_account_role(account_name, role_name)
        except AccountSpecError as err:
            raise WorldSpecError(str(err)) from err
        self._msg(result["message"])

    def _parse_countrycreate_args(self):
        """Parse staff country-create arguments."""

        if not self.args or "=" not in self.args:
            raise WorldSpecError(
                "countrycreate 格式需要 `King名稱=國名,入口房間,額度`。"
            )
        king_name, rest = self.args.split("=", 1)
        parts = [part.strip() for part in rest.split(",")]
        if len(parts) != 3:
            raise WorldSpecError(
                "countrycreate 格式需要 `King名稱=國名,入口房間,額度`。"
            )
        return king_name.strip(), parts[0], parts[1], parts[2]

    def _handle_countrycreate(self):
        from evennia import search_object

        king_name, country_name, entrance_name, quota = self._parse_countrycreate_args()
        king_matches = search_object(king_name, exact=True)
        if not king_matches:
            raise WorldSpecError(f"找不到 King 角色：{king_name}")
        entrance_matches = search_object(entrance_name, exact=True)
        if not entrance_matches:
            raise WorldSpecError(f"找不到入口房間：{entrance_name}")
        try:
            result = create_kingdom(
                king_matches[0], country_name, entrance_matches[0], int(quota)
            )
        except ValueError as err:
            raise WorldSpecError(str(err)) from err
        self._msg(f"已建立國家：{result.key}")

    def _handle_countries(self):
        if self._has_staff_world_access():
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
        if self._has_staff_world_access():
            country_name = (self.lhs or "").strip()
            new_name = (self.rhs or "").strip()
            if not country_name or not new_name:
                raise WorldSpecError(
                    "countryrename 格式需要 `國名=新國名`；King 可用 `@agentworld/countryrename 新國名`。"
                )
            kingdom = self._require_staff_country(country_name)
        else:
            new_name = (self.args or self.rhs or self.lhs or "").strip()
            if not new_name:
                raise WorldSpecError("countryrename 格式需要 `新國名`。")
            kingdom = self._require_king_actor_country()
        try:
            result = rename_kingdom(kingdom, new_name)
        except ValueError as err:
            raise WorldSpecError(str(err)) from err
        self._msg(result["message"])

    def _handle_countryquota(self):
        country_name = (self.lhs or "").strip()
        new_total = (self.rhs or "").strip()
        if not country_name or not new_total:
            raise WorldSpecError("countryquota 格式需要 `國名=新總額度`。")
        kingdom = self._require_staff_country(country_name)
        try:
            result = set_kingdom_quota(kingdom, new_total)
        except ValueError as err:
            raise WorldSpecError(str(err)) from err
        self._msg(result["message"])

    def _handle_countryentrance(self):
        from evennia import search_object

        country_name = (self.lhs or "").strip()
        entrance_name = (self.rhs or "").strip()
        if not country_name or not entrance_name:
            raise WorldSpecError("countryentrance 格式需要 `國名=入口房間`。")
        kingdom = self._require_staff_country(country_name)
        entrance_matches = search_object(entrance_name, exact=True)
        if not entrance_matches:
            raise WorldSpecError(f"找不到入口房間：{entrance_name}")
        result = set_kingdom_entrance(kingdom, entrance_matches[0])
        self._msg(result["message"])

    def _handle_countrydelete(self):
        country_name = (self.args or self.lhs or "").strip()
        if not country_name:
            raise WorldSpecError("countrydelete 格式需要 `國名`。")
        kingdom = self._require_staff_country(country_name)
        try:
            result = delete_kingdom(kingdom)
        except ValueError as err:
            raise WorldSpecError(str(err)) from err
        self._msg(result["message"])

    def func(self):
        try:
            self._ensure_switch_access()

            if "help" in self.switches:
                self._show_help()
                return

            if "addroom" in self.switches:
                self._handle_addroom()
                return
            if "adddetail" in self.switches:
                self._handle_adddetail()
                return
            if "addscenery" in self.switches:
                self._handle_addscenery()
                return
            if "addexit" in self.switches:
                self._handle_addexit()
                return
            if "move" in self.switches:
                self._handle_move()
                return
            if "role" in self.switches:
                self._handle_role()
                return
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

            if "room" in self.switches:
                self._handle_status()
                return
            if "status" in self.switches:
                self._handle_status()
                return
            if "check" in self.switches:
                self._handle_checklike(mode="check")
                return
            if "dryrun" in self.switches:
                self._handle_checklike(mode="dryrun")
                return
            if "forcerebuild" in self.switches:
                self._handle_force_rebuild()
                return

            self._handle_build()
        except WorldSpecError as err:
            self._msg(f"|r{err}|n")
