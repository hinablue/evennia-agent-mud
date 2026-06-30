from __future__ import annotations

import random

from evennia import CmdSet, Command
from evennia.commands import cmdhandler
from evennia.utils.utils import inherits_from

from world.combat_manager import manager


def clamp(value, minimum=0.05, maximum=0.95):
    """將機率值限制在安全範圍內。"""
    return max(minimum, min(maximum, value))


def _get_spell_metadata(skill_key):
    """P0-2：從 magic_tools.py (ScriptDB) 載入咒語元資料。

    如果找到則傳回法術屬性的字典，如果未註冊則傳回 None 。
    這取代了維護兩個單獨的技能表的需要。"""
    try:
        from world.magic_tools import get_spell_by_name

        spell = get_spell_by_name(skill_key.strip())
        return _scriptdb_to_spell_dict(spell) if spell else None
    except Exception:
        return None


def _scriptdb_to_spell_dict(scr):
    """將 ScriptDB 拼字條目轉換為執行_combat_action 的平面字典。"""
    return {
        "spell_id": getattr(scr.db, "spell_id", getattr(scr, "key", "")),
        "name": getattr(scr.db, "name", getattr(scr, "key", "")),
        "mp_cost": getattr(scr.db, "mp_cost", 0),
        "chance": getattr(scr.db, "chance", 0.8),
        "dmg_min": getattr(scr.db, "dmg_min", 0),
        "dmg_max": getattr(scr.db, "dmg_max", 0),
        "is_heal": getattr(scr.db, "is_heal", False),
        "heal_min": getattr(scr.db, "heal_min", 0),
        "heal_max": getattr(scr.db, "heal_max", 0),
        "status_effect": getattr(scr.db, "status_effect", None),
        "buff_stat": getattr(scr.db, "buff_stat", None),
        "buff_min": getattr(scr.db, "buff_min", 0),
        "buff_max": getattr(scr.db, "buff_max", 0),
        "buff_duration": getattr(scr.db, "buff_duration", 0),
        "debuff_stat": getattr(scr.db, "debuff_stat", None),
        "debuff_min": getattr(scr.db, "debuff_min", 0),
        "debuff_max": getattr(scr.db, "debuff_max", 0),
        "damage_type": getattr(
            scr.db,
            "damage_type",
            getattr(scr.db, "magic_type", "physical"),
        ),
        "effect_type": getattr(scr.db, "effect_type", "damage"),
        "magic_type": getattr(scr.db, "magic_type", "physical"),
        "target_self": getattr(scr.db, "target_self", False),
        "target_enemy": getattr(scr.db, "target_enemy", True),
        "spell_level": getattr(scr.db, "spell_level", 1),
        "mult": 1.5,  # 如果未指定則預設乘數
    }


def _apply_status_effect(target, status):
    """應用戰鬥狀態並在需要時初始化持續時間。"""
    if not status:
        return
    target.db.combat_status = status
    if status in {"stunned", "frozen"}:
        target.db.combat_status_duration = max(
            1, int(getattr(target.db, "combat_status_duration", 1) or 1)
        )


def _apply_stat_effect(recipient, stat_key, amount, duration, is_debuff=False):
    """使用接收者可用的 API 表面套用增益或減益。"""
    if not recipient or not stat_key or duration <= 0:
        return False

    if is_debuff:
        if hasattr(recipient, "apply_debuff_to_self"):
            recipient.apply_debuff_to_self(stat_key, amount, duration)
            return True
        debuffs = dict(getattr(recipient.db, "active_debuffs", {}) or {})
        debuffs[stat_key] = {"amount": int(amount), "duration": int(duration)}
        recipient.db.active_debuffs = debuffs
        return True

    if hasattr(recipient, "apply_buff"):
        recipient.apply_buff(stat_key, amount, duration)
        return True

    buffs = dict(getattr(recipient.db, "active_buffs", {}) or {})
    buffs[stat_key] = {"amount": int(amount), "duration": int(duration)}
    recipient.db.active_buffs = buffs
    return True


def is_player_character(obj):
    return (
        bool(obj)
        and inherits_from(obj, "typeclasses.characters.Character")
        and not getattr(obj.db, "is_npc", False)
    )


