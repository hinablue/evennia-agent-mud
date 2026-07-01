"""Live smoke probe for persistent Gem socket references."""

from evennia import create_object

from commands.combat_socket import CmdSocketGem
from typeclasses.characters import Character
from world.gem_tools import bootstrap_default_gems, create_gem, delete_gem, update_gem


def main():
    """Run the Gem socket smoke probe."""
    created = bootstrap_default_gems()
    print("BOOTSTRAP", [gem.db.gem_id for gem in created])
    char = create_object(Character, key="__gem_probe_char__", location=None, home=None)
    char.msg = lambda text: print("MSG", text)
    temp_id = "probegem"
    try:
        try:
            delete_gem(temp_id)
        except Exception:
            pass
        gem = create_gem(temp_id, "測試寶石", {"str": 2})["gem"]
        cmd = object.__new__(CmdSocketGem)
        setattr(cmd, "caller", char)
        setattr(cmd, "args", f"{temp_id} 1")
        cmd.func()
        stored = char.db.sockets["slot1"]
        print("STORED_REF", stored.id == gem.id, stored.db.gem_id)
        print("STAT_BEFORE", char.get_stat("str"))
        update_gem(temp_id, stats={"str": 7})
        print("STAT_AFTER", char.get_stat("str"))
    finally:
        try:
            delete_gem(temp_id)
        except Exception as err:
            print("DELETE_TEMP_ERR", err)
        char.delete()


main()
