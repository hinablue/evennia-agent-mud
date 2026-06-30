# `@agentworld` 國家 CRUD 功能實作計畫

> **For Hermes:** 若要照這份計畫落地，先走 TDD；每完成一個 task 就跑對應測試，再進下一步。

**Goal:** 把目前分散在 `@kingdom` / `@king` / `world.kingdom` 的國家管理能力，整理成 `@agentworld` 內可操作的國家 CRUD 介面，並明確落實權限：**GM = 全 CRUD**、**King = 只可 Read / Update，不可 Create / Delete**。

**Architecture:** 不重做整套 Kingdom 模型，直接沿用既有 `world/kingdom.py` 的 `Kingdom` Script 與 `change_name()`、`create_kingdom()` 等能力。把 `@agentworld` 擴成新的 country-* switches，並把目前散在指令層的國家操作搬回 `world/kingdom.py` 成為共用 helper，避免 `@agentworld`、`@king`、`@kingdom` 各自複製邏輯。

**Tech Stack:** Evennia MuxCommand、`DefaultScript` Kingdom model、專案既有 unit tests（`unittest` + stub/mocks）。

---

## 1. 現況摘要（依目前程式）

### 已存在
- `world/kingdom.py`
  - `Kingdom` script
  - `create_kingdom()`
  - `get_kingdom_by_name()`
  - `get_kingdom_status()`
  - `change_name()` / `delete()` instance methods
- `commands/kingdom_admin.py`
  - GM 用的 `@kingdom/create|list|status|quota|delete`
- `commands/king_admin.py`
  - King 用的 `@king/status`、`@king/name`
- `commands/world_admin.py`
  - 目前只有 live world build / addroom / adddetail / addscenery / addexit / move / role
  - 已有 per-switch 權限閘道，King 僅能用少數 switch

### 問題
- 國家管理入口分散：GM 在 `@kingdom`，King 在 `@king`，世界管理在 `@agentworld`
- 使用者要求要「放在 `@agentworld` 裡」
- 現有 `world/kingdom.py` helper 不完整：
  - rename / delete / quota / entrance / ownership cleanup 邏輯沒有完整抽成 command-agnostic API
- `King 可 Update 但不可 Create/Delete` 的規則，目前在 `@agentworld` 對 country entity 還不存在

---

## 2. 建議指令介面

不要把子命令塞成自由字串解析，直接沿用 Evennia switch 習慣，新增明確 switches。

### `@agentworld` 新增 switches

#### GM 全功能
- `@agentworld/countrycreate <King名稱>=<國名>,<入口房間>,<額度>`
- `@agentworld/countries`
- `@agentworld/countrystatus <國名>`
- `@agentworld/countryrename <國名>=<新國名>`
- `@agentworld/countryquota <國名>=<新總額度>`
- `@agentworld/countryentrance <國名>=<入口房間>`
- `@agentworld/countrydelete <國名>`

#### King 只開 UR
- `@agentworld/countries`
  - 只顯示自己的國家
- `@agentworld/countrystatus`
  - 不帶參數時預設看自己的國家
  - 若帶別國名，拒絕
- `@agentworld/countryrename <新國名>`
  - King 模式不需要左側國名，直接改自己國家
  - 若保留 `lhs=rhs` 統一格式，也必須驗證 lhs 為自己國家

### 為什麼不用 `countryupdate`
`update` 在這裡實際上不是單一欄位更新，而是多種更新操作：
- rename
- quota
- entrance room

拆成多個 switch 可讓權限矩陣更清楚：
- King 只開 `countryrename`
- `countryquota` / `countryentrance` 仍是 GM-only

---

## 3. 權限矩陣

| Switch | GM/Admin/Developer | King | 說明 |
|---|---:|---:|---|
| `countrycreate` | ✅ | ❌ | 建國一定是 staff 行為 |
| `countries` | ✅ | ✅ | King 只看自己的國家 |
| `countrystatus` | ✅ | ✅ | King 只能看自己的國家 |
| `countryrename` | ✅ | ✅ | King 只能改自己的國名 |
| `countryquota` | ✅ | ❌ | 額度屬於 staff 控管 |
| `countryentrance` | ✅ | ❌ | 首間房/入口屬於 GM 結構管理 |
| `countrydelete` | ✅ | ❌ | 刪國是 destructive staff action |

這樣正好對應你要的：
- **GM = CRUD 全開**
- **King = UR only**（這裡的 U 明確落在 rename）

---

## 4. 檔案層級改動規劃

### A. `world/kingdom.py` —— 抽出共用國家操作 API

**目標：** 讓 command layer 不再直接拼業務流程。

**Modify:** `world/kingdom.py`

新增/整理 helper：
- `list_kingdoms()`
- `rename_kingdom(kingdom, new_name)`
- `set_kingdom_quota(kingdom, new_total)`
- `set_kingdom_entrance(kingdom, room)`
- `delete_kingdom(kingdom)`
- `resolve_caller_kingdom(caller)`

建議規則：
1. `rename_kingdom()`
   - 包住現有 `kingdom.change_name(new_name)`
   - 先做空字串 / 同名 / 重名驗證
   - 回傳標準 dict payload（`message`, `old_name`, `new_name`）
