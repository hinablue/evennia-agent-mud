"""法術（Magic / Spell）CRUD 工具。

法術存放在 Evennia 的 Script 系統中當作全域資料庫。
每筆法術是一個 Script 實例，具有以下屬性：
  - key: 法術ID（唯一）
  - db.name: 顯示名稱
  - db.desc: 描述
  - db.aliases: 別名清單
  - db.mp_cost: 消耗 MP
  - db.damage_type: 傷害類型（physical/fire/ice/lightning/...）
  - db.effect_type: 效果類型（damage/heal/buff/debuff/...）
  - db.magic_type: 舊版相容欄位（由 damage_type / effect_type 推導）
  - db.dmg_min: 最小傷害
  - db.dmg_max: 最大傷害
  - db.buff_stat: 增幅屬性（str/def/spirit/intel/agility/stamina）
  - db.buff_min: 最小增幅值
  - db.buff_max: 最大增幅值
  - db.debuff_stat: 降低屬性
  - db.debuff_min: 最小降低值
  - db.debuff_max: 最大降低值
  - db.buff_duration: buff持續回合（0=無效）
  - db.is_heal: 是否為治療法術
  - db.heal_min: 最小治療量
  - db.heal_max: 最大治療量
  - db.chance: 命中率
  - db.target_self: 是否可對自己施放
  - db.target_enemy: 是否可對敵人施放
  - db.status_effect: 附加狀態（stunned/poisoned/frozen等）
  - db.spell_level: 法術等級需求
"""

from __future__ import annotations

from dataclasses import dataclass

from evennia import search_script
from evennia.scripts.models import ScriptDB
from evennia.utils.utils import make_iter


@dataclass
class MagicSpecError(ValueError):
    """Raised when a spell CRUD request is invalid."""

    message: str

    def __str__(self):
        return self.message


DAMAGE_TYPES = {
    "physical": "物理",
    "fire": "火焰",
    "ice": "冰冷",
    "lightning": "雷電",
    "water": "水系傷害",
    "wind": "風系傷害",
    "earth": "土系傷害",
    "nature": "自然系傷害",
    "poison": "毒素",
    "acid": "酸蝕",
    "holy": "神聖",
    "shadow": "暗影",
    "arcane": "奧術",
    "psychic": "心靈",
    "sonic": "音波",
    "radiant": "光輝",
    "void": "虛空",
    "blood": "血系傷害",
}


EFFECT_TYPES = {
    "damage": "傷害",
    "heal": "治療",
    "regeneration": "持續恢復",
    "revive": "復活",
    "cleanse": "淨化",
    "restore": "恢復資源/狀態",
    "barrier": "護盾",
    "buff": "增益",
    "debuff": "減益",
    "haste": "加速",
    "strengthen": "強化攻擊",
    "fortify": "強化防禦",
    "focus": "專注",
    "blessing": "祝福",
    "camouflage": "隱匿",
    "reflect": "傷害反射",
    "absorb": "傷害吸收",
    "curse": "詛咒",
    "slow": "緩速",
    "weaken": "虛弱",
    "fragile": "破甲",
    "blind": "致盲",
    "silence": "沉默",
    "fear": "恐懼",
    "taunt": "嘲諷",
    "vulnerability": "易傷",
    "stun": "暈眩",
    "freeze": "冰凍",
    "sleep": "睡眠",
    "paralyze": "麻痺",
    "root": "定身",
    "confuse": "混亂",
    "charm": "魅惑",
    "burn": "燃燒",
    "bleed": "流血",
    "poisoned": "中毒",
    "disease": "疾病",
    "frostbite": "凍傷",
    "illusion": "幻術",
    "seal": "封印",
    "drain": "吸取",
    "time": "時間操控",
}


SELF_EFFECT_TYPES = {
    "heal",
    "regeneration",
    "revive",
    "cleanse",
    "restore",
    "barrier",
    "buff",
    "haste",
    "strengthen",
    "fortify",
    "focus",
    "blessing",
    "camouflage",
    "reflect",
    "absorb",
}


