"""Kingdom (國家) script and tools for GM/King/Player hierarchy."""

from evennia import DefaultScript, create_object, search_object
from evennia.utils.utils import inherits_from
from typeclasses.rooms import Room
from typeclasses.exits import Exit


class Kingdom(DefaultScript):
    """
    國家腳本，掛在 King Character 上（或獨立 GlobalScript 以 key 索引）。
    key = 國名（唯一）
    """

    def at_script_creation(self):
        self.key = ""  # 國名
        self.db.king = None  # Character (King)
        self.db.gm_continent_rooms = []  # GM 大陸上連結到此國的房間 dbref 清單
        self.db.entrance_room = None  # King 的第一個房間（Home，GM 指定）
        self.db.room_quota = 0  # GM 分配的空房間額度
        self.db.rooms_created = 0  # 已建立房間數
        self.db.nationality_tag = ""  # 國籍標籤，供 Player 打標用（如 "Astra"）

    def get_quota_remaining(self):
        """剩餘可建房間額度"""
        return max(0, self.db.room_quota - self.db.rooms_created)

    def can_create_room(self):
        """是否還能建房"""
        return self.get_quota_remaining() > 0

    def increment_rooms_created(self):
        """建房計數 +1"""
        self.db.rooms_created += 1

    def decrement_rooms_created(self):
        """刪房計數 -1"""
        self.db.rooms_created = max(0, self.db.rooms_created - 1)

    def set_king(self, king_char):
        """設定國王"""
        self.db.king = king_char
        king_char.db.is_king = True
        king_char.db.kingdom = self
        king_char.save()

    def set_entrance_room(self, room):
        """設定入口房間"""
        self.db.entrance_room = room
        # 打標
        room.tags.add("king_entrance", category="ownership")
        room.tags.add(f"kingdom:{self.key}", category="ownership")
        room.save()

    def add_gm_continent_room(self, room):
        """記錄 GM 大陸連結房間"""
        if room.id not in self.db.gm_continent_rooms:
            self.db.gm_continent_rooms.append(room.id)

    def change_name(self, new_name):
        """變更國名，同步更新所有標籤與 Player 國籍"""
        old_key = self.key
        self.key = new_name
        self.db.nationality_tag = new_name
        self.save()

        # 更新 King 的 kingdom 參照
        if self.db.king:
            self.db.king.db.kingdom = self
            self.db.king.save()

        # 更新所有自國物件的 kingdom: tag
        from evennia.objects.models import ObjectDB

        for obj in ObjectDB.objects.all():
            for tag in obj.tags.all(category="ownership"):
                if tag.key == f"kingdom:{old_key}":
                    obj.tags.remove(tag, category="ownership")
                    obj.tags.add(f"kingdom:{new_name}", category="ownership")

        # 更新所有該國 Player 的 nationality
        from typeclasses.characters import Character

        for player in Character.objects.filter(db_nationality=old_key):
            player.db.nationality = new_name
            player.save()

    def delete(self):
        """刪除國家時的清理"""
        # 可選：解除 King 的 is_king、kingdom
        if self.db.king:
            self.db.king.db.is_king = False
            self.db.king.db.kingdom = None
            self.db.king.save()
        super().delete()


# --- Kingdom Tools (供指令呼叫) ---


def create_kingdom(king_char, kingdom_name, entrance_room, room_quota):
    """
    GM 建立新國家：
    - 建立 Kingdom script 掛在 King character 上
    - 設定 King 的 is_king、kingdom
    - 設定 entrance_room 並打標
    - 設定 King 的 home = entrance_room
    """
    if not inherits_from(king_char, "typeclasses.characters.Character"):
        raise ValueError("king_char 必須是 Character")

    # 檢查國名唯一
    existing = search_object(kingdom_name, typeclass="world.kingdom.Kingdom")
    if existing:
        raise ValueError(f"國名已存在：{kingdom_name}")

    kingdom = create_object(Kingdom, key=kingdom_name)
    kingdom.set_king(king_char)
    kingdom.set_entrance_room(entrance_room)
    kingdom.db.room_quota = room_quota
    kingdom.db.nationality_tag = kingdom_name
    kingdom.save()

    # King 設定 home
    king_char.home = entrance_room
    king_char.save()

    return kingdom


def get_kingdom_by_name(name):
    """依國名查找 Kingdom script"""
    matches = search_object(name, typeclass="world.kingdom.Kingdom")
    return matches[0] if matches else None


def get_kingdom_by_king(king_char):
    """依 King character 查找 Kingdom"""
    return getattr(king_char.db, "kingdom", None)


def create_kingdom_channels(kingdom_key, king_char):
    """建國時自動建立該國公共頻道，並讓 King 自動訂閱"""
    from evennia.comms.models import ChannelDB
    from evennia.utils import create

    chan_name = f"kingdom:{kingdom_key}"
    # 避免重複
    existing = ChannelDB.objects.filter(db_key=chan_name).first()
    if existing:
        existing.connect(king_char)
        return existing

    chan = create.create_channel(
        chan_name,
        locks=f"listen:is_same_kingdom();send:is_same_kingdom()",
        desc=f"{kingdom_key} 國公共頻道",
    )
    chan.connect(king_char)
    return chan
