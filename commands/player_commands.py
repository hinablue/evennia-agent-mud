"""Player-facing commands for status, inventory, equipment, and shopping."""

from commands.command import MuxCommand
from evennia.utils import utils


class CmdStatus(MuxCommand):
    """
    顯示角色狀態（HP、MP、屬性等）。

    Usage:
      status
      stat
    """

    key = "status"
    aliases = ["stat", "狀態", "屬性"]
    locks = "cmd:pperm(Player)"
    help_category = "General"

    def func(self):
        caller = self.caller

        # Get base stats
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

        # Get computed stats (with equipment bonuses)
        str_val = caller.get_stat("str")
        def_val = caller.get_stat("def")
        spirit_val = caller.get_stat("spirit")
        intel_val = caller.get_stat("intel")
        agility_val = caller.get_stat("agility")
        stamina_val = caller.get_stat("stamina")
        spd_val = caller.get_stat("spd")
        atk_val = caller.get_stat("atk")

        # Combat state
        combat_state = getattr(caller.db, "combat_state", "idle")
        combat_status = getattr(caller.db, "combat_status", "normal")

        # Build status display
        hp_bar = self._make_bar(hp, max_hp, 20, "red")
        mp_bar = self._make_bar(mp, max_mp, 20, "blue")
        stam_bar = self._make_bar(stamina, max_stamina, 20, "green")

        lines = [
            f" {caller.key} 的狀態",
            f" 等級：{level}  經驗值：{exp}/{max_exp}",
            f" HP：{hp}/{max_hp} {hp_bar}",
            f" MP：{mp}/{max_mp} {mp_bar}",
            f" 體力：{stamina}/{max_stamina} {stam_bar}",
            f" Token：{tokens}",
            f" 戰鬥狀態：{combat_state} | 異常狀態：{combat_status}",
            f" 力量：{str_val}   智力：{intel_val}   敏捷：{agility_val}",
            f" 防禦：{def_val}   精神：{spirit_val}   體質：{stamina_val}",
            f" 速度：{spd_val}   攻擊：{atk_val}",
        ]

        caller.msg("\n".join(lines))

    def _make_bar(self, current, maximum, length, color):
        """Create a visual progress bar."""
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

    Usage:
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
        equipped = caller.get_all_equipped()

        lines = [f"|w┌─ {caller.key} 的背包 ({len(inventory)}/{capacity}) ─┐|n"]

        if not inventory:
            lines.append("│ 背包是空的。")
        else:
            for idx, item in enumerate(inventory, 1):
                if not item:
                    continue
                name = item.get_display_name(caller)
                # Check if equipped
                equip_info = ""
                for slot, eq_item in equipped.items():
                    if eq_item and eq_item.id == item.id:
                        slot_names = {
                            "hat": "帽子", "top": "上身", "bottom": "下身",
                            "cloak": "披風", "shoes": "鞋子", "gloves": "手套",
                            "glasses": "眼鏡", "earring": "耳環", "ring": "戒指",
                            "main_hand": "主手", "off_hand": "副手", "two_hand": "雙手",
                        }
                        slot_name = slot_names.get(slot, slot)
                        equip_info = f" |g(已裝備：{slot_name})|n"
                        break
                lines.append(f"│ {idx:2d}. {name}{equip_info}")

        lines.append(f"└{'─' * 38}┘")

        caller.msg("\n".join(lines))


class CmdEquipment(MuxCommand):
    """
    顯示裝備欄位。

    Usage:
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

        slot_display = {
            "hat": "帽子", "top": "上身", "bottom": "下身",
            "cloak": "披風", "shoes": "鞋子", "gloves": "手套",
            "glasses": "眼鏡", "earring": "耳環", "ring": "戒指",
            "main_hand": "主手武器", "off_hand": "副手武器", "two_hand": "雙手武器",
        }

        lines = [f"|w┌─ {caller.key} 的裝備 ─┐|n"]

        if not equipment:
            lines.append("│ 目前沒有穿戴任何裝備。")
        else:
            for slot in ["hat", "top", "bottom", "cloak", "shoes", "gloves",
                         "glasses", "earring", "ring", "main_hand", "off_hand", "two_hand"]:
                item = equipment.get(slot)
                slot_name = slot_display.get(slot, slot)
                if item:
                    name = item.get_display_name(caller)
                    wear_style = getattr(item.db, "wear_style", "")
                    style_str = f" ({wear_style})" if wear_style else ""
                    lines.append(f"│ {slot_name:6s}：{name}{style_str}")
                else:
                    lines.append(f"│ {slot_name:6s}：|x空|n")

        lines.append(f"└{'─' * 30}┘")

        caller.msg("\n".join(lines))


class CmdShop(MuxCommand):
    """顯示目前房間的商店清單。"""

    key = "shop"
    aliases = ["商店", "store"]
    locks = "cmd:pperm(Player)"
    help_category = "General"

    def func(self):
        """Show the current room's available stock."""
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
        """Buy one item by stock index or template name."""
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
