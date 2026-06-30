"""這是使用者在 Web 瀏覽器中輸入 URL 時的起點。

url 匹配（透過正規表示式）並映射到「視圖」—Python 函數或
可調用類別（通常）使用“模板”（一個 html 文件
帶有可以被動態內容替換的插槽）以呈現 HTML
向使用者顯示的頁面。

該文件包含網站、Web 用戶端和管理中的 URL。來凌駕於你之上
應該修改這些子目錄中的 urls.py 。

在 Django 文件中搜尋「URL 排程器」以獲得更多協助。"""

from django.urls import include, path

# 預設 Evennia 模式
from evennia.web.urls import urlpatterns as evennia_default_urlpatterns

# 添加圖案
urlpatterns = [
    # 網站
    path("", include("web.website.urls")),
    # 網路客戶端
    path("webclient/", include("web.webclient.urls")),
    # 網路管理員
    path("admin/", include("web.admin.urls")),
    # 在這裡添加任何額外的網址：
    # 路徑（“mypath/”，包括（“path.to.my.urls.file”）），
]

# 'urlpatterns' 必須這樣命名才能讓 Django 找到它。
urlpatterns = urlpatterns + evennia_default_urlpatterns
