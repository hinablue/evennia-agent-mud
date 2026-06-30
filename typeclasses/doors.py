from typeclasses.objects import Object


class DoorObject(Object):
    """充當房間之間門的特殊物體。
    屬性：
    - db.direction：此門控制的方向（例如“北”）
    - db.state：目前狀態（「開啟」、「關閉」或「鎖定」）
    - db.locked_by：解鎖所需的金鑰（可選）"""

    def at_object_creation(self):
        self.db.direction = "north"
        self.db.state = "closed"
        self.db.locked_by = None

    def cmd_open(self):
        if self.db.state == "locked":
            return "The door is locked. You need a key."
        self.db.state = "open"
        return "You open the door."

    def cmd_close(self):
        self.db.state = "closed"
        return "You close the door."

    def cmd_lock(self):
        self.db.state = "locked"
        return "You lock the door."

    def cmd_unlock(self, key_obj=None):
        if key_obj and self.db.locked_by == key_obj:
            self.db.state = "closed"
            return "You unlock the door."
        return "The key doesn't fit or you have no key."
