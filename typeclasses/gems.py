"""寶石 typeclass。

此模組提供可由管理者持久化維護的 Gem 物件。Gem 本身是 Evennia
Object，因此可以被 Attribute 儲存為物件 reference，讓已鑲嵌的 socket
在管理者調整寶石數值後即時讀取最新屬性。
"""

from evennia.objects.objects import DefaultObject
from typeclasses.objects import ObjectParent


class Gem(ObjectParent, DefaultObject):
    """可鑲嵌寶石。

    Attributes:
        gem_id: 管理與玩家指令使用的穩定 ID，例如 ``ruby``。
        display_name: 玩家看到的名稱，例如 ``紅寶石``。
        stats: 屬性加成 dict，例如 ``{"str": 3}``。
        enabled: 是否可被玩家鑲嵌。
        rarity: 稀有度標籤。
        desc: 說明文字。
    """

    default_description = "這是一顆可以鑲嵌的寶石。"

    def at_object_creation(self):
        """初始化 Gem 的預設屬性。"""
        super().at_object_creation()
        defaults = {
            "gem_id": None,
            "display_name": "",
            "stats": {},
            "enabled": True,
            "rarity": "common",
            "desc": self.default_description,
            "is_gem": True,
        }
        for key, value in defaults.items():
            if self.attributes.get(key) is None:
                self.attributes.add(key, value)

    def get_display_name(self, looker=None, **kwargs):
        """回傳寶石顯示名稱。"""
        return getattr(self.db, "display_name", None) or self.key
