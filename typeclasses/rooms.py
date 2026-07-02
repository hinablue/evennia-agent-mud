"""房間

房間是簡單的容器，沒有自己的位置。"""

from evennia.contrib.grid.extended_room import ExtendedRoom

from .objects import ObjectParent


class Room(ObjectParent, ExtendedRoom):
    """房間就像任何物件一樣，只是它們的位置是“無”
    （這是預設的）。他們也使用 basetype_setup() 來
    添加鎖，這樣它們就不會被操縱或拾取。
    （若要改變這一點，請使用 at_object_creation 來取代）

    有關列表，請參閱 mygame/typeclasses/objects.py
    所有物件都可用的屬性和方法。"""

    fallback_desc = "這裡暫時還沒有描述。"