DEFAULT_SPELL_DEFS = [
    {
        "spell_key": "heavy_strike",
        "name": "重擊",
        "desc": "消耗 MP 的強力單體攻擊。",
        "aliases": ["重擊"],
        "mp_cost": 10,
        "damage_type": "physical",
        "effect_type": "damage",
        "chance": 0.7,
    },
    {
        "spell_key": "stun_bash",
        "name": "震盪擊",
        "desc": "嘗試使目標眩暈。",
        "aliases": ["震盪擊"],
        "mp_cost": 15,
        "damage_type": "physical",
        "effect_type": "stun",
        "chance": 0.5,
        "status_effect": "stunned",
    },
    {
        "spell_key": "poison_dart",
        "name": "毒鏢",
        "desc": "造成中毒效果。",
        "aliases": ["毒鏢"],
        "mp_cost": 5,
        "damage_type": "physical",
        "effect_type": "poisoned",
        "chance": 0.8,
        "status_effect": "poisoned",
    },
    {
        "spell_key": "fireball",
        "name": "火球術",
        "desc": "發射一顆灼熱的火球攻擊敵人。",
        "aliases": ["火球術"],
        "mp_cost": 20,
        "damage_type": "fire",
        "effect_type": "damage",
        "dmg_min": 18,
        "dmg_max": 32,
        "chance": 0.85,
    },
    {
        "spell_key": "ice_shard",
        "name": "冰刺術",
        "desc": "發射銳利的冰刺攻擊敵人，並有概率凍住目標。",
        "aliases": ["冰刺術"],
        "mp_cost": 18,
        "damage_type": "ice",
        "effect_type": "freeze",
        "dmg_min": 14,
        "dmg_max": 26,
        "chance": 0.6,
        "status_effect": "frozen",
    },
    {
        "spell_key": "lightning_bolt",
        "name": "閃電術",
        "desc": "召喚一道閃電攻擊敵人。",
        "aliases": ["閃電術"],
        "mp_cost": 25,
        "damage_type": "lightning",
        "effect_type": "damage",
        "dmg_min": 24,
        "dmg_max": 38,
        "chance": 0.75,
    },
    {
        "spell_key": "heal",
        "name": "治療術",
        "desc": "回復自己的 HP。",
        "aliases": ["治療術"],
        "mp_cost": 12,
        "damage_type": "holy",
        "effect_type": "heal",
        "is_heal": True,
        "heal_min": 18,
        "heal_max": 30,
        "chance": 1.0,
        "target_self": True,
        "target_enemy": False,
    },
]


# ---------------------------------------------------------------------------
# Helpers
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


def _format_aliases(aliases):
    return "、".join(aliases) if aliases else "無"


def _coerce_bool(value):
    if isinstance(value, str):
        return _clean_text(value).lower() in {"1", "true", "yes", "on"}
    return bool(value)


def _normalize_damage_type(value):
    value = _clean_text(value or "physical").lower()
    if value not in DAMAGE_TYPES:
        raise MagicSpecError(
            "damage_type 不合法，可用值：%s" % ", ".join(sorted(DAMAGE_TYPES))
        )
    return value


def _normalize_effect_type(value):
    value = _clean_text(value or "damage").lower()
    if value not in EFFECT_TYPES:
        raise MagicSpecError(
            "effect_type 不合法，可用值：%s" % ", ".join(sorted(EFFECT_TYPES))
        )
    return value


def _resolve_spell_types(spec):
    legacy_magic_type = _clean_text(spec.get("magic_type") or "").lower()
    damage_type = _clean_text(spec.get("damage_type") or "").lower()
    effect_type = _clean_text(spec.get("effect_type") or "").lower()

    if legacy_magic_type:
        if not damage_type and legacy_magic_type in DAMAGE_TYPES:
            damage_type = legacy_magic_type
        if not effect_type and legacy_magic_type in EFFECT_TYPES:
            effect_type = legacy_magic_type

    if not effect_type:
        status_effect = _clean_text(spec.get("status_effect") or "").lower()
        if _coerce_bool(spec.get("is_heal", False)):
            effect_type = "heal"
        elif status_effect == "stunned":
            effect_type = "stun"
        elif status_effect == "frozen":
            effect_type = "freeze"
        elif status_effect in EFFECT_TYPES:
            effect_type = status_effect
        elif _clean_text(spec.get("debuff_stat") or ""):
            effect_type = "debuff"
        elif _clean_text(spec.get("buff_stat") or ""):
            effect_type = "buff"
        else:
            effect_type = "damage"

    if not damage_type:
        damage_type = "holy" if effect_type == "heal" else "physical"

    return _normalize_damage_type(damage_type), _normalize_effect_type(effect_type)


