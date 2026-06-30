"""房間內的商店助理負責有限的設備銷售。"""

from __future__ import annotations

from dataclasses import dataclass

from evennia.objects.models import ObjectDB

from world.equipment_tools import (
    EquipmentSpecError,
    _find_exact_object,
    _get_room_or_error,
    clone_equipment,
)


@dataclass
class ShopSpecError(ValueError):
    """當商店配置或購買輸入無效時引發。"""

    message: str

    def __str__(self):
        """傳回人類可讀的錯誤文字。"""
        return self.message


INFINITE_STOCK = -1


def _clean_text(value):
    """規範化使用者提供的文字值。"""
    return (value or "").strip()


def _get_room(room_or_name=None, room=None):
    """從直接物件或房間名稱解析房間物件。"""
    if room is not None:
        return room
    if room_or_name is None:
        raise ShopSpecError("請提供房間。")
    if hasattr(room_or_name, "db") and hasattr(room_or_name, "attributes"):
        return room_or_name
    return _get_room_or_error(room_or_name)


def _coerce_price(price):
    """驗證並標準化價格值。"""
    try:
        value = int(price)
    except (TypeError, ValueError) as exc:
        raise ShopSpecError("價格必須是整數。") from exc
    if value < 0:
        raise ShopSpecError("價格不能小於 0。")
    return value


def _coerce_quantity(quantity):
    """驗證並標準化數量值。"""
    try:
        value = int(quantity)
    except (TypeError, ValueError) as exc:
        raise ShopSpecError("數量必須是整數；-1 代表無限。") from exc
    if value < INFINITE_STOCK:
        raise ShopSpecError("數量不能小於 -1。")
    return value


def _get_template_or_error(template_key):
    """透過鍵解析設備模板物件。"""
    try:
        template = _find_exact_object(template_key)
    except EquipmentSpecError as exc:
        raise ShopSpecError(str(exc)) from exc
    if not template:
        raise ShopSpecError(f"找不到裝備模板：{template_key}")
    return template


def _get_template_from_entry(entry):
    """解析儲存在庫存條目中的設備模板。"""
    template_id = entry.get("template_id")
    if template_id is not None:
        try:
            return ObjectDB.objects.get(id=template_id)
        except Exception:
            pass
    template_key = entry.get("template_key")
    template = _find_exact_object(template_key)
    if not template:
        raise ShopSpecError(f"商店模板不存在：{template_key}")
    return template


def _get_room_stock(room):
    """返回房間庫存清單的可變副本。"""
    return list(getattr(room.db, "shop_stock", []) or [])


def _save_room_stock(room, stock):
    """將庫存保留回房間物件上。"""
    room.db.shop_stock = stock
    if hasattr(room, "save"):
        room.save()


def _format_quantity(quantity):
    """渲染面向使用者的輸出量。"""
    if quantity == INFINITE_STOCK:
        return "∞"
    return str(quantity)


def _find_stock_index(stock, selection):
    """從數字或範本鍵解析股票條目索引。"""
    selection = _clean_text(selection)
    if not selection:
        raise ShopSpecError("請指定商品編號或名稱。")

    if selection.isdigit():
        index = int(selection) - 1
        if 0 <= index < len(stock):
            return index
        raise ShopSpecError("找不到這個商品編號。")

    lowered = selection.lower()
    for index, entry in enumerate(stock):
        if str(entry.get("template_key", "")).lower() == lowered:
            return index
    raise ShopSpecError(f"找不到商品：{selection}")


def set_room_shop_stock(template_key, room_name, price, quantity):
    """建立或更新房間的商店庫存條目。

    參數：
        template_key：用作銷售範本的現有設備物件。
        room_name：擁有商店庫存的房間。
        價格：一次購買的代幣價格。
        數量：剩餘庫存。 ``-1`` 表示無限制。

    返回：
        dict：帶有人類可讀訊息的結果有效負載。"""
    template = _get_template_or_error(template_key)
    room = _get_room(room_name)
    clean_price = _coerce_price(price)
    clean_quantity = _coerce_quantity(quantity)
    stock = _get_room_stock(room)

    entry = {
        "template_id": getattr(template, "id", None),
        "template_key": template.key,
        "price": clean_price,
        "quantity": clean_quantity,
    }

    updated = False
    for index, current in enumerate(stock):
        if current.get("template_id") == entry["template_id"] or current.get("template_key") == entry["template_key"]:
            stock[index] = entry
            updated = True
            break
    if not updated:
        stock.append(entry)

    _save_room_stock(room, stock)
    quantity_text = "無限" if clean_quantity == INFINITE_STOCK else str(clean_quantity)
    action = "更新" if updated else "加入"
    return {
        "room": room,
        "entry": entry,
        "message": f"已將 `{template.key}` {action}到 `{room.key}` 商店：價格 {clean_price} 代幣，數量 {quantity_text}。",
    }


