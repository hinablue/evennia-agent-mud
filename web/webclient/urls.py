"""這會從 URL 重新路由到 python 視圖函數/類別。

主 web/urls.py 包含所有以 `webclient/` 開頭的 URL 的路由
（此處不應再次包含 `webclient/` 部分）。"""

from django.urls import path

from evennia.web.webclient.urls import urlpatterns as evennia_webclient_urlpatterns

# 在這裡添加圖案
urlpatterns = [
    # 路徑（“url-pattern”，imported_python_view），
    # 路徑（“url-pattern”，imported_python_view），
]

# 由 Django 讀取
urlpatterns = urlpatterns + evennia_webclient_urlpatterns
