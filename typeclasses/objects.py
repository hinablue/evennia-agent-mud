"""
Object

The Object is the class for general items in the game world.

Use the ObjectParent class to implement common features for *all* entities
with a location in the game world (like Characters, Rooms, Exits).

"""

from collections import defaultdict

from evennia.objects.objects import DefaultObject
from evennia.contrib.rpg.rpsystem import ContribRPObject


def _zh_join(items):
    items = [str(item) for item in items if item]
    return "、".join(items)


class ObjectParent:
    """
    This is a mixin that can be used to override *all* entities inheriting at
    some distance from DefaultObject (Objects, Exits, Characters and Rooms).

    Just add any method that exists on `DefaultObject` to this class. If one
    of the derived classes has itself defined that same hook already, that will
    take precedence.

    """

    def get_numbered_name(self, count, looker, **kwargs):
        """以較自然的中文形式顯示物件數量。"""
        key = str(kwargs.get("key", self.get_display_name(looker, **kwargs)))
        plural = f"{count} 個{key}"

        if kwargs.get("no_article") and count == 1:
            if kwargs.get("return_string"):
                return key
            return key, key

        if kwargs.get("return_string"):
            return key if count == 1 else plural

        return key, plural

    def get_display_exits(self, looker, **kwargs):
        exits = self.filter_visible(
            self.contents_get(content_type="exit"), looker, **kwargs
        )
        exit_names = sorted(exi.get_display_name(looker, **kwargs) for exi in exits)
        exit_names = _zh_join(exit_names)
        return f"|w出口：|n {exit_names}" if exit_names else ""

    def get_display_characters(self, looker, **kwargs):
        characters = self.filter_visible(
            self.contents_get(content_type="character"), looker, **kwargs
        )
        character_names = _zh_join(
            char.get_display_name(looker, **kwargs) for char in characters
        )
        return f"|w這裡的人：|n {character_names}" if character_names else ""

    def get_display_things(self, looker, **kwargs):
        things = self.filter_visible(
            self.contents_get(content_type="object"), looker, **kwargs
        )

        grouped_things = defaultdict(list)
        for thing in things:
            grouped_things[thing.get_display_name(looker, **kwargs)].append(thing)

        thing_names = []
        for thingname, thinglist in sorted(grouped_things.items()):
            nthings = len(thinglist)
            thing = thinglist[0]
            singular, plural = thing.get_numbered_name(nthings, looker, key=thingname)
            thing_names.append(singular if nthings == 1 else plural)

        thing_names = _zh_join(thing_names)
        return f"|w你看見：|n {thing_names}" if thing_names else ""


class Object(ObjectParent, ContribRPObject):
    """
    This is the root Object typeclass, representing all entities that
    have an actual presence in-game. DefaultObjects generally have a
    location. They can also be manipulated and looked at. Game
    entities you define should inherit from DefaultObject at some distance.

    It is recommended to create children of this class using the
    `evennia.create_object()` function rather than to initialize the class
    directly - this will both set things up and efficiently save the object
    without `obj.save()` having to be called explicitly.

    Note: Check the autodocs for complete class members, this may not always
    be up-to date.
    """

    default_description = "你看不出什麼特別之處。"
