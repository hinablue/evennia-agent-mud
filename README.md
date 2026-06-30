# 歡迎來到埃文尼亞！

這是您的遊戲目錄，設定後可以讓您開始
馬上你的新遊戲。該目錄的概述可在此處找到：
https://github.com/evennia/evennia/wiki/Directory-Overview#the-game-directory

您可以在閱讀此自述文件後將其刪除
重新排列此遊戲目錄中的內容以適合您自己的感覺
組織（唯一的例外是目錄結構
`server/` 目錄，這是 Evennia 所期望的）。如果你改變結構
但是，您還必須編輯/添加到您的設定檔中以告訴 Evennia
去哪裡找東西。

您的遊戲的主設定檔位於
`server/conf/settings.py` （但你不需要改變它來獲得
開始）。如果您剛剛建立了這個目錄（這表示您已經
如果您遵循預設說明，則有 `virtualenv` 正在執行），
`cd` 到此目錄，然後使用初始化一個新資料庫

    埃文尼亞遷徙

若要啟動伺服器，請進入此目錄並執行

    埃文尼亞開始

這將啟動伺服器，並將輸出記錄到控制台。製作
確保在詢問時創建超級用戶。預設情況下，您現在可以連接
使用 `localhost`、連接埠 `4000` 上的 MUD 用戶端連接到您的新遊戲。  你可以
也可以透過瀏覽器登入 Web 用戶端
`http://localhost:4001`。

# 入門

從這裡開始，您可能想查看初學者教程之一：
http://github.com/evennia/evennia/wiki/Tutorials.

Evennia 的文檔在這裡：
https://github.com/evennia/evennia/wiki.

享受！
