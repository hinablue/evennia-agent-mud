"""面向玩家的狀態、庫存、裝備和購物指令。"""

from commands.command import MuxCommand

SLOT_DISPLAY_NAMES = {
    "hat": "帽子",
    "top": "上身",
    "bottom": "下身",
    "cloak": "披風",
    "shoes": "鞋子",
    "gloves": "手套",
    "glasses": "眼鏡",
    "earring": "耳環",
    "ring": "戒指",
    "main_hand": "主手武器",
    "off_hand": "副手武器",
    "two_hand": "雙手武器",
}


def _match_item_name(item, query, caller=None):
    """Return whether an item matches key, display name, alias, or dbref."""
    query = (query or "").strip().lower()
    if not item or not query:
        return False
    if query == str(getattr(item, "id", "")) or query == f"#{getattr(item, 'id', '')}":
        return True
    names = [getattr(item, "key", ""), getattr(item, "name", "")]
    try:
        names.append(item.get_display_name(caller))
    except Exception:
        pass
    aliases = getattr(item, "aliases", None)
    if aliases and hasattr(aliases, "all"):
        try:
            names.extend(aliases.all())
        except Exception:
            pass
    elif aliases:
        try:
            names.extend(list(aliases))
        except Exception:
            pass
    return any(query == str(name).lower() for name in names if name)


def _find_inventory_item(caller, query):
    """Find an item in the caller's local inventory/contents."""
    candidates = []
    if hasattr(caller, "get_inventory"):
        candidates.extend(caller.get_inventory())
    candidates.extend(getattr(caller, "contents", []) or [])
    for item in candidates:
        if _match_item_name(item, query, caller):
            return item
    if hasattr(caller, "search"):
        try:
            return caller.search(query, candidates=candidates)
        except Exception:
            return None
    return None


def _find_equipped_item(caller, query):
    """Find an equipped item by slot or item name."""
    query = (query or "").strip()
    equipment = caller.get_all_equipped() if hasattr(caller, "get_all_equipped") else {}
    if query in equipment:
        return query, equipment.get(query)
    for slot, item in equipment.items():
        if _match_item_name(item, query, caller):
            return slot, item
    return None, None


class CmdStatus(MuxCommand):
    """
    顯示角色狀態（HP、MP、屬性等）。

    用法:
      status
      stat
    """

    key = "status"
    aliases = ["stat", "狀態", "屬性"]
    locks = "cmd:pperm(Player)"
    help_category = "General"

    def func(self):
        caller = self.caller

        # 取得基礎統計數據
        hp = getattr(caller.db, "hp", 0)
        max_hp = getattr(caller.db, "max_hp", 0)
        mp = getattr(caller.db, "mp", 0)
        max_mp = getattr(caller.db, "max_mp", 0)
        stamina = getattr(caller.db, "stamina", 0)
        max_stamina = getattr(caller.db, "max_stamina", 0)
        level = getattr(caller.db, "level", 1)
        exp = getattr(caller.db, "exp", 0)
        max_exp = getattr(caller.db, "max_exp", 100)
        tokens = getattr(caller.db, "tokens", 0)

        # 取得計算統計資料（有設備獎勵）
        str_val = caller.get_stat("str")
        def_val = caller.get_stat("def")
        spirit_val = caller.get_stat("spirit")
        intel_val = caller.get_stat("intel")
        agility_val = caller.get_stat("agility")
        stamina_val = caller.get_stat("stamina")
        spd_val = caller.get_stat("spd")
        atk_val = caller.get_stat("atk")

        # 戰鬥狀態
        combat_state = getattr(caller.db, "combat_state", "idle")
        combat_status = getattr(caller.db, "combat_status", "normal")

        # 建置狀態顯示
        hp_bar = self._make_bar(hp, max_hp, 20, "red")
        mp_bar = self._make_bar(mp, max_mp, 20, "blue")
        stam_bar = self._make_bar(stamina, max_stamina, 20, "green")

        lines = [
            f" {caller.key} 的狀態",
            f" 等級：{level}  經驗值：{exp}/{max_exp}",
            f" HP：{hp}/{max_hp} {hp_bar}",
            f" MP：{mp}/{max_mp} {mp_bar}",
            f" 體力：{stamina}/{max_stamina} {stam_bar}",
            f" 代幣：{tokens}",
            f" 戰鬥狀態：{combat_state} | 異常狀態：{combat_status}",
            f" 力量：{str_val}   智力：{intel_val}   敏捷：{agility_val}",
            f" 防禦：{def_val}   精神：{spirit_val}   體質：{stamina_val}",
            f" 速度：{spd_val}   攻擊：{atk_val}",
        ]

        caller.msg("\n".join(lines))

    def _make_bar(self, current, maximum, length, color):
        """建立一個視覺進度條。"""
        if maximum <= 0:
            return "|x[" + " " * length + "]|n"
        filled = int((current / maximum) * length)
        filled = max(0, min(length, filled))
        empty = length - filled
        color_map = {"red": "r", "blue": "b", "green": "g", "yellow": "y"}
        c = color_map.get(color, "w")
        return f"|{c}[{'█' * filled}{' ' * empty}]|n"