def _legacy_magic_type(damage_type, effect_type):
    return effect_type if effect_type != "damage" else damage_type


def _refresh_legacy_types(spell):
    damage_type, effect_type = _resolve_spell_types(
        {
            "damage_type": getattr(spell.db, "damage_type", None),
            "effect_type": getattr(spell.db, "effect_type", None),
            "magic_type": getattr(spell.db, "magic_type", None),
            "is_heal": getattr(spell.db, "is_heal", False),
            "status_effect": getattr(spell.db, "status_effect", None),
            "buff_stat": getattr(spell.db, "buff_stat", None),
            "debuff_stat": getattr(spell.db, "debuff_stat", None),
        }
    )
    spell.db.damage_type = damage_type
    spell.db.effect_type = effect_type
    spell.db.magic_type = _legacy_magic_type(damage_type, effect_type)


def _refresh_target_defaults(spell):
    effect_type = getattr(spell.db, "effect_type", "damage")
    target_self_default = (
        bool(getattr(spell.db, "is_heal", False))
        or bool(getattr(spell.db, "buff_stat", ""))
        or effect_type in SELF_EFFECT_TYPES
    )
    spell.db.target_self = bool(target_self_default)
    spell.db.target_enemy = not bool(target_self_default)


def _is_spell_script(scr):
    """Return True when the script row should be treated as a spell entry."""
    if not scr:
        return False
    db = getattr(scr, "db", None)
    if getattr(db, "is_spell", False):
        return True
    if _clean_text(getattr(db, "spell_id", "")):
        return True
    return _clean_text(getattr(scr, "key", "")) == "spell"


def _get_spell_identifier(scr):
    """Return the canonical spell id for a spell script."""
    db = getattr(scr, "db", None)
    spell_id = _clean_text(getattr(db, "spell_id", ""))
    if spell_id:
        return spell_id
    key = _clean_text(getattr(scr, "key", ""))
    if key and key != "spell":
        return key
    return _clean_text(getattr(db, "name", ""))


def _apply_spell_fields(obj, spec):
    """Write normalized spell fields onto a ScriptDB row."""
    damage_type, effect_type = _resolve_spell_types(spec)
    obj.db.is_spell = True
    obj.db.spell_id = spec["spell_key"]
    obj.db.name = _clean_text(spec.get("name") or spec["spell_key"])
    obj.db.desc = _clean_text(spec.get("desc") or "")
    obj.db.aliases = _normalize_aliases(spec.get("aliases") or [])
    obj.db.mp_cost = int(spec.get("mp_cost", 0))
    obj.db.damage_type = damage_type
    obj.db.effect_type = effect_type
    obj.db.magic_type = _legacy_magic_type(damage_type, effect_type)
    obj.db.dmg_min = int(spec.get("dmg_min", 0))
    obj.db.dmg_max = int(spec.get("dmg_max", 0))
    obj.db.buff_stat = _clean_text(spec.get("buff_stat") or "")
    obj.db.buff_min = int(spec.get("buff_min", 0))
    obj.db.buff_max = int(spec.get("buff_max", 0))
    obj.db.debuff_stat = _clean_text(spec.get("debuff_stat") or "")
    obj.db.debuff_min = int(spec.get("debuff_min", 0))
    obj.db.debuff_max = int(spec.get("debuff_max", 0))
    obj.db.buff_duration = int(spec.get("buff_duration", 0))
    obj.db.is_heal = _coerce_bool(spec.get("is_heal", effect_type == "heal"))
    obj.db.heal_min = int(spec.get("heal_min", 0))
    obj.db.heal_max = int(spec.get("heal_max", 0))
    obj.db.chance = float(spec.get("chance", 0.8))
    obj.db.status_effect = _clean_text(spec.get("status_effect") or "") or None
    obj.db.spell_level = int(spec.get("spell_level", 1))
    target_self_default = obj.db.is_heal or bool(obj.db.buff_stat) or effect_type in SELF_EFFECT_TYPES
    obj.db.target_self = bool(spec.get("target_self", target_self_default))
    obj.db.target_enemy = bool(spec.get("target_enemy", not obj.db.target_self))
    obj.save()


