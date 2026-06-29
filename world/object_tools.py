
"""Admin helpers for managing game Objects."""

from evennia import create_object, search_object
from evennia.utils.utils import make_iter
from dataclasses import dataclass

@dataclass
class ObjectSpecError(ValueError):
    message: str
    def __str__(self):
        return self.message

def _clean_text_safe(value):
    return (value or "").strip()

def _find_exact_object(key):
    key = _clean_text_safe(key)
    if not key:
        return None
    matches = search_object(key, exact=True)
    return matches[0] if matches else None

def _get_room_or_error(room_name):
    room_name = _clean_text_safe(room_name)
    if not room_name:
        raise ObjectSpecError("請提供房間名稱。")
    room = _find_exact_object(room_name)
    if not room:
        raise ObjectSpecError(f"房間不存在：{room_name}")
    if not room.typeclass_path.startswith("typeclasses.rooms"):
        raise ObjectSpecError(f"`{room_name}` 不是房間。")
    return room

def _get_object_or_error(obj_key):
    obj_key = _clean_text_safe(obj_key)
    if not obj_key:
        raise ObjectSpecError("請提供物件名稱。")
    obj = _find_exact_object(obj_key)
    if not obj:
        raise ObjectSpecError(f"找不到物件：{obj_key}")
    return obj

def _get_player_or_error(char_key):
    char_key = _clean_text_safe(char_key)
    if not char_key:
        raise ObjectSpecError("請提供角色名稱。")
    obj = _find_exact_object(char_key)
    if not obj:
        raise ObjectSpecError(f"找不到角色：{char_key}")
    return obj

def summarize_object(obj_key):
    obj = _get_object_or_error(obj_key)
    location = getattr(obj, "location", None)
    loc_name = getattr(location, "key", "無") if location else "無"
    desc = getattr(obj.db, "desc", "無") or "無"
    aliases = list(obj.aliases.all()) if hasattr(obj, "aliases") else []
    
    lines = [f"Object：{obj.key}"]
    lines.append(f"- 位置：{loc_name}")
    lines.append(f"- 描述：{desc}")
    lines.append(f"- Aliases：{', '.join(aliases) if aliases else '無'}")
    lines.append(f"- Typeclass：{obj.typeclass_path}")
    lines.append(f"- 可拿取：{'是' if getattr(obj.db, 'takeable', True) else '否'}")
    lines.append(f"- 可裝備：{'是' if getattr(obj.db, 'equippable', False) else '否'}")
    return "\n".join(lines)

def list_objects(room_name=None):
    from evennia.objects.models import ObjectDB
    if room_name:
        room = _get_room_or_error(room_name)
        objects = [obj for obj in ObjectDB.objects.all() if obj.location == room]
    else:
        objects = ObjectDB.objects.all()
    
    if not objects:
        return "目前沒有找到任何物件。"
    
    title = f"物件清單：{room_name}" if room_name else "物件清單：全世界"
    lines = [title]
    for obj in objects:
        lines.append(f"- {obj.key} (位於: {getattr(obj.location, 'key', '無')})")
    return "\n".join(lines)

def create_object_admin(obj_key, room_name, desc=None, aliases=None):
    from typeclasses.objects import Object
    obj_key = _clean_text_safe(obj_key)
    if not obj_key:
        raise ObjectSpecError("create 需要物件名稱。")
    if _find_exact_object(obj_key):
        raise ObjectSpecError(f"同名物件已存在：{obj_key}")
    
    room = _get_room_or_error(room_name)
    desc = _clean_text_safe(desc) or "一個普通的物件。"
    
    obj = create_object(
        Object,
        key=obj_key,
        location=room,
        aliases=aliases or [],
        attributes=[("desc", desc)],
    )
    obj.save()
    return {"message": f"已建立物件 `{obj_key}`，目前位於 `{room.key}`。"}

def move_object(obj_key, room_name):
    obj = _get_object_or_error(obj_key)
    room = _get_room_or_error(room_name)
    obj.location = room
    obj.save()
    return {"message": f"已將 `{obj.key}` 移到 `{room.key}`。"}

def set_object_desc(obj_key, desc):
    obj = _get_object_or_error(obj_key)
    desc = _clean_text_safe(desc)
    if not desc:
        raise ObjectSpecError("desc 需要描述內容。")
    obj.db.desc = desc
    obj.save()
    return {"message": f"已更新 `{obj.key}` 的描述。"}

def delete_object(obj_key):
    obj = _get_object_or_error(obj_key)
    key = obj.key
    obj.delete()
    return {"message": f"已刪除物件 `{key}`。"}

def set_object_takeable(obj_key, takeable=True):
    obj = _get_object_or_error(obj_key)
    obj.db.takeable = takeable
    obj.save()
    status = "可拿取" if takeable else "不可拿取"
    return {"message": f"已將 `{obj.key}` 設定為 {status}。"}

def set_object_equippable(obj_key, equippable=True):
    obj = _get_object_or_error(obj_key)
    obj.db.equippable = equippable
    obj.save()
    status = "可裝備" if equippable else "不可裝備"
    return {"message": f"已將 `{obj.key}` 設定為 {status}。"}

def set_object_stat(obj_key, stat_pair):
    obj = _get_object_or_error(obj_key)
    if ":" not in stat_pair:
        raise ObjectSpecError("setstat 格式需要 `屬性:值` (例如 attack:5)。")
    stat, value = stat_pair.split(":", 1)
    stat, value = stat.strip(), value.strip()
    obj.db[stat] = value
    obj.save()
    return {"message": f"已將 `{obj.key}` 的屬性 `{stat}` 設定為 `{value}`。"}

def equip_object(char_key, obj_key, slot="main"):
    char = _get_player_or_error(char_key)
    obj = _get_object_or_error(obj_key)
    
    # Optional: verify equippable flag here if desired
    # if not getattr(obj.db, 'equippable', False):
    #     raise ObjectSpecError(f"物件 `{obj.key}` 不可裝備。")

    if hasattr(char, "equip"):
        try:
            char.equip(obj, slot=slot)
        except Exception as e:
            raise ObjectSpecError(f"裝備失敗：{str(e)}")
    else:
        char.db[f"equipped_{slot}"] = obj
        obj.location = char
        char.save()
        obj.save()
    return {"message": f"已將 `{obj.key}` 強制裝備到 `{char.key}` 的 `{slot}` 槽位。"}
