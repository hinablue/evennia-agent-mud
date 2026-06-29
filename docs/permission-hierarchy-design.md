# 三層權限架構設計文件

> **Agent 迷航 — GM / King / Player 權限層級設計**

---

## 1. 概念總覽

```
┌─────────────────────────────────────────────────────────────────┐
│  GM (Admin / Developer) — 上帝視角                               │
│  • 無所不能，建立 Kingdom、分配空房間額度、指定 King 首間房間     │
│  • GM 大陸上的任何物件/房間/出口，King 完全不可更動               │
├─────────────────────────────────────────────────────────────────┤
│  King — 國王（由 GM 建立）                                         │
│  • 只能在「自己國家範圍內」完全掌控                                 │
│  • 第一個房間（與 GM 大陸相連的入口）結構不可改、出入口不可改       │
│  • 房間內容（物品、NPC、描述、detail）可改                         │
│  • 在額度內自建房間/出口/物件，完整擁有權                           │
│  • 可設定國家名稱                                                   │
│  • Home = 第一個房間（GM 指定）                                     │
│  • @agentworld 完全不可用                                           │
│  • 不能碰其他 King 的任何東西                                       │
├─────────────────────────────────────────────────────────────────┤
│  Player（人民）——由 King 建立                                       │
│  • 預設擁有該國國籍                                                  │
│  • Player 之間完全不隔離，只有國籍標記不同                           │
└─────────────────────────────────────────────────────────────────┘
```

---

## 2. 權限字串定義

在 Evennia `Permission` 系統中新增三個專用權限：

| 權限名稱 | 用途 | 對應層級 |
|---------|------|---------|
| `GM` | 原 `Admin`/`Developer` 同義，保留作為最高層 | GM |
| `King` | 國王專屬權限，僅 GM 可授予 | King |
| `Player` | 一般玩家權限，King 建立角色時自動給予 | Player |

> **相容性**：現有 `Admin`、`Developer` 權限保留，`GM` 視為最高層別名；既有指令 `locks = "cmd:perm(Admin) or perm(Developer)"` 維持不變，僅在新增 King/Player 相關指令與物件 lock 時使用新權限字串。

---

## 3. 資料模型擴充

### 3.1 Kingdom（國家）資料表

```python
# world/kingdom.py（新檔）
from evennia import DefaultScript

class Kingdom(DefaultScript):
    """
    國家腳本，掛在 King Character 上（或獨立 GlobalScript 以 key 索引）。
    key = 國名（唯一）
    """
    def at_script_creation(self):
        self.key = ""                 # 國名
        self.db.king = None           # Character (King)
        self.db.gm_continent_rooms = []  # GM 大陸上連結到此國的房間 dbref 清單
        self.db.entrance_room = None  # King 的第一個房間（Home，GM 指定）
        self.db.room_quota = 0        # GM 分配的空房間額度
        self.db.rooms_created = 0     # 已建立房間數
        self.db.nationality_tag = ""  # 國籍標籤，供 Player 打標用（如 "Astra"）
```

### 3.2 Character 擴充屬性

```python
# typeclasses/characters.py（既有 Character 類別擴充）

# King 專用
db.is_king = False           # bool
db.kingdom = None            # 指向 Kingdom script

# Player 專用
db.nationality = ""          # 國籍字串（對應 Kingdom.key）
db.king = None               # 所屬 King（Character）
```

### 3.3 Room / Exit / Object 標記

所有 GM 大陸既有物件、King 首間房間、連結出口，皆打標記：

```python
# GM 大陸物件
obj.tags.add("gm_continent", category="ownership")

# King 首間房間（GM 建立、指定給 King）
room.tags.add("king_entrance", category="ownership")
room.tags.add(f"kingdom:{kingdom_key}", category="ownership")

# King 自建房間/物件/出口
obj.tags.add(f"kingdom:{kingdom_key}", category="ownership")
obj.tags.add("king_created", category="ownership")  # 區分 GM vs King 建立

# 連結 GM 大陸的出口（在 King 首間房間內）
exit.tags.add("gm_link_exit", category="ownership")
exit.tags.add(f"kingdom:{kingdom_key}", category="ownership")
```