def room_allows_pvp(room):
    return bool(room and getattr(room.db, "pvp_enabled", False))


def validate_combat_target(attacker, target):
    if not attacker or not target:
        return False, "找不到該目標。"
    if target == attacker:
        return False, "你不能攻擊自己。"
    if getattr(target.db, "hp", 0) <= 0:
        return False, "目標已經倒下了。"

    attacker_session = getattr(attacker.db, "combat_session", None)
    target_locked = manager.is_combatant_locked_by_session(
        target, exclude_session_id=attacker_session
    )

    if getattr(target.db, "is_npc", False):
        if not getattr(target.db, "npc_attackable", True):
            return False, f"{target.key} 目前不能被攻擊。"

        if target_locked:
            return False, f"{target.key} 正在與其他敵人戰鬥中，無法同時被多人攻擊。"

    elif target_locked:
        return False, f"{target.key} 正在與其他敵人戰鬥中，無法同時被多人攻擊。"

    if (
        is_player_character(attacker)
        and is_player_character(target)
        and not room_allows_pvp(getattr(attacker, "location", None))
    ):
        return False, "這個房間不是 PVP 房，玩家不能互相攻擊。"

    return True, None


def find_open_world_target(caller, target_name):
    if not caller or not target_name:
        return None
    target_name = target_name.strip()
    location = getattr(caller, "location", None)
    if location:
        wanted = target_name.lower()
        for candidate in getattr(location, "contents", []) or []:
            if candidate == caller:
                continue
            candidate_names = {
                str(candidate.key).lower(),
                str(getattr(candidate, "id", "")).lower(),
                f"#{getattr(candidate, 'id', '')}".lower(),
            }
            try:
                candidate_names.update(
                    str(alias).lower() for alias in candidate.aliases.all()
                )
            except Exception:
                pass
            if wanted in candidate_names:
                # 檢查是否在冷卻中
                if hasattr(candidate, "is_in_cooldown") and candidate.is_in_cooldown():
                    return None
                return candidate
    try:
        return caller.search(target_name)
    except Exception:
        return None


def maybe_start_combat(caller, target):
    existing_session = manager.sessions.get(getattr(caller.db, "combat_session", None))
    if existing_session:
        return existing_session, False
    session = manager.start_combat([caller, target])
    return session, True


def find_session_target(session, target_name):
    """僅在目前戰鬥人員中解析目標名稱。"""
    if not session or not target_name:
        return None

    query = target_name.strip()
    query_lower = query.lower()
    for combatant in session.combatants:
        if query in {str(combatant.id), f"#{combatant.id}"}:
            return combatant
        if combatant.key.lower() == query_lower:
            return combatant
        aliases = []
        if hasattr(combatant, "aliases") and combatant.aliases:
            try:
                aliases = combatant.aliases.all()
            except Exception:
                aliases = []
        if any(str(alias).lower() == query_lower for alias in aliases):
            return combatant
    return None


