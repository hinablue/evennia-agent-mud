"""寶石 CRUD 與 socket 查詢工具。"""

from __future__ import annotations

from dataclasses import dataclass

from evennia import create_object
from evennia.objects.models import ObjectDB
from evennia.utils.utils import inherits_from

from typeclasses.gems import Gem

DEFAULT_GEMS = {
    "ruby": {
        "name": "紅寶石",
        "stats": {"str": 3, "stamina": 1},
        "rarity": "common",
        "desc": "蘊含生命熱度的紅色寶石。",
    },
    "sapphire": {
        "name": "藍寶石",
        "stats": {"intel": 3, "spirit": 1},
        "rarity": "common",
        "desc": "映著深海光澤的藍色寶石。",
    },
    "emerald": {
        "name": "綠寶石",
        "stats": {"agility": 3, "spd": 1},
        "rarity": "common",
        "desc": "帶有疾風氣息的綠色寶石。",
    },
}

VALID_GEM_STATS = (
    "str",
    "def",
    "intel",
    "spirit",
    "stamina",
    "agility",
    "agi",
    "spd",
    "atk",
    "hp",
    "mp",
    "max_hp",
    "max_mp",
)


@dataclass
class GemSpecError(ValueError):
    """寶石管理參數錯誤。"""

    message: str

    def __str__(self):
        """回傳錯誤訊息。"""
        return self.message


def clean_text(value):
    """清理文字參數。"""
    return (value or "").strip()


def normalize_gem_id(gem_id):
    """將 Gem ID 正規化。"""
    return clean_text(gem_id).lower()


def is_gem(obj):
    """判斷物件是否為 Gem。"""
    return bool(obj) and inherits_from(obj, "typeclasses.gems.Gem")


def iter_gems():
    """列出所有 Gem 物件。"""
    return [obj for obj in ObjectDB.objects.all() if is_gem(obj)]


def find_gem(gem_id):
    """依 gem_id 或 key 尋找 Gem；找不到時回傳 None。"""
    gem_id = normalize_gem_id(gem_id)
    if not gem_id:
        return None
    for gem in iter_gems():
        stored_id = normalize_gem_id(getattr(gem.db, "gem_id", None) or gem.key)
        if stored_id == gem_id or normalize_gem_id(gem.key) == gem_id:
            return gem
    return None


def parse_stats(stats_raw):
    """解析 ``stat=value`` 字串為 dict。

    Args:
        stats_raw: 逗號分隔的屬性字串，例如 ``str=3,stamina=1``。

    Returns:
        dict[str, int]: 屬性加成。

    Raises:
        GemSpecError: 格式或數值不合法。
    """
    stats_raw = clean_text(stats_raw)
    if not stats_raw:
        return {}
    stats = {}
    for pair in stats_raw.split(","):
        pair = clean_text(pair)
        if not pair:
            continue
        if "=" not in pair:
            raise GemSpecError(f"stat 格式錯誤：`{pair}`")
        key, value = [part.strip() for part in pair.split("=", 1)]
        if not key:
            raise GemSpecError(f"stat 名稱不可空白：`{pair}`")
        if key not in VALID_GEM_STATS:
            raise GemSpecError(
                f"無效的 stat：`{key}`。有效值：{', '.join(VALID_GEM_STATS)}"
            )
        try:
            stats[key] = int(value)
        except ValueError:
            raise GemSpecError(f"stat 值必須是整數：`{pair}`")
    return stats


def format_stats(stats):
    """格式化屬性 dict。"""
    stats = stats or {}
    if not stats:
        return "無"
    return ", ".join(f"{key}={value}" for key, value in sorted(stats.items()))


def bootstrap_default_gems():
    """建立缺少的預設 Gem 物件。

    Returns:
        list: 本次新建立的 Gem 物件。
    """
    created = []
    for gem_id, data in DEFAULT_GEMS.items():
        if find_gem(gem_id):
            continue
        created.append(
            create_gem(
                gem_id,
                data["name"],
                data["stats"],
                rarity=data.get("rarity", "common"),
                desc=data.get("desc", ""),
            )["gem"]
        )
    return created


def ensure_seeded_if_empty():
    """若世界完全沒有 Gem 物件，建立預設寶石。"""
    if not iter_gems():
        bootstrap_default_gems()


def get_gem_by_id(gem_id, require_enabled=False):
    """取得 Gem 物件。

    Args:
        gem_id: Gem ID。
        require_enabled: 是否要求 enabled=True。

    Returns:
        Gem: 持久 Gem 物件。

    Raises:
        GemSpecError: 找不到或停用時。
    """
    ensure_seeded_if_empty()
    gem = find_gem(gem_id)
    if not gem:
        available = ", ".join(gem_ids(enabled_only=require_enabled)) or "無"
        raise GemSpecError(f"找不到這種寶石。可用寶石：{available}")
    if require_enabled and not bool(getattr(gem.db, "enabled", True)):
        raise GemSpecError(f"寶石 `{gem_id}` 目前已停用。")
    return gem


