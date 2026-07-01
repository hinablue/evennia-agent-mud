"""寶石管理命令。"""

from commands.command import MuxCommand
from world.gem_tools import (
    GemSpecError,
    bootstrap_default_gems,
    create_gem,
    delete_gem,
    parse_bool,
    parse_stats,
    summarize_gem,
    summarize_gems,
    update_gem,
)


class CmdAgentGem(MuxCommand):
    """管理可鑲嵌 Gem 物件。

    使用方式:
      @agentgem/list
      @agentgem/status ruby
      @agentgem/create ruby=紅寶石|str=3,stamina=1|common|描述
      @agentgem/update ruby=name=赤紅寶石,stats=str=5,enabled=on,rarity=rare,desc=描述
      @agentgem/enable ruby=off
      @agentgem/delete ruby
      @agentgem/bootstrap

    Gem 是持久 Object；玩家 socket 會儲存 Gem object reference，
    所以管理者更新 stats 後，已鑲嵌的寶石加成會即時改變。
    """

    key = "@agentgem"
    aliases = ["@gem", "@agentjewel"]
    locks = "cmd:perm(Admin) or perm(Developer)"
    help_category = "Admin"
    switch_options = (
        "list",
        "status",
        "create",
        "update",
        "enable",
        "delete",
        "bootstrap",
        "help",
    )

    def _msg(self, text):
        self.caller.msg(text)

    def _show_help(self):
        self._msg(
            "|w@agentgem|n\n"
            "  |w@agentgem|n 或 |w@agentgem/list|n：列出所有 Gem。\n"
            "  |w@agentgem/status gem_id|n：查看單一 Gem。\n"
            "  |w@agentgem/create id=名稱|stats|rarity|desc|n：建立 Gem。\n"
            "    例：|w@agentgem/create ruby=紅寶石|str=3,stamina=1|common|紅色寶石|n\n"
            "  |w@agentgem/update id=name=名稱,stats=str=5,enabled=on,rarity=rare,desc=描述|n：更新 Gem。\n"
            "  |w@agentgem/enable id=on/off|n：啟用或停用 Gem。\n"
            "  |w@agentgem/delete id|n：刪除 Gem。\n"
            "  |w@agentgem/bootstrap|n：補齊 ruby/sapphire/emerald 預設 Gem。"
        )

    def _handle_list(self):
        self._msg(summarize_gems())

    def _handle_status(self):
        gem_id = (self.args or self.lhs or "").strip()
        self._msg(summarize_gem(gem_id))

    def _handle_create(self):
        gem_id = (self.lhs or "").strip()
        raw = (self.rhs or "").strip()
        if not gem_id or not raw:
            raise GemSpecError("create 格式：`id=名稱|stat=value,...|rarity|desc`")
        params = [part.strip() for part in raw.split("|")]
        name = params[0] if len(params) > 0 else ""
        stats = parse_stats(params[1]) if len(params) > 1 and params[1] else {}
        rarity = params[2] if len(params) > 2 and params[2] else "common"
        desc = params[3] if len(params) > 3 and params[3] else None
        self._msg(create_gem(gem_id, name, stats, rarity=rarity, desc=desc)["message"])

    def _parse_update_pairs(self):
        raw = (self.rhs or "").strip()
        if not self.lhs or not raw:
            raise GemSpecError(
                "update 格式：`id=name=名稱,stats=str=5,enabled=on,rarity=rare,desc=描述`"
            )
        pairs = {}
        current_key = None
        current_value = []
        top_level_keys = {"name", "stats", "enabled", "rarity", "desc"}
        for part in raw.split(","):
            part = part.strip()
            if "=" in part:
                maybe_key, value = [item.strip() for item in part.split("=", 1)]
                if maybe_key in top_level_keys:
                    if current_key is not None:
                        pairs[current_key] = ",".join(current_value).strip()
                    current_key = maybe_key
                    current_value = [value]
                    continue
            if current_key:
                current_value.append(part)
            else:
                raise GemSpecError(f"update 片段缺少 key=value：`{part}`")
        if current_key is not None:
            pairs[current_key] = ",".join(current_value).strip()
        return pairs

    def _handle_update(self):
        gem_id = (self.lhs or "").strip()
        pairs = self._parse_update_pairs()
        allowed = {"name", "stats", "enabled", "rarity", "desc"}
        unknown = sorted(set(pairs) - allowed)
        if unknown:
            raise GemSpecError(f"未知欄位：{', '.join(unknown)}")
        updates = {}
        if "name" in pairs:
            updates["name"] = pairs["name"]
        if "stats" in pairs:
            updates["stats"] = parse_stats(pairs["stats"])
        if "enabled" in pairs:
            updates["enabled"] = parse_bool(pairs["enabled"])
        if "rarity" in pairs:
            updates["rarity"] = pairs["rarity"]
        if "desc" in pairs:
            updates["desc"] = pairs["desc"]
        self._msg(update_gem(gem_id, **updates)["message"])

    def _handle_enable(self):
        gem_id = (self.lhs or "").strip()
        raw = (self.rhs or "").strip()
        if not gem_id or not raw:
            raise GemSpecError("enable 格式：`id=on/off`")
        self._msg(update_gem(gem_id, enabled=parse_bool(raw))["message"])

    def _handle_delete(self):
        gem_id = (self.args or self.lhs or "").strip()
        self._msg(delete_gem(gem_id)["message"])

    def _handle_bootstrap(self):
        created = bootstrap_default_gems()
        if created:
            names = ", ".join(getattr(gem.db, "gem_id", None) or gem.key for gem in created)
            self._msg(f"已補齊預設 Gem：{names}。")
            return
        self._msg("預設 Gem 已存在，沒有新增。")

    def func(self):
        """執行管理命令。"""
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
            if "update" in self.switches:
                self._handle_update()
                return
            if "enable" in self.switches:
                self._handle_enable()
                return
            if "delete" in self.switches:
                self._handle_delete()
                return
            if "bootstrap" in self.switches:
                self._handle_bootstrap()
                return
            self._handle_list()
        except GemSpecError as err:
            self._msg(f"|r{err}|n")
