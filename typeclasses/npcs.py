"""NPC typeclasses for simple NPCs and LLM-backed NPCs."""

import random

from .characters import Character
from .llm_npc import DEFAULT_PROMPT_PREFIX, LocalLLMNPC


# 等級屬性倍率表：等級 N 的屬性 = base * (1 + (N-1) * scale)
LEVEL_SCALING = {
    "hp": 0.15,  # 每級 +15%
    "mp": 0.10,  # 每級 +10%
    "str": 0.05,  # 每級 +5%
    "def": 0.05,
    "spirit": 0.05,
    "intel": 0.05,
    "agility": 0.05,
    "stamina": 0.05,
    "spd": 0.03,
    "atk": 0.04,
}

# 等級預設屬性
BASE_STATS_BY_LEVEL = {
    "str": 10,
    "def": 10,
    "spirit": 10,
    "intel": 10,
    "agility": 10,
    "stamina": 10,
    "spd": 10,
    "atk": 10,
    "hp": 100,
    "max_hp": 100,
    "mp": 30,
    "max_mp": 30,
}


def scale_stat(base_value, level, stat_key):
    """根據等級計算屬性最終值。"""
    scale = LEVEL_SCALING.get(stat_key, 0.05)
    return int(base_value * (1 + (level - 1) * scale))


class NPC(Character):
    """A lightweight non-player character typeclass."""

    default_description = "這是一名 NPC。"

    def at_object_creation(self):
        super().at_object_creation()
        self.db.is_npc = True
        self.db.npc_kind = "npc"
        self.db.npc_attackable = True
        self.db.npc_retaliates = True
        self.db.npc_can_die = True

        # 等級系統
        self.db.level = 1
        self.db.base_level = 1

        # 冷卻與重生
        self.db.npc_cooldown = 60  # 重生冷卻（秒）
        self.db.npc_death_time = None  # 死亡時間戳

        # Token 系統
        self.db.npc_token_min = 1
        self.db.npc_token_max = 5
        self.db.npc_always_drops_tokens = True

        # Loot 系統
        self.db.npc_loot_table = []  # 列表: [{"typeclass": "typeclasses.equipment.Equipment", "key": "鐵劍", "chance": 0.3, "level_min": 1}, ...]
        self.db.npc_always_drops_loot = False

        # 逃跑系統
        self.db.npc_can_flee = True
        self.db.npc_flee_chance = 0.20  # 基礎失敗率 20%（所以成功率高）
        self.db.npc_flee_countdown = 0  # 逃跑倒數計時

        # 主動攻擊機率
        self.db.npc_aggro_chance = 0.0  # 被 look 時主動攻擊機率

        # 裝備
        self.db.equipment = {}

        if not self.db.desc:
            self.db.desc = self.default_description

        self._apply_level_stats()

    def _apply_level_stats(self):
        """根據等級套用屬性倍率。"""
        level = max(1, int(self.db.level or 1))
        base = self.db.base_level or 1

        # 等級差距加成
        if level > base:
            for stat_key in BASE_STATS_BY_LEVEL:
                base_val = BASE_STATS_BY_LEVEL[stat_key]
                new_val = scale_stat(base_val, level, stat_key)
                attr_name = (
                    f"base_{stat_key}"
                    if stat_key
                    in {
                        "str",
                        "def",
                        "spirit",
                        "intel",
                        "agility",
                        "stamina",
                        "spd",
                        "atk",
                    }
                    else stat_key
                )
                current = getattr(self.db, attr_name, base_val)
                # 只往上加，不覆寫管理者手動設的更高值
                if current < new_val:
                    setattr(self.db, attr_name, new_val)

        # 等級影響 HP/MP 上限
        max_hp = scale_stat(100, level, "hp")
        max_mp = scale_stat(30, level, "mp")
        if getattr(self.db, "max_hp", 100) < max_hp:
            self.db.max_hp = max_hp
        if getattr(self.db, "max_mp", 30) < max_mp:
            self.db.max_mp = max_mp

        # 同步 HP
        if self.db.hp and self.db.hp < self.db.max_hp:
            pass  # 保留當前 HP
        else:
            self.db.hp = self.db.max_hp
        if self.db.mp and self.db.mp < self.db.max_mp:
            pass
        else:
            self.db.mp = self.db.max_mp

    def get_tokens_for_drop(self):
        """計算死亡後要掉落的 Token 數量。"""
        level = max(1, int(self.db.level or 1))
        token_min = max(1, int(self.db.npc_token_min or 1))
        token_max = max(1, int(self.db.npc_token_max or 5))
        base = random.randint(token_min, token_max)
        # 等級加成
        bonus = (level - 1) * 2
        return base + bonus

    def is_in_cooldown(self):
        """NPC 是否在冷卻中（死亡/逃跑後重生倒數）。"""
        if self.db.npc_death_time is None:
            return False
        import time

        elapsed = time.time() - self.db.npc_death_time
        return elapsed < self.db.npc_cooldown

    def get_cooldown_remaining(self):
        """回傳剩餘冷卻秒數。"""
        if self.db.npc_death_time is None:
            return 0
        import time

        elapsed = time.time() - self.db.npc_death_time
        remaining = self.db.npc_cooldown - elapsed
        return max(0, int(remaining))

    def enter_cooldown(self, from_death=True):
        """進入冷卻狀態。"""
        import time

        self.db.npc_death_time = time.time()
        self.db.npc_flee_countdown = 0

    def can_respawn(self):
        """是否可以重生。"""
        return self.is_in_cooldown() is False

    def respawn(self):
        """重生 NPC。"""
        self.db.hp = self.db.max_hp
        self.db.mp = self.db.max_mp
        self.db.npc_death_time = None
        self.db.combat_state = "idle"
        self.db.combat_session = None
        self.db.combat_status = "normal"

    def check_aggro_on_look(self):
        """被 look 時檢查是否要主動攻擊。"""
        if not self.db.npc_aggro_chance:
            return False
        return random.random() < self.db.npc_aggro_chance

    def attempt_flee(self):
        """NPC 嘗試逃跑。成功回 True，失敗回 False。"""
        if not self.db.npc_can_flee:
            return False
        # 失敗率 = 基礎失敗率（越高越容易失敗）
        fail_rate = max(0.05, min(0.90, float(self.db.npc_flee_chance or 0.20)))
        if random.random() < fail_rate:
            return False  # 逃跑失敗
        return True  # 逃跑成功

    def drop_loot(self, player):
        """NPC 死亡時根據 loot_table 直接把掉落物生成在房間地上。"""
        import random
        from evennia import create_object
        from evennia.utils.utils import class_from_module

        loot_table = getattr(self.db, "npc_loot_table", [])
        if not loot_table:
            return

        location = getattr(self, "location", None)
        home = location
        for entry in loot_table:
            chance = entry.get("chance", 0.0)
            if random.random() >= chance:
                continue

            typeclass_path = entry.get("typeclass", "typeclasses.equipment.Equipment")
            key = entry.get("key", "戰利品")
            aliases = entry.get("aliases", [])
            desc = entry.get("desc", "從敵人身上撿到的戰利品。")
            stats = entry.get("stats", {})
            slot = entry.get("equip_slot", None)
            max_durability = entry.get("max_durability", 100)
            two_handed = bool(entry.get("two_handed", False))
            magic_buffs = list(entry.get("magic_buffs", []) or [])
            wear_style = entry.get("wear_style", "") or ""

            try:
                typeclass = class_from_module(typeclass_path)
            except Exception:
                typeclass = class_from_module("typeclasses.equipment.Equipment")

            create_object(
                typeclass,
                key=key,
                location=location,
                home=home,
                aliases=aliases,
                attributes=[
                    ("desc", desc),
                    ("stats", stats),
                    ("equip_slot", slot),
                    ("max_durability", max_durability),
                    ("durability", max_durability),
                    ("two_handed", two_handed),
                    ("magic_buffs", magic_buffs),
                    ("wear_style", wear_style),
                    ("is_equipment", True),
                ],
            )
            if player:
                player.msg(f"💎 {key} 掉在地上了。")
            if location:
                location.msg_contents(f"💎 {key} 從 {self.key} 身上掉落在地上。")