def _bootstrap_default_spells():
    """Create default spells when the live registry is empty."""
    try:
        from evennia import create_script
    except Exception:
        return False

    for spec in DEFAULT_SPELL_DEFS:
        existing = [
            row
            for row in search_script(spec["spell_key"])
            if getattr(row, "key", None) == spec["spell_key"]
        ]
        if existing:
            row = existing[0]
            if not _is_spell_script(row):
                _apply_spell_fields(row, spec)
            continue
        row = create_script(
            "typeclasses.scripts.Script", key=spec["spell_key"], persistent=True
        )
        _apply_spell_fields(row, spec)
    return True


def _get_spell_or_error(spell_key):
    """依 key 或 alias 找到法術 Script。"""
    spell_key = _clean_text(spell_key)
    if not spell_key:
        raise MagicSpecError("請提供法術名稱。")

    results = [
        row
        for row in search_script(spell_key)
        if getattr(row, "key", None) == spell_key
    ]
    for result in results:
        if _is_spell_script(result):
            _refresh_legacy_types(result)
            return result

    all_spells = [scr for scr in ScriptDB.objects.all() if _is_spell_script(scr)]
    if not all_spells and _bootstrap_default_spells():
        all_spells = [scr for scr in ScriptDB.objects.all() if _is_spell_script(scr)]

    for scr in all_spells:
        if _get_spell_identifier(scr) == spell_key:
            _refresh_legacy_types(scr)
            return scr
        if getattr(scr.db, "name", "") == spell_key:
            _refresh_legacy_types(scr)
            return scr
        if spell_key in (getattr(scr.db, "aliases", []) or []):
            _refresh_legacy_types(scr)
            return scr

    raise MagicSpecError(f"找不到法術：{spell_key}")


def _list_all_spells():
    """列舉所有法術。"""
    spells = [scr for scr in ScriptDB.objects.all() if _is_spell_script(scr)]
    if not spells and _bootstrap_default_spells():
        spells = [scr for scr in ScriptDB.objects.all() if _is_spell_script(scr)]
    for spell in spells:
        _refresh_legacy_types(spell)
    return spells


def _format_spell(spell):
    """Format spell for display."""
    spell_id = _get_spell_identifier(spell)
    lines = []
    lines.append(f"ID：{spell_id}")
    lines.append(f"- 名稱：{getattr(spell.db, 'name', spell_id)}")
    lines.append(f"- 別名：{_format_aliases(getattr(spell.db, 'aliases', []) or [])}")
    lines.append(f"- 描述：{_clean_text(getattr(spell.db, 'desc', '') or '無')}")
    lines.append(f"- 消耗 MP：{getattr(spell.db, 'mp_cost', 0)}")
    lines.append(f"- 傷害類型：{getattr(spell.db, 'damage_type', 'physical')}")
    lines.append(f"- 效果類型：{getattr(spell.db, 'effect_type', 'damage')}")
    lines.append(
        f"- 傷害：{getattr(spell.db, 'dmg_min', 0)}~{getattr(spell.db, 'dmg_max', 0)}"
    )
    lines.append(
        f"- 增幅：{getattr(spell.db, 'buff_stat', '無')} "
        f"{getattr(spell.db, 'buff_min', 0)}~{getattr(spell.db, 'buff_max', 0)} "
        f"（持續 {getattr(spell.db, 'buff_duration', 0)} 回合）"
    )
    lines.append(
        f"- 削弱：{getattr(spell.db, 'debuff_stat', '無')} "
        f"{getattr(spell.db, 'debuff_min', 0)}~{getattr(spell.db, 'debuff_max', 0)}"
    )
    if getattr(spell.db, "is_heal", False):
        lines.append(
            f"- 治療：{getattr(spell.db, 'heal_min', 0)}~{getattr(spell.db, 'heal_max', 0)}"
        )
    if getattr(spell.db, "status_effect", None):
        lines.append(
            f"- 狀態：{spell.db.status_effect}（命中率 {getattr(spell.db, 'chance', 0.8):.0%}）"
        )
    lines.append(f"- 等級需求：{getattr(spell.db, 'spell_level', 1)}")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# CRUD
