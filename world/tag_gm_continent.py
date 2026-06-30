"""用於標記所有現有 GM 大陸物件的一次性遷移腳本。

部署新的權限層次結構後執行一次。
使用「gm_Continental」所有權標籤標記所有現有房間、出口和物件。"""

from evennia import search_object
from evennia.objects.models import ObjectDB
from evennia.utils.utils import inherits_from


def tag_gm_continent():
    """將所有現有物件標記為 GM 大陸資產。

    這假設資料庫中目前的所有內容都屬於通用汽車大陸。
    未來 King 創建的物件將被貼上不同的標籤。"""
    # 取得資料庫中所有對象
    all_objects = ObjectDB.objects.all()

    tagged_count = 0
    for obj in all_objects:
        # 如果已標記則跳過
        if obj.tags.has("gm_continent", category="ownership"):
            continue

        # 標記它
        obj.tags.add("gm_continent", category="ownership")
        tagged_count += 1

        # 如果它們連接到將要連接的內容，則也使用 gm_link_exit 標記退出
        # 特大號床入口房間（但我們還不知道這些 - 將被標記
        # 當GM創建國王入口房間時手動）

    print(f"Tagged {tagged_count} objects with gm_continent ownership tag.")
    return tagged_count


def tag_specific_rooms_as_gm_continent(room_names):
    """將特定房間標記為 GM 大陸（用於選擇性標記）。"""
    for name in room_names:
        matches = search_object(name, exact=True)
        if matches:
            room = matches[0]
            room.tags.add("gm_continent", category="ownership")
            print(f"Tagged room: {room.key} (id={room.id})")
        else:
            print(f"Room not found: {name}")


def tag_gm_link_exits(exit_names):
    """將特定出口標記為 GM 連結出口（連接到 King 入口）。"""
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
