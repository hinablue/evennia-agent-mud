"""用於建立和管理設備物件的管理助理。"""

from __future__ import annotations

from dataclasses import dataclass

from evennia import create_object, search_object
from evennia.objects.models import ObjectDB
from evennia.utils.utils import class_from_module, inherits_from, make_iter

from typeclasses.equipment import Equipment


DEFAULT_EQUIPMENT_DESC = "這是一件普通的裝備。"


@dataclass
class EquipmentSpecError(ValueError):
    message: str

    def __str__(self):
        return self.message


# ---------------------------------------------------------------------------
# 共享助手
# ---------------------------------------------------------------------------


def _clean_text(value):
    return (value or "").strip()


def _normalize_aliases(aliases):
    seen = set()
    ordered = []
    for alias in make_iter(aliases or []):
        alias = _clean_text(alias)
        if alias and alias not in seen:
            ordered.append(alias)
            seen.add(alias)
    return ordered


def _format_list(items):
    items = [str(item) for item in items if item]
    return "、".join(items) if items else "無"


def _find_exact_object(key):
    key = _clean_text(key)
    if not key:
        return None
    matches = search_object(key, exact=True)
    return matches[0] if matches else None


def _get_room_or_error(room_name):
    room_name = _clean_text(room_name)
    if not room_name:
        raise EquipmentSpecError("請提供房間名稱。")
    room = _find_exact_object(room_name)
    if not room:
        raise EquipmentSpecError(f"房間不存在：{room_name}")
    if not inherits_from(room, "typeclasses.rooms.Room"):
        raise EquipmentSpecError(f"`{room_name}` 不是房間。")
    return room


def _get_equipment_or_error(eq_key):
    eq_key = _clean_text(eq_key)
    if not eq_key:
        raise EquipmentSpecError("請提供裝備名稱。")
    obj = _find_exact_object(eq_key)
    if not obj:
        raise EquipmentSpecError(f"找不到裝備：{eq_key}")
    if not inherits_from(obj, "typeclasses.equipment.Equipment"):
        raise EquipmentSpecError(f"`{eq_key}` 不是 Equipment。")
    return obj


def _is_equipment(obj):
    return bool(obj) and inherits_from(obj, "typeclasses.equipment.Equipment")


def _get_equipment_location(obj):
    location = getattr(obj, "location", None)
    return getattr(location, "key", "無") if location else "無"


def _truncate(text, limit=160):
    text = _clean_text(text)
    if len(text) <= limit:
        return text or "無"
    return text[: limit - 1] + "…"


def _clone_equipment_attributes(template):
    """從模板物件建立新設備屬性有效負載。"""
    stats = dict(getattr(template.db, "stats", {}) or {})
    magic_buffs = list(getattr(template.db, "magic_buffs", []) or [])
    max_durability = getattr(template.db, "max_durability", 100) or 100
    return [
        ("desc", _clean_text(getattr(template.db, "desc", "")) or DEFAULT_EQUIPMENT_DESC),
        ("equip_slot", getattr(template.db, "equip_slot", None)),
        ("stats", stats),
        ("max_durability", max_durability),
        ("durability", max_durability),
        ("two_handed", bool(getattr(template.db, "two_handed", False))),
        ("magic_buffs", magic_buffs),
        ("wear_style", getattr(template.db, "wear_style", "") or ""),
        ("is_equipment", True),
    ]


# ---------------------------------------------------------------------------
# 設備類型等級槽位
# ---------------------------------------------------------------------------
VALID_SLOTS = (
    "hat",
    "top",
    "bottom",
    "cloak",
    "shoes",
    "gloves",
    "glasses",
    "earring",
    "ring",
    "main_hand",
    "off_hand",
    "two_hand",
)


# ---------------------------------------------------------------------------
# 摘要
# ---------------------------------------------------------------------------


def summarize_equipment(eq_key):
    obj = _get_equipment_or_error(eq_key)
    lines = [f"Equipment：{obj.key}"]

    # 別名
    alias = getattr(obj.db, "player_alias", None)
    if alias:
        lines.append(f"- 暱稱：{alias}")

    # 投幣口
    slot = getattr(obj.db, "equip_slot", None)
    lines.append(f"- 裝備槽：{slot or '未裝備'}")

    # 房間
    lines.append(f"- 所在：{_get_equipment_location(obj)}")

    # 描述
    lines.append(f"- 描述：{_clean_text(getattr(obj.db, 'desc', '')) or '無'}")

    # 統計數據
    stats = getattr(obj.db, "stats", {}) or {}
    if stats:
        stats_parts = [f"{k}={v}" for k, v in sorted(stats.items())]
        lines.append(f"- 屬性：{', '.join(stats_parts)}")

    # 耐用性
    max_dur = getattr(obj.db, "max_durability", 100) or 100
    dur = getattr(obj.db, "durability", 100) or 100
    broken = getattr(obj.db, "broken", False)
    status = "已損壞" if broken else "正常"
    lines.append(f"- 耐用度：{dur}/{max_dur}（{status}）")

    # 雙手
    two_hand = getattr(obj.db, "two_handed", False)
    lines.append(f"- 雙手武器：{'是' if two_hand else '否'}")

    # 魔法愛好者
    buffs = getattr(obj.db, "magic_buffs", []) or []
    if buffs:
        buff_parts = [f"{b['stat']}{b['value']:+d}" for b in buffs]
        lines.append(f"- 魔法 Buff：{', '.join(buff_parts)}")

    lines.append(f"- typeclass：{obj.typeclass_path}")
    return "\n".join(lines)


