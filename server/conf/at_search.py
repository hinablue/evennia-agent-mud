"""搜尋和多重配對處理

此模組允許重載 Evennia 使用的兩個函數
搜尋功能：

    at_搜尋_結果：
        每當從物件傳回結果時都會呼叫此函數
        搜尋（命令中的常見操作）。  應該（一起
        與下面的 at_multimatch_input）定義某種方式來呈現和
        區分多個匹配（預設情況下，這些是
        呈現為 1 球、2 球等）
    at_multimatch_input：
        這是用搜尋詞調用的，應該能夠
        確定使用者是否想要分離多重配對結果
        （例如先前搜尋的結果）。預設情況下，這
        函數將 1-ball、2-ball 等形式的輸入理解為
        表明「ball」的第一個或第二個匹配應該是
        使用過。

預設不呼叫該模組，要使用它，請新增以下內容
行到您的設定檔：

    SEARCH_AT_RESULT = "server.conf.at_search.at_search_result"
"""


def at_search_result(matches, caller, query="", quiet=False, **kwargs):
    """這是一個用於處理所有搜尋處理的通用掛鉤
    結果，包括錯誤報告。

    參數：
        matches (list): 這是一個包含 0、1 或多個類型類別實例的列表，
            搜尋的匹配結果。如果為 0，則應出現不符錯誤
            被回顯，如果 >1，則應給出多重匹配錯誤。僅
            如果單一匹配結果應該通過。
        呼叫者（對象）：執行搜尋和/或應該執行搜尋的對象
        接收錯誤訊息。
    query（str，可選）：用於產生 `matches` 的搜尋查詢。
        Quiet (bool, 可選)：如果 `True`，則不會向呼叫者回顯任何訊息
            關於錯誤。

    關鍵字參數：
        nofound_string (str)：用於回顯未找到錯誤的替換字串。
        multimatch_string (str)：用於回顯多重符合錯誤的替換字串。

    返回：
        processed_result（物件或無）：這始終是單一結果
            或 `None`。如果 `None`，任何錯誤報告/處理都應該
            已經發生了。"""