2. `set_kingdom_quota()`
   - 不要沿用 `add_room_quota()` 做差值心算
   - 改成明確設定總額度，回傳 `old_quota`, `new_quota`
3. `set_kingdom_entrance()`
   - 重設 `entrance_room`
   - 補 `king_entrance` / `kingdom:<name>` tag
   - 同步更新 `king.home`
4. `delete_kingdom()`
   - 包住 `Kingdom.delete()`，但補上前置檢查與報告
   - 最少要決定：
     - 是否允許刪除仍有 King / 玩家 / 自建房的國家
     - 若允許，清理策略是什麼
   - **建議先走保守版**：
     - 若仍有角色 nationality = 該國，拒絕刪除
     - 若仍有 `kingdom:<name>` 房間/物件，拒絕刪除
     - 先讓 GM 手動清場再刪
   - 這樣第一版比較安全，不會不小心把 live 世界炸掉

### B. `commands/world_admin.py` —— 把 country 管理正式併進 `@agentworld`

**目標：** 讓 `@agentworld` 成為唯一主要入口。

**Modify:** `commands/world_admin.py`

要改的地方：
1. `switch_options`
   - 加入：
     - `countrycreate`
     - `countries`
     - `countrystatus`
     - `countryrename`
     - `countryquota`
     - `countryentrance`
     - `countrydelete`
2. `KING_ALLOWED_SWITCHES`
   - 在既有 live-world switches 之外，加入：
     - `countries`
     - `countrystatus`
     - `countryrename`
3. `_ensure_switch_access()`
   - 目前 King 只允許 addroom/adddetail/addscenery/addexit
   - 要擴成「King 可用 live-building + country R/U subset」
   - 建議拆成：
     - `KING_WORLD_ALLOWED_SWITCHES`
     - `KING_COUNTRY_ALLOWED_SWITCHES`
   - 避免一個 set 越長越難讀
4. `_show_help()`
   - 明寫 country switches 與權限差異
   - 避免 stale help
5. `func()` routing
   - 新增 `_handle_countrycreate()` / `_handle_countries()` / `_handle_countrystatus()` / `_handle_countryrename()` / `_handle_countryquota()` / `_handle_countryentrance()` / `_handle_countrydelete()`

### C. `commands/king_admin.py` —— 避免雙重邏輯漂移

**目標：** 若 `@king` 保留，至少不要再自己維護 rename/status 邏輯。

**Modify:** `commands/king_admin.py`

建議：
- `_handle_status()` 改呼叫 `world.kingdom.get_kingdom_status()` + 共用 formatter
- `_handle_name()` 改呼叫 `world.kingdom.rename_kingdom()`
- help 補一句：`國家資料也可用 @agentworld/countrystatus 與 /countryrename`

這一步不是必須砍 `@king`，而是先把邏輯收斂。

### D. `commands/kingdom_admin.py` —— 過渡相容層

**目標：** 避免舊 GM 操作馬上壞掉。

**Modify:** `commands/kingdom_admin.py`

建議兩種做法二選一：
1. **保守相容**：保留 `@kingdom`，但內部改呼叫新的 `world.kingdom` helper
2. **直接瘦身**：help 文案標記 `@agentworld/country*` 為主入口，`@kingdom` 為 legacy alias

我建議先走 **保守相容**。

### E. 測試

**Modify:**
- `tests/test_world_admin.py`
- `tests/test_kingdom.py`
- 視需要新增 `tests/test_king_admin.py`（如果目前沒有，就先把 rename/status 的 shared helper 測到位）

#### 必補測試案例

`tests/test_world_admin.py`
- Admin 可 route `countrycreate`
- Admin 可 route `countrydelete`
- King 可 route `countries`
- King 可 route `countrystatus`
- King 可 route `countryrename`
- King 不可 route `countrycreate`
- King 不可 route `countrydelete`
- King 不可 route `countryquota`
- King 不可看別國 `countrystatus`

`tests/test_kingdom.py`
- `rename_kingdom()` 同名拒絕
- `rename_kingdom()` 重名拒絕
- `set_kingdom_quota()` 正確覆寫總額度
- `set_kingdom_entrance()` 同步更新 `king.home`
- `delete_kingdom()` 在有角色/房間殘留時拒絕
- `delete_kingdom()` 安全刪除時會清掉 king 狀態

### F. 文件

**Modify:**
- `docs/module-reference.md`
- `docs/permission-hierarchy-design.md`

文件要同步反映：
- `@agentworld` 新增 country 管理面
- `King` 在 `@agentworld` 不再只有 live-room add* 四個 switch
- 但 `King` 對 country entity 仍只有 UR，沒有 CD

如果之後還要同步外部 HTML，再另外補：
- `agentworld-admin-command.html`
- `game-admin-manual.html`
- 其他對外頁面

---

## 5. 具體任務拆解

### Task 1: 先補 `world/kingdom.py` 的 helper 測試

**Objective:** 先把國家業務規則固定下來，再讓 command layer 接上去。

