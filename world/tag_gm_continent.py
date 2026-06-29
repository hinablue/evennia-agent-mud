"""One-time migration script to tag all existing GM continent objects.

Run this once after deploying the new permission hierarchy.
Tags all existing rooms, exits, and objects with 'gm_continent' ownership tag.
"""

from evennia import search_object
from evennia.objects.models import ObjectDB
from evennia.utils.utils import inherits_from


def tag_gm_continent():
    """Tag all existing objects as GM continent assets.

    This assumes everything currently in the database belongs to GM continent.
    Future King-created objects will be tagged differently.
    """
    # Get all objects in the database
    all_objects = ObjectDB.objects.all()

    tagged_count = 0
    for obj in all_objects:
        # Skip if already tagged
        if obj.tags.has("gm_continent", category="ownership"):
            continue

        # Tag it
        obj.tags.add("gm_continent", category="ownership")
        tagged_count += 1

        # Also tag exits with gm_link_exit if they connect to what will be
        # King entrance rooms (but we don't know those yet - will be tagged
        # manually when GM creates King entrance rooms)

    print(f"Tagged {tagged_count} objects with gm_continent ownership tag.")
    return tagged_count


def tag_specific_rooms_as_gm_continent(room_names):
    """Tag specific rooms as GM continent (for selective tagging)."""
    for name in room_names:
        matches = search_object(name, exact=True)
        if matches:
            room = matches[0]
            room.tags.add("gm_continent", category="ownership")
            print(f"Tagged room: {room.key} (id={room.id})")
        else:
            print(f"Room not found: {name}")


def tag_gm_link_exits(exit_names):
    """Tag specific exits as GM link exits (connecting to King entrance)."""
    for name in exit_names:
        matches = search_object(name, exact=True)
        if matches:
            exit_obj = matches[0]
            exit_obj.tags.add("gm_link_exit", category="ownership")
            exit_obj.tags.add("gm_continent", category="ownership")
            print(f"Tagged exit: {exit_obj.key} (id={exit_obj.id})")
        else:
            print(f"Exit not found: {name}")


if __name__ == "__main__":
    tag_gm_continent()
