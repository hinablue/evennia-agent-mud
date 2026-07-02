# 玩家 RP 指令

agent-mud 透過 `commands/rp_commands.py` 掛載遊戲世界專用 `GameRPSystemCmdSet`，不直接修改 Evennia contrib `rpsystem.py`。

## 指令與繁中 alias

| 功能 | 英文指令 | 繁中 alias | 說明 |
|------|----------|------------|------|
| 動作描述 | `emote`, `:` | `動作`, `表情` | 描述角色動作，可使用 RPSystem `/ref` 標記指向同房間角色或物件。 |
| 說話 | `say`, `"`, `'` | `說`, `講`, `說話` | 以角色身分對目前房間說話。 |
| 短描 | `sdesc` | `短描`, `外貌`, `描述` | 設定或查看自己的短描述。 |
| 姿態 | `pose` | `姿態`, `姿勢` | 設定目前靜態姿態；另支援 `預設`、`重置`、`清除` 作為 `default` / `reset` 模式入口。 |
| 辨認 | `recog`, `recognize` | `認出`, `記住` | 將同房間對象的短描記成私人稱呼；中文分隔詞可用 `作為`、`叫做`。 |
| 忘記辨認 | `forget` | `忘記` | 移除既有私人稱呼。這個 alias 會先正規化成 upstream `forget`，避免走錯 `recog` 分支。 |
| 面具 | `mask` | `面具`, `偽裝` | 暫時以新的短描遮蔽身分，並停用他人對你的辨認。 |
| 取下面具 | `unmask` | `卸下面具`, `脫下面具`, `解除偽裝` | 恢復原本短描。這些 alias 會先正規化成 upstream `unmask`，避免走錯 `mask` 分支。 |

## 範例

```text
說 今天風有點冷。
動作 /me 看向 /高個子男人。
短描 穿深色外套的年輕工程師
姿態 靠在牆邊整理手套。
認出 高個子男人 作為 Hina
忘記 Hina
面具 戴銀色面具的旅人
卸下面具
```

## 維護規則

- 第一層只包裝 command class 與 alias，不 fork 整份 contrib `rpsystem.py`。
- `forget` / `unmask` 這類依賴 `cmdstring` 分支的 alias 必須先正規化，再交給 upstream `func()`。
- 玩家可見文案可在 `commands/rp_commands.py` 逐個 command 覆寫；parser/helper 仍優先沿用 contrib。
