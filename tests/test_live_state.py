import pytest

from crypto_bot.live_state import LiveStateStore


def test_live_state_persists_owned_quantity(tmp_path):
    path = tmp_path / "live_state.json"
    store = LiveStateStore(str(path))
    store.state.owned_quantity = 0.0123
    store.state.last_signal_candle = 12345
    store.save()

    loaded = LiveStateStore(str(path))
    assert loaded.state.owned_quantity == pytest.approx(0.0123)
    assert loaded.state.last_signal_candle == 12345


def test_corrupt_live_state_refuses_to_reset(tmp_path):
    path = tmp_path / "live_state.json"
    path.write_text("{not json", encoding="utf-8")
    with pytest.raises(RuntimeError, match="refusing to trade"):
        LiveStateStore(str(path))



def test_pending_order_intent_survives_restart(tmp_path):
    path = tmp_path / "live_state.json"
    store = LiveStateStore(str(path))
    store.state.pending_order = "BUY BTCUSDT candle=123"
    store.save()

    restarted = LiveStateStore(str(path))
    assert restarted.state.pending_order == "BUY BTCUSDT candle=123"



def test_live_state_rejects_nonfinite_position(tmp_path):
    path = tmp_path / "live_state.json"
    path.write_text('{"owned_quantity": NaN}', encoding="utf-8")
    with pytest.raises(RuntimeError, match="refusing to trade"):
        LiveStateStore(str(path))
