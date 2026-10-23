from crypto_bot.strategy import latest_signal


def test_strategy_detects_bullish_crossover():
    signal = latest_signal([3, 2, 1, 2, 3], fast_window=2, slow_window=3)
    assert signal.action == "buy"


def test_strategy_detects_bearish_crossover():
    signal = latest_signal([1, 2, 3, 2, 1], fast_window=2, slow_window=3)
    assert signal.action == "sell"


def test_strategy_holds_when_averages_do_not_cross():
    signal = latest_signal([100] * 8, fast_window=2, slow_window=3)
    assert signal.action == "hold"


def test_strategy_rejects_insufficient_data():
    import pytest
    with pytest.raises(ValueError, match="not enough"):
        latest_signal([1, 2, 3], fast_window=2, slow_window=4)