def summarize_equipments(room_name=None):
    room = _get_room_or_error(room_name) if room_name else None
    matches = []
    for obj in ObjectDB.objects.all():
        if not _is_equipment(obj):
            continue
        if room and obj.location != room:
            continue
        matches.append(obj)

    title = f"Equipment 清單：{room.key}" if room else "Equipment 清單：全世界"
    lines = [title]
    if not matches:
        lines.append("- 目前沒有找到裝備。")
        return "\n".join(lines)

    for obj in sorted(matches, key=lambda x: x.key):
        alias = getattr(obj.db, "player_alias", None)
        alias_str = f"（{alias}）" if alias else ""
        slot = getattr(obj.db, "equip_slot", None) or "未裝備"
        dur = getattr(obj.db, "durability", 100) or 100
        max_dur = getattr(obj.db, "max_durability", 100) or 100
        broken = "已損壞" if getattr(obj.db, "broken", False) else ""
        status_str = f" {broken}" if broken else ""
        lines.append(
            f"- {obj.key}{alias_str}｜槽位：{slot}｜耐用：{dur}/{max_dur}{status_str}｜所在：{_get_equipment_location(obj)}"
        )
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# 突變
# ---------------------------------------------------------------------------


def create_equipment(
    eq_key,
    slot,
    room_name=None,
    desc=None,
    aliases=None,
    stats=None,
    max_durability=None,
    two_handed=None,
):
    """建立一個新的設備項目。

    參數：
        eq_key：設備名稱
        插槽：裝備槽位（帽子、上衣、下裝、斗篷、鞋子、手套、
              眼鏡、耳環、戒指、主手、副手、雙手）
        room_name：可選的建立房間
        描述：描述
        別名：別名列表
        stats：統計修飾符 {stat: value, ...} 的字典
        max_durability：最大耐久性（預設100）
        two_handed: 這是否是雙手武器"""
    eq_key = _clean_text(eq_key)
    if not eq_key:
        raise EquipmentSpecError("create 需要裝備名稱。")
    if _find_exact_object(eq_key):
        raise EquipmentSpecError(f"同名物件已存在：{eq_key}")

    if slot and slot not in VALID_SLOTS:
        raise EquipmentSpecError(
            f"無效的 slot：`{slot}`。有效值：{', '.join(VALID_SLOTS)}"
        )

    room = _get_room_or_error(room_name) if room_name else None
    aliases = _normalize_aliases(aliases)
    desc = _clean_text(desc) or DEFAULT_EQUIPMENT_DESC

    equipment = create_object(
        Equipment,
        key=eq_key,
        location=room,
        home=room,
        aliases=aliases,
        attributes=[
            ("desc", desc),
            ("equip_slot", slot),
            ("stats", stats or {}),
            ("max_durability", max_durability if max_durability is not None else 100),
            ("durability", max_durability if max_durability is not None else 100),
            ("two_handed", two_handed if two_handed is not None else False),
            ("magic_buffs", []),
            ("is_equipment", True),
        ],
    )

    if aliases:
        for alias in aliases:
            equipment.aliases.add(alias)

    location_str = f"位於 `{room.key}`" if room else "在倉庫中"
    return {
        "equipment": equipment,
        "message": f"已建立 Equipment `{eq_key}`（槽位：{slot or '無'}），{location_str}。",
    }


def move_equipment(eq_key, room_name):
    obj = _get_equipment_or_error(eq_key)
    room = _get_room_or_error(room_name)
    obj.location = room
    obj.save()
    return {
        "equipment": obj,
        "message": f"已將 `{obj.key}` 移到 `{room.key}`。",
    }


