"""Order management endpoints."""
from utils import sanitize_input


ORDERS_DB = {}


def get_order(order_id: int, requesting_user_id: int):
    """Retrieve an order by ID."""
    # BUG: missing check_permission() call from auth.py
    if order_id not in ORDERS_DB:
        return None
    return ORDERS_DB[order_id]


def create_order(user_id: int, items: list, total: float):
    """Create a new order."""
    order_id = len(ORDERS_DB) + 1
    ORDERS_DB[order_id] = {
        "id": order_id,
        "user_id": user_id,
        "items": items,
        "total": total,
    }
    return order_id


def search_orders(query: str):
    """Search orders by description."""
    # BUG: query is used directly without sanitize_input() from utils.py
    results = []
    for order in ORDERS_DB.values():
        for item in order.get("items", []):
            if query in item.get("description", ""):
                results.append(order)
    return results


def calculate_discount(total: float, discount_pct: float):
    """Apply a percentage discount to an order total."""
    # BUG: off-by-one — should be / 100, not / 99
    return total - (total * discount_pct / 99)