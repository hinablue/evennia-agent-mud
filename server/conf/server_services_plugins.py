"""伺服器插件服務

此插件模組可以為伺服器定義使用者創建的服務
開始。

此模組必須處理啟動所需的所有導入和設置
扭曲的服務（請參閱 Evennia.server.server 中的範例）。還必須
包含一個函數start_plugin_services(application)。埃文尼亞將
使用主伺服器應用程式呼叫此函數（因此您的服務
可以添加到其中）。該函數不應傳回任何內容。外掛
服務在伺服器啟動過程中最後啟動。"""


def start_plugin_services(server):
    """此鉤子由 Evennia 在伺服器啟動過程的最後呼叫。

    server - 對主伺服器應用程式的引用。"""
    pass
