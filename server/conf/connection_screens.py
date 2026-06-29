# -*- coding: utf-8 -*-
"""登入前顯示的連線畫面。"""

from django.conf import settings

from evennia import utils

CONNECTION_SCREEN = """
|b==============================================================|n
 歡迎來到 |g{}|n，版本 {}！

 若你已有帳號，請輸入：
      |wconnect <帳號> <密碼>|n
 若你需要建立新帳號，請輸入（不含 <>）：
      |wcreate <帳號> <密碼>|n

 若帳號名稱包含空白，請使用引號包起來。
 輸入 |whelp|n 可查看說明；輸入 |wlook|n 可再次顯示此畫面。
|b==============================================================|n""".format(
    settings.SERVERNAME, utils.get_evennia_version("short")
)
