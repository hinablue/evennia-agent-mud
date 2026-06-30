# Agent 迷航 — 模組參考文件

> **版本：v2.1 — 2026-06-30**
> **維護者：Rosie (許御琪)**

---

## 1. 架構總覽

```
agent-mud/
├── world/          # 遊戲邏輯與工具函數
├── commands/       # 玩家/GM/King 指令
├── typeclasses/    # Evennia 型別類別
├── tests/          # 單元測試 + 整合測試
├── docs/           # 設計文件
└── server/         # Evennia 伺服器設定
```

---

## 2. world/ — 遊戲邏輯

### 2.1戰鬥管理器.py
CombatManager 單例 + CombatSession，管理回合制戰鬥流程。

| 方法 | 說明 |
|------|------|
| `start_combat(combatants, timer_factory)` | 建立戰鬥 session，排序行動序 |
| `end_combat(session_id, reason)` | 結束戰鬥，清除狀態 |
| `next_turn()` | 推進下一位行動者 |
| `process_status_effects()` | 處理 poison/buff tick |
| `npc_death(npc, session_id)` | NPC 死亡：掉落 token/loot、cooldown |
| `npc_flee(npc, session_id)` | NPC 逃跑：冷却、不掉落 |
| `is_combatant_locked()` | 檢查是否被其他 session 鎖定 |

### 2.2戰鬥工具.py
GM 戰鬥控制工具。

| 方法 | 說明 |
|------|------|
| `stop_combat(char_key)` | 強行終止戰鬥狀態 |
| `force_win(char_key)` | 強制設為獲勝 |
| `set_npc_state(npc_key, state)` | 切換 NPC AI 狀態 |

### 2.3 王國.py
Kingdom (國家) Script + GM 建國工具。

**Kingdom 類別方法：**

| 方法 | 說明 |
|------|------|
| `get_quota_remaining()` | 剩餘可建房間 |
| `can_create_room()` | 是否還能建房 |
| `increment_rooms_created()` | 建房計數 +1 |
| `decrement_rooms_created()` | 刪房計數 -1 |
| `set_king(king_char)` | 設定國王 |
| `set_entrance_room(room)` | 設定入口房間 + 打標 |
| `add_gm_continent_room(room)` | 記錄 GM 大陸連結房間 |
| `change_name(new_name)` | 變更國名 + 同步 tag/nationality |
| `delete()` | 刪除國家 + 清理 |

**模組函數：**

| 函數 | 說明 |
|------|------|
| `create_kingdom(king_char, name, entrance_room, quota)` | GM 建國 |
| `get_kingdom_by_name(name)` | 依國名查找 |
| `get_kingdom_by_king(king_char)` | 依 King 查找 |
| `create_kingdom_channels(key, king_char)` | 建國家頻道 |
| `add_room_quota(kingdom, additional)` | GM 追加額度 |
| `get_kingdom_status(kingdom)` | 國家狀態摘要 |

### 2.4 magic_tools.py
法術 CRUD 工具。

| 函數 | 說明 |
|------|------|
| `create_spell(spell_key, ...)` | 建立法術 |
| `update_spell(spell_key, ...)` | 更新法術屬性 |
| `delete_spell(spell_key)` | 刪除法術 |
| `list_spells()` | 列出所有法術 |
| `get_spell(spell_key)` | 依 key/alias 查找 |
| `get_spell_by_name(name_or_key)` | 依名稱查找 |

### 2.5 npc_tools.py
NPC/LLMNPC CRUD 工具。

| 函數 | 說明 |
|------|------|
| `create_npc(kind, key, room, ...)` | 建立 NPC |
| `summarize_npc(key)` / `summarize_npcs(room)` | NPC 摘要 |
| `move_npc(key, room)` | 移動 NPC |
| `set_npc_desc/aliases/stats/skills/...` | 設定 NPC 屬性 |
| `set_llm_config/get_llm_config` | LLM 設定 |
| `set_npc_combat_flags/level/cooldown/...` | 戰鬥屬性 |
| `set_npc_flee/aggro/equipment/loot_table` | 戰鬥行為 |
| `delete_npc(key)` | 刪除 NPC |