# ---------------------------------------------------------------------------


def create_spell(
    spell_key,
    name=None,
    desc=None,
    aliases=None,
    mp_cost=10,
    damage_type="physical",
    effect_type="damage",
    magic_type=None,
    dmg_min=0,
    dmg_max=0,
    buff_stat=None,
    buff_min=0,
    buff_max=0,
    debuff_stat=None,
    debuff_min=0,
    debuff_max=0,
    buff_duration=0,
    is_heal=False,
    heal_min=0,
    heal_max=0,
    chance=0.8,
    status_effect=None,
    spell_level=1,
):
    """建立新法術。"""
    spell_key = _clean_text(spell_key)
    if not spell_key:
        raise MagicSpecError("建立法術需要一個 ID。")
    try:
        _get_spell_or_error(spell_key)
        raise MagicSpecError(f"法術 ID `{spell_key}` 已存在。")
    except MagicSpecError:
        pass

    from evennia import create_script

    obj = create_script("typeclasses.scripts.MuxScript", key=spell_key, persistent=True)
    _apply_spell_fields(
        obj,
        {
            "spell_key": spell_key,
            "name": name,
            "desc": desc,
            "aliases": aliases,
            "mp_cost": mp_cost,
            "damage_type": damage_type,
            "effect_type": effect_type,
            "magic_type": magic_type,
            "dmg_min": dmg_min,
            "dmg_max": dmg_max,
            "buff_stat": buff_stat,
            "buff_min": buff_min,
            "buff_max": buff_max,
            "debuff_stat": debuff_stat,
            "debuff_min": debuff_min,
            "debuff_max": debuff_max,
            "buff_duration": buff_duration,
            "is_heal": is_heal,
            "heal_min": heal_min,
            "heal_max": heal_max,
            "chance": chance,
            "status_effect": status_effect,
            "spell_level": spell_level,
        },
    )
    return {
        "spell": obj,
        "message": f"已建立法術 `{spell_key}`（{obj.db.name}）。",
    }


