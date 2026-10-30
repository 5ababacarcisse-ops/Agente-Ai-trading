"""Strict validation for live market-order responses."""

from math import isfinite


def confirmed_filled_quantity(response: dict) -> float:
    """Return executed quantity only for a fully filled, valid order response.

    Any partial, rejected, unknown, or malformed response raises so the caller
    keeps its persisted pending-order intent and requires manual reconciliation.
    """
    if not isinstance(response, dict):
        raise RuntimeError("Invalid Binance order response; pending intent retained for reconciliation")
    if response.get("status") != "FILLED":
        raise RuntimeError(
            f"Binance order status is {response.get('status')!r}, not FILLED; "
            "pending intent retained. Inspect Binance order/trade history."
        )
    try:
        executed = float(response.get("executedQty", 0))
    except (TypeError, ValueError) as exc:
        raise RuntimeError(
            "Invalid executed quantity; pending intent retained. Inspect Binance order history."
        ) from exc
    if not isfinite(executed) or executed <= 0:
        raise RuntimeError(
            "Order has no valid executed quantity; pending intent retained. Inspect Binance order history."
        )
    return executed
