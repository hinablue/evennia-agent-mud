"""伺服器會話

伺服器會話是伺服器端記憶體中的表示
連接到遊戲的用戶。  Evennia 每管理一次會話
連接到遊戲。所以一個用戶用多個帳號登入遊戲
客戶端（如果 Evennia 配置為允許）將有多個
會話綁定到一個帳戶物件。 Evennia之間的所有通訊
現實世界的使用者會經歷與該使用者關聯的會話。

需要注意的是，修改Session物件通常不是
除了最定制和異國情調的設計之外，這是必要的 - 甚至
那麼只需添加自訂會話級命令就足夠了
改為 SessionCmdSet。

通常不呼叫該模組。告訴 Evennia 使用該類
在此模組中而不是預設模組中，將以下內容新增至您的
設定檔：

    SERVER_SESSION_CLASS = "server.conf.serversession.ServerSession"
"""

from evennia.server.serversession import ServerSession as BaseServerSession


class ServerSession(BaseServerSession):
    """該類別代表玩家的會話，並且是一個模板
    與 Evennia 通訊的單獨協定。

    每個帳戶每次連線時都會分配一個或多個會話
    到遊戲伺服器。遊戲和帳戶之間的所有通訊都會進行
    透過他們的會議。"""

    pass
