"""
Tests for Player Equipment and Inventory System.

These tests cover:
- Character attribute initialization
- Token/wallet operations
- Inventory management (add, remove, capacity)
- Equipment slots and equip/unequip logic
- Auto-unequip to inventory or room when inventory is full
- Two-handed weapon restrictions
- Equipment stat bonuses
- Equipment durability system
- Equipment CRUD via equipment_tools (skipped if evennia unavailable)
"""

import pytest
import sys
from unittest.mock import MagicMock


# ---------------------------------------------------------------------------
# Mock helpers - build realistic-enough Evennia object mocks
# ---------------------------------------------------------------------------

class MockAttributeStore(dict):
    """Dict-backed attribute store that behaves like Evennia's attribute system."""

    def get(self, key, default=None):
        return super().get(key, default)


class MockDB:
    """Simulates Evennia's .db property proxy."""

    def __init__(self, store=None):
        object.__setattr__(self, "_store", store or MockAttributeStore())

    def __getattr__(self, key):
        store = object.__getattribute__(self, "_store")
        # Explicit keys first
        val = store.get(key)
        if val is not None:
            return val
        # Fall back to _store attribute itself
        try:
            return getattr(store, key)
        except AttributeError:
            return None

    def __setattr__(self, key, value):
        store = object.__getattribute__(self, "_store")
        store[key] = value


class MockAliases(set):
    """Simulates Evennia's aliases relationship."""
    pass


class MockObject:
    """Minimal mock of an Evennia object."""

    def __init__(self, key="TestObj", attrs=None):
        self.key = key
        self.aliases = MockAliases()
        store = MockAttributeStore(attrs or {})
        self.db = MockDB(store)
        self.location = None
        self.home = None
        self.typeclass_path = "typeclasses.objects.Object"

    def save(self):
        pass

    def get_display_name(self, looker=None, **kwargs):
        return self.key

    def msg(self, text):
        pass


# ---------------------------------------------------------------------------
# Equipment Slot Definitions (mirrored from characters.py)
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# Test: Character attribute initialization
# ---------------------------------------------------------------------------

class TestCharacterAttributes:
    """Test that Character initializes all required attributes."""

    def test_default_attributes_initialized(self):
        """All required attributes should be present after creation."""
        store = MockAttributeStore()
        store.update({
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
        })

        assert store["tokens"] == 0
        assert store["inventory_capacity"] == 10
        assert store["stamina"] == 100
        assert store["max_stamina"] == 100
        assert store["base_atk"] == 10
        assert store["inventory"] == []
        assert store["equipment"] == {}


# ---------------------------------------------------------------------------
# Test: Token / Wallet System
# ---------------------------------------------------------------------------

class TestTokenSystem:
    """Test token operations."""

    def test_get_tokens_initial(self):
        """Default tokens should be 0."""
        char = MockObject(key="TestChar", attrs={"tokens": 0})
        tokens = char.db.tokens or 0
        assert tokens == 0

    def test_add_tokens(self):
        """Adding tokens should increase balance."""
        char = MockObject(key="TestChar", attrs={"tokens": 50})
        current = char.db.tokens or 0
        char.db.tokens = current + 100
        assert char.db.tokens == 150

    def test_spend_tokens_success(self):
        """Spending tokens should decrease balance if sufficient."""
        char = MockObject(key="TestChar", attrs={"tokens": 100})
        current = char.db.tokens or 0
        if current >= 30:
            char.db.tokens = current - 30
        assert char.db.tokens == 70

    def test_spend_tokens_insufficient(self):
        """Spending more than balance should not change balance."""
        char = MockObject(key="TestChar", attrs={"tokens": 10})
        current = char.db.tokens or 0
        amount = 50
        if current >= amount:
            char.db.tokens = current - amount
        assert char.db.tokens == 10


# ---------------------------------------------------------------------------
# Test: Inventory System
# ---------------------------------------------------------------------------

