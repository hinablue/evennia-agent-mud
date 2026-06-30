"""頻道

頻道類代表可以使用的不正常的聊天室
遊戲中的帳號。它大多是為了改變它的外觀而重載，但是
通道可用於實現多種不同形式的訊息
分配系統。

請注意，向通道發送資料是透過 CMD_CHANNEL 處理的
syscommand（請參閱evennia.syscmds）。發送通常不需要
待修改。"""

from evennia.comms.comms import DefaultChannel


class Channel(DefaultChannel):
    r"""這是所有通道通訊的基底類別。從此繼承到
    創建不同類型的溝通管道。

    類別級變數：
    - `send_to_online_only` (bool, 預設 True) - 如果設置，只會嘗試
      發送給實際活躍的訂閱者。這是一個有用的優化。
    - `log_file`（str，預設`"channel_{channelname}.log"`）。這是
      將保存通道歷史記錄的日誌檔案。 `{channelname}` 標籤
      將被 Channel 的 key 取代。如果屬性“log_file”
      設定後，將使用它。如果這是 None 且沒有找到屬性，
      不會保存任何歷史記錄。
    - `channel_prefix_string` (str, 預設 `"[{channelname} ]"`) - 使用此
      作為一個簡單的模板來取得帶有 `.channel_prefix()` 的通道前綴。它被用來
      在每個頻道訊息前面；使用 `{channelmessage}` 標記插入
      目前頻道的名稱。如果您不需要前綴（或想要
      相反，在訊息生成期間在掛鉤中處理它。
    - `channel_msg_nick_pattern`(str, 預設 `"{alias}\\s*?|{alias}\\s+?(?P<arg1>.+?)") -
      this is what used when a channel subscriber gets a channel nick assigned to this
      channel. The nickhandler uses the pattern to pick out this channel's name from user
      input. The `{alias}` token will get both the channel's key and any set/custom aliases
      per subscriber. You need to allow for an `<arg1>` regex group to catch any message
      that should be send to the  channel. You usually don't need to change this pattern
      unless you are changing channel command-style entirely.
    - `channel_msg_nick_replacement` (str, default `"頻道 {channelname} = $1"` - this
      is used by the nickhandler to generate a replacement string once the nickhandler (using
      the `channel_msg_nick_pattern`) identifies that the channel should be addressed
      to send a message to it. The `<arg1>` regex pattern match from `channel_msg_nick_pattern`
      will end up at the `$1` position in the replacement. Together, this allows you do e.g.
      'public Hello' and have that become a mapping to `channel public = Hello__MASK_23channel__MASK_24y_22__channel public = Hello__MASK_23_channel__MASK_24y___K__75_7___K__25_`chan__%。

    * 屬性：
        靜音列表
        禁止名單
        整體列表

    * 工作方法：
        取得日誌檔名()
        設定日誌檔案名稱（檔案名稱）
        has_connection(account) - 檢查給定帳戶是否監聽此頻道
        connect(account) - 將帳戶連接到此頻道
        disconnect(account) - 中斷帳號與頻道的連接
        access(access_obj, access_type='listen', default=False) - 檢查
                    訪問該頻道（預設 access_type 為listen）
        創建（鍵，創建者=無，*args，**kwargs）
        delete() - 刪除該頻道
        message_transform(msg, 發出=False, 字首=True,
                          sender_strings=None, external=False) - 呼叫者
                          通信系統並觸發下面的鉤子
        msg(msgobj, header=None, senders=None, sender_strings=None,
            持久=無，在線=假，發出=假，外部=假） - 主要
                send 方法，建立一條新訊息並將其傳送到通道。
        tempmsg(msg, header=None, senders=None) - 用於發送非持久性的包裝器
                消息。
        distribution_message(msg, online=False) - 向所有人發送訊息
                頻道上已連線的帳戶，可選擇僅發送
                發送至目前線上的帳戶（針對非常大的發送進行了最佳化）
        靜音（訂閱者，**kwargs）
        取消靜音（訂閱者，**kwargs）
        禁令（目標，**kwargs）
        解禁（目標，**kwargs）
        add_user_channel_alias（用戶，別名，**kwargs）
        刪除_用戶_頻道_別名（用戶，別名，**kwargs）


    有用的鉤子：
        at_channel_creation() - 建立通道時呼叫一次
        基本型別_設定()
        at_init()
        at_first_save()
        channel_prefix() - 通道應該是什麼樣子
                  返回給使用者時添加前綴。回傳一個字串
        format_senders(senders) - 應該回傳如何顯示多個
                頻道的發送者
        pose_transform(msg, sender_string) - 應該偵測是否
                發送者正在擺姿勢，如果是，則修改字串
        format_external(msg,senders,emit=False) - 格式化傳送的訊息
                從遊戲外部，例如 IRC
        format_message（msg，emit = False） - 之前格式化訊息正文
                將其顯示給使用者。 「發出」通常意味著
                訊息不應與寄件者姓名一起顯示。
        頻道前綴()

        pre_join_channel(joiner) - 如果傳回 False，則中止加入
        post_join_channel(joiner) - 成功加入後立即調用
        pre_leave_channel(leaver) - 如果回傳 False，則中止離開
        post_leave_channel(leaver) - 成功離開後立即調用
        at_pre_msg（訊息，**kwargs）
        at_post_msg（訊息，**kwargs）
        web_get_admin_url()
        web_get_create_url()
        web_get_detail_url()
        web_get_update_url()
        web_get_delete_url()"""

    pass
