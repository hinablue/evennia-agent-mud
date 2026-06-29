from __future__ import annotations

from evennia import Command

GEM_DB = {
    "ruby": {"name": "紅寶石", "stats": {"str": 3, "stamina": 1}},
    "sapphire": {"name": "藍寶石", "stats": {"intel": 3, "spirit": 1}},
    "emerald": {"name": "綠寶石", "stats": {"agility": 3, "spd": 1}},
}


class CmdSocketGem(Command):
    """鑲嵌寶石指令。"""

    key = "socket"
    aliases = ["鑲嵌", "gem"]
    help_category = "Combat"

    def func(self):
        caller = self.caller
        args = self.args.strip().split()
        if len(args) < 2:
            caller.msg("用法: socket <寶石id> <槽位(1-3)>")
            return

        gem_id, slot_num = args[0], args[1]
        if gem_id not in GEM_DB:
            caller.msg(f"找不到這種寶石。可用: {', '.join(GEM_DB.keys())}")
            return

        max_sockets = getattr(caller.db, "max_sockets", 3) or 3
        try:
            slot_index = int(slot_num)
            if slot_index > max_sockets or slot_index < 1:
                caller.msg(f"槽位超出範圍 (1-{max_sockets})")
                return
            slot_id = f"slot{slot_index}"
        except ValueError:
            caller.msg("槽位必須是數字。")
            return

        gem_data = GEM_DB[gem_id]
        sockets = getattr(caller.db, "sockets", None) or {}
        caller.db.sockets = sockets
        caller.db.sockets[slot_id] = gem_data

        stats_msg = ", ".join([f"{k} +{v}" for k, v in gem_data["stats"].items()])
        caller.msg(f"💎 你將 {gem_data['name']} 鑲嵌到了 {slot_id} 中！")
        caller.msg(f"屬性提升: {stats_msg}")


COMBAT_SOCKET_COMMANDS = [CmdSocketGem]
