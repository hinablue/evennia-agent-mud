"""這會從 URL 重新路由到 python 視圖函數/類別。

主 web/urls.py 包含所有 url 的這些路由（url 的根）
這樣它就可以重新路由到所有網站頁面。"""

from django.urls import path

from evennia.web.website.urls import urlpatterns as evennia_website_urlpatterns

# 在這裡添加圖案
urlpatterns = [
    # 路徑（“url-pattern”，imported_python_view），
    # 路徑（“url-pattern”，imported_python_view），
]

# 由 Django 讀取
urlpatterns = urlpatterns + evennia_website_urlpatterns
