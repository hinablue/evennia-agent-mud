# -*- 編碼：utf-8 -*-
"""登入前顯示的連線畫面。"""

from django.conf import settings

from evennia import utils

CONNECTION_SCREEN = """
|b==============================================================|n
 歡迎來到 |g{}|n，版本 {}！

 若帳號名稱包含空白，請使用引號包起來。
|b==============================================================|n""".format(
    settings.SERVERNAME, utils.get_evennia_version("short")
)
