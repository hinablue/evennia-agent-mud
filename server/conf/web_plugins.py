"""Web 插件掛鉤。"""


def at_webserver_root_creation(web_root):
    """當 Web 伺服器完成建置其預設值時呼叫此方法
    路徑樹。此時，media/ 和 static/ URI 已經
    已新增至網路根目錄。

    參數：
        web_root (twisted.web.resource.Resource)：根
            URI 樹的資源。使用 .putChild() 來
            將新的子網域新增到樹中。

    返回：
        web_root (twisted.web.resource.Resource)：潛在的
            修改根結構。

    範例：
        從twisted.web 導入靜態
        my_page = static.File("web/mypage/")
        my_page.indexNames = ["index.html"]
        web_root.putChild("我的頁面", my_page)"""
    return web_root


def at_webproxy_root_creation(web_root):
    """此功能可以修改Portal代理服務。
    參數：
        web_root (evennia.server.webserver.Website)：Evennia
            網站申請。使用 .putChild() 新增新的
            可透過 TCP 進行入口網站存取的子網域；
            主要用於新協議開發，但適合
            對於其他惡作劇。"""
    return web_root