def clone_equipment(
    eq_key,
    new_key=None,
    room_name=None,
    location=None,
    home=None,
    allow_duplicate_key=False,
):
    """將設備物件複製到新實例中。

    參數：
        eq_key：現有設備範本名稱。
        new_key：可選的新物件鍵。預設為模板鍵。
        room_name：可選的目標房間名稱。
        location：可選的直接位置物件。允許覆蓋``room_name``.
        home: Optional home object for the clone.
        allow_duplicate_key: Whether a duplicate ``new_key``。

    返回：
        dict：使用新的設備物件和訊息複製結果有效負載。"""
    template = _get_equipment_or_error(eq_key)
    clone_key = _clean_text(new_key) or template.key
    if not allow_duplicate_key and _find_exact_object(clone_key):
        raise EquipmentSpecError(f"同名物件已存在：{clone_key}")

    destination = location or (_get_room_or_error(room_name) if room_name else None)
    clone_home = home or destination or getattr(template, "home", None) or getattr(template, "location", None)
    aliases = list(template.aliases.all()) if hasattr(template, "aliases") else []

    try:
        typeclass = class_from_module(getattr(template, "typeclass_path", "typeclasses.equipment.Equipment"))
    except Exception:
        typeclass = Equipment

    equipment = create_object(
        typeclass,
        key=clone_key,
        location=destination,
        home=clone_home,
        aliases=aliases,
        attributes=_clone_equipment_attributes(template),
    )
    location_str = getattr(destination, "key", None) or "無"
    return {
        "equipment": equipment,
        "message": f"已複製 `{template.key}` 成為 `{equipment.key}`（位置：{location_str}）。",
    }


def set_equipment_stats(eq_key, stats_dict):
    """設定設備統計資料。替換現有的統計資料。

    參數：
        eq_key：設備名稱
        stats_dict：類似 {"atk": 5, "def": -2} 的字典"""
    obj = _get_equipment_or_error(eq_key)
    obj.db.stats = dict(stats_dict)
    obj.save()
    parts = [f"{k}={v}" for k, v in sorted(stats_dict.items())]
    return {
        "equipment": obj,
        "message": f"已更新 `{obj.key}` 的屬性：{', '.join(parts)}。",
    }


def add_equipment_stat(eq_key, stat, value):
    """新增或修改裝置上的單一統計資料。"""
    obj = _get_equipment_or_error(eq_key)
    stats = getattr(obj.db, "stats", {}) or {}
    stats[stat] = stats.get(stat, 0) + value
    obj.db.stats = stats
    obj.save()
    return {
        "equipment": obj,
        "message": f"已更新 `{obj.key}` 的屬性：{stat} {value:+d}（現有：{stats[stat]}）。",
    }


def add_equipment_magic_buff(eq_key, stat, value):
    """為裝備添加魔法增益。"""
    obj = _get_equipment_or_error(eq_key)
    buffs = getattr(obj.db, "magic_buffs", []) or []
    buffs.append({"stat": stat, "value": value})
    obj.db.magic_buffs = buffs

    # 也適用於基礎統計數據
    stats = getattr(obj.db, "stats", {}) or {}
    stats[stat] = stats.get(stat, 0) + value
    obj.db.stats = stats
    obj.save()

    return {
        "equipment": obj,
        "message": f"已對 `{obj.key}` 附加魔法 Buff：{stat} {value:+d}。",
    }


def set_equipment_alias(eq_key, alias):
    """設定玩家定義的設備別名。"""
    obj = _get_equipment_or_error(eq_key)
    alias = _clean_text(alias)
    obj.db.player_alias = alias if alias else None
    obj.save()
    if alias:
        return {
            "equipment": obj,
            "message": f"已將 `{obj.key}` 的暱稱設為「{alias}」。",
        }
    return {"equipment": obj, "message": f"已清除 `{obj.key}` 的暱稱。"}


def set_equipment_desc(eq_key, desc):
    """設定設備描述。"""
    obj = _get_equipment_or_error(eq_key)
    desc = _clean_text(desc)
    if not desc:
        raise EquipmentSpecError("desc 需要描述內容。")
    obj.db.desc = desc
    obj.save()
    return {"equipment": obj, "message": f"已更新 `{obj.key}` 的描述。"}


def set_equipment_durability(eq_key, durability, max_durability=None):
    """設定裝備耐久度。"""
    obj = _get_equipment_or_error(eq_key)
    durability = int(durability)
    if max_durability is not None:
        max_durability = int(max_durability)
        obj.db.max_durability = max_durability
    obj.db.durability = durability
    if durability <= 0:
        obj.db.broken = True
    else:
        obj.db.broken = False
    obj.save()
    return {
        "equipment": obj,
        "message": f"已設定 `{obj.key}` 的耐用度：{durability}/{max_durability or getattr(obj.db, 'max_durability', 100)}。",
    }


def repair_equipment(eq_key, amount=None):
    """修復設備耐久性。"""
    obj = _get_equipment_or_error(eq_key)
    max_dur = getattr(obj.db, "max_durability", 100) or 100
    current = getattr(obj.db, "durability", 0) or 0
    if amount is None:
        obj.db.durability = max_dur
    else:
        obj.db.durability = min(max_dur, current + int(amount))
    obj.db.broken = False
    obj.save()
    return {
        "equipment": obj,
        "message": f"已修復 `{obj.key}`，目前耐用度：{obj.db.durability}/{max_dur}。",
    }


def delete_equipment(eq_key):
    """刪除裝備。"""
    obj = _get_equipment_or_error(eq_key)
    key = obj.key
    obj.delete()
    return {
        "message": f"已刪除 Equipment `{key}`。",
    }