---

## 4. Lock Functions（server/conf/lockfuncs.py 新增）

```python
# server/conf/lockfuncs.py

def is_gm(accessing_obj, accessed_obj, *args, **kwargs):
    """GM（Admin/Developer）權限檢查"""
    if not hasattr(accessing_obj, "account"):
        return False
    account = accessing_obj.account
    return account and (account.check_permstring("Admin") or
                        account.check_permstring("Developer") or
                        account.check_permstring("GM"))

def is_king(accessing_obj, accessed_obj, *args, **kwargs):
    """King 權限檢查（需同時擁有 King perm 且 is_king=True）"""
    if not hasattr(accessing_obj, "account"):
        return False
    account = accessing_obj.account
    char = accessing_obj
    return (account and account.check_permstring("King") and
            getattr(char.db, "is_king", False))

def is_king_of(accessing_obj, accessed_obj, *args, **kwargs):
    """
    檢查 accessing_obj 是否為 accessed_obj 所屬國家的 King
    用法：control:is_king_of()、edit:is_king_of()
    accessed_obj 需有 tag category="ownership" 的 kingdom:xxx
    """
    if not (hasattr(accessing_obj, "account") and hasattr(accessed_obj, "tags")):
        return False
    char = accessing_obj
    if not (char.account.check_permstring("King") and getattr(char.db, "is_king", False)):
        return False
    kingdom_tag = accessed_obj.tags.get(category="ownership", key__startswith="kingdom:")
    if not kingdom_tag:
        return False
    kingdom_key = kingdom_tag.split(":", 1)[1]
    return getattr(char.db, "kingdom", None) and char.db.kingdom.key == kingdom_key

def is_same_kingdom(accessing_obj, accessed_obj, *args, **kwargs):
    """雙方是否同一國家（Player 之間、King vs 自家物件）"""
    if not (hasattr(accessing_obj, "db") and hasattr(accessed_obj, "tags")):
        return False
    nat = getattr(accessing_obj.db, "nationality", "")
    if not nat:
        return False
    kingdom_tag = accessed_obj.tags.get(category="ownership", key__startswith="kingdom:")
    if not kingdom_tag:
        return False
    return kingdom_tag.split(":", 1)[1] == nat

def is_gm_continent(accessing_obj, accessed_obj, *args, **kwargs):
    """目標是否屬於 GM 大陸（不可被 King 動）"""
    if not hasattr(accessed_obj, "tags"):
        return False
    return accessed_obj.tags.has("gm_continent", category="ownership")

def is_king_entrance(accessing_obj, accessed_obj, *args, **kwargs):
    """目標是否為 King 首間房間（結構不可改）"""
    if not hasattr(accessed_obj, "tags"):
        return False
    return accessed_obj.tags.has("king_entrance", category="ownership")

def is_gm_link_exit(accessing_obj, accessed_obj, *args, **kwargs):
    """目標出口是否為連結 GM 大陸的出口（King 不可動）"""
    if not hasattr(accessed_obj, "tags"):
        return False
    return accessed_obj.tags.has("gm_link_exit", category="ownership")
```

---

## 5. 物件 Lock 字串設計

| 物件類型 | Lock String | 說明 |
|---------|-------------|------|
| **GM 大陸房間/物件/出口** | `control:is_gm();edit:is_gm();delete:is_gm();call:is_gm()` | 只有 GM 可控制/編輯/刪除/呼叫 |
| **King 首間房間（入口房）** | `control:is_gm() or is_king_of();edit:is_gm() or (is_king_of() and not is_king_entrance());delete:is_gm();call:all()` | King 可編輯內容，但不可改結構、不可刪、不可動 GM 連結出口 |
| **King 首間房間內的 GM 連結出口** | `control:is_gm();edit:is_gm();delete:is_gm();traverse:all()` | 只有 GM 可控制/編輯/刪除，所有人可通行 |
| **King 自建房間/物件/出口** | `control:is_gm() or is_king_of();edit:is_gm() or is_king_of();delete:is_gm() or is_king_of();call:is_gm() or is_king_of()` | GM + 該國 King 全權 |
| **其他 King 的物件** | `control:is_gm();edit:is_gm();delete:is_gm();call:is_gm()` | 對非所屬 King 等同 GM 大陸（不可碰） |
| **Player 建立的物品（若開放）** | `control:is_gm() or is_king_of() or id(%i) or is_same_kingdom();edit:is_gm() or is_king_of() or id(%i)` | 自己、同國 King/Player、GM 可動 |

