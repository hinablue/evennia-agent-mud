# Game RPSystem CmdSet Implementation Plan

> **For Hermes:** Use subagent-driven-development skill to implement this plan task-by-task.

**Goal:** 把目前直接引用 `evennia.contrib.rpg.rpsystem.RPSystemCmdSet` 的方式，改成 agent-mud 遊戲世界專用的 RP CmdSet，讓 RP 指令可逐步本地化、加中文 alias、限制權限與修補行為，而不修改 Evennia contrib 原始碼。

**Architecture:** 保留 `ContribRPCharacter`、`ContribRPObject`、`ContribRPRoom` 作為 typeclass mixin，因為目前角色、物件、房間已經繼承它們。只把指令註冊層抽成 `commands/rp_commands.py`，建立 `GameRPSystemCmdSet`。第一步以 wrapper 方式復用 upstream command classes，第二步再逐一覆寫需要改文案或行為的 command。

**Tech Stack:** Evennia CmdSet / Command、agent-mud `commands/default_cmdsets.py`、host-side stub tests、Docker Evennia live smoke。

---

## Baseline facts

已讀到的現況：

- Upstream 檔案：`~/Workspace/Evennia/evennia/evennia/contrib/rpg/rpsystem/rpsystem.py`
- `RPSystemCmdSet` 目前只註冊六個指令：`CmdEmote`、`CmdSay`、`CmdSdesc`、`CmdPose`、`CmdRecog`、`CmdMask`。
- agent-mud 目前在 `commands/default_cmdsets.py` 第 25 行直接 `from evennia.contrib.rpg.rpsystem import RPSystemCmdSet`，第 96 行 `self.add(RPSystemCmdSet())`。
- agent-mud 已經在 typeclass 層引用 contrib：
  - `typeclasses/characters.py`：`Character(..., ContribRPCharacter)`
  - `typeclasses/objects.py`：`Object(..., ContribRPObject)`
  - `typeclasses/rooms.py`：`Room(..., ContribRPRoom)`
- 因此最小安全改法是先只替換 CmdSet，不動 typeclass 繼承。

## Hypothesis

可以做，而且應該做成遊戲世界專用 CmdSet。

理由：

1. 目前 upstream `RPSystemCmdSet` 的 command 文案大多是英文，直接掛在遊戲世界會讓玩家指令體驗不一致。
2. agent-mud 已經有大量本地玩家指令與中文 alias，RP 指令應該同樣由遊戲 repo 控制。
3. 不應該改 `~/Workspace/Evennia/evennia/.../contrib` 來客製遊戲行為，因為那是 framework/contrib source，不是遊戲世界邏輯。
4. wrapper-first 可以降低風險：先證明 cmdset replacement 行為等價，再逐步本地化。

## Success criteria

- `CharacterCmdSet` 不再直接 import 或 add upstream `RPSystemCmdSet`。
- 新增 `commands/rp_commands.py`，提供 `GameRPSystemCmdSet`。
- `GameRPSystemCmdSet` 註冊原本六個 RP command，並可新增中文 alias。
- 現有 `ContribRPCharacter/Object/Room` 繼承不受影響。
- Unit test 能證明 `CharacterCmdSet` 註冊的是 game cmdset。
- Live smoke 能在 Evennia container 中確認 `say`、`emote`、`pose`、`sdesc` 至少仍可被解析。

## Independent failure signals

- `CharacterCmdSet.at_cmdset_creation()` import 失敗。
- `say` 或 `emote` 被 default command 覆蓋回去，沒有使用 RPSystem emote path。
- `sdesc`、`recog`、`mask` 因 caller 沒有 `sdesc`/`recog` handler 而出錯。
- 新 CmdSet 重複註冊，導致同名 command 多重匹配。
- test stub 因仍假設 `evennia.contrib.rpg.rpsystem.RPSystemCmdSet` 而掩蓋真實 import 變化。

## Ablation expectations