class CmdInventory(MuxCommand):
    """
    顯示背包內容。

    用法:
      inventory
      inv
      i
      背包
    """

    key = "inventory"
    aliases = ["inv", "i", "背包"]
    locks = "cmd:pperm(Player)"
    help_category = "General"

    def func(self):
        caller = self.caller

        inventory = caller.get_inventory()
        capacity = caller.get_inventory_capacity()

        lines = [f"|w┌─ {caller.key} 的背包 ({len(inventory)}/{capacity}) ─┐|n"]

        if not inventory:
            lines.append("│ 背包是空的。")
        else:
            for idx, item in enumerate(inventory, 1):
                if not item:
                    continue
                name = item.get_display_name(caller)
                lines.append(f"│ {idx:2d}. {name}")

        lines.append(f"└{'─' * 38}┘")

        caller.msg("\n".join(lines))


class CmdEquipment(MuxCommand):
    """
    顯示裝備欄位。

    用法:
      equipment
      eq
      裝備
    """

    key = "equipment"
    aliases = ["eq", "裝備"]
    locks = "cmd:pperm(Player)"
    help_category = "General"

    def func(self):
        caller = self.caller

        equipment = caller.get_all_equipped()

        slot_display = SLOT_DISPLAY_NAMES

        lines = [f"|w┌─ {caller.key} 的裝備 ─┐|n"]

        if not equipment:
            lines.append("│ 目前沒有穿戴任何裝備。")
        else:
            for slot in [
                "hat",
                "top",
                "bottom",
                "cloak",
                "shoes",
                "gloves",
                "glasses",
                "earring",
                "ring",
                "main_hand",
                "off_hand",
                "two_hand",
            ]:
                item = equipment.get(slot)
                slot_name = slot_display.get(slot, slot)
                if item:
                    name = item.get_display_name(caller)
                    wear_style = getattr(item.db, "wear_style", "")
                    style_str = f" ({wear_style})" if wear_style else ""
                    covered_by = getattr(item.db, "covered_by", None)
                    cover_str = (
                        f" |y(被 {covered_by.get_display_name(caller)} 覆蓋)|n"
                        if covered_by
                        else ""
                    )
                    lines.append(f"│ {slot_name:6s}：{name}{style_str}{cover_str}")
                else:
                    lines.append(f"│ {slot_name:6s}：|x空|n")

        lines.append(f"└{'─' * 30}┘")

        caller.msg("\n".join(lines))


class CmdWearEquipment(MuxCommand):
    """穿戴背包中的裝備。

    用法:
      wear <裝備> [=] [穿戴描述]
      穿戴 <裝備> [穿戴描述]
    """

    key = "wear"
    aliases = ["穿", "穿戴", "equip", "裝備"]
    locks = "cmd:pperm(Player)"
    help_category = "General"

    def func(self):
        caller = self.caller
        if not self.args:
            caller.msg("用法：wear <裝備> [=] [穿戴描述]")
            return
        item_name = self.lhs if self.rhs is not None else self.args
        wear_style = self.rhs or ""
        item = _find_inventory_item(caller, item_name)
        if not item and self.rhs is None:
            parts = self.args.split(maxsplit=1)
            item = _find_inventory_item(caller, parts[0])
            if item:
                item_name = parts[0]
                wear_style = parts[1] if len(parts) > 1 else ""
        if not item:
            caller.msg(f"⚠️ 背包裡找不到：{item_name}")
            return
        if not getattr(item.db, "is_equipment", False):
            caller.msg(f"⚠️ {item.get_display_name(caller)} 不是可以穿戴的裝備。")
            return
        caller.equip_item(item, wear_style=wear_style)


class CmdRemoveEquipment(MuxCommand):
    """卸下已穿戴的裝備。"""

    key = "remove"
    aliases = ["脫下", "卸下", "unequip"]
    locks = "cmd:pperm(Player)"
    help_category = "General"

    def func(self):
        caller = self.caller
        selection = (self.args or "").strip()
        if not selection:
            caller.msg("用法：remove <裝備或欄位>")
            return
        slot, item = _find_equipped_item(caller, selection)
        caller.unequip_item(item or slot or selection)


