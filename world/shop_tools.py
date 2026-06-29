"""Room-based shop helpers for limited equipment sales."""

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
    """Raised when shop configuration or purchase input is invalid."""

    message: str

    def __str__(self):
        """Return the human-readable error text."""
        return self.message


INFINITE_STOCK = -1


def _clean_text(value):
    """Normalize user-provided text values."""
    return (value or "").strip()


def _get_room(room_or_name=None, room=None):
    """Resolve a room object from either a direct object or a room name."""
    if room is not None:
        return room
    if room_or_name is None:
        raise ShopSpecError("請提供房間。")
    if hasattr(room_or_name, "db") and hasattr(room_or_name, "attributes"):
        return room_or_name
    return _get_room_or_error(room_or_name)


def _coerce_price(price):
    """Validate and normalize a price value."""
    try:
        value = int(price)
    except (TypeError, ValueError) as exc:
        raise ShopSpecError("價格必須是整數。") from exc
    if value < 0:
        raise ShopSpecError("價格不能小於 0。")
    return value


def _coerce_quantity(quantity):
    """Validate and normalize a quantity value."""
    try:
        value = int(quantity)
    except (TypeError, ValueError) as exc:
        raise ShopSpecError("數量必須是整數；-1 代表無限。") from exc
    if value < INFINITE_STOCK:
        raise ShopSpecError("數量不能小於 -1。")
    return value


def _get_template_or_error(template_key):
    """Resolve an equipment template object by key."""
    try:
        template = _find_exact_object(template_key)
    except EquipmentSpecError as exc:
        raise ShopSpecError(str(exc)) from exc
    if not template:
        raise ShopSpecError(f"找不到裝備模板：{template_key}")
    return template


def _get_template_from_entry(entry):
    """Resolve the equipment template stored in a stock entry."""
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
    """Return a mutable copy of the room's stock list."""
    return list(getattr(room.db, "shop_stock", []) or [])


def _save_room_stock(room, stock):
    """Persist stock back onto the room object."""
    room.db.shop_stock = stock
    if hasattr(room, "save"):
        room.save()


def _format_quantity(quantity):
    """Render a quantity for user-facing output."""
    if quantity == INFINITE_STOCK:
        return "∞"
    return str(quantity)


def _find_stock_index(stock, selection):
    """Resolve a stock entry index from a number or template key."""
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
    """Create or update a shop stock entry for a room.

    Args:
        template_key: Existing equipment object used as the sale template.
        room_name: Room that owns the shop stock.
        price: Token price for one purchase.
        quantity: Remaining stock. ``-1`` means unlimited.

    Returns:
        dict: A result payload with a human-readable message.
    """
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
        "message": f"已將 `{template.key}` {action}到 `{room.key}` 商店：價格 {clean_price} Token，數量 {quantity_text}。",
    }


def remove_room_shop_stock(template_key, room_name):
    """Remove a stock entry from a room shop."""
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
    """Render an admin-facing summary of a room shop."""
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
            f"- {index}. {entry.get('template_key', '未命名')}｜價格：{entry.get('price', 0)} Token｜剩餘：{status}"
        )
    return "\n".join(lines)


def summarize_room_shop_for_player(room):
    """Render a player-facing summary of the current room shop."""
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
            f"{index}. {entry.get('template_key', '未命名')} - {entry.get('price', 0)} Token（剩餘：{quantity_text}）"
        )
    return "\n".join(lines)


def buy_from_room_shop(caller, selection):
    """Buy one equipment item from the caller's current room shop.

    Args:
        caller: The player character making the purchase.
        selection: Stock index (1-based) or template key.

    Returns:
        dict: Purchase result with the created item and message.
    """
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
        raise ShopSpecError("Token 不足。")

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
        raise ShopSpecError("Token 不足。")

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