- 只替換 cmdset import，不覆寫 command class：行為應與現在完全等價。
- 再加入中文 aliases：英文原 key 應繼續可用，中文 alias 應解析到同一 command。
- 若本地化 command message：只改玩家可見文案，不改 `parse_sdescs_and_recogs`、`send_emote`、handler 資料結構。

---

## Task 1: Add a game-owned RP command module

**Objective:** 建立遊戲世界自己的 RP CmdSet 入口，不碰 Evennia contrib source。

**Files:**

- Create: `commands/rp_commands.py`
- Test: `tests/test_player_commands.py`

**Implementation shape:**

```python
"""Game-local RP command set wrappers."""

from evennia.commands.cmdset import CmdSet
from evennia.contrib.rpg.rpsystem.rpsystem import (
    CmdEmote,
    CmdMask,
    CmdPose,
    CmdRecog,
    CmdSay,
    CmdSdesc,
)


class GameRPSystemCmdSet(CmdSet):
    """Game-local RP command set.

    This mirrors Evennia's contrib RPSystemCmdSet first, then gives agent-mud
    a stable place to localize aliases, help text, and player-facing messages.
    """

    key = "agent_mud_rpsystem_cmdset"

    def at_cmdset_creation(self):
        """Populate RP commands used by the game world."""
        self.add(CmdEmote())
        self.add(CmdSay())
        self.add(CmdSdesc())
        self.add(CmdPose())
        self.add(CmdRecog())
        self.add(CmdMask())
```

**Verification:**

- Host syntax: `python -m py_compile commands/rp_commands.py commands/default_cmdsets.py`
- Existing player command tests still import.

## Task 2: Switch CharacterCmdSet to the game-owned CmdSet

**Objective:** 讓玩家角色掛載 `GameRPSystemCmdSet`，而不是 upstream `RPSystemCmdSet`。

**Files:**

- Modify: `commands/default_cmdsets.py`
- Test: `tests/test_player_commands.py`

**Code change:**

```python
# replace
from evennia.contrib.rpg.rpsystem import RPSystemCmdSet

# with
from .rp_commands import GameRPSystemCmdSet
```

```python
# replace
self.add(RPSystemCmdSet())

# with
self.add(GameRPSystemCmdSet())
```

**Test update:**

- Update stubs so `evennia.commands.cmdset.CmdSet` exists.
- Add `commands.rp_commands.GameRPSystemCmdSet` import through real module, not a stub.
- Extend registration test to assert `agent_mud_rpsystem_cmdset` or the six RP command keys are present.

**Expected result:**

- `CharacterCmdSet.at_cmdset_creation()` still works.
- No direct `RPSystemCmdSet` import remains in `commands/default_cmdsets.py`.

## Task 3: Add bilingual aliases without changing behavior

**Objective:** 加中文入口，但先不改核心 RP parser。

**Files:**

- Modify: `commands/rp_commands.py`
- Test: new or existing test in `tests/test_player_commands.py`

**Implementation shape:**

Create light subclasses only for metadata:

```python
class CmdGameEmote(CmdEmote):
    """Describe an action in the room."""

    aliases = [":", "動作", "表情"]


class CmdGameSay(CmdSay):
    """Speak as your character."""

    aliases = ['"', "'", "說", "講"]
```

Likely alias set:

- `emote`：`動作`, `表情`
- `say`：`說`, `講`
- `sdesc`：`短描`, `外貌`
- `pose`：`姿態`, `姿勢`
- `recog`：`認出`, `記住`
- `forget`：保留 upstream alias，另補 `忘記` 需要小心，因為 upstream `CmdRecog.func()` 用 `self.cmdstring == "forget"` 判斷 forget mode。若加 `忘記`，必須覆寫判斷，不能只加 alias。
- `mask`：`面具`, `偽裝`
- `unmask`：同樣需要注意 upstream 用 `self.cmdstring == "mask"`，中文 alias 可能需要覆寫判斷。

