"""In-memory backend simulating customer, order, and refund systems.

Deliberately uses heterogeneous data formats:
- customer system: ISO 8601 timestamps
- order system: Unix epoch timestamps
- refund system: numeric status codes

This heterogeneity is the exact scenario Task Statement 1.5 describes
for PostToolUse normalization hooks.
"""
from datetime import datetime, timezone
from typing import Optional

CUSTOMERS = {
    "C-1001": {
        "id": "C-1001",
        "name": "Ada Lovelace",
        "email": "test1001@example.com",
        "verified_at": "2024-03-12T14:22:00Z",   # ISO 8601
        "tier": "gold",
    },
    "C-1002": {
        "id": "C-1002",
        "name": "Alan Turing",
        "email": "test1002@example.com",
        "verified_at": "2024-07-01T09:00:00Z",
        "tier": "standard",
    },
    "C-1003": {
        "id": "C-1003",
        "name": "Grace Hopper",
        "email": "test1003@example.com",
        "verified_at": "2024-03-12T14:22:00Z",   # ISO 8601
        "tier": "standard",
    },
}

ORDERS = {
    "O-5001": {
        "order_id": "O-5001",
        "customer_id": "C-1001",
        "amount_usd": 249.99,
        "placed_at_epoch": 1709913600,  # Unix epoch (heterogeneity!)
        "status": "delivered",
        "items": [{"sku": "WIDGET-A", "qty": 1, "price_usd": 249.99}],
    },
    "O-5002": {
        "order_id": "O-5002",
        "customer_id": "C-1001",
        "amount_usd": 89.50,
        "placed_at_epoch": 1712505600,
        "status": "delivered",
        "items": [{"sku": "GADGET-B", "qty": 2, "price_usd": 44.75}],
    },
    "O-5003": {
        "order_id": "O-5003",
        "customer_id": "C-1002",
        "amount_usd": 1299.00,    # Above refund limit on purpose
        "placed_at_epoch": 1715184000,
        "status": "delivered",
        "items": [{"sku": "PREMIUM-C", "qty": 1, "price_usd": 1299.00}],
    },
    "O-5004": {
        "order_id": "O-5004",
        "customer_id": "C-1003",
        "amount_usd": 75.00,
        "placed_at_epoch": 1717718400,   # 2024-06-07
        "status": "delivered",
        "items": [{"sku": "SHIRT-RED-M", "qty": 1, "price_usd": 75.00}],
    },
    "O-5005": {
        "order_id": "O-5005",
        "customer_id": "C-1003",
        "amount_usd": 120.00,
        "placed_at_epoch": 1719964800,   # 2024-07-03
        "status": "in_transit",
        "items": [{"sku": "GADGET-D", "qty": 1, "price_usd": 120.00}],
    },
    "O-5006": {
        "order_id": "O-5006",
        "customer_id": "C-1003",
        "amount_usd": 50.00,
        "placed_at_epoch": 1722643200,   # 2024-08-03
        "status": "delivered",
        "items": [{"sku": "ACCESSORY-X", "qty": 2, "price_usd": 25.00}],
    },
}

SHIPMENT_TRACKING = {
    "O-5005": {
        "order_id": "O-5005",
        "carrier": "FedEx",
        "tracking_number": "1Z999AA10123456784",
        "status": "in_transit",
        "last_scan": "Memphis, TN",
        "last_scan_at_epoch": 1720224000,  # 2024-07-06
        "estimated_delivery_iso": "2024-07-10T17:00:00Z",
    },
}

# Status codes (numeric, will be normalized by hook)
REFUND_STATUS = {0: "pending", 1: "completed", 2: "rejected"}
_refund_counter = 9000


def find_customer(customer_id: Optional[str] = None,
                  email: Optional[str] = None) -> list[dict]:
    """Return matching customer records. May return >1 to test clarification logic."""
    results = []
    for c in CUSTOMERS.values():
        if customer_id and c["id"] == customer_id:
            results.append(c)
        elif email and c["email"].lower() == email.lower():
            results.append(c)
    return results


def find_order(order_id: str) -> Optional[dict]:
    return ORDERS.get(order_id)


def create_refund(order_id: str, amount_usd: float) -> dict:
    global _refund_counter
    _refund_counter += 1
    return {
        "refund_id": f"R-{_refund_counter}",
        "order_id": order_id,
        "amount_usd": amount_usd,
        "status_code": 0,  # numeric, will be normalized
        "created_at_epoch": int(datetime.now(timezone.utc).timestamp()),
    }

def get_shipment_tracking(order_id: str):
    return SHIPMENT_TRACKING.get(order_id)