"""更改預設命令解析器

cmdparser 負責解析插入的原始文本
用戶，識別哪些命令匹配並返回一個或多個
匹配命令對象。它由 Evennia 的 cmdhandler 調用並且
必須以同一表單接受輸入並傳回結果。預設
處理程序非常通用，因此您通常不需要重載它
除非你有非常奇特的解析需求；高階解析是最好的
在 Command.parse 層級完成。

預設的 cmdparser 理解以下命令組合
（其中 [] 標記可選部分。）

[cmdname[ cmdname2 cmdname3 ...] [其餘]

命令可以由任意數量的空格分隔的單字組成
長度，並包含任何字元。它也可能是空的。

解析器利用 cmdset 來找出候選指令。的
解析器傳回匹配列表。每場比賽都是一個元組及其第一個
三個元素是解析的 cmdname（小寫），其餘的
參數以及 cmdset 中匹配的 cmdobject。


預設情況下不存取該模組。告訴 Evennia 使用它
將以下行新增至而不是預設的命令解析器
您的設定檔：

    COMMAND_PARSER = "server.conf.cmdparser.cmdparser"
"""


def cmdparser(raw_string, cmdset, caller, match_index=None):
    """一旦 cmdhandler 完成此操作，就會呼叫此函數
    收集並合併對此特定解析有效的所有有效命令集。

    raw_string - 呼叫者輸入的未解析文字。
    cmdset - 合併後的目前有效的 cmdset
    caller - 觸發此解析的呼叫者
    match_index - 一個可選的整數索引，用於在 a 中選擇給定的匹配項
                  同名指令匹配的列表。

    返回：
     元組列表：[(cmdname, args, cmdobj, cmdlen, mratio), ...]
            其中 cmdname 是符合的指令名稱，args 是
            cmdname 中未包含的所有內容。 Cmdobj 是實際的
            從cmdset中取得的命令實例，cmdlen是長度
            指令名稱和 mratio 的質量值
            （可能）分開多個比賽。"""
    # 您的實施在這裡