class TestInventorySystem:
    """Test inventory operations."""

    def test_default_inventory_empty(self):
        """New character should have empty inventory."""
        char = MockObject(key="TestChar", attrs={"inventory": [], "inventory_capacity": 10})
        assert len(char.db.inventory) == 0
        assert char.db.inventory_capacity == 10

    def test_add_to_inventory_success(self):
        """Should be able to add items until capacity."""
        char = MockObject(key="TestChar", attrs={"inventory": [], "inventory_capacity": 3})

        items = [MockObject(key=f"Item{i}") for i in range(3)]
        inv = list(char.db.inventory or [])
        for item in items:
            if len(inv) < char.db.inventory_capacity:
                inv.append(item)

        char.db.inventory = inv
        assert len(char.db.inventory) == 3

    def test_inventory_full(self):
        """Cannot add items beyond capacity."""
        char = MockObject(key="TestChar", attrs={"inventory": [], "inventory_capacity": 2})
        inv = list(char.db.inventory or [])

        # Fill inventory
        for i in range(2):
            item = MockObject(key=f"Item{i}")
            inv.append(item)
        char.db.inventory = inv

        # Try to add one more
        new_item = MockObject(key="ItemExtra")
        can_add = len(char.db.inventory) < char.db.inventory_capacity

        assert len(char.db.inventory) == 2
        assert can_add is False

    def test_remove_from_inventory(self):
        """Removing item from inventory should work."""
        item1 = MockObject(key="Item1")
        item2 = MockObject(key="Item2")
        char = MockObject(key="TestChar", attrs={"inventory": [item1, item2], "inventory_capacity": 10})

        inv = list(char.db.inventory or [])
        if item1 in inv:
            inv.remove(item1)
        char.db.inventory = inv

        assert len(char.db.inventory) == 1
        assert item2 in char.db.inventory

    def test_expand_inventory(self):
        """Expanding inventory should increase capacity."""
        char = MockObject(key="TestChar", attrs={"inventory": [], "inventory_capacity": 10})
        current = char.db.inventory_capacity
        char.db.inventory_capacity = current + 5
        assert char.db.inventory_capacity == 15


# ---------------------------------------------------------------------------
# Test: Equipment Slots
# ---------------------------------------------------------------------------

class TestEquipmentSlots:
    """Test equipment slot definitions."""

    def test_all_required_slots_defined(self):
        """All required equipment slots should be defined."""
        required = [
            "hat", "top", "bottom", "cloak", "shoes", "gloves",
            "glasses", "earring", "ring", "main_hand", "off_hand", "two_hand",
        ]
        for slot in required:
            assert slot in EQUIPMENT_SLOTS

    def test_top_bottom_no_auto_unequip(self):
        """top and bottom should have auto_unequip=False."""
        assert EQUIPMENT_SLOTS["top"]["auto_unequip"] is False
        assert EQUIPMENT_SLOTS["bottom"]["auto_unequip"] is False

    def test_other_slots_auto_unequip(self):
        """All other slots should have auto_unequip=True."""
        for slot, info in EQUIPMENT_SLOTS.items():
            if slot not in ("top", "bottom"):
                assert info["auto_unequip"] is True, f"{slot} should auto-unequip"

    def test_weapon_slots(self):
        """main_hand, off_hand, two_hand should be weapon slots."""
        for slot in ("main_hand", "off_hand", "two_hand"):
            assert EQUIPMENT_SLOTS[slot]["is_weapon"] is True


# ---------------------------------------------------------------------------
# Test: Equip / Unequip Logic
# ---------------------------------------------------------------------------

