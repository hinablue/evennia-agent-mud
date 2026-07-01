"""Agent 迷航的世界建立、檢查與管理工具。"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from evennia import create_object, search_object
from evennia.objects.models import ObjectDB

from typeclasses.exits import Exit
from typeclasses.npcs import NPC
from typeclasses.objects import Object
from typeclasses.rooms import Room

LIMBO_ROOM_KEY = "莫比爾站"
LEGACY_LIMBO_KEYS = ("Limbo", "莫比爾站")

ROSIE_KEY = "rosie"
ROSIE_ALIASES = ["蘿西", "接待員"]
ROSIE_HOME = "迎賓大廳"
ROSIE_DESC = (
    "她安靜站在光線較柔的地方，像早就習慣在陌生人靠近前先觀察對方。"
    " 目光很穩，語氣大概也不會太吵。"
)
NPC_DEFS = {
    ROSIE_KEY: {
        "typeclass": NPC,
        "room": ROSIE_HOME,
        "aliases": ROSIE_ALIASES,
        "desc": ROSIE_DESC,
        "attributes": {
            "is_npc": True,
            "npc_kind": "npc",
            "npc_attackable": False,
            "npc_retaliates": False,
            "npc_can_die": False,
            "npc_aggro_chance": 0.0,
        },
    },
}
PLAYER_DESC = "這是剛登入此地的旅人，身上還帶著一點從現實殘留下來的節奏。"
SCENERY_LOCKS = (
    "get:false();drop:false();call:true();control:perm(Developer) or perm(Admin)"
)
DEFAULT_ROOM_DESC = "這裡暫時還沒有描述。"
DEFAULT_SCENERY_DESC = "這件場景物還沒有補上描述。"

ROOM_DEFS = {
    LIMBO_ROOM_KEY: {
        "desc": (
            "這裡像是一座被世界遺忘的月台。白光沒有來源，遠方卻隱約傳來列車掠過的低鳴。"
            " 你明知道自己還沒真正抵達任何地方，卻也已經離開了原本的位置。"
            " 牆面標示冷冷亮著，指向前方唯一確定的出口：|wlobby|n。"
        ),
        "details": [
            (
                ("月台", "站台"),
                "月台邊緣沒有鐵軌，只有一道向下吞沒視線的白色深淵，像被故意抹去了真正的終點。",
            ),
            (
                ("白光", "燈光", "光"),
                "光線沒有燈具，也沒有明確方向，只是均勻覆在空間裡，讓影子失去存在的理由。",
            ),
            (
                ("標示", "指示牌", "路標"),
                "唯一清楚可辨的標示只寫著 |wlobby|n，像有人早就替你決定好下一步。",
            ),
        ],
        "objects": [
            {
                "key": "金屬長椅",
                "aliases": ["長椅", "椅子"],
                "desc": "冰冷長椅固定在地面上，表面沒有使用痕跡，像從來沒有人真正等到過列車。",
            },
            {
                "key": "時刻顯示板",
                "aliases": ["顯示板", "時刻表"],
                "desc": "黑色顯示板偶爾閃出雜訊般的白字，卻始終沒有任何一班列車的實際到站時間。",
            },
            {
                "key": "封閉閘門",
                "aliases": ["閘門", "門"],
                "desc": "閘門緊閉，邊框透著微弱藍光，像在提醒你這裡不是給人折返的地方。",
            },
        ],
    },
    "迎賓大廳": {
        "desc": (
            "柔白燈帶沿著牆面向前延伸，將整個空間照得很安靜。"
            " 地板像被反覆拋光過，映著人影與訊號流。"
            " 這裡是整個站點最適合重新整理思緒的地方。"
        ),
        "details": [
            (
                ("燈帶", "燈光"),
                "燈帶埋在牆縫裡，光色柔和得近乎克制，像一種不帶情緒的接待。",
            ),
            (
                ("地板", "地面"),
                "深色地板光潔得能映出輪廓，但又不至於亮到讓人失去安全感。",
            ),
            (
                ("空氣", "氣味"),
                "空氣裡有很淡的金屬與紙張氣味，像長時間運作的設施與被反覆翻閱的文件。",
            ),
        ],
        "objects": [
            {
                "key": "公告白板",
                "aliases": ["白板", "公告"],
                "desc": "白板上用整齊的字跡寫著：『先學會觀察，再決定要修改世界的哪一塊。』",
            },
            {
                "key": "接待櫃台",
                "aliases": ["櫃台", "桌台"],
                "desc": "接待櫃台空得過分，只留下一支筆、一疊空白表單，和某種尚未被填寫的秩序感。",
            },
            {
                "key": "導覽終端",
                "aliases": ["終端", "導覽機"],
                "desc": "螢幕維持待機亮度，介面只列出幾個可前往的區域，像很有禮貌地等你自己做決定。",
            },
        ],
    },
    "訓練廳": {
        "desc": (
            "地面畫著成組的引導線與站位框，像是專門給新來者熟悉移動、觀察與互動的區域。"
            " 空間裡沒有喧鬧，只有規律、克制、與等待。"
        ),
        "details": [
            (
                ("引導線", "線條"),
                "不同顏色的引導線從牆邊延伸到場中央，像一套被拆開來講解的行動邏輯。",
            ),
            (
                ("站位框", "框線", "站位"),
                "地上的框線刻意留出距離，彷彿每一步都該先經過思考再落下。",
            ),
            (
                ("牆面", "牆"),
                "牆面覆著吸音材，讓任何聲響都被很快吞沒，只剩自己的呼吸比較清楚。",
            ),
        ],
        "objects": [
            {
                "key": "木製練習偶",
                "aliases": ["練習偶", "木偶"],
                "desc": "練習偶表面留著反覆修補的痕跡，看起來已經承受過無數次測試。",
            },
            {
                "key": "計時面板",
                "aliases": ["面板", "計時器"],
                "desc": "計時面板靜靜顯示著待命狀態，像只要你一開口，它就會開始計算每一次遲疑。",
            },
            {
                "key": "器材箱",
                "aliases": ["箱子", "收納箱"],
                "desc": "厚重器材箱堆在角落，裡面放著訓練護具、標記片與幾個磨損過頭的測試模組。",
            },
        ],
    },
    "裝備間": {
        "desc": (
            "狹長房間兩側是整齊的收納架與工具掛板。"
            " 每樣東西都被標記、歸位、編號，像在提醒每一次出手都該有理由。"
        ),
        "details": [
            (
                ("收納架", "架子"),
                "層架上的標籤排列得近乎偏執，每一格都像替某種應變場景預留了位置。",
            ),
            (
                ("掛板", "工具掛板"),
                "掛板上的工具以輪廓線固定，少了哪一件都會一眼被看出來。",
            ),
            (
                ("標籤", "編號"),
                "標籤字體一致，編號規則也簡潔冷靜，看得出這裡很討厭混亂。",
            ),
        ],
        "objects": [
            {
                "key": "工具櫃",
                "aliases": ["櫃子", "工具櫃"],
                "desc": "金屬工具櫃貼著舊標籤，裡面放著維修器材、測試模組與幾套尚未啟用的部件。",
            },
            {
                "key": "防護背心",
                "aliases": ["背心", "防具"],
                "desc": "幾件防護背心掛在側邊，布料看起來厚實但靈活，像是專門留給會衝進麻煩裡的人。",
            },
            {
                "key": "檢修推車",
                "aliases": ["推車", "手推車"],
                "desc": "三層檢修推車上放著扳手、測筆與線材捲，看起來隨時可以被推往任何一處故障現場。",
            },
        ],
    },
    "觀測室": {
        "desc": (
            "弧形觀景窗外是一片模糊而流動的光幕，像資料海，也像遠方城市的夜景。"
            " 站在這裡的人很容易不小心把沉默看得太深。"
        ),
        "details": [
            (
                ("光幕", "景色", "外面"),
                "外頭那片流動的光像是訊號、雨痕與城市輪廓疊在一起，怎麼看都不像單一世界。",
            ),
            (
                ("玻璃", "窗面", "窗"),
                "玻璃乾淨得近乎不存在，只有靠近時才會從涼意裡重新意識到它的邊界。",
            ),
            (
                ("倒影", "影子"),
                "窗上的倒影比你想像中更淡，像這個地方不太願意替任何人留下完整輪廓。",
            ),
        ],
        "objects": [
            {
                "key": "弧形觀景窗",
                "aliases": ["觀景窗", "窗戶"],
                "desc": "玻璃表面微微發冷，映出你的輪廓，也映出外頭那片似真似假的光。",
            },
            {
                "key": "測距鏡",
                "aliases": ["鏡子", "觀測鏡"],
                "desc": "測距鏡固定在支架上，鏡筒朝向遠處最亮的一片區域，像試圖替混沌找出可量測的距離。",
            },
            {
                "key": "記錄桌",
                "aliases": ["桌子", "書寫桌"],
                "desc": "記錄桌上散著幾張觀測筆記與一支沒蓋好的筆，像剛有人把一個念頭寫到一半就停住了。",
            },
        ],
    },
    "控制中樞": {
        "desc": (
            "這裡比其他房間更安靜。數列、狀態燈與終端畫面在黑色桌面上無聲閃爍，"
            " 像整個世界把心跳藏到了這裡。"
        ),
        "details": [
            (
                ("狀態燈", "燈號"),
                "紅、綠、藍色燈號規律亮滅，像有人用極度節制的方式替系統表達情緒。",
            ),
            (
                ("數列", "數字", "畫面"),
                "終端上的數列飛快更新，對不熟悉的人來說像雜訊，對熟悉的人則像脈搏。",
            ),
            (
                ("桌面", "黑桌", "控制台"),
                "黑色桌面沒有多餘裝飾，只留最必要的操作區與一種不容分心的壓力。",
            ),
        ],
        "objects": [
            {
                "key": "終端機陣列",
                "aliases": ["終端機", "陣列"],
                "desc": "數台終端機並排亮著，畫面上流過監測資訊、事件記錄與尚未處理的工作。",
            },
            {
                "key": "主控座椅",
                "aliases": ["座椅", "椅子"],
                "desc": "主控座椅略微向後傾，扶手磨損得剛好，像長時間坐在這裡的人幾乎沒有真正放鬆過。",
            },
            {
                "key": "備援電池艙",
                "aliases": ["電池艙", "備援艙"],
                "desc": "厚重電池艙嵌在牆面下方，低低嗡鳴著，像把整個空間最後一口氣安靜地存起來。",
            },
        ],
    },
    "圓桌之光的聖域": {
        "desc": (
            "莊嚴的白色騎士大廳向高處拱起，冷白石柱與深藍旗幟沿著兩側排開，"
            " 正中央像仍殘留著聖劍出鞘後的光。整個空間乾淨、筆直，近乎不容妥協。"
        ),
        "details": [
            (
                ("旗幟", "軍旗", "藍旗"),
                "旗幟垂得很安靜，布面沒有一絲多餘皺褶，像在要求踏進來的人先端正自己的站姿。",
            ),
            (
                ("聖光", "光", "反光"),
                "冷白光滑過牆邊的劍架與石面，讓每一道反光都像短暫出鞘的誓言。",
            ),
            (
                ("圓桌", "石桌", "王座區"),
                "大廳深處的圓桌與王座區沒有任何浮華裝飾，只有一種克制到近乎嚴苛的王者秩序。",
            ),
        ],
        "objects": [
            {
                "key": "誓約劍架",
                "aliases": ["劍架", "武器架"],
                "desc": "深色木架上陳列著數把樣式古典的長劍，劍柄包皮被保養得很好，像任何一次出鞘都不容輕率。",
            },
            {
                "key": "白銀胸甲",
                "aliases": ["胸甲", "盔甲"],
                "desc": "拋光過的胸甲立在支架上，弧面映著房內冷靜的光，看起來比裝飾更像一種必須承受的責任。",
            },
            {
                "key": "王選講台",
                "aliases": ["講台", "石台"],
                "desc": "低矮石台刻著細密紋路，像是給人在出戰前短暫停下，對自己重申原則的地方。",
            },
        ],
    },
    "無盡劍之丘": {
        "desc": (
            "黃昏像永遠停在這裡。乾裂原野一路鋪到視線盡頭，無數劍身斜插在焦土中，"
            " 上方則是巨大齒輪緩慢轉動的天空，像一座被理想燒到最後只剩武器的世界。"
        ),
        "details": [
            (
                ("齒輪", "天空", "天幕"),
                "巨大的齒輪在赤銅色天空中緩慢咬合，發出低沉卻近乎無情的運轉聲。",
            ),
            (
                ("劍丘", "劍", "原野"),
                "每一把插在地上的劍都像某段被複製、理解、再放棄的歷史殘片。",
            ),
            (
                ("黃昏", "暮色", "風"),
                "黃昏沒有真正墜落，只是讓荒風一再把鐵鏽與灰燼的味道吹回來。",
            ),
        ],
        "objects": [
            {
                "key": "投影兵裝列",
                "aliases": ["兵裝", "武器列"],
                "desc": "數把形制各異的刀劍被插成一排，邊緣帶著微妙的不真實感，像剛從記憶裡被強行鍛出。",
            },
            {
                "key": "齒輪殘架",
                "aliases": ["齒輪架", "殘架"],
                "desc": "半埋在地面的金屬齒輪架還在低速轉動，彷彿整個固有結界連崩壞都遵守自己的節拍。",
            },
            {
                "key": "鍛造檯影",
                "aliases": ["鍛造檯", "工作檯"],
                "desc": "像海市蜃樓般浮現的鍛造檯殘影，表面留著反覆敲擊與燒灼痕跡。",
            },
        ],
    },
    "凱爾特之槍的荒原": {
        "desc": (
            "風從蒼綠原野深處一路割過來，帶著草汁、泥土與尚未乾透的血腥氣。"
            " 這裡沒有多餘遮蔽，只有速度、直覺，以及出槍前那一下短得不能再短的停頓。"
        ),
        "details": [
            (
                ("長草", "草浪", "原野"),
                "長草被強風吹得伏低又立起，像整片荒原都在替某場決鬥屏住呼吸。",
            ),
            (
                ("風聲", "氣流", "空氣"),
                "風聲乾脆得近乎銳利，吹過耳側時像一支已經決定方向的槍。",
            ),
            (
                ("腳印", "步道", "地面"),
                "地面留著幾條急停與轉身時踩出的磨痕，從起步到突刺幾乎沒有任何浪費。",
            ),
        ],
        "objects": [
            {
                "key": "赤紋槍架",
                "aliases": ["槍架", "長槍架"],
                "desc": "槍架上固定著幾支長槍，槍柄包布吸汗卻不顯破舊，像每一次握持都帶著高度紀律。",
            },
            {
                "key": "起步樁",
                "aliases": ["木樁", "起步點"],
                "desc": "低矮起步樁被反覆踩磨得發亮，像提醒任何爆發都來自極短的一次決定。",
            },
            {
                "key": "護手綁帶盒",
                "aliases": ["綁帶盒", "盒子"],
                "desc": "盒裡收著整齊折好的護手綁帶，布料帶著些微藥草與汗氣，實用得近乎不近人情。",
            },
        ],
    },
    "靜謐的石化迷宮": {
        "desc": (
            "石造走廊在陰影中層層折返，潮濕牆面反著冷光，安靜得讓每一步聲音都像闖入禁忌。"
            " 某種被凝視過的恐懼仍殘留在空氣裡，像視線一旦交會就會永遠失去移動能力。"
        ),
        "details": [
            (
                ("石牆", "牆面", "迷宮"),
                "石牆表面覆著細小水氣與裂紋，摸上去冰冷得像早已不再屬於活人。",
            ),
            (
                ("眼紋", "紋樣", "壁刻"),
                "牆面隱約可見蛇髮與眼瞳交纏的紋樣，讓人不太想久看。",
            ),
            (
                ("回音", "腳步", "沈默"),
                "這裡的回音很短，像聲音才剛離開你，就被迷宮本身吞了下去。",
            ),
        ],
        "objects": [
            {
                "key": "蛇首馬具架",
                "aliases": ["馬具架", "馬具"],
                "desc": "暗色架子上掛著金屬扣件與韁繩，蛇首雕飾在陰影裡泛著冷硬光澤。",
            },
            {
                "key": "青銅踏鐙",
                "aliases": ["踏鐙", "鐙"],
                "desc": "成對踏鐙放在矮台上，邊角磨損圓滑，顯然曾陪過不少急促而漫長的旅程。",
            },
            {
                "key": "石化鏡片",
                "aliases": ["鏡片", "黑鏡"],
                "desc": "一片深色鏡片被封在展示匣裡，表面幽暗得像會把靠近的人影慢慢定住。",
            },
        ],
    },
    "神代魔術的禁忌工坊": {
        "desc": (
            "術式圈紋沿地板與牆面靜靜發亮，卷軸、藥瓶與金屬器皿把空間擠得近乎沒有留白。"
            " 這裡像一場永遠停在臨界點的推演，知識、背叛與奇蹟全被裝進同一盞冷光裡。"
        ),
        "details": [
            (
                ("術式", "法陣", "圈紋"),
                "圈紋彼此咬合成精密結構，線條細到近乎病態，像每一筆都為了限制失控而存在。",
            ),
            (
                ("書影", "書頁", "紙頁"),
                "層層書影在側牆堆疊，讓這裡比房間更像一個把知識濃縮過頭的肺葉。",
            ),
            (
                ("餘燼", "焦痕", "氣味"),
                "空氣裡那點輕微焦味不像失誤，反而像過度靠近真相後留下的正常代價。",
            ),
        ],
        "objects": [
            {
                "key": "浮光法陣盤",
                "aliases": ["法陣盤", "圓盤"],
                "desc": "金屬圓盤上刻滿分層術式，邊緣有微光流轉，像只要補上最後一個參數就會開始運轉。",
            },
            {
                "key": "束頁魔導書",
                "aliases": ["魔導書", "書"],
                "desc": "厚重書冊用皮帶束起，紙頁邊緣塞滿註記紙條，像內容早已超過普通記憶能承受的密度。",
            },
            {
                "key": "破戒匕首匣",
                "aliases": ["匕首匣", "黑匣"],
                "desc": "狹長匣盒內襯深紫絨布，中央凹槽明顯留給某把不該輕易示人的短刃。",
            },
        ],
    },
    "月下之橋的劍道場": {
        "desc": (
            "一座狹長木橋橫跨靜水，月光像薄霜般鋪在橋面上。這裡沒有牆、沒有多餘景物，"
            " 只留下最適合把一式劍招磨到極致的空白與寒意。"
        ),
        "details": [
            (
                ("木橋", "橋面", "橋"),
                "木橋筆直得近乎固執，寬度只夠容下最必要的進退與一次漂亮到不近人情的斬擊。",
            ),
            (
                ("月光", "月色", "銀光"),
                "月光薄而冷，落在橋面時像替每一道劍路都預先畫好了邊界。",
            ),
            (
                ("水面", "池水", "倒影"),
                "橋下水面平得像鏡子，偶爾才被夜風拉開一絲紋路，像連漣漪都怕驚擾這裡的專注。",
            ),
        ],
        "objects": [
            {
                "key": "燕返木人",
                "aliases": ["木人", "練習偶"],
                "desc": "木人身上留下三道幾乎同時落下的斬痕，間距漂亮得讓人不太想細想那是怎麼辦到的。",
            },
            {
                "key": "橋頭石燈",
                "aliases": ["石燈", "燈籠"],
                "desc": "石燈裡沒有火，卻被月光照得輪廓清冷，像只是為了見證決鬥而存在。",
            },
            {
                "key": "洗心手水盆",
                "aliases": ["手水盆", "水盆"],
                "desc": "淺石盆裡的水安靜得近乎凝止，像踏上橋前應該先把雜念洗掉。",
            },
        ],
    },
    "十二試煉的巨神之殿": {
        "desc": (
            "殘破神殿在高聳石柱間撐出沉重穹頂，牆面撞痕、斷鏈與碎盾堆成一種近乎野蠻的壓迫感。"
            " 這裡像不是為了訓練而存在，而是為了證明怪物般的不滅究竟要拿多少破壞來換。"
        ),
        "details": [
            (
                ("石柱", "神殿", "穹頂"),
                "巨柱表面刻著被歲月與暴力一起磨損的浮雕，看起來像連神話都曾在這裡喘不過氣。",
            ),
            (
                ("鎖鏈", "鐵鏈", "鏈條"),
                "粗重鎖鏈垂掛在牆邊，節面磨得發亮，像不是為了展示，而是真的曾被反覆扯緊到極限。",
            ),
            (
                ("撞痕", "裂痕", "牆面"),
                "牆面留著大大小小的撞痕與修補層，說明這裡的安靜從來不是理所當然。",
            ),
        ],
        "objects": [
            {
                "key": "鎮暴鍛柱",
                "aliases": ["鍛柱", "鐵柱"],
                "desc": "厚重鐵柱被固定在地面，表面有層層敲擊與抓刮痕，看得出它主要用途不是好看。",
            },
            {
                "key": "破盾堆",
                "aliases": ["破盾", "盾牌"],
                "desc": "幾面裂開的厚盾被隨手堆在角落，邊緣崩口猙獰得像每一次防守都撐得很勉強。",
            },
            {
                "key": "拘束皮帶架",
                "aliases": ["皮帶架", "拘束帶"],
                "desc": "金屬架上掛著多條加厚拘束帶，扣環磨得發亮，像有人很清楚失控之後必須付出的成本。",
            },
        ],
    },
    "黃金之王的至寶庫": {
        "desc": (
            "奢華得近乎蠻橫的黃金殿堂向四面延展，牆面、階梯與穹頂都在反射過盛的金光。"
            " 幾道懸浮門扉靜靜打開一道縫，像任何寶物都只是王隨手可以丟出的餘裕。"
        ),
        "details": [
            (
                ("門扉", "寶庫門", "金門"),
                "漂浮門扉像液態金屬被強行定型，門縫後的黑暗反而比黃金更讓人不安。",
            ),
            (
                ("王座", "階座", "高台"),
                "高台上的王座離地很高，明顯不是為了讓人親近，而是為了讓人抬頭。",
            ),
            (
                ("金光", "寶光", "反射"),
                "金光太盛，幾乎把所有東西都照成可被佔有的樣子，只有傲慢仍然保持原形。",
            ),
        ],
        "objects": [
            {
                "key": "王財門扉",
                "aliases": ["門扉", "寶庫門"],
                "desc": "數道金色門扉懸浮在空中，表面紋路繁複得像每一道都通往一段被據為己有的歷史。",
            },
            {
                "key": "琥珀酒杯",
                "aliases": ["酒杯", "金杯"],
                "desc": "細長酒杯盛著深琥珀色液體，杯腳與杯緣都誇張得像連飲酒都必須帶著王者惡趣味。",
            },
            {
                "key": "金階王座",
                "aliases": ["王座", "寶座"],
                "desc": "王座覆著金箔與深紅軟墊，看起來舒適，卻又明顯只歡迎一個人坐下。",
            },
        ],
    },
    "暗影之城的處刑場": {
        "desc": (
            "幽暗巷道與窄牆在此彼此交錯，像一座被陰影拼接起來的無聲城市。"
            " 每一寸空間都像替埋伏、逼近與最後那一下審判留下了剛好的距離。"
        ),
        "details": [
            (
                ("陰影", "暗處", "影子"),
                "陰影在房裡不是缺光，而像被主動馴化過的工具，總比你預期更先抵達角落。",
            ),
            (
                ("地毯", "地面", "腳步"),
                "深色地面吞掉了大部分腳步聲，連自己的存在都會變得可疑。",
            ),
            (
                ("薄幕", "帷幕", "布幕"),
                "側邊薄幕分隔出幾個半開空間，像任何視線一旦鬆懈，就會錯過真正重要的部分。",
            ),
        ],
        "objects": [
            {
                "key": "隱刃抽屜櫃",
                "aliases": ["抽屜櫃", "櫃子"],
                "desc": "矮櫃抽屜結構精巧，打開時幾乎沒有聲音，裡面整齊收著短刃、鋼線與鎖具工具。",
            },
            {
                "key": "無聲面具架",
                "aliases": ["面具架", "面具"],
                "desc": "架上掛著幾張沒有表情的面具，材質薄而輕，像只為了讓一個人更徹底地消失。",
            },
            {
                "key": "心臟沙盤桌",
                "aliases": ["沙盤桌", "桌子"],
                "desc": "桌面沙盤被做成城市剖面，中心卻嵌著一枚赤色心臟標記，像一場處刑永遠只瞄準最核心的位置。",
            },
        ],
    },
    "萬象之惡的深淵": {
        "desc": (
            "漆黑空間像液體一樣往下緩慢流動，地面與天空的界線都被仇恨與黏稠惡意溶解掉了。"
            " 這裡沒有真正的方向，只有痛苦、詛咒與被世界推進深處的感覺。"
        ),
        "details": [
            (
                ("黑泥", "深淵", "污濁"),
                "黑泥在地表緩慢脈動，像一顆把全世界惡意都收納進去後仍嫌不夠大的心臟。",
            ),
            (
                ("哀鳴", "低語", "聲音"),
                "四周像不斷傳來極低的低語與哀鳴，卻分不清那是別人，還是你自己的念頭被放大了。",
            ),
            (
                ("裂口", "裂隙", "邊界"),
                "空間邊界不時裂出黑色縫隙，裡面沒有光，只剩一種會把名字也磨掉的深度。",
            ),
        ],
        "objects": [
            {
                "key": "污濁祭坑",
                "aliases": ["祭坑", "黑坑"],
                "desc": "凹陷祭坑裡的黑泥正緩慢翻湧，像只要再多丟進去一點惡意，它就會張口吞下整個房間。",
            },
            {
                "key": "逆咒石碑",
                "aliases": ["石碑", "咒碑"],
                "desc": "石碑表面刻滿互相覆寫的詛咒句式，讀得越久，越分不清哪一句原本是寫給誰。",
            },
            {
                "key": "空名鎖鏈",
                "aliases": ["鎖鏈", "黑鏈"],
                "desc": "幾條無所依附的鎖鏈懸在半空，末端沒有扣環，卻像隨時會纏住某個不幸被選中的人。",
            },
        ],
    },
    "永恆的收藏室": {
        "desc": "這裡是一個充滿陽光的溫馨房間，空氣中飄著淡淡的舊書卷氣息。房間裡堆滿了看似雜亂但被精心整理的魔法書、乾燥的花草和奇怪的瓶瓶罐罐。窗邊有一張巨大的工作桌，上面鋪著一張永遠沒有摺疊起來的古老地圖。",
        "details": [(("陽光", "光"), "陽光照在塵埃上，營造出一種慵懶而漫長的永恆感。")],
        "objects": [
            {
                "key": "魔法書堆",
                "aliases": ["書籍", "書"],
                "desc": "數以千計的書籍，其中一本標題是《能讓衣服去污的魔法》或《能讓花朵再次盛開的魔法》。",
            },
            {
                "key": "舊木箱",
                "aliases": ["木箱", "箱子"],
                "desc": "裡面裝著旅途間收集的各種奇怪的小東西。",
            },
            {
                "key": "半睡的枕頭",
                "aliases": ["枕頭"],
                "desc": "一個巨大的、看起來極其舒適的枕頭。",
            },
        ],
    },
    "秩序的避風港": {
        "desc": "極其乾淨且井然有序。床鋪被摺疊得像軍隊一樣平整，衣櫥裡的衣服按顏色和季節分門別類。房間角落有一個小巧的梳妝台，擺放著簡單的保養品。整體色調溫暖，給人一種安定感。",
        "details": [
            (("地板", "地面"), "地板光潔得幾乎沒有一絲灰塵，反映出主人對秩序的堅持。")
        ],
        "objects": [
            {
                "key": "熨燙得平整的長袍",
                "aliases": ["長袍", "衣服"],
                "desc": "一件毫無摺痕的魔法師長袍。",
            },
            {
                "key": "藥草整理箱",
                "aliases": ["整理箱", "藥草"],
                "desc": "各種藥劑被標記得清清楚楚。",
            },
            {
                "key": "小巧的鏡子",
                "aliases": ["鏡子"],
                "desc": "鏡子邊緣貼著一張小小的備忘錄。",
            },
        ],
    },
    "勇氣的訓練場": {
        "desc": "房間內擺放著沉重的訓練器材，地板上有明顯的磨損痕跡。牆上掛著幾張關於戰鬥技巧的圖表。雖然整體試圖維持整潔，但某些角落仍有著少年時期的稚氣。",
        "details": [(("牆面", "圖表"), "牆上貼著幾張關於肌肉訓練與戰斧揮砍的示意圖。")],
        "objects": [
            {
                "key": "巨大的戰斧",
                "aliases": ["戰斧", "斧頭"],
                "desc": "被擦拭得發亮，斧刃閃爍著寒光。",
            },
            {
                "key": "揉皺的筆記本",
                "aliases": ["筆記本", "筆記"],
                "desc": "記錄著戰鬥心得，但邊緣有被汗水浸濕的痕跡。",
            },
            {
                "key": "厚實的毯子",
                "aliases": ["毯子"],
                "desc": "一件看起來很暖和的毯子，像是一個能讓他放下強撐的勇氣、安心休息的繭。",
            },
        ],
    },
    "遺留的光輝": {
        "desc": "這個房間被布置得像一座小型博物館。中央擺放著一座熠熠生輝的銅像，四周環繞著他生前留下的遺物。光線柔和而神聖，空氣中彷彿還殘留著某種溫暖的笑意。",
        "details": [(("光線", "氛圍"), "光線柔和而神聖，像是時光在此處溫柔地停駐。")],
        "objects": [
            {
                "key": "華麗的劍鞘",
                "aliases": ["劍鞘"],
                "desc": "雖然劍已不在，但劍鞘依然維持著勇者的尊嚴。",
            },
            {
                "key": "雕刻精美的鏡子",
                "aliases": ["鏡子"],
                "desc": "鏡子中映照出觀看者的身影，讓人想起他對「美」的執著。",
            },
            {
                "key": "一束永不凋零的花",
                "aliases": ["鮮花", "花束"],
                "desc": "由魔法維持的鮮花，象徵著他留給世界的溫暖影響力。",
            },
        ],
    },
    "至高之城的孤高": {
        "desc": "極其宏偉且空曠。房間沒有多餘的裝飾，只有大理石地板和極高挑的穹頂。中央是一把冰冷的至高王座，四周環繞著漂浮的禁書。這裡沒有生活氣息，只有純粹的魔法能量在流動。",
        "details": [
            (("穹頂", "天花板"), "極高挑的穹頂反射出深邃的星空，讓人感到自身的渺小。")
        ],
        "objects": [
            {
                "key": "漂浮的禁書",
                "aliases": ["禁書", "魔法書"],
                "desc": "書頁在沒有風的情況下緩緩翻動，內容是凡人無法理解的深奧魔法。",
            },
            {
                "key": "一座古老的沙漏",
                "aliases": ["沙漏"],
                "desc": "沙子流動得極其緩慢，象徵著她視時間如無物的傲慢。",
            },
            {
                "key": "一個單獨的茶杯",
                "aliases": ["茶杯"],
                "desc": "在宏大的空間中，只有這一個茶杯，透露出一種極致的孤高與寂寞。",
            },
        ],
    },
}

EXIT_DEFS = [
    ("lobby", "莫比爾站", "迎賓大廳", ["hall", "大廳"]),
    ("mobil", "迎賓大廳", "莫比爾站", ["return", "返回", "station"]),
    ("training", "迎賓大廳", "訓練廳", ["train", "訓練"]),
    ("lobby", "訓練廳", "迎賓大廳", ["back", "大廳"]),
    ("armory", "迎賓大廳", "裝備間", ["gear", "裝備"]),
    ("lobby", "裝備間", "迎賓大廳", ["back", "大廳"]),
    ("observatory", "迎賓大廳", "觀測室", ["observe", "觀測"]),
    ("lobby", "觀測室", "迎賓大廳", ["back", "大廳"]),
    ("core", "迎賓大廳", "控制中樞", ["control", "中樞"]),
    ("lobby", "控制中樞", "迎賓大廳", ["back", "大廳"]),
    ("saber", "訓練廳", "圓桌之光的聖域", ["圓桌", "聖域"]),
    ("training", "圓桌之光的聖域", "訓練廳", ["train", "訓練"]),
    ("lancer", "訓練廳", "凱爾特之槍的荒原", ["槍兵", "荒原"]),
    ("training", "凱爾特之槍的荒原", "訓練廳", ["train", "訓練"]),
    ("assassin", "訓練廳", "月下之橋的劍道場", ["佐佐木", "劍道場"]),
    ("training", "月下之橋的劍道場", "訓練廳", ["train", "訓練"]),
    ("archer", "控制中樞", "無盡劍之丘", ["弓兵", "劍丘"]),
    ("core", "無盡劍之丘", "控制中樞", ["control", "中樞"]),
    ("gilgamesh", "控制中樞", "黃金之王的至寶庫", ["金閃閃", "寶庫"]),
    ("core", "黃金之王的至寶庫", "控制中樞", ["control", "中樞"]),
    ("trueassassin", "控制中樞", "暗影之城的處刑場", ["哈桑", "處刑場"]),
    ("core", "暗影之城的處刑場", "控制中樞", ["control", "中樞"]),
    ("caster", "觀測室", "神代魔術的禁忌工坊", ["術士", "工坊"]),
    ("observatory", "神代魔術的禁忌工坊", "觀測室", ["observe", "觀測"]),
    ("avenger", "觀測室", "萬象之惡的深淵", ["黑泥", "深淵"]),
    ("observatory", "萬象之惡的深淵", "觀測室", ["observe", "觀測"]),
    ("rider", "裝備間", "靜謐的石化迷宮", ["騎兵", "迷宮"]),
    ("armory", "靜謐的石化迷宮", "裝備間", ["gear", "裝備"]),
    ("berserker", "裝備間", "十二試煉的巨神之殿", ["狂戰士", "巨神之殿"]),
    ("armory", "十二試煉的巨神之殿", "裝備間", ["gear", "裝備"]),
    ("frieren", "迎賓大廳", "永恆的收藏室", ["frieren", "芙莉蓮"]),
    ("lobby", "永恆的收藏室", "迎賓大廳", ["back", "大廳"]),
    ("fern", "迎賓大廳", "秩序的避風港", ["fern", "費倫"]),
    ("lobby", "秩序的避風港", "迎賓大廳", ["back", "大廳"]),
    ("stark", "迎賓大廳", "勇氣的訓練場", ["stark", "修塔爾克"]),
    ("lobby", "勇氣的訓練場", "迎賓大廳", ["back", "大廳"]),
    ("himmel", "迎賓大廳", "遺留的光輝", ["himmel", "欣梅爾"]),
    ("lobby", "遺留的光輝", "迎賓大廳", ["back", "大廳"]),
    ("serie", "迎賓大廳", "至高之城的孤高", ["serie", "賽莉耶"]),
    ("lobby", "至高之城的孤高", "迎賓大廳", ["back", "大廳"]),
    ("fern", "永恆的收藏室", "秩序的避風港", ["fern", "費倫"]),
    ("frieren", "秩序的避風港", "永恆的收藏室", ["frieren", "芙莉蓮"]),
    ("himmel", "永恆的收藏室", "遺留的光輝", ["himmel", "欣梅爾"]),
    ("frieren", "遺留的光輝", "永恆的收藏室", ["frieren", "芙莉蓮"]),
    ("serie", "永恆的收藏室", "至高之城的孤高", ["serie", "賽莉耶"]),
    ("frieren", "至高之城的孤高", "永恆的收藏室", ["frieren", "芙莉蓮"]),
    ("stark", "秩序的避風港", "勇氣的訓練場", ["stark", "修塔爾克"]),
    ("fern", "勇氣的訓練場", "秩序的避風港", ["fern", "費倫"]),
    ("fern", "至高之城的孤高", "秩序的避風港", ["fern", "費倫"]),
    ("serie", "秩序的避風港", "至高之城的孤高", ["serie", "賽莉耶"]),
]

ROOM_ORDER = list(ROOM_DEFS.keys())
COMPONENT_NAMES = ("rooms", "details", "objects", "exits", "npcs")
FORCE_REBUILD_STAGING_KEY = "__agentworld_rebuild_staging__"
FORCE_REBUILD_STAGING_DESC = "世界重建暫存區。"


@dataclass
class WorldSpecError(ValueError):
    message: str

    def __str__(self):
        return self.message


# ---------------------------------------------------------------------------
# 共享助手
# ---------------------------------------------------------------------------


def _clean_text(value):
    return (value or "").strip()


def _format_list(items):
    items = [str(item) for item in items if item]
    return "、".join(items) if items else "無"


def _normalize_aliases(aliases):
    seen = set()
    ordered = []
    for alias in aliases or []:
        alias = _clean_text(alias)
        if alias and alias not in seen:
            ordered.append(alias)
            seen.add(alias)
    return ordered


def _spec_room_names():
    return list(ROOM_DEFS.keys())


def is_spec_room(room_name):
    return room_name in ROOM_DEFS


def resolve_spec_room_name(room_name):
    room_name = _clean_text(room_name)
    if not room_name:
        raise WorldSpecError("請提供房間名稱。")
    if room_name in ROOM_DEFS:
        return room_name
    raise WorldSpecError(
        f"找不到規格房間：{room_name}。可用房間：{_format_list(_spec_room_names())}"
    )


def _resolve_scope(room_name=None):
    if room_name:
        return [resolve_spec_room_name(room_name)]
    return _spec_room_names()


def _component_selection(*components):
    chosen = []
    for component in components:
        if component and component not in chosen:
            chosen.append(component)
    if not chosen:
        return list(COMPONENT_NAMES)
    return chosen


def _find_by_key(key):
    matches = list(ObjectDB.objects.filter(db_key=key).order_by("id"))
    if not matches:
        matches = search_object(key, exact=True)
    return matches[0] if matches else None


def _find_all_by_key(key):
    matches = list(ObjectDB.objects.filter(db_key=key).order_by("id"))
    if matches:
        return matches
    return list(search_object(key, exact=True))


def _find_limbo_room():
    for key in LEGACY_LIMBO_KEYS:
        room = _find_by_key(key)
        if room:
            return room
    return None


def _worldbuild_home_room():
    limbo = _find_limbo_room()
    if limbo:
        return limbo
    for room_name in ROOM_ORDER:
        room = _find_by_key(room_name)
        if room:
            return room
    staging = _find_by_key(FORCE_REBUILD_STAGING_KEY)
    if staging:
        return staging
    raise WorldSpecError("找不到可作為 home 的房間；請先建立至少一個房間。")


def _find_room(room_name):
    if room_name == LIMBO_ROOM_KEY:
        return _find_limbo_room()
    return _find_by_key(room_name)


def _get_room_or_error(room_name):
    room = _find_room(room_name)
    if not room:
        raise WorldSpecError(f"房間不存在：{room_name}")
    return room


def _get_room_contents(room):
    return list(getattr(room, "contents", []) or [])


def _find_object_in_room(room, key):
    for obj in _get_room_contents(room):
        if getattr(obj, "destination", None) is None and obj.key == key:
            return obj
    return None


def _find_exit(location, key, destination=None):
    matches = []
    for obj in _get_room_contents(location):
        if getattr(obj, "destination", None) is None:
            continue
        if obj.key != key:
            continue
        if destination is not None and obj.destination != destination:
            continue
        matches.append(obj)

    if not matches:
        return None

    keeper = matches[0]
    for duplicate in matches[1:]:
        duplicate.delete()
    return keeper


def _find_room_name_for_obj(obj):
    location = getattr(obj, "location", None)
    return getattr(location, "key", "無") if location else "無"


def _current_aliases(obj):
    return list(obj.aliases.all()) if obj else []


def _detail_map(room):
    return dict(getattr(room, "details", {}) or {})


def _matches_desc(obj, desc):
    return _clean_text(getattr(obj.db, "desc", "")) == _clean_text(desc)


def _missing_aliases(obj, expected_aliases):
    current = set(_current_aliases(obj))
    return [
        alias for alias in _normalize_aliases(expected_aliases) if alias not in current
    ]


def _ensure_aliases(obj, aliases):
    current = set(obj.aliases.all())
    changed = False
    for alias in _normalize_aliases(aliases):
        if alias not in current:
            obj.aliases.add(alias)
            changed = True
    return changed


def _ensure_room(key, desc):
    room = _find_room(key)
    created = False
    updated = False
    if not room:
        room = create_object(
            Room,
            key=key,
            home=_worldbuild_home_room(),
            attributes=[("desc", desc)],
        )
        created = True
        # 標記為 GM 大陸資產
        room.tags.add("gm_continent", category="ownership")
    else:
        if room.key != key:
            room.key = key
            updated = True
        if not _matches_desc(room, desc):
            room.db.desc = desc
            updated = True
        if updated:
            room.save()
    return room, created, updated


def _ensure_room_details(room, details):
    desired = {}
    for aliases, desc in details:
        for alias in aliases:
            desired[_clean_text(alias)] = desc

    current = _detail_map(room)
    changed = current != desired
    if changed:
        room.details = {}
        for alias, desc in desired.items():
            room.add_detail(alias, desc)
    return changed


def _ensure_object(key, location, desc, aliases=None):
    obj = _find_object_in_room(location, key)
    created = False
    updated = False
    if not obj:
        obj = create_object(
            Object,
            key=key,
            location=location,
            home=location,
            aliases=_normalize_aliases(aliases),
            locks=SCENERY_LOCKS,
            attributes=[("desc", desc)],
        )
        created = True
        # 標記為 GM 大陸資產
        obj.tags.add("gm_continent", category="ownership")
    else:
        if obj.location != location:
            obj.location = location
            updated = True
        if obj.home != location:
            obj.home = location
            updated = True
        if not _matches_desc(obj, desc):
            obj.db.desc = desc
            updated = True
        if _ensure_aliases(obj, aliases):
            updated = True
        obj.locks.add(SCENERY_LOCKS)
        if updated:
            obj.save()
    return obj, created, updated


def _ensure_exit(key, location, destination, aliases=None):
    exi = _find_exit(location, key, destination=destination)
    created = False
    updated = False
    if exi:
        if _ensure_aliases(exi, aliases):
            updated = True
        if updated:
            exi.save()
        return exi, created, updated

    fallback_matches = [
        obj
        for obj in _get_room_contents(location)
        if getattr(obj, "destination", None) == destination
    ]
    if fallback_matches:
        exi = fallback_matches[0]
        if exi.key != key:
            exi.key = key
            updated = True
        if _ensure_aliases(exi, aliases):
            updated = True
        if updated:
            exi.save()
        return exi, created, updated

    exi = create_object(
        Exit,
        key=key,
        location=location,
        home=location,
        destination=destination,
        aliases=_normalize_aliases(aliases),
    )
    created = True
    # 標記為 GM 大陸資產
    exi.tags.add("gm_continent", category="ownership")
    return exi, created, updated


def _ensure_npc(key, spec, room_cache):
    room_name = spec["room"]
    target_room = room_cache.get(room_name) or _find_room(room_name)
    if not target_room:
        raise WorldSpecError(f"NPC `{key}` 的目標房間不存在：{room_name}")

    npc = _find_by_key(key)
    created = False
    moved = False
    updated = False
    attributes = dict(spec.get("attributes", {}))
    attributes.setdefault("desc", spec.get("desc", ""))

    if not npc:
        npc = create_object(
            spec.get("typeclass", NPC),
            key=key,
            location=target_room,
            home=target_room,
            aliases=_normalize_aliases(spec.get("aliases", [])),
            attributes=list(attributes.items()),
        )
        npc.tags.add("gm_continent", category="ownership")
        created = True
        return npc, created, moved, updated

    if npc.location != target_room:
        npc.location = target_room
        npc.home = target_room
        moved = True
    elif npc.home != target_room:
        npc.home = target_room
        moved = True
    if not _matches_desc(npc, spec.get("desc", "")):
        npc.db.desc = spec.get("desc", "")
        updated = True
    if _ensure_aliases(npc, spec.get("aliases", [])):
        updated = True
    for attr, value in attributes.items():
        if getattr(npc.db, attr, None) != value:
            setattr(npc.db, attr, value)
            updated = True
    if moved or updated:
        npc.save()
    return npc, created, moved, updated


def _npc_defs_for_scope(scope):
    scope = set(scope)
    return {
        key: spec
        for key, spec in NPC_DEFS.items()
        if spec.get("room") in scope or len(scope) == len(ROOM_DEFS)
    }


def _ensure_hina_desc():
    updated = False
    for candidate in _find_all_by_key("hina"):
        if candidate.db.desc in (None, "", "This is User #1."):
            candidate.db.desc = PLAYER_DESC
            candidate.save()
            updated = True
    return updated


def _exit_defs_for_scope(room_names):
    room_names = set(room_names)
    matches = []
    for exit_key, source_name, dest_name, aliases in EXIT_DEFS:
        if source_name in room_names or dest_name in room_names:
            matches.append((exit_key, source_name, dest_name, aliases))
    return matches


def _ensure_room_dependencies(room_cache, scoped_exit_defs):
    for _exit_key, source_name, dest_name, _aliases in scoped_exit_defs:
        for room_name in (source_name, dest_name):
            if room_name in room_cache:
                continue
            room_def = ROOM_DEFS[room_name]
            room, _created, _updated = _ensure_room(room_name, room_def["desc"])
            room_cache[room_name] = room


def _get_or_create_force_rebuild_staging_room():
    staging = _find_by_key(FORCE_REBUILD_STAGING_KEY)
    if staging:
        if not _matches_desc(staging, FORCE_REBUILD_STAGING_DESC):
            staging.db.desc = FORCE_REBUILD_STAGING_DESC
            staging.save()
        return staging, False

    staging = create_object(
        Room,
        key=FORCE_REBUILD_STAGING_KEY,
        attributes=[("desc", FORCE_REBUILD_STAGING_DESC)],
    )
    return staging, True


def _move_obj_to_room(obj, room):
    changed = False
    if getattr(obj, "location", None) != room:
        obj.location = room
        changed = True

    try:
        current_home = getattr(obj, "home", None)
    except Exception:
        current_home = None
    if current_home != room:
        obj.home = room
        changed = True

    if changed:
        obj.save()
    return changed


def _spec_scenery_keys():
    return {
        obj_def["key"]
        for room_def in ROOM_DEFS.values()
        for obj_def in room_def["objects"]
    }


def _delete_all_spec_scenery():
    deleted = 0
    for room_name in ROOM_ORDER:
        room = _find_room(room_name)
        if not room:
            continue
        expected_object_keys = {
            obj_def["key"] for obj_def in ROOM_DEFS[room_name]["objects"]
        }
        for obj in list(_get_room_contents(room)):
            if getattr(obj, "destination", None) is not None:
                continue
            if obj.key not in expected_object_keys:
                continue
            obj.delete()
            deleted += 1

    spec_keys = _spec_scenery_keys()
    for key in spec_keys:
        for obj in _find_all_by_key(key):
            if getattr(obj, "destination", None) is not None:
                continue
            obj.delete()
            deleted += 1
    return deleted


def force_rebuild_agent_world():
    """Delete the live Agent 世界 spec rooms and rebuild them from source of truth."""

    from world.agent_xyzgrid import migrate_existing_world_to_xyzgrid

    staging_room, staging_created = _get_or_create_force_rebuild_staging_room()
    preserved_keys = []
    stats = {
        "staging_created": int(staging_created),
        "rooms_deleted": 0,
        "exits_deleted": 0,
        "objects_deleted": 0,
        "objects_preserved": 0,
        "objects_relocated_after_rebuild": 0,
    }

    stats["objects_deleted"] += _delete_all_spec_scenery()

    for room_name in ROOM_ORDER:
        room = _find_room(room_name)
        if not room:
            continue

        expected_object_keys = {
            obj_def["key"] for obj_def in ROOM_DEFS[room_name]["objects"]
        }
        for obj in list(_get_room_contents(room)):
            if getattr(obj, "destination", None) is not None:
                obj.delete()
                stats["exits_deleted"] += 1
                continue

            if obj.key in expected_object_keys:
                obj.delete()
                stats["objects_deleted"] += 1
                continue

            if _move_obj_to_room(obj, staging_room):
                stats["objects_preserved"] += 1
            preserved_keys.append(obj.key)

        room.delete()
        stats["rooms_deleted"] += 1

    build_result = build_agent_world()
    xyzgrid_result = migrate_existing_world_to_xyzgrid(spawn=True)
    fallback_room = _find_room(ROSIE_HOME) or _find_room(LIMBO_ROOM_KEY) or staging_room

    for obj_key in preserved_keys:
        obj = _find_by_key(obj_key)
        if not obj:
            continue
        if (
            getattr(obj, "location", None) == staging_room
            or getattr(obj, "home", None) == staging_room
        ):
            if _move_obj_to_room(obj, fallback_room):
                stats["objects_relocated_after_rebuild"] += 1

    staging_room = _find_by_key(FORCE_REBUILD_STAGING_KEY)
    if staging_room and not _get_room_contents(staging_room):
        staging_room.delete()

    return {
        **stats,
        "build": build_result,
        "xyzgrid": xyzgrid_result,
        "fallback_room": getattr(fallback_room, "key", None),
    }


# ---------------------------------------------------------------------------
# 第 1-3 階段：建置/狀態/檢查/試運行
# ---------------------------------------------------------------------------


def build_agent_world(room_name=None, components=None):
    scope = _resolve_scope(room_name)
    chosen = _component_selection(*(components or COMPONENT_NAMES))
    result = {
        "scope": scope,
        "components": chosen,
        "rooms_total": len(scope),
        "rooms_created": 0,
        "rooms_updated": 0,
        "details_updated": 0,
        "objects_created": 0,
        "objects_updated": 0,
        "exits_created": 0,
        "exits_updated": 0,
        "npcs_created": 0,
        "npcs_moved": 0,
        "npcs_updated": 0,
        "player_descs_updated": 0,
    }

    room_cache = {}

    for scoped_room_name in scope:
        room_def = ROOM_DEFS[scoped_room_name]
        room, created, updated = _ensure_room(scoped_room_name, room_def["desc"])
        room_cache[scoped_room_name] = room
        result["rooms_created"] += int(created)
        result["rooms_updated"] += int(updated)

        if "details" in chosen and _ensure_room_details(room, room_def["details"]):
            result["details_updated"] += 1

        if "objects" in chosen:
            for obj_def in room_def["objects"]:
                _, obj_created, obj_updated = _ensure_object(
                    obj_def["key"],
                    room,
                    obj_def["desc"],
                    aliases=obj_def.get("aliases", []),
                )
                result["objects_created"] += int(obj_created)
                result["objects_updated"] += int(obj_updated)

    if "exits" in chosen:
        scoped_exit_defs = _exit_defs_for_scope(scope)
        _ensure_room_dependencies(room_cache, scoped_exit_defs)
        for exit_key, source_name, dest_name, aliases in scoped_exit_defs:
            _, created, updated = _ensure_exit(
                exit_key,
                room_cache[source_name],
                room_cache[dest_name],
                aliases=aliases,
            )
            result["exits_created"] += int(created)
            result["exits_updated"] += int(updated)

    if "npcs" in chosen:
        for npc_key, npc_spec in _npc_defs_for_scope(scope).items():
            _npc, npc_created, npc_moved, npc_updated = _ensure_npc(
                npc_key, npc_spec, room_cache
            )
            result["npcs_created"] += int(npc_created)
            result["npcs_moved"] += int(npc_moved)
            result["npcs_updated"] += int(npc_updated)
        result["player_descs_updated"] += int(_ensure_hina_desc())

    from world.account_tools import ensure_first_player_account_is_gm

    result["bootstrap"] = ensure_first_player_account_is_gm()
    result["rooms"] = scope
    return result


def _check_room_desc(room_name, room, issues, stats):
    expected = ROOM_DEFS[room_name]["desc"]
    if not _matches_desc(room, expected):
        issues.append(f"- {room_name}：房間描述與規格不一致。")
        stats["room_desc_updates"] += 1


def _check_room_details(room_name, room, issues, stats):
    current_details = _detail_map(room)
    for aliases, desc in ROOM_DEFS[room_name]["details"]:
        for alias in aliases:
            current_desc = current_details.get(alias)
            if current_desc is None:
                issues.append(f"- {room_name}：缺少 detail `{alias}`。")
                stats["detail_aliases_missing"] += 1
            elif _clean_text(current_desc) != _clean_text(desc):
                issues.append(f"- {room_name}：detail `{alias}` 描述不一致。")
                stats["detail_desc_updates"] += 1


def _check_room_objects(room_name, room, issues, stats):
    for obj_def in ROOM_DEFS[room_name]["objects"]:
        obj = _find_object_in_room(room, obj_def["key"])
        if not obj:
            issues.append(f"- {room_name}：缺少場景物 `{obj_def['key']}`。")
            stats["objects_missing"] += 1
            continue
        if not _matches_desc(obj, obj_def["desc"]):
            issues.append(f"- {room_name}：場景物 `{obj_def['key']}` 描述不一致。")
            stats["object_desc_updates"] += 1
        missing_aliases = _missing_aliases(obj, obj_def.get("aliases", []))
        if missing_aliases:
            issues.append(
                f"- {room_name}：場景物 `{obj_def['key']}` 缺少 alias：{_format_list(missing_aliases)}。"
            )
            stats["object_aliases_missing"] += len(missing_aliases)


def _check_room_exits(scope, issues, stats):
    for exit_key, source_name, dest_name, aliases in _exit_defs_for_scope(scope):
        source_room = _find_room(source_name)
        dest_room = _find_room(dest_name)
        if not source_room:
            issues.append(f"- {source_name}：房間不存在，無法檢查出口 `{exit_key}`。")
            stats["rooms_missing"] += 1
            continue
        if not dest_room:
            issues.append(f"- 出口 `{exit_key}` 目標房間 `{dest_name}` 不存在。")
            stats["rooms_missing"] += 1
            continue
        exi = _find_exit(source_room, exit_key, destination=dest_room)
        if not exi:
            issues.append(f"- {source_name}：缺少出口 `{exit_key}` → {dest_name}。")
            stats["exits_missing"] += 1
            continue
        missing_aliases = _missing_aliases(exi, aliases)
        if missing_aliases:
            issues.append(
                f"- {source_name}：出口 `{exit_key}` 缺少 alias：{_format_list(missing_aliases)}。"
            )
            stats["exit_aliases_missing"] += len(missing_aliases)


def _check_npcs(scope, issues, stats):
    for npc_key, npc_spec in _npc_defs_for_scope(scope).items():
        npc = _find_by_key(npc_key)
        if not npc:
            issues.append(f"- 缺少 NPC `{npc_key}`。")
            stats["npcs_missing"] += 1
            continue

        target_room_name = npc_spec["room"]
        target_room = _find_room(target_room_name)
        if target_room and npc.location != target_room:
            issues.append(
                f"- `{npc_key}` 目前在 `{_find_room_name_for_obj(npc)}`，預期應在 `{target_room_name}`。"
            )
            stats["npcs_misplaced"] += 1
        if not _matches_desc(npc, npc_spec.get("desc", "")):
            issues.append(f"- `{npc_key}` 描述與規格不一致。")
            stats["npc_desc_updates"] += 1
        missing_aliases = _missing_aliases(npc, npc_spec.get("aliases", []))
        if missing_aliases:
            issues.append(f"- `{npc_key}` 缺少 alias：{_format_list(missing_aliases)}。")
            stats["npc_aliases_missing"] += len(missing_aliases)


def analyze_agent_world(room_name=None, components=None):
    scope = _resolve_scope(room_name)
    chosen = _component_selection(*(components or COMPONENT_NAMES))
    issues = []
    stats = {
        "rooms_missing": 0,
        "room_desc_updates": 0,
        "detail_aliases_missing": 0,
        "detail_desc_updates": 0,
        "objects_missing": 0,
        "object_desc_updates": 0,
        "object_aliases_missing": 0,
        "exits_missing": 0,
        "exit_aliases_missing": 0,
        "npcs_missing": 0,
        "npcs_misplaced": 0,
        "npc_desc_updates": 0,
        "npc_aliases_missing": 0,
    }

    for scoped_room_name in scope:
        room = _find_room(scoped_room_name)
        if not room:
            issues.append(f"- {scoped_room_name}：房間不存在。")
            stats["rooms_missing"] += 1
            continue
        if "rooms" in chosen:
            _check_room_desc(scoped_room_name, room, issues, stats)
        if "details" in chosen:
            _check_room_details(scoped_room_name, room, issues, stats)
        if "objects" in chosen:
            _check_room_objects(scoped_room_name, room, issues, stats)

    if "exits" in chosen:
        _check_room_exits(scope, issues, stats)
    if "npcs" in chosen:
        _check_npcs(scope, issues, stats)

    actionable_total = sum(stats.values())
    return {
        "scope": scope,
        "components": chosen,
        "issues": issues,
        "stats": stats,
        "actionable_total": actionable_total,
        "is_clean": actionable_total == 0,
    }


def render_analysis(analysis, mode="check"):
    header = "|w世界檢查結果|n" if mode == "check" else "|w世界 dry-run 預估|n"
    lines = [header]
    lines.append(f"- 範圍：{_format_list(analysis['scope'])}")
    lines.append(f"- 元件：{_format_list(analysis['components'])}")
    lines.append(f"- 待處理項目：{analysis['actionable_total']}")
    lines.append("")

    if analysis["is_clean"]:
        lines.append("目前範圍內沒有發現需要修正的項目。")
        return "\n".join(lines)

    lines.append("需要處理的項目：")
    lines.extend(analysis["issues"])
    lines.append("")
    lines.append("摘要：")
    for key, value in analysis["stats"].items():
        if value:
            lines.append(f"- {key}: {value}")
    return "\n".join(lines)


def summarize_room(room_name):
    room = _get_room_or_error(room_name)
    exits = sorted(exi.key for exi in room.exits)
    contents = sorted(
        obj.key
        for obj in _get_room_contents(room)
        if getattr(obj, "destination", None) is None
    )
    details = sorted(_detail_map(room).keys())
    lines = [f"房間：{room.key}"]
    lines.append(f"- 描述：{_clean_text(getattr(room.db, 'desc', '')) or '無'}")
    lines.append(f"- 出口：{_format_list(exits)}")
    lines.append(f"- 內容：{_format_list(contents)}")
    lines.append(f"- details：{len(details)} 個（{_format_list(details)}）")
    return "\n".join(lines)


def summarize_agent_world(room_name=None):
    if room_name:
        return summarize_room(room_name)

    lines = ["世界房間："]
    for scoped_room_name in ROOM_ORDER:
        room = _find_room(scoped_room_name)
        if not room:
            lines.append(f"- {scoped_room_name}：尚未建立")
            continue
        exits = sorted(exi.key for exi in room.exits)
        things = sorted(
            obj.key
            for obj in _get_room_contents(room)
            if getattr(obj, "destination", None) is None
        )
        detail_count = len(_detail_map(room))
        lines.append(
            f"- {room.key}｜出口：{_format_list(exits)}｜內容：{_format_list(things)}｜細節：{detail_count}"
        )
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# 第 4 階段：即時世界管理操作
# ---------------------------------------------------------------------------


def create_live_room(room_name, desc=None):
    room_name = _clean_text(room_name)
    if not room_name:
        raise WorldSpecError("addroom 需要房間名稱。")
    if _find_room(room_name):
        raise WorldSpecError(f"房間已存在：{room_name}")
    desc = _clean_text(desc) or DEFAULT_ROOM_DESC
    room = create_object(
        Room, key=room_name, home=_worldbuild_home_room(), attributes=[("desc", desc)]
    )
    return {
        "room": room,
        "message": f"已建立房間 `{room_name}`。這是 live 世界變更，尚未回寫 world/agent_world.py。",
    }


def add_live_room_detail(room_name, aliases, desc):
    room = _get_room_or_error(room_name)
    aliases = _normalize_aliases(aliases)
    desc = _clean_text(desc)
    if not aliases or not desc:
        raise WorldSpecError("adddetail 需要 alias 與描述。")
    for alias in aliases:
        room.add_detail(alias, desc)
    return {
        "room": room,
        "message": f"已在 `{room.key}` 新增/覆寫 detail：{_format_list(aliases)}。這是 live 世界變更，尚未回寫 world/agent_world.py。",
    }


def add_live_scenery(room_name, object_key, desc, aliases=None):
    room = _get_room_or_error(room_name)
    object_key = _clean_text(object_key)
    desc = _clean_text(desc) or DEFAULT_SCENERY_DESC
    if not object_key:
        raise WorldSpecError("addscenery 需要物件名稱。")
    obj = _find_object_in_room(room, object_key)
    created = False
    if not obj:
        obj = create_object(
            Object,
            key=object_key,
            location=room,
            home=room,
            aliases=_normalize_aliases(aliases),
            locks=SCENERY_LOCKS,
            attributes=[("desc", desc)],
        )
        created = True
    else:
        obj.db.desc = desc
        obj.locks.add(SCENERY_LOCKS)
        _ensure_aliases(obj, aliases)
        obj.save()
    return {
        "object": obj,
        "created": created,
        "message": f"已在 `{room.key}` {'新增' if created else '更新'}場景物 `{object_key}`。這是 live 世界變更，尚未回寫 world/agent_world.py。",
    }


def add_live_exit(source_name, exit_key, dest_name, aliases=None):
    source_room = _get_room_or_error(source_name)
    dest_room = _get_room_or_error(dest_name)
    exit_key = _clean_text(exit_key)
    if not exit_key:
        raise WorldSpecError("addexit 需要出口名稱。")
    exi, created, updated = _ensure_exit(
        exit_key, source_room, dest_room, aliases=aliases
    )
    return {
        "exit": exi,
        "created": created,
        "updated": updated,
        "message": f"已在 `{source_room.key}` {'新增' if created else '更新'}出口 `{exit_key}` → `{dest_room.key}`。這是 live 世界變更，尚未回寫 world/agent_world.py。",
    }


def move_live_entity(entity_key, dest_name):
    entity_key = _clean_text(entity_key)
    if not entity_key:
        raise WorldSpecError("move 需要物件或角色名稱。")
    dest_room = _get_room_or_error(dest_name)
    matches = _find_all_by_key(entity_key)
    if not matches:
        raise WorldSpecError(f"找不到物件或角色：{entity_key}")
    if len(matches) > 1:
        where = [f"{obj.key}@{_find_room_name_for_obj(obj)}" for obj in matches]
        raise WorldSpecError(
            f"找到多個同名目標：{_format_list(where)}，請先改成唯一名稱後再移動。"
        )
    obj = matches[0]
    obj.location = dest_room
    if getattr(obj, "home", None) != dest_room:
        obj.home = dest_room
    obj.save()
    return {
        "entity": obj,
        "message": f"已把 `{obj.key}` 移到 `{dest_room.key}`。這是 live 世界變更，尚未回寫 world/agent_world.py。",
    }
