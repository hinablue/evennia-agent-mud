# MCP Tooling Reference — Agent 迷航

> 本文件定義 AI Agent 可用的 MCP 工具清單，供 Evennia 遊戲世界操作。

---

## 工具清單

### 世界管理
| 工具名 | 對應函數 | 說明 |
|--------|----------|------|
| `build_agent_world` | `world.agent_world.build_agent_world` | 建立世界 |
| `force_rebuild` | `world.agent_world.force_rebuild_agent_world` | 強制重建世界 |
| `summarize_world` | `world.agent_world.summarize_agent_world` | 世界摘要 |

### 房間管理
| 工具名 | 對應函數 | 說明 |
|--------|----------|------|
| `list_rooms` | `world.room_tools.RoomTools.list_rooms` | 列出房間 |
| `create_room` | `world.room_tools.RoomTools.create_room` | 建立房間 |
| `update_room_desc` | `world.room_tools.RoomTools.update_desc` | 更新房間描述 |
| `delete_room` | `world.room_tools.RoomTools.delete_room` | 刪除房間 |
| `set_pvp` | `world.room_tools.RoomTools.set_pvp_state` | 設定 PVP |

### 角色管理
| 工具名 | 對應函數 | 說明 |
|--------|----------|------|
| `create_player` | `world.player_tools.create_player` | 建立角色 |
| `summarize_player` | `world.player_tools.summarize_player` | 角色摘要 |
| `move_player` | `world.player_tools.move_player` | 移動角色 |
| `delete_player` | `world.player_tools.delete_player` | 刪除角色 |

### NPC 管理
| 工具名 | 對應函數 | 說明 |
|--------|----------|------|
| `create_npc` | `world.npc_tools.create_npc` | 建立 NPC |
| `summarize_npc` | `world.npc_tools.summarize_npc` | NPC 摘要 |
| `set_npc_stats` | `world.npc_tools.set_npc_stats` | 設定 NPC 屬性 |
| `set_llm_config` | `world.npc_tools.set_llm_config` | LLM 設定 |

### 物件管理
| 工具名 | 對應函數 | 說明 |
|--------|----------|------|
| `create_object` | `world.object_tools.create_object_admin` | 建立物件 |
| `move_object` | `world.object_tools.move_object` | 移動物件 |
| `delete_object` | `world.object_tools.delete_object` | 刪除物件 |

### 裝備管理
| 工具名 | 對應函數 | 說明 |
|--------|----------|------|
| `create_equipment` | `world.equipment_tools.create_equipment` | 建立裝備 |
| `clone_equipment` | `world.equipment_tools.clone_equipment` | 複製裝備 |
| `repair_equipment` | `world.equipment_tools.repair_equipment` | 修復裝備 |

### 法術管理
| 工具名 | 對應函數 | 說明 |
|--------|----------|------|
| `create_spell` | `world.magic_tools.create_spell` | 建立法術 |
| `update_spell` | `world.magic_tools.update_spell` | 更新法術 |
| `delete_spell` | `world.magic_tools.delete_spell` | 刪除法術 |
| `list_spells` | `world.magic_tools.list_spells` | 列出法術 |

### 國家管理
| 工具名 | 對應函數 | 說明 |
|--------|----------|------|
| `create_kingdom` | `world.kingdom.create_kingdom` | 建立國家 |
| `add_room_quota` | `world.kingdom.add_room_quota` | 追加額度 |
| `get_kingdom_status` | `world.kingdom.get_kingdom_status` | 國家狀態 |

### 帳號管理
| 工具名 | 對應函數 | 說明 |
|--------|----------|------|
| `create_account` | `world.account_tools.create_account` | 建立帳號 |
| `set_account_role` | `world.account_tools.set_account_role` | 設定角色 |
| `appoint_king` | `world.account_tools.appoint_king` | 指派國王 |

### 戰鬥管理
| 工具名 | 對應函數 | 說明 |
|--------|----------|------|
| `stop_combat` | `world.combat_tools.stop_combat` | 終止戰鬥 |
| `force_win` | `world.combat_tools.force_win` | 強制勝利 |

### 商店管理
| 工具名 | 對應函數 | 說明 |
|--------|----------|------|
| `set_shop_stock` | `world.shop_tools.set_room_shop_stock` | 設定商品 |
| `buy_from_shop` | `world.shop_tools.buy_from_room_shop` | 購買商品 |

### 任務管理
| 工具名 | 對應函數 | 說明 |
|--------|----------|------|
| `give_quest` | `world.quest_tools.give_quest` | 發放任務 |
| `complete_quest` | `world.quest_tools.complete_quest` | 完成任務 |

---

*版本：v1.0 — 2026-06-30*
