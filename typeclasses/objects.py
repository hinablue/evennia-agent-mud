"""物件

物件是遊戲世界中一般物品的類別。

使用 ObjectParent 類別實作*所有*實體的通用功能
具有遊戲世界中的位置（如角色、房間、出口）。"""

from collections import defaultdict

from evennia.objects.objects import DefaultObject
from evennia.contrib.rpg.rpsystem import ContribRPObject


def _zh_join(items):
    items = [str(item) for item in items if item]
    return "、".join(items)


class ObjectParent:
    """這是一個 mixin，可用來覆寫繼承於的*所有*實體
    與預設物件（物件、出口、角色和房間）有一段距離。

    只需將 `DefaultObject` 上存在的任何方法添加到此類即可。如果有一個
    衍生類別本身已經定義了相同的鉤子，這將
    優先。"""

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
    """這是根物件類型類，代表所有實體
    在遊戲中實際存在。預設物件通常有一個
    位置。它們也可以被操縱和觀察。遊戲
    您定義的實體應該在一定距離處從 DefaultObject 繼承。

    建議使用以下方法建立此類別的子級
    `evennia.create_object()` 函數而非初始化類
    直接 - 這將既設置好東西又有效地保存對象
    無需明確調用 `obj.save()` 。

    注意：檢查自動文件以獲取完整的類別成員，這可能並不總是
    保持最新狀態。"""

    default_description = "你看不出什麼特別之處。"
