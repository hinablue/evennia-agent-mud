# 網站瀏覽量和其他程式碼

「視圖」是 python 程式碼（函數或可呼叫類別），負責
產生一個 HTML 頁面供使用者查看，以回應訪問給定的 URL
在他們的瀏覽器中。在 Evennia 行話中，它的功能與命令類似，其中
輸入/參數是 URL/請求，輸出是新網頁。

urls.py 檔案包含針對提供的運行的正規表示式
URL - 當找到匹配項時，執行將傳遞到視圖，然後
負責（通常）透過填寫_模板_ - a 來產生網頁
HTML 文件中可以包含特殊標籤，這些標籤可以被動態替換
內容。然後它返回完成的 HTML 頁面供用戶查看。

請參閱[關於視圖的 Django 文件](https://docs.djangoproject.com/en/4.1/topics/http/views/)
更多資訊。

## 覆蓋視圖

1. 將要變更的原始程式碼從 `evennia/web/website/views/` 複製到
`mygame/web/website/views/` 並根據需要進行編輯。
2. 查看 `evennia/web/website/urls.py` 並找到指向該視圖的正規表示式。新增這個正規表示式
到您自己的 `mygam/website/urls.pye` 但將其更改為導入並指向您的
改為更改版本。
3. 重新載入伺服器，頁面現在使用您的視圖版本。