> **注意**：Evennia 的 `call` lock 控制 `obj.call()`（如使用技能、觸發腳本），一般物件不需特別限制；重點在 `control`（移動/銷毀/重命名）、`edit`（屬性修改）、`delete`。

---

## 6. 指令權限（Command Locks）

### 6.1 新增 King 專用指令集

```python
# commands/king_admin.py（新檔）
class CmdKingAdmin(MuxCommand):
    """King 管理自己的國家"""
    key = "@kingdom"
    aliases = ["@king"]
    locks = "cmd:perm(King)"          # 只有 King 權限可用
    help_category = "King"
    switch_options = ("status", "name", "buildroom", "buildexit", "buildobj", "help")

    # /status      → 看自己國家狀態、額度、房間列表
    # /name 新國名 → 更改國家名稱（需 GM 同意或自行可改，視政策）
    # /buildroom   → 在額度內建房間
    # /buildexit   → 建出口（限自家房間間）
    # /buildobj    → 放置物件/NPC
```

### 6.2 既有指令 Lock 調整

| 指令 | 原 Lock | 新 Lock | 說明 |
|------|---------|---------|------|
| `@agentworld` | `cmd:perm(Admin) or perm(Developer)` | `cmd:perm(Admin) or perm(Developer)` | **King 完全不可用**（保持原樣，GM 專用） |
| `@agentaccount` | `cmd:perm(Admin) or perm(Developer)` | 同上 | GM 專用 |
| `@agentplayer` | `cmd:perm(Admin) or perm(Developer)` | `cmd:perm(Admin) or perm(Developer) or perm(King)` | **King 可用**（建立/管理自國 Player） |
| 一般玩家指令 | `cmd:pperm(Player)` | 同上 | Player 正常使用 |

> **關鍵**：`@agentplayer` 開放 `perm(King)`，但 `player_tools.py` 內部需加入檢查：**King 只能建立/操作自己國籍的 Player**，且建立時自動打上 `db.nationality = kingdom_key`、`db.king = king_char`。

---

## 7. @agentplayer / player_tools.py 修改重點

```python
# world/player_tools.py 關鍵修改點

def create_player(caller, name, home_room, desc, aliases, account_key=None):
    """
    caller 可能是 GM (Account) 或 King (Character)
    - 若 caller 是 King：強制 home_room 必須在自國範圍內，自動打國籍
    - 若 caller 是 GM：可指定任何 home_room，不打國籍（或由 GM 指定）
    """
    king_char = None
    if hasattr(caller, "db") and getattr(caller.db, "is_king", False):
        king_char = caller
        # 驗證 home_room 是否屬於自國
        if not home_room.tags.has(f"kingdom:{king_char.db.kingdom.key}", category="ownership"):
            raise PlayerSpecError("King 只能在自國範圍內建立角色。")
        nationality = king_char.db.kingdom.key
    else:
        nationality = ""

    # ... 建立 Character ...
    character.db.nationality = nationality
    if king_char:
        character.db.king = king_char
```

---

## 8. King 建國流程（GM 操作）

### 8.1 GM 指令：`@kingdom/create <King名稱>=<國名>,<首間房間>,<房間額度>`