def gem_ids(enabled_only=False):
    """回傳 Gem ID 清單。"""
    ensure_seeded_if_empty()
    ids = []
    for gem in iter_gems():
        if enabled_only and not bool(getattr(gem.db, "enabled", True)):
            continue
        ids.append(getattr(gem.db, "gem_id", None) or gem.key)
    return sorted(ids)


def create_gem(gem_id, name, stats=None, rarity="common", desc=None, enabled=True):
    """建立 Gem 物件。"""
    gem_id = normalize_gem_id(gem_id)
    name = clean_text(name)
    if not gem_id:
        raise GemSpecError("create 需要寶石 ID。")
    if not name:
        raise GemSpecError("create 需要寶石名稱。")
    if find_gem(gem_id):
        raise GemSpecError(f"Gem ID 已存在：{gem_id}")
    if isinstance(stats, str):
        stats = parse_stats(stats)
    gem = create_object(
        Gem,
        key=gem_id,
        location=None,
        home=None,
        aliases=[name] if name != gem_id else None,
        attributes=[
            ("gem_id", gem_id),
            ("display_name", name),
            ("stats", dict(stats or {})),
            ("enabled", bool(enabled)),
            ("rarity", clean_text(rarity) or "common"),
            ("desc", clean_text(desc) or Gem.default_description),
            ("is_gem", True),
        ],
    )
    return {"gem": gem, "message": f"已建立 Gem `{gem_id}`（{name}）：{format_stats(stats)}。"}


def update_gem(gem_id, **updates):
    """更新 Gem 物件。"""
    gem = get_gem_by_id(gem_id)
    changed = []
    if "name" in updates and updates["name"] is not None:
        name = clean_text(updates["name"])
        if not name:
            raise GemSpecError("name 不可空白。")
        gem.db.display_name = name
        changed.append("name")
    if "stats" in updates and updates["stats"] is not None:
        stats = updates["stats"]
        if isinstance(stats, str):
            stats = parse_stats(stats)
        gem.db.stats = dict(stats or {})
        changed.append("stats")
    if "enabled" in updates and updates["enabled"] is not None:
        gem.db.enabled = parse_bool(updates["enabled"])
        changed.append("enabled")
    if "rarity" in updates and updates["rarity"] is not None:
        gem.db.rarity = clean_text(updates["rarity"]) or "common"
        changed.append("rarity")
    if "desc" in updates and updates["desc"] is not None:
        gem.db.desc = clean_text(updates["desc"])
        changed.append("desc")
    gem.save()
    changed_str = ", ".join(changed) if changed else "無"
    return {"gem": gem, "message": f"已更新 Gem `{gem.db.gem_id or gem.key}`：{changed_str}。"}


def parse_bool(value):
    """解析布林文字。"""
    if isinstance(value, bool):
        return value
    raw = clean_text(value).lower()
    if raw in {"1", "true", "yes", "on", "啟用", "是"}:
        return True
    if raw in {"0", "false", "no", "off", "停用", "否"}:
        return False
    raise GemSpecError(f"布林值必須是 on/off：`{value}`")


def delete_gem(gem_id):
    """刪除 Gem 物件。"""
    gem = get_gem_by_id(gem_id)
    stable_id = getattr(gem.db, "gem_id", None) or gem.key
    name = getattr(gem.db, "display_name", None) or gem.key
    gem.delete()
    return {"message": f"已刪除 Gem `{stable_id}`（{name}）。已鑲嵌的舊 reference 將不再提供屬性。"}


def summarize_gem(gem_id):
    """回傳單一 Gem 摘要。"""
    gem = get_gem_by_id(gem_id)
    stable_id = getattr(gem.db, "gem_id", None) or gem.key
    name = getattr(gem.db, "display_name", None) or gem.key
    lines = [f"Gem：{stable_id}"]
    lines.append(f"- 名稱：{name}")
    lines.append(f"- 狀態：{'啟用' if getattr(gem.db, 'enabled', True) else '停用'}")
    lines.append(f"- 稀有度：{getattr(gem.db, 'rarity', 'common') or 'common'}")
    lines.append(f"- 屬性：{format_stats(getattr(gem.db, 'stats', {}) or {})}")
    lines.append(f"- 描述：{clean_text(getattr(gem.db, 'desc', '')) or '無'}")
    lines.append(f"- DBRef：#{gem.id}")
    return "\n".join(lines)


def summarize_gems(enabled_only=False):
    """回傳 Gem 清單。"""
    ensure_seeded_if_empty()
    gems = [gem for gem in iter_gems() if not enabled_only or getattr(gem.db, "enabled", True)]
    title = "Gem 清單：啟用中" if enabled_only else "Gem 清單：全世界"
    lines = [title]
    if not gems:
        lines.append("- 目前沒有 Gem。")
        return "\n".join(lines)
    for gem in sorted(gems, key=lambda obj: getattr(obj.db, "gem_id", None) or obj.key):
        stable_id = getattr(gem.db, "gem_id", None) or gem.key
        name = getattr(gem.db, "display_name", None) or gem.key
        status = "啟用" if getattr(gem.db, "enabled", True) else "停用"
        lines.append(
            f"- {stable_id}｜{name}｜{status}｜{format_stats(getattr(gem.db, 'stats', {}) or {})}｜#{gem.id}"
        )
    return "\n".join(lines)
