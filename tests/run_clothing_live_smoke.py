"""Live smoke for local clothing/equipment integration."""

from evennia import create_object
from evennia.objects.models import ObjectDB

from typeclasses.characters import Character, get_worn_equipment
from typeclasses.equipment import Equipment
from typeclasses.npcs import LLMNPC, NPC


def _first_room():
    room = (
        ObjectDB.objects.filter(db_typeclass_path__contains="rooms")
        .order_by("id")
        .first()
    )
    if not room:
        room = ObjectDB.objects.filter(db_key="Limbo").first()
    return room


def main():
    room = _first_room()
    created = []
    char = hat = cloak = sword = npc = npc_hat = llm_npc = llm_hat = None
    try:
        char = create_object(
            Character, key="__clothing_smoke_char", location=room, home=room
        )
        created.append(char)
        char.db.inventory = []
        char.db.inventory_capacity = 10
        char.db.equipment = {}
        char.db.desc = "煙測角色。"

        hat = create_object(
            Equipment,
            key="__clothing_smoke_hat",
            location=char,
            home=room,
            attributes=[
                ("equip_slot", "hat"),
                ("clothing_type", "hat"),
                ("is_equipment", True),
                ("stats", {"def": 2}),
                ("wear_style", ""),
                ("worn", False),
                ("covered_by", None),
            ],
        )
        cloak = create_object(
            Equipment,
            key="__clothing_smoke_cloak",
            location=char,
            home=room,
            attributes=[
                ("equip_slot", "cloak"),
                ("clothing_type", "cloak"),
                ("is_equipment", True),
                ("stats", {}),
                ("wear_style", ""),
                ("worn", False),
                ("covered_by", None),
            ],
        )
        sword = create_object(
            Equipment,
            key="__clothing_smoke_sword",
            location=char,
            home=room,
            attributes=[
                ("equip_slot", "main_hand"),
                ("clothing_type", "main_hand"),
                ("is_equipment", True),
                ("stats", {"atk": 5}),
                ("wear_style", ""),
                ("worn", False),
                ("covered_by", None),
            ],
        )
        created.extend([hat, cloak, sword])
        char.db.inventory = [hat, cloak, sword]

        assert char.equip_item(hat, wear_style="斜斜地戴著", quiet=True)
        assert hat not in char.get_inventory(), "equipped item should leave inventory"
        assert char.get_equipped("hat") == hat
        assert hat.db.worn == "斜斜地戴著"
        assert "斜斜地戴著" in char.get_display_desc(char)

        assert char.equip_item(cloak, quiet=True)
        hat.db.covered_by = cloak
        visible = get_worn_equipment(char, exclude_covered=True)
        assert hat not in visible and cloak in visible, "covered item should be hidden"
        assert not char.unequip_item(hat, quiet=True), "covered item should not unequip"
        assert char.unequip_item(cloak, quiet=True), "removing cover should work"
        assert hat.db.covered_by is None, "removing cover should reveal covered item"

        assert char.equip_item(sword, quiet=True)
        assert char.get_stat("atk") == 15, "equipment stat bonus should apply"
        assert char.unequip_item("hat", quiet=True)
        assert hat in char.get_inventory(), "unequipped item should return to inventory"

        npc = create_object(NPC, key="__clothing_smoke_npc", location=room, home=room)
        created.append(npc)
        npc.db.inventory = []
        npc.db.inventory_capacity = 10
        npc.db.equipment = {}
        npc_hat = create_object(
            Equipment,
            key="__clothing_smoke_npc_hat",
            location=npc,
            home=room,
            attributes=[
                ("equip_slot", "hat"),
                ("clothing_type", "hat"),
                ("is_equipment", True),
                ("stats", {"def": 3}),
                ("wear_style", ""),
                ("worn", False),
                ("covered_by", None),
            ],
        )
        created.append(npc_hat)
        npc.db.inventory = [npc_hat]
        assert npc.equip_item(npc_hat, wear_style="端正地戴著", quiet=True)
        assert (
            npc_hat not in npc.get_inventory()
        ), "NPC equipped item should leave inventory"
        assert npc.get_equipped("hat") == npc_hat
        assert "端正地戴著" in npc.get_display_desc(char)

        llm_npc = create_object(
            LLMNPC, key="__clothing_smoke_llm", location=room, home=room
        )
        created.append(llm_npc)
        llm_npc.db.inventory = []
        llm_npc.db.inventory_capacity = 10
        llm_npc.db.equipment = {}
        llm_hat = create_object(
            Equipment,
            key="__clothing_smoke_llm_hat",
            location=llm_npc,
            home=room,
            attributes=[
                ("equip_slot", "hat"),
                ("clothing_type", "hat"),
                ("is_equipment", True),
                ("stats", {"def": 1}),
                ("wear_style", ""),
                ("worn", False),
                ("covered_by", None),
            ],
        )
        created.append(llm_hat)
        llm_npc.db.inventory = [llm_hat]
        assert llm_npc.equip_item(llm_hat, quiet=True)
        assert llm_npc.get_equipped("hat") == llm_hat
        assert hasattr(llm_npc, "build_messages")

        print("CLOTHING_SMOKE_OK")
        print("equipment_slots", sorted(char.get_all_equipped().keys()))
        print("inventory", [obj.key for obj in char.get_inventory()])
    finally:
        for obj in reversed(created):
            try:
                obj.delete()
            except Exception:
                pass


main()