**Files:**
- Modify: `tests/test_kingdom.py`
- Modify: `world/kingdom.py`

**Step 1: 寫 failing tests**
- 補 `rename_kingdom`, `set_kingdom_quota`, `set_kingdom_entrance`, `delete_kingdom`
- 尤其是 delete 的保守拒絕策略

**Step 2: 跑測試確認失敗**

Run:
```bash
cd /home/hina/services/data/agent-mud && python -m unittest tests.test_kingdom -v
```

**Step 3: 在 `world/kingdom.py` 補 helper**
- 只做最小實作讓測試過
- 回傳統一 dict payload

**Step 4: 重跑測試確認 pass**

Run:
```bash
cd /home/hina/services/data/agent-mud && python -m unittest tests.test_kingdom -v
```

---

### Task 2: 擴充 `@agentworld` switch surface

**Objective:** 把 country CRUD 的公開入口正式掛到 `@agentworld`。

**Files:**
- Modify: `commands/world_admin.py`
- Test: `tests/test_world_admin.py`

**Step 1: 寫 failing routing/access tests**
- 先補 King/GM 的 switch 權限矩陣

**Step 2: 跑測試確認失敗**

Run:
```bash
cd /home/hina/services/data/agent-mud && python -m unittest tests.test_world_admin -v
```

**Step 3: 實作 switches + handlers**
- 加 switch options
- 改 `_ensure_switch_access()`
- 補 handlers
- 補 help

**Step 4: 重跑測試確認 pass**

Run:
```bash
cd /home/hina/services/data/agent-mud && python -m unittest tests.test_world_admin -v
```

---

### Task 3: 收斂 `@king` / `@kingdom` 到 shared helper

**Objective:** 避免 rename/status/create/delete 的業務規則分岔。

**Files:**
- Modify: `commands/king_admin.py`
- Modify: `commands/kingdom_admin.py`

**Step 1: 將 rename/status/create/delete/quota 改呼叫 `world.kingdom` helper**

**Step 2: 補最小 smoke-style unit tests（若需要）**
- 沒有現成 test file 就先補 command routing 的 mock-based test

**Step 3: 跑 targeted tests**

Run:
```bash
cd /home/hina/services/data/agent-mud && python -m unittest tests.test_kingdom tests.test_world_admin -v
```

---

### Task 4: 文件同步

**Objective:** 讓 repo 內設計文件不要再寫舊入口。

**Files:**
- Modify: `docs/module-reference.md`
- Modify: `docs/permission-hierarchy-design.md`

**Step 1: 更新 command reference**
- `@agentworld` 補 country switches
- `@kingdom` 標成 legacy / GM compatibility（若保留）

**Step 2: 更新 permission design**
- 把 King 對 `@agentworld` 的能力從「完全不可用」改成「可用 subset」
- country CRUD matrix 寫清楚

---

### Task 5: 全量驗證

**Objective:** 確認 helper、command、文件一致。

**Files:**
- No code changes expected

**Run:**
```bash
cd /home/hina/services/data/agent-mud && python -m unittest tests.test_kingdom tests.test_world_admin -v
```

如果後面補到更多 command tests，再擴成：
```bash
cd /home/hina/services/data/agent-mud && python -m unittest tests.test_kingdom tests.test_world_admin tests.test_account_admin -v
```

---

## 6. 關鍵設計決策

### 決策 A：`delete country` 第一版先走保守拒絕，不做自動清場
理由：
- 刪國會牽涉 Player、King、自建房、物件、channel、tag
- 現在 `Kingdom.delete()` 只清 `is_king` / `kingdom`，對 live 世界太薄
- 先做「有殘留就拒絕刪除」比較安全

### 決策 B：King 的 `U` 先只開 `rename`
理由：
- quota/entrance 都是結構級權限，不適合 King
- rename 已有既有能力 `@king/name`，最容易收斂進 `@agentworld`
- 這樣最貼近你要的「UR 不能 CD」，又不會讓 U 變得模糊

### 決策 C：保留 `@king` / `@kingdom`，但改成 shared helper frontends
理由：
- 可以逐步遷移，不會一次砍舊操作面
- 主入口雖然轉到 `@agentworld`，但不必硬破壞相容性

---

## 7. 驗收標準

完成後應該滿足：

1. GM 可以：
   - 建國
   - 列國
   - 看國家狀態
   - 改國名
   - 改額度
   - 改入口房
   - 刪國
2. King 只能：
   - 看自己的國家列表/狀態
   - 改自己的國名
3. King 不能：
   - 建國
   - 刪國
   - 改別國
   - 改 quota
   - 改 entrance room
4. `@agentworld` help 與測試都反映這個矩陣
5. repo 內文件同步更新

---

## 8. 我對這版規劃的建議結論

如果要最穩地做，我建議這次 **不要直接移除 `@kingdom` / `@king`**，而是：

- 先把 **國家 CRUD 主入口放進 `@agentworld`**
- 再把 **底層 helper 收斂到 `world/kingdom.py`**
- 舊指令變成相容殼層

這樣改動最小、風險最低，也最符合你要的操作面統一。