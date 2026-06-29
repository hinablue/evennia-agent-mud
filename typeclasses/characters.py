"""
Characters

Characters are (by default) Objects setup to be puppeted by Accounts.
They are what you "see" in game. The Character class in this module
is setup to be the "default" character type created by the default
creation commands.

"""

from evennia.objects.objects import DefaultCharacter
from evennia.contrib.game_systems.clothing import ClothedCharacter
from evennia.contrib.game_systems.gendersub import GenderCharacter
from evennia.contrib.rpg.rpsystem import ContribRPCharacter

from commands.combat_commands import CombatCmdSet
from .objects import ObjectParent


# Equipment slot definitions
# slot_name: (display_name, auto_unequip_on_replaced, is_weapon_slot)
EQUIPMENT_SLOTS = {
    "hat": {"name": "帽子", "auto_unequip": True, "is_weapon": False},
    "top": {"name": "上身", "auto_unequip": False, "is_weapon": False},
    "bottom": {"name": "下身", "auto_unequip": False, "is_weapon": False},
    "cloak": {"name": "披風", "auto_unequip": True, "is_weapon": False},
    "shoes": {"name": "鞋子", "auto_unequip": True, "is_weapon": False},
    "gloves": {"name": "手套", "auto_unequip": True, "is_weapon": False},
    "glasses": {"name": "眼鏡", "auto_unequip": True, "is_weapon": False},
    "earring": {"name": "耳環", "auto_unequip": True, "is_weapon": False},
    "ring": {"name": "戒指", "auto_unequip": True, "is_weapon": False},
    "main_hand": {"name": "主手武器", "auto_unequip": True, "is_weapon": True},
    "off_hand": {"name": "副手武器", "auto_unequip": True, "is_weapon": True},
    "two_hand": {"name": "雙手武器", "auto_unequip": True, "is_weapon": True},
}


