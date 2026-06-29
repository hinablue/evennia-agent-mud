from typeclasses.objects import Object

class DoorObject(Object):
    """
    A specialized object that acts as a door between rooms.
    Attributes:
    - db.direction: The direction this door controls (e.g. 'north')
    - db.state: Current state ('open', 'closed', or 'locked')
    - db.locked_by: Key required to unlock (optional)
    """
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