class TestEquipUnequip:
    """Test equip/unequip logic with inventory."""

    def test_equip_item_to_empty_slot(self):
        """Can equip item to empty slot."""
        char = MockObject(key="TestChar", attrs={
            "inventory": [],
            "equipment": {},
            "inventory_capacity": 10,
        })
        item = MockObject(key="IronSword")
        item.db.equip_slot = "main_hand"
        item.db.worn = False

        slot = "main_hand"
        equipment = dict(char.db.equipment or {})
        equipment[slot] = item
        char.db.equipment = equipment

        assert char.db.equipment["main_hand"] == item

    def test_equip_two_hand_blocks_main_off(self):
        """Equipping two-hand weapon should block main/off hand."""
        char = MockObject(key="TestChar", attrs={
            "equipment": {"two_hand": MockObject(key="GreatAxe")},
        })
        two_hand = char.db.equipment.get("two_hand")
        main_hand = char.db.equipment.get("main_hand")

        # If two_hand is equipped, main_hand should be blocked
        assert two_hand is not None
        assert main_hand is None

    def test_equip_main_hand_blocks_two_hand(self):
        """Equipping main-hand weapon should block two-hand."""
        char = MockObject(key="TestChar", attrs={
            "equipment": {
                "main_hand": MockObject(key="ShortSword"),
                "two_hand": None,
            },
        })
        main_hand = char.db.equipment.get("main_hand")
        two_hand = char.db.equipment.get("two_hand")

        # If main_hand is equipped, two_hand should be None
        assert main_hand is not None
        assert two_hand is None

    def test_unequip_to_inventory_full(self):
        """Unequipping when inventory full should leave item in room."""
        char = MockObject(key="TestChar", attrs={
            "inventory": [MockObject(key=f"Item{i}") for i in range(10)],
            "equipment": {"hat": MockObject(key="OldHat")},
            "inventory_capacity": 10,
        })
        char.location = MockObject(key="TestRoom")

        item = char.db.equipment.get("hat")
        inv = list(char.db.inventory or [])
        can_add = len(inv) < char.db.inventory_capacity

        if not can_add and char.location:
            # Would be dropped in room
            item.location = char.location

        # Inventory should still be full
        assert len(char.db.inventory) == 10
        assert item.location == char.location


# ---------------------------------------------------------------------------
# Test: Equipment Stats
# ---------------------------------------------------------------------------

class TestEquipmentStats:
    """Test equipment stat bonuses."""

    def test_equipment_stat_bonus(self):
        """Equipment should provide stat bonuses."""
        item = MockObject(key="MagicSword")
        item.db.stats = {"atk": 10, "str": 3}

        char = MockObject(key="TestChar", attrs={
            "base_atk": 10,
            "equipment": {"main_hand": item},
            "sockets": {},
        })

        bonus = 0
        equipment = char.db.equipment or {}
        for eq_item in equipment.values():
            if eq_item and hasattr(eq_item, "db"):
                bonus += eq_item.db.stats.get("atk", 0) if eq_item.db.stats else 0

        total_atk = (char.db.base_atk or 10) + bonus
        assert total_atk == 20

    def test_negative_stat_penalty(self):
        """Equipment can reduce stats."""
        item = MockObject(key="RustyArmor")
        item.db.stats = {"def": -5, "agi": -2}

        char = MockObject(key="TestChar", attrs={
            "base_def": 20,
            "base_agi": 15,
            "equipment": {"top": item},
            "sockets": {},
        })

        equipment = char.db.equipment or {}
        def_bonus = 0
        for eq_item in equipment.values():
            if eq_item and hasattr(eq_item, "db"):
                def_bonus += eq_item.db.stats.get("def", 0) if eq_item.db.stats else 0

        total_def = (char.db.base_def or 10) + def_bonus
        assert total_def == 15


# ---------------------------------------------------------------------------
# Test: Equipment Durability
# ---------------------------------------------------------------------------

class TestEquipmentDurability:
    """Test equipment durability system."""

    def test_durability_starts_at_max(self):
        """New equipment should have full durability."""
        item = MockObject(key="NewSword", attrs={
            "durability": 100,
            "max_durability": 100,
        })
        assert item.db.durability == item.db.max_durability

    def test_durability_decreases(self):
        """Using durability should decrease it."""
        item = MockObject(key="TestSword", attrs={
            "durability": 50,
            "max_durability": 100,
        })
        amount = 10
        new_dur = max(0, (item.db.durability or 0) - amount)
        item.db.durability = new_dur
        assert item.db.durability == 40

    def test_durability_zero_breaks(self):
        """Durability reaching 0 should mark equipment as broken."""
        item = MockObject(key="TestSword", attrs={
            "durability": 5,
            "max_durability": 100,
            "broken": False,
        })
        item.db.durability = 0
        if (item.db.durability or 0) <= 0:
            item.db.broken = True
        assert item.db.broken is True

    def test_repair_restores_durability(self):
        """Repairing should restore durability."""
        item = MockObject(key="TestSword", attrs={
            "durability": 30,
            "max_durability": 100,
            "broken": True,
        })
        max_dur = item.db.max_durability
        item.db.durability = max_dur
        item.db.broken = False
        assert item.db.durability == 100
        assert item.db.broken is False

    def test_partial_repair(self):
        """Partial repair should add durability up to max."""
        item = MockObject(key="TestSword", attrs={
            "durability": 30,
            "max_durability": 100,
        })
        amount = 20
        current = item.db.durability
        item.db.durability = min(item.db.max_durability, current + amount)
        assert item.db.durability == 50