def remove_room_shop_stock(template_key, room_name):
    """從房間商店中刪除庫存條目。"""
    room = _get_room(room_name)
    template = _get_template_or_error(template_key)
    stock = _get_room_stock(room)
    filtered = [
        entry
        for entry in stock
        if entry.get("template_id") != getattr(template, "id", None)
        and entry.get("template_key") != template.key
    ]
    if len(filtered) == len(stock):
        raise ShopSpecError(f"`{room.key}` 商店中沒有 `{template.key}`。")
    _save_room_stock(room, filtered)
    return {
        "room": room,
        "message": f"已將 `{template.key}` 從 `{room.key}` 商店下架。",
    }


def summarize_room_shop(room_name=None, room=None):
    """呈現面向管理員的房間商店摘要。"""
    room = _get_room(room_name, room=room)
    stock = _get_room_stock(room)
    lines = [f"商店清單：{room.key}"]
    if not stock:
        lines.append("- 目前沒有上架商品。")
        return "\n".join(lines)

    for index, entry in enumerate(stock, 1):
        quantity = entry.get("quantity", 0)
        status = "售完" if quantity == 0 else _format_quantity(quantity)
        lines.append(
            f"- {index}. {entry.get('template_key', '未命名')}｜價格：{entry.get('price', 0)} 代幣｜剩餘：{status}"
        )
    return "\n".join(lines)


def summarize_room_shop_for_player(room):
    """渲染目前房間商店面向玩家的摘要。"""
    room = _get_room(room=room)
    stock = _get_room_stock(room)
    lines = [f"|w{room.key} 商店清單|n"]
    if not stock:
        lines.append("這裡目前沒有販售任何商品。")
        return "\n".join(lines)

    for index, entry in enumerate(stock, 1):
        quantity = entry.get("quantity", 0)
        if quantity == INFINITE_STOCK:
            quantity_text = "∞"
        elif quantity == 0:
            quantity_text = "售完"
        else:
            quantity_text = str(quantity)
        lines.append(
            f"{index}. {entry.get('template_key', '未命名')} - {entry.get('price', 0)} 代幣（剩餘：{quantity_text}）"
        )
    return "\n".join(lines)


def buy_from_room_shop(caller, selection):
    """從呼叫者目前的房間商店購買一件設備。

    參數：
        呼叫者：進行購買的玩家角色。
        選擇：股票索引（從 1 開始）或範本鍵。

    返回：
        dict：帶有創建的項目和訊息的購買結果。"""
    room = getattr(caller, "location", None)
    if not room:
        raise ShopSpecError("你現在不在任何房間裡。")

    stock = _get_room_stock(room)
    if not stock:
        raise ShopSpecError("這裡沒有可以購買的商品。")

    index = _find_stock_index(stock, selection)
    entry = dict(stock[index])
    quantity = int(entry.get("quantity", 0))
    if quantity == 0:
        raise ShopSpecError(f"`{entry.get('template_key', '這個商品')}` 已經售完。")

    template = _get_template_from_entry(entry)
    price = _coerce_price(entry.get("price", 0))
    if getattr(caller, "get_tokens", None) and caller.get_tokens() < price:
        raise ShopSpecError("代幣不足。")

    clone_result = clone_equipment(
        template.key,
        location=caller,
        home=room,
        allow_duplicate_key=True,
    )
    new_item = clone_result["equipment"]

    if not caller.add_to_inventory(new_item):
        if hasattr(new_item, "delete"):
            new_item.delete()
        raise ShopSpecError("背包已滿。")

    if not caller.spend_tokens(price):
        caller.remove_from_inventory(new_item)
        if hasattr(new_item, "delete"):
            new_item.delete()
        raise ShopSpecError("代幣不足。")

    if quantity != INFINITE_STOCK:
        entry["quantity"] = max(0, quantity - 1)
        stock[index] = entry
        _save_room_stock(room, stock)

    remaining = entry.get("quantity", INFINITE_STOCK)
    remaining_text = "∞" if remaining == INFINITE_STOCK else str(remaining)
    return {
        "item": new_item,
        "message": f"你購買了 {new_item.key}。剩餘數量：{remaining_text}。",
    }