```python
# commands/kingdom_admin.py（GM 專用，locks = "cmd:perm(Admin) or perm(Developer)"）
switch_options = ("create", "list", "delete", "quota", "help")

def _handle_create(self):
    # 1. 建立/找到 King Character（@agentplayer/create King名=首間房間|描述|...）
    # 2. 給 King Character 權限：account.permissions.add("King")
    # 3. 設定 character.db.is_king = True
    # 4. 建立 Kingdom script，掛在 King character 上
    #    kingdom.db.king = king_char
    #    kingdom.db.entrance_room = entrance_room
    #    kingdom.db.room_quota = quota
    #    kingdom.db.nationality_tag = 國名
    # 5. 將首間房間打標：king_entrance + kingdom:<國名>
    # 6. 將首間房間內連往 GM 大陸的出口打標：gm_link_exit + kingdom:<國名>
    # 7. 設定 King character.home = 首間房間
```

### 8.2 King 後續自建流程

- `@kingdom/buildroom 房間名=描述` → 檢查 `kingdom.db.rooms_created < quota`，在自國任意房間下建新室，自動打 `kingdom:<國名>` + `king_created`。
- `@kingdom/buildexit 來源=出口名|目標|alias` → 來源/目標皆需屬自國。
- `@kingdom/buildobj 房間=物件名|alias|描述` → 物件打自國標籤。
- `@kingdom/deleteroom 房間` → 見 §12.2 刪房邏輯；強制遷移房內 Player 到入口房、刪除所有物品/NPC、刪除房間。
- `@kingdom/name 新國名` → 修改 `kingdom.key`、所有自國物件 tag、Player `nationality`。

---

## 9. 隔離規則總表

| 操作 | GM | King A | King B | Player (A國) | Player (B國) |
|------|----|--------|--------|--------------|--------------|
| 控制 GM 大陸物件 | ✅ | ❌ | ❌ | ❌ | ❌ |
| 控制 King A 首間房間結構 | ✅ | ❌ | ❌ | ❌ | ❌ |
| 編輯 King A 首間房間內容 | ✅ | ✅ | ❌ | ❌ | ❌ |
| 動 King A 首間房間的 GM 連結出口 | ✅ | ❌ | ❌ | ❌ | ❌ |
| 控制 King A 自建房間/物件/出口 | ✅ | ✅ | ❌ | ❌* | ❌* |
| 控制 King B 自建房間/物件/出口 | ✅ | ❌ | ✅ | ❌ | ❌* |
| 使用 `@agentworld` | ✅ | ❌ | ❌ | ❌ | ❌ |
| 使用 `@agentplayer` | ✅ | ✅（限自國） | ✅（限自國） | ❌ | ❌ |
| Player 互動（說話、交易、組隊） | ✅ | ✅ | ✅ | ✅ | ✅（跨國無限制） |

\* Player 若持有物品（`id(%i)` lock）可控制自己的裝備，但無法動房間結構。

---

## 10. 實作步驟建議

1. **資料層**：新增 `world/kingdom.py`、`world/kingdom_tools.py`；擴充 `Character.db` 欄位。
2. **Lock 層**：`server/conf/lockfuncs.py` 加入 7 個新 lockfunc。
3. **標記既有資料**：一次性腳本掃描現有 GM 大陸房間/出口/物件，打 `gm_continent` 標籤。
4. **GM 指令**：新增 `commands/kingdom_admin.py`（`@kingdom`）。
5. **King 指令**：新增 `commands/king_admin.py`（`@kingdom` 同名不同 lock，或用 `@king`）。
6. **Player 建立邏輯**：修改 `world/player_tools.py`、`commands/player_admin.py`。
7. **現有 `@agentworld` 物件建立流程**：建立時自動判斷 caller 是 GM 還是 King，打對應 tag。
8. **測試**：單元測試 lockfunc、整合測試 King 建國→建房→建 Player→跨國隔離。

---

## 11. 相容性與遷移

- 現有 `Admin`/`Developer` 權限帳號**不需變更**，繼續享有 GM 全權。
- 既有 Player 角色若無 `db.nationality`，視為「無國籍/流浪者」，不受 King 管轄，GM 可後續指派。
- 既有房間/物件若無 ownership tag，視為 GM 大陸資產，King 不可動。

---

## 12. 設計決策（已確認）