class CmdCoverEquipment(MuxCommand):
    """用另一件裝備覆蓋已穿戴裝備。"""

    key = "cover"
    aliases = ["遮住", "覆蓋"]
    rhs_split = (" with ", "=")
    locks = "cmd:pperm(Player)"
    help_category = "General"

    def func(self):
        caller = self.caller
        lhs = self.lhs
        rhs = self.rhs
        if rhs is None and " with " in (self.args or ""):
            lhs, rhs = [part.strip() for part in self.args.split(" with ", 1)]
        if not self.args or not rhs:
            caller.msg("用法：cover <已穿戴裝備> with <裝備>")
            return
        _, target = _find_equipped_item(caller, lhs)
        if not target:
            caller.msg(f"⚠️ 你沒有穿戴：{lhs}")
            return
        cover_slot, cover_item = _find_equipped_item(caller, rhs)
        if not cover_item:
            cover_item = _find_inventory_item(caller, rhs)
            if cover_item and not caller.equip_item(cover_item):
                return
        if not cover_item:
            caller.msg(f"⚠️ 找不到用來覆蓋的裝備：{rhs}")
            return
        if cover_item == target:
            caller.msg("⚠️ 不能用同一件裝備覆蓋自己。")
            return
        cover_type = getattr(cover_item.db, "clothing_type", None) or getattr(
            cover_item.db, "equip_slot", None
        )
        try:
            from typeclasses.characters import CLOTHING_TYPE_CANT_COVER_WITH
        except Exception:
            CLOTHING_TYPE_CANT_COVER_WITH = set()
        if cover_type in CLOTHING_TYPE_CANT_COVER_WITH:
            caller.msg(
                f"⚠️ {cover_item.get_display_name(caller)} 不適合用來覆蓋其他裝備。"
            )
            return
        if getattr(cover_item.db, "covered_by", None):
            caller.msg(f"⚠️ {cover_item.get_display_name(caller)} 自己已經被覆蓋了。")
            return
        if getattr(target.db, "covered_by", None):
            caller.msg(f"⚠️ {target.get_display_name(caller)} 已經被其他裝備覆蓋了。")
            return
        target.db.covered_by = cover_item
        caller.msg(
            f"✅ 你用 {cover_item.get_display_name(caller)} 覆蓋了 {target.get_display_name(caller)}。"
        )


class CmdUncoverEquipment(MuxCommand):
    """揭開被覆蓋的裝備。"""

    key = "uncover"
    aliases = ["露出", "揭開"]
    locks = "cmd:pperm(Player)"
    help_category = "General"

    def func(self):
        caller = self.caller
        selection = (self.args or "").strip()
        if not selection:
            caller.msg("用法：uncover <已穿戴裝備>")
            return
        _, item = _find_equipped_item(caller, selection)
        if not item:
            caller.msg(f"⚠️ 你沒有穿戴：{selection}")
            return
        cover = getattr(item.db, "covered_by", None)
        if not cover:
            caller.msg(f"⚠️ {item.get_display_name(caller)} 沒有被覆蓋。")
            return
        if getattr(cover.db, "covered_by", None):
            caller.msg(
                f"⚠️ {item.get_display_name(caller)} 被壓在太多層下面，還不能露出。"
            )
            return
        item.db.covered_by = None
        caller.msg(f"✅ 你露出了 {item.get_display_name(caller)}。")


class CmdShop(MuxCommand):
    """顯示目前房間的商店清單。"""

    key = "shop"
    aliases = ["商店", "store"]
    locks = "cmd:pperm(Player)"
    help_category = "General"

    def func(self):
        """顯示目前房間的可用庫存。"""
        caller = self.caller
        room = getattr(caller, "location", None)
        if not room:
            caller.msg("⚠️ 你現在不在任何房間裡。")
            return

        from world.shop_tools import ShopSpecError, summarize_room_shop_for_player

        try:
            caller.msg(summarize_room_shop_for_player(room))
        except ShopSpecError as err:
            caller.msg(f"⚠️ {err}")


class CmdBuy(MuxCommand):
    """從目前房間商店購買一件商品。"""

    key = "buy"
    aliases = ["購買"]
    locks = "cmd:pperm(Player)"
    help_category = "General"

    def func(self):
        """按股票指數或範本名稱購買一件商品。"""
        caller = self.caller
        selection = (self.args or "").strip()
        if not selection:
            caller.msg("用法：buy <商品編號或名稱>")
            return

        from world.shop_tools import ShopSpecError, buy_from_room_shop

        try:
            result = buy_from_room_shop(caller, selection)
        except ShopSpecError as err:
            caller.msg(f"⚠️ {err}")
            return

        caller.msg(result["message"])