def update_spell(
    spell_key,
    name=None,
    desc=None,
    aliases=None,
    mp_cost=None,
    damage_type=None,
    effect_type=None,
    magic_type=None,
    dmg_min=None,
    dmg_max=None,
    buff_stat=None,
    buff_min=None,
    buff_max=None,
    debuff_stat=None,
    debuff_min=None,
    debuff_max=None,
    buff_duration=None,
    is_heal=None,
    heal_min=None,
    heal_max=None,
    chance=None,
    status_effect=None,
    spell_level=None,
):
    """更新法術屬性。"""
    spell = _get_spell_or_error(spell_key)
    updates = []
    recompute_target_defaults = False

    if name is not None:
        spell.db.name = _clean_text(name)
        updates.append(f"name={spell.db.name}")
    if desc is not None:
        spell.db.desc = _clean_text(desc)
        updates.append("desc=已更新")
    if aliases is not None:
        spell.db.aliases = _normalize_aliases(aliases)
        updates.append(f"aliases={_format_aliases(spell.db.aliases)}")
    if mp_cost is not None:
        spell.db.mp_cost = int(mp_cost)
        updates.append(f"mp_cost={spell.db.mp_cost}")
    if damage_type is not None:
        spell.db.damage_type = _normalize_damage_type(damage_type)
        updates.append(f"damage_type={spell.db.damage_type}")
    if effect_type is not None:
        spell.db.effect_type = _normalize_effect_type(effect_type)
        updates.append(f"effect_type={spell.db.effect_type}")
        recompute_target_defaults = True
    if magic_type is not None:
        legacy_magic_type = _clean_text(magic_type).lower()
        if legacy_magic_type in DAMAGE_TYPES:
            spell.db.damage_type = _normalize_damage_type(legacy_magic_type)
            updates.append(f"damage_type={spell.db.damage_type}")
        elif legacy_magic_type in EFFECT_TYPES:
            spell.db.effect_type = _normalize_effect_type(legacy_magic_type)
            updates.append(f"effect_type={spell.db.effect_type}")
            recompute_target_defaults = True
        else:
            raise MagicSpecError(
                "magic_type 已拆分為 damage_type / effect_type，請使用新欄位或合法舊值。"
            )
    if dmg_min is not None:
        spell.db.dmg_min = int(dmg_min)
        updates.append(f"dmg_min={spell.db.dmg_min}")
    if dmg_max is not None:
        spell.db.dmg_max = int(dmg_max)
        updates.append(f"dmg_max={spell.db.dmg_max}")
    if buff_stat is not None:
        spell.db.buff_stat = _clean_text(buff_stat)
        updates.append(f"buff_stat={spell.db.buff_stat}")
        recompute_target_defaults = True
    if buff_min is not None:
        spell.db.buff_min = int(buff_min)
        updates.append(f"buff_min={spell.db.buff_min}")
    if buff_max is not None:
        spell.db.buff_max = int(buff_max)
        updates.append(f"buff_max={spell.db.buff_max}")
    if debuff_stat is not None:
        spell.db.debuff_stat = _clean_text(debuff_stat)
        updates.append(f"debuff_stat={spell.db.debuff_stat}")
    if debuff_min is not None:
        spell.db.debuff_min = int(debuff_min)
        updates.append(f"debuff_min={spell.db.debuff_min}")
    if debuff_max is not None:
        spell.db.debuff_max = int(debuff_max)
        updates.append(f"debuff_max={spell.db.debuff_max}")
    if buff_duration is not None:
        spell.db.buff_duration = int(buff_duration)
        updates.append(f"buff_duration={spell.db.buff_duration}")
    if is_heal is not None:
        spell.db.is_heal = _coerce_bool(is_heal)
        updates.append(f"is_heal={spell.db.is_heal}")
        recompute_target_defaults = True
    if heal_min is not None:
        spell.db.heal_min = int(heal_min)
        updates.append(f"heal_min={spell.db.heal_min}")
    if heal_max is not None:
        spell.db.heal_max = int(heal_max)
        updates.append(f"heal_max={spell.db.heal_max}")
    if chance is not None:
        spell.db.chance = float(chance)
        updates.append(f"chance={spell.db.chance:.0%}")
    if status_effect is not None:
        spell.db.status_effect = _clean_text(status_effect) or None
        updates.append(f"status_effect={spell.db.status_effect or '無'}")
    if spell_level is not None:
        spell.db.spell_level = int(spell_level)
        updates.append(f"spell_level={spell.db.spell_level}")

    _refresh_legacy_types(spell)
    if recompute_target_defaults:
        _refresh_target_defaults(spell)

    spell.save()
    if not updates:
        raise MagicSpecError("至少需要提供一個要更新的欄位。")
    return {
        "spell": spell,
        "message": f"已更新 `{_get_spell_identifier(spell)}`：{'、'.join(updates)}。",
    }


def delete_spell(spell_key):
    """刪除法術。"""
    spell = _get_spell_or_error(spell_key)
    key = _get_spell_identifier(spell)
    spell.delete()
    return {
        "message": f"已刪除法術 `{key}`。",
    }


def list_spells():
    """列出所有法術。"""
    spells = _list_all_spells()
    if not spells:
        return "目前沒有任何法術。"
    lines = ["法術列表："]
    for spell in spells:
        spell_id = _get_spell_identifier(spell)
        name = getattr(spell.db, "name", spell_id)
        damage_type = getattr(spell.db, "damage_type", "physical")
        effect_type = getattr(spell.db, "effect_type", "damage")
        mp = getattr(spell.db, "mp_cost", 0)
        dmg = f"{getattr(spell.db, 'dmg_min', 0)}~{getattr(spell.db, 'dmg_max', 0)}"
        aliases = _format_aliases(getattr(spell.db, "aliases", []) or [])
        lines.append(
            f"- {spell_id}｜{name}｜damage_type：{damage_type}｜effect_type：{effect_type}｜MP：{mp}｜傷害：{dmg}｜別名：{aliases}"
        )
    return "\n".join(lines)


def get_spell(spell_key):
    """取得單一法術詳細資訊。"""
    spell = _get_spell_or_error(spell_key)
    return _format_spell(spell)


def get_spell_by_name(name_or_key):
    """以名稱或 key 取得法術（供戰鬥系統呼叫）。"""
    try:
        return _get_spell_or_error(name_or_key)
    except MagicSpecError:
        return None