| # | 問題 | 決策 | 實作影響 |
|---|------|------|---------|
| 1 | King 可否自行改國名？ | ✅ **可以** | `@kingdom/name` 直接可用，King 修改時同步更新 `Kingdom.key`、所有自國物件的 `kingdom:` tag、旗下 Player 的 `nationality` |
| 2 | 額度用完怎麼加？ | **GM 追加** | 新增 `@kingdom/quota <國名>=<新額度>`（GM 專用）；King 看得到額度但不能改 |
| 3 | King 刪除自建房間時裡面的 Player/物品？ | **Player → 入口房，物品 → 消滅** | `@kingdom/deleteroom` 執行時：① 將房內所有 Player 強制移到入口房 ② 刪除房內所有物件/NPC ③ 刪除房間本身。入口房不可刪（lock 已保護） |
| 4 | Player 重生預設 home？ | **入口房** | King 建立 Player 時 `character.home = kingdom.db.entrance_room`（預設）；Player 死亡後 `at_post_unpuppet` 或重生指令回到 home |
| 5 | 跨國頻道隔離？ | **隔離** | 每個 Kingdom 擁有獨立公開頻道，Player 預設只能看到/發言於自國頻道；GM 可跨頻道（override）。跨國私訊 (`tell`) 不受限 |
| 6 | 次權限層（大臣/官員）？ | **不需要** | 不設計次權限層，King 為該國唯一管理者 |

---

## 12.1 補充設計：跨國頻道隔離

### 頻道架構

```
Channel: "public"               → GM 頻道（既有，不動）
Channel: "kingdom:<國名>"       → 各國公共頻道（King 建國時自動建立）
Channel: "kingdom_gm"           → GM ↔ King 之間共用頻道（可選）
```

### Lock 設計

| 頻道 | 訂閱 lock | 發言 lock | 說明 |
|------|----------|----------|------|
| `public` | `all()` | `all()` | 既有頻道，所有 Player 可聽可發 |
| `kingdom:<國名>` | `is_same_kingdom()` | `is_same_kingdom()` | 只有該國 Player 可聽可發 |
| `kingdom_gm` | `is_gm() or is_king()` | `is_gm() or is_king()` | GM + 所有 King 共用 |

### King 建國時

```python
# kingdom_tools.py
def create_kingdom_channels(kingdom_key):
    chan_name = f"kingdom:{kingdom_key}"
    chan = create.create_channel(
        chan_name,
        locks=f"listen:is_same_kingdom();send:is_same_kingdom()",
        desc=f"{kingdom_key} 國公共頻道"
    )
    # 自動將 King 自己加入訂閱
    chan.connect(king_char)
```

### Player 建角色時

```python
# 建立 Player 後自動訂閱自國頻道
chan = ChannelDB.objects.channel_search(f"kingdom:{nationality}")
if chan:
    chan.connect(player_char)
```

### 跨國私訊

`tell` / `page` 指令不受隔離限制，Player 之間可跨國私訊。Lock 維持 `send:all()`。

---

## 12.2 補充設計：King 刪房邏輯

```python
# kingdom_tools.py
def delete_king_room(king_char, room):
    """King 刪除自建房間"""
    kingdom = king_char.db.kingdom

    # 1. 防呆：不可刪入口房
    if room.tags.has("king_entrance", category="ownership"):
        raise CommandError("不可刪除入口房間。")

    # 2. 防呆：不可刪非自國房間
    if not room.tags.has(f"kingdom:{kingdom.key}", category="ownership"):
        raise CommandError("你只能刪除自己國家的房間。")

    # 3. 遷移房內 Player 到入口房
    for char in room.contents_get(content_type="character"):
        if char.has_account:  # Player
            char.move_to(kingdom.db.entrance_room, quiet=False)
            char.msg(f"你所處的房間已被國王拆除，你被傳送回 {kingdom.key} 的入口。")

    # 4. 刪除房內所有物件（NPC、物品）
    for obj in room.contents_get(content_type="object"):
        obj.delete()

    # 5. 刪除房間本身（連帶其出口一併移除）
    room.delete()

    # 6. 更新額度計數
    kingdom.db.rooms_created -= 1
```

---

*文件版本：v2.0 — 2025-06-29*  
*作者：Rosie (許御琪) 為 Hina Chen 整理*