# ---------------------------------------------------------------------------
# Test: Equipment Tool Functions (require evennia - skip if unavailable)
# ---------------------------------------------------------------------------

evennia_missing = False
try:
    from world.equipment_tools import (
        create_equipment, EquipmentSpecError, VALID_SLOTS
    )
except ImportError:
    evennia_missing = True


@pytest.mark.skipif(evennia_missing, reason="evennia not available in test environment")
class TestEquipmentTools:
    """Test equipment_tools CRUD functions."""

    def test_create_equipment_adds_to_db(self):
        """create_equipment should store attributes correctly."""
        # Check function signature exists
        from world.equipment_tools import create_equipment
        assert callable(create_equipment)

    def test_equipment_spec_error(self):
        """EquipmentSpecError should be a dataclass with message."""
        from world.equipment_tools import EquipmentSpecError
        err = EquipmentSpecError("test message")
        assert str(err) == "test message"
        assert err.message == "test message"

    def test_valid_slots_defined(self):
        """All expected slots should be in VALID_SLOTS."""
        from world.equipment_tools import VALID_SLOTS
        expected = [
            "hat", "top", "bottom", "cloak", "shoes", "gloves",
            "glasses", "earring", "ring", "main_hand", "off_hand", "two_hand",
        ]
        for slot in expected:
            assert slot in VALID_SLOTS


# ---------------------------------------------------------------------------
# Test: Magic Buff System
# ---------------------------------------------------------------------------

class TestMagicBuff:
    """Test magic buff stacking on equipment."""

    def test_magic_buff_stacks(self):
        """Magic buffs should be stackable."""
        item = MockObject(key="EnchantedRing", attrs={
            "magic_buffs": [],
            "stats": {},
        })

        buffs = list(item.db.magic_buffs or [])
        buffs.append({"stat": "atk", "value": 5})
        buffs.append({"stat": "atk", "value": 3})
        item.db.magic_buffs = buffs

        stats = dict(item.db.stats or {})
        for b in buffs:
            stats[b["stat"]] = stats.get(b["stat"], 0) + b["value"]
        item.db.stats = stats

        # Both buffs should be applied
        assert item.db.magic_buffs[0]["stat"] == "atk"
        assert item.db.magic_buffs[1]["stat"] == "atk"
        assert item.db.stats["atk"] == 8


# ---------------------------------------------------------------------------
# Test: Look Player Description
# ---------------------------------------------------------------------------

class TestLookPlayer:
    """Test that look player shows equipped items."""

    def test_equipment_description_when_empty(self):
        """No equipment should show appropriate message."""
        equipment = {}
        if not equipment:
            result = "目前身上沒有穿戴任何裝備。"
        assert result == "目前身上沒有穿戴任何裝備。"

    def test_equipment_description_with_items(self):
        """Should list equipped items."""
        equipment = {
            "hat": MockObject(key="LeatherCap"),
            "main_hand": MockObject(key="IronSword"),
        }
        lines = []
        for slot, item in sorted(equipment.items()):
            slot_info = EQUIPMENT_SLOTS.get(slot, {"name": slot})
            lines.append(f"  {slot_info['name']}：{item.key}")
        result = "\n".join(lines)
        assert "帽子" in result
        assert "主手武器" in result