### 2.6 物件工具.py
遊戲物件管理工具。

| 函數 | 說明 |
|------|------|
| `create_object_admin(key, room, ...)` | 建立物件 |
| `summarize_object(key)` / `list_objects(room)` | 物件摘要 |
| `move_object(key, room)` | 移動物件 |
| `set_object_desc/takeable/equippable/stat` | 設定屬性 |
| `equip_object(char_key, obj_key, slot)` | 穿戴裝備 |
| `delete_object(key)` | 刪除物件 |

### 2.7 玩家工具.py
玩家角色管理工具。

| 函數 | 說明 |
|------|------|
| `create_player(key, room, ...)` | 建立角色 |
| `summarize_player(key)` / `summarize_players(room)` | 角色摘要 |
| `move_player/summon_player/send_player_home` | 移動角色 |
| `set_player_home/desc/aliases` | 設定屬性 |
| `rename_player(key, new_name)` | 改名 |
| `bind_player/unbind_player` | 綁定/解綁帳號 |
| `delete_player(key)` | 刪除角色 |

### 2.8 quest_tools.py
任務管理工具。

| 函數 | 說明 |
|------|------|
| `give_quest(char_key, quest_key)` | 發放任務 |
| `complete_quest(char_key, quest_key)` | 完成任務 |
| `summarize_quests(char_key)` | 任務摘要 |

### 2.9 room_tools.py
房間管理工具（RoomTools 類別）。

| 方法 | 說明 |
|------|------|
| `list_rooms(query)` | 列出房間 |
| `create_room(name, desc)` | 建立房間 |
| `update_desc(room, desc)` | 更新描述 |
| `delete_room(room)` | 刪除房間 |
| `set_pvp_state(room, enabled)` | 設定 PVP |
| `set_door_state(room, direction, state)` | 門狀態 |
| `summarize_room(room)` | 房間摘要 |

### 2.10 account_tools.py
帳號管理工具。

| 函數 | 說明 |
|------|------|
| `create_account(name, password, email)` | 建立帳號 |
| `set_account_role(name, role)` | 設定角色 (GM/King/Player) |
| `add/remove_account_permission` | 增刪權限 |
| `set_account_nationality(name, nat)` | 設定國籍 |
| `appoint_king(account, char_key)` | 指派 King |
| `delete_account(name)` | 刪除帳號 |

### 2.11 裝置工具.py
裝備 CRUD 工具。

| 函數 | 說明 |
|------|------|
| `create_equipment(key, room, ...)` | 建立裝備 |
| `clone_equipment(key, room, ...)` | 複製裝備 |
| `set_equipment_stats/alias/desc/durability` | 設定屬性 |
| `add_equipment_stat/magic_buff` | 增加屬性/魔法增幅 |
| `repair_equipment(key, amount)` | 修復耐久 |
| `delete_equipment(key)` | 刪除裝備 |

### 2.12 shop_tools.py
限定商店工具。

| 函數 | 說明 |
|------|------|
| `set_room_shop_stock(template_key, room, price, qty)` | 設定商品 |
| `remove_room_shop_stock(template_key, room)` | 移除商品 |
| `buy_from_room_shop(caller, selection)` | 購買商品 |
| `summarize_room_shop/for_player` | 商店摘要 |

### 2.13 代理世界.py
世界建立、檢查與管理工具。

| 函數 | 說明 |
|------|------|
| `build_agent_world(room, components)` | 建立世界 |
| `force_rebuild_agent_world()` | 強制重建 |
| `analyze_agent_world(room, components)` | 分析世界 |
| `create/add_live_room/detail/scenery/exit` | 增建元件 |
| `move_live_entity(key, dest)` | 移動實體 |

### 2.14 代理_xyzgrid.py
XYZGrid 地圖與遷移工具。

---

## 3. commands/ — 指令

### 3.1 GM 指令

| 指令 | 模組 | 說明 |
|------|------|------|
| `@agentworld` | world_admin.py | 世界管理（King 限 addroom/adddetail/addscenery/addexit） |
| `@agentaccount` | account_admin.py | 帳號管理 |
| `@agentplayer` | player_admin.py | 角色管理 |
| `@agentnpc` | npc_admin.py | NPC 管理 |
| `@agentobject` | object_admin.py | 物件管理 |
| `@agentweapon` | equipment_admin.py | 裝備管理 |
| `@agentroom` | room_admin.py | 房間管理 |
| `@agentcombat` | combat_admin.py | 戰鬥控制 |
| `@agentmagic` | magic_admin.py | 法術管理 |
| `@agentquest` | quest_admin.py | 任務管理 |
| `@agentkingdom` / `@kingdom` | kingdom_admin.py | 國家管理主入口（GM 完整 CRUD；King 限 countries/countrystatus/countryrename） |

### 3.2 King 指令

| 指令 | 模組 | 說明 |
|------|------|------|
| `@king` | king_admin.py | King 管理自國 |

### 3.3 Player 指令

| 指令 | 模組 | 說明 |
|------|------|------|
| `status` | player_commands.py | 角色狀態 |
| `inventory` | player_commands.py | 背包 |
| `equipment` | player_commands.py | 裝備欄位 |
| `shop` / `buy` | player_commands.py | 商店/購買 |
| `socket` | combat_socket.py | 鑲嵌寶石 |

---

## 4. typeclasses/ — 型別類別

| 類別 | 模組 | 說明 |
|------|------|------|
| `Character` | characters.py | 玩家角色（屬性、背包、裝備、buff） |
| `NPC` / `LLMNPC` | npcs.py / llm_npc.py | NPC（冷卻、仇恨、逃跑、掠奪） |
| `Equipment` | equipment.py | 裝備（耐久、魔法增幅） |
| `Room` | rooms.py | 房間 |
| `Object` | objects.py | 遊戲物件 |
| `CombatSession` | scripts.py | 戰鬥 session（回合、AI） |
| `Kingdom` | kingdom.py | 國家（額度、King、標籤） |

---

## 5. tests/ — 測試覆蓋

| 測試檔 | 目標模組 | 測試數量 |
|--------|----------|----------|
|測試戰鬥系統.py |戰鬥管理器 + 戰鬥指令 | 35 | 35
| test_combat_session_behavior.py | CombatSession 行為 | 34 |
| test_combat_live_smoke.py | 線上 smoke test | 14 |
|測試設備系統.py |設備+庫存| 31 |
|測試帳號管理.py | account_tools + CmdAgentAccount | 11 | 11
|測試玩家指令.py |面向玩家的指令 | 7 |
|測試世界管理.py | world_admin 指令 | 5 |
|測試_代理_xyzgrid.py | XYZ網格| 4 |
|測試_代理_世界.py |代理世界 | 3 |
|測試商店工具.py |商店工具 | 4 |
|測試_kingdom.py |王國.py | 🆕 |
|測試魔法工具.py | magic_tools.py | 🆕 |
|測試任務工具.py | quest_tools.py | 🆕 |
|測試戰鬥工具.py |戰鬥工具.py | 🆕 |
|測試_combat_socket_cmd.py | Battle_socket.py | 🆕 |
|測試_npc_tools.py | npc_tools.py | 🆕 |
|測試物件工具.py |物件工具.py | 🆕 |
|測試玩家工具.py |玩家工具.py | 🆕 |
|測試室工具.py | room_tools.py | 🆕 |

---

*文件版本：v2.2 — 2026-06-30*
*維護者：Rosie (許御琪) 為 Hina Chen 整理*
