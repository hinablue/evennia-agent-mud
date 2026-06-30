"""原型

原型是創建個人化實例的簡單方法
給定類型類別。它是具有特定鍵名稱的字典。

例如，您可能有一個 Sword 類型類，它實現了所有內容
劍需要這樣做。不同劍之間的唯一區別
將是它們的鍵、描述和一些屬性。原型系統
允許創建一系列只有微小變化的此類劍。原型
也可以繼承並組合在一起形成整個層次結構（例如
給所有軍刀和所有闊劍一些共同的屬性）。注意較大的
變體，例如自訂指令或功能屬於下列層次結構
類型類別代替。

原型可以是放入全域變數中的字典
python 模組（“模組原型”）或作為字典儲存在資料庫中
特殊腳本（資料庫原型）。前者只需添加字典即可創建
Evennia 尋找原型的模組，後者是最容易創建的
在遊戲中透過 `olc` 指令/選單。

使用 `spawn` 命令讀取原型並用於建立新對象
或直接通過 `evennia.spawn` 或完整路徑 `evennia.prototypes.spawner.spawn`。

原型字典有以下關鍵字：

可能的關鍵字有：
- `prototype_key` - 原型的名稱。這是資料庫原型所必需的，
  對於模組原型，使用字典的全域變數名
- `prototype_parent` - 指向父原型的字串（如果有）。原型繼承
  與課堂類似，孩子的價值觀凌駕於父母的價值觀之上。
- `key` - 字串，主要物件識別碼。
- `typeclass` - 字串，如果未設置，將使用 `settings.BASE_OBJECT_TYPECLASS`。
- `location` - 這應該是一個有效的物件或#dbref。
- `home` - 有效物件或#dbref。
- `destination` - 僅對退出有效（物件或#dbref）。
- `permissions` - 字串或權限字串清單。
- `locks` - 用於產生物件的鎖定字串。
- `aliases` - 字串或字串清單。
- `attrs` - 屬性，以 `(attrname, value)` 形式表示為元組列表，
  `(attrname, value, category)` 或 `(attrname, value, category, locks)`。如果使用一個
   對於較短的形式，其餘部分使用預設值。
- `tags` - 標籤，作為元組列表 `(tag,)`、`(tag, category)` 或 `(tag, category, data)`。
- 任何其他關鍵字都被解釋為沒有類別或鎖定的屬性。
   這些將會在內部加入 `attrs` （相當於 `(attrname, value)`。

有關詳細信息，請參閱 `spawn` 命令和 `evennia.prototypes.spawner.spawn`。"""

# 使用基於模組的原型範例
# 變數名稱為 `prototype_key` 和
# 簡單屬性

# 從隨機導入 randint
#
# 小妖精 = {
# "key": "妖精咕嚕聲",
# 「健康」：lambda：randint（20,30），
# "resists": ["冷", "毒"],
# 「攻擊」：[「拳頭」]，
# “弱點”：[“火”，“光”]，
# “標籤”：= [（“綠皮”，“怪物”），（“人形生物”，“怪物”）]
# }
#
# GOBLIN_WIZARD = {
# "prototype_parent": "妖精",
# "key": "妖精巫師",
# "spells": ["火球", "閃電"]
# }
#
# GOBLIN_ARCHER = {
# "prototype_parent": "妖精",
# "key": "妖精弓箭手",
# 「攻擊」：[「短弓」]
# }
#
# 這是一個沒有原型的原型範例
# （也不是密鑰）自己的，所以它通常應該只是
# 用作混合，如妖精的範例
# 下面的大法師。
# ARCHWIZARD_MIXIN = {
# "attacks": ["大法師法杖"],
# "spells": ["更強的火球", "更強的照明"]
# }
#
# GOBLIN_ARCHWIZARD = {
# "key": "妖精大法師",
# “prototype_parent”：（“GOBLIN_WIZARD”，“ARCHWIZARD_MIXIN”）
# }
