# HTML 模板

模板是 HTML 文件，（通常）有特殊的 `{{ ... }}` 模板
其中的標記允許 Evennia/Django 在 Web 中插入動態內容
頁。一個例子是列出遊戲中目前有多少用戶在線上。

模板由 _views_ 引用 - Python 函數或可呼叫類
準備模板所需的資料並將其“渲染”為成品
傳回給使用者的 HTML 頁面。

您可以透過覆蓋此資料夾中的 Evennia 預設範本來替換它們。
原件位於 `evennia/web/templates/` - 只需將範本複製到
此處對應的位置（因此網站的 `index.html` 應複製到
`website/index.html` 可以修改）。重新載入伺服器以查看您的變更。