**Important constraint:**

`forget`、`unmask` 這類依賴 `cmdstring` 的 alias 不要只加中文 alias。先只加不會改分支語義的 alias，或在同一任務覆寫 `func()` 的 mode 判斷。

## Task 4: Localize player-facing messages command by command

**Objective:** 把 RP commands 的玩家可見文字改成繁中，同時保持 parser/helper 不變。

**Files:**

- Modify: `commands/rp_commands.py`
- Tests: `tests/test_rp_commands.py` or extend `tests/test_player_commands.py`

**Order:**

1. `CmdGameSay`，最小，只有空訊息錯誤與 `at_pre_say` 互動。
2. `CmdGameEmote`，空訊息錯誤。
3. `CmdGameSdesc`，查看、clear、設定文案。
4. `CmdGamePose`，usage、不可 pose、過長、成功文案。
5. `CmdGameRecog`，usage、list、remember、forget、多重匹配文案。
6. `CmdGameMask`，mask/unmask 文案與中文 alias mode 判斷。

**Rule:**

不要 fork 整個 `rpsystem.py`。只覆寫 command class 需要改的 `func()` / `get_help()`。`send_emote`、`parse_sdescs_and_recogs`、`SdescHandler`、`RecogHandler` 仍由 contrib 提供。

## Task 5: Add focused tests

**Objective:** 用 lightweight stubs 驗證 cmdset registration 與 alias metadata，不先碰 DB。

**Files:**

- Modify: `tests/test_player_commands.py`, or create `tests/test_rp_commands.py`

**Test targets:**

- `GameRPSystemCmdSet.at_cmdset_creation()` adds six commands.
- `CharacterCmdSet.at_cmdset_creation()` includes RP commands through the game cmdset path.
- Alias tests cover safe aliases.
- Explicit tests for `忘記` / `卸下面具` only after mode logic is overridden.

**Command:**

```bash
cd /home/hina/services/data/agent-mud
python -m unittest tests.test_player_commands -v
```

If direct host imports fail due Evennia/Django imports, use the existing stub approach in `tests/test_player_commands.py` or run inside Docker with Django settings.

## Task 6: Live smoke in Evennia container

**Objective:** 證明不是只有 unit test 能 import，而是 live server 可解析指令。

**Command pattern:**

```bash
docker compose -f /home/hina/services/docker-compose.yaml ps evennia
docker compose -f /home/hina/services/docker-compose.yaml exec -T evennia bash -lc 'cd /opt/evennia/game && python -m py_compile commands/rp_commands.py commands/default_cmdsets.py'
docker compose -f /home/hina/services/docker-compose.yaml exec -T evennia bash -lc 'cd /opt/evennia/game && evennia shell -c "from commands.default_cmdsets import CharacterCmdSet; c=CharacterCmdSet(); c.at_cmdset_creation(); print([getattr(cmd, \"key\", None) for cmd in c.commands if getattr(cmd, \"key\", None) in (\"say\", \"emote\", \"sdesc\", \"pose\", \"recog\", \"mask\")])"'
```

**Expected:**

Prints all six RP command keys once.

## Task 7: Docs sync if behavior or aliases change

**Objective:** 玩家文件不要漂移。

**Files to check:**

- `docs/` under agent-mud, especially player command references.
- Static HTML docs if they mention player commands.

**Rule:**

如果只是 wrapper replacement，不需要大改 docs。如果新增中文 alias 或改 player-visible behavior，就同步玩家命令文件。

## Recommended implementation boundary

第一輪我會只做 Tasks 1, 2, 5, 6。也就是：做成遊戲世界專用 CmdSet，但保持行為等價。

第二輪再做 Tasks 3, 4, 7。也就是：中文 alias 和繁中文案。

這樣風險最低，因為第一輪如果出問題，問題只可能在 cmdset replacement，不會混入本地化與 parser 行為變更。
