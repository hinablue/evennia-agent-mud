"""法術（Magic）管理指令。"""

from commands.command import MuxCommand
from world.magic_tools import (
    MagicSpecError,
    create_spell,
    delete_spell,
    get_spell,
    list_spells,
    update_spell,
)


class CmdAgentMagic(MuxCommand):
    """
    管理法術（Spell / Magic）。

    使用方式:
      @agentmagic
      @agentmagic/list
      @agentmagic/create 火球術|火球術|fireball,火焰|fire|20|8|25|fire|冰刺術|ice_shard,冰|ice|18|6|22|ice
        （格式：key|name|aliases|type|mp|dmg_min|dmg_max|magic_type）
      @agentmagic/get 火球術
      @agentmagic/update 火球術|mp_cost=25,dmg_min=10,dmg_max=30
      @agentmagic/delete 火球術

    不帶 switch 時，等同於 list。
    這顆工具是 live 世界管理工具，不會自動回寫任何 world spec 或持久化流程。
    """

    key = "@agentmagic"
    aliases = ["@spellworld", "@spell", "@magicworld", "@magic"]
    locks = "cmd:perm(Admin) or perm(Developer)"
    help_category = "Admin"
    switch_options = ("list", "create", "get", "update", "delete", "help")

    def _msg(self, text):
        self.caller.msg(text)

    def _show_help(self):
        self._msg(
            "|w@agentmagic|n\n"
            "  |w@agentmagic|n 或 |w@agentmagic/list|n：列出所有法術。\n"
            "  |w@agentmagic/create key|name|aliases|type|mp|dmg_min|dmg_max|magic_type|...\n"
            "    建立法術。所有欄位均可選，只提供 key 與 name 即可建立最簡法術。\n"
            "    完整欄位：key|name|aliases|type|mp|dmg_min|dmg_max|magic_type|buff_stat|buff_min|buff_max|debuff_stat|debuff_min|debuff_max|buff_duration|is_heal|heal_min|heal_max|chance|status_effect|spell_level\n"
            "  |w@agentmagic/get 法術ID|n：查看法術詳細資訊。\n"
            "  |w@agentmagic/update 法術ID|欄位1=值1,欄位2=值2,...|n：更新法術屬性。\n"
            "  |w@agentmagic/delete 法術ID|n：刪除法術。\n\n"
            "可用欄位（update/create）：\n"
            "  name, aliases, desc, mp_cost, magic_type,\n"
            "  dmg_min, dmg_max, buff_stat, buff_min, buff_max,\n"
            "  debuff_stat, debuff_min, debuff_max, buff_duration,\n"
            "  is_heal, heal_min, heal_max, chance, status_effect, spell_level\n\n"
            "magic_type 參考值：physical / fire / ice / lightning / heal / buff / debuff\n"
            "is_heal=1 表示此法術為治療法術（可對自己施放）。\n"
            "chance 為 0~1 的小數，代表命中率。\n"
            "buff_duration 為 0 表示無buff效果，>0 表示持續回合數。\n\n"
            "範例：\n"
            "  @agentmagic/create heal_1|初級治療術|heal1,治療|heal|5|0|0|heal|||||||3|1|10|30|0.95||1\n"
            "  @agentmagic/create power_blade|力量祝福|power_blade,賦武||0|0|0|buff|str|5|10|||5||0|0|0|0.9||1\n"
            "  @agentmagic/update 火球術|mp_cost=30,dmg_min=15,dmg_max=40"
        )

    def _handle_list(self):
        self._msg(list_spells())

    def _handle_create(self):
        usage = (
            "create 格式需要 `key|name|aliases|type|mp|dmg_min|dmg_max|magic_type`，"
            "最少需要 `key|name`。"
        )
        raw = (self.args or "").strip()
        if not raw:
            raise MagicSpecError(usage)
        parts = [p.strip() for p in raw.split("|")]
        if len(parts) < 2:
            raise MagicSpecError(usage)

        spell_key = parts[0]
        name = parts[1] if len(parts) > 1 else spell_key
        aliases = (
            [a.strip() for a in parts[2].split(",")]
            if len(parts) > 2 and parts[2]
            else []
        )
        spell_type = parts[3] if len(parts) > 3 else "physical"
        mp = int(parts[4]) if len(parts) > 4 and parts[4] else 10
        dmg_min = int(parts[5]) if len(parts) > 5 and parts[5] else 0
        dmg_max = int(parts[6]) if len(parts) > 6 and parts[6] else 0
        magic_type = parts[7] if len(parts) > 7 and parts[7] else spell_type

        result = create_spell(
            spell_key,
            name=name,
            aliases=aliases,
            mp_cost=mp,
            magic_type=magic_type,
            dmg_min=dmg_min,
            dmg_max=dmg_max,
        )
        self._msg(result["message"])

    def _handle_get(self):
        spell_key = (self.args or "").strip()
        if not spell_key:
            raise MagicSpecError("get 格式需要 `法術ID`。")
        self._msg(get_spell(spell_key))

    def _handle_update(self):
        usage = "update 格式需要 `法術ID|欄位1=值1,欄位2=值2,...`。"
        raw = (self.args or "").strip()
        if not raw or "|" not in raw:
            raise MagicSpecError(usage)
        spell_key, field_part = raw.split("|", 1)
        spell_key = spell_key.strip()
        if not spell_key:
            raise MagicSpecError(usage)
        fields = {}
        for chunk in field_part.split(","):
            chunk = chunk.strip()
            if not chunk or "=" not in chunk:
                continue
            k, v = chunk.split("=", 1)
            k = k.strip()
            v = v.strip()
            # 嘗試自動轉換類型
            if v.lower() in ("true", "false", "1", "0"):
                v = v.lower() in ("true", "1")
            elif v.isdigit():
                v = int(v)
            else:
                try:
                    v = float(v)
                except ValueError:
                    pass
            fields[k] = v
        if not fields:
            raise MagicSpecError(usage)
        result = update_spell(spell_key, **fields)
        self._msg(result["message"])

    def _handle_delete(self):
        spell_key = (self.args or self.lhs or "").strip()
        if not spell_key:
            raise MagicSpecError("delete 格式需要 `法術ID`。")
        result = delete_spell(spell_key)
        self._msg(result["message"])

    def func(self):
        try:
            if "help" in self.switches:
                self._show_help()
                return
            if "list" in self.switches:
                self._handle_list()
                return
            if "create" in self.switches:
                self._handle_create()
                return
            if "get" in self.switches:
                self._handle_get()
                return
            if "update" in self.switches:
                self._handle_update()
                return
            if "delete" in self.switches:
                self._handle_delete()
                return
            self._handle_list()
        except MagicSpecError as err:
            self._msg(f"|r{err}|n")
