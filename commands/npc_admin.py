"""NPC / LLMNPC management command."""

from commands.command import MuxCommand
from world.npc_tools import (
    NPCSpecError,
    create_npc,
    delete_npc,
    get_llm_config,
    move_npc,
    set_llm_config,
    set_llm_prompt,
    set_llm_thinking,
    set_npc_aliases,
    set_npc_combat_flags,
    set_npc_desc,
    set_npc_level,
    set_npc_cooldown,
    set_npc_tokens,
    set_npc_flee,
    set_npc_aggro,
    set_npc_skills,
    set_npc_stats,
    summarize_npc,
    summarize_npcs,
)


class CmdAgentNPC(MuxCommand):
    """
    管理 NPC 與 LLMNPC。

    使用方式:
      @agentnpc
      @agentnpc/list
      @agentnpc/list 迎賓大廳
      @agentnpc/status rosie
      @agentnpc/create npc 守門員=迎賓大廳|站在門邊觀察來客。|守衛,門衛
      @agentnpc/create llm 檔案員=觀測室|她說話很輕，像怕打擾到房間裡的灰塵。|書記,管理員|你現在正在扮演檔案員...
      @agentnpc/move 檔案員=控制中樞
      @agentnpc/desc 檔案員=新的描述
      @agentnpc/aliases 檔案員=書記,管理員,檔案官
      @agentnpc/flags 守門員=attackable:on,retaliates:off,can_die:on
      @agentnpc/stats 守門員=str=18,def=12,hp=120,mp=20,spd=14
      @agentnpc/skills 守門員=heavy_strike,stun_bash
      @agentnpc/llm 檔案員?base_url=https://api.example.com&model=gpt-4&api_key=sk-xxx
      @agentnpc/prompt 檔案員=新的 prompt prefix
      @agentnpc/thinking 檔案員=2.5|她安靜地想了一下。|她把你的問題在心裡翻了一遍。
      @agentnpc/delete 檔案員
      @agentnpc/level 守門員=5
      @agentnpc/cooldown 守門員=120
      @agentnpc/tokens 守門員=5,20
      @agentnpc/flee 守門員=on,0.3
      @agentnpc/aggro 守門員=0.15

    不帶 switch 時，等同於 list。
    這顆工具是 live 世界管理工具，不會自動回寫任何 world spec。
    """

    key = "@agentnpc"
    aliases = ["@npcworld", "@npc"]
    locks = "cmd:perm(Admin) or perm(Developer)"
    help_category = "Admin"
    switch_options = ("list", "status", "create", "move", "desc", "aliases", "flags", "stats", "skills", "llm", "prompt", "thinking", "delete", "level", "cooldown", "tokens", "flee", "aggro", "help")

    def _msg(self, text):
        self.caller.msg(text)

    def _parse_pipe_segments(self, expected_min, usage):
        parts = [part.strip() for part in (self.rhs or "").split("|")]
        if len(parts) < expected_min:
            raise NPCSpecError(usage)
        return parts

    def _show_help(self):
        self._msg(
            "|w@agentnpc|n\n"
            "  |w@agentnpc|n 或 |w@agentnpc/list [房間]|n：列出所有受管理 NPC。\n"
            "  |w@agentnpc/status 名稱|n：看單一 NPC 狀態。\n"
            "  |w@agentnpc/create npc 名稱=房間|描述|alias1,alias2|n：建立一般 NPC。\n"
            "  |w@agentnpc/create llm 名稱=房間|描述|alias1,alias2|prompt|n：建立 LLMNPC。\n"
            "  |w@agentnpc/move 名稱=房間|n：移動 NPC。\n"
            "  |w@agentnpc/desc 名稱=描述|n：更新描述。\n"
            "  |w@agentnpc/aliases 名稱=alias1,alias2|n：覆寫 aliases。\n"
            "  |w@agentnpc/flags 名稱=attackable:on,retaliates:off,can_die:on|n：設定戰鬥旗標。\n"
            "  |w@agentnpc/stats 名稱=str=18,def=12,hp=120,mp=20,spd=14|n：設定戰鬥數值。\n"
            "  |w@agentnpc/skills 名稱=heavy_strike,stun_bash|n：覆寫 NPC 技能清單。\n"
            "  |w@agentnpc/llm 名稱?base_url=...&model=...&api_key=...|n：設定 LLM 參數。\n"
            "  |w@agentnpc/prompt 名稱=prompt prefix|n：更新 LLMNPC prompt。\n"
            "  |w@agentnpc/thinking 名稱=秒數|訊息1|訊息2...|n：更新 LLMNPC thinking 設定。\n"
            "  |w@agentnpc/level 名稱=等級|n：設定 NPC 等級（影響屬性倍率）。\n"
            "  |w@agentnpc/cooldown 名稱=秒數|n：設定死亡/逃跑後重生冷卻時間。\n"
            "  |w@agentnpc/tokens 名稱=最小,最大|n：設定 Token 掉落範圍。\n"
            "  |w@agentnpc/flee 名稱=開關,fail_chance|n：設定逃跑功能與基礎失敗率。\n"
            "  |w@agentnpc/aggro 名稱=機率|n：設定被 look 時主動攻擊的機率（0~1）。\n"
            "  |w@agentnpc/delete 名稱|n：刪除 NPC。\n\n"
            "註：這顆工具直接修改 live DB；如果要長期保留設定，請再把內容整理進 world spec 或其他持久化流程。"
        )

    def _handle_list(self):
        room_name = (self.args or self.lhs or "").strip()
        self._msg(summarize_npcs(room_name or None))

    def _handle_status(self):
        npc_key = (self.args or self.lhs or "").strip()
        self._msg(summarize_npc(npc_key))

    def _handle_create(self):
        usage = "create 格式需要 `型別 名稱=房間|描述|alias1,alias2`；LLMNPC 可再追加 `|prompt`。"
        raw = (self.args or "").strip()
        if not raw or " " not in raw or "=" not in raw:
            raise NPCSpecError(usage)
        kind, remainder = raw.split(None, 1)
        kind = kind.lower().strip()
        npc_key, rhs = [part.strip() for part in remainder.split("=", 1)]
        if not npc_key:
            raise NPCSpecError(usage)
        parts = [part.strip() for part in rhs.split("|")]
        if len(parts) < 3:
            raise NPCSpecError(usage)
        room_name, desc, alias_part = parts[:3]
        aliases = [alias.strip() for alias in alias_part.split(",") if alias.strip()]
        prompt_prefix = "|".join(parts[3:]).strip() if len(parts) > 3 else None
        result = create_npc(kind, npc_key, room_name=room_name, desc=desc, aliases=aliases, prompt_prefix=prompt_prefix)
        self._msg(result["message"])

    def _handle_move(self):
        npc_key = (self.lhs or "").strip()
        room_name = (self.rhs or "").strip()
        if not npc_key or not room_name:
            raise NPCSpecError("move 格式需要 `名稱=房間`。")
        result = move_npc(npc_key, room_name)
        self._msg(result["message"])

    def _handle_desc(self):
        npc_key = (self.lhs or "").strip()
        desc = (self.rhs or "").strip()
        if not npc_key or not desc:
            raise NPCSpecError("desc 格式需要 `名稱=描述`。")
        result = set_npc_desc(npc_key, desc)
        self._msg(result["message"])

    def _handle_aliases(self):
        npc_key = (self.lhs or "").strip()
        aliases = [alias.strip() for alias in (self.rhs or "").split(",") if alias.strip()]
        if not npc_key or not aliases:
            raise NPCSpecError("aliases 格式需要 `名稱=alias1,alias2`。")
        result = set_npc_aliases(npc_key, aliases)
        self._msg(result["message"])

    def _parse_boolish_map(self, raw):
        result = {}
        for chunk in (raw or "").split(","):
            chunk = chunk.strip()
            if not chunk:
                continue
            if ":" not in chunk:
                raise NPCSpecError("flags 格式需要 `attackable:on,retaliates:off,can_die:on`。")
            key, value = [part.strip().lower() for part in chunk.split(":", 1)]
            if value not in {"on", "off", "true", "false", "1", "0"}:
                raise NPCSpecError(f"不支援的布林值：{value}")
            result[key] = value in {"on", "true", "1"}
        return result

    def _handle_flags(self):
        npc_key = (self.lhs or "").strip()
        flag_map = self._parse_boolish_map(self.rhs)
        if not npc_key or not flag_map:
            raise NPCSpecError("flags 格式需要 `名稱=attackable:on,retaliates:off,can_die:on`。")
        result = set_npc_combat_flags(
            npc_key,
            attackable=flag_map.get("attackable"),
            retaliates=flag_map.get("retaliates"),
            can_die=flag_map.get("can_die"),
        )
        self._msg(result["message"])

    def _handle_stats(self):
        npc_key = (self.lhs or "").strip()
        updates = {}
        for chunk in (self.rhs or "").split(","):
            chunk = chunk.strip()
            if not chunk:
                continue
            if "=" not in chunk:
                raise NPCSpecError("stats 格式需要 `名稱=str=18,def=12,hp=120`。")
            stat_key, raw_value = [part.strip().lower() for part in chunk.split("=", 1)]
            updates[stat_key] = raw_value
        if not npc_key or not updates:
            raise NPCSpecError("stats 格式需要 `名稱=str=18,def=12,hp=120`。")
        result = set_npc_stats(npc_key, updates)
        self._msg(result["message"])

    def _handle_llm(self):
        raw = (self.args or "").strip()
        if not raw:
            self._msg("llm 格式：@agentnpc/llm 名稱?base_url=...&model=...&api_key=...")
            self._msg("範例：@agentnpc/llm 檔案員?base_url=https://api.openai.com/v1,model=gpt-4,api_key=sk-xxx")
            self._msg("所有參數可單獨設定，無需全部給定。")
            return
        if "?" in raw:
            name_part, params_part = raw.split("?", 1)
            npc_key = name_part.strip()
            base_url = None
            model = None
            api_key = None
            for param in params_part.split("&"):
                if "=" in param:
                    k, v = param.split("=", 1)
                    k = k.strip().lower()
                    v = v.strip()
                    if k == "base_url":
                        base_url = v
                    elif k == "model":
                        model = v
                    elif k == "api_key":
                        api_key = v
            if not npc_key:
                raise NPCSpecError("llm 需要提供 NPC 名稱。")
            result = set_llm_config(npc_key, base_url=base_url, model=model, api_key=api_key)
            self._msg(result["message"])
        else:
            npc_key = raw.strip()
            if not npc_key:
                raise NPCSpecError("llm 需要提供 NPC 名稱。")
            result = get_llm_config(npc_key)
            self._msg(result)

    def _handle_skills(self):
        npc_key = (self.lhs or "").strip()
        skills = [item.strip() for item in (self.rhs or "").split(",") if item.strip()]
        if not npc_key:
            raise NPCSpecError("skills 格式需要 `名稱=heavy_strike,stun_bash`。")
        result = set_npc_skills(npc_key, skills)
        self._msg(result["message"])

    def _handle_prompt(self):
        npc_key = (self.lhs or "").strip()
        prompt_prefix = (self.rhs or "").strip()
        if not npc_key or not prompt_prefix:
            raise NPCSpecError("prompt 格式需要 `名稱=prompt prefix`。")
        result = set_llm_prompt(npc_key, prompt_prefix)
        self._msg(result["message"])

    def _handle_thinking(self):
        npc_key = (self.lhs or "").strip()
        parts = self._parse_pipe_segments(1, "thinking 格式需要 `名稱=秒數|訊息1|訊息2...`。")
        if not npc_key:
            raise NPCSpecError("thinking 格式需要 `名稱=秒數|訊息1|訊息2...`。")
        timeout = parts[0]
        messages = parts[1:]
        result = set_llm_thinking(npc_key, timeout, messages=messages)
        self._msg(result["message"])

    def _handle_level(self):
        npc_key = (self.lhs or "").strip()
        level_str = (self.rhs or "").strip()
        if not npc_key or not level_str:
            raise NPCSpecError("level 格式需要 `名稱=等級`。")
        result = set_npc_level(npc_key, level_str)
        self._msg(result["message"])

    def _handle_cooldown(self):
        npc_key = (self.lhs or "").strip()
        cooldown_str = (self.rhs or "").strip()
        if not npc_key or not cooldown_str:
            raise NPCSpecError("cooldown 格式需要 `名稱=秒數`。")
        result = set_npc_cooldown(npc_key, cooldown_str)
        self._msg(result["message"])

    def _handle_tokens(self):
        npc_key = (self.lhs or "").strip()
        tokens_str = (self.rhs or "").strip()
        if not npc_key or not tokens_str:
            raise NPCSpecError("tokens 格式需要 `名稱=最小,最大`。")
        parts = tokens_str.split(",")
        if len(parts) != 2:
            raise NPCSpecError("tokens 格式需要 `名稱=最小,最大`，例如 `守門員=3,15`。")
        result = set_npc_tokens(npc_key, parts[0].strip(), parts[1].strip())
        self._msg(result["message"])

    def _handle_flee(self):
        npc_key = (self.lhs or "").strip()
        flee_str = (self.rhs or "").strip()
        if not npc_key or not flee_str:
            raise NPCSpecError("flee 格式需要 `名稱=開關,fail_chance`，例如 `守門員=on,0.3`。")
        parts = flee_str.split(",")
        enable = parts[0].strip().lower()
        fail_chance = float(parts[1].strip()) if len(parts) > 1 else None
        result = set_npc_flee(npc_key, enable, fail_chance)
        self._msg(result["message"])

    def _handle_aggro(self):
        npc_key = (self.lhs or "").strip()
        chance_str = (self.rhs or "").strip()
        if not npc_key or not chance_str:
            raise NPCSpecError("aggro 格式需要 `名稱=機率`，機率範圍 0~1，例如 `0.15`。")
        result = set_npc_aggro(npc_key, chance_str)
        self._msg(result["message"])

    def _handle_delete(self):
        npc_key = (self.args or self.lhs or "").strip()
        result = delete_npc(npc_key)
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
            if "desc" in self.switches:
                self._handle_desc()
                return
            if "aliases" in self.switches:
                self._handle_aliases()
                return
            if "flags" in self.switches:
                self._handle_flags()
                return
            if "stats" in self.switches:
                self._handle_stats()
                return
            if "skills" in self.switches:
                self._handle_skills()
                return
            if "llm" in self.switches:
                self._handle_llm()
                return
            if "prompt" in self.switches:
                self._handle_prompt()
                return
            if "thinking" in self.switches:
                self._handle_thinking()
                return
            if "level" in self.switches:
                self._handle_level()
                return
            if "cooldown" in self.switches:
                self._handle_cooldown()
                return
            if "tokens" in self.switches:
                self._handle_tokens()
                return
            if "flee" in self.switches:
                self._handle_flee()
                return
            if "aggro" in self.switches:
                self._handle_aggro()
                return
            if "delete" in self.switches:
                self._handle_delete()
                return
            self._handle_list()
        except NPCSpecError as err:
            self._msg(f"|r{err}|n")