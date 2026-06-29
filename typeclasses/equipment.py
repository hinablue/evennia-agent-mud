"""
Equipment - Weapons, armor, and accessories for the game.

This module provides the Equipment typeclass, which represents
wearable items, weapons, and accessories that players can equip.
"""

from evennia.objects.objects import DefaultObject
from typeclasses.objects import ObjectParent


class Equipment(ObjectParent, DefaultObject):
    """
    Equipment is an item that can be equipped by a Character.
    It has stats, durability, magic slots, and can be worn in
    specific equipment slots.
    """

    default_description = "這是一件普通的裝備。"

    # Equipment slot constants
    SLOT_HAT = "hat"
    SLOT_TOP = "top"
    SLOT_BOTTOM = "bottom"
    SLOT_CLOAK = "cloak"
    SLOT_SHOES = "shoes"
    SLOT_GLOVES = "gloves"
    SLOT_GLASSES = "glasses"
    SLOT_EARRING = "earring"
    SLOT_RING = "ring"
    SLOT_MAIN_HAND = "main_hand"
    SLOT_OFF_HAND = "off_hand"
    SLOT_TWO_HAND = "two_hand"

    VALID_SLOTS = (
        SLOT_HAT,
        SLOT_TOP,
        SLOT_BOTTOM,
        SLOT_CLOAK,
        SLOT_SHOES,
        SLOT_GLOVES,
        SLOT_GLASSES,
        SLOT_EARRING,
        SLOT_RING,
        SLOT_MAIN_HAND,
        SLOT_OFF_HAND,
        SLOT_TWO_HAND,
    )

    # Valid stat names that equipment can modify
    VALID_STATS = (
        "str",
        "def",
        "intel",
        "agi",
        "spirit",
        "stamina",
        "spd",
        "atk",
        "hp",
        "mp",
        "max_hp",
        "max_mp",
    )

    def at_object_creation(self):
        """Initialize default equipment attributes."""
        super().at_object_creation()

        defaults = {
            "equip_slot": None,
            "stats": {},
            "max_durability": 100,
            "durability": 100,
            "two_handed": False,
            "magic_buffs": [],
            "wear_style": "",
            "is_equipment": True,
        }
        for key, value in defaults.items():
            if self.attributes.get(key) is None:
                self.attributes.add(key, value)

    def get_display_name(self, looker=None, **kwargs):
        """Return the display name with alias if set."""
        alias = getattr(self.db, "player_alias", None)
        if alias:
            return f"{self.key}（{alias}）"
        return self.key

    def get_stats_description(self):
        """Return a human-readable description of stat modifiers."""
        stats = getattr(self.db, "stats", {}) or {}
        if not stats:
            return ""
        parts = []
        for stat, value in sorted(stats.items()):
            if value == 0:
                continue
            sign = "+" if value > 0 else ""
            parts.append(f"{sign}{value} {stat}")
        return ", ".join(parts) if parts else ""

    def get_durability_status(self):
        """Return durability as a percentage and display string."""
        max_dur = getattr(self.db, "max_durability", 100) or 100
        dur = getattr(self.db, "durability", 100) or 100
        pct = int((dur / max_dur) * 100) if max_dur > 0 else 0
        return pct, f"{dur}/{max_dur}"

    def use_durability(self, amount=1):
        """Reduce durability by amount. Returns True if still usable."""
        dur = getattr(self.db, "durability", 100) or 100
        max_dur = getattr(self.db, "max_durability", 100) or 100
        dur = max(0, dur - amount)
        self.db.durability = dur

        if dur <= 0:
            self.db.broken = True
            return False
        return True

    def repair(self, amount=None):
        """Repair durability. If amount is None, fully restore."""
        max_dur = getattr(self.db, "max_durability", 100) or 100
        if amount is None:
            self.db.durability = max_dur
        else:
            current = getattr(self.db, "durability", 0) or 0
            self.db.durability = min(max_dur, current + amount)
        self.db.broken = False

    def add_magic_buff(self, buff_stat, buff_value):
        """Add a magic buff to the equipment."""
        buffs = getattr(self.db, "magic_buffs", []) or []
        buffs.append({"stat": buff_stat, "value": buff_value})
        self.db.magic_buffs = buffs

        # Apply to stats
        stats = getattr(self.db, "stats", {}) or {}
        stats[buff_stat] = stats.get(buff_stat, 0) + buff_value
        self.db.stats = stats

    def get_magic_buffs_description(self):
        """Return description of magic buffs."""
        buffs = getattr(self.db, "magic_buffs", []) or []
        if not buffs:
            return ""
        parts = []
        for buff in buffs:
            sign = "+" if buff["value"] > 0 else ""
            parts.append(f"魔法+ {sign}{buff['value']} {buff['stat']}")
        return ", ".join(parts)

    def get_full_description(self, looker=None):
        """Return full description including stats and durability."""
        lines = []
        lines.append(f"名稱：{self.get_display_name(looker)}")

        alias = getattr(self.db, "player_alias", None)
        if alias:
            lines.append(f"暱稱：{alias}")

        desc = getattr(self.db, "desc", "") or "無描述"
        lines.append(f"描述：{desc}")

        slot = getattr(self.db, "equip_slot", None)
        if slot:
            lines.append(f"裝備槽：{slot}")

        two_hand = getattr(self.db, "two_handed", False)
        if two_hand:
            lines.append("雙手武器：是")

        stats_desc = self.get_stats_description()
        if stats_desc:
            lines.append(f"屬性：{stats_desc}")

        magic_desc = self.get_magic_buffs_description()
        if magic_desc:
            lines.append(f"魔法：{magic_desc}")

        pct, dur_str = self.get_durability_status()
        lines.append(f"耐用度：{dur_str} ({pct}%)")

        broken = getattr(self.db, "broken", False)
        if broken:
            lines.append("狀態：已損壞（無法使用）")

        return "\n".join(lines)
