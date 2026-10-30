import pytest

from crypto_bot.live_orders import confirmed_filled_quantity


def test_accepts_only_fully_filled_order():
    assert confirmed_filled_quantity({"status": "FILLED", "executedQty": "0.012"}) == pytest.approx(0.012)


@pytest.mark.parametrize("status", ["PARTIALLY_FILLED", "NEW", "CANCELED", "REJECTED", None])
def test_non_filled_order_keeps_pending_intent(status):
    with pytest.raises(RuntimeError, match="pending intent retained"):
        confirmed_filled_quantity({"status": status, "executedQty": "0.004"})


@pytest.mark.parametrize("quantity", ["0", "-1", "NaN", "Infinity", None, "bad"])
def test_invalid_executed_quantity_is_rejected(quantity):
    with pytest.raises(RuntimeError, match="pending intent retained"):
        confirmed_filled_quantity({"status": "FILLED", "executedQty": quantity})


def test_non_object_response_is_rejected():
    with pytest.raises(RuntimeError, match="pending intent retained"):
        confirmed_filled_quantity(None)