def execute_combat_action(actor, action_type, target, skill_key=None):
    """為演員執行一個戰鬥動作。

    P0-1：取消每位玩家動作的回合超時計時器。
    P0-2：從 magic_tools.py (ScriptDB) 動態讀取法術元資料。"""
    if not actor or not target:
        return

    session = manager.sessions.get(actor.db.combat_session)
    if not session:
        actor.msg("找不到對應的戰鬥會話。")
        return

    # P0-1：玩家採取行動 - 立即取消等待的暫停
    session._cancel_turn_timer()

    if session.has_ended():
        manager.end_combat(actor.db.combat_session)
        return

    if getattr(target.db, "hp", 0) <= 0:
        actor.msg("目標已經倒下了。")
        return

    if action_type == "attack":
        hit_chance = clamp(
            0.8 + (actor.get_stat("intel") - target.get_stat("agility")) / 100
        )
        if random.random() > hit_chance:
            broadcast_msg(actor, f"❌ {actor.key} 的攻擊被 {target.key} 靈巧地閃避了！")
            session_next_turn(actor)
            return

        atk_power = actor.get_stat("str") + (actor.get_stat("stamina") // 4)
        def_power = target.get_stat("def") + (target.get_stat("stamina") // 4)
        damage = max(1, atk_power - def_power)
        apply_result(actor, target, damage, "普通攻擊", None)
        return

    if action_type == "skill":
        skill_key = skill_key or "heavy_strike"
        spell = _get_spell_metadata(skill_key)
        if not spell:
            actor.msg(f"不認識技能：{skill_key}")
            return

        mp_cost = spell.get("mp_cost", 0)
        hit_chance = clamp(spell.get("chance", 0.8) + (actor.get_stat("intel") / 100))
        dmg_min = spell.get("dmg_min", 0)
        dmg_max = spell.get("dmg_max", 0)
        is_heal = spell.get("is_heal", False)
        heal_min = spell.get("heal_min", 0)
        heal_max = spell.get("heal_max", 0)
        skill_name = spell.get("name", skill_key)
        status_effect = spell.get("status_effect") or None
        buff_stat = spell.get("buff_stat")
        debuff_stat = spell.get("debuff_stat")
        buff_duration = spell.get("buff_duration", 0)
        target_self = spell.get("target_self", False)

        if getattr(actor.db, "mp", 0) < mp_cost:
            broadcast_msg(actor, f"⚠️ {actor.key} 法力不足，無法使用 {skill_name}！")
            session_next_turn(actor)
            return

        actor.db.mp -= mp_cost

        recipient = actor if target_self else target

        if is_heal:
            heal_amount = (
                random.randint(heal_min, heal_max) if heal_min < heal_max else heal_min
            )
            recipient.db.hp = min(
                recipient.db.hp + heal_amount,
                getattr(recipient.db, "max_hp", recipient.db.hp + heal_amount),
            )
            broadcast_msg(actor, f"💚 {recipient.key} 恢復了 {heal_amount} 點 HP！")
            session_next_turn(actor)
            return

        if buff_stat and buff_duration > 0:
            amount = spell.get("buff_max", 0)
            if spell.get("buff_min", 0) < spell.get("buff_max", 0):
                amount = random.randint(
                    spell.get("buff_min", 0), spell.get("buff_max", 0)
                )
            _apply_stat_effect(
                recipient, buff_stat, amount, buff_duration, is_debuff=False
            )
            broadcast_msg(
                actor,
                f"✨ {recipient.key} 的 {buff_stat} 獲得了 {amount} 點增益，持續 {buff_duration} 回合。",
            )
            session_next_turn(actor)
            return

        if random.random() <= hit_chance:
            if dmg_max >= dmg_min and dmg_max > 0:
                damage = random.randint(dmg_min, dmg_max)
            else:
                atk_power = actor.get_stat("str") * spell.get("mult", 1.5)
                def_power = target.get_stat("def") + (target.get_stat("stamina") // 4)
                damage = int(max(1, atk_power - def_power))

            final_status = None
            resisted = False
            if status_effect:
                resist_chance = clamp(target.get_stat("spirit") / 100, 0.0, 0.95)
                if random.random() > resist_chance:
                    final_status = status_effect
                    _apply_status_effect(target, status_effect)
                else:
                    resisted = True

            if debuff_stat and buff_duration > 0 and not resisted:
                amount = spell.get("debuff_max", 0)
                if spell.get("debuff_min", 0) < spell.get("debuff_max", 0):
                    amount = random.randint(
                        spell.get("debuff_min", 0), spell.get("debuff_max", 0)
                    )
                _apply_stat_effect(
                    target, debuff_stat, amount, buff_duration, is_debuff=True
                )
                broadcast_msg(
                    actor,
                    f"⚠️ {target.key} 的 {debuff_stat} 被削弱了 {amount} 點，持續 {buff_duration} 回合。",
                )

            if resisted:
                broadcast_msg(
                    actor,
                    f"🛡️ {target.key} 憑藉強大的精神力抵抗了 {skill_name} 的效果！",
                )

            apply_result(actor, target, damage, skill_name, final_status)
            return

        broadcast_msg(actor, f"❌ {actor.key} 嘗試使用 {skill_name}，但落空了！")
        session_next_turn(actor)


def apply_result(actor, target, damage, action_name, status):
    """對目標施加傷害和可選狀態效果。"""
    raw_hp = max(0, getattr(target.db, "hp", 0) - damage)
    prevented_death = bool(
        getattr(target.db, "is_npc", False)
        and not getattr(target.db, "npc_can_die", True)
        and raw_hp <= 0
    )
    target.db.hp = 1 if prevented_death else raw_hp

    msg = f"⚔️ {actor.key} 使用 {action_name} 攻擊 {target.key}，造成 {damage} 點傷害！"
    if status:
        _apply_status_effect(target, status)
        msg += f"\n✨ {target.key} 陷入了 {status} 狀態！"
    if prevented_death:
        msg += f"\n🛡️ {target.key} 不會死亡，勉強維持著最後一口氣。"
    elif target.db.hp <= 0:
        msg += f"\n💀 {target.key} 被擊敗了！"

    # NPC 死亡處理
    is_npc = getattr(target.db, "is_npc", False)
    is_dead = target.db.hp <= 0
    session_id = getattr(actor.db, "combat_session", None)

    broadcast_msg(actor, msg)

    if is_npc and is_dead:
        # NPC 死亡：發放 Token、進入冷卻；若戰鬥尚未結束則繼續推進回合
        manager.npc_death(target, session_id)
        if session_id in manager.sessions:
            session_next_turn(actor)
        return

    session_next_turn(actor)


def attempt_npc_flee(npc, player_target):
    """嘗試讓 NPC 逃跑，成功=逃離，失敗=繼續打"""
    if not hasattr(npc, "attempt_flee"):
        return False
    if not npc.db.npc_can_flee:
        return False
    if npc.db.npc_flee_countdown > 0:
        npc.db.npc_flee_countdown -= 1
        return False

    succeeded = npc.attempt_flee()
    if succeeded:
        session_id = getattr(npc.db, "combat_session", None)
        if session_id:
            manager.npc_flee(npc, session_id)
        return True
    else:
        # 逃跑失敗，設定倒數（每場戰鬥只嘗試一次）
        npc.db.npc_flee_countdown = 999
        return False


def broadcast_msg(actor, msg):
    """向所有參與者廣播戰鬥訊息。"""
    session = manager.sessions.get(actor.db.combat_session)
    if session:
        for combatant in session.combatants:
            combatant.msg(msg)
        return
    actor.msg(msg)


def session_next_turn(actor):
    """推進戰鬥並在只剩下一方時結束比賽。"""
    session_id = actor.db.combat_session
    session = manager.sessions.get(session_id)
    if not session:
        return

    if session.has_ended():
        manager.end_combat(session_id)
        return

    # 使用 _advance_past_actor 正確處理：
    # - 指數進步
    # - 輪數增量+狀態效果處理（毒蜱）
    # - NPC AI觸發
    # - 輪流公告
    session._advance_past_actor()


class CmdCombatAttack(Command):
    """基本戰鬥攻擊指令。"""

    key = "attack"
    aliases = ["atk", "攻擊"]
    help_category = "General"

    def func(self):
        caller = self.caller
        args = self.args.strip()
        if not args:
            caller.msg("用法：attack <目標>")
            return

        if caller.db.combat_state != "fighting":
            target = find_open_world_target(caller, args)
            ok, reason = validate_combat_target(caller, target)
            if not ok:
                caller.msg(reason)
                return
            session, _started = maybe_start_combat(caller, target)
            if session.get_current_actor() != caller:
                caller.msg("你先發起了戰鬥，但目前還沒輪到你行動！")
                return
            execute_combat_action(caller, "attack", target)
            return

        session = manager.sessions.get(caller.db.combat_session)
        if not session or session.get_current_actor() != caller:
            caller.msg("現在還沒輪到你行動！")
            return
        target = find_session_target(session, args) if args else None
        ok, reason = validate_combat_target(caller, target)
        if not ok:
            caller.msg(reason)
            return
        if target not in session.combatants:
            caller.msg("找不到該目標或目標不在戰鬥中。")
            return
        execute_combat_action(caller, "attack", target)


class CmdCombatSkill(Command):
    """戰鬥技能指揮。"""

    key = "skill"
    aliases = ["sk", "技能"]
    help_category = "General"

    def func(self):
        caller = self.caller
        args = self.args.strip().split(maxsplit=1)
        if len(args) < 2:
            caller.msg("用法：skill <技能 ID> <目標>")
            return
        skill_id, target_name = args[0], args[1]

        spell = _get_spell_metadata(skill_id)
        if not spell:
            caller.msg(f"不認識這個技能：{skill_id}")
            return

        allows_self = bool(spell.get("target_self", False))

        if caller.db.combat_state != "fighting":
            target = find_open_world_target(caller, target_name)
            if target == caller and not allows_self:
                caller.msg("你不能對自己施放這個技能。")
                return

            if target != caller:
                ok, reason = validate_combat_target(caller, target)
                if not ok:
                    caller.msg(reason)
                    return

            session_target = target if target != caller else caller
            session, _started = maybe_start_combat(caller, session_target)
            if session.get_current_actor() != caller:
                caller.msg("你先發起了戰鬥，但目前還沒輪到你行動！")
                return
            execute_combat_action(caller, "skill", session_target, skill_key=skill_id)
            return

        session = manager.sessions.get(caller.db.combat_session)
        if not session or session.get_current_actor() != caller:
            caller.msg("現在還沒輪到你行動！")
            return
        target = find_session_target(session, target_name)
        if target == caller and not allows_self:
            caller.msg("你不能對自己施放這個技能。")
            return

        if target != caller:
            ok, reason = validate_combat_target(caller, target)
            if not ok:
                caller.msg(reason)
                return

        if target not in session.combatants:
            caller.msg("找不到目標。")
            return
        execute_combat_action(caller, "skill", target, skill_key=skill_id)
        return


class CmdCombatFlee(Command):
    """嘗試從戰鬥中逃跑。"""

    key = "flee"
    aliases = ["逃跑", "run"]
    help_category = "General"

    def func(self):
        caller = self.caller
        if caller.db.combat_state != "fighting":
            caller.msg("你目前不在戰鬥中，無法逃跑。")
            return

        session = manager.sessions.get(caller.db.combat_session)
        if not session or session.get_current_actor() != caller:
            caller.msg("現在還沒輪到你行動，無法逃跑！")
            return

        # 逃跑失敗率基於敏捷
        agility = caller.get_stat("agility")
        fail_chance = max(0.10, min(0.70, 0.60 - (agility - 10) * 0.025))
        # 敏捷 10 = 55% 失敗（45% 成功），敏捷 30 = 25% 失敗（75% 成功）

        if random.random() < fail_chance:
            caller.msg(f"❌ 你嘗試逃跑，但被敵人追上了！")
            session_next_turn(caller)
        else:
            caller.msg(f"🏃 你成功逃離了戰鬥！")
            if session:
                for combatant in session.combatants:
                    if combatant is not caller:
                        combatant.msg(f"🏃 {caller.key} 成功逃離了戰鬥！")
            session_id = caller.db.combat_session
            manager.end_combat(session_id, reason="flee")


class CmdPick(Command):
    """撿起房間裡的物品。"""

    key = "pick"
    aliases = ["撿", "拾取", "get"]
    help_category = "General"

    def func(self):
        caller = self.caller
        args = (self.args or "").strip()
        if not args:
            caller.msg("用法：pick <物品名稱> 或 pick all")
            return

        location = getattr(caller, "location", None)
        if not location:
            caller.msg("你不在任何地方，無法撿起物品。")
            return

        if args.lower() == "all":
            # 撿起所有可撿物品
            picked = []
            failed = []
            contents = list(getattr(location, "contents", []) or [])
            for item in contents:
                if item == caller:
                    continue
                # 只撿可拿起的物件（不是房間、不是其他角色）
                if inherits_from(item, "typeclasses.objects.Object"):
                    if caller.add_to_inventory(item):
                        item.location = caller
                        item.save()
                        picked.append(item.get_display_name(caller))
                    else:
                        failed.append(item.get_display_name(caller))
            if picked:
                caller.msg(f"📦 你撿起了：{'、'.join(picked)}")
            if failed:
                caller.msg(f"⚠️ 無法撿起：{'、'.join(failed)}（背包已滿）")
            if not picked and not failed:
                caller.msg("這裡沒有任何東西可以撿。")
            return

        # 撿起指定物品
        target_name = args.lower()
        contents = list(getattr(location, "contents", []) or [])
        for item in contents:
            if item == caller:
                continue
            item_key = str(item.key).lower()
            matches = [item_key] + [str(a).lower() for a in item.aliases.all()]
            if target_name in matches:
                if not caller.add_to_inventory(item):
                    caller.msg(
                        f"⚠️ 背包已滿，無法撿起 {item.get_display_name(caller)}！"
                    )
                    return
                item.location = caller
                item.save()
                caller.msg(f"📦 你撿起了 {item.get_display_name(caller)}。")
                return

        caller.msg(f"找不到物品：{args}。")


class CmdCast(Command):
    """施放法術（使用 @agentmagic 建立的法術）。

    用法：
      cast <法術名稱> <目標>    - 對敵人施放法術
      cast <法術名稱> self      - 對自己施放治療/增益法術
      cast <法術名稱>           - 不帶目標時嘗試自我施放（治療/增益）

    範例：
      cast 火球術 哥布林
      cast 初級治療術 self
      cast 力量祝福
    """

    key = "cast"
    aliases = ["施法", "castspell"]
    help_category = "General"

    def func(self):
        caller = self.caller
        args = self.args.strip() if self.args else ""

        if not args:
            caller.msg("用法：cast <法術名稱> [目標]，或 cast <法術名稱> self")
            return

        # 解析法術名稱與目標
        parts = args.split(maxsplit=1)
        spell_name = parts[0]
        target_str = parts[1].strip() if len(parts) > 1 else ""

        # 查找法術
        from world.magic_tools import get_spell_by_name, MagicSpecError

        spell = get_spell_by_name(spell_name)
        if not spell:
            caller.msg(f"找不到法術：{spell_name}")
            return

        # 讀取法術參數
        mp_cost = getattr(spell.db, "mp_cost", 0)
        is_heal = getattr(spell.db, "is_heal", False)
        effect_type = getattr(spell.db, "effect_type", getattr(spell.db, "magic_type", "damage"))
        dmg_min = getattr(spell.db, "dmg_min", 0)
        dmg_max = getattr(spell.db, "dmg_max", 0)
        heal_min = getattr(spell.db, "heal_min", 0)
        heal_max = getattr(spell.db, "heal_max", 0)
        buff_stat = getattr(spell.db, "buff_stat", "")
        buff_min = getattr(spell.db, "buff_min", 0)
        buff_max = getattr(spell.db, "buff_max", 0)
        debuff_stat = getattr(spell.db, "debuff_stat", "")
        debuff_min = getattr(spell.db, "debuff_min", 0)
        debuff_max = getattr(spell.db, "debuff_max", 0)
        buff_duration = getattr(spell.db, "buff_duration", 0)
        spell_level_req = getattr(spell.db, "spell_level", 1)
        spell_display_name = getattr(spell.db, "name", spell.key)

        # MP 檢查
        current_mp = getattr(caller.db, "mp", 0)
        if current_mp < mp_cost:
            caller.msg(
                f"⚠️ 你的法力不足以施放 {spell_display_name}（需要 {mp_cost} MP，你只有 {current_mp} MP）。"
            )
            return

        # 等級檢查
        caller_level = getattr(caller.db, "level", 1)
        if caller_level < spell_level_req:
            caller.msg(
                f"⚠️ 你的等級不足，無法施放 {spell_display_name}（需要等級 {spell_level_req}）。"
            )
            return

        # 自我施法：heal / buff 類型，或者 target_str == "self"
        is_self_cast = (
            is_heal
            or effect_type in ("heal", "buff")
            or target_str.lower() in ("self", "自己", "me")
        )

        if is_self_cast:
            # 自我施放（治療 / buff）
            if is_heal or effect_type == "heal":
                if heal_min <= 0 and heal_max <= 0:
                    caller.msg(f"{spell_display_name} 沒有治療效果。")
                    return
                import random

                heal_amount = random.randint(int(heal_min), int(heal_max))
                actual = caller.heal_self(heal_amount, heal_amount)
            elif effect_type == "buff" and buff_stat:
                if buff_min <= 0 and buff_max <= 0:
                    caller.msg(f"{spell_display_name} 沒有增益效果。")
                    return
                import random

                amount = random.randint(int(buff_min), int(buff_max))
                # 自我施放需要消耗一回合
                if caller.db.combat_state == "fighting":
                    # 在戰鬥中施放 buff：套用並推進回合
                    caller.apply_buff(
                        buff_stat,
                        amount,
                        int(buff_duration) if buff_duration > 0 else 3,
                    )
                    caller.msg(
                        f"✨ 你對自己施放了 {spell_display_name}，{buff_stat} +{amount}（持續 {buff_duration or 3} 回合）。"
                    )
                    session_next_turn(caller)
                else:
                    # 非戰鬥中施放 buff
                    caller.apply_buff(
                        buff_stat,
                        amount,
                        int(buff_duration) if buff_duration > 0 else 3,
                    )
                    caller.msg(
                        f"✨ 你對自己施放了 {spell_display_name}，{buff_stat} +{amount}（持續 {buff_duration or 3} 回合）。"
                    )
            else:
                caller.msg(f"{spell_display_name} 無法對自己施放。")
                return

            # 扣 MP
            caller.db.mp = current_mp - mp_cost
            caller.msg(f"💠 你施放了 {spell_display_name}（-{mp_cost} MP）。")
            return

        # 對敵人施放
        if not target_str:
            caller.msg(
                f"用法：cast <法術名稱> <目標>（{spell_display_name} 是攻擊法術，需要指定目標）"
            )
            return

        target = (
            find_open_world_target(caller, target_str)
            if caller.db.combat_state != "fighting"
            else None
        )
        if not target:
            # 在戰鬥中查找目標
            session = (
                manager.sessions.get(caller.db.combat_session)
                if caller.db.combat_state == "fighting"
                else None
            )
            if session:
                target = find_session_target(session, target_str)
            if not target:
                caller.msg(f"找不到目標：{target_str}")
                return

        ok, reason = validate_combat_target(caller, target)
        if not ok:
            caller.msg(reason)
            return

        # 檢查命中率
        chance = getattr(spell.db, "chance", 0.8)
        if random.random() > chance:
            caller.msg(f"❌ 你的 {spell_display_name} 落空了！")
            if caller.db.combat_state == "fighting":
                session_next_turn(caller)
            return

        # 扣 MP
        caller.db.mp = current_mp - mp_cost
        caller.msg(f"💠 你施放了 {spell_display_name}（-{mp_cost} MP）。")

        # 計算傷害
        intel = caller.get_stat("intel")
        atk_power = intel * 1.5 + caller.get_stat("str") * 0.5
        def_power = target.get_stat("def") + (target.get_stat("stamina") // 4)
        damage = int(
            max(
                1,
                atk_power * 0.8
                + random.randint(int(dmg_min), int(dmg_max))
                - def_power,
            )
        )

        apply_result(
            caller,
            target,
            damage,
            spell_display_name,
            getattr(spell.db, "status_effect", None),
        )


class CmdCombatNoMatch(Command):
    """戰鬥命令集處於活動狀態時後備指令。"""

    key = cmdhandler.CMD_NOMATCH
    help_category = "General"

    def func(self):
        self.caller.msg("⚠️ 你正處於激烈的戰鬥中，現在只能使用 attack、skill 或 flee。")


class CombatCmdSet(CmdSet):
    """僅戰鬥命令集，用於在戰鬥期間鎖定正常命令。"""

    key = "CombatCmdSet"
    priority = 120
    mergetype = "Replace"

    def at_cmdset_creation(self):
        self.add(CmdCombatAttack())
        self.add(CmdCombatSkill())
        self.add(CmdCombatFlee())
        self.add(CmdCast())
        self.add(CmdCombatNoMatch())


COMBAT_COMMANDS = [CmdCombatAttack, CmdCombatSkill, CmdCombatFlee, CmdPick, CmdCast]
