"""裝備/武器管理命令。"""

from commands.command import MuxCommand
from world.equipment_tools import (
    EquipmentSpecError,
    add_equipment_magic_buff,
    add_equipment_stat,
    clone_equipment,
    create_equipment,
    delete_equipment,
    move_equipment,
    repair_equipment,
    set_equipment_alias,
    set_equipment_desc,
    set_equipment_durability,
    set_equipment_stats,
    summarize_equipment,
    summarize_equipments,
)
from world.shop_tools import (
    ShopSpecError,
    remove_room_shop_stock,
    set_room_shop_stock,
    summarize_room_shop,
)


class CmdAgentWeapon(MuxCommand):
    """
    管理武器與裝備（Equipment）。

    使用方式:
      @agentweapon
      @agentweapon/list
      @agentweapon/list 迎賓大廳
      @agentweapon/status 鐵劍
      @agentweapon/create main_hand 鐵劍=迎賓大廳|一把普通的鐵劍。|劍,武器
      @agentweapon/create two_hand 巨斧=迎賓大廳|沈重的雙手巨斧。||atk=15,str=5|two_hand
      @agentweapon/create hat 皮帽=迎賓大廳|簡單的皮製帽子。|帽子|def=1,agi=1
      @agentweapon/move 鐵劍=控制中樞
      @agentweapon/stats 鐵劍=atk=5,def=2
      @agentweapon/addstat 鐵劍=atk=3
      @agentweapon/buff 鐵劍=atk=2
      @agentweapon/alias 鐵劍=我的劍
      @agentweapon/desc 鐵劍=這是一把鋒利的長劍。
      @agentweapon/dur 鐵劍=50/100
      @agentweapon/repair 鐵劍
      @agentweapon/repair 鐵劍=20
      @agentweapon/clone 鐵劍=商店鐵劍樣板|迎賓大廳
      @agentweapon/shop 迎賓大廳
      @agentweapon/stock 鐵劍=迎賓大廳|30|5
      @agentweapon/unstock 鐵劍=迎賓大廳
      @agentweapon/delete 鐵劍

    不帶 switch 時，等同於 list。
    這顆工具是 live 世界管理工具，不會自動回寫任何 world spec。

    slot 可用值：
      hat / top / bottom / cloak / shoes / gloves / glasses / earring / ring
      main_hand / off_hand / two_hand
    """

    key = "@agentweapon"
    aliases = ["@agentequip", "@equip", "@weapon"]
    locks = "cmd:perm(Admin) or perm(Developer)"
    help_category = "Admin"
    switch_options = (
        "list",
        "status",
        "create",
        "move",
        "stats",
        "addstat",
        "buff",
        "alias",
        "desc",
        "dur",
        "repair",
        "clone",
        "shop",
        "stock",
        "unstock",
        "delete",
        "help",
    )

    def _msg(self, text):
        self.caller.msg(text)

    def _show_help(self):
        self._msg(
            "|w@agentweapon|n\n"
            "  |w@agentweapon|n 或 |w@agentweapon/list [房間]|n：列出所有武器/裝備。\n"
            "  |w@agentweapon/status 名稱|n：看單一裝備狀態。\n"
            "  |w@agentweapon/create slot 名稱=房間|描述|alias1,alias2|stat_dict|two_hand|n：建立裝備。\n"
            "  |w@agentweapon/move 名稱=房間|n：移動裝備。\n"
            "  |w@agentweapon/stats 名稱=atk=5,def=-2|n：設定屬性（覆寫）。\n"
            "  |w@agentweapon/addstat 名稱=atk=3|n：增加/減少屬性。\n"
            "  |w@agentweapon/buff 名稱=atk=2|n：附加魔法增益。\n"
            "  |w@agentweapon/alias 名稱=暱稱|n：設定 Player 暱稱。\n"
            "  |w@agentweapon/desc 名稱=描述|n：更新描述。\n"
            "  |w@agentweapon/dur 名稱=50/100|n：設定耐用度（當前/上限）。\n"
            "  |w@agentweapon/repair 名稱[=amount]|n：修復（可指定數值）。\n"
            "  |w@agentweapon/clone 名稱=新名稱|房間|n：複製一件新裝備樣板。\n"
            "  |w@agentweapon/shop [房間]|n：查看房間商店清單。\n"
            "  |w@agentweapon/stock 名稱=房間|價格|數量|n：把裝備樣板上架到房間商店。\n"
            "  |w@agentweapon/unstock 名稱=房間|n：把裝備樣板從房間商店下架。\n"
            "  |w@agentweapon/delete 名稱|n：刪除裝備。\n\n"
            "slot 可用值：hat, top, bottom, cloak, shoes, gloves, glasses,\n"
            "             earring, ring, main_hand, off_hand, two_hand\n\n"
            "stat 屬性名：hp, mp, str, def, intel, agi, spirit, stamina, spd, atk"
        )

    def _parse_key_value(self, expected_keys=None):
        """從 rhs 解析 key=value 對。"""
        pairs = {}
        if not self.rhs:
            return pairs
        for part in self.rhs.split(","):
            part = part.strip()
            if "=" in part:
                key, val = part.split("=", 1)
                pairs[key.strip()] = val.strip()
            elif expected_keys:
                for k in expected_keys:
                    if k not in pairs:
                        pairs[k] = part
                        break
        return pairs

    def _handle_list(self):
        room_name = (self.args or self.lhs or "").strip()
        self._msg(summarize_equipments(room_name or None))

    def _handle_status(self):
        eq_key = (self.args or self.lhs or "").strip()
        self._msg(summarize_equipment(eq_key))

    def _handle_create(self):
        usage = (
            "create 格式：`slot 名稱=房間|描述|alias1,alias2|stat_key=val,...|two_hand`\n"
            "  slot：hat, top, bottom, cloak, shoes, gloves, glasses, earring, ring,\n"
            "        main_hand, off_hand, two_hand\n"
            "  stat_key=val：atk=5, def=-2, str=3 ...\n"
            "  最後一個參數 two_hand 表示雙手武器（只用於 main_hand/off_hand slot）"
        )
        raw = (self.args or "").strip()
        if not raw or " " not in raw or "=" not in raw:
            raise EquipmentSpecError(usage)

        # 解析：slot key=room|desc|aliases|stats|two_hand
        parts = raw.split(None, 1)
        if len(parts) < 2:
            raise EquipmentSpecError(usage)
        slot = parts[0].strip().lower()
        remainder = parts[1]

        eq_key, rhs = [s.strip() for s in remainder.split("=", 1)]
        if not eq_key:
            raise EquipmentSpecError(usage)

        params = [p.strip() for p in rhs.split("|")]
        room_name = params[0] if len(params) > 0 and params[0] else None
        desc = params[1] if len(params) > 1 and params[1] else None
        alias_str = params[2] if len(params) > 2 and params[2] else None
        aliases = (
            [a.strip() for a in alias_str.split(",") if a.strip()]
            if alias_str
            else None
        )
        stats_str = params[3] if len(params) > 3 and params[3] else None
        stats = {}
        if stats_str:
            for pair in stats_str.split(","):
                pair = pair.strip()
                if "=" in pair:
                    k, v = pair.split("=", 1)
                    try:
                        stats[k.strip()] = int(v.strip())
                    except ValueError:
                        raise EquipmentSpecError(f"stat 值必須是整數：`{pair}`")
        two_hand = len(params) > 4 and params[4].strip().lower() == "two_hand"

        result = create_equipment(
            eq_key,
            slot=slot,
            room_name=room_name,
            desc=desc,
            aliases=aliases,
            stats=stats,
            two_handed=two_hand,
        )
        self._msg(result["message"])

    def _handle_move(self):
        eq_key = (self.lhs or "").strip()
        room_name = (self.rhs or "").strip()
        if not eq_key or not room_name:
            raise EquipmentSpecError("move 格式：`名稱=房間`")
        result = move_equipment(eq_key, room_name)
        self._msg(result["message"])

    def _handle_stats(self):
        eq_key = (self.lhs or "").strip()
        stats_raw = (self.rhs or "").strip()
        if not eq_key or not stats_raw:
            raise EquipmentSpecError("stats 格式：`名稱=atk=5,def=-2,...`")
        stats = {}
        for pair in stats_raw.split(","):
            pair = pair.strip()
            if "=" not in pair:
                raise EquipmentSpecError(f"stat 格式錯誤：`{pair}`")
            k, v = pair.split("=", 1)
            try:
                stats[k.strip()] = int(v.strip())
            except ValueError:
                raise EquipmentSpecError(f"stat 值必須是整數：`{pair}`")
        result = set_equipment_stats(eq_key, stats)
        self._msg(result["message"])

    def _handle_addstat(self):
        eq_key = (self.lhs or "").strip()
        raw = (self.rhs or "").strip()
        if not eq_key or not raw or "=" not in raw:
            raise EquipmentSpecError("addstat 格式：`名稱=stat=value`")
        k, v = raw.split("=", 1)
        try:
            val = int(v.strip())
        except ValueError:
            raise EquipmentSpecError(f"stat 值必須是整數：`{v}`")
        result = add_equipment_stat(eq_key, k.strip(), val)
        self._msg(result["message"])

    def _handle_buff(self):
        eq_key = (self.lhs or "").strip()
        raw = (self.rhs or "").strip()
        if not eq_key or not raw or "=" not in raw:
            raise EquipmentSpecError("buff 格式：`名稱=stat=value`")
        k, v = raw.split("=", 1)
        try:
            val = int(v.strip())
        except ValueError:
            raise EquipmentSpecError(f"buff 值必須是整數：`{v}`")
        result = add_equipment_magic_buff(eq_key, k.strip(), val)
        self._msg(result["message"])

    def _handle_alias(self):
        eq_key = (self.lhs or "").strip()
        alias = (self.rhs or "").strip()
        if not eq_key:
            raise EquipmentSpecError("alias 格式：`名稱=暱稱`")
        result = set_equipment_alias(eq_key, alias)
        self._msg(result["message"])

    def _handle_desc(self):
        eq_key = (self.lhs or "").strip()
        desc = (self.rhs or "").strip()
        if not eq_key or not desc:
            raise EquipmentSpecError("desc 格式：`名稱=描述`")
        result = set_equipment_desc(eq_key, desc)
        self._msg(result["message"])

    def _handle_dur(self):
        eq_key = (self.lhs or "").strip()
        raw = (self.rhs or "").strip()
        if not eq_key or not raw:
            raise EquipmentSpecError("dur 格式：`名稱=current/max` 或 `名稱=current`")
        parts = raw.split("/", 1)
        try:
            durability = int(parts[0].strip())
            max_dur = int(parts[1].strip()) if len(parts) > 1 else None
        except ValueError:
            raise EquipmentSpecError("dur 數值必須是整數。")
        result = set_equipment_durability(eq_key, durability, max_dur)
        self._msg(result["message"])

    def _handle_repair(self):
        eq_key = (self.lhs or "").strip()
        raw = (self.args or "").replace(self.lhs or "", "", 1).strip()
        if not eq_key:
            raise EquipmentSpecError("repair 格式：`名稱` 或 `名稱=amount`")
        amount = None
        if raw:
            try:
                amount = int(raw)
            except ValueError:
                raise EquipmentSpecError(f"repair amount 必須是整數：`{raw}`")
        result = repair_equipment(eq_key, amount)
        self._msg(result["message"])

    def _handle_clone(self):
        template_key = (self.lhs or "").strip()
        raw = (self.rhs or "").strip()
        if not template_key or not raw:
            raise EquipmentSpecError("clone 格式：`名稱=新名稱|房間`")
        params = [part.strip() for part in raw.split("|")]
        new_key = params[0] if params else ""
        room_name = params[1] if len(params) > 1 and params[1] else None
        if not new_key:
            raise EquipmentSpecError("clone 需要新的裝備名稱。")
        result = clone_equipment(
            template_key,
            new_key=new_key,
            room_name=room_name,
            allow_duplicate_key=False,
        )
        self._msg(result["message"])

    def _handle_shop(self):
        room_name = (self.args or self.lhs or "").strip()
        self._msg(summarize_room_shop(room_name or None, room=self.caller.location if not room_name else None))

    def _handle_stock(self):
        template_key = (self.lhs or "").strip()
        raw = (self.rhs or "").strip()
        if not template_key or not raw:
            raise ShopSpecError("stock 格式：`名稱=房間|價格|數量`（數量 -1 代表無限）")
        params = [part.strip() for part in raw.split("|")]
        if len(params) < 3:
            raise ShopSpecError("stock 格式：`名稱=房間|價格|數量`（數量 -1 代表無限）")
        room_name, price, quantity = params[0], params[1], params[2]
        result = set_room_shop_stock(template_key, room_name, price, quantity)
        self._msg(result["message"])

    def _handle_unstock(self):
        template_key = (self.lhs or "").strip()
        room_name = (self.rhs or "").strip()
        if not template_key or not room_name:
            raise ShopSpecError("unstock 格式：`名稱=房間`")
        result = remove_room_shop_stock(template_key, room_name)
        self._msg(result["message"])

    def _handle_delete(self):
        eq_key = (self.args or self.lhs or "").strip()
        result = delete_equipment(eq_key)
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
            if "stats" in self.switches:
                self._handle_stats()
                return
            if "addstat" in self.switches:
                self._handle_addstat()
                return
            if "buff" in self.switches:
                self._handle_buff()
                return
            if "alias" in self.switches:
                self._handle_alias()
                return
            if "desc" in self.switches:
                self._handle_desc()
                return
            if "dur" in self.switches:
                self._handle_dur()
                return
            if "repair" in self.switches:
                self._handle_repair()
                return
            if "clone" in self.switches:
                self._handle_clone()
                return
            if "shop" in self.switches:
                self._handle_shop()
                return
            if "stock" in self.switches:
                self._handle_stock()
                return
            if "unstock" in self.switches:
                self._handle_unstock()
                return
            if "delete" in self.switches:
                self._handle_delete()
                return
            self._handle_list()
        except (EquipmentSpecError, ShopSpecError) as err:
            self._msg(f"|r{err}|n")