class Character(ObjectParent, ClothedCharacter, GenderCharacter, ContribRPCharacter):
    """
    The Character just re-implements some of the Object's methods and hooks
    to represent a Character entity in-game.

    See mygame/typeclasses/objects.py for a list of
    properties and methods available on all Object child classes like this.
    """

    default_description = "這是一名旅人。"
    _COMBAT_ALLOWED_COMMANDS = {"attack", "atk", "攻擊", "skill", "sk", "技能"}

    def at_object_creation(self):
        """Initialize default combat and progression attributes."""
        super().at_object_creation()
        defaults = {
            "combat_state": "idle",
            "combat_session": None,
            "combat_status": "normal",
            "hp": 100,
            "max_hp": 100,
            "mp": 30,
            "max_mp": 30,
            "stamina": 100,
            "max_stamina": 100,
            "level": 1,
            "exp": 0,
            "max_exp": 100,
            "max_sockets": 3,
            "sockets": {},
            "equipped_items": [],
            "skills": [],
            "tokens": 0,
            "inventory_capacity": 10,
            "inventory": [],
            "equipment": {},
            "base_str": 10,
            "base_def": 10,
            "base_spirit": 10,
            "base_intel": 10,
            "base_agility": 10,
            "base_stamina": 10,
            "base_spd": 10,
            "base_atk": 10,
        }
        for key, value in defaults.items():
            if self.attributes.get(key) is None:
                self.attributes.add(key, value)

    def at_cmdset_get(self, **kwargs):
        """Toggle the combat-only cmdset based on current combat state."""
        super().at_cmdset_get(**kwargs)
        in_combat = getattr(self.db, "combat_state", "idle") == "fighting"
        try:
            if in_combat:
                self.cmdset.add_default(CombatCmdSet, persistent=False)
            else:
                self.cmdset.remove_default(CombatCmdSet)
        except Exception:
            pass

    def at_pre_cmd(self, raw_string, **kwargs):
        """Block non-combat commands while the character is fighting."""
        if getattr(self.db, "combat_state", "idle") != "fighting":
            return False

        command_name = (raw_string or "").strip().split(maxsplit=1)[0]
        if not command_name:
            return False
        if command_name.startswith("__"):
            return False
        if command_name.lower() in self._COMBAT_ALLOWED_COMMANDS:
            return False

        self.msg("⚠️ 你正處於激烈的戰鬥中，現在只能使用戰鬥指令。")
        return True

    def get_stat(self, stat_name):
        """Return the final stat after equipment and gem bonuses."""
        base_val = getattr(self.db, f"base_{stat_name}", 10)

        bonus = 0
        equipment = getattr(self.db, "equipment", {}) or {}
        for item in equipment.values():
            if item and hasattr(item, "db"):
                item_stats = getattr(item.db, "stats", {})
                bonus += item_stats.get(stat_name, 0)

        sockets = getattr(self.db, "sockets", {}) or {}
        for gem in sockets.values():
            if hasattr(gem, "get"):
                gem_stats = gem.get("stats", {}) or {}
            else:
                gem_stats = getattr(gem, "stats", {})
            bonus += gem_stats.get(stat_name, 0)

        return base_val + bonus

    # -------------------------------------------------------------------------
    # Token / Wallet System
    # -------------------------------------------------------------------------

    def get_tokens(self):
        """Get current token balance."""
        return getattr(self.db, "tokens", 0) or 0

    def add_tokens(self, amount):
        """Add tokens to wallet."""
        if amount <= 0:
            return False
        current = self.get_tokens()
        self.db.tokens = current + amount
        self.msg(f"💰 你獲得了 {amount} 枚 Token。")
        return True

    def spend_tokens(self, amount):
        """Spend tokens from wallet. Returns True if successful."""
        if amount <= 0:
            return False
        current = self.get_tokens()
        if current < amount:
            self.msg(f"⚠️ Token 不足！你需要 {amount} 枚，但只有 {current} 枚。")
            return False
        self.db.tokens = current - amount
        self.msg(f"💸 你支付了 {amount} 枚 Token。")
        return True

    # -------------------------------------------------------------------------
    # Inventory System
    # -------------------------------------------------------------------------

    def get_inventory(self):
        """Get list of items in inventory."""
        return list(getattr(self.db, "inventory", []) or [])

    def get_inventory_capacity(self):
        """Get inventory capacity."""
        return getattr(self.db, "inventory_capacity", 10) or 10

    def expand_inventory(self, amount=5):
        """Expand inventory capacity."""
        current = self.get_inventory_capacity()
        self.db.inventory_capacity = current + amount
        self.msg(f"🎒 背包容量增加了 {amount} 格，現在共有 {current + amount} 格。")

    def _get_inventory_count(self):
        """Get current item count in inventory."""
        inv = self.get_inventory()
        return len([item for item in inv if item])

    def add_to_inventory(self, item):
        """Add item to inventory. Returns True if successful."""
        if not item:
            return False
        inv = self.get_inventory()
        if len(inv) >= self.get_inventory_capacity():
            self.msg(f"⚠️ 背包已滿，無法放入 {item.get_display_name(self)}！")
            return False
        inv.append(item)
        self.db.inventory = inv
        return True

    def remove_from_inventory(self, item):
        """Remove item from inventory. Returns True if successful."""
        if not item:
            return False
        inv = self.get_inventory()
        if item in inv:
            inv.remove(item)
            self.db.inventory = inv
            return True
        return False

    def find_in_inventory(self, key):
        """Find item in inventory by key or alias."""
        inv = self.get_inventory()
        for item in inv:
            if item.key.lower() == key.lower():
                return item
            if key.lower() in [alias.lower() for alias in item.aliases.all()]:
                return item
        return None

    # -------------------------------------------------------------------------
    # Equipment System
    # -------------------------------------------------------------------------

    def get_equipped(self, slot):
        """Get equipped item in slot."""
        equipment = getattr(self.db, "equipment", {}) or {}
        return equipment.get(slot)

    def get_all_equipped(self):
        """Get all equipped items."""
        equipment = getattr(self.db, "equipment", {}) or {}
        return {slot: item for slot, item in equipment.items() if item}

    def _unequip_to_inventory(self, item):
        """Try to move unequipped item to inventory, or drop in room."""
        if not item:
            return
        if self.add_to_inventory(item):
            self.msg(f"📦 {item.get_display_name(self)} 被收進背包。")
        else:
            # Drop in room
            if self.location:
                item.location = self.location
                item.save()
                self.msg(f"📦 背包已滿，{item.get_display_name(self)} 被丟在房間地上。")

    def equip_item(self, item, slot=None):
        """
        Equip an item. If slot is None, auto-detect from item's equip_slot.
        Returns True if successful.
        """
        if not item:
            return False

        # Determine slot
        if slot is None:
            slot = getattr(item.db, "equip_slot", None)
            if not slot:
                self.msg(f"⚠️ {item.get_display_name(self)} 無法裝備：沒有指定的裝備欄位。")
                return False

        if slot not in EQUIPMENT_SLOTS:
            self.msg(f"⚠️ 無效的裝備槽位：{slot}")
            return False

        slot_info = EQUIPMENT_SLOTS[slot]
        is_weapon_slot = slot_info["is_weapon"]

        # Handle two-handed weapon conflict
        if slot == "two_hand":
            # Check if already holding something in main/off hand
            main_hand = self.get_equipped("main_hand")
            off_hand = self.get_equipped("off_hand")
            if main_hand or off_hand:
                self.msg("⚠️ 你已經在手持武器，必須先卸下才能裝備雙手武器。")
                return False
            # Check if item is two-handed
            if not getattr(item.db, "two_handed", False):
                self.msg(f"⚠️ {item.get_display_name(self)} 不是雙手武器。")
                return False

        if slot in ("main_hand", "off_hand"):
            # Check two-handed weapon conflict
            two_hand = self.get_equipped("two_hand")
            if two_hand:
                self.msg("⚠️ 你已經在持雙手武器，必須先卸下才能裝備單手武器。")
                return False
            # Check if item is two-handed
            if getattr(item.db, "two_handed", False):
                self.msg("⚠️ 雙手武器必須裝備到雙手欄位。")
                return False

        # Remove current item in slot
        current_item = self.get_equipped(slot)
        if current_item:
            if slot_info["auto_unequip"]:
                self._unequip_to_inventory(current_item)
            else:
                # Top/bottom don't auto-unequip - the new item just replaces
                self.msg(f"⚠️ 你的 {slot_info['name']} 已經穿著了。")

        # If equipping to main/off hand, remove from inventory if present
        if is_weapon_slot:
            self.remove_from_inventory(item)

        # Equip
        equipment = getattr(self.db, "equipment", {}) or {}
        equipment[slot] = item
        self.db.equipment = equipment

        # Set worn flag for clothing system compatibility
        item.db.worn = True
        item.db.equip_slot = slot

        self.msg(f"✅ 你裝備了 {item.get_display_name(self)}（{slot_info['name']}）。")
        return True

    def unequip_item(self, slot):
        """Unequip item from slot and move to inventory."""
        item = self.get_equipped(slot)
        if not item:
            slot_info = EQUIPMENT_SLOTS.get(slot, {"name": slot})
            self.msg(f"⚠️ {slot_info['name']} 欄位沒有裝備任何東西。")
            return False

        slot_info = EQUIPMENT_SLOTS[slot]

        # Try to add to inventory
        if not self.add_to_inventory(item):
            # Inventory full
            if self.location:
                item.location = self.location
                item.save()
                self.msg(f"📦 背包已滿，{item.get_display_name(self)} 被丟在房間地上。")

        # Clear slot
        equipment = getattr(self.db, "equipment", {}) or {}
        equipment[slot] = None
        self.db.equipment = equipment

        item.db.worn = False
        item.db.equip_slot = None

        self.msg(f"✅ 你卸下了 {item.get_display_name(self)}。")
        return True

    def get_equipment_description(self):
        """Get description of equipped items for 'look' command."""
        equipment = self.get_all_equipped()
        if not equipment:
            return "目前身上沒有穿戴任何裝備。"

        lines = []
        for slot, item in sorted(equipment.items(), key=lambda x: list(EQUIPMENT_SLOTS.keys()).index(x[0]) if x[0] in EQUIPMENT_SLOTS else 999):
            slot_info = EQUIPMENT_SLOTS.get(slot, {"name": slot, "is_weapon": False})
            slot_name = slot_info["name"]
            item_name = item.get_display_name(self)
            wear_style = getattr(item.db, "wear_style", "")
            style_str = f"（{wear_style}）" if wear_style else ""
            lines.append(f"  {slot_name}：{item_name}{style_str}")

        return "\n".join(lines)

    # -------------------------------------------------------------------------
    # Combat / Level Up
    # -------------------------------------------------------------------------

    def gain_exp(self, amount):
        """增加經驗值並檢查升級。"""
        current_exp = getattr(self.db, "exp", 0) or 0
        current_max_exp = getattr(self.db, "max_exp", 100) or 100
        current_level = getattr(self.db, "level", 1) or 1

        self.db.exp = current_exp + amount
        self.db.max_exp = current_max_exp
        self.db.level = current_level
        self.msg(f"✨ 你獲得了 {amount} 點經驗值！")

        while self.db.exp >= self.db.max_exp:
            self.db.exp -= self.db.max_exp
            self.db.level += 1
            self.db.max_exp = max(1, int(self.db.max_exp * 1.2))

            import random

            stats_to_buff = [
                "base_str",
                "base_def",
                "base_spirit",
                "base_intel",
                "base_agility",
                "base_stamina",
            ]
            buffed = random.choice(stats_to_buff)
            current_value = getattr(self.db, buffed, 10) or 10
            setattr(self.db, buffed, current_value + 2)

            self.msg(f"🎊 等級提升！你現在等級 {self.db.level}！")
            self.msg(f"💪 你的 {buffed.replace('base_', '')} 提升了 2 點！")

    def learn_skill(self, skill_id):
        """預留：學習新技能的邏輯。"""
        if not hasattr(self.db, "skills") or self.db.skills is None:
            self.db.skills = []
        if skill_id not in self.db.skills:
            self.db.skills.append(skill_id)
            self.msg(f"📖 你學會了新技能：{skill_id}！")
        else:
            self.msg("你已經掌握這個技能了。")

    # -------------------------------------------------------------------------
    # Buff / Active Effect System
    # -------------------------------------------------------------------------

    def apply_buff(self, stat, amount, duration):
        """
        對自己施加 buff效果（佔用一回合）。
        stat: 屬性名（如 'str', 'def', 'atk'）
        amount: 增幅值
        duration: 持續回合數（戰鬥回合）
        """
        if duration <= 0:
            return
        buffs = getattr(self.db, "active_buffs", {}) or {}
        import time
        buffs[stat] = {
            "amount": int(amount),
            "duration": int(duration),
            "applied_at": time.time(),
        }
        self.db.active_buffs = buffs
        self.msg(f"✨ 你的 {stat} 獲得了 +{amount} 的增幅，持續 {duration} 回合。")

    def apply_debuff_to_self(self, stat, amount, duration):
        """對自己施加 debuff（負面效果）。"""
        if duration <= 0:
            return
        debuffs = getattr(self.db, "active_debuffs", {}) or {}
        import time
        debuffs[stat] = {
            "amount": int(amount),
            "duration": int(duration),
            "applied_at": time.time(),
        }
        self.db.active_debuffs = debuffs
        self.msg(f"⚠️ 你的 {stat} 被降低了 {amount}，持續 {duration} 回合。")

    def get_buff_bonus(self, stat_name):
        """取得某屬性的 buff 加成值。"""
        buffs = getattr(self.db, "active_buffs", {}) or {}
        buff = buffs.get(stat_name)
        if not buff:
            return 0
        return buff.get("amount", 0)

    def get_debuff_penalty(self, stat_name):
        """取得某屬性的 debuff 減益值。"""
        debuffs = getattr(self.db, "active_debuffs", {}) or {}
        debuff = debuffs.get(stat_name)
        if not debuff:
            return 0
        return debuff.get("amount", 0)

    def tick_buffs(self):
        """每回合開始時呼叫遞減 buff 持續時間。"""
        buffs = getattr(self.db, "active_buffs", {}) or {}
        debuffs = getattr(self.db, "active_debuffs", {}) or {}
        expired = []
        for stat, data in buffs.items():
            data["duration"] -= 1
            if data["duration"] <= 0:
                expired.append(stat)
                self.msg(f"⏳ 你的 {stat} 增幅效果結束了。")
        for stat in expired:
            del buffs[stat]
        self.db.active_buffs = buffs

        expired_debuff = []
        for stat, data in debuffs.items():
            data["duration"] -= 1
            if data["duration"] <= 0:
                expired_debuff.append(stat)
                self.msg(f"⏳ 你的 {stat} 減益效果結束了。")
        for stat in expired_debuff:
            del debuffs[stat]
        self.db.active_debuffs = debuffs

    def heal_self(self, min_hp, max_hp):
        """自我治療。"""
        import random
        amount = random.randint(int(min_hp), int(max_hp))
        current_hp = getattr(self.db, "hp", 0)
        max_hp_val = getattr(self.db, "max_hp", 100)
        actual = min(amount, max_hp_val - current_hp)
        self.db.hp = current_hp + actual
        self.msg(f"💚 你恢復了 {actual} 點 HP（目前 HP：{self.db.hp}/{max_hp_val}）。")
        return actual

    def get_final_stat(self, stat_name):
        """計算最終屬性（含 buff/debuff）。"""
        base = self.get_stat(stat_name)
        buff_bonus = self.get_buff_bonus(stat_name)
        debuff_penalty = self.get_debuff_penalty(stat_name)
        return base + buff_bonus - debuff_penalty