"""檔案式 help 條目。"""

HELP_ENTRY_DICTS = [
    {
        "key": "evennia",
        "aliases": ["ev"],
        "category": "一般",
        "locks": "read:perm(Developer)",
        "text": """
Evennia 是以 Python 撰寫的 MU 遊戲伺服器與開發框架。你可以在
https://www.evennia.com 取得更多資訊。

# 子主題

## 安裝

安裝說明可參考 https://www.evennia.com。

## 社群

如果你需要幫助，或想和其他開發者交流，可以參考以下管道。

### 討論區

GitHub Discussions：
https://github.com/evennia/evennia/discussions

### Discord

官方 Discord：
https://discord.gg/AJJpcRUhtF
        """,
    },
]
