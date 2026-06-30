"""輸入功能

輸入函數總是從客戶端呼叫（它們處理伺服器
輸入，因此得名）。

該模組透過包含在
`settings.INPUT_FUNC_MODULES` 元組。

考慮此模組中包含的所有*全域函數*
輸入處理函數，可以由客戶端呼叫處理
輸入。

輸入函數必須具有以下呼叫簽名：

    cmdname（會話，*args，**kwargs）

其中 session 將是活動會話，*args、**kwargs 是額外的
傳入參數和關鍵字屬性。

一個特殊的命令是「預設」命令，它將被稱為
當沒有其他 cmdname 匹配時。它也接收未找到的 cmdname
作為論證。

    預設（會話、cmdname、*args、**kwargs）"""

# def oob_echo(會話, *args, **kwargs):
#     """
# 範例迴聲函數。回顯發送給它的 args、kwargs。
#
# 參數：
# 會話（Session）：接收回顯的Session。
# args（str列表）：回顯文字。
# kwargs（str 的字典，可選）：鍵控回顯文本
#
#     """
#     session.msg(oob=("echo", args, kwargs))
#
#
# def 預設值（會話、cmdname、*args、**kwargs）：
#     """
# 處理沒有符合的 inputhandler 函數的命令。
#
# 參數：
# 會話（Session）：活動會話。
# cmdname (str)：（不符的）指令名稱
# args、kwargs（任意）：函數的參數。
#
#     """
# 經過
