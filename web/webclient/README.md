# 網路客戶端視圖

webclient主要是直接在瀏覽器中透過Javascript控制，所以
您通常透過 `mygame/web/static/webclient/js/` - 文件來自訂它。

從這裡你可以改變的很少，除非你想實施
從頭開始您自己的客戶。

## 關於視圖

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
