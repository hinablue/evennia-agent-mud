"""啟動插件服務

此插件模組可以為 Portal 定義使用者創建的服務
開始。

此模組必須處理啟動所需的所有導入和設置
扭曲的服務（請參閱 Evennia.server.portal.portal 中的範例）。它
也必須包含函數 start_plugin_services(application)。
Evennia 將透過主 Portal 應用程式呼叫此函數（因此
您的服務可以添加到其中）。該函數不應該返回
任何東西。插件服務在Portal啟動時最後啟動
過程。"""


def start_plugin_services(portal):
    """此掛鉤由 Evennia 在 Portal 啟動過程的最後呼叫。

    門戶 - 對主門戶應用程式的引用。"""
    pass
