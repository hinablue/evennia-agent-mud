"""退出

出口是房間之間的連接器。出口始終具有目標屬性
set 並在其自身上定義了一個與其鍵同名的命令，
用於允許角色穿過出口到達目的地。"""

from evennia.objects.objects import DefaultExit

from .objects import ObjectParent


class Exit(ObjectParent, DefaultExit):
    """出口是房間之間的連接器。出口是普通對象，除了
    他們定義了 `destination` 屬性並覆蓋了一些鉤子
    以及表示出口的方法。

    有關列表，請參閱 mygame/typeclasses/objects.py
    像這樣的所有物件子類別都可用的屬性和方法。"""

    default_description = "這是一條可通行的出口。"
