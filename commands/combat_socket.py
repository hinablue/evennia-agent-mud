from __future__ import annotations

from evennia import Command

from world.gem_tools import GemSpecError, gem_ids, get_gem_by_id

STAT_LABELS = {
    "str": "力量",
    "stamina": "體質",
    "intel": "智力",
    "spirit": "精神",
    "agility": "敏捷",
    "agi": "敏捷",
    "spd": "速度",
    "def": "防禦",
    "atk": "攻擊",
    "hp": "生命",
    "mp": "魔力",
    "max_hp": "生命上限",
    "max_mp": "魔力上限",
}


class CmdSocketGem(Command):
    """鑲嵌持久 Gem 物件 reference 的指令。"""

    key = "socket"
    aliases = ["鑲嵌", "gem"]
    help_category = "General"

    def func(self):
        caller = self.caller
        args = self.args.strip().split()
        if len(args) < 2:
            caller.msg("用法：socket <寶石 ID> <槽位（1-3）>")
            return

        gem_id, slot_num = args[0], args[1]
        try:
            gem = get_gem_by_id(gem_id, require_enabled=True)
        except GemSpecError:
            caller.msg(f"找不到這種寶石。可用寶石：{', '.join(gem_ids(enabled_only=True))}")
            return

        max_sockets = getattr(caller.db, "max_sockets", 3) or 3
        try:
            slot_index = int(slot_num)
            if slot_index > max_sockets or slot_index < 1:
                caller.msg(f"槽位超出範圍 (1-{max_sockets})")
                return
            slot_id = f"slot{slot_index}"
            slot_label = f"第 {slot_index} 槽"
        except ValueError:
            caller.msg("槽位必須是數字。")
            return

        sockets = getattr(caller.db, "sockets", None) or {}
        caller.db.sockets = sockets
        caller.db.sockets[slot_id] = gem

        gem_name = getattr(gem.db, "display_name", None) or gem.key
        gem_stats = getattr(gem.db, "stats", {}) or {}
        stats_msg = ", ".join(
            [f"{STAT_LABELS.get(k, k)} +{v}" for k, v in gem_stats.items()]
        ) or "無"
        caller.msg(f"💎 你將 {gem_name} 鑲嵌到了{slot_label}！")
        caller.msg(f"屬性提升：{stats_msg}")


COMBAT_SOCKET_COMMANDS = [CmdSocketGem]
