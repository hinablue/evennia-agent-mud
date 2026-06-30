"""MSSP（泥漿伺服器狀態協定）元資訊

修改此檔案以指定哪些 MUD 清單網站將報告有關您的遊戲的資訊。
所有欄位都是靜態的。當前活躍玩家的數量以及您的遊戲的
Evennia 將自動新增目前的正常運作時間。

您不必填寫所有內容（並且大多數欄位不會被所有人顯示/使用）
無論如何，爬蟲）；如果需要，請保留預設值。您需要重新載入伺服器
在更新的資訊可供爬蟲使用之前（重新加載不會
不影響正常運轉時間）。

更改此文件中的值後，您必須向
MUD 網站列出了您想要追蹤的人。然後列表爬蟲會定期
連接到您的伺服器以獲取最新資訊。無需進一步配置
埃文尼亞這邊需要。"""

MSSPTable = {
    # 必填字段
    "NAME": "Mygame",  # 通常與 SERVERNAME 相同
    # 通用的
    "CRAWL DELAY": "-1",  # 限制爬蟲更新清單的頻率。 -1表示無限制
    "HOSTNAME": "",  # 遠端登入主機名
    "PORT": ["4000"],  # telnet 連接埠 - 最重要的連接埠應該是清單中的*最後*！
    "CODEBASE": "Evennia",
    "CONTACT": "",  # 聯絡mud的電子郵件
    "CREATED": "",  # MUD 建立年份
    "ICON": "",  # 圖示 32x32 或更大的 url； <32kb。
    "IP": "",  # 目前或新的 IP 位址
    "LANGUAGE": "",  # 使用的語言名稱，例如英語
    "LOCATION": "",  # 伺服器國家的英文全名
    "MINIMUM AGE": "0",  # 如果不適用則設定為 0
    "WEBSITE": "",  # http:// 您的遊戲網站位址
    # 分類
    "FAMILY": "Evennia",
    "GENRE": "None",  # 成人、奇幻、歷史、恐怖、現代、無或科幻小說
    # 遊戲玩法：冒險、教育、砍殺、無、
    # 玩家對玩家，玩家對環境，
    # 角色扮演、模擬、社交或策略
    "GAMEPLAY": "",
    "STATUS": "Open Beta",  # 允許：Alpha、封閉測試版、公開測試版、即時測試版
    "GAMESYSTEM": "Custom",  # D&D、d20 系統、黑暗世界等。如果是自製程序，請使用自訂
    # 子類型： LASG、中世紀奇幻、第二次世界大戰、科學怪人、
    # Cyber​​punk、Dragonlance 等。若不適用，則無。
    "SUBGENRE": "None",
    # 世界
    "AREAS": "0",
    "HELPFILES": "0",
    "MOBILES": "0",
    "OBJECTS": "0",
    "ROOMS": "0",  # 如果沒有空間則使用 0
    "CLASSES": "0",  # 如果無類別則使用 0
    "LEVELS": "0",  # 如果無等級則使用 0
    "RACES": "0",  # 若無競爭則使用 0
    "SKILLS": "0",  # 如果缺乏技能則使用 0
    # 協議設定為1或0；通常不應更改）
    "ANSI": "1",
    "GMCP": "1",
    "MSDP": "1",
    "MXP": "1",
    "SSL": "1",
    "UTF-8": "1",
    "MCCP": "1",
    "XTERM 256 COLORS": "1",
    "XTERM TRUE COLORS": "0",
    "ATCP": "0",
    "MCP": "0",
    "MSP": "0",
    "VT100": "0",
    "PUEBLO": "0",
    "ZMP": "0",
    # 商業設定為1或0）
    "PAY TO PLAY": "0",
    "PAY FOR PERKS": "0",
    # 招募設定為 1 或 0)
    "HIRING BUILDERS": "0",
    "HIRING CODERS": "0",
    # 擴充變數
    # 世界
    "DBSIZE": "0",
    "EXITS": "0",
    "EXTRA DESCRIPTIONS": "0",
    "MUDPROGS": "0",
    "MUDTRIGS": "0",
    "RESETS": "0",
    # 遊戲（設定為 1 或 0，或給定的選項之一）
    "ADULT MATERIAL": "0",
    "MULTICLASSING": "0",
    "NEWBIE FRIENDLY": "0",
    "PLAYER CITIES": "0",
    "PLAYER CLANS": "0",
    "PLAYER CRAFTING": "0",
    "PLAYER GUILDS": "0",
    "EQUIPMENT SYSTEM": "None",  # “無”、“等級”、“技能”、“兩者”
    "MULTIPLAYING": "None",  # “無”、“受限”、“全部”
    "PLAYERKILLING": "None",  # “無”、“受限”、“全部”
    "QUEST SYSTEM": "None",  # “無”、“仙跑”、“自動化”、“整合”
    "ROLEPLAYING": "None",  # 「無」、「接受」、「鼓勵」、「強制」
    "TRAINING SYSTEM": "None",  # “無”、“等級”、“技能”、“兩者”
    # 世界原創性：“全部庫存”、“大部分庫存”、“大部分原創”、“全部原創”
    "WORLD ORIGINALITY": "All Original",
}