class LLMNPC(LocalLLMNPC):
    """LLM-backed NPC with sane defaults for this game."""

    default_description = "這是一名會回話的 NPC。"

    def at_object_creation(self):
        super().at_object_creation()
        self.db.is_npc = True
        self.db.npc_kind = "llm"
        self.db.npc_attackable = True
        self.db.npc_retaliates = True
        self.db.npc_can_die = True

        # 等級系統
        self.db.level = 1
        self.db.base_level = 1

        # 冷卻與重生
        self.db.npc_cooldown = 60
        self.db.npc_death_time = None

        # Token 系統
        self.db.npc_token_min = 1
        self.db.npc_token_max = 5
        self.db.npc_always_drops_tokens = True

        # Loot 系統
        self.db.npc_loot_table = []  # 列表: [{"typeclass": "typeclasses.equipment.Equipment", "key": "鐵劍", "chance": 0.3, "level_min": 1}, ...]
        self.db.npc_always_drops_loot = False

        # 逃跑系統
        self.db.npc_can_flee = True
        self.db.npc_flee_chance = 0.20
        self.db.npc_flee_countdown = 0

        # 主動攻擊
        self.db.npc_aggro_chance = 0.0

        # 裝備
        self.db.equipment = {}

        if not self.db.desc:
            self.db.desc = self.default_description
        if not self.attributes.has("prompt_prefix"):
            self.attributes.add("prompt_prefix", DEFAULT_PROMPT_PREFIX)

        self._apply_level_stats()
