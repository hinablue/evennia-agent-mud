"""與 FuncParser 一起應用於傳出訊息的傳出可呼叫物件。

此模組中的函數將作為 $funcname(args, kwargs) 可用
在所有傳出字串中，如果添加

    FUNCPARSER_PARSE_OUTGOING_MESSAGES_ENABLED = True

到您的設定檔。預設的內聯函數位於
`evennia.utils.funcparser`。

在文字中，用法很簡單：

__面具_2__

範例 1（使用“pad”inlinefunc）：
    說這是寬度為 50 的 $pad("a center-padded text", 50,c,-)。
    ->
    John 說：“這是 -------------- 中心填充的文字 -------------- 寬度為 50。”

範例 2（使用巢狀的“pad”和“time”內聯函數）：
    說現在時間是 $pad($time(), 30)。
    ->
    約翰說：“現在時間是 10 月 25 日 11:09。”

若要新增更多內聯函數，請將它們新增至此模組中，使用
以下調用簽名：

    def funcname(*args, **kwargs)
        ……"""

# def 大寫(*args, **kwargs):
# 「愚蠢的大寫範例。用作 $capitalize
# 如果沒有參數：
# 返回 '​​'
# 會話 = kwargs.get("會話")
# 返回args[0].capitalize